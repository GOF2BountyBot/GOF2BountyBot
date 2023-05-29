import os
from typing import Callable, List, Optional, Set, Tuple, Union, cast
from enum import Enum

from discord import Colour, Embed, app_commands, Interaction, SelectOption, ButtonStyle
from discord.utils import MISSING
from discord.app_commands import Range
from discord.ui import View, Button, Select

from .. import client, lib
from ..lib.discordUtil import ImageFile
from ..cfg import bbData, cfg
from ..cfg.cfg import basicAccessLevels
from ..interactions import basedCommand
from ..interactions.basedApp import BasedCog
from ..interactions.basedComponent import StaticComponents
from .util.CommonAutocomplete import criminalAutoComplete, CriminalKey, \
                                    shipAutoComplete, ShipKey, \
                                    shipSkinAutoComplete, ShipSkinKey, \
                                    systemAutoComplete, SystemKey, \
                                    weaponAutoComplete, PrimaryWeaponKey, \
                                    moduleAutoComplete, ModuleKey, \
                                    turretAutoComplete, TurretKey, \
                                    toolAutoComplete, ToolKey, \
                                    medalAutoComplete, MedalKey
from .util.EmbedEditorUtil import interactionErrorString
from ..gameObjects.bounties.bountyBoards import bountyBoardChannel
from ..gameObjects.items.ships.shipBlueprint import ShipBlueprint
from ..baseClasses.embedFillable import EmbedFillableMixin
from ..gameObjects.gameObject import SerializedLoadedObject
from ..logging import LogCategory

class ListSearchableItemTypes(Enum):
    """Extended from bbData.ItemCategory"""
    ship = "ship"
    weapon = "weapon"
    module = "module"
    turret = "turret"
    tool = "tool"
    criminal = "criminal"
    skin = "skin"
    medal = "medal"
    system = "system"

CWD = os.getcwd()
robotIcon = "https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/twitter/259/robot_1f916.png"
SCROLL_ICON = "https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/twitter/282/scroll_1f4dc.png"

SHOW_SKIN_ARGS_SEPARATOR = "%"

def packShowSkinNumArgs(shipName: str, skinNum: int, userId: Union[str, int, None] = None) -> str:
    if SHOW_SKIN_ARGS_SEPARATOR in shipName:
        raise ValueError("shipName cannot contain reserved character " + SHOW_SKIN_ARGS_SEPARATOR)
    return f"{userId if userId else ''}{SHOW_SKIN_ARGS_SEPARATOR}{shipName}{SHOW_SKIN_ARGS_SEPARATOR}{skinNum}"


def unpackShowSkinNumArgs(args: str) -> Tuple[Optional[int], str, int]:
    userId, shipName, skinNum = args.split(SHOW_SKIN_ARGS_SEPARATOR)
    return int(userId) if userId else None, shipName, int(skinNum)


def packShowSkinNameArgs(shipName: str, userId: Union[str, int, None] = None) -> str:
    if SHOW_SKIN_ARGS_SEPARATOR in shipName:
        raise ValueError("shipName cannot contain reserved character " + SHOW_SKIN_ARGS_SEPARATOR)
    return f"{userId if userId else ''}{SHOW_SKIN_ARGS_SEPARATOR}{shipName}"


def unpackShowSkinNameArgs(args: str) -> Tuple[Optional[int], str]:
    userId, shipName = args.split(SHOW_SKIN_ARGS_SEPARATOR)
    return int(userId) if userId else None, shipName


class UserGof2InfoCog(BasedCog):
    def __init__(self, bot: "client.BasedClient", *args, **kwargs):
        super().__init__(bot, *args, **kwargs)
        self.buildListData()


    def buildListData(self):
        """Initialize data needed for the /list command."""
        self.LIST_FACTION_OBJS = {
            ListSearchableItemTypes.system: bbData.builtInSystemObjs,
            ListSearchableItemTypes.criminal: bbData.builtInCriminalObjs
        }
        self.LIST_MANUFACTURER_OBJS = {
            ListSearchableItemTypes.weapon: bbData.builtInWeaponObjs,
            ListSearchableItemTypes.module: bbData.builtInModuleObjs,
            ListSearchableItemTypes.turret: bbData.builtInTurretObjs,
            ListSearchableItemTypes.ship: bbData.builtInShipData
        }
        self.LIST_TL_OBJS = {
            ListSearchableItemTypes.weapon: bbData.builtInWeaponObjs, 
            ListSearchableItemTypes.module: bbData.builtInModuleObjs,
            ListSearchableItemTypes.turret: bbData.builtInTurretObjs, 
            ListSearchableItemTypes.ship: bbData.builtInShipData
        }
        self.LIST_DICT_OBJS = {
            ListSearchableItemTypes.ship: bbData.builtInShipData
        }


