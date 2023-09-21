from discord import app_commands, Interaction
from discord.app_commands import Range

from .. import client, lib
from ..lib import gameMaths
from ..lib.discordUtil import ZWSP
from ..cfg import cfg
from ..cfg.cfg import basicAccessLevels
from ..cfg.bbData import ItemCategory, ItemCategoryOrAll
from ..interactions import basedCommand
from ..interactions.basedApp import BasedCog
from .util.CommonAutocomplete import anyUserHangerItemAutoComplete, AnyUserHangarItem
from .util.transformers import BoolYesNo
from ..gameObjects.kaamoShop import KaamoShop
from ..gameObjects.items.ships.shipItem import Ship
from ..logging import LogCategory


class UserKaamoCog(BasedCog):
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="kaamo club",
                                formattedDesc="Move an item from your Kaamo Club storage to your hangar.\n" \
                                            + f"This command can only be used by level {cfg.maxTechLevel} bounty hunters.")
    @app_commands.describe(
        item_type="The type of item to get.",
        item_number="The number of the item to get, from `/kaamo`."
    )
    @app_commands.command(name="kaamo-get",
                            description="Retrieve an item from the Kaamo Club. This command can only be used by " \
                                    + f"level {cfg.maxTechLevel} bounty hunters.")
    async def cmd_kaamo_get(self, interaction: Interaction, item_type: ItemCategory, item_number: Range[int, 1]):
        """Move the item of the given item type, at the given index, from the user's Kaamo Club storage into their hangar.
        """
        if not self.bot.usersDB.idExists(interaction.user.id):
            await interaction.response.send_message(f":x: This command can only be used by level {cfg.maxTechLevel} bounty hunters!", ephemeral=True)
            return

        requestedBBUser = self.bot.usersDB.getUser(interaction.user.id)
        if requestedBBUser.classicModeEnabled:
            await interaction.response.send_message(":x: This command is not available in classic mode!", ephemeral=True)
            return
        if gameMaths.calculateUserBountyHuntingLevel(requestedBBUser.bountyHuntingXP) < cfg.maxTechLevel:
            await interaction.response.send_message(f":x: This command can only be used by level {cfg.maxTechLevel} bounty hunters!", ephemeral=True)
            return

        if requestedBBUser.kaamo is None:
            await interaction.response.send_message(":x: There are no items stored in your Kaamo Club!", ephemeral=True)
        else:
            shopItemStock = requestedBBUser.kaamo.getStock(item_type)
            if item_number > shopItemStock.numKeys:
                if shopItemStock.numKeys == 0:
                    await interaction.response.send_message(f":x: There are no {item_type.value}s in your Kaamo Club!", ephemeral=True)
                else:
                    await interaction.response.send_message(f":x: Invalid item number! Your Kaamo Club has {shopItemStock.numKeys} {item_type.value}(s).", ephemeral=True)
                return

            requestedItem = shopItemStock[item_number - 1].item

            if item_type is ItemCategory.ship:
                requestedBBUser.kaamo.userBuyShipIndex(requestedBBUser, item_number - 1)
            elif item_type is ItemCategory.weapon:
                requestedBBUser.kaamo.userBuyWeaponIndex(requestedBBUser, item_number - 1)
            elif item_type is ItemCategory.turret:
                requestedBBUser.kaamo.userBuyTurretIndex(requestedBBUser, item_number - 1)
            elif item_type is ItemCategory.module:
                requestedBBUser.kaamo.userBuyModuleIndex(requestedBBUser, item_number - 1)
            elif item_type is ItemCategory.tool:
                requestedBBUser.kaamo.userBuyToolIndex(requestedBBUser, item_number - 1)
            else:
                raise NotImplementedError(f"Valid but unsupported item name: {item_type.value}")

            await interaction.response.send_message(f":outbox_tray: The **{requestedItem.name}** was moved to your hangar.", ephemeral=True)

        # Destroy Kaamo object if it is now empty
        if requestedBBUser.kaamo is not None and requestedBBUser.kaamo.isEmpty():
            requestedBBUser.kaamo = None

    
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="kaamo club",
                                formattedDesc="Move an item from your hanger to your private Kaamo Club storage.\n" \
                                                "When storing a ship, give `unequip_items=Yes` to first unequip all items, and store only the ship.\n" \
                                            + f"This command can only be used by level {cfg.maxTechLevel} bounty hunters.\n" \
                                            + f"Items in the Kaamo Club can only be retrieved again by level {cfg.maxTechLevel} bounty hunters.\n")
    @app_commands.describe(
        item="The item to retrieve.",
        unequip_items="If the item is a ship, give Yes to unequip all items before storing (Defaults to No)."
    )
    @anyUserHangerItemAutoComplete()
    @app_commands.command(name="kaamo-store",
                            description="Store an item in the Kaamo Club. This command can only be used by " \
                                    + f"level {cfg.maxTechLevel} bounty hunters.")
    async def cmd_kaamo_store(self, interaction: Interaction, item: AnyUserHangarItem, unequip_items: BoolYesNo = BoolYesNo.No):
        """Transfer the item of the given item type, at the given index, from the user's inactive items, to their kaamo club shop.
        """
        itemType, itemNum = item
        clearItems = bool(unequip_items)

        # if not self.bot.usersDB.idExists(interaction.user.id):
        #     await interaction.response.send_message(f":x: This command can only be used by level {cfg.maxTechLevel} bounty hunters!", ephemeral=True)
        #     return

        requestedBBUser = self.bot.usersDB.getOrAddID(interaction.user.id)
        if requestedBBUser.classicModeEnabled:
            await interaction.response.send_message(":x: This command is not available in classic mode!", ephemeral=True)
            return
        # if gameMaths.calculateUserBountyHuntingLevel(requestedBBUser.bountyHuntingXP) < cfg.maxTechLevel:
        #     await interaction.response.send_message(f":x: This command can only be used by level {cfg.maxTechLevel} bounty hunters!", ephemeral=True)
        #     return

        userItemInactives = requestedBBUser.getInventory(itemType)
        if itemNum > userItemInactives.numKeys:
            await interaction.response.send_message(":x: Invalid item number! You have " + str(userItemInactives.numKeys) + " " + itemType.value + "s.", ephemeral=True)
            return
        if itemNum < 1:
            await interaction.response.send_message(":x: Invalid item number! Must be at least 1.", ephemeral=True)
            return

        if requestedBBUser.kaamo is None:
            requestedBBUser.kaamo = KaamoShop()
        elif requestedBBUser.kaamo.isFull():
            if requestedBBUser.kaamo.shipsStock.totalItems > 0:
                await interaction.response.send_message(":x: The Kaamo Club has run out of storage space! Please remove some items to store more.\n" \
                                    + "If there are items equipped on your stored ships, they count too.", ephemeral=True)
            else:
                await interaction.response.send_message(":x: The Kaamo Club has run out of storage space! Please remove some items to store more.", ephemeral=True)
            return

        requestedItem = userItemInactives[itemNum - 1].item

        if itemType in [ItemCategory.weapon, ItemCategory.module, ItemCategory.turret, ItemCategory.tool]:
            {ItemCategory.weapon:      requestedBBUser.kaamo.userSellWeaponIndex,
                ItemCategory.module:   requestedBBUser.kaamo.userSellModuleIndex,
                ItemCategory.turret:   requestedBBUser.kaamo.userSellTurretIndex,
                ItemCategory.tool:     requestedBBUser.kaamo.userSellToolIndex}[itemType](requestedBBUser, itemNum - 1)
            await interaction.response.send_message(f":inbox_tray: The **{requestedItem.name}** was moved to Kaamo Club storage.", ephemeral=True)
        elif itemType == ItemCategory.ship:
            ship = requestedBBUser.getInventory(ItemCategory.ship).itemAtIndex(itemNum - 1)
            if not isinstance(ship, Ship):
                raise TypeError(f"Found non {Ship.__name__}-typed ship in user ship inventory: {type(ship).__name__} {ship}")
            if clearItems:
                unequipped = requestedBBUser.unequipAll(ship)
            else:
                unequipped = 0
            requestedBBUser.kaamo.userSellShipObj(requestedBBUser, ship)
            await interaction.response.send_message(f":inbox_tray: The **{requestedItem.name}** was moved to Kaamo Club storage." \
                                                    + (f"\n**{unequipped}** items were unequipped, and moved to your hangar." if unequipped else ""),
                                                    ephemeral=True)
        else:
            raise NotImplementedError(f"Valid but unsupported item name: {itemType.value}")


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="kaamo club",
                                formattedDesc="List all items in your Kaamo Club storage. Kaamo has a max capacity of " \
                                            + f"{cfg.kaamoMaxCapacity} items, including items on ships. Give an item type " \
                                            + f"({'/'.join(i.value for i in ItemCategory)}) to only list items of that type.\n\n" \
                                            + f"⚠ `/kaamo-store` and `/kaamo get` can only be used by level {cfg.maxTechLevel} bounty hunters.")
    @app_commands.describe(
        item_type="The type of items to list. Defaults to all items.",
    )
    @app_commands.command(name="kaamo",
                            description="List all items in your private Kaamo Club storage. Kaamo has a max capacity of " \
                                    + f"{cfg.kaamoMaxCapacity} items.")
    async def cmd_kaamo(self, interaction: Interaction, item_type: ItemCategoryOrAll = ItemCategoryOrAll.all):
        """list the items currently stored in the user's kaamo club.
        Can specify an item type to list. TODO: Make specified item listings more detailed as in !bb bounties
        """
        if not self.bot.usersDB.idExists(interaction.user.id):
            shopEmbed = lib.discordUtil.makeEmbed(titleTxt="Kaamo Club Storage",
                                                desc=f"{interaction.user.mention}\n*0/{cfg.kaamoMaxCapacity} items*",
                                                footerTxt="All items" if item_type is ItemCategoryOrAll.all else (item_type.value + "s").title(),
                                                thumb=interaction.user.display_avatar.with_size(64).url)
            shopEmbed.add_field(name=ZWSP, value="No items stored.")
        
        else:
            callingBBUser = self.bot.usersDB.getUser(interaction.user.id)

            numItemsStr = str(callingBBUser.kaamo.totalItems) if callingBBUser.kaamo is not None else "0"
            shopEmbed = lib.discordUtil.makeEmbed(titleTxt="Kaamo Club Storage",
                                                    desc=interaction.user.mention + "\n*" \
                                                        + f"{numItemsStr}/{cfg.kaamoMaxCapacity} items*",
                                                    footerTxt="All items" if item_type is ItemCategoryOrAll.all else (item_type.value + "s").title(),
                                                    thumb=interaction.user.display_avatar.with_size(64).url)

            if callingBBUser.kaamo is None or callingBBUser.kaamo.totalItems == 0:
                shopEmbed.add_field(name=ZWSP, value="No items stored.")
            else:
                for currentItemType in [ItemCategoryOrAll.ship, ItemCategoryOrAll.weapon, ItemCategoryOrAll.module, ItemCategoryOrAll.turret, ItemCategoryOrAll.tool]:
                    if item_type in [ItemCategoryOrAll.all, currentItemType]:
                        currentStock = callingBBUser.kaamo.getStock(currentItemType.noAll())
                        for itemNum in range(1, currentStock.numKeys + 1):
                            if itemNum == 1:
                                shopEmbed.add_field(name=ZWSP,
                                                    value=f"__**{currentItemType.value.title()}s**__",
                                                    inline=False)

                            try:
                                currentItem = currentStock.itemAtIndex(itemNum - 1)
                            except KeyError:
                                try:
                                    self.bot.logger.log("Main", "cmd_kaamo",
                                                        f"Requested {currentItemType.value} '{currentStock.keys[itemNum-1].name}" \
                                                            + f"' (index {itemNum-1}" \
                                                            + "), which was not found in the shop stock",
                                                        category=LogCategory.shop, eventType="UNKWN_KEY", interaction=interaction)
                                except IndexError:
                                    break
                                except AttributeError as e:
                                    self.bot.logger.log("Main", "cmd_kaamo",
                                                        f"Unexpected type in {currentItemType.value}sStock KEYS, index " \
                                                            + str(itemNum-1) + ". Got " \
                                                            + type(currentStock.keys[itemNum-1]).__name__ \
                                                            + ".\nInventory keys: " \
                                                            + ", ".join(str(item) for item in currentStock.items),
                                                        category=LogCategory.shop, eventType="INVTY_KEY_TYPE", interaction=interaction)
                                    shopEmbed.add_field(name=f"{itemNum}. **⚠ #INVALID-ITEM# '{currentStock.keys[itemNum-1]}'",
                                                        value="Do not attempt to get. Could cause issues.", inline=True)
                                    continue
                                shopEmbed.add_field(name=f"{itemNum}. **⚠ #INVALID-ITEM# '{currentStock.keys[itemNum-1].name}'",
                                                    value="Do not attempt to get. Could cause issues.", inline=True)
                                continue

                            currentItemCount = currentStock.items[currentItem].count
                            shopEmbed.add_field(name=str(itemNum) + ". " \
                                                    + (currentItem.emoji.sendable + " " if currentItem.hasEmoji else "") \
                                                    + ((" `(" + str(currentItemCount) + ")` ") if currentItemCount > 1 else "") \
                                                    + "**" + currentItem.name + "**",
                                                value=lib.stringUtil.commaSplitNum(currentItem.value) + " Credits\n" \
                                                    + currentItem.statsStringShort(), inline=True)

        await interaction.response.send_message(embed=shopEmbed, ephemeral=True)


async def setup(bot: client.BasedClient):
    await bot.add_cog(UserKaamoCog(bot))
