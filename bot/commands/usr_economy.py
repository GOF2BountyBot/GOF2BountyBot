import re
from aiohttp.client import request
import discord

from . import commandsDB as botCommands
from .. import botState, lib
from ..lib.stringTyping import commaSplitNum
from ..lib import gameMaths
from ..cfg import cfg
from ..users import basedGuild, basedUser
from ..databases.bountyDB import divisionNameForLevel
from . import util_tempdisabled

botCommands.addHelpSection(0, "economy")


async def cmd_balance(message : discord.Message, args : str, isDM : bool):
    """print the balance of the specified user, use the calling user if no user is specified.

    :param discord.Message message: the discord message calling the command
    :param str args: string, can be empty or contain a user mention
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    # If no user is specified, send the balance of the calling user
    if args == "":
        if not botState.usersDB.idExists(message.author.id):
            botState.usersDB.addID(message.author.id)
        await message.reply(mention_author=False, content=":moneybag: **" + message.author.display_name + "**, you have **" \
                                    + commaSplitNum(botState.usersDB.getUser(message.author.id).credits) + " Credits**.")

    # If a user is specified
    else:
        # Verify the passed user tag
        requestedUser = lib.discordUtil.getMemberByRefOverDB(args, dcGuild=message.guild)
        if requestedUser is None:
            await message.reply(mention_author=False, content=":x: Unknown user!")
            return
        # ensure that the user is in the users database
        if not botState.usersDB.idExists(requestedUser.id):
            botState.usersDB.addID(requestedUser.id)
        # send the user's balance
        await message.reply(mention_author=False, content=":moneybag: **" + lib.discordUtil.userOrMemberName(requestedUser, message.guild) \
                                    + "** has **" + commaSplitNum(botState.usersDB.getUser(requestedUser.id).credits) + " Credits**.")

botCommands.register("balance", cmd_balance, 0, aliases=["bal", "credits"], forceKeepArgsCasing=True, allowDM=True,
                        helpSection="economy", signatureStr="**balance** *[user]*",
                        shortHelp="Get the credits balance of yourself, or another user if one is given.",
                        longHelp="Get the credits balance of yourself, or another user if one is given. If used from inside" \
                                    + " of a server, `user` can be a mention, ID, username, or username with discriminator " \
                                    + "(#number). If used from DMs, `user` must be an ID or mention.")


async def cmd_shop(message : discord.Message, args : str, isDM : bool):
    """list the current stock of the guildShop owned by the guild containing the sent message.
    Can specify an item type to list. TODO: Make specified item listings more detailed as in !bb bounties

    :param discord.Message message: the discord message calling the command
    :param str args: either empty string, or one of cfg.validItemNames
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    requestedBGuild = botState.guildsDB.getGuild(message.guild.id)
    if requestedBGuild.shopsDisabled:
        await message.reply(mention_author=False, content=":x: This server does not have shops.")
        return

    divName = ""
    if args:
        for n in cfg.bountyDivisions:
            if args.startswith(n):
                divName = n
                args = args[len(n):].lstrip()
                break

    item = "all"
    if args.rstrip("s") in cfg.validItemNames:
        item = args.rstrip("s")
    elif args != "":
        await message.reply(mention_author=False,
                            content=":x: Unknown argument! You can give either or both of:\n" \
                                    + f"- a division name ({'/'.join(cfg.bountyDivisions)})\n" \
                                    + f"- an item type (ship/weapon/module/turret/tool/all)")
        return

    divisionNames = list(cfg.bountyDivisions.keys())
    userDivision = ""

    if botState.usersDB.idExists(message.author.id):
        bUser = botState.usersDB.getUser(message.author.id)
        userLevel = gameMaths.calculateUserBountyHuntingLevel(bUser.bountyHuntingXP)
        userDivision = divisionNameForLevel(userLevel)
        if not divName:
            divName = userDivision
    else:
        userDivision = divisionNames[0]
        if not divName:
            divName = divisionNameForLevel(cfg.minTechLevel)

    if divisionNames.index(userDivision) < divisionNames.index(divName):
        await message.reply(f":x: You are not high enough level to use the {divName} shop!")
        return

    sendChannel = None
    sendDM = False

    if item == "all":
        if message.author.dm_channel is None:
            await message.author.create_dm()
        if message.author.dm_channel is None:
            sendChannel = message.channel
        else:
            sendChannel = message.author.dm_channel
            sendDM = True
    else:
        sendChannel = message.channel

    requestedShop = botState.guildsDB.getGuild(message.guild.id).divisionShops[divName]
    shopEmbed = lib.discordUtil.makeEmbed(titleTxt="Shop", desc="__" + message.guild.name + "__\n`Current Tech Level: " \
                                                + str(requestedShop.currentTechLevel) + "`",
                                            footerTxt="All items" if item == "all" else (item + "s").title(),
                                            thumb="" if message.guild.icon is None else message.guild.icon_url_as(size=64))

    for currentItemType in ["ship", "weapon", "module", "turret", "tool"]:
        if item in ["all", currentItemType]:
            currentStock = requestedShop.getStockByName(currentItemType)
            for itemNum in range(1, currentStock.numKeys + 1):
                if itemNum == 1:
                    shopEmbed.add_field(name="‎", value="__**" + currentItemType.title() + "s**__", inline=False)

                try:
                    currentItem = currentStock[itemNum - 1].item
                except KeyError:
                    try:
                        botState.logger.log("Main", "cmd_shop",
                                            "Requested " + currentItemType + " '" + currentStock.keys[itemNum-1].name \
                                                + "' (index " + str(itemNum-1) + "), which was not found in the shop stock",
                                            category="shop", eventType="UNKWN_KEY")
                    except IndexError:
                        break
                    except AttributeError as e:
                        keysStr = ""
                        for item in currentStock.items:
                            keysStr += str(item) + ", "
                        botState.logger.log("Main", "cmd_shop",
                                            "Unexpected type in " + currentItemType + "sStock KEYS, index " \
                                                + str(itemNum-1) + ". Got " + type(currentStock.keys[itemNum-1]).__name__ \
                                                + ".\nInventory keys: " + keysStr[:-2],
                                            category="shop", eventType="INVTY_KEY_TYPE")
                        shopEmbed.add_field(name=str(itemNum) + ". **⚠ #INVALID-ITEM# '" + currentStock.keys[itemNum-1] + "'",
                                            value="Do not attempt to buy. Could cause issues.", inline=True)
                        continue
                    shopEmbed.add_field(name=str(itemNum) + ". **⚠ #INVALID-ITEM# '" + currentStock.keys[itemNum-1].name \
                                            + "'",
                                        value="Do not attempt to buy. Could cause issues.", inline=True)

                    
                    continue


                currentItemCount = currentStock.items[currentItem].count
                shopEmbed.add_field(name=str(itemNum) + ". " \
                                        + (currentItem.emoji.sendable + " " if currentItem.hasEmoji else "") \
                                        + ((" `(" + str(currentItemCount) + ")` ") if currentItemCount > 1 else "") \
                                        + "**" + currentItem.name + "**",
                                    value=lib.stringTyping.commaSplitNum(currentItem.value) + " Credits\n" \
                                        + currentItem.statsStringShort(), inline=True)

    try:
        await sendChannel.send(embed=shopEmbed)
    except discord.Forbidden:
        await message.reply(mention_author=False, content=":x: I can't DM you, " + message.author.display_name \
                                    + "! Please enable DMs from users who are not friends.")
        return
    if sendDM:
        await message.add_reaction(cfg.defaultEmojis.dmSent.sendable)