#region util

    async def objectInfo(self, interaction: Interaction, obj: EmbedFillableMixin, objectTypeName: str):
        statsEmbed = Embed(description=f"__{objectTypeName} Information__")
        attachments = obj.fillEmbed(statsEmbed)
        
        await interaction.response.send_message(embed=statsEmbed, files=MISSING if attachments is None else [f.file for f in attachments])

        for f in attachments or []:
            f.closeAll()


    def makeShowSkinView(self, shipName: str, currentSkin: int, userId: Union[str, int, None] = None) -> Optional[View]:
        shipData = bbData.builtInShipData[shipName]
        compatibleSkins = shipData.get("compatibleSkins", [])
        skinnable = shipData.get("skinnable", False)
        
        if not (skinnable and compatibleSkins):
            return None
        
        lastSkin = len(compatibleSkins)
        currentSkin = max(0, min(currentSkin, lastSkin))
        previousSkin = currentSkin - 1
        previousSkin = lastSkin if previousSkin < 0 else previousSkin
        nextSkin = currentSkin + 1
        nextSkin = 0 if nextSkin > lastSkin else nextSkin
        
        currentSkinName = "No skin" if currentSkin == 0 else compatibleSkins[currentSkin - 1]
        
        view = View()
        
        prevButton = Button(emoji=cfg.defaultEmojis.previous.sendable, row=0)
        prevButton = StaticComponents.User_ShowShip_WithSkinNumber(prevButton, packShowSkinNumArgs(shipName, previousSkin, userId))
        view.add_item(prevButton)
        
        nextButton = Button(emoji=cfg.defaultEmojis.next.sendable, row=0)
        nextButton = StaticComponents.User_ShowShip_WithSkinNumber(nextButton, packShowSkinNumArgs(shipName, nextSkin, userId))
        view.add_item(nextButton)

        if userId:
            deleteButton = Button(emoji=cfg.defaultEmojis.delete.sendable, row=0, style=ButtonStyle.red)
            deleteButton = StaticComponents.Delete_Message(deleteButton, str(userId))
            view.add_item(deleteButton)
        
        options = [
            SelectOption(label=name.title(), value=str(i + 1), default=i == currentSkin - 1) for i, name in enumerate(compatibleSkins)
        ]
        options = [SelectOption(label="No skin", value="0", default=currentSkin == 0)] + options
        
        skinSelect = Select(placeholder=currentSkinName.title(), row=1, options=options)
        skinSelect = StaticComponents.User_ShowShip_WithSkinName(skinSelect, packShowSkinNameArgs(shipName, userId))
        view.add_item(skinSelect)
        
        return view


    def makeShowSkinEmbed(self, shipName: str, currentSkin: int, userId: Union[str, int, None] = None) -> Embed:
        shipData = bbData.builtInShipData[shipName]
        compatibleSkins = shipData.get("compatibleSkins", [])
        skinnable = shipData.get("skinnable", False)
        owner = self.bot.get_user(int(userId)) if userId else None
        
        if currentSkin == 0:
            skinName = "Default texture"
            img = shipData.get("icon", None)
        else:
            skin = compatibleSkins[currentSkin - 1]
            skinName = f"Skin: {skin.capitalize()}"
            img = bbData.builtInShipSkins[skin].shipRenders[shipName][0]
        
        embed = lib.discordUtil.makeEmbed(
            col=Colour.random(),
            img=img,
            titleTxt=shipName,
            desc=skinName,
            footerTxt=f"Menu owned by: {owner}" if owner and skinnable and compatibleSkins else ""
        )
        
        return embed

