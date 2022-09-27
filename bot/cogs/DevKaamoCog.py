import json
from typing import List, cast
from discord import Forbidden, app_commands, Interaction
from discord.abc import Snowflake
from discord.app_commands import Range
from discord.utils import MISSING

from .. import client, lib
from ..cfg import cfg, bbData
from ..cfg.cfg import basicAccessLevels
from ..cfg.bbData import ItemCategory
from ..interactions import basedCommand, basedApp
from ..gameObjects.items import gameItem
from ..gameObjects.items.shipItem import Ship
from ..gameObjects.kaamoShop import KaamoShop
from ..gameObjects import guildShop
from ..logging import LogCategory

class DevKaamoCog(basedApp.BasedCog):
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer, helpSection="kaamo")
    @app_commands.command(name="kaamo-give",
                            description="Developer command spawning the described item, and placing it in the given user's kaamo shop.")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_kaamo_give(self, interaction: Interaction, item_json: str, user_id: str = ""):
        """developer command spawning the described item, and placing it in the given user's kaamo shop.
        item must be a json format description in line with the item's deserialize function.
        """
        requestedUser, _, _, _ = await self.UsersUtilCog.getOrCreateBasedUserOrAuthor(interaction, user_id)
        if requestedUser is None: return

        dcUser = self.bot.get_user(requestedUser.id) or await self.bot.tryFetchUser(requestedUser.id)
        userMention = "<unknown user>" if dcUser is None else dcUser.mention

        if requestedUser.kaamo is not None and requestedUser.kaamo.isFull():
            await interaction.response.send_message(":x: That user's Kaamo storage is full!", ephemeral=True)
            return

        try:
            itemDict = json.loads(item_json)
        except json.JSONDecodeError as e:
            await interaction.response.send_message(f":x: Your `item_json` is not valid json: {e}", ephemeral=True)
            return

        if "type" not in itemDict:
            await interaction.response.send_message(f":x: Failed to deserialize your `item_json`: Missing 'type' property", ephemeral=True)
            return

        if itemDict["type"] not in gameItem.subClassNames:
            await interaction.response.send_message(f":x: Failed to deserialize your `item_json`: Unknown gameItem subclass '{itemDict['type']}'", ephemeral=True)
            return

        newItem = gameItem.spawnItem(itemDict)
        if not isinstance(newItem, guildShop.StoredItemTypesTuple):
            await interaction.response.send_message(f":x: Deserialized item type '{type(newItem).__name__}' is not stored in shops.", ephemeral=True)
            return
        
        if requestedUser.kaamo is None:
            requestedUser.kaamo = KaamoShop()
        itemStock = requestedUser.kaamo.getStockByType(type(newItem))
        itemStock.addItem(newItem)

        await interaction.response.send_message(f":white_check_mark: Given one '{newItem.name}' to **" \
                                                + userMention + "**!", ephemeral=True)


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer, helpSection="kaamo")
    @app_commands.command(name="debug-kaamo",
                            description="")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_debug_kaamo(self, interaction: Interaction, user_id: str = ""):
        """developer command printing the requested user's kaamo, including object memory addresses.
        """
        requestedBBUser, _, _ = await self.UsersUtilCog.getBasedUserOrAuthor(interaction, user_id)
        if requestedBBUser is None: return

        if requestedBBUser.kaamo is None:
            await interaction.response.send_message(":x: The requested pilot has no kaamo!", ephemeral=True)
            return
        if requestedBBUser.kaamo.isEmpty():
            await interaction.response.send_message(":x: The kaamo is empty!", ephemeral=True)
            return

        requestedUser = self.bot.get_user(requestedBBUser.id) or await self.bot.tryFetchUser(requestedBBUser.id)
        userMention = "<unknown user>" if requestedUser is None else requestedUser.mention
        userProfile = "" if requestedUser is None else requestedUser.display_avatar.with_size(64).url

        shopEmbed = lib.discordUtil.makeEmbed(titleTxt="Kaamo",
                                                desc=userMention,
                                                footerTxt="All items",
                                                thumb=userProfile)

        await interaction.response.defer(ephemeral=True)

        itemTypes = (ItemCategory.ship, ItemCategory.weapon, ItemCategory.module, ItemCategory.turret, ItemCategory.tool)
        for itemType in itemTypes:
            itemInv = requestedBBUser.kaamo.getStock(itemType)
            await interaction.user.send(f"{itemType.value.upper()} KEYS: {itemInv.keys}\n" +\
                                        f"{itemType.value.upper()} LISTING KEYS: {itemInv.items.keys()}")

        for itemType in itemTypes:
            currentStock = requestedBBUser.kaamo.getStock(itemType)

            shopEmbed.add_field(name="‎", value=f"__**{itemType.value.title()}s**__", inline=False)
            expectedNumKeys = len(currentStock.keys)
            if currentStock.numKeys != expectedNumKeys:
                shopEmbed.description = f"Expected {currentStock.numKeys} keys, found {expectedNumKeys}"
                self.bot.logger.log(type(self).__name__, self.dev_cmd_debug_kaamo.callback.__name__,
                                    f"Unexpected number of keys in {itemType.value}sStock. Expected {currentStock.numKeys}, found {expectedNumKeys}.",
                                    category=LogCategory.shop, eventType="INVTY_KEY_COUNT")

            for itemNum, currentKey in enumerate(currentStock.keys):
                if not isinstance(currentKey, gameItem.GameItem):
                    self.bot.logger.log(type(self).__name__, self.dev_cmd_debug_kaamo.callback.__name__,
                                        f"Unexpected type in {itemType.value}sStock KEYS, index {itemNum}. " \
                                            + f"Got {type(currentKey).__name__}.\n" \
                                            + "Inventory keys: " \
                                            + ", ".join(str(i) for i in currentStock.items),
                                        category=LogCategory.shop, eventType="INVTY_KEY_TYPE")

                    shopEmbed.add_field(name=f"{itemNum+1}. **⚠ #INVALID-ITEM# '{currentKey}'",
                                        value="Do not attempt to buy. Could cause issues.", inline=True)
                    continue

                try:
                    currentItem = cast(guildShop.StoredItemType, currentStock[itemNum].item)
                except KeyError:
                    self.bot.logger.log(type(self).__name__, self.dev_cmd_debug_kaamo.callback.__name__,
                                        f"Requested {itemType.value} '{currentKey.name}' (index {itemNum}), "
                                        + "which was not found in the shop stock",
                                        category=LogCategory.shop, eventType="UNKWN_KEY")
                    shopEmbed.add_field(name=f"{itemNum+1}. **⚠ #INVALID-ITEM# '{currentKey.name}'",
                                        value="Do not attempt to buy. Could cause issues.", inline=True)
                    continue

                if not isinstance(currentItem, gameItem.GameItem):
                    self.bot.logger.log(type(self).__name__, self.dev_cmd_debug_kaamo.callback.__name__,
                                        f"Unexpected type in {itemType.value}sStock listing item, index {itemNum}. " \
                                            + f"Got {type(currentItem).__name__}.\n" \
                                            + "Inventory keys: " \
                                            + ", ".join(str(i) for i in currentStock.items),
                                        category=LogCategory.shop, eventType="INVTY_LSTNG_ITEM_TYPE")
                    shopEmbed.add_field(name=f"{itemNum+1}. **⚠ #INVALID-ITEM# '{currentItem}'",
                                        value="Do not attempt to buy. Could cause issues.", inline=True)
                    continue
                
                itemListing = currentStock.getListing(currentItem)
                currentItemCount = itemListing.count
                currentitemEmoji = currentItem.emoji.sendable + " " if currentItem.hasEmoji else ""
                currentItemCountStr = (" `(" + str(currentItemCount) + ")` ") if currentItemCount > 1 else ""
                
                shopEmbed.add_field(name=f"{itemNum+1}. {currentitemEmoji} {currentItemCountStr} **{currentItem.name}**",
                                    value=currentItem.statsStringShort(), inline=True)

        try:
            await interaction.user.send(embed=shopEmbed)
        except Forbidden:
            await interaction.followup.send(":x: I can't DM you, " + interaction.user.display_name \
                + "! Please enable DMs from users who are not friends.", ephemeral=True)
        else:
            await interaction.followup.send("Debug sent to DMs.", ephemeral=True)


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer, helpSection="kaamo")
    @app_commands.command(name="del-kaamo-item",
                            description="Delete one of an item in a requested user's kaamo. If the user has multiple, only one is affected.")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_del_kaamo_item(self, interaction: Interaction, item_type: ItemCategory, item_number: Range[int, 1], user_id: str = ""):
        """Delete an item in a requested user's kaamo.
        """
        requestedBBUser, _, _ = await self.UsersUtilCog.getBasedUserOrAuthor(interaction, user_id)
        if requestedBBUser is None: return

        if requestedBBUser.kaamo is None:
            await interaction.response.send_message(":x: The requested pilot has no kaamo!", ephemeral=True)
            return
        if requestedBBUser.kaamo.isEmpty():
            await interaction.response.send_message(":x: The user's kaamo is empty!", ephemeral=True)
            return

        kaamoItemStock = requestedBBUser.kaamo.getStock(item_type)
        if item_number > kaamoItemStock.numKeys:
            await interaction.response.send_message(f":x: Invalid item number! The user only has {kaamoItemStock.numKeys} {item_type.value}s.", ephemeral=True)
            return
        if item_number < 1:
            await interaction.response.send_message(":x: Invalid item number! Must be at least 1.", ephemeral=True)
            return

        requestedUser = self.bot.get_user(requestedBBUser.id) or await self.bot.tryFetchUser(requestedBBUser.id)
        userMention = "<unknown user>" if requestedUser is None else requestedUser.mention

        requestedItem = cast(guildShop.StoredItemType, kaamoItemStock[item_number - 1].item)
        itemName = ""
        itemEmbed = None

        if not isinstance(requestedItem, gameItem.GameItem):
            itemName = f"Unexpected item type: {type(requestedItem).__name__}"
        elif isinstance(requestedItem, Ship):
            itemName = requestedItem.getNameAndNick()
            itemEmbed = lib.discordUtil.makeEmbed(col=bbData.factionColours.get(requestedItem.manufacturer, bbData.factionColours["neutral"]),
                                                    thumb=requestedItem.icon if requestedItem.hasIcon else "")

            itemEmbed.add_field(name="Item:", inline=False,
                                value=f"{requestedItem.getNameAndNick()}\n{requestedItem.statsStringNoItems()}")

            for itemType, maxEquips in (
                    (ItemCategory.weapon, requestedItem.getMaxPrimaries()),
                    (ItemCategory.module, requestedItem.getMaxModules()),
                    (ItemCategory.turret, requestedItem.getMaxTurrets())):

                if maxEquips > 0:
                    actives = requestedItem.getActives(itemType)
                    itemEmbed.add_field(name="‎", inline=False,
                                        value=f"__**Equipped {itemType.value.title()}s**__ *{len(actives)}/{maxEquips}*")

                    for itemNum, item in enumerate(actives):
                        itemEmoji = item.emoji.sendable + " " if item.hasEmoji else ""
                        itemEmbed.add_field(name=f"{itemNum+1}. {itemEmoji}{item.name}",
                                            value=item.statsStringShort(), inline=True)
        else:
            itemName = requestedItem.name + "\n" + requestedItem.statsStringShort()

        kaamoItemStock.removeItem(requestedItem)
        await interaction.response.send_message(f":white_check_mark: One item deleted from {userMention}'s kaamo: {itemName}",
                                                embed=itemEmbed or MISSING, ephemeral=True)

        # Destroy Kaamo object if it is now empty
        if requestedBBUser.kaamo.isEmpty():
            requestedBBUser.kaamo = None


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer, helpSection="kaamo")
    @app_commands.command(name="del-kaamo-item-key",
                            description="Delete ALL of an item in a requested user's kaamo.")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_del_kaamo_item_key(self, interaction: Interaction, item_type: ItemCategory, item_number: Range[int, 1], user_id: str = ""):
        """Delete ALL OF an item in a requested user's kaamo.
        """
        requestedBBUser, _, _ = await self.UsersUtilCog.getBasedUserOrAuthor(interaction, user_id)
        if requestedBBUser is None: return

        if requestedBBUser.kaamo is None:
            await interaction.response.send_message(":x: The requested pilot has no kaamo!", ephemeral=True)
            return
        if requestedBBUser.kaamo.isEmpty():
            await interaction.response.send_message(":x: The user's kaamo is empty!", ephemeral=True)
            return

        kaamoItemStock = requestedBBUser.kaamo.getStock(item_type)
        if item_number > kaamoItemStock.numKeys:
            await interaction.response.send_message(f":x: Invalid item number! The user only has {kaamoItemStock.numKeys} {item_type.value}s.", ephemeral=True)
            return
        if item_number < 1:
            await interaction.response.send_message(":x: Invalid item number! Must be at least 1.", ephemeral=True)
            return

        requestedUser = self.bot.get_user(requestedBBUser.id) or await self.bot.tryFetchUser(requestedBBUser.id)
        userMention = "<unknown user>" if requestedUser is None else requestedUser.mention

        requestedItem = cast(guildShop.StoredItemType, kaamoItemStock[item_number - 1].item)
        itemName = ""
        itemEmbed = None

        if not isinstance(requestedItem, gameItem.GameItem):
            itemName = f"Unexpected item type: {type(requestedItem).__name__}"
        elif isinstance(requestedItem, Ship):
            itemName = requestedItem.getNameAndNick()
            itemEmbed = lib.discordUtil.makeEmbed(col=bbData.factionColours.get(requestedItem.manufacturer, bbData.factionColours["neutral"]),
                                                    thumb=requestedItem.icon if requestedItem.hasIcon else "")

            itemEmbed.add_field(name="Item:", inline=False,
                                value=f"{requestedItem.getNameAndNick()}\n{requestedItem.statsStringNoItems()}")

            for itemType, maxEquips in (
                    (ItemCategory.weapon, requestedItem.getMaxPrimaries()),
                    (ItemCategory.module, requestedItem.getMaxModules()),
                    (ItemCategory.turret, requestedItem.getMaxTurrets())):

                if maxEquips > 0:
                    actives = requestedItem.getActives(itemType)
                    itemEmbed.add_field(name="‎", inline=False,
                                        value=f"__**Equipped {itemType.value.title()}s**__ *{len(actives)}/{maxEquips}*")

                    for itemNum, item in enumerate(actives):
                        itemEmoji = item.emoji.sendable + " " if item.hasEmoji else ""
                        itemEmbed.add_field(name=f"{itemNum+1}. {itemEmoji}{item.name}",
                                            value=item.statsStringShort(), inline=True)
        else:
            itemName = requestedItem.name + "\n" + requestedItem.statsStringShort()

        if requestedItem not in kaamoItemStock.items:
            kaamoItemStock.keys.remove(requestedItem)
            kaamoItemStock.numKeys -= 1
            await interaction.response.send_message(f":white_check_mark: **Erroneous key** deleted from {userMention}'s kaamo: {itemName}",
                                                    embed=itemEmbed or MISSING, ephemeral=True)
        else:
            itemCount = kaamoItemStock.items[requestedItem].count
            del kaamoItemStock.items[requestedItem]
            kaamoItemStock.keys.remove(requestedItem)
            kaamoItemStock.numKeys -= 1
            await interaction.response.send_message(f":white_check_mark: {itemCount} item(s) deleted from {userMention}'s kaamo: {itemName}",
                                                    embed=itemEmbed or MISSING, ephemeral=True)

        # Destroy Kaamo object if it is now empty
        if requestedBBUser.kaamo.isEmpty():
            requestedBBUser.kaamo = None


async def setup(bot: client.BasedClient):
    # Casting here because for some reason pyright doesn't think SerializableDiscordObject is a Snowflake,
    # even though it extends discord.Object
    await bot.add_cog(DevKaamoCog(bot), guilds=cast(List[Snowflake], cfg.developmentGuilds))
