from typing import List, Literal, Optional, Union, cast
from discord import Guild, Member, User, app_commands, Interaction
from discord.app_commands import Range

from .. import client, lib
from ..lib.discordUtil import makeEmbed, ZWSP
from ..cfg import cfg, bbData
from ..cfg.cfg import basicAccessLevels
from ..cfg.bbData import ItemCategory, ItemCategoryOrAll
from ..interactions import basedCommand
from ..interactions.basedApp import BasedCog
from ..users import basedUser
from ..gameObjects.inventories.inventoryListing import SerializedInventoryListing
from ..gameObjects.items.gameItem import TypedSerializedGameItemUnion, spawnItem, GameItem
from ..gameObjects.inventories.inventory import Inventory
from ..gameObjects.items.ships.shipItem import Ship
from ..gameObjects.items.weapons.primaryWeapon import PrimaryWeapon
from ..gameObjects.items.weapons.turretWeapon import TurretWeapon
from ..gameObjects.items.modules.moduleItem import ModuleItem
from .util.CommonAutocomplete import CriminalKey, AnyUserHangarItem, anyEquippableUserHangerItemAutoComplete, IntList
from .util.transformers import BoolYesNo
from ..interactions.commandChecks import guildOnly
from ..databases.bountyDB import BountyDB