#endregion
#region static components

    @BasedCog.staticComponentCallback(StaticComponents.User_ShowShip_WithSkinNumber)
    async def showShipWithSkinNumber(self, interaction: Interaction, args: str):
        userId, shipName, skinNum = unpackShowSkinNumArgs(args)
        if not self.CommonStaticComponentsCog.ensureOwnership(interaction, userId): return
        
        view = self.makeShowSkinView(shipName, skinNum, userId)
        embed = self.makeShowSkinEmbed(shipName, skinNum, userId)
        
        await interaction.response.edit_message(embed=embed, view=view)
            
            
    @BasedCog.staticComponentCallback(StaticComponents.User_ShowShip_WithSkinName)
    async def showShipWithSkinName(self, interaction: Interaction, args: str):
        userId, shipName = unpackShowSkinNameArgs(args)
        if not self.CommonStaticComponentsCog.ensureOwnership(interaction, userId): return
        
        selected: Optional[List[str]] = None if interaction.data is None else interaction.data.get("values", None)

        if not selected:
            await interaction.response.send_message(f"{cfg.defaultEmojis.cancel} This type of interaction is not valid here.", ephemeral=True)
            self.bot.logger.log(UserGof2InfoCog.__name__, UserGof2InfoCog.showShipWithSkinName.__name__,
                                "select-based static component triggered for non-select interaction: " \
                                    + interactionErrorString(interaction, StaticComponents.User_ShowShip_WithSkinName),
                                category=LogCategory.staticComponents, eventType="COMPONENT_NOT_SELECT", interaction=interaction)
            return
        
        skinNum = int(selected[0])
        view = self.makeShowSkinView(shipName, skinNum, userId)
        embed = self.makeShowSkinEmbed(shipName, skinNum, userId)
        
        await interaction.response.edit_message(embed=embed, view=view)
            
        
#endregion
#region commands

    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="GOF2 Info")
    @app_commands.command(name="map",
                            description="Send the complete GOF2 starmap with jumpgate routes, including all secret and DLC systems.")
    async def cmd_map(self, interaction: Interaction):
        """send the image of the GOF2 starmap
        """
        await interaction.response.send_message(bbData.mapImageNoGraphLink)


    @systemAutoComplete("start")
    @systemAutoComplete("end")
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="GOF2 Info",
                                formattedDesc="Find the shortest route from `start` to `end`. Both systems must have jump " \
                                            + "gates. To find out if a system has a jump gate, use `info`.")
    @app_commands.command(name="make-route",
                            description="Find the shortest route between two systems.")
    async def cmd_make_route(self, interaction: Interaction, start: SystemKey, end: SystemKey):
        """display the shortest route between two systems
        """
        if start == end:
            await interaction.response.send_message(":thinking: You're already there, pilot!")
            return

        startSyst = bbData.builtInSystemObjs[start]
        endSyst = bbData.builtInSystemObjs[end]
        # report any systems that were recognised, but do not have any neighbours
        if not startSyst.hasJumpGate():
            await interaction.response.send_message(f":x: The **{start}** system does not have a jump gate!", ephemeral=True)
            return
        if not endSyst.hasJumpGate():
            await interaction.response.send_message(f":x: The **{endSyst}** system does not have a jump gate!", ephemeral=True)
            return

        # build and print the route, reporting any errors in the route generation process
        routeStr = ""
        route = lib.pathfinding.makeRoute(startSyst.name, endSyst.name)
        
        if route is lib.pathfinding.PathfindingError.MAX_LENGTH_REACHED:
            await interaction.response.send_message(":x: ERR: The route was too long to compute!")
        elif route is lib.pathfinding.PathfindingError.NO_ROUTE_FOUND:
            await interaction.response.send_message(":x: ERR: No route found!")
        else:
            routeStr = ", ".join(route)
            routeImg = bountyBoardChannel.renderRouteMap(route)
            if routeImg is None:
                routeFile = MISSING
            else:
                routeFile = ImageFile(routeImg, "route.png")

            await interaction.response.send_message(f"Here's the shortest route from **{startSyst.name}** to **{endSyst.name}**:\n> {routeStr} :rocket:",
                                                    file=routeFile.file)

            if routeFile is not None:
                routeFile.closeAll()

