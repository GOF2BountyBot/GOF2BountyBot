import os
from typing import Optional, Set, cast
from enum import Enum

from discord import Colour, Embed, app_commands, Interaction
from discord.utils import MISSING
from discord.app_commands import Range

from .. import client, lib
from ..lib.discordUtil import ImageFile
from ..cfg import bbData, cfg
from ..cfg.cfg import basicAccessLevels
from ..interactions import basedCommand
from ..interactions.basedApp import BasedCog
from .util.CommonAutocomplete import criminalAutoComplete, criminalVerify, \
                                    shipAutoComplete, shipVerify, \
                                    shipSkinAutoComplete, shipSkinVerify, \
                                    systemAutoComplete, systemVerify, \
                                    weaponAutoComplete, weaponVerify, \
                                    moduleAutoComplete, moduleVerify, \
                                    turretAutoComplete, turretVerify, \
                                    toolAutoComplete, toolVerify, \
                                    medalAutoComplete, medalVerify
from ..gameObjects.bounties.bountyBoards import bountyBoardChannel
from ..gameObjects.items.ships.shipBlueprint import ShipBlueprint
from ..baseClasses.embedFillable import EmbedFillableMixin
from ..gameObjects.gameObject import SerializedLoadedObject

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
    @systemVerify("start")
    @systemVerify("end")
    async def cmd_make_route(self, interaction: Interaction, start: str, end: str):
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
    @systemVerify()
    async def cmd_info_system(self, interaction: Interaction, system: str):
        """return statistics about a specified system
        """
        await self.objectInfo(interaction, bbData.builtInSystemObjs[system], "System")

    
    @criminalAutoComplete()
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="GOF2 Info")
    @app_commands.command(name="info-criminal",
                            description="Look up information about a criminal.")
    @criminalVerify()
    async def cmd_info_criminal(self, interaction: Interaction, name: str):
        """return statistics about a specified criminal
        """
        await self.objectInfo(interaction, bbData.builtInCriminalObjs[name], "Criminal")

    
    @shipAutoComplete()
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="GOF2 Info")
    @app_commands.command(name="info-ship",
                            description="Look up information about a ship.")
    @shipVerify()
    async def cmd_info_ship(self, interaction: Interaction, ship: str):
        """return statistics about a specified ship
        """
        await self.objectInfo(interaction, ShipBlueprint.deserialize(bbData.builtInShipData[ship]), "Ship")

    
    @weaponAutoComplete()
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="GOF2 Info")
    @app_commands.command(name="info-weapon",
                            description="Look up information about a weapon.")
    @weaponVerify()
    async def cmd_info_weapon(self, interaction: Interaction, weapon: str):
        """return statistics about a specified weapon
        """
        await self.objectInfo(interaction, bbData.builtInWeaponObjs[weapon], "Weapon")

    
    @moduleAutoComplete()
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="GOF2 Info")
    @app_commands.command(name="info-module",
                            description="Look up information about a module.")
    @moduleVerify()
    async def cmd_info_module(self, interaction: Interaction, module: str):
        """return statistics about a specified module
        """
        await self.objectInfo(interaction, bbData.builtInModuleObjs[module], "Module")

    
    @turretAutoComplete()
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="GOF2 Info")
    @app_commands.command(name="info-turret",
                            description="Look up information about a turret.")
    @turretVerify()
    async def cmd_info_turret(self, interaction: Interaction, turret: str):
        """return statistics about a specified turret
        """
        await self.objectInfo(interaction, bbData.builtInTurretObjs[turret], "Turret")

    
    @shipSkinAutoComplete()
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="GOF2 Info")
    @app_commands.command(name="info-skin",
                            description="Look up information about a skin.")
    @shipSkinVerify()
    async def cmd_info_skin(self, interaction: Interaction, skin: str):
        """return statistics about a specified skin
        """
        await self.objectInfo(interaction, bbData.builtInShipSkins[skin], "Skin")

    
    @medalAutoComplete()
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="GOF2 Info")
    @app_commands.command(name="info-medal",
                            description="Look up information about a medal.")
    @medalVerify()
    async def cmd_info_medal(self, interaction: Interaction, medal: str):
        """return statistics about a specified medal
        """
        await self.objectInfo(interaction, bbData.medalObjs[medal], "Medal")

    
    @toolAutoComplete()
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="GOF2 Info")
    @app_commands.command(name="info-tool",
                            description="Look up information about a tool.")
    @toolVerify()
    async def cmd_info_tool(self, interaction: Interaction, tool: str):
        """return statistics about a specified tool
        """
        await self.objectInfo(interaction, bbData.builtInToolObjs[tool], "Tool")

#endregion info
#region showme
    
    @criminalAutoComplete()
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="GOF2 Info")
    @app_commands.command(name="showme-criminal",
                            description="Look up the image for a criminal.")
    @criminalVerify()
    async def cmd_showme_criminal(self, interaction: Interaction, name: str):
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
    @shipVerify()
    @shipSkinVerify()
    async def cmd_showme_ship(self, interaction: Interaction, ship: str, skin: Optional[str] = None):
        """Get the icon for the specified ship
        """
        shipData = bbData.builtInShipData[ship]
        if skin is not None:
            if not shipData["skinnable"]:
                await interaction.response.send_message(":x: That ship is not skinnable!", ephemeral=True)
                return

            if skin not in shipData.get("compatibleSkins", []):
                await interaction.response.send_message(f":x: That skin is not compatible with the **{ship}**!", ephemeral=True)
                return

            itemEmbed = lib.discordUtil.makeEmbed(col=Colour.random(),
                                                    img=bbData.builtInShipSkins[skin].shipRenders[ship][0],
                                                    titleTxt=ship,
                                                    footerTxt="Custom skin: " + skin.capitalize())
            await interaction.response.send_message(embed=itemEmbed)
        else:
            obj = ShipBlueprint.deserialize(shipData)
            if obj.hasIcon:
                embed = Embed(title=obj.name)
                embed.set_image(url=obj.icon)
                embed.colour = Colour.random()
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.response.send_message(f"I don't have an image for the {obj.name}!", ephemeral=True)

    
    @weaponAutoComplete()
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="GOF2 Info")
    @app_commands.command(name="showme-weapon",
                            description="Look up the image for a weapon.")
    @weaponVerify()
    async def cmd_showme_weapon(self, interaction: Interaction, weapon: str):
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
    @moduleVerify()
    async def cmd_showme_module(self, interaction: Interaction, module: str):
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
    @turretVerify()
    async def cmd_showme_turret(self, interaction: Interaction, turret: str):
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
    @toolVerify()
    async def cmd_showme_tool(self, interaction: Interaction, tool: str):
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