EQUIPPABLE_BUT_NOT_SHIP = Literal[
    ItemCategory.weapon,
    ItemCategory.module,
    ItemCategory.turret
]


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
    async def cmd_loadout(self, interaction: Interaction, user: Optional[Union[User, Member]] = None, user_id: str = ""):
        """list the requested user or criminal's currently equipped items.
        """
        if not (user := await self.UsersUtilCog.targetUserOrAuthor(interaction, user, user_id)): return

        if not self.bot.usersDB.idExists(user.id):
            activeShip = Ship.deserialize(basedUser.defaultShipLoadoutDict)
            loadoutEmbed = lib.discordUtil.makeEmbed(titleTxt="Loadout", desc=user.mention,
                                                        col=bbData.factionColours[activeShip.manufacturer] \
                                                            if activeShip.manufacturer in bbData.factionColours \
                                                            else bbData.factionColours["neutral"],
                                                        thumb=activeShip.icon if activeShip.hasIcon \
                                                            else user.display_avatar.with_size(64).url)

            await interaction.response.send_message(embed=activeShip.fillLoadoutEmbed(loadoutEmbed))
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

        await interaction.response.send_message(embed=loadoutEmbed)


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
            await interaction.response.send_message(outStr, ephemeral=True)

        elif isinstance(requestedItem, PrimaryWeapon):
            if not activeShip.canEquipMoreWeapons():
                await interaction.response.send_message(":x: Your active ship does not have any free weapon slots!", ephemeral=True)
                return

            if requestedBBUser is None: requestedBBUser = self.bot.usersDB.addID(interaction.user.id)

            requestedBBUser.activeShip.equipWeapon(requestedItem)
            requestedBBUser.inactiveWeapons.removeItem(requestedItem)

            await interaction.response.send_message(":wrench: You equipped the **" + requestedItem.name + "**.", ephemeral=True)

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

            await interaction.response.send_message(":wrench: You equipped the **" + requestedItem.name + "**.", ephemeral=True)

        elif isinstance(requestedItem, TurretWeapon):
            if not activeShip.canEquipMoreTurrets():
                await interaction.response.send_message(":x: Your active ship does not have any free turret slots!", ephemeral=True)
                return

            if requestedBBUser is None: requestedBBUser = self.bot.usersDB.addID(interaction.user.id)

            requestedBBUser.activeShip.equipTurret(requestedItem)
            requestedBBUser.inactiveTurrets.removeItem(requestedItem)

            await interaction.response.send_message(":wrench: You equipped the **" + requestedItem.name + "**.", ephemeral=True)

        else:
            raise NotImplementedError(f"Unexpected item type for category {itemType.value}: {type(requestedItem)}")


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="loadout",
                                formattedDesc="Equip multiple items from your hangar onto your active ship. Item numbers are shown next " \
                                            + "to items in your `/hangar`.")
    @app_commands.describe(
        item_numbers="A comma-separated list of the item numbers to equip, from /hangar"
    )
    @app_commands.command(
        name="multi-equip",
        description="Equip multiple items from your hangar into your loadout."
    )
    async def cmd_multi_equip(self, interaction: Interaction, item_type: EQUIPPABLE_BUT_NOT_SHIP, item_numbers: IntList):
        """Equip the item of the given item type, at the given index, from the user's inactive items.
        if "transfer" is specified, the new ship's items are cleared, and the old ship's items attempt to fill new ship.
        "transfer" is only valid when equipping a ship.
        """
        requestedBBUser = self.bot.usersDB.getOrAddID(interaction.user.id)
        userItemInactives = requestedBBUser.getInventory(item_type)

        for itemNum in item_numbers:
            if itemNum > userItemInactives.numKeys:
                await interaction.response.send_message(f":x: Invalid item number! You have {userItemInactives.numKeys} {item_type.value}s.", ephemeral=True)
                return
            if itemNum < 1:
                await interaction.response.send_message(":x: Invalid item number! Must be at least 1.", ephemeral=True)
                return
        
        # Remove duplicates
        item_numbers = list(set(item_numbers))
        equipped: List[GameItem] = []
        leftover: List[GameItem] = []

        #Equip the items one by one
        iterations = 1
        for itemNum in item_numbers:
            requestedSlot = userItemInactives[itemNum - iterations]
            lastItemInSlot = requestedSlot.count == 1
            requestedItem = requestedSlot.item

            if isinstance(requestedItem, PrimaryWeapon):
                if not requestedBBUser.activeShip.canEquipMoreWeapons():
                    leftover.append(requestedItem)
                else:
                    equipped.append(requestedItem)
                    requestedBBUser.activeShip.equipWeapon(requestedItem)
                
            elif isinstance(requestedItem, ModuleItem):
                if not requestedBBUser.activeShip.canEquipMoreModules() or not requestedBBUser.activeShip.canEquipModuleType(type(requestedItem)):
                    leftover.append(requestedItem)
                else:
                    equipped.append(requestedItem)
                    requestedBBUser.activeShip.equipModule(requestedItem)

            elif isinstance(requestedItem, TurretWeapon):
                if not requestedBBUser.activeShip.canEquipMoreTurrets():
                    leftover.append(requestedItem)
                else:
                    equipped.append(requestedItem)
                    requestedBBUser.activeShip.equipTurret(requestedItem)
            
            else:
                raise NotImplementedError(f"Unexpected item type for category {item_type.value}: {type(requestedItem)}")

            if lastItemInSlot:
                iterations += 1

        for item in equipped:
            # Ignoring here because I can't convince pyright that the types will match
            userItemInactives.removeItem(item) # type: ignore[reportGeneralTypeIssues]
        
        if len(equipped) == 1:
            equippedStr = f":wrench: You equipped the **{equipped[0].name}**."
        elif equipped:
            equippedStr = ":wrench: You equipped the following items:\n" \
                        + "\n".join(f"• {i.name}" for i in equipped)
        else:
            equippedStr = ""

        if len(leftover) == 1:
            leftoverStr = f":x: Your active ship does not have any free {item_type.value} slots!"
        elif equipped:
            leftoverStr = ":x: The following items could not be equipped, because there is not enough free slots on your ship:\n" \
                        + "\n".join(f"• {i.name}" for i in leftover)
        else:
            leftoverStr = ""
        
        await interaction.response.send_message("\n".join((equippedStr, leftoverStr)))


    @app_commands.describe(
        item="The item to equip",
        move_equipped_items="When equipping a ship, move your currently equipped items to the new one. Default: No",
    )
    @app_commands.command(
        name="equip",
        description="Equip an item from your hangar into your loadout."
    )
    async def cmd_unequip(self, interaction: Interaction, item: Union[Literal["all"], EQUIPPABLE_BUT_NOT_SHIP]):
        """Unequip the item of the given item type, at the given index, from the user's active ship.
        """
        argsSplit = args.split(" ")
        unequipAllItems = len(argsSplit) > 0 and argsSplit[0] == "all"

        if isDM:
            prefix = cfg.defaultCommandPrefix
        else:
            prefix = botState.client.guildsDB.getGuild(message.guild.id).commandPrefix

        if not unequipAllItems and len(argsSplit) < 2:
            await message.reply(mention_author=False, content=":x: Not enough arguments! Please provide both an item type (all/weapon/module/turret) " \
                                        + "and an item number from `" + prefix + "hangar` or `all`.")
            return
        if len(argsSplit) > 2:
            await message.reply(mention_author=False, content=":x: Too many arguments! Please only give an item type (all/weapon/module/turret), " \
                                        + "an item number or `all`.")
            return

        requestedBBUser = botState.client.usersDB.getOrAddID(message.author.id)

        if unequipAllItems:
            requestedBBUser.unequipAll(requestedBBUser.activeShip)

            await message.reply(mention_author=False, content=":wrench: You unequipped **all items** from your ship.")
            return

        _item = argsSplit[0].rstrip("s")
        if not ItemCategory.hasValue(_item):
            await message.reply(":x: Invalid item name! Please choose from: ship, weapon, module or turret.",
                                mention_author=False)
            return
        item = ItemCategory(_item)

        if item is ItemCategory.ship:
            await message.reply(mention_author=False, content=":x: You can't go without a ship! Instead, switch to another one.")
            return

        unequipAll = argsSplit[1] == "all"
        if not unequipAll:
            itemNum = argsSplit[1]
            if not lib.stringTyping.isInt(itemNum):
                await message.reply(mention_author=False, content=":x: Invalid item number!")
                return
            itemNum = int(itemNum)
            if itemNum > len(requestedBBUser.activeShip.getActives(item)):
                await message.reply(mention_author=False, content=":x: Invalid item number! Your ship has " \
                                            + str(len(requestedBBUser.activeShip.getActives(item))) + " " + item.value + "s.")
                return
            if itemNum < 1:
                await message.reply(mention_author=False, content=":x: Invalid item number! Must be at least 1.")
                return
        else:
            itemNum = None

        if item is ItemCategory.weapon:
            if not requestedBBUser.activeShip.hasWeaponsEquipped():
                await message.reply(mention_author=False, content=":x: Your active ship does not have any weapons equipped!")
                return
            if unequipAll:
                for weapon in requestedBBUser.activeShip.weapons:
                    requestedBBUser.inactiveWeapons.addItem(weapon)
                    requestedBBUser.activeShip.unequipWeaponObj(weapon)

                await message.reply(mention_author=False, content=":wrench: You unequipped all **weapons**.")
            else:
                requestedItem = requestedBBUser.activeShip.weapons[itemNum - 1]
                requestedBBUser.inactiveWeapons.addItem(requestedItem)
                requestedBBUser.activeShip.unequipWeaponIndex(itemNum - 1)

                await message.reply(mention_author=False, content=":wrench: You unequipped the **" + requestedItem.name + "**.")

        elif item is ItemCategory.module:
            if not requestedBBUser.activeShip.hasModulesEquipped():
                await message.reply(mention_author=False, content=":x: Your active ship does not have any modules equipped!")
                return
            if unequipAll:
                for module in requestedBBUser.activeShip.modules:
                    requestedBBUser.inactiveModules.addItem(module)
                    requestedBBUser.activeShip.unequipModuleObj(module)

                await message.reply(mention_author=False, content=":wrench: You unequipped all **modules**.")
            else:
                requestedItem = requestedBBUser.activeShip.modules[itemNum - 1]
                requestedBBUser.inactiveModules.addItem(requestedItem)
                requestedBBUser.activeShip.unequipModuleIndex(itemNum - 1)

                await message.reply(mention_author=False, content=":wrench: You unequipped the **" + requestedItem.name + "**.")

        elif item is ItemCategory.turret:
            if not requestedBBUser.activeShip.hasTurretsEquipped():
                await message.reply(mention_author=False, content=":x: Your active ship does not have any turrets equipped!")
                return
            if unequipAll:
                for turret in requestedBBUser.activeShip.turrets:
                    requestedBBUser.inactiveTurrets.addItem(turret)
                    requestedBBUser.activeShip.unequipTurretObj(turret)

                await message.reply(mention_author=False, content=":wrench: You unequipped all **turrets**.")
            else:
                requestedItem = requestedBBUser.activeShip.turrets[itemNum - 1]
                requestedBBUser.inactiveTurrets.addItem(requestedItem)
                requestedBBUser.activeShip.unequipTurretIndex(itemNum - 1)

                await message.reply(mention_author=False, content=":wrench: You unequipped the **" + requestedItem.name + "**.")

        else:
            raise NotImplementedError("Valid but unsupported item name: " + item.value)

    textCommandsDB.register("unequip", cmd_unequip, 0, allowDM=True, helpSection="loadout",
                        signatureStr="**unequip <item-type> <item-num>**",
                        shortHelp="Move an item from your active ship to your hangar. Item numbers can be gotten from `loadout`.",
                        longHelp="Unequip the requested item from your active ship, into your hangar. Item numbers are shown " \
                                    + "next to items in your `loadout`.")



async def setup(bot: client.BasedClient):
    await bot.add_cog(UserLoadoutCog(bot))
