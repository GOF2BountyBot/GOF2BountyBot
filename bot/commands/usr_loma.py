import discord

from . import commandsDB as bbCommands
from .. import botState, lib
from ..lib.stringTyping import commaSplitNum
from ..cfg import cfg
from ..gameObjects.inventories.inventory import DiscountableTypeRestrictedInventory
from ..users.basedUser import BasedUser
from ..gameObjects.inventories.inventoryListing import DiscountableItemListing


bbCommands.addHelpSection(0, "loma")

async def cmd_loma_buy(message : discord.Message, args : str, isDM : bool):
    """Buy the item of the given item type, at the given index, from the user's loma shop.
    The typical "sell" and "transfer" shortcut args from cmd_buy are not compatible with this command.

    :param discord.Message message: the discord message calling the command
    :param str args: string containing an item type and an index number
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    if not botState.usersDB.idExists(message.author.id):
        await message.channel.send("The Loma pirates do not have any items to sell!")
        return

    requestedBUser: BasedUser = botState.usersDB.getUser(message.author.id)
    if requestedBUser.loma is None or requestedBUser.loma.isEmpty():
        await message.channel.send("The Loma pirates do not have any items to sell!")
        return

    commandPrefix = cfg.defaultCommandPrefix if isDM else botState.guildsDB.getGuild(message.guild.id).commandPrefix

    argsSplit = args.split(" ")
    if len(argsSplit) < 2:
        await message.channel.send(":x: Not enough arguments! Please provide both an item type (ship/weapon/module/turret) " \
                                    + f"and an item number from `{commandPrefix}loma`")
        return
    if len(argsSplit) > 4:
        await message.channel.send(":x: Too many arguments! Please only give an item type (ship/weapon/module/turret) " \
                                    + f"and an item number from `{commandPrefix}loma`")
        return

    itemCategory = argsSplit[0].rstrip("s")
    if itemCategory == "all" or itemCategory not in cfg.validItemNames:
        await message.channel.send(":x: Invalid item name! Please choose from: ship, weapon, module, turret or tool.")
        return

    itemNum = argsSplit[1]
    if not lib.stringTyping.isInt(itemNum):
        await message.channel.send(":x: Invalid item number!")
        return

    itemNum = int(itemNum)
    shopItemStock: DiscountableTypeRestrictedInventory = requestedBUser.loma.getStockByName(itemCategory)
    if itemNum > shopItemStock.numKeys:
        if shopItemStock.numKeys == 0:
            await message.channel.send(":x: The Loma pirates don't have any " + itemCategory + "s in stock!")
        else:
            await message.channel.send(":x: Invalid item number! Loma currently has " + str(shopItemStock.numKeys) \
                                        + " " + itemCategory + "(s).")
        return

    if itemNum < 1:
        await message.channel.send(":x: Invalid item number! Must be at least 1.")
        return

    itemListing: DiscountableItemListing = shopItemStock[itemNum - 1]
    requestedItem = itemListing.item

    if not requestedBUser.loma.userCanAffordItemObj(requestedBUser, requestedItem):
        await message.channel.send(":x: You can't afford that item!")
        return

    _, valueDiscount = shopItemStock.removeItemAndDiscount(requestedItem)
    requestedBUser.credits -= int(requestedItem.value * valueDiscount)
    requestedBUser.getInactivesByName(itemCategory).addItem(requestedItem)

    await message.channel.send(":moneybag: Congratulations on your new **" + requestedItem.name \
                                + "**! \n\nYour balance is now: **" + str(requestedBUser.credits) + " credits**.")

    # Destroy Loma object if it is now empty
    if requestedBUser.loma.isEmpty():
        requestedBUser.loma = None

bbCommands.register("loma buy", cmd_loma_buy, 0, allowDM=True, helpSection="loma",
                        signatureStr="**loma buy <item-type> <item-number>**",
                        shortHelp="Buy the requested item from the pirates at Loma. Item numbers can be seen in `loma`.",
                        longHelp="Buy the requested item from the pirates at Loma. Item numbers are shown next to items in " \
                                    + "`loma`. The `sell` and `transfer` options from `shop buy` do not apply to loma.")


async def cmd_loma(message : discord.Message, args : str, isDM : bool):
    """list the items currently available in the user's loma shop.
    Can specify an item type to list. TODO: Make specified item listings more detailed as in !bb bounties

    :param discord.Message message: the discord message calling the command
    :param str args: either empty string, or one of bbConfig.validItemNames
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    commandPrefix = cfg.defaultCommandPrefix if isDM else botState.guildsDB.getGuild(message.guild.id).commandPrefix
    if args.startswith("buy"):
        await cmd_loma_buy(message, args[4:].lstrip(" "), isDM)
        return
    elif args.startswith("sell"):
        await message.channel.send(":x: The Loma pirates do not buy items, they only sell.\nFor private item storage," \
                                    f" consider `{commandPrefix}kaamo`. If you need money, then `{commandPrefix}sell` to " \
                                    f"a server's `{commandPrefix}shop`.")
        return

    item = "all"
    if args.rstrip("s") in cfg.validItemNames:
        item = args.rstrip("s")
    elif args != "":
        await message.channel.send(":x: Invalid item type! (ship/weapon/module/turret/tool/all)")
        return

    sendChannel = None
    sendDM = False
    callingBBUser: BasedUser = botState.usersDB.getOrAddID(message.author.id)

    if item == "all":
        if message.author.dm_channel is None:
            await message.author.create_dm()
        if message.author.dm_channel is None:
            await message.channel.send(":x: I can't DM you, " + message.author.display_name \
                                        + "! Please enable DMs from users who are not friends.")
            return
        else:
            sendChannel = message.author.dm_channel
            sendDM = True
    else:
        sendChannel = message.channel

    shopEmbed = lib.discordUtil.makeEmbed(titleTxt="Loma",
                                            desc=message.author.mention,
                                            footerTxt="All items" if item == "all" else (item + "s").title(),
                                            thumb=message.author.avatar_url_as(size=64))

    if callingBBUser.loma is None or callingBBUser.loma.isEmpty():
        shopEmbed.add_field(name="‎", value="No items currently available.")
    else:
        for currentItemType in ["ship", "weapon", "module", "turret", "tool"]:
            if item in ["all", currentItemType]:
                currentStock = callingBBUser.loma.getStockByName(currentItemType)
                for itemNum in range(1, currentStock.numKeys + 1):
                    if itemNum == 1:
                        shopEmbed.add_field(name="‎", value="__**" + currentItemType.title() + "s**__", inline=False)

                    try:
                        currentItem = currentStock[itemNum - 1].item
                    except KeyError:
                        try:
                            botState.logger.log("Main", "cmd_loma",
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
                            botState.logger.log("Main", "cmd_loma",
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
        await sendChannel.send(embed=shopEmbed)
    except discord.Forbidden:
        await message.channel.send(":x: I can't DM you, " + message.author.display_name \
            + "! Please enable DMs from users who are not friends.")
        return
    if sendDM:
        await message.add_reaction(cfg.defaultEmojis.dmSent.sendable)

bbCommands.register("loma", cmd_loma, 0, allowDM=True, helpSection="loma", signatureStr="**loma** *[item-type]*",
                    shortHelp="List all items currently on offer, to you only, by the pirates at Loma.",
                    longHelp="List all items currently on offer, to you only, by the pirates at Loma. Give an item type " \
                        + "(ship/weapon/turret/module/tool) to only list items of that type.")