botCommands.register("shop", util_tempdisabled.err_tempDisabled, 0, aliases=["store"], allowDM=False, helpSection="economy",
                        signatureStr="**shop** *[division-name]* *[item-type]*",
                        shortHelp="Display all items currently for sale. Shop stock is refreshed every six hours. Give an " \
                                    + "item type to only list items of that type.",
                        longHelp="Display all items currently for sale. Shop stock is refreshed every six hours, with items" \
                                    + " based on its tech level. Give an item type (ship/weapon/turret/module/tool) to only" \
                                    + " list items of that type. To shop the shop for a division other than your own, " \
                                    + "specify the division name.")


async def cmd_shop_buy(message : discord.Message, args : str, isDM : bool):
    """Buy the item of the given item type, at the given index, from the guild's shop.
    if "transfer" is specified, the new ship's items are unequipped, and the old ship's items attempt to fill the new ship.
    any items left unequipped are added to the user's inactive items lists.
    if "sell" is specified, the user's old activeShip is stripped of items and sold to the shop.
    "transfer" and "sell" are only valid when buying a ship.

    :param discord.Message message: the discord message calling the command
    :param str args: string containing an item type and an index number, and optionally "transfer", and optionally "sell"
                        separated by a single space
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    requestedBGuild = botState.guildsDB.getGuild(message.guild.id)
    if requestedBGuild.shopsDisabled:
        await message.reply(mention_author=False, content=":x: This server does not have shops.")
        return

    divName = ""
    if args:
        for n in cfg.bountyDivisions:
            if args.startswith(n):
                divName = n
                args = args[len(n):].lstrip()
                break

    divisionNames = list(cfg.bountyDivisions.keys())
    userDivision = ""

    if botState.usersDB.idExists(message.author.id):
        bUser = botState.usersDB.getUser(message.author.id)
        userLevel = gameMaths.calculateUserBountyHuntingLevel(bUser.bountyHuntingXP)
        userDivision = divisionNameForLevel(userLevel)
        if not divName:
            divName = userDivision
    else:
        userDivision = divisionNames[0]
        if not divName:
            divName = divisionNameForLevel(cfg.minTechLevel)

    if divisionNames.index(userDivision) < divisionNames.index(divName):
        await message.reply(f":x: You are not high enough level to use the {divName} shop!")
        return

    requestedShop = requestedBGuild.divisionShops[divName]

    # verify this is the calling user's home guild. If no home guild is set, transfer here.
    requestedBUser = botState.usersDB.getOrAddID(message.author.id)
    if not requestedBUser.hasHomeGuild():
        await requestedBUser.transferGuild(message.guild)
        await message.reply(mention_author=False, content=":airplane_arriving: Your home guild has been set.")
    elif requestedBUser.homeGuildID != message.guild.id:
        await message.reply(mention_author=False, content=":x: This command can only be used from your home guild!")
        return

    argsSplit = args.split(" ")
    if len(argsSplit) < 2:
        await message.reply(mention_author=False, content=":x: Not enough arguments! Please provide both an item type (ship/weapon/module/turret) " \
                                    + "and an item number from `" + requestedBGuild.commandPrefix + "shop`")
        return

    cmdArgsStr = f"- Optionally, a division name ({'/'.join(cfg.bountyDivisions)})\n" \
                + "- An item type (ship/weapon/module/turret/tool)\n" \
                + "- An item number from `$shop`\n" \
                + "- Optionally, `sell` and/or `transfer` when buying a ship."

    if len(argsSplit) > 4:
        await message.reply(mention_author=False, content=f":x: Too many arguments! Please only give:\n{cmdArgsStr}")
        return

    item = argsSplit[0].rstrip("s")
    if item == "all" or item not in cfg.validItemNames:
        await message.reply(mention_author=False, content=":x: Invalid item name! Please choose from: ship, weapon, module, turret or tool.")
        return

    itemNum = argsSplit[1]
    if not lib.stringTyping.isInt(itemNum):
        await message.reply(mention_author=False, content=":x: Invalid item number!")
        return
    itemNum = int(itemNum)
    shopItemStock = requestedShop.getStockByName(item)
    if itemNum > shopItemStock.numKeys:
        if shopItemStock.numKeys == 0:
            await message.reply(mention_author=False, content=":x: This shop has no " + item + "s in stock!")
        else:
            await message.reply(mention_author=False, content=":x: Invalid item number! This shop has " + str(shopItemStock.numKeys) \
                                        + " " + item + "(s).")
        return

    if itemNum < 1:
        await message.reply(mention_author=False, content=":x: Invalid item number! Must be at least 1.")
        return

    transferItems = False
    sellOldShip = False
    if len(argsSplit) > 2:
        for arg in argsSplit[2:]:
            if arg == "transfer":
                if transferItems:
                    await message.reply(mention_author=False, content=":x: Invalid argument! Please only specify `transfer` once!")
                    return
                if item != "ship":
                    await message.reply(mention_author=False, content=":x: `transfer` can only be used when buying a ship!")
                    return
                transferItems = True
            elif arg == "sell":
                if sellOldShip:
                    await message.reply(mention_author=False, content=":x: Invalid argument! Please only specify `sell` once!")
                    return
                if item != "ship":
                    await message.reply(mention_author=False, content=":x: `sell` can only be used when buying a ship!")
                    return
                sellOldShip = True
            else:
                await message.reply(mention_author=False, content=f":x: Invalid argument! Please only give:\n{cmdArgsStr}")
                return

    requestedItem = shopItemStock[itemNum - 1].item

    if item == "ship":
        newShipValue = requestedItem.getValue()
        activeShip = requestedBUser.activeShip

        # Check the item can be afforded
        if (not sellOldShip and not requestedShop.userCanAffordItemObj(requestedBUser, requestedItem)) or \
                    (sellOldShip and not requestedShop.amountCanAffordShipObj(requestedBUser.credits \
                    + requestedBUser.activeShip.getValue(shipUpgradesOnly=transferItems), requestedItem)):
            await message.reply(mention_author=False, content=":x: You can't afford that item! (" + str(requestedItem.getValue()) + ")")
            return

        requestedBUser.inactiveShips.addItem(requestedItem)

        if transferItems:
            requestedBUser.unequipAll(requestedItem)
            activeShip.transferItemsTo(requestedItem)
            requestedBUser.unequipAll(activeShip)

        if sellOldShip:
            # TODO: move to a separate sellActiveShip function
            oldShipValue = activeShip.getValue(shipUpgradesOnly=transferItems)
            requestedBUser.credits += oldShipValue
            shopItemStock.addItem(activeShip)
        else:
            oldShipValue = None

        requestedBUser.equipShipObj(requestedItem, noSaveActive=sellOldShip)
        requestedBUser.credits -= newShipValue
        shopItemStock.removeItem(requestedItem)

        outStr = ":moneybag: Congratulations on your new **" + requestedItem.name + "**!"
        if sellOldShip:
            outStr += "\nYou received **" \
                        + str(oldShipValue) + " credits** for your old **" \
                        + str(activeShip.name) + "**."
        else:
            outStr += " Your old **" + activeShip.name + "** can be found in the hangar."
        if transferItems:
            outStr += "\nItems thay could not fit in your new ship can be found in the hangar."
        outStr += "\n\nYour balance is now: **" \
                    + str(requestedBUser.credits) + " credits**."

        await message.reply(mention_author=False, content=outStr)

    elif item in ["weapon", "module", "turret", "tool"]:
        if not requestedShop.userCanAffordItemObj(requestedBUser, requestedItem):
            await message.reply(mention_author=False, content=":x: You can't afford that item! (" + str(requestedItem.value) + ")")
            return

        requestedBUser.credits -= requestedItem.value
        requestedBUser.getInactivesByName(item).addItem(requestedItem)
        shopItemStock.removeItem(requestedItem)

        await message.reply(mention_author=False, content=":moneybag: Congratulations on your new **" + requestedItem.name \
                                    + "**! \n\nYour balance is now: **" + str(requestedBUser.credits) + " credits**.")
    else:
        raise NotImplementedError("Valid but unsupported item name: " + item)

botCommands.register("buy", util_tempdisabled.err_tempDisabled, 0, allowDM=False, helpSection="economy",
                        signatureStr="**buy** *[division-name]* **<item-type> <item-number>** *[transfer] [sell]*",
                        shortHelp="Buy the requested item from the shop. Item numbers can be seen in the `shop`." \
                                    + "\n🌎 This command must be used in your **home server**.",
                        longHelp="Buy the requested item from the shop. Item numbers are shown next to items in the `shop`." \
                                    + "\nWhen buying from a division other than your own, specify the division name." \
                                    + "\nWhen buying a ship, specify `sell` to sell your active ship, and/or `transfer` to " \
                                    + "move your active items to the new ship. I.e, *to sell your active ship without " \
                                    + "selling the items on the ship, use:* `buy ship <ship number> sell transfer`.*" \
                                    + "\n🌎 This command must be used in your **home server**.")


async def cmd_shop_sell(message : discord.Message, args : str, isDM : bool):
    """Sell the item of the given item type, at the given index, from the user's inactive items, to the guild's shop.
    if "clear" is specified, the ship's items are unequipped before selling.
    "clear" is only valid when selling a ship.

    :param discord.Message message: the discord message calling the command
    :param str args: string containing an item type and an index number, and optionally "clear", separated by a single space
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    requestedBGuild = botState.guildsDB.getGuild(message.guild.id)
    if requestedBGuild.shopsDisabled:
        await message.reply(mention_author=False, content=":x: This server does not have shops.")
        return

    divName = ""
    if args:
        for n in cfg.bountyDivisions:
            if args.startswith(n):
                divName = n
                args = args[len(n):].lstrip()
                break

    divisionNames = list(cfg.bountyDivisions.keys())
    userDivision = ""

    if botState.usersDB.idExists(message.author.id):
        bUser = botState.usersDB.getUser(message.author.id)
        userLevel = gameMaths.calculateUserBountyHuntingLevel(bUser.bountyHuntingXP)
        userDivision = divisionNameForLevel(userLevel)
        if not divName:
            divName = userDivision
    else:
        userDivision = divisionNames[0]
        if not divName:
            divName = divisionNameForLevel(cfg.minTechLevel)

    if divisionNames.index(userDivision) < divisionNames.index(divName):
        await message.reply(f":x: You are not high enough level to use the {divName} shop!")
        return

    requestedShop = requestedBGuild.divisionShops[divName]

    # verify this is the calling user's home guild. If no home guild is set, transfer here.
    requestedBUser = botState.usersDB.getOrAddID(message.author.id)
    if not requestedBUser.hasHomeGuild():
        await requestedBUser.transferGuild(message.guild)
        await message.reply(mention_author=False, content=":airplane_arriving: Your home guild has been set.")
    elif requestedBUser.homeGuildID != message.guild.id:
        await message.reply(mention_author=False, content=":x: This command can only be used from your home guild!")
        return

    argsSplit = args.split(" ")
    if len(argsSplit) < 2:
        await message.reply(mention_author=False, content=":x: Not enough arguments! Please provide both an item type (ship/weapon/module/turret) " \
                                    + "and an item number from `" + requestedBGuild.commandPrefix + "hangar`")
        return

    cmdArgsStr = f"- Optionally, a division name ({'/'.join(cfg.bountyDivisions)})\n" \
                + "- An item type (ship/weapon/module/turret/tool)\n" \
                + "- An item number from `$shop`\n" \
                + "- Optionally, `clear` when selling a ship."

    if len(argsSplit) > 3:
        await message.reply(mention_author=False, content=f":x: Too many arguments! Please only give:\n{cmdArgsStr}")
        return

    item = argsSplit[0].rstrip("s")
    if item == "all" or item not in cfg.validItemNames:
        await message.reply(mention_author=False, content=":x: Invalid item name! Please choose from: ship, weapon, module or turret.")
        return

    itemNum = argsSplit[1]
    if not lib.stringTyping.isInt(itemNum):
        await message.reply(mention_author=False, content=":x: Invalid item number!")
        return
    itemNum = int(itemNum)

    userItemInactives = requestedBUser.getInactivesByName(item)
    if itemNum > userItemInactives.numKeys:
        await message.reply(mention_author=False, content=":x: Invalid item number! You have " + str(userItemInactives.numKeys) + " " + item + "s.")
        return
    if itemNum < 1:
        await message.reply(mention_author=False, content=":x: Invalid item number! Must be at least 1.")
        return

    clearItems = False
    if len(argsSplit) == 3:
        if argsSplit[2] == "clear":
            if item != "ship":
                await message.reply(mention_author=False, content=":x: `clear` can only be used when selling a ship!")
                return
            clearItems = True
        else:
            await message.reply(mention_author=False, content=f":x: Invalid argument! Please only give:\n{cmdArgsStr}")
            return

    shopItemStock = requestedShop.getStockByName(item)
    requestedItem = userItemInactives[itemNum - 1].item

    if item == "ship":
        if clearItems:
            requestedBUser.unequipAll(requestedItem)

        requestedBUser.credits += requestedItem.getValue()
        userItemInactives.removeItem(requestedItem)
        shopItemStock.addItem(requestedItem)

        outStr = ":moneybag: You sold your **" + requestedItem.getNameOrNick() + "** for **" \
                    + str(requestedItem.getValue()) + " credits**!"
        if clearItems:
            outStr += "\nItems removed from the ship can be found in the hangar."
        await message.reply(mention_author=False, content=outStr)

    elif item in ["weapon", "module", "turret", "tool"]:
        {"weapon": requestedShop.userSellWeaponObj, "module": requestedShop.userSellModuleObj,
            "turret": requestedShop.userSellTurretObj,
            "tool": requestedShop.userSellToolObj}[item](requestedBUser, requestedItem)

        await message.reply(mention_author=False, content=":moneybag: You sold your **" + requestedItem.name + "** for **" \
                                    + str(requestedItem.getValue()) + " credits**!")

    else:
        raise NotImplementedError("Valid but unsupported item name: " + item)

