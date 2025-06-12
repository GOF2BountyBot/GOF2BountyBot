from typing import List, Optional, Union, cast
from discord import Guild, Member, User, app_commands, Interaction
from discord.app_commands import Range
from discord.ui import View, Button

from bot import client, lib
from bot.lib.discordUtil import makeEmbed, ZWSP
from bot.cfg import cfg, bbData
from bot.cfg.cfg import basicAccessLevels
from bot.cfg.bbData import ItemCategory, ItemCategoryOrAll
from bot.interactions import basedCommand
from bot.interactions.basedApp import BasedCog
from bot.interactions.basedComponent import StaticComponents
from bot.users import basedUser
from bot.gameObjects.inventories.inventoryListing import SerializedInventoryListing
from bot.gameObjects.items.gameItem import TypedSerializedGameItemUnion, spawnItem, GameItem
from bot.gameObjects.inventories.inventory import Inventory
from bot.gameObjects.items.ships.shipItem import Ship
from bot.gameObjects.items.weapons.primaryWeapon import PrimaryWeapon
from bot.gameObjects.items.weapons.turretWeapon import TurretWeapon
from bot.gameObjects.items.modules.moduleItem import ModuleItem
from .util.CommonAutocomplete import CriminalKey, AnyUserHangarItem, anyEquippableUserHangerItemAutoComplete, IntList, anyShipEquippedItemAutoComplete, AnyShipEquippedItemOrAll, AutocompleteResult
from .util.transformers import BoolYesNo
from bot.interactions.commandChecks import guildOnly
from bot.databases.bountyDB import BountyDB


