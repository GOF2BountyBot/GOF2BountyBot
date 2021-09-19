import discord # type: ignore[import]
import json

from . import commandsDB as botCommands
from .. import lib, botState
from ..lib.stringTyping import commaSplitNum
from ..cfg import cfg, bbData
from ..gameObjects.items import gameItem
from ..users.basedUser import BasedUser
from ..gameObjects.lomaShop import LomaShop
from ..gameObjects.inventories.inventoryListing import DiscountableItemListing
from ..gameObjects.itemDiscount import ItemDiscount


botCommands.addHelpSection(3, "loma")

async def dev_cmd_loma_give(message : discord.Message, args : str, isDM : bool):
    """developer command spawning the described item, and placing it in the given user's loma shop.
    user must be either a mention or an ID or empty (to give the item to the calling user).
    type must be in cfg.validItemNames (but not 'all')
    item must be a json format description in line with the item's to and fromDict functions.

    :param discord.Message message: the discord message calling the command
    :param str args: string, containing either a user ID or mention or nothing (to give item to caller), followed by a string
                        from cfg.validItemNames (but not 'all'), followed by a serialized item
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    requestedUser: BasedUser = None
    argsSplit = args.split(" ")
    if not lib.stringTyping.isInt(argsSplit[0]) and not lib.stringTyping.isMention(argsSplit[0]):
        requestedUser = botState.usersDB.getOrAddID(message.author.id)
        itemStr = args

    # otherwise get the specified user's bb object
    # [!] no validation is done.
    else:
        requestedUser = botState.usersDB.getOrAddID(int(argsSplit[0].lstrip("<@!").rstrip(">")))
        itemStr = args[len(argsSplit[0]) + 1:]

    itemType = itemStr.split(" ")[0].lower()
    itemDict = json.loads(itemStr[len(itemStr.split(" ")[0]):])

    if "type" not in itemDict:
        await message.channel.send(":x: Please give a type in your item dictionary.")
        return

    if itemDict["type"] not in gameItem.subClassNames:
        await message.channel.send(":x: Unknown gameItem subclass type: " + itemDict["type"])
        return


    if itemType == "all" or itemType not in cfg.validItemNames:
        await message.channel.send(":x: Invalid item type arg - " + itemType)
        return

    newItem = gameItem.spawnItem(itemDict)

    if requestedUser.loma is None:
        requestedUser.loma = LomaShop()
    itemStock = requestedUser.loma.getStockByName(itemType)
    itemStock.addItem(newItem)

    await message.channel.send(":white_check_mark: Given one '" + newItem.name + "' to **" \
                                + lib.discordUtil.userOrMemberName(botState.client.get_user(requestedUser.id),
                                                                                            message.guild) + "**!")

botCommands.register("loma-give", dev_cmd_loma_give, 3, forceKeepArgsCasing=True, allowDM=True, helpSection="loma", useDoc=True)


async def dev_cmd_loma_give_discount(message : discord.Message, args : str, isDM : bool):
    """developer command the described item item discount, and placing it in the given user's loma shop, for the described item.
    user must be either a mention or an ID or empty (to give the item to the calling user).
    type must be in cfg.validItemNames (but not 'all')
    item number must be a number as shown in dev_cmd_debug_loma
    item discount must be a json format description in line with ItemDiscount.fromDict.

    :param discord.Message message: the discord message calling the command
    :param str args: string, containing either a user ID or mention or nothing (to give item to caller), followed by a string
                        from cfg.validItemNames (but not 'all'), followed by an item number from debug_loma, and a serialized ItemDiscount
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    requestedUser: BasedUser = None
    argsSplit = args.split(" ")
    if not lib.stringTyping.isInt(argsSplit[0]) and not lib.stringTyping.isMention(argsSplit[0]):
        requestedUser = botState.usersDB.getOrAddID(message.author.id)
        itemStr = args

    # otherwise get the specified user's bb object
    # [!] no validation is done.
    else:
        requestedUser = botState.usersDB.getOrAddID(int(argsSplit[0].lstrip("<@!").rstrip(">")))
        itemStr = args[len(argsSplit[0]) + 1:]

    if requestedUser.loma is None or requestedUser.loma.isEmpty():
        await message.author.send("That user has no items in loma!")
        return

    itemStrSplit = itemStr.split(" ")
    itemType = itemStrSplit[0].lower()
    itemNum = int(itemStrSplit[1])
    discountDict = json.loads(itemStr[len(itemStrSplit[0]) + len(itemStrSplit[1]) + 2:])

    if itemType == "all" or itemType not in cfg.validItemNames:
        await message.channel.send(":x: Invalid item type arg - " + itemType)
        return

    itemListing: DiscountableItemListing = requestedUser.loma.getStockByName(itemType)[itemNum - 1]
    newDiscount = ItemDiscount.fromDict(discountDict)
    itemListing.pushDiscount(newDiscount)

    await message.channel.send(f":white_check_mark: Given one '{newDiscount.toDict()}' to **" \
                                + lib.discordUtil.userOrMemberName(botState.client.get_user(requestedUser.id),
                                                                    message.guild) + "**, for their " \
                                + itemListing.item.name + ".")