botCommands.register("sell", util_tempdisabled.err_tempDisabled, 0, allowDM=False, helpSection="economy",
                        signatureStr="**sell** *[division-name]* **<item-type> <item-number>** *[clear]*",
                        shortHelp="Sell the requested item from your hangar. Item numbers can be gotten from `hangar`.\n" \
                                    + "🌎 This command must be used in your **home server**.",
                        longHelp="Sell the requested item from your hangar to the shop. Item numbers are shown next to " \
                                    + "items in your `hangar`. When buying from a division other than your own, " \
                                    + "specify the division name. When selling a ship, specify `clear` to first remove all " \
                                    + "items from the ship. See `help buy` for how to sell your active ship.\n" \
                                    + "🌎 This command must be used in your **home server**.")


async def cmd_pay(message : discord.Message, args : str, isDM : bool):
    """Pay a given user the given number of credits from your balance.
    """
    argsSplit = args.split(" ")
    if len(argsSplit) < 2:
        await message.reply(mention_author=False, content=":x: Please give a target user and an amount!")
        return

    if not lib.stringTyping.isInt(argsSplit[1]):
        await message.reply(mention_author=False, content=":x: Invalid amount!")
        return

    requestedUser = lib.discordUtil.getMemberByRefOverDB(argsSplit[0], dcGuild=message.guild)
    if requestedUser is None:
        await message.reply(mention_author=False, content=":x: Unknown user!")
        return

    amount = int(argsSplit[1])
    if amount < 1:
        await message.reply(mention_author=False, content=":x: You have to pay at least 1 credit!")
        return

    if botState.usersDB.idExists(message.author.id):
        sourceBBUser: basedUser.BasedUser = botState.usersDB.getUser(message.author.id)
    else:
        sourceBBUser: basedUser.BasedUser = botState.usersDB.addID(message.author.id)

    if not sourceBBUser.credits >= amount:
        await message.reply(mention_author=False, content=":x: You don't have that many credits!")
        return

    if botState.usersDB.idExists(requestedUser.id):
        targetBBUser: basedUser.BasedUser = botState.usersDB.getUser(requestedUser.id)
    else:
        targetBBUser: basedUser.BasedUser = botState.usersDB.addID(requestedUser.id)

    homeGuild: discord.Guild = botState.client.get_guild(sourceBBUser.homeGuildID)

    if not targetBBUser.hasHomeGuild() or not sourceBBUser.hasHomeGuild() or \
            targetBBUser.homeGuildID != sourceBBUser.homeGuildID:
        await message.channel.send(":x: You can only pay players whose home server is " \
                                    + homeGuild.name + "!")
        return

    sourceBBUser.credits -= amount
    targetBBUser.credits += amount

    await message.reply(mention_author=False, content=":moneybag: You paid " + lib.discordUtil.userOrMemberName(requestedUser, message.guild) \
                                + " **" + str(amount) + "** credits!")
    
    if message.guild.get_member(requestedUser.id) is None:
        homeBGuild: basedGuild.BasedGuild = botState.guildsDB.getGuild(homeGuild.id)
        if homeBGuild.hasPlayChannel():
            await homeBGuild.getPlayChannel().send(f":moneybag: {message.author.mention} paid " \
                                                    + f"{requestedUser.mention} **{amount}** credits!")
        else:
            try:
                await requestedUser.send(f":moneybag: {message.author.mention} paid you **{amount}** credits!")
            except (discord.Forbidden, discord.HTTPException, discord.NotFound) as e:
                botState.logger.log("user_economy", "cmd_pay", "Exception thrown when attempting to DM pay announcement",
                                    exception=e)
        