class UserLoadoutCog(BasedCog):
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="loadout")
    @app_commands.describe(
        item_type="The type of items to show. Defaults to all items.",
        page="The page number to show. Defaults to 1."
    )
    @app_commands.command(name="hangar",
                            description="Show the items stored in your hangar. Give an item type to only list items of that type.")
    async def cmd_hangar(self, interaction: Interaction, item_type: ItemCategoryOrAll = ItemCategoryOrAll.all, page: Range[int, 1] = 1):
        """return a page listing the calling user's items.
        """
        if item_type == ItemCategoryOrAll.all:
            maxPerPage = cfg.maxItemsPerHangarPageAll
        else:
            maxPerPage = cfg.maxItemsPerHangarPageIndividual

        firstPlace = maxPerPage * (page - 1) + 1
        pageError = ""

        if page < 1:
            pageError = ":x: Invalid page number. Showing page one:"
            page = 1
            firstPlace = 1
            
        if not self.bot.usersDB.idExists(interaction.user.id):
            if page > 1:
                pageError = ":x: You only have one page of items. Showing page one:"
                page = 1
                firstPlace = 1

            hangarEmbed = makeEmbed(titleTxt="Hangar", desc=interaction.user.mention,
                                    col=bbData.factionColours["neutral"],
                                    footerTxt=("All items" if item_type == ItemCategoryOrAll.all else f"{item_type.value.title()}s") \
                                            + " - page " + str(page),
                                    thumb=interaction.user.display_avatar.with_size(64).url)

            for itemType in ItemCategory:
                itemInactivesDict = basedUser.defaultUserDict.get(basedUser.itemCategoryUserKeys[itemType], False)
                if not itemInactivesDict:
                    continue
                
                itemInactivesDict = cast(List[SerializedInventoryListing[TypedSerializedGameItemUnion]], itemInactivesDict)

                itemInactives = Inventory(basedUser.itemCategoryStoredTypes[itemType])
                for itemDict in itemInactivesDict:
                    itemInactives.addItem(spawnItem(itemDict["item"]), itemDict.get("count", 1))
                
                numPages = int(itemInactives.numKeys / maxPerPage) + (0 if itemInactives.numKeys % maxPerPage == 0 else 1)
                lastItemNumber = (firstPlace + maxPerPage) if page < numPages else itemInactives.numKeys

                for itemNum in range(firstPlace, lastItemNumber + 1):
                    if itemNum == firstPlace:
                        hangarEmbed.add_field(name=ZWSP, value=f"__**Stored {itemType.value.title()}s**__", inline=False)

                    currentItem = cast(GameItem, itemInactives[itemNum - 1].item)
                    currentItemCount = itemInactives[itemNum- 1].count
                    hangarEmbed.add_field(name=str(itemNum) + ". " \
                                                + (currentItem.emoji.sendable + " " if currentItem.hasEmoji else "") \
                                                + ((" `(" + str(currentItemCount) + ")` ") if currentItemCount > 1 else "") \
                                                + currentItem.name,
                                            value=currentItem.statsStringShort(), inline=False)

            if not hangarEmbed.fields:
                hangarEmbed.add_field(name="No Stored Items", value=ZWSP, inline=False)
            await interaction.response.send_message(pageError, embed=hangarEmbed)
            return

        else:
            requestedBBUser = self.bot.usersDB.getUser(interaction.user.id)

            maxPage = requestedBBUser.numInventoryPages(item_type, maxPerPage)
            if maxPage == 0:
                await interaction.response.send_message(":x: You don't have any " \
                                                        + ("items!" if item_type == ItemCategoryOrAll.all else "of that item!"))
                return
            elif page > maxPage:
                pageError = ":x: You only have one page of items. Showing page one:"
                page = maxPage

            firstPlace = maxPerPage * (page - 1) + 1

            itemName = "All item" if item_type is ItemCategoryOrAll.all else item_type.value.rstrip("s").title()
            hangarEmbed = makeEmbed(titleTxt="Hangar", desc=interaction.user.mention,
                                    col=bbData.factionColours["neutral"],
                                    footerTxt=f"{itemName}s - page {page}/{maxPage}",
                                    thumb=interaction.user.display_avatar.with_size(64).url)

            if item_type in [ItemCategoryOrAll.all, ItemCategoryOrAll.ship]:
                for shipNum in range(firstPlace, requestedBBUser.lastItemNumberOnPage(ItemCategory.ship, page, maxPerPage) + 1):
                    if shipNum == firstPlace:
                        hangarEmbed.add_field(name=ZWSP, value="__**Stored Ships**__", inline=False)

                    currentItem = requestedBBUser.inactiveShips.itemAtIndex(shipNum - 1)
                    currentItemCount = requestedBBUser.inactiveShips.items[currentItem].count

                    itemEmoji = f"{currentItem.emoji.sendable} " if currentItem.hasEmoji else ""
                    amountStr = (f" `({currentItemCount})` ") if currentItemCount > 1 else ""

                    hangarEmbed.add_field(name=f"{shipNum}. {itemEmoji}{amountStr}{currentItem.getNameAndNick()}",
                                            value=currentItem.statsStringShort(),
                                            inline=False)

            if item_type in [ItemCategoryOrAll.all, ItemCategoryOrAll.weapon]:
                for weaponNum in range(firstPlace, requestedBBUser.lastItemNumberOnPage(ItemCategory.weapon, page, maxPerPage) + 1):
                    if weaponNum == firstPlace:
                        hangarEmbed.add_field(name=ZWSP, value="__**Stored Weapons**__", inline=False)

                    currentItem = requestedBBUser.inactiveWeapons.itemAtIndex(weaponNum - 1)
                    currentItemCount = requestedBBUser.inactiveWeapons.items[currentItem].count

                    itemEmoji = f"{currentItem.emoji.sendable} " if currentItem.hasEmoji else ""
                    amountStr = (f" `({currentItemCount})` ") if currentItemCount > 1 else ""

                    hangarEmbed.add_field(name=f"{weaponNum}. {itemEmoji}{amountStr}{currentItem.name}",
                                            value=currentItem.statsStringShort(),
                                            inline=False)

            if item_type in [ItemCategoryOrAll.all, ItemCategoryOrAll.module]:
                for moduleNum in range(firstPlace, requestedBBUser.lastItemNumberOnPage(ItemCategory.module, page, maxPerPage) + 1):
                    if moduleNum == firstPlace:
                        hangarEmbed.add_field(name=ZWSP, value="__**Stored Modules**__", inline=False)

                    currentItem = requestedBBUser.inactiveModules.itemAtIndex(moduleNum - 1)
                    currentItemCount = requestedBBUser.inactiveModules.items[currentItem].count

                    itemEmoji = f"{currentItem.emoji.sendable} " if currentItem.hasEmoji else ""
                    amountStr = (f" `({currentItemCount})` ") if currentItemCount > 1 else ""

                    hangarEmbed.add_field(name=f"{moduleNum}. {itemEmoji}{amountStr}{currentItem.name}",
                                            value=currentItem.statsStringShort(),
                                            inline=False)

            if item_type in [ItemCategoryOrAll.all, ItemCategoryOrAll.turret]:
                for turretNum in range(firstPlace, requestedBBUser.lastItemNumberOnPage(ItemCategory.turret, page, maxPerPage) + 1):
                    if turretNum == firstPlace:
                        hangarEmbed.add_field(name=ZWSP, value="__**Stored Turrets**__", inline=False)

                    currentItem = requestedBBUser.inactiveTurrets.itemAtIndex(turretNum - 1)
                    currentItemCount = requestedBBUser.inactiveTurrets.items[currentItem].count

                    itemEmoji = f"{currentItem.emoji.sendable} " if currentItem.hasEmoji else ""
                    amountStr = (f" `({currentItemCount})` ") if currentItemCount > 1 else ""

                    hangarEmbed.add_field(name=f"{turretNum}. {itemEmoji}{amountStr}{currentItem.name}",
                                            value=currentItem.statsStringShort(),
                                            inline=False)

            if item_type in [ItemCategoryOrAll.all, ItemCategoryOrAll.tool]:
                for toolNum in range(firstPlace, requestedBBUser.lastItemNumberOnPage(ItemCategory.tool, page, maxPerPage) + 1):
                    if toolNum == firstPlace:
                        hangarEmbed.add_field(name=ZWSP, value="__**Stored Tools**__", inline=False)

                    currentItem = requestedBBUser.inactiveTools.itemAtIndex(toolNum - 1)
                    currentItemCount = requestedBBUser.inactiveTools.items[currentItem].count

                    itemEmoji = f"{currentItem.emoji.sendable} " if currentItem.hasEmoji else ""
                    amountStr = (f" `({currentItemCount})` ") if currentItemCount > 1 else ""

                    hangarEmbed.add_field(name=f"{toolNum}. {itemEmoji}{amountStr}{currentItem.name}",
                                            value=currentItem.statsStringShort(),
                                            inline=False)

            await interaction.response.send_message(pageError, embed=hangarEmbed, ephemeral=True)

    
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="loadout")
    @app_commands.describe(
        user="The user whose loadout to show. Defaults to you.",
        user_id="The ID of the user whose loadout to show. Useful if they are in another server. Defaults to you."
    )
    @app_commands.command(name="loadout",
                            description="Display your current ship and the items equipped onto it, or those equipped by someone else.")
    async def cmd_loadout(self, interaction: Interaction, user: Optional[Union[User, Member]] = None, user_id: Optional[str] = None):
        """list the requested user or criminal's currently equipped items.
        """
        if not (user := await self.UsersUtilCog.targetUserOrAuthor(interaction, user, user_id)): return

        view = View()
        swapImagesButton = Button(emoji="🔎")
        swapImagesButton = StaticComponents.Swap_Embed_Image_And_Thumbnail(swapImagesButton)
        view.add_item(swapImagesButton)

        if not self.bot.usersDB.idExists(user.id):
            activeShip = Ship.deserialize(basedUser.defaultShipLoadoutDict)
            loadoutEmbed = lib.discordUtil.makeEmbed(titleTxt="Loadout", desc=user.mention,
                                                        col=bbData.factionColours[activeShip.manufacturer] \
                                                            if activeShip.manufacturer in bbData.factionColours \
                                                            else bbData.factionColours["neutral"],
                                                        thumb=activeShip.icon if activeShip.hasIcon \
                                                            else user.display_avatar.with_size(64).url)

            await interaction.response.send_message(embed=activeShip.fillLoadoutEmbed(loadoutEmbed), view=view)
            return

        requestedBBUser = self.bot.usersDB.getUser(user.id)
        activeShip = requestedBBUser.activeShip
        loadoutEmbed = lib.discordUtil.makeEmbed(titleTxt="Loadout", desc=user.mention,
                                                    col=bbData.factionColours[activeShip.manufacturer] if \
                                                        activeShip.manufacturer in bbData.factionColours else \
                                                        bbData.factionColours["neutral"],
                                                    thumb=activeShip.icon if activeShip.hasIcon else \
                                                        user.display_avatar.with_size(64).url)

        if activeShip is None:
            loadoutEmbed.add_field(name="Active Ship:", value="None", inline=False)
        else:
            loadoutEmbed = activeShip.fillLoadoutEmbed(loadoutEmbed)

        await interaction.response.send_message(embed=loadoutEmbed, view=view)


    @guildOnly(bountiesEnabled=True)
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="loadout")
    @app_commands.describe(
        criminal="The criminal whose loadout to show. They must be wanted in this server."
    )
    @app_commands.command(
        name="criminal-loadout",
        description="Display the current loadout of a wanted criminal."
    )
    async def cmd_criminal_loadout(self, interaction: Interaction, criminal: CriminalKey):
        """list the requested criminal's currently equipped items.
        """
        # Assume that the command is being called from within a guild with bounties enabled, because this command is decorated with @guildOnly(bountiesEnabled=True)
        callingBBGuild = self.bot.guildsDB.getGuild(cast(Guild, interaction.guild).id)
        bountiesDB = cast(BountyDB, callingBBGuild.bountiesDB)

        criminalObj = bbData.builtInCriminalObjs[criminal]
        # report unrecognised criminal names
        if not bountiesDB.criminalObjExists(criminalObj, noEscapedCrim=False):
            errmsg = ":x: That pilot is not currently wanted!"

            if lib.stringTyping.isMention(criminal):
                errmsg += "\n:warning: **Don't tag users**, use their name and discriminator like so: `/loadout criminal Trimatix#2244`"

            await interaction.response.send_message(errmsg)
            return

        try:
            bountyObj = bountiesDB.getBountyByCrim(criminalObj)
        except KeyError:
            bountyObj = bountiesDB.getEscapedBountyByCrim(criminalObj)

        # Casting to Ship here because the bounty is active, so they must have an equipped ship
        activeShip = cast(Ship, bountyObj.activeShip)
        loadoutEmbed = lib.discordUtil.makeEmbed(titleTxt="Loadout",
                                                    desc=criminalObj.name.title() + "\n`Difficulty: " \
                                                        + str(bountyObj.techLevel) + "`",
                                                    col=bbData.factionColours[criminalObj.faction] \
                                                        if criminalObj.faction in bbData.factionColours \
                                                        else bbData.factionColours["neutral"],
                                                    thumb=criminalObj.icon)
        loadoutEmbed = activeShip.fillLoadoutEmbed(loadoutEmbed, shipEmoji=True)

        await interaction.response.send_message(embed=loadoutEmbed)
        return


    @anyEquippableUserHangerItemAutoComplete()
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="loadout",
                                formattedDesc="Equip an item from your hangar onto your loadout. " \
                                            + "When equipping a ship, give `move_equipped_items` as `Yes` to move all items " \
                                            + "to the new ship.")
    @app_commands.describe(
        item="The item to equip",
        move_equipped_items="When equipping a ship, move your currently equipped items to the new one. Default: No",
    )
    @app_commands.command(
        name="equip",
        description="Equip an item from your hangar into your loadout."
    )
    async def cmd_equip(self, interaction: Interaction, item: AnyUserHangarItem, move_equipped_items: BoolYesNo = BoolYesNo.No):
        """Equip the item of the given item type, at the given index, from the user's inactive items.
        if "transfer" is specified, the new ship's items are cleared, and the old ship's items attempt to fill new ship.
        "transfer" is only valid when equipping a ship.
        """
        moveEquippedItems = bool(move_equipped_items)
        itemType, itemNum = item

        if self.bot.usersDB.idExists(interaction.user.id):
            requestedBBUser = self.bot.usersDB.getUser(interaction.user.id)
            result = await self.UsersUtilCog.getUserItemByIndex(interaction, requestedBBUser, itemType, itemNum)
            if result is None: return
            _, requestedItem = result
            activeShip = requestedBBUser.activeShip
        else:
            requestedBBUser = None
            requestedItem = await self.UsersUtilCog.getDefaultUserItemByIndex(interaction, True, itemType, itemNum)
            if requestedItem is None: return
            activeShip = Ship.deserialize(basedUser.defaultShipLoadoutDict)

        if isinstance(requestedItem, Ship):
            if requestedBBUser is None: requestedBBUser = self.bot.usersDB.addID(interaction.user.id)

            if moveEquippedItems:
                requestedBBUser.unequipAll(requestedItem)
                leftoverItems = requestedBBUser.activeShip.transferItemsTo(requestedItem)
                requestedBBUser.unequipAll(activeShip)
            else:
                leftoverItems = 0

            requestedBBUser.equipShipObj(requestedItem)

            outStr = f":rocket: You switched to the **{requestedItem.getNameOrNick()}**."
            if moveEquippedItems:
                outStr += f"\n{leftoverItems} items that could not fit in your new ship can be found in the hangar."
            await interaction.response.send_message(outStr)

        elif isinstance(requestedItem, PrimaryWeapon):
            if not activeShip.canEquipMoreWeapons():
                await interaction.response.send_message(":x: Your active ship does not have any free weapon slots!", ephemeral=True)
                return

            if requestedBBUser is None: requestedBBUser = self.bot.usersDB.addID(interaction.user.id)

            requestedBBUser.activeShip.equipWeapon(requestedItem)
            requestedBBUser.inactiveWeapons.removeItem(requestedItem)

            await interaction.response.send_message(":wrench: You equipped the **" + requestedItem.name + "**.")

        elif isinstance(requestedItem, ModuleItem):
            if not activeShip.canEquipMoreModules():
                await interaction.response.send_message(":x: Your active ship does not have any free module slots!", ephemeral=True)
                return

            if not activeShip.canEquipModuleType(type(requestedItem)):
                await interaction.response.send_message(":x: You already have the max of this type of module equipped!", ephemeral=True)
                return

            if requestedBBUser is None: requestedBBUser = self.bot.usersDB.addID(interaction.user.id)

            requestedBBUser.activeShip.equipModule(requestedItem)
            requestedBBUser.inactiveModules.removeItem(requestedItem)

            await interaction.response.send_message(":wrench: You equipped the **" + requestedItem.name + "**.")

        elif isinstance(requestedItem, TurretWeapon):
            if not activeShip.canEquipMoreTurrets():
                await interaction.response.send_message(":x: Your active ship does not have any free turret slots!", ephemeral=True)
                return

            if requestedBBUser is None: requestedBBUser = self.bot.usersDB.addID(interaction.user.id)

            requestedBBUser.activeShip.equipTurret(requestedItem)
            requestedBBUser.inactiveTurrets.removeItem(requestedItem)

            await interaction.response.send_message(":wrench: You equipped the **" + requestedItem.name + "**.")

        else:
            raise NotImplementedError(f"Unexpected item type for category {itemType.value}: {type(requestedItem)}")


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="loadout",
                                formattedDesc="Equip multiple items from your hangar onto your active ship. Item numbers are shown next " \
                                            + "to items in your `/hangar`.")
    @app_commands.describe(
        item_numbers="A comma-separated list of the item numbers to equip, from /hangar"
    )
    @app_commands.choices(
        item_type=[
            app_commands.Choice(name=i.name, value=i.value)
            for i in bbData.shipEquippableItemCategories
        ]
    )
    @app_commands.command(
        name="multi-equip",
        description="Equip multiple items from your hangar into your loadout."
    )
    async def cmd_multi_equip(self, interaction: Interaction, item_type: str, item_numbers: IntList):
        """Equip the item of the given item type, at the given index, from the user's inactive items.
        if "transfer" is specified, the new ship's items are cleared, and the old ship's items attempt to fill new ship.
        "transfer" is only valid when equipping a ship.
        """
        # TODO: Casting here as a quick fix because dpy doesn't accept enum literals as param hints
        itemType = cast(bbData.ShipEquippableItemCategoryType, bbData.ItemCategory(item_type))
        requestedBBUser = self.bot.usersDB.getOrAddID(interaction.user.id)
        userItemInactives = requestedBBUser.getInventory(itemType)

        for itemNum in item_numbers:
            if itemNum > userItemInactives.numKeys:
                await interaction.response.send_message(f":x: Invalid item number! You have {userItemInactives.numKeys} {itemType.value}s.", ephemeral=True)
                return
            if itemNum < 1:
                await interaction.response.send_message(":x: Invalid item number! Must be at least 1.", ephemeral=True)
                return
        
        items = [userItemInactives.itemAtIndex(itemNum - 1) for itemNum in item_numbers]
        equipped: List[GameItem] = []
        leftover: List[GameItem] = []

        #Equip the items one by one
        for requestedItem in items:
            if not userItemInactives.stores(requestedItem): continue
            if isinstance(requestedItem, PrimaryWeapon):
                if not requestedBBUser.activeShip.canEquipMoreWeapons():
                    leftover.append(requestedItem)
                else:
                    equipped.append(requestedItem)
                    requestedBBUser.activeShip.equipWeapon(requestedItem)
                    # Ignoring here because I can't convince pyright that the types will match
                    userItemInactives.removeItem(requestedItem) # type: ignore[reportGeneralTypeIssues]
                
            elif isinstance(requestedItem, ModuleItem):
                if not requestedBBUser.activeShip.canEquipMoreModules() or not requestedBBUser.activeShip.canEquipModuleType(type(requestedItem)):
                    leftover.append(requestedItem)
                else:
                    equipped.append(requestedItem)
                    requestedBBUser.activeShip.equipModule(requestedItem)
                    # Ignoring here because I can't convince pyright that the types will match
                    userItemInactives.removeItem(requestedItem) # type: ignore[reportGeneralTypeIssues]

            elif isinstance(requestedItem, TurretWeapon):
                if not requestedBBUser.activeShip.canEquipMoreTurrets():
                    leftover.append(requestedItem)
                else:
                    equipped.append(requestedItem)
                    requestedBBUser.activeShip.equipTurret(requestedItem)
                    # Ignoring here because I can't convince pyright that the types will match
                    userItemInactives.removeItem(requestedItem) # type: ignore[reportGeneralTypeIssues]
            
            else:
                raise NotImplementedError(f"Unexpected item type for category {itemType.value}: {type(requestedItem)}")
        
        if len(equipped) == 1:
            equippedStr = f":wrench: You equipped the **{equipped[0].name}**."
        elif equipped:
            equippedStr = ":wrench: You equipped the following items:\n" \
                        + "\n".join(f"• {i.name}" for i in equipped)
        else:
            equippedStr = ""

        if len(leftover) == 1:
            leftoverStr = f":x: The {leftover[0].name} could not be equipped, because your active ship does not have any free {itemType.value} slots!"
        elif leftover:
            leftoverStr = ":x: The following items could not be equipped, because there are not enough free slots on your ship:\n" \
                        + "\n".join(f"• {i.name}" for i in leftover)
        else:
            leftoverStr = ""
        
        await interaction.response.send_message("\n".join((equippedStr, leftoverStr)))


    @anyShipEquippedItemAutoComplete(allowAll=True)
    @app_commands.describe(
        item="The item to unequip"
    )
    @app_commands.command(
        name="unequip",
        description="Unequip one or all of the items from your active ship, to your hangar."
    )
    async def cmd_unequip(self, interaction: Interaction, item: AnyShipEquippedItemOrAll):
        """Unequip the item of the given item type, at the given index, from the user's active ship.
        """
        if isinstance(item, AutocompleteResult):
            if item != AutocompleteResult.AllSelected:
                raise NotImplementedError(f"Unsupported AutocompleteResult: {item}")
            
            requestedBBUser = self.bot.usersDB.getOrAddID(interaction.user.id)
            requestedBBUser.unequipAll(requestedBBUser.activeShip)

            await interaction.response.send_message(":wrench: You unequipped **all items** from your ship.")
            return
        
        requestedBBUser = self.bot.usersDB.getOrAddID(interaction.user.id)

        itemType, itemNum = item

        if itemType is ItemCategory.weapon:
            requestedItem = requestedBBUser.activeShip.weapons[itemNum - 1]
            requestedBBUser.inactiveWeapons.addItem(requestedItem)
            requestedBBUser.activeShip.unequipWeaponIndex(itemNum - 1)

            await interaction.response.send_message(":wrench: You unequipped the **" + requestedItem.name + "**.")

        elif itemType is ItemCategory.module:
            requestedItem = requestedBBUser.activeShip.modules[itemNum - 1]
            requestedBBUser.inactiveModules.addItem(requestedItem)
            requestedBBUser.activeShip.unequipModuleIndex(itemNum - 1)

            await interaction.response.send_message(":wrench: You unequipped the **" + requestedItem.name + "**.")

        elif itemType is ItemCategory.turret:
            requestedItem = requestedBBUser.activeShip.turrets[itemNum - 1]
            requestedBBUser.inactiveTurrets.addItem(requestedItem)
            requestedBBUser.activeShip.unequipTurretIndex(itemNum - 1)

            await interaction.response.send_message(":wrench: You unequipped the **" + requestedItem.name + "**.")

        else:
            raise NotImplementedError("Valid but unsupported item name: " + itemType.value)


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="loadout",
                                formattedDesc="Unequip multiple items from your active ship into your hangar. Item numbers are shown next " \
                                            + "to items in your `/loadout`.")
    @app_commands.describe(
        item_numbers="A comma-separated list of the item numbers to unequip, from /loadout"
    )
    
    @app_commands.choices(
        item_type=[
            app_commands.Choice(name=i.name, value=i.value)
            for i in bbData.shipEquippableItemCategories
        ]
    )
    @app_commands.command(
        name="multi-unequip",
        description="Unequip multiple items from your loadout into your hangar."
    )
    async def cmd_multi_unequip(self, interaction: Interaction, item_type: str, item_numbers: IntList):
        """Unequip the items of the given item type, at the given indexes, from the user's active ship.
        """
        # TODO: Casting here as a quick fix because dpy doesn't accept enum literals as param hints
        itemType = cast(bbData.ShipEquippableItemCategoryType, bbData.ItemCategory(item_type))
        requestedBBUser = self.bot.usersDB.getOrAddID(interaction.user.id)
        shipActives = requestedBBUser.activeShip.getActives(itemType)
        userInactives = requestedBBUser.getInventory(itemType)

        for itemNum in item_numbers:
            if itemNum > len(shipActives):
                await interaction.response.send_message(f":x: Invalid item number! You have {len(shipActives)} {itemType.value}s equipped.", ephemeral=True)
                return
            if itemNum < 1:
                await interaction.response.send_message(":x: Invalid item number! Must be at least 1.", ephemeral=True)
                return
        
        # Remove duplicates
        item_numbers = sorted(list(set(item_numbers)), reverse=True)
        unequipped = []
        
        for itemNum in item_numbers:
            item = shipActives.pop(itemNum - 1)
            unequipped.append(item)
            # TODO
            userInactives.addItem(item) # type: ignore[reportGeneralTypeIssues]
        
        if len(unequipped) == 1:
            unequippedStr = f":wrench: You unequipped the **{unequipped[0].name}**."
        elif unequipped:
            unequippedStr = ":wrench: You unequipped the following items:\n" \
                        + "\n".join(f"• {i.name}" for i in unequipped)
        else:
            raise RuntimeError("No items unequipped")
        
        await interaction.response.send_message(unequippedStr)


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="loadout")
    @app_commands.describe(
        nickname=f"A custom nickname for this ship. Must be {cfg.maxShipNickLength} characters or less."
    )
    @app_commands.command(
        name="name-ship",
        description="Give your active ship a nickname!"
    )
    async def cmd_nameship(self, interaction: Interaction, nickname: Range[str, 1, cfg.maxShipNickLength]):
        """Set the nickname of the active ship.
        """
        requestedBBUser = self.bot.usersDB.getOrAddID(interaction.user.id)
        requestedBBUser.activeShip.changeNickname(nickname)
        await interaction.response.send_message(f":pencil: You named your {requestedBBUser.activeShip.name}: **{nickname}**.")
        
        
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="loadout")
    @app_commands.command(
        name="unname-ship",
        description="Reset your active ship's nickname."
    )
    async def cmd_unnameship(self, interaction: Interaction):
        """Remove the nickname of the active ship.
        """
        requestedBBUser = self.bot.usersDB.getOrAddID(interaction.user.id)

        if not requestedBBUser.activeShip.hasNickname:
            await interaction.response.send_message(":x: Your active ship does not have a nickname!")
            return

        requestedBBUser.activeShip.removeNickname()
        await interaction.response.send_message(f":pencil: You reset your **{requestedBBUser.activeShip.name}**'s nickname.")


async def setup(bot: client.BasedClient):
    await bot.add_cog(UserLoadoutCog(bot))
