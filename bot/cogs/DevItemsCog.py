import json
from typing import List, Set, cast

from discord import app_commands, Interaction
from discord.abc import Snowflake
from discord.utils import MISSING
from discord.app_commands import Range

from ..gameObjects.items.ships import shipItem

from .. import client, lib
from bot.cfg import cfg, bbData
from bot.cfg.bbData import ItemCategory, ItemCategoryOrAll
from bot.cfg.cfg import basicAccessLevels
from ..interactions import basedCommand
from ..interactions.basedApp import BasedCog
from ..gameObjects.items import gameItem
from .util.CommonAutocomplete import divisionAutoComplete, DivisionNameOrAll
from .util.parameterVerifiers import verifyDivName
from ..users.basedGuild import BasedGuild
from ..gameObjects.guildShop import TechLeveledShop
from ..databases.bountyDB import divisionNameForLevel
from ..logging import LogCategory
from ..views.serializedItemModal import SerializedItemModal


class DevItemsCog(BasedCog):
#region commands

    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer, helpSection="items")
    @app_commands.command(name="give-item",
                            description="Spawn in an item and give it to a user.")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_give(self, interaction: Interaction, user_id: str = ""):
        """developer command giving the provided user the provided item of the provided type.
        user must be either an ID or empty (to give the item to the calling user).
        item must be a json format description in line with the item's to and deserialize functions.
        """
        requestedUser, _, _, _ = await self.UsersUtilCog.getOrCreateBasedUserOrAuthor(interaction, user_id)
        if requestedUser is None: return

        dcUser = self.bot.get_user(requestedUser.id) or await self.bot.tryFetchUser(requestedUser.id)
        userMention = "<unknown user>" if dcUser is None else dcUser.mention

        itemModal = SerializedItemModal()
        await interaction.response.send_modal(itemModal)
        if await itemModal.wait(): return
        
        if not itemModal.isValid:
            await itemModal.interaction.response.send_message(f":x: One or more validation errors occurred when processing your serialized item:\n - " \
                                                            + "\n - ".join(itemModal.errors))
            return
        
        itemDict = itemModal.itemJson()

        if itemDict["type"] not in gameItem.subClassNames:
            await itemModal.interaction.response.send_message(f":x: Failed to deserialize your `item_json`: Unknown gameItem subclass '{itemDict['type']}'", ephemeral=True)
            return

        try:
            newItem = gameItem.spawnItem(itemDict)
        except Exception as e:
            await itemModal.interaction.response.send_message(f":x: Failed to deserialize your `item_json`: {type(e).__name__} '{e}'", ephemeral=True)
            return
        
        requestedUser.getInventoryForItem(newItem).addItem(newItem)

        await itemModal.interaction.response.send_message(f":white_check_mark: Given one '{newItem.name}' to **{userMention}**!", ephemeral=True)


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer, helpSection="items")
    @app_commands.command(name="delete-item",
                            description="Delete one of an item in a user's inventory. If they have more several, the other are not affected.")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_del_item(self, interaction: Interaction, item_type: ItemCategory, item_number: Range[int, 1], user_id: str = ""):
        """Delete an item in a requested user's inventory.
        """
        user, _, _ = await self.UsersUtilCog.getBasedUserOrAuthor(interaction, user_id)
        if user is None: return None
        itemResult = await self.UsersUtilCog.getUserItemByIndex(interaction, user, item_type, item_number)
        if itemResult is None: return None
        userItemInactives, requestedItem = itemResult

        itemName = ""
        itemEmbed = None

        if isinstance(requestedItem, shipItem.Ship):
            itemName = requestedItem.getNameAndNick()
            itemEmbed = lib.discordUtil.makeEmbed(col=bbData.factionColours.get(requestedItem.manufacturer, bbData.factionColours["neutral"]),
                                                    thumb=requestedItem.icon if requestedItem.hasIcon else "")

            if requestedItem is None:
                itemEmbed.add_field(name="Item:",
                                    value="None", inline=False)
            else:
                requestedItem.fillLoadoutEmbed(itemEmbed, titlePrefix="Item: ")

        else:
            itemName = requestedItem.name + "\n" + requestedItem.statsStringShort()

        # Ignoring here because requestedItem is guaranteed to match userItemInactives's contained type, because it was retrieved from userItemInactives
        userItemInactives.removeItem(requestedItem) # type: ignore[reportGeneralTypeIssues]

        userName = str(self.bot.get_user(user.id) or "<unknown user>")
        await interaction.response.send_message(f":white_check_mark: One item deleted from {userName}'s inventory: {itemName}",
                                                embed=itemEmbed or MISSING, ephemeral=True)


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer, helpSection="items")
    @app_commands.command(name="delete-all-of-item",
                            description="Delete all of an item from a user's inventory.")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_del_item_key(self, interaction: Interaction, item_type: ItemCategory, item_number: Range[int, 1], user_id: str = ""):
        """Delete ALL of an item in a requested user's inventory.
        """
        user, _, _ = await self.UsersUtilCog.getBasedUserOrAuthor(interaction, user_id)
        if user is None: return None
        itemResult = await self.UsersUtilCog.getUserItemByIndex(interaction, user, item_type, item_number)
        if itemResult is None: return None
        userItemInactives, requestedItem = itemResult

        itemName = ""
        itemEmbed = None

        if isinstance(requestedItem, shipItem.Ship):
            itemName = requestedItem.getNameAndNick()
            itemEmbed = lib.discordUtil.makeEmbed(col=bbData.factionColours.get(requestedItem.manufacturer, bbData.factionColours["neutral"]),
                                                    thumb=requestedItem.icon if requestedItem.hasIcon else "")

            if requestedItem is None:
                itemEmbed.add_field(name="Item:",
                                    value="None", inline=False)
            else:
                requestedItem.fillLoadoutEmbed(itemEmbed, titlePrefix="Item: ")

        else:
            itemName = requestedItem.name + "\n" + requestedItem.statsStringShort()

        # Ignoring here because requestedItem is guaranteed to match userItemInactives's contained type, because it was retrieved from userItemInactives
        invListing = userItemInactives.items.pop(requestedItem, None) # type: ignore[reportGeneralTypeIssues]
        keyRemoved = userItemInactives.keys.pop(item_number - 1, None) # type: ignore[reportGeneralTypeIssues]
        if keyRemoved:
            userItemInactives.numKeys -= 1

        userName = str(self.bot.get_user(user.id) or "<unknown user>")
        listingName = f'{invListing.count} item(s)' if invListing else '**Erroneous key**'
        await interaction.response.send_message(f":white_check_mark: {listingName} deleted from {userName}'s inventory: {itemName}",
                                                embed=itemEmbed or MISSING, ephemeral=True)


    @divisionAutoComplete()
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer, helpSection="items")
    @app_commands.command(name="refresh-shop",
                            description="Developer command refreshing division shop(s) for given guild(s). Does not reset the refresh timer.")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_refreshshop(self, interaction: Interaction, guild_id: str = "here", division: DivisionNameOrAll = "all", new_level: str = "random"):
        """Refresh the shop stock of the current guild. Does not reset the shop stock cooldown.
        """
        valid, guild = await self.GuildsUtilCog.guildWithShopsByIdOrAllOrContext(interaction, guild_id)
        if not valid:
            return

        if new_level == "random":
            level = -1
        elif lib.stringTyping.isInt(new_level):
            level = int(new_level)
            if level < cfg.minTechLevel or level > cfg.maxTechLevel:
                await interaction.response.send_message(f"Invalid tech level! Must be either a number between {cfg.minTechLevel} and {cfg.maxTechLevel}, or `random`.",
                                                        ephemeral=True)
                return
            division = divisionNameForLevel(level)
        else:
            await interaction.response.send_message(f"Invalid tech level! Must be either a number between {cfg.minTechLevel} and {cfg.maxTechLevel}, or `random`.",
                                                    ephemeral=True)
            return

        async def refreshShop(guild: BasedGuild, divisionName: str, shop: TechLeveledShop):
            if level != -1:
                if shop.minLevel <= level <= shop.maxLevel:
                    shop.refreshStock(level)
                    await guild.announceNewShopStock(level)
            else:
                shop.refreshStock()
                if division != "all":
                    await guild.announceNewShopStock(level)

        await self.GuildsUtilCog.operateOverShopsAsync("dev_cmd_refreshshop", refreshShop, f"shop(s) refreshed{f' to level {level}' if level == -1 else ''}", interaction, guild, division, division == "all", logCategory=LogCategory.shop, className="DevItemsCog")
        
        # shop stock announcements are deferred until the end if all divisions are to be operated over
        # This is so that we don't send an announcement (a ping!) for every shop in the server
        if level == -1 and division == "all":
            async def announceStock(guild: BasedGuild):
                if not guild.shopsDisabled:
                    await guild.announceNewShopStock()

            await self.GuildsUtilCog.operateOverBasedGuildsAsync("dev_cmd_refreshshop", announceStock, "", interaction, guild, sendSuccess=False, logCategory=LogCategory.shop, className="DevItemsCog")


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer, helpSection="items")
    @app_commands.command(name="debug-hangar",
                            description="Developer command printing the requested user's hangar, including object memory addresses.")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_debug_hangar(self, interaction: Interaction, user_id: str = ""):
        """developer command printing the requested user's hangar, including object memory addresses.
        """
        requestedBBUser, _, _ = await self.UsersUtilCog.getBasedUserOrAuthor(interaction, user_id)
        if requestedBBUser is None: return
        requestedUser = self.bot.get_user(requestedBBUser.id) or await self.bot.tryFetchUser(requestedBBUser.id)
        userMention = "<unknown user>" if requestedUser is None else requestedUser.mention
        userProfile = "" if requestedUser is None else requestedUser.display_avatar.with_size(64).url

        maxPerPage = cfg.maxItemsPerHangarPageAll

        maxPage = requestedBBUser.numInventoryPages(ItemCategoryOrAll.all, maxPerPage)
        if maxPage == 0:
            await interaction.response.send_message(":x: The requested pilot doesn't have any items!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        for itemType in ItemCategory:
            itemInv = requestedBBUser.getInventory(itemType)
            await interaction.user.send(f"{itemType.value.upper()} KEYS: {itemInv.keys}\n" +\
                                        f"{itemType.value.upper()} LISTING KEYS: {itemInv.items.keys()}")

        for page in range(1, maxPage + 1):

            hangarEmbed = lib.discordUtil.makeEmbed(titleTxt="Hangar", desc=userMention,
                                                    col=bbData.factionColours["neutral"],
                                                    footerTxt="All items - page " + str(page) + "/" \
                                                        + str(requestedBBUser.numInventoryPages(ItemCategoryOrAll.all, maxPerPage)),
                                                    thumb=userProfile)
            firstPlace = maxPerPage * (page - 1) + 1

            for itemType in ItemCategory:
                itemInv = requestedBBUser.getInventory(itemType)
                displayedItems = []

                for itemNum in range(firstPlace, requestedBBUser.lastItemNumberOnPage(itemType, page, maxPerPage) + 1):
                    if itemNum == firstPlace:
                        hangarEmbed.add_field(name="‎", value="__**Stored " + itemType.value.title() + "s**__", inline=False)

                    currentItem = itemInv.keys[itemNum - 1]
                    itemStored = currentItem in itemInv.items
                    currentItemCount = itemInv.numStored(currentItem) if itemStored else 0
                    displayedItems.append(currentItem)
                    
                    if isinstance(currentItem, shipItem.Ship):
                        currentItemName = currentItem.getNameAndNick()
                    else:
                        currentItemName = currentItem.name
                    try:
                        hangarEmbed.add_field(name=str(itemNum) \
                                                + (currentItem.emoji.sendable + " " if currentItem.hasEmoji else "") + ". " \
                                                + ("" if itemStored else "⚠ KEY NOT FOUND IN ITEMS DICT ") \
                                                + ((" `(" + str(currentItemCount) + ")` ") if currentItemCount > 1 else "") \
                                                + currentItemName + "\n`" + repr(currentItem) + "`",
                                            value=currentItem.statsStringShort(), inline=False)
                    except AttributeError:
                        hangarEmbed.add_field(name=str(itemNum) + ". " \
                                                + ("" if itemStored else "⚠ KEY NOT FOUND IN ITEMS DICT ") \
                                                + ((" `(" + str(currentItemCount) + ")` ") if currentItemCount > 1 else "") \
                                                + currentItemName + "\n`" + repr(currentItem) + "`",
                                            value="unexpected type", inline=False)

                expectedKeys = list(itemInv.items.keys())
                for itemNum in range(len(expectedKeys)):
                    itemKey = expectedKeys[itemNum]
                    if itemKey not in displayedItems:
                        # ignoring type here because the type checker can't know that the item type matches
                        currentItemCount = itemInv.items[itemKey].count # type: ignore[reportGeneralTypeIssues]
                        displayedItems.append(itemKey)
                        if isinstance(itemKey, shipItem.Ship):
                            currentItemName = itemKey.getNameAndNick()
                        else:
                            currentItemName = itemKey.name
                        try:
                            hangarEmbed.add_field(name=str(itemNum) + (itemKey.emoji.sendable + " " if itemKey.hasEmoji else "") \
                                                    + ". ⚠ ITEM LISTING NOT FOUND IN KEYS " \
                                                    + ((" `(" + str(currentItemCount) + ")` ") if currentItemCount > 1 else "") \
                                                    + currentItemName + "\n`" + repr(itemKey) + "`",
                                                value=itemKey.statsStringShort(), inline=False)
                        except AttributeError:
                            hangarEmbed.add_field(name=str(itemNum) + ". ⚠ ITEM LISTING NOT FOUND IN KEYS " \
                                                    + ((" `(" + str(currentItemCount) + ")` ") if currentItemCount > 1 else "") \
                                                    + currentItemName + "\n`" + repr(itemKey) + "`",
                                                value="unexpected type", inline=False)

            await interaction.user.send(embed=hangarEmbed)
        
        await interaction.followup.send("Debug sent to DMs.", ephemeral=True)

#endregion

async def setup(bot: client.BasedClient):
    # Casting here because for some reason pyright doesn't think SerializableDiscordObject is a Snowflake,
    # even though it extends discord.Object
    await bot.add_cog(DevItemsCog(bot), guilds=cast(List[Snowflake], cfg.developmentGuilds))