botCommands.register("pay", cmd_pay, 0, forceKeepArgsCasing=True, allowDM=True, helpSection="economy",
                        signatureStr="**pay <user> <amount>**",
                        shortHelp="Pay the given user an amount of credits from your balance.",
                        longHelp="Pay the given user an amount of credits from your balance.\n" \
                                    + "If used from inside of a server, `user` can be a mention, ID, username, or username " \
                                    + "with discriminator (#number). If used from DMs, `user` must be an ID or mention.")


async def cmd_total_value(message : discord.Message, args : str, isDM : bool):
    """⚠ WARNING: MARKED FOR CHANGE ⚠
    The following function is provisional and marked as planned for overhaul.
    Details: The command output is finalised. However, the inner workings of the command are to be replaced with attribute
    getters. It is inefficient to calculate total value measurements on every call, so current totals should be cached in
    object attributes whenever modified.

    print the total value of the specified user, use the calling user if no user is specified.

    :param discord.Message message: the discord message calling the command
    :param str args: string, can be empty or contain a user mention or ID
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    # If no user is specified, send the balance of the calling user
    if args == "":
        if not botState.usersDB.idExists(message.author.id):
            botState.usersDB.addID(message.author.id)
        await message.reply(mention_author=False, content=":moneybag: **" + message.author.display_name \
                                    + "**, your items and balance are worth a total of **" \
                                    + str(botState.usersDB.getUser(message.author.id).getStatByName("value")) + " Credits**.")

    # If a user is specified
    else:
        # Verify the passed user tag
        requestedUser = lib.discordUtil.getMemberByRefOverDB(args, dcGuild=message.guild)
        if requestedUser is None:
            await message.reply(mention_author=False, content=":x: Unknown user!")
            return
        # ensure that the user is in the users database
        if not botState.usersDB.idExists(requestedUser.id):
            botState.usersDB.addID(requestedUser.id)
        # send the user's balance
        await message.reply(mention_author=False, content=":moneybag: **" + lib.discordUtil.userOrMemberName(requestedUser, message.guild) \
                                    + "**'s items and balance have a total value of **" \
                                    + str(botState.usersDB.getUser(requestedUser.id).getStatByName("value")) + " Credits**.")

botCommands.register("total-value", cmd_total_value, 0, forceKeepArgsCasing=True, allowDM=True, helpSection="economy",
                        signatureStr="**total-value** *[user]*",
                        shortHelp="Get the total value of all of your items, including your credits balance, or that of " \
                                    + "another user.",
                        longHelp="Get the total value of all of your items, including your credits balance. Give a user to " \
                                    + "check someone else's total inventory value.")