#region info

    @systemAutoComplete()
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="GOF2 Info")
    @app_commands.command(name="info-system",
                            description="Look up information about a system in the galaxy.")
    async def cmd_info_system(self, interaction: Interaction, system: SystemKey):
        """return statistics about a specified system
        """
        await self.objectInfo(interaction, bbData.builtInSystemObjs[system], "System")

    
    @criminalAutoComplete()
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="GOF2 Info")
    @app_commands.command(name="info-criminal",
                            description="Look up information about a criminal.")
    async def cmd_info_criminal(self, interaction: Interaction, name: CriminalKey):
        """return statistics about a specified criminal
        """
        await self.objectInfo(interaction, bbData.builtInCriminalObjs[name], "Criminal")

    
    @shipAutoComplete()
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="GOF2 Info")
    @app_commands.command(name="info-ship",
                            description="Look up information about a ship.")
    async def cmd_info_ship(self, interaction: Interaction, ship: ShipKey):
        """return statistics about a specified ship
        """
        await self.objectInfo(interaction, ShipBlueprint.deserialize(bbData.builtInShipData[ship]), "Ship")

    
    @weaponAutoComplete()
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="GOF2 Info")
    @app_commands.command(name="info-weapon",
                            description="Look up information about a weapon.")
    async def cmd_info_weapon(self, interaction: Interaction, weapon: PrimaryWeaponKey):
        """return statistics about a specified weapon
        """
        await self.objectInfo(interaction, bbData.builtInWeaponObjs[weapon], "Weapon")

    
    @moduleAutoComplete()
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="GOF2 Info")
    @app_commands.command(name="info-module",
                            description="Look up information about a module.")
    async def cmd_info_module(self, interaction: Interaction, module: ModuleKey):
        """return statistics about a specified module
        """
        await self.objectInfo(interaction, bbData.builtInModuleObjs[module], "Module")

    
    @turretAutoComplete()
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="GOF2 Info")
    @app_commands.command(name="info-turret",
                            description="Look up information about a turret.")
    async def cmd_info_turret(self, interaction: Interaction, turret: TurretKey):
        """return statistics about a specified turret
        """
        await self.objectInfo(interaction, bbData.builtInTurretObjs[turret], "Turret")

    
    @shipSkinAutoComplete()
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="GOF2 Info")
    @app_commands.command(name="info-skin",
                            description="Look up information about a skin.")
    async def cmd_info_skin(self, interaction: Interaction, skin: ShipSkinKey):
        """return statistics about a specified skin
        """
        await self.objectInfo(interaction, bbData.builtInShipSkins[skin], "Skin")

    
    @medalAutoComplete()
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="GOF2 Info")
    @app_commands.command(name="info-medal",
                            description="Look up information about a medal.")
    async def cmd_info_medal(self, interaction: Interaction, medal: MedalKey):
        """return statistics about a specified medal
        """
        await self.objectInfo(interaction, bbData.medalObjs[medal], "Medal")

    
    @toolAutoComplete()
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="GOF2 Info")
    @app_commands.command(name="info-tool",
                            description="Look up information about a tool.")
    async def cmd_info_tool(self, interaction: Interaction, tool: ToolKey):
        """return statistics about a specified tool
        """
        await self.objectInfo(interaction, bbData.builtInToolObjs[tool], "Tool")

