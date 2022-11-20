from typing import List, cast
from discord import app_commands, Interaction
from discord.app_commands import Range

from .. import client
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


class UserLoadoutCog(BasedCog):
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="loadout")
    @app_commands.command(name="set-balance",
                            description="Set a user's credits balance")
    async def cmd_hangar(self, interaction: Interaction, item_type: ItemCategoryOrAll = ItemCategoryOrAll.all, page: Range[int, 1] = 1):
        """return a page listing the calling user's items.
        """
        if item_type == ItemCategoryOrAll.all:
            maxPerPage = cfg.maxItemsPerHangarPageAll
        else:
            maxPerPage = cfg.maxItemsPerHangarPageIndividual

        firstPlace = maxPerPage * (page - 1) + 1
        pageError = ""

        if not self.bot.usersDB.idExists(interaction.user.id):
            if page > 1:
                pageError = ":x: You only have one page of items. Showing page one:"
                page = 1
                firstPlace = 1
            elif page < 1:
                pageError = ":x: Invalid page number. Showing page one:"
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
            await message.reply(mention_author=False, embed=hangarEmbed)
            return

        else:
            requestedBBUser = self.bot.usersDB.getUser(interaction.user.id)

            if page < 1:
                await message.reply(mention_author=False, content=":x: Invalid page number. Showing page one:")
                page = 1
                firstPlace = 1
            else:
                maxPage = requestedBBUser.numInventoryPages(item_type, maxPerPage)
                if maxPage == 0:
                    await message.reply(mention_author=False, content=":x: " + ("The requested pilot doesn't" if foundUser else "You don't") \
                                                + " have any " + ("items" if item_type == ItemCategoryOrAll.all else "of that item") + "!")
                    return
                elif page > maxPage:
                    await message.reply(mention_author=False, content=":x: " + ("The requested pilot" if foundUser else "You") + " only " \
                                                + ("has " if foundUser else "have ") + str(maxPage) \
                                                + " page(s) of items. Showing page " + str(maxPage) + ":")
                    page = maxPage
                    firstPlace = maxPerPage * (page - 1) + 1

            hangarEmbed = lib.discordUtil.makeEmbed(titleTxt="Hangar", desc=interaction.user.mention,
                                                    col=bbData.factionColours["neutral"],
                                                    footerTxt=("All item" if item_type is ItemCategoryOrAll.all else item_type.value.rstrip("s").title()) \
                                                                + "s - page " + str(page) + "/" \
                                                                + str(requestedBBUser.numInventoryPages(item_type, maxPerPage)),
                                                    thumb=interaction.user.avatar_url_as(size=64))

            if item_type in [ItemCategoryOrAll.all, ItemCategoryOrAll.ship]:
                for shipNum in range(firstPlace, requestedBBUser.lastItemNumberOnPage(ItemCategory.ship, page, maxPerPage) + 1):
                    if shipNum == firstPlace:
                        hangarEmbed.add_field(name=ZWSP, value="__**Stored Ships**__", inline=False)
                    currentItem = requestedBBUser.inactiveShips[shipNum - 1].item
                    currentItemCount = requestedBBUser.inactiveShips.items[currentItem].count
                    hangarEmbed.add_field(name=str(shipNum) + ". " \
                                                + (currentItem.emoji.sendable + " " if currentItem.hasEmoji else "") \
                                                + ((" `(" + str(currentItemCount) + ")` ") if currentItemCount > 1 else "") \
                                                + currentItem.getNameAndNick(), value=currentItem.statsStringShort(),
                                            inline=False)

            if item_type in [ItemCategoryOrAll.all, ItemCategoryOrAll.weapon]:
                for weaponNum in range(firstPlace, requestedBBUser.lastItemNumberOnPage(ItemCategory.weapon, page, maxPerPage) + 1):
                    if weaponNum == firstPlace:
                        hangarEmbed.add_field(name=ZWSP, value="__**Stored Weapons**__", inline=False)
                    currentItem = requestedBBUser.inactiveWeapons[weaponNum - 1].item
                    currentItemCount = requestedBBUser.inactiveWeapons.items[currentItem].count
                    hangarEmbed.add_field(name=str(weaponNum) + ". " \
                                                + (currentItem.emoji.sendable + " " if currentItem.hasEmoji else "") \
                                                + ((" `(" + str(currentItemCount) + ")` ") if currentItemCount > 1 else "") \
                                                + currentItem.name, value=currentItem.statsStringShort(), inline=False)

            if item_type in [ItemCategoryOrAll.all, ItemCategoryOrAll.module]:
                for moduleNum in range(firstPlace, requestedBBUser.lastItemNumberOnPage(ItemCategory.module, page, maxPerPage) + 1):
                    if moduleNum == firstPlace:
                        hangarEmbed.add_field(name=ZWSP, value="__**Stored Modules**__", inline=False)
                    currentItem = requestedBBUser.inactiveModules[moduleNum - 1].item
                    currentItemCount = requestedBBUser.inactiveModules.items[currentItem].count
                    hangarEmbed.add_field(name=str(moduleNum) + ". " \
                                                + (currentItem.emoji.sendable + " " if currentItem.hasEmoji else "") \
                                                + ((" `(" + str(currentItemCount) + ")` ") if currentItemCount > 1 else "") \
                                                + currentItem.name,
                                            value=currentItem.statsStringShort(), inline=False)

            if item_type in [ItemCategoryOrAll.all, ItemCategoryOrAll.turret]:
                for turretNum in range(firstPlace, requestedBBUser.lastItemNumberOnPage(ItemCategory.turret, page, maxPerPage) + 1):
                    if turretNum == firstPlace:
                        hangarEmbed.add_field(name=ZWSP, value="__**Stored Turrets**__", inline=False)
                    currentItem = requestedBBUser.inactiveTurrets[turretNum - 1].item
                    currentItemCount = requestedBBUser.inactiveTurrets.items[currentItem].count
                    hangarEmbed.add_field(name=str(turretNum) + ". " \
                                                + (currentItem.emoji.sendable + " " if currentItem.hasEmoji else "") \
                                                + ((" `(" + str(currentItemCount) + ")` ") if currentItemCount > 1 else "") \
                                                + currentItem.name,
                                            value=currentItem.statsStringShort(), inline=False)

            if item_type in [ItemCategoryOrAll.all, ItemCategoryOrAll.tool]:
                for toolNum in range(firstPlace, requestedBBUser.lastItemNumberOnPage(ItemCategory.tool, page, maxPerPage) + 1):
                    if toolNum == firstPlace:
                        hangarEmbed.add_field(name=ZWSP, value="__**Stored Tools**__", inline=False)
                    currentItem = requestedBBUser.inactiveTools[toolNum - 1].item
                    currentItemCount = requestedBBUser.inactiveTools.items[currentItem].count
                    hangarEmbed.add_field(name=str(toolNum) + ". " \
                                                + (currentItem.emoji.sendable + " " if currentItem.hasEmoji else "") \
                                                + ((" `(" + str(currentItemCount) + ")` ") if currentItemCount > 1 else "") \
                                                + currentItem.name,
                                            value=currentItem.statsStringShort(), inline=False)

            try:
                await sendChannel.send(embed=hangarEmbed)
                if sendDM:
                    await message.add_reaction(cfg.defaultEmojis.dmSent.sendable)
            except discord.Forbidden:
                await message.reply(mention_author=False, content=":x: I can't DM you, " + message.author.display_name \
                                            + "! Please enable DMs from users who are not friends.")

    textCommandsDB.register("hangar", cmd_hangar, 0, aliases=["hanger"], forceKeepArgsCasing=True, allowDM=True,
                        helpSection="loadout", signatureStr="**hangar** *[item-type]* *[page-number]*",
                        longHelp="Display the items stored in your hangar. Give an item type (ship/weapon/turret/module) to " \
                                    + "only list items of that type.")
    textCommandsDB.register("hangar", cmd_hangar, 2, aliases=["hanger"], forceKeepArgsCasing=True, allowDM=True,
                        signatureStr="**hangar** *[item-type]* *[page-number]* *[user]*", shortHelp="Administrators have permission to view " \
                                        + "the hangars of other users.", longHelp="Display the items stored in your hangar. " \
                                        + "Give an item type (ship/weapon/turret/module) to only list items of that type.\n" \
                                        + "Administrators have permission to view the hangars of other users.")


async def setup(bot: client.BasedClient):
    await bot.add_cog(UserLoadoutCog(bot))