botCommands.register("loma-give-discount", dev_cmd_loma_give_discount, 3, forceKeepArgsCasing=True, allowDM=True, helpSection="loma", useDoc=True)


async def dev_cmd_debug_loma(message : discord.Message, args : str, isDM : bool):
    """developer command printing the requested user's loma, including object memory addresses.

    :param discord.Message message: the discord message calling the command
    :param str args: string containing a user mention or ID
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    if not (lib.stringTyping.isInt(args) or lib.stringTyping.isMention(args)):
        await message.author.send(":x: Invalid user!")
        return

    requestedUser = botState.client.get_user(int(args.lstrip("<@!").rstrip(">")))
    if requestedUser is None:
        await message.author.send(":x: Unrecognised user!")
        return

    if not botState.usersDB.idExists(requestedUser.id):
        await message.author.send("User has not played yet!")
        return

    requestedBBUser: BasedUser = botState.usersDB.getUser(requestedUser.id)
    if requestedBBUser.loma is None:
        await message.author.send(":x: The requested pilot has no loma!")
        return
    if requestedBBUser.loma.isEmpty():
        await message.author.send(":x: The loma is empty!")
        return





    shopEmbed = lib.discordUtil.makeEmbed(titleTxt="Loma",
                                            desc=requestedUser.mention,
                                            footerTxt="All items",
                                            thumb=requestedUser.avatar_url_as(size=64))

    itemTypes = ("ship", "weapon", "module", "turret", "tool")
    for itemType in itemTypes:
        itemInv = requestedBBUser.loma.getStockByName(itemType)
        await message.author.send(itemType.upper() + " KEYS: " + str(itemInv.keys) + "\n" + itemType.upper() \
                                    + " LISTINGS: " + str(list(itemInv.items.keys())))

    for currentItemType in itemTypes:
        currentStock = requestedBBUser.loma.getStockByName(currentItemType)
        for itemNum in range(1, currentStock.numKeys + 1):
            if itemNum == 1:
                shopEmbed.add_field(name="‎", value="__**" + currentItemType.title() + "s**__", inline=False)

            try:
                currentItem = currentStock[itemNum - 1].item
            except KeyError:
                try:
                    botState.logger.log("dev_loma", "dev_cmd_debug_loma",
                                        "Requested " + currentItemType + " '" + currentStock.keys[itemNum-1].name \
                                            + "' (index " + str(itemNum-1) \
                                            + "), which was not found in the shop stock",
                                        category="shop", eventType="UNKWN_KEY")
                except IndexError:
                    break
                except AttributeError as e:
                    keysStr = ""
                    for item in currentStock.items:
                        keysStr += str(item) + ", "
                    botState.logger.log("dev_loma", "dev_cmd_debug_loma",
                                        "Unexpected type in " + currentItemType + "sStock KEYS, index " \
                                            + str(itemNum-1) + ". Got " \
                                            + type(currentStock.keys[itemNum-1]).__name__ + ".\nInventory keys: " \
                                            + keysStr[:-2],
                                        category="shop", eventType="INVTY_KEY_TYPE")
                    shopEmbed.add_field(name=str(itemNum) + ". **⚠ #INVALID-ITEM# '" \
                                            + currentStock.keys[itemNum-1] + "'",
                                        value="Do not attempt to buy. Could cause issues.", inline=True)
                    continue
                shopEmbed.add_field(name=str(itemNum) + ". **⚠ #INVALID-ITEM# '" \
                                        + currentStock.keys[itemNum-1].name + "'",
                                    value="Do not attempt to buy. Could cause issues.", inline=True)
                continue
            
            itemListing: DiscountableItemListing = currentStock.getListing(currentItem)
            currentItemCount = itemListing.count
            if itemListing.discounts:
                discountedValue = int(currentItem.value * itemListing.discounts[0].mult)
                discountAmountStr = lib.stringTyping.formatMultiplier(itemListing.discounts[0].mult)
                valueStr = f"~~{commaSplitNum(currentItem.value)}~~ {commaSplitNum(discountedValue)}" \
                            + f" Credits\n*{discountAmountStr} : {itemListing.discounts[0].desc}*\n"
            else:
                valueStr = f"{commaSplitNum(currentItem.value)} Credits\n"
            shopEmbed.add_field(name=str(itemNum) + ". " \
                                    + (currentItem.emoji.sendable + " " if currentItem.hasEmoji else "") \
                                    + ((" `(" + str(currentItemCount) + ")` ") if currentItemCount > 1 else "") \
                                    + "**" + currentItem.name + "**",
                                value=valueStr + currentItem.statsStringShort(), inline=True)

    try:
        await message.author.send(embed=shopEmbed)
    except discord.Forbidden:
        await message.channel.send(":x: I can't DM you, " + message.author.display_name \
            + "! Please enable DMs from users who are not friends.")
        return
    await message.add_reaction(cfg.defaultEmojis.dmSent.sendable)

botCommands.register("debug-loma", dev_cmd_debug_loma, 3, allowDM=True, helpSection="loma", useDoc=True)


async def dev_cmd_del_loma_item(message : discord.Message, args : str, isDM : bool):
    """Delete an item in a requested user's loma.
    arg 1: user mention or ID
    arg 2: item type (ship/weapon/module/turret)
    arg 3: item number (from $debug-loma)

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
        await message.channel.send(":x: Not enough arguments! Please provide a user, an item type " \
                                    + "(ship/weapon/module/turret) and an item number from `" + prefix + "debug-loma`")
        return
    if len(argsSplit) > 3:
        await message.channel.send(":x: Too many arguments! Please only give a user, an item type " \
                                    + "(ship/weapon/module/turret), and an item number.")
        return

    itemCategory = argsSplit[1].rstrip("s")
    if itemCategory == "all" or itemCategory not in cfg.validItemNames:
        await message.channel.send(":x: Invalid item name! Please choose from: ship, weapon, module or turret.")
        return

    if not (lib.stringTyping.isInt(argsSplit[0]) or lib.stringTyping.isMention(argsSplit[0])):
        await message.channel.send(":x: Invalid user! ")
        return
    requestedBBUser: BasedUser = botState.usersDB.getOrAddID(int(argsSplit[0].lstrip("<@!").rstrip(">")))

    requestedUser = botState.client.get_user(requestedBBUser.id)
    if requestedUser is None:
        await message.channel.send(":x: Unrecognised user!")
        return

    itemNum = argsSplit[2]
    if not lib.stringTyping.isInt(itemNum):
        await message.channel.send(":x: Invalid item number!")
        return
    itemNum = int(itemNum)

    if requestedBBUser.loma is None or requestedBBUser.loma.isEmpty():
        await message.channel.send(":x: Requested user has no loma items!")
        return

    lomaItemStock = requestedBBUser.loma.getStockByName(itemCategory)
    if itemNum > lomaItemStock.numKeys:
        await message.channel.send(":x: Invalid item number! The user only has " + str(lomaItemStock.numKeys) \
                                    + " " + itemCategory + "s.")
        return
    if itemNum < 1:
        await message.channel.send(":x: Invalid item number! Must be at least 1.")
        return

    requestedItem = lomaItemStock[itemNum - 1].item
    itemName = ""
    itemEmbed = None

    if itemCategory == "ship":
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

    await message.channel.send(":white_check_mark: One item deleted from " \
                                + lib.discordUtil.userOrMemberName(requestedUser, message.guild) \
                                + "'s loma: " + itemName, embed=itemEmbed)
    lomaItemStock.removeItem(requestedItem)

    # Destroy Loma object if it is now empty
    if requestedBBUser.loma.isEmpty():
        requestedBBUser.loma = None