#endregion info
#region showme
    
    @criminalAutoComplete()
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="GOF2 Info")
    @app_commands.command(name="showme-criminal",
                            description="Look up the image for a criminal.")
    async def cmd_showme_criminal(self, interaction: Interaction, name: CriminalKey):
        """Get the icon for the specified criminal
        """
        obj = bbData.builtInCriminalObjs[name]
        embed = Embed(title=obj.name)
        embed.set_image(url=obj.icon)
        embed.colour = Colour.random()
        await interaction.response.send_message(embed=embed)

    
    @shipAutoComplete()
    @shipSkinAutoComplete()
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="GOF2 Info")
    @app_commands.command(name="showme-ship",
                            description="Look up the image for a ship.")
    async def cmd_showme_ship(self, interaction: Interaction, ship: ShipKey, skin: Optional[ShipSkinKey] = None):
        """Get the icon for the specified ship
        """
        shipData = bbData.builtInShipData[ship]
        if skin is not None:
            if not shipData["skinnable"]:
                await interaction.response.send_message(":x: That ship is not skinnable!", ephemeral=True)
                return

            compatibleSkins = shipData.get("compatibleSkins", [])
            if skin not in compatibleSkins:
                await interaction.response.send_message(f":x: That skin is not compatible with the **{ship}**!", ephemeral=True)
                return
            
            skinNum = compatibleSkins.index(skin) + 1
        else:
            skinNum = 0
                
        view = self.makeShowSkinView(ship, skinNum, interaction.user.id)
        embed = self.makeShowSkinEmbed(ship, skinNum, interaction.user.id)
        
        await interaction.response.send_message(embed=embed, view=view or MISSING)

    
    @weaponAutoComplete()
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="GOF2 Info")
    @app_commands.command(name="showme-weapon",
                            description="Look up the image for a weapon.")
    async def cmd_showme_weapon(self, interaction: Interaction, weapon: PrimaryWeaponKey):
        """Get the icon for the specified weapon
        """
        obj = bbData.builtInWeaponObjs[weapon]
        if obj.hasIcon:
            embed = Embed(title=obj.name)
            embed.set_image(url=obj.icon)
            embed.colour = Colour.random()
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(f"I don't have an image for the {obj.name}!", ephemeral=True)

    
    @moduleAutoComplete()
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="GOF2 Info")
    @app_commands.command(name="showme-module",
                            description="Look up the image for a module.")
    async def cmd_showme_module(self, interaction: Interaction, module: ModuleKey):
        """Get the icon for the specified module
        """
        obj = bbData.builtInModuleObjs[module]
        if obj.hasIcon:
            embed = Embed(title=obj.name)
            embed.set_image(url=obj.icon)
            embed.colour = Colour.random()
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(f"I don't have an image for the {obj.name}!", ephemeral=True)

    
    @turretAutoComplete()
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="GOF2 Info")
    @app_commands.command(name="showme-turret",
                            description="Look up the image for a turret.")
    async def cmd_showme_turret(self, interaction: Interaction, turret: TurretKey):
        """Get the icon for the specified turret
        """
        obj = bbData.builtInTurretObjs[turret]
        if obj.hasIcon:
            embed = Embed(title=obj.name)
            embed.set_image(url=obj.icon)
            embed.colour = Colour.random()
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(f"I don't have an image for the {obj.name}!", ephemeral=True)

    
    @toolAutoComplete()
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="GOF2 Info")
    @app_commands.command(name="showme-tool",
                            description="Look up the image for a tool.")
    async def cmd_showme_tool(self, interaction: Interaction, tool: ToolKey):
        """Get the icon for the specified tool
        """
        obj = bbData.builtInToolObjs[tool]
        if obj.hasIcon:
            embed = Embed(title=obj.name)
            embed.set_image(url=obj.icon)
            embed.colour = Colour.random()
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(f"I don't have an image for the {obj.name}!", ephemeral=True)

