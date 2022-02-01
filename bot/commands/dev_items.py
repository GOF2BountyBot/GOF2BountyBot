import discord
import json

from . import commandsDB as botCommands
from .. import lib, botState
from ..cfg import cfg, bbData
from ..gameObjects.items import gameItem
from ..gameObjects.bounties.bounty import Bounty
from ..databases.bountyDB import divisionNameForLevel
from ..users import basedGuild


botCommands.addHelpSection(3, "items")


async def dev_cmd_give(message : discord.Message, args : str, isDM : bool):
    """developer command giving the provided user the provided item of the provided type.
    user must be either a mention or an ID or empty (to give the item to the calling user).
    type must be in cfg.validItemNames (but not 'all')
    item must be a json format description in line with the item's to and fromDict functions.

    :param discord.Message message: the discord message calling the command
    :param str args: string, containing either a user ID or mention or nothing (to give item to caller), followed by a string
                        from cfg.validItemNames (but not 'all'), followed by an item dictionary representation
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    if not lib.stringTyping.isInt(args.split(" ")[0]) and not lib.stringTyping.isMention(args.split(" ")[0]):
        requestedUser = botState.usersDB.getOrAddID(message.author.id)
        itemStr = args

    # otherwise get the specified user's bb object
    # [!] no validation is done.
    else:
        requestedUser = botState.usersDB.getOrAddID(
            int(args.split(" ")[0].lstrip("<@!").rstrip(">")))
        itemStr = args[len(args.split(" ")[0]) + 1:]

    itemType = itemStr.split(" ")[0].lower()

    itemDict = json.loads(itemStr[len(itemStr.split(" ")[0]):])
    if "type" not in itemDict:
        await message.reply(mention_author=False, content=":x: Please give a type in your item dictionary.")
        return

    if itemDict["type"] not in gameItem.subClassNames:
        await message.reply(mention_author=False, content=":x: Unknown gameItem subclass type: " + itemDict["type"])
        return


    if itemType == "all" or itemType not in cfg.validItemNames:
        await message.reply(mention_author=False, content=":x: Invalid item type arg - " + itemType)
        return

    newItem = gameItem.spawnItem(itemDict)

    requestedUser.getInactivesByName(itemType).addItem(newItem)

    await message.reply(mention_author=False, content=":white_check_mark: Given one '" + newItem.name + "' to **" \
                                + lib.discordUtil.userOrMemberName(botState.client.get_user(requestedUser.id),
                                                                                            message.guild) + "**!")

botCommands.register("give", dev_cmd_give, 3, forceKeepArgsCasing=True, allowDM=True, helpSection="items", useDoc=True)


async def dev_cmd_del_item(message : discord.Message, args : str, isDM : bool):
    """Delete an item in a requested user's inventory.
    arg 1: user mention or ID
    arg 2: item type (ship/weapon/module/turret)
    arg 3: item number (from $hangar)

    :param discord.Message message: the discord message calling the command
    :param str args: string containing a user mention, an item type and an index number, separated by a single space
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    if isDM:
        prefix = cfg.defaultCommandPrefix
    else:
        prefix = botState.guildsDB.getGuild(message.guild.id).commandPrefix

    argsSplit = args.split(" ")
    if len(argsSplit) < 3:
        await message.reply(mention_author=False, content=":x: Not enough arguments! Please provide a user, an item type " \
                                    + "(ship/weapon/module/turret) and an item number from `" + prefix + "hangar`")
        return
    if len(argsSplit) > 3:
        await message.reply(mention_author=False, content=":x: Too many arguments! Please only give a user, an item type " \
                                    + "(ship/weapon/module/turret), and an item number.")
        return

    item = argsSplit[1].rstrip("s")
    if item == "all" or item not in cfg.validItemNames:
        await message.reply(mention_author=False, content=":x: Invalid item name! Please choose from: ship, weapon, module or turret.")
        return

    if not (lib.stringTyping.isInt(argsSplit[0]) or lib.stringTyping.isMention(argsSplit[0])):
        await message.reply(mention_author=False, content=":x: Invalid user! ")
        return
    requestedBBUser = botState.usersDB.getOrAddID(
        int(argsSplit[0].lstrip("<@!").rstrip(">")))

    requestedUser = botState.client.get_user(requestedBBUser.id)
    if requestedUser is None:
        await message.reply(mention_author=False, content=":x: Unrecognised user!")
        return

    itemNum = argsSplit[2]
    if not lib.stringTyping.isInt(itemNum):
        await message.reply(mention_author=False, content=":x: Invalid item number!")
        return
    itemNum = int(itemNum)

    userItemInactives = requestedBBUser.getInactivesByName(item)
    if itemNum > userItemInactives.numKeys:
        await message.reply(mention_author=False, content=":x: Invalid item number! The user only has " + str(userItemInactives.numKeys) \
                                    + " " + item + "s.")
        return
    if itemNum < 1:
        await message.reply(mention_author=False, content=":x: Invalid item number! Must be at least 1.")
        return

    requestedItem = userItemInactives[itemNum - 1].item
    itemName = ""
    itemEmbed = None

    if item == "ship":
        itemName = requestedItem.getNameAndNick()
        itemEmbed = lib.discordUtil.makeEmbed(col=bbData.factionColours[requestedItem.manufacturer] \
                                                if requestedItem.manufacturer in bbData.factionColours else \
                                                bbData.factionColours["neutral"],
                                                thumb=requestedItem.icon if requestedItem.hasIcon else "")

        if requestedItem is None:
            itemEmbed.add_field(name="Item:",
                                value="None", inline=False)
        else:
            itemEmbed.add_field(name="Item:", value=requestedItem.getNameAndNick(
            ) + "\n" + requestedItem.statsStringNoItems(), inline=False)

            if requestedItem.getMaxPrimaries() > 0:
                itemEmbed.add_field(name="‎", value="__**Equipped Weapons**__ *" + str(len(
                    requestedItem.weapons)) + "/" + str(requestedItem.getMaxPrimaries()) + "*", inline=False)
                for weaponNum in range(1, len(requestedItem.weapons) + 1):
                    itemEmbed.add_field(name=str(weaponNum) + ". " + (requestedItem.weapons[weaponNum - 1].emoji.sendable \
                                            + " " if requestedItem.weapons[weaponNum - 1].hasEmoji else "") \
                                            + requestedItem.weapons[weaponNum - 1].name,
                                        value=requestedItem.weapons[weaponNum - 1].statsStringShort(), inline=True)

            if requestedItem.getMaxModules() > 0:
                itemEmbed.add_field(name="‎", value="__**Equipped Modules**__ *" + str(len(
                    requestedItem.modules)) + "/" + str(requestedItem.getMaxModules()) + "*", inline=False)
                for moduleNum in range(1, len(requestedItem.modules) + 1):
                    itemEmbed.add_field(name=str(moduleNum) + ". " + (requestedItem.modules[moduleNum - 1].emoji.sendable \
                                            + " " if requestedItem.modules[moduleNum - 1].hasEmoji else "") \
                                            + requestedItem.modules[moduleNum - 1].name,
                                        value=requestedItem.modules[moduleNum - 1].statsStringShort(), inline=True)

            if requestedItem.getMaxTurrets() > 0:
                itemEmbed.add_field(name="‎", value="__**Equipped Turrets**__ *" + str(len(
                    requestedItem.turrets)) + "/" + str(requestedItem.getMaxTurrets()) + "*", inline=False)
                for turretNum in range(1, len(requestedItem.turrets) + 1):
                    itemEmbed.add_field(name=str(turretNum) + ". " + (requestedItem.turrets[turretNum - 1].emoji.sendable \
                                            + " " if requestedItem.turrets[turretNum - 1].hasEmoji else "") \
                                            + requestedItem.turrets[turretNum - 1].name,
                                        value=requestedItem.turrets[turretNum - 1].statsStringShort(), inline=True)

    else:
        itemName = requestedItem.name + "\n" + requestedItem.statsStringShort()

    await message.reply(mention_author=False, content=":white_check_mark: One item deleted from " \
                                + lib.discordUtil.userOrMemberName(requestedUser, message.guild) \
                                + "'s inventory: " + itemName, embed=itemEmbed)
    userItemInactives.removeItem(requestedItem)

