from discord import app_commands, Interaction
from discord.app_commands import Range

from .. import client
from bot.lib.discordUtil import makeEmbed
from bot.lib.stringTyping import formatMultiplier, commaSplitNum
from bot.cfg import cfg
from ..logging import LogCategory
from bot.cfg.bbData import ItemCategory, ItemCategoryOrAll
from bot.cfg.cfg import basicAccessLevels
from ..interactions import basedCommand
from ..interactions.basedApp import BasedCog
from bot.gameObjects.guildShop import StoredItemTypesTuple


class UserLomaCog(BasedCog):
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="loma",
                                formattedDesc="Buy the requested item from the pirates at Loma. Item numbers are shown next to items in `/loma`.")
    @app_commands.describe(
        item_type="The type of item to get.",
        item_number="The number of the item to get, from `/kaamo`."
    )
    @app_commands.command(name="loma-buy",
                            description="Buy an item from the pirates at Loma. Item numbers can be seen in /Loma.")
    async def cmd_loma_buy(self, interaction: Interaction, item_type: ItemCategory, item_number: Range[int, 1]):
        """Buy the item of the given item type, at the given index, from the user's loma shop.
        """
        if not self.bot.usersDB.idExists(interaction.user.id):
            await interaction.response.send_message("The Loma pirates do not have any items to sell!", ephemeral=True)
            return

        requestedBUser = self.bot.usersDB.getUser(interaction.user.id)
        if requestedBUser.loma is None or requestedBUser.loma.isEmpty():
            await interaction.response.send_message("The Loma pirates do not have any items to sell!", ephemeral=True)
            if requestedBUser.loma is None: requestedBUser.loma = None
            return

        shopItemStock = requestedBUser.loma.getStock(item_type)
        if item_number > shopItemStock.numKeys:
            if shopItemStock.numKeys == 0:
                await interaction.response.send_message(f":x: The Loma pirates don't have any {item_type.value}s in stock!", ephemeral=True)
            else:
                await interaction.response.send_message(f":x: Invalid item number! Loma currently has {shopItemStock.numKeys} {item_type.value}(s).", ephemeral=True)
            return

        itemListing = shopItemStock[item_number - 1]
        requestedItem = itemListing.item
        if not isinstance(requestedItem, StoredItemTypesTuple):
            raise TypeError(f"Unexpected item type: {type(requestedItem)} {requestedItem}")

        if not requestedBUser.loma.userCanAffordItemObj(requestedBUser, requestedItem):
            await interaction.response.send_message(":x: You can't afford that item!", ephemeral=True)
            return

        requestedBUser.loma.userBuyItem(requestedBUser, requestedItem)
        await interaction.response.send_message(":moneybag: Congratulations on your new **" + requestedItem.name \
                                    + "**! \n\nYour balance is now: **" + str(requestedBUser.credits) + " credits**.")

        # Destroy Loma object if it is now empty
        if requestedBUser.loma.isEmpty():
            requestedBUser.loma = None
            

    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="loma",
                                formattedDesc="List all items currently on offer, to you only, by the pirates at Loma. Give an item type " \
                                            + "to only list items of that type.")
    @app_commands.describe(
        item_type="The type of items to view.",
    )
    @app_commands.command(name="loma",
                            description="List all items currently on offer, to you only, by the pirates at Loma.")
    async def cmd_loma(self, interaction: Interaction, item_type: ItemCategoryOrAll = ItemCategoryOrAll.all):
        """list the items currently available in the user's loma shop.
        Can specify an item type to list.
        TODO: Make specified item listings more detailed as in !bb bounties
        """
        shopEmbed = makeEmbed(titleTxt="Loma",
                                desc=interaction.user.mention,
                                footerTxt="All items" if item_type is ItemCategoryOrAll.all else (item_type.value + "s").title(),
                                thumb=interaction.user.display_avatar.with_size(64).url)
        
        if not self.bot.usersDB.idExists(interaction.user.id):
            shopEmbed.add_field(name="‎", value="No items currently available.")
            await interaction.response.send_message(embed=shopEmbed, ephemeral=True)
            return

        callingBBUser = self.bot.usersDB.getUser(interaction.user.id)

        if callingBBUser.loma is None or callingBBUser.loma.isEmpty():
            shopEmbed.add_field(name="‎", value="No items currently available.")
            await interaction.response.send_message(embed=shopEmbed, ephemeral=True)
            return
        
        for currentItemType in [ItemCategoryOrAll.ship, ItemCategoryOrAll.weapon, ItemCategoryOrAll.module, ItemCategoryOrAll.turret, ItemCategoryOrAll.tool]:
            if item_type in [ItemCategoryOrAll.all, currentItemType]:
                currentStock = callingBBUser.loma.getStock(currentItemType.noAll())
                for itemNum in range(1, currentStock.numKeys + 1):
                    if itemNum == 1:
                        shopEmbed.add_field(name="‎", value="__**" + currentItemType.value.title() + "s**__", inline=False)

                    try:
                        currentItem = currentStock.itemAtIndex(itemNum - 1)
                    except KeyError:
                        try:
                            self.bot.logger.log("Main", "cmd_loma",
                                                "Requested " + currentItemType.value + " '" + currentStock.keys[itemNum-1].name \
                                                    + "' (index " + str(itemNum-1) \
                                                    + "), which was not found in the shop stock",
                                                category=LogCategory.shop, eventType="UNKWN_KEY", interaction=interaction)
                        except IndexError:
                            break
                        except AttributeError as e:
                            keysStr = ""
                            for item in currentStock.items:
                                keysStr += str(item) + ", "
                            self.bot.logger.log("Main", "cmd_loma",
                                                "Unexpected type in " + currentItemType.value + "sStock KEYS, index " \
                                                    + str(itemNum-1) + ". Got " \
                                                    + type(currentStock.keys[itemNum-1]).__name__ + ".\nInventory keys: " \
                                                    + keysStr[:-2],
                                                category=LogCategory.shop, eventType="INVTY_KEY_TYPE", interaction=interaction)
                            shopEmbed.add_field(name=f"{itemNum}. **⚠ #INVALID-ITEM# '{currentStock.keys[itemNum-1]}'",
                                                value="Do not attempt to buy. Could cause issues.", inline=True)
                            continue
                        shopEmbed.add_field(name=str(itemNum) + ". **⚠ #INVALID-ITEM# '" \
                                                + currentStock.keys[itemNum-1].name + "'",
                                            value="Do not attempt to buy. Could cause issues.", inline=True)
                        continue
                    
                    itemListing = currentStock.getListing(currentItem)
                    currentItemCount = itemListing.count
                    if itemListing.discounts:
                        discountedValue = int(currentItem.value * itemListing.discounts[0].mult)
                        discountAmountStr = formatMultiplier(itemListing.discounts[0].mult)
                        valueStr = f"~~{commaSplitNum(currentItem.value)}~~ {commaSplitNum(discountedValue)}" \
                                    + f" Credits\n*{discountAmountStr}: {itemListing.discounts[0].desc}*\n"
                    else:
                        valueStr = f"{commaSplitNum(currentItem.value)} Credits\n"
                    shopEmbed.add_field(name=str(itemNum) + ". " \
                                            + (currentItem.emoji.sendable + " " if currentItem.hasEmoji else "") \
                                            + ((" `(" + str(currentItemCount) + ")` ") if currentItemCount > 1 else "") \
                                            + "**" + currentItem.name + "**",
                                        value=valueStr + currentItem.statsStringShort(), inline=True)
    
        await interaction.response.send_message(embed=shopEmbed)


async def setup(bot: client.BasedClient):
    await bot.add_cog(UserLomaCog(bot))