#endregion showme
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="GOF2 Info")
    @app_commands.command(name="list",
                            description="List all objects in the game that match the given criteria.")
    async def cmd_list(self, interaction: Interaction, item_type: ListSearchableItemTypes, manufacturer: Optional[str] = None, tech_level: Optional[Range[int, cfg.minTechLevel, cfg.maxTechLevel]] = None):	
        """List all items in the game that match a set of criteria.
        """
        if item_type == ListSearchableItemTypes.medal:
            if tech_level is not None:
                await interaction.response.send_message(":x: Medals don't have tech levels!", ephemeral=True)
                return
            elif manufacturer is not None:
                await interaction.response.send_message(":x: Medals don't have manufacturers!", ephemeral=True)
                return
            else:
                foundObjs = bbData.medalObjs.values()

        elif item_type == ListSearchableItemTypes.skin:
            foundObjs = bbData.builtInShipSkins.values()
            if tech_level is not None:
                foundObjs = [i.skin for i in bbData.builtInCrateObjs["levelUp"][tech_level].itemPool]
            elif manufacturer is not None:
                foundObjs = [i for i in foundObjs if i.designer == manufacturer]

        else:
            foundObjs = []

            if tech_level is not None and item_type not in self.LIST_TL_OBJS:
                await interaction.response.send_message(f":x: {item_type.value.title()}s don't have tech levels!", ephemeral=True)
                return

            if item_type in self.LIST_FACTION_OBJS:
                if item_type in self.LIST_DICT_OBJS:
                    for item in self.LIST_FACTION_OBJS[item_type].values():
                        if (manufacturer is None or (manufacturer is not None and item["faction"] == manufacturer)) and \
                                (item_type not in self.LIST_TL_OBJS or (item_type in self.LIST_TL_OBJS and \
                                    (tech_level is None or (tech_level is not None and item["techLevel"])) == tech_level)):
                            foundObjs.append(item)
                else:
                    for item in self.LIST_FACTION_OBJS[item_type].values():
                        if (manufacturer is None or (manufacturer is not None and item.faction == manufacturer)) and \
                                (item_type not in self.LIST_TL_OBJS or (item_type in self.LIST_TL_OBJS and \
                                    (tech_level is None or (tech_level is not None and item.techLevel == tech_level)))):
                            foundObjs.append(item)

            elif item_type in self.LIST_MANUFACTURER_OBJS:
                if item_type in self.LIST_DICT_OBJS:    
                    for item in self.LIST_MANUFACTURER_OBJS[item_type].values():
                        if (manufacturer is None or (manufacturer is not None and item["manufacturer"] == manufacturer)) and \
                                (item_type not in self.LIST_TL_OBJS or (item_type in self.LIST_TL_OBJS and \
                                    (tech_level is None or (tech_level is not None and item["techLevel"] == tech_level)))):
                            foundObjs.append(item)
                else:
                    for item in self.LIST_MANUFACTURER_OBJS[item_type].values():
                        if (manufacturer is None or (manufacturer is not None and item.manufacturer == manufacturer)) and \
                                (item_type not in self.LIST_TL_OBJS or (item_type in self.LIST_TL_OBJS and \
                                    (tech_level is None or (tech_level is not None and item.techLevel == tech_level)))):
                            foundObjs.append(item)

        if not foundObjs:
            await interaction.response.send_message("No results found!")
        else:
            itemsPerPage = 10
            # if len(foundObjs) < itemsPerPage:
            if True:
                resultsStr = ""
                for item in foundObjs:
                    if item_type in self.LIST_DICT_OBJS:
                        item = cast(SerializedLoadedObject, item)
                        resultsStr += (item.get("emoji", "•")) \
                                        + " " + item["name"] + "\n"
                    else:
                        try:
                            # TODO: I don't yet have a 'HasEmoji' base class or similar, so I'm just going to catch AttributeErrors here
                            resultsStr += (item.emoji.sendable if item.hasEmoji else "•") + " " + item.name + "\n" # type: ignore[reportGeneralTypeIssues]
                        except AttributeError:
                            resultsStr += "• " + item.name + "\n"
                resultsEmbed = lib.discordUtil.makeEmbed(authorName="Search Results",
                                                            titleTxt=((("level " + str(tech_level) + " ") if tech_level is not None \
                                                                    else "") \
                                                                + ((manufacturer + " ") if manufacturer else "") \
                                                                + item_type.value + "s").capitalize(),
                                                            desc=resultsStr,
                                                            icon=self.bot.user.avatar.with_size(64).url if self.bot.user is not None and self.bot.user.avatar is not None else "")
                await interaction.response.send_message(embed=resultsEmbed)

            # TODO: Put results of size more than itemsPerPage on a pagedreactionmenu

            # await interaction.response.send_message("No results found!" if not foundObjs \
            #     else ("** **- " + "\n - ".join((item["name"] if item_type in dictObjs else item.name) for item in foundObjs)))
            # resultsMenu = PagedReactionMenu.PagedReactionMenu()
            # resultsEmbed = lib.discordUtil.makeEmbed()

#endregion commands


async def setup(bot: client.BasedClient):
    await bot.add_cog(UserGof2InfoCog(bot))