botCommands.register("del-item", dev_cmd_del_item, 3, allowDM=True, helpSection="items", useDoc=True)


async def dev_cmd_del_item_key(message : discord.Message, args : str, isDM : bool):
    """Delete ALL of an item in a requested user's inventory.
    arg 1: user mention or ID
    arg 2: item type (ship/weapon/module/turret)
    arg 3: item number (from $hangar)

    :param discord.Message message: the discord message calling the command
    :param str args: string containing a user mention, an item type and an index number, separated by a single space
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    if isDM:
        prefix = cfg.defaultCommandPrefix
    else:
        prefix = botState.guildsDB.getGuild(message.guild.id).commandPrefix
    argsSplit = args.split(" ")
    if len(argsSplit) < 3:
        await message.reply(mention_author=False, content=":x: Not enough arguments! Please provide a user, an item type " \
                                    + "(ship/weapon/module/turret) and an item number from `" + prefix + "hangar`")
        return
    if len(argsSplit) > 3:
        await message.reply(mention_author=False, content=":x: Too many arguments! Please only give a user, an item type " \
                                    + "(ship/weapon/module/turret), and an item number.")
        return

    item = argsSplit[1].rstrip("s")
    if item == "all" or item not in cfg.validItemNames:
        await message.reply(mention_author=False, content=":x: Invalid item name! Please choose from: ship, weapon, module or turret.")
        return

    if not (lib.stringTyping.isInt(argsSplit[0]) or lib.stringTyping.isMention(argsSplit[0])):
        await message.reply(mention_author=False, content=":x: Invalid user! ")
        return
    requestedBBUser = botState.usersDB.getOrAddID(
        int(argsSplit[0].lstrip("<@!").rstrip(">")))

    requestedUser = botState.client.get_user(requestedBBUser.id)
    if requestedUser is None:
        await message.reply(mention_author=False, content=":x: Unrecognised user!")
        return

    itemNum = argsSplit[2]
    if not lib.stringTyping.isInt(itemNum):
        await message.reply(mention_author=False, content=":x: Invalid item number!")
        return
    itemNum = int(itemNum)

    userItemInactives = requestedBBUser.getInactivesByName(item)
    if itemNum > userItemInactives.numKeys:
        await message.reply(mention_author=False, content=":x: Invalid item number! The user only has " + str(userItemInactives.numKeys) \
                                    + " " + item + "s.")
        return
    if itemNum < 1:
        await message.reply(mention_author=False, content=":x: Invalid item number! Must be at least 1.")
        return

    requestedItem = userItemInactives.keys[itemNum - 1]
    itemName = ""
    itemEmbed = None

    if item == "ship":
        itemName = requestedItem.getNameAndNick()
        itemEmbed = lib.discordUtil.makeEmbed(col=bbData.factionColours[requestedItem.manufacturer] \
                                                    if requestedItem.manufacturer in bbData.factionColours \
                                                    else bbData.factionColours["neutral"],
                                                thumb=requestedItem.icon if requestedItem.hasIcon else "")

        if requestedItem is None:
            itemEmbed.add_field(name="Item:",
                                value="None", inline=False)
        else:
            itemEmbed.add_field(name="Item:", value=requestedItem.getNameAndNick(
            ) + "\n" + requestedItem.statsStringNoItems(), inline=False)

            if requestedItem.getMaxPrimaries() > 0:
                itemEmbed.add_field(name="‎", value="__**Equipped Weapons**__ *" + str(len(
                    requestedItem.weapons)) + "/" + str(requestedItem.getMaxPrimaries()) + "*", inline=False)
                for weaponNum in range(1, len(requestedItem.weapons) + 1):
                    itemEmbed.add_field(name=str(weaponNum) + ". " + (requestedItem.weapons[weaponNum - 1].emoji.sendable \
                                            + " " if requestedItem.weapons[weaponNum - 1].hasEmoji else "") \
                                            + requestedItem.weapons[weaponNum - 1].name,
                                        value=requestedItem.weapons[weaponNum - 1].statsStringShort(), inline=True)

            if requestedItem.getMaxModules() > 0:
                itemEmbed.add_field(name="‎", value="__**Equipped Modules**__ *" + str(len(
                    requestedItem.modules)) + "/" + str(requestedItem.getMaxModules()) + "*", inline=False)
                for moduleNum in range(1, len(requestedItem.modules) + 1):
                    itemEmbed.add_field(name=str(moduleNum) + ". " + (requestedItem.modules[moduleNum - 1].emoji.sendable \
                                            + " " if requestedItem.modules[moduleNum - 1].hasEmoji else "") \
                                            + requestedItem.modules[moduleNum - 1].name,
                                        value=requestedItem.modules[moduleNum - 1].statsStringShort(), inline=True)

            if requestedItem.getMaxTurrets() > 0:
                itemEmbed.add_field(name="‎", value="__**Equipped Turrets**__ *" + str(len(
                    requestedItem.turrets)) + "/" + str(requestedItem.getMaxTurrets()) + "*", inline=False)
                for turretNum in range(1, len(requestedItem.turrets) + 1):
                    itemEmbed.add_field(name=str(turretNum) + ". " + (requestedItem.turrets[turretNum - 1].emoji.sendable \
                                            + " " if requestedItem.turrets[turretNum - 1].hasEmoji else "") \
                                            + requestedItem.turrets[turretNum - 1].name,
                                        value=requestedItem.turrets[turretNum - 1].statsStringShort(), inline=True)

    else:
        itemName = requestedItem.name + "\n" + requestedItem.statsStringShort()

    if requestedItem not in userItemInactives.items:
        userItemInactives.keys.remove(requestedItem)
        userItemInactives.numKeys -= 1
        await message.reply(mention_author=False, content=":white_check_mark: **Erroneous key** deleted from " \
                                    + lib.discordUtil.userOrMemberName(requestedUser, message.guild) \
                                    + "'s inventory: " + itemName, embed=itemEmbed)
    else:
        itemCount = userItemInactives.items[requestedItem].count
        del userItemInactives.items[requestedItem]
        userItemInactives.keys.remove(requestedItem)
        userItemInactives.numKeys -= 1
        await message.reply(mention_author=False, content=":white_check_mark: " + str(itemCount) + " item(s) deleted from " \
                                    + lib.discordUtil.userOrMemberName(requestedUser, message.guild) \
                                    + "'s inventory: " + itemName, embed=itemEmbed)

botCommands.register("del-item-key", dev_cmd_del_item_key, 3, allowDM=True, helpSection="items", useDoc=True)


async def dev_cmd_refreshshop(message : discord.Message, args : str, isDM : bool):
    """Refresh the shop stock of the current guild. Does not reset the shop stock cooldown.
    To refresh all divisions, give no arguments.
    To refresh a division to a specific level, give the name of the division followed by the level.
    To refresh just one division to a random level, just give the division name.

    :param discord.Message message: the discord message calling the command
    :param str args: nothing, a division name, or a division name and a level and optionally '-f'
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    if not args:
        await message.reply("Give a division and optionally a tl, or 'all'.")
        return

    guild: basedGuild.BasedGuild = botState.guildsDB.getGuild(message.guild.id)
    if guild.shopsDisabled:
        await message.reply(mention_author=False, content=":x: This guild's shops are disabled.")
        return

    if args.endswith("-f"):
        args = args[:-2].rstrip()
        forceInvalidTL = True
    else:
        forceInvalidTL = False

    if args == "all":
        allShops = True
        divName = ""
        level = -1

    else:
        allShops = False

        argsSplit = args.split(" ")
        if len(argsSplit) == 1:
            divName = args
            level = -1
        else:
            divName = " ".join(argsSplit[:-1])
            tlStr = argsSplit[-1]
            if not lib.stringTyping.isInt(tlStr):
                await message.reply("Invalid tl: " + tlStr)
                return
            level = int(tlStr)
            if level < cfg.minTechLevel or level > cfg.maxTechLevel:
                        await message.reply(mention_author=False,
                                            content=f"Invalid tech level! Must be between {cfg.minTechLevel} and {cfg.maxTechLevel}.")
                        return

        if not divName and level != -1:
            divName = divisionNameForLevel(level)

        if divName not in cfg.bountyDivisionNames:
            await message.reply("Unknown division name: " + divName)
            return
    
    if allShops:
        for shop in guild.divisionShops.values():
            shop.refreshStock()
    else:
        if level == -1:
            guild.divisionShops[divName].refreshStock()
        else:
            if not forceInvalidTL and (level < guild.divisionShops[divName].minLevel or level > guild.divisionShops[divName].maxLevel):
                await message.reply(f"Invalid level. This shop's tech level range is {guild.divisionShops[divName].minLevel} - {guild.divisionShops[divName].maxLevel}. To refresh a shop outside of its normal range, give `-f`.")
                return
            guild.divisionShops[divName].refreshStock(level)
    
    await guild.announceNewShopStock()