botCommands.register("del-loma-item", dev_cmd_del_loma_item, 3, allowDM=True, helpSection="loma", useDoc=True)


async def dev_cmd_del_loma_item_key(message : discord.Message, args : str, isDM : bool):
    """Delete ALL of an item in a requested user's loma.
    arg 1: user mention or ID
    arg 2: item type (ship/weapon/module/turret)
    arg 3: item number (from $debug-loma)

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
        await message.channel.send(":x: Not enough arguments! Please provide a user, an item type " \
                                    + "(ship/weapon/module/turret) and an item number from `" + prefix + "debug-loma`")
        return
    if len(argsSplit) > 3:
        await message.channel.send(":x: Too many arguments! Please only give a user, an item type " \
                                    + "(ship/weapon/module/turret), and an item number.")
        return

    itemCategory = argsSplit[1].rstrip("s")
    if itemCategory == "all" or itemCategory not in cfg.validItemNames:
        await message.channel.send(":x: Invalid item name! Please choose from: ship, weapon, module or turret.")
        return

    if not (lib.stringTyping.isInt(argsSplit[0]) or lib.stringTyping.isMention(argsSplit[0])):
        await message.channel.send(":x: Invalid user! ")
        return
    requestedBBUser: BasedUser = botState.usersDB.getOrAddID(int(argsSplit[0].lstrip("<@!").rstrip(">")))

    requestedUser = botState.client.get_user(requestedBBUser.id)
    if requestedUser is None:
        await message.channel.send(":x: Unrecognised user!")
        return

    itemNum = argsSplit[2]
    if not lib.stringTyping.isInt(itemNum):
        await message.channel.send(":x: Invalid item number!")
        return
    itemNum = int(itemNum)

    if requestedBBUser.loma is None or requestedBBUser.loma.isEmpty():
        await message.channel.send(":x: Requested user has no loma items!")
        return

    lomaItemStock = requestedBBUser.loma.getStockByName(itemCategory)
    if itemNum > lomaItemStock.numKeys:
        await message.channel.send(":x: Invalid item number! The user only has " + str(lomaItemStock.numKeys) \
                                    + " " + itemCategory + "s.")
        return
    if itemNum < 1:
        await message.channel.send(":x: Invalid item number! Must be at least 1.")
        return

    requestedItem = lomaItemStock.keys[itemNum - 1]
    itemName = ""
    itemEmbed = None

    if itemCategory == "ship":
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

    if requestedItem not in lomaItemStock.items:
        lomaItemStock.keys.remove(requestedItem)
        lomaItemStock.numKeys -= 1
        await message.channel.send(":white_check_mark: **Erroneous key** deleted from " \
                                    + lib.discordUtil.userOrMemberName(requestedUser, message.guild) \
                                    + "'s loma: " + itemName, embed=itemEmbed)
    else:
        itemCount = lomaItemStock.items[requestedItem].count
        del lomaItemStock.items[requestedItem]
        lomaItemStock.keys.remove(requestedItem)
        lomaItemStock.numKeys -= 1
        await message.channel.send(":white_check_mark: " + str(itemCount) + " item(s) deleted from " \
                                    + lib.discordUtil.userOrMemberName(requestedUser, message.guild) \
                                    + "'s loma: " + itemName, embed=itemEmbed)

    # Destroy Loma object if it is now empty
    if requestedBBUser.loma.isEmpty():
        requestedBBUser.loma = None

botCommands.register("del-loma-item-key", dev_cmd_del_loma_item_key, 3, allowDM=True, helpSection="loma", useDoc=True)


async def dev_cmd_del_loma_discount(message : discord.Message, args : str, isDM : bool):
    """Delete an item in a requested user's loma.
    arg 1: user mention or ID
    arg 2: item type (ship/weapon/module/turret)
    arg 3: item number (from $debug-loma)
    arg 4: discount index

    :param discord.Message message: the discord message calling the command
    :param str args: string containing a user mention, an item type and an index number, separated by a single space
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    if isDM:
        prefix = cfg.defaultCommandPrefix
    else:
        prefix = botState.guildsDB.getGuild(message.guild.id).commandPrefix

    argsSplit = args.split(" ")
    if len(argsSplit) < 4:
        await message.channel.send(":x: Not enough arguments! Please provide a user, an item type " \
                                    + "(ship/weapon/module/turret) and an item number from `" + prefix + "debug-loma`, " \
                                    + "and a discount index")
        return
    if len(argsSplit) > 4:
        await message.channel.send(":x: Too many arguments! Please only give a user, an item type " \
                                    + "(ship/weapon/module/turret), and an item number, " \
                                    + "and a discount index")
        return

    itemCategory = argsSplit[1].rstrip("s")
    if itemCategory == "all" or itemCategory not in cfg.validItemNames:
        await message.channel.send(":x: Invalid item name! Please choose from: ship, weapon, module or turret.")
        return

    if not (lib.stringTyping.isInt(argsSplit[0]) or lib.stringTyping.isMention(argsSplit[0])):
        await message.channel.send(":x: Invalid user! ")
        return
    requestedBBUser: BasedUser = botState.usersDB.getOrAddID(int(argsSplit[0].lstrip("<@!").rstrip(">")))

    requestedUser = botState.client.get_user(requestedBBUser.id)
    if requestedUser is None:
        await message.channel.send(":x: Unrecognised user!")
        return

    itemNum = argsSplit[2]
    if not lib.stringTyping.isInt(itemNum):
        await message.channel.send(":x: Invalid item number!")
        return
    itemNum = int(itemNum)

    discountNum = argsSplit[-1]
    if not lib.stringTyping.isInt(discountNum):
        await message.channel.send(":x: Invalid discount index!")
        return
    discountNum = int(discountNum)

    if requestedBBUser.loma is None or requestedBBUser.loma.isEmpty():
        await message.channel.send(":x: Requested user has no loma items!")
        return

    lomaItemStock = requestedBBUser.loma.getStockByName(itemCategory)
    if itemNum > lomaItemStock.numKeys:
        await message.channel.send(":x: Invalid item number! The user only has " + str(lomaItemStock.numKeys) \
                                    + " " + itemCategory + "s.")
        return
    if itemNum < 1:
        await message.channel.send(":x: Invalid item number! Must be at least 1.")
        return

    itemListing = lomaItemStock[itemNum - 1]

    if discountNum > len(itemListing.discounts) - 1:
        await message.channel.send(":x: Invalid discount number! The user only has " + str(itemListing.discounts) \
                                    + " discounts for that item.")
        return
    if itemNum < 0:
        await message.channel.send(":x: Invalid item number! Must be at least 0.")
        return

    requestedItem = itemListing.item
    itemName = ""
    itemEmbed = None

    discountObj = itemListing.discounts[discountNum]

    if itemCategory == "ship":
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

    await message.channel.send(f":white_check_mark: Discount '{discountObj.toDict()}' from " \
                                + lib.discordUtil.userOrMemberName(requestedUser, message.guild) \
                                + "'s loma: " + itemName, embed=itemEmbed)
    lomaItemStock.removeItem(requestedItem)

botCommands.register("del-loma-discount", dev_cmd_del_loma_discount, 3, allowDM=True, helpSection="loma", useDoc=True)