botCommands.register("refreshshop", dev_cmd_refreshshop, 3, allowDM=False, helpSection="items", useDoc=True)


async def dev_cmd_debug_hangar(message : discord.Message, args : str, isDM : bool):
    """developer command printing the requested user's hangar, including object memory addresses.

    :param discord.Message message: the discord message calling the command
    :param str args: string containing a user mention or ID
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    if not (lib.stringTyping.isInt(args) or lib.stringTyping.isMention(args)):
        await message.reply(mention_author=False, content=":x: Invalid user!")
        return

    requestedUser = botState.client.get_user(int(args.lstrip("<@!").rstrip(">")))
    if requestedUser is None:
        await message.reply(mention_author=False, content=":x: Unrecognised user!")
        return

    if not botState.usersDB.idExists(requestedUser.id):
        await message.reply(mention_author=False, content="User has not played yet!")
        return

    requestedBBUser = botState.usersDB.getUser(requestedUser.id)
    maxPerPage = cfg.maxItemsPerHangarPageAll

    maxPage = requestedBBUser.numInventoryPages("all", maxPerPage)
    if maxPage == 0:
        await message.reply(mention_author=False, content=":x: The requested pilot doesn't have any items!")
        return

    itemTypes = ("ship", "weapon", "module", "turret")
    for itemType in itemTypes:
        itemInv = requestedBBUser.getInactivesByName(itemType)
        await message.reply(mention_author=False, content=itemType.upper() + " KEYS: " + str(itemInv.keys) + "\n" + itemType.upper() \
                                    + " LISTINGS: " + str(list(itemInv.items.keys())))

    for page in range(1, maxPage + 1):

        hangarEmbed = lib.discordUtil.makeEmbed(titleTxt="Hangar", desc=requestedUser.mention,
                                                col=bbData.factionColours["neutral"],
                                                footerTxt="All items - page " + str(page) + "/" \
                                                    + str(requestedBBUser.numInventoryPages("all", maxPerPage)),
                                                thumb=requestedUser.avatar_url_as(size=64))
        firstPlace = maxPerPage * (page - 1) + 1

        for itemType in itemTypes:
            itemInv = requestedBBUser.getInactivesByName(itemType)
            displayedItems = []

            for itemNum in range(firstPlace, requestedBBUser.lastItemNumberOnPage(itemType, page, maxPerPage) + 1):
                if itemNum == firstPlace:
                    hangarEmbed.add_field(
                        name="‎", value="__**Stored " + itemType.title() + "s**__", inline=False)
                currentItem = itemInv.keys[itemNum - 1]
                itemStored = currentItem in itemInv.items
                currentItemCount = itemInv.numStored(
                    currentItem) if itemStored else 0
                displayedItems.append(currentItem)
                if itemType == "ship":
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

            expectedKeys = itemInv.items.keys()
            for itemNum in range(len(expectedKeys)):
                itemKey = itemInv.items.expectedKeys[itemNum]
                if itemKey not in displayedItems:
                    currentItemCount = itemInv.items[itemKey].count
                    displayedItems.append(itemKey)
                    if itemType == "ship":
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

        await message.reply(mention_author=False, embed=hangarEmbed)


botCommands.register("debug-hangar", dev_cmd_debug_hangar, 3, allowDM=True, helpSection="items", useDoc=True)


# TODO: Move to dev_economy
async def dev_cmd_crim_value(message : discord.Message, args : str, isDM : bool):
    """⚠ WARNING: MARKED FOR CHANGE ⚠
    The following function is provisional and marked as planned for overhaul.
    Details: The command output is finalised. However, the inner workings of the command are to be replaced with attribute
    getters. It is inefficient to calculate total value measurements on every call, so current totals should be cached in
    object attributes whenever modified.

    print the total value of the specified criminal.

    :param discord.Message message: the discord message calling the command
    :param str args: string containing a criminal name.
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    # If no user is specified, send the balance of the calling user
    if args == "":
        await message.reply(":x: Please give a criminal!")

    # If a user is specified
    else:
        callingBBGuild = botState.guildsDB.getGuild(message.guild.id)
        if callingBBGuild.bountiesDisabled:
            await message.channel.send(":x: This server has bounties disabled!")
            return

        # look up the criminal object
        criminalName = args.title()

        # report unrecognised criminal names
        if not callingBBGuild.bountiesDB.bountyNameExists(criminalName, noEscapedCrim=True):
            errmsg = ":x: That pilot is not currently wanted!"

            if lib.stringTyping.isMention(criminalName):
                errmsg += "\n:warning: **Don't tag users**, use their name and ID number like so: `" \
                            + callingBBGuild.commandPrefix + "loadout criminal Trimatix#2244`"

            await message.channel.send(errmsg)
            return

        bountyObj: Bounty = callingBBGuild.bountiesDB.getBounty(criminalName)

        # send the user's balance
        await message.reply(mention_author=False, content=":moneybag: **" + criminalName \
                                    + "**'s loadout has a total value of **" \
                                    + str(bountyObj.activeShip.getValue()) + " Credits**.")

botCommands.register("crim-value", dev_cmd_crim_value, 3, forceKeepArgsCasing=True, allowDM=False, helpSection="items",
                        signatureStr="**crim-value** *[criminal name]*",
                        shortHelp="Get the total value of a criminal's loadout.")
