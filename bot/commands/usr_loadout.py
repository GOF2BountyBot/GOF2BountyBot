from typing import cast
import discord

from . import commandsDB as botCommands
from .. import lib, botState
from ..cfg import cfg, bbData
from ..users import basedUser
from ..gameObjects.items import shipItem, gameItem
from ..gameObjects.inventories import inventory


botCommands.addHelpSection(0, "loadout")


async def cmd_hangar(message : discord.Message, args : str, isDM : bool):
    """return a page listing the calling user's items. Administrators may view the hangar of any user.
    can apply to a specified user, or the calling user if none is specified.
    can apply to a type of item (ships, modules, turrets or weapons), or all items if none is specified.
    can apply to a page, or the first page if none is specified.
    Arguments can be given in any order, and must be separated by a single space.

    TODO: try displaying as a discord message rather than embed?
    TODO: add icons for ships and items!?

    :param discord.Message message: the discord message calling the command
    :param str args: string containing the arguments as specified above
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    argsSplit = args.split(" ")

    requestedUser = message.author
    item = "all"
    page = 1

    useDummyData = False
    prefix = cfg.defaultCommandPrefix if isDM else botState.guildsDB.getGuild(message.guild.id).commandPrefix

    if len(argsSplit) > 3:
        await message.reply(f":x: Too many arguments! Please see `{prefix}help hangar`.",
                            mention_author=False)
        return

    def extractArgs():
        requestedUser = message.author
        item = "all"
        page = 1
        foundUser = False
        foundItem = False
        foundPage = False

        arg = argsSplit[0]
        if arg.rstrip("s") in cfg.validItemNames:
            item = arg.rstrip("s")
            foundItem = True
            if len(argsSplit) == 1:
                return requestedUser, item, page, True

        arg = argsSplit[int(foundItem)]
        if lib.stringTyping.isInt(arg):
            page = int(arg)
            foundPage = True
            if len(argsSplit) < foundItem + foundPage + 1:
                return requestedUser, item, page, True

        arg = " ".join(argsSplit[foundItem+foundPage:])
        userAttempt = lib.discordUtil.getMemberByRefOverDB(arg, dcGuild=message.guild)
        if userAttempt is not None:
            requestedUser = userAttempt
            foundUser = True
        
        finalIndex = foundItem+foundPage+foundUser
        success = finalIndex == 0 or finalIndex + 1 != len(argsSplit)

        return requestedUser if foundUser else None, item, page, success

    if args != "":
        requestedUser, item, page, success = extractArgs()
        if not success:
            if requestedUser is None:
                await message.reply(f":x: Unrecognised user!")
            else:
                await message.reply(f":x: Invalid arguments, please see `{prefix}help hangar`.",
                                    mention_author=False)
            return

    if requestedUser is None:
        await message.reply(mention_author=False, content=":x: Unrecognised user!")
        return

    if not botState.usersDB.idExists(requestedUser.id):
        useDummyData = True

    foundUser = requestedUser != message.author
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

    if item == "all":
        maxPerPage = cfg.maxItemsPerHangarPageAll
    else:
        maxPerPage = cfg.maxItemsPerHangarPageIndividual

    firstPlace = maxPerPage * (page - 1) + 1

    if useDummyData:
        if page > 1:
            await message.reply(mention_author=False, content=":x: " + ("The requested pilot" if foundUser else "You") + " only " \
                                        + ("has" if foundUser else "have") + " one page of items. Showing page one:")
            page = 1
        elif page < 1:
            await message.reply(mention_author=False, content=":x: Invalid page number. Showing page one:")
            page = 1

        hangarEmbed = lib.discordUtil.makeEmbed(titleTxt="Hangar", desc=requestedUser.mention,
                                                col=bbData.factionColours["neutral"],
                                                footerTxt="All items" if item == "all" else item.rstrip("s").title() \
                                                            + "s - page " + str(page),
                                                thumb=requestedUser.avatar_url_as(size=64))

        for itemType in ("ship", "weapon", "module", "turret", "tool"):
            itemInactivesDict = basedUser.defaultUserDict.get(f"inactive{itemType.title()}s", False)
            if not itemInactivesDict:
                continue

            itemInactives = inventory.Inventory()
            for itemDict in itemInactivesDict:
                itemInactives.addItem(gameItem.spawnItem(itemDict["item"]), itemDict.get("count", 1))
            
            numPages = int(itemInactives.numKeys / maxPerPage) + (0 if itemInactives.numKeys % maxPerPage == 0 else 1)
            lastItemNumber = (firstPlace + maxPerPage) if page < numPages else itemInactives.numKeys

            for itemNum in range(firstPlace, lastItemNumber + 1):
                if itemNum == firstPlace:
                    hangarEmbed.add_field(name="‎", value=f"__**Stored {itemType.title()}s**__", inline=False)

                currentItem = cast(gameItem.GameItem, itemInactives[itemNum - 1].item)
                currentItemCount = itemInactives[itemNum- 1].count
                hangarEmbed.add_field(name=str(itemNum) + ". " \
                                            + (currentItem.emoji.sendable + " " if currentItem.hasEmoji else "") \
                                            + ((" `(" + str(currentItemCount) + ")` ") if currentItemCount > 1 else "") \
                                            + currentItem.name,
                                        value=currentItem.statsStringShort(), inline=False)

        if not hangarEmbed.fields:
            hangarEmbed.add_field(name="No Stored Items", value="‎", inline=False)
        await message.reply(mention_author=False, embed=hangarEmbed)
        return

    else:
        requestedBBUser = botState.usersDB.getUser(requestedUser.id)

        if page < 1:
            await message.reply(mention_author=False, content=":x: Invalid page number. Showing page one:")
            page = 1
        else:
            maxPage = requestedBBUser.numInventoryPages(item, maxPerPage)
            if maxPage == 0:
                await message.reply(mention_author=False, content=":x: " + ("The requested pilot doesn't" if foundUser else "You don't") \
                                            + " have any " + ("items" if item == "all" else "of that item") + "!")
                return
            elif page > maxPage:
                await message.reply(mention_author=False, content=":x: " + ("The requested pilot" if foundUser else "You") + " only " \
                                            + ("has " if foundUser else "have ") + str(maxPage) \
                                            + " page(s) of items. Showing page " + str(maxPage) + ":")
                page = maxPage

        hangarEmbed = lib.discordUtil.makeEmbed(titleTxt="Hangar", desc=requestedUser.mention,
                                                col=bbData.factionColours["neutral"],
                                                footerTxt=("All item" if item == "all" else item.rstrip("s").title()) \
                                                            + "s - page " + str(page) + "/" \
                                                            + str(requestedBBUser.numInventoryPages(item, maxPerPage)),
                                                thumb=requestedUser.avatar_url_as(size=64))

        if item in ["all", "ship"]:
            for shipNum in range(firstPlace, requestedBBUser.lastItemNumberOnPage("ship", page, maxPerPage) + 1):
                if shipNum == firstPlace:
                    hangarEmbed.add_field(name="‎", value="__**Stored Ships**__", inline=False)
                currentItem = requestedBBUser.inactiveShips[shipNum - 1].item
                currentItemCount = requestedBBUser.inactiveShips.items[currentItem].count
                hangarEmbed.add_field(name=str(shipNum) + ". " \
                                            + (currentItem.emoji.sendable + " " if currentItem.hasEmoji else "") \
                                            + ((" `(" + str(currentItemCount) + ")` ") if currentItemCount > 1 else "") \
                                            + currentItem.getNameAndNick(), value=currentItem.statsStringShort(),
                                        inline=False)

        if item in ["all", "weapon"]:
            for weaponNum in range(firstPlace, requestedBBUser.lastItemNumberOnPage("weapon", page, maxPerPage) + 1):
                if weaponNum == firstPlace:
                    hangarEmbed.add_field(name="‎", value="__**Stored Weapons**__", inline=False)
                currentItem = requestedBBUser.inactiveWeapons[weaponNum - 1].item
                currentItemCount = requestedBBUser.inactiveWeapons.items[currentItem].count
                hangarEmbed.add_field(name=str(weaponNum) + ". " \
                                            + (currentItem.emoji.sendable + " " if currentItem.hasEmoji else "") \
                                            + ((" `(" + str(currentItemCount) + ")` ") if currentItemCount > 1 else "") \
                                            + currentItem.name, value=currentItem.statsStringShort(), inline=False)

        if item in ["all", "module"]:
            for moduleNum in range(firstPlace, requestedBBUser.lastItemNumberOnPage("module", page, maxPerPage) + 1):
                if moduleNum == firstPlace:
                    hangarEmbed.add_field(name="‎", value="__**Stored Modules**__", inline=False)
                currentItem = requestedBBUser.inactiveModules[moduleNum - 1].item
                currentItemCount = requestedBBUser.inactiveModules.items[currentItem].count
                hangarEmbed.add_field(name=str(moduleNum) + ". " \
                                            + (currentItem.emoji.sendable + " " if currentItem.hasEmoji else "") \
                                            + ((" `(" + str(currentItemCount) + ")` ") if currentItemCount > 1 else "") \
                                            + currentItem.name,
                                        value=currentItem.statsStringShort(), inline=False)

        if item in ["all", "turret"]:
            for turretNum in range(firstPlace, requestedBBUser.lastItemNumberOnPage("turret", page, maxPerPage) + 1):
                if turretNum == firstPlace:
                    hangarEmbed.add_field(name="‎", value="__**Stored Turrets**__", inline=False)
                currentItem = requestedBBUser.inactiveTurrets[turretNum - 1].item
                currentItemCount = requestedBBUser.inactiveTurrets.items[currentItem].count
                hangarEmbed.add_field(name=str(turretNum) + ". " \
                                            + (currentItem.emoji.sendable + " " if currentItem.hasEmoji else "") \
                                            + ((" `(" + str(currentItemCount) + ")` ") if currentItemCount > 1 else "") \
                                            + currentItem.name,
                                        value=currentItem.statsStringShort(), inline=False)

        if item in ["all", "tool"]:
            for toolNum in range(firstPlace, requestedBBUser.lastItemNumberOnPage("tool", page, maxPerPage) + 1):
                if toolNum == firstPlace:
                    hangarEmbed.add_field(name="‎", value="__**Stored Tools**__", inline=False)
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

botCommands.register("hangar", cmd_hangar, 0, aliases=["hanger"], forceKeepArgsCasing=True, allowDM=True,
                    helpSection="loadout", signatureStr="**hangar** *[item-type]*",
                    longHelp="Display the items stored in your hangar. Give an item type (ship/weapon/turret/module) to " \
                                + "only list items of that type.")
botCommands.register("hangar", cmd_hangar, 1, aliases=["hanger"], forceKeepArgsCasing=True, allowDM=True,
                    signatureStr="**hangar** *[user]* *[item-type]*", shortHelp="Administrators have permission to view " \
                                    + "the hangars of other users.", longHelp="Display the items stored in your hangar. " \
                                    + "Give an item type (ship/weapon/turret/module) to only list items of that type.\n" \
                                    + "Administrators have permission to view the hangars of other users.")


async def cmd_loadout(message : discord.Message, args : str, isDM : bool):
    """list the requested user or criminal's currently equipped items.

    :param discord.Message message: the discord message calling the command
    :param str args: either empty string, or a user mention, or 'criminal' followed by a criminal alias.
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    requestedUser = message.author
    useDummyData = False
    argsSplit = args.split(" ")
    isCriminal = len(argsSplit) > 0 and argsSplit[0].lower() == "criminal"

    if len(argsSplit) > 1 and not isCriminal:
        await message.reply(mention_author=False, content=":x: Too many arguments! I can only take a target user/criminal!")
        return
    elif len(argsSplit) == 1 and isCriminal:
        await message.channel.send(":x: Not enough arguments! Please give the criminal name.")
        return

    if isCriminal:
        if isDM:
            await message.channel.send(":x: criminal loadouts can only be requested from inside a server!")
        else:
            callingBBGuild = botState.guildsDB.getGuild(message.guild.id)
            if callingBBGuild.bountiesDisabled:
                await message.channel.send(":x: This server has bounties disabled!")
                return

            # look up the criminal object
            criminalName = args[9:].title()

            # report unrecognised criminal names
            if not callingBBGuild.bountiesDB.bountyNameExists(criminalName, noEscapedCrim=True):
                errmsg = ":x: That pilot is not currently wanted!"

                if lib.stringTyping.isMention(criminalName):
                    errmsg += "\n:warning: **Don't tag users**, use their name and ID number like so: `" \
                                + callingBBGuild.commandPrefix + "loadout criminal Trimatix#2244`"

                await message.channel.send(errmsg)
                return

            bountyObj = callingBBGuild.bountiesDB.getBounty(criminalName)
            criminalObj = bountyObj.criminal

            activeShip = bountyObj.activeShip
            loadoutEmbed = lib.discordUtil.makeEmbed(titleTxt="Loadout",
                                                        desc=criminalObj.name.title() + "\n`Difficulty: " \
                                                            + str(bountyObj.techLevel) + "`",
                                                        col=bbData.factionColours[criminalObj.faction] \
                                                            if criminalObj.faction in bbData.factionColours \
                                                            else bbData.factionColours["neutral"],
                                                        thumb=criminalObj.icon)
            loadoutEmbed = activeShip.fillLoadoutEmbed(loadoutEmbed, shipEmoji=True)

            await message.channel.send(embed=loadoutEmbed)
            return

    if args != "":
        requestedUser = lib.discordUtil.getMemberByRefOverDB(args, dcGuild=message.guild)
        if requestedUser is None:
            await message.reply(mention_author=False, content=":x: Invalid user requested! Please either ping them, or give their ID!")
            return

    if not botState.usersDB.idExists(requestedUser.id):
        useDummyData = True

    if useDummyData:
        activeShip = shipItem.Ship.fromDict(basedUser.defaultShipLoadoutDict)
        loadoutEmbed = lib.discordUtil.makeEmbed(titleTxt="Loadout", desc=requestedUser.mention,
                                                    col=bbData.factionColours[activeShip.manufacturer] \
                                                        if activeShip.manufacturer in bbData.factionColours \
                                                        else bbData.factionColours["neutral"],
                                                    thumb=activeShip.icon if activeShip.hasIcon \
                                                        else requestedUser.avatar_url_as(size=64))

        await message.reply(mention_author=False, embed=activeShip.fillLoadoutEmbed(loadoutEmbed))
        return

    else:
        requestedBBUser = botState.usersDB.getUser(requestedUser.id)
        activeShip = requestedBBUser.activeShip
        loadoutEmbed = lib.discordUtil.makeEmbed(titleTxt="Loadout", desc=requestedUser.mention,
                                                    col=bbData.factionColours[activeShip.manufacturer] if \
                                                        activeShip.manufacturer in bbData.factionColours else \
                                                        bbData.factionColours["neutral"],
                                                    thumb=activeShip.icon if activeShip.hasIcon else \
                                                        requestedUser.avatar_url_as(size=64))

        if activeShip is None:
            loadoutEmbed.add_field(name="Active Ship:", value="None", inline=False)
        else:
            loadoutEmbed = activeShip.fillLoadoutEmbed(loadoutEmbed)

        await message.reply(mention_author=False, embed=loadoutEmbed)

botCommands.register("loadout", cmd_loadout, 0, forceKeepArgsCasing=True, allowDM=True, helpSection="loadout",
                    signatureStr="**loadout** *[user]*",
                    shortHelp="Display your current ship and the items equipped onto it, " \
                                + "or those equipped by another player.")


async def cmd_equip(message : discord.Message, args : str, isDM : bool):
    """Equip the item of the given item type, at the given index, from the user's inactive items.
    if "transfer" is specified, the new ship's items are cleared, and the old ship's items attempt to fill new ship.
    "transfer" is only valid when equipping a ship.

    :param discord.Message message: the discord message calling the command
    :param str args: string containing an item type and an index number, and optionally "transfer",
                        separated by a single space
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    if isDM:
        prefix = cfg.defaultCommandPrefix
    else:
        prefix = botState.guildsDB.getGuild(message.guild.id).commandPrefix

    argsSplit = args.split(" ")
    if len(argsSplit) < 2:
        await message.reply(mention_author=False, content=f":x: Not enough arguments! Please provide both an item type (ship/weapon/module/turret) " \
                                    + "an item number (Or a comma seperated list of item numbers) from `" + prefix + "hangar`, and optionally `transfer` when equipping a ship.")
        return

    item = argsSplit[0].rstrip("s")
    if item in ["all", "tool"] or item not in cfg.validItemNames:
        await message.reply(mention_author=False, content=":x: Invalid item name! Please choose from: ship, weapon, module or turret.")
        return

    requestedBBUser = botState.usersDB.getOrAddID(message.author.id)

    itemNum = argsSplit[1]
    
    
    #if itemNum includes a "," -> put valid ItemNums into a list
    if "," in itemNum:
        multipleItems = True
        transferItems = False
        itemNum = []
        for arg in argsSplit:
            #Check if the argument is the item
            if arg in cfg.validItemNames:
                continue
            #remove any ","       
            arg = arg.rstrip(",")

            if not lib.stringTyping.isInt(arg):
                await message.reply(mention_author=False, content=":x: Invalid item number!")
                return
            arg = int(arg)
            userItemInactives = requestedBBUser.getInactivesByName(item)
            if arg > userItemInactives.numKeys:
                await message.reply(mention_author=False, content=":x: Invalid item number! You have " + str(userItemInactives.numKeys) + " " + item + "s.")
                return
            if arg < 1:
                await message.reply(mention_author=False, content=":x: Invalid item number! Must be at least 1.")
                return

            if arg == "transfer":
                transferItems = True
                break
            itemNum.append(arg)
        
        itemNum.sort()
        
        #Equip the items one by one
        iterations = 1
        for i in itemNum:
            requestedSlot = userItemInactives[i - iterations]
            lastItemInSlot = requestedSlot.count == 1
            requestedItem = requestedSlot.item

            if item == "ship":
                activeShip = requestedBBUser.activeShip
                if transferItems:
                    requestedBBUser.unequipAll(requestedItem)
                    requestedBBUser.activeShip.transferItemsTo(requestedItem)
                    requestedBBUser.unequipAll(activeShip)

                requestedBBUser.equipShipObj(requestedItem)

                outStr = ":rocket: You switched to the **" + requestedItem.getNameOrNick() + "**."
                if transferItems:
                    outStr += "\nItems that could not fit in your new ship can be found in the hangar."
                await message.reply(mention_author=False, content=outStr)

            elif item == "weapon":
                if not requestedBBUser.activeShip.canEquipMoreWeapons():
                    await message.reply(mention_author=False, content=":x: Your active ship does not have any free weapon slots!")
                    return

                requestedBBUser.activeShip.equipWeapon(requestedItem)
                requestedBBUser.inactiveWeapons.removeItem(requestedItem)

                await message.reply(mention_author=False, content=":wrench: You equipped the **" + requestedItem.name + "**.")
                
            elif item == "module":
                if not requestedBBUser.activeShip.canEquipMoreModules():
                    await message.reply(mention_author=False, content=":x: Your active ship does not have any free module slots!")
                    return

                if not requestedBBUser.activeShip.canEquipModuleType(type(requestedItem)):
                    await message.reply(mention_author=False, content=":x: You already have the max of this type of module equipped!")
                    return

                requestedBBUser.activeShip.equipModule(requestedItem)
                requestedBBUser.inactiveModules.removeItem(requestedItem)

                await message.reply(mention_author=False, content=":wrench: You equipped the **" + requestedItem.name + "**.")

            elif item == "turret":
                if not requestedBBUser.activeShip.canEquipMoreTurrets():
                    await message.reply(mention_author=False, content=":x: Your active ship does not have any free turret slots!")
                    return

                requestedBBUser.activeShip.equipTurret(requestedItem)
                requestedBBUser.inactiveTurrets.removeItem(requestedItem)

                await message.reply(mention_author=False, content=":wrench: You equipped the **" + requestedItem.name + "**.")
            
            else:
                raise NotImplementedError("Valid but unsupported item name: " + item)

            if lastItemInSlot:
                iterations += 1
            

    #if there isn't a ","
    else:
        
        if not lib.stringTyping.isInt(itemNum):
            await message.reply(mention_author=False, content=":x: Invalid item number!")
            return
        
        if len(argsSplit) > 3:
            await message.reply(mention_author=False, content=":x: Too many arguments! Please only give an item type (ship/weapon/module/turret), " \
                                        + "an item number (Or a comma seperated list of item numbers), and optionally `transfer` when equipping a ship.")
            return
        
        itemNum = int(itemNum)
        userItemInactives = requestedBBUser.getInactivesByName(item)
        if itemNum > userItemInactives.numKeys:
            await message.reply(mention_author=False, content=":x: Invalid item number! You have " + str(userItemInactives.numKeys) + " " + item + "s.")
            return
        if itemNum < 1:
            await message.reply(mention_author=False, content=":x: Invalid item number! Must be at least 1.")
            return

        transferItems = False
        if len(argsSplit) == 3:
            if argsSplit[2] == "transfer":
                if item != "ship":
                    await message.reply(mention_author=False, content=":x: `transfer` can only be used when equipping a ship!")
                    return
                transferItems = True
            else:
                await message.reply(mention_author=False, content=":x: Invalid argument! Please only give an item type (ship/weapon/module/turret), " \
                                            + "an item number, and optionally `transfer` when equipping a ship.")
                return

        requestedItem = userItemInactives[itemNum - 1].item

        if item == "ship":
            activeShip = requestedBBUser.activeShip
            if transferItems:
                requestedBBUser.unequipAll(requestedItem)
                requestedBBUser.activeShip.transferItemsTo(requestedItem)
                requestedBBUser.unequipAll(activeShip)

            requestedBBUser.equipShipObj(requestedItem)

            outStr = ":rocket: You switched to the **" + requestedItem.getNameOrNick() + "**."
            if transferItems:
                outStr += "\nItems that could not fit in your new ship can be found in the hangar."
            await message.reply(mention_author=False, content=outStr)

        elif item == "weapon":
            if not requestedBBUser.activeShip.canEquipMoreWeapons():
                await message.reply(mention_author=False, content=":x: Your active ship does not have any free weapon slots!")
                return

            requestedBBUser.activeShip.equipWeapon(requestedItem)
            requestedBBUser.inactiveWeapons.removeItem(requestedItem)

            await message.reply(mention_author=False, content=":wrench: You equipped the **" + requestedItem.name + "**.")

        elif item == "module":
            if not requestedBBUser.activeShip.canEquipMoreModules():
                await message.reply(mention_author=False, content=":x: Your active ship does not have any free module slots!")
                return

            if not requestedBBUser.activeShip.canEquipModuleType(type(requestedItem)):
                await message.reply(mention_author=False, content=":x: You already have the max of this type of module equipped!")
                return

            requestedBBUser.activeShip.equipModule(requestedItem)
            requestedBBUser.inactiveModules.removeItem(requestedItem)

            await message.reply(mention_author=False, content=":wrench: You equipped the **" + requestedItem.name + "**.")

        elif item == "turret":
            if not requestedBBUser.activeShip.canEquipMoreTurrets():
                await message.reply(mention_author=False, content=":x: Your active ship does not have any free turret slots!")
                return

            requestedBBUser.activeShip.equipTurret(requestedItem)
            requestedBBUser.inactiveTurrets.removeItem(requestedItem)

            await message.reply(mention_author=False, content=":wrench: You equipped the **" + requestedItem.name + "**.")

        else:
            raise NotImplementedError("Valid but unsupported item name: " + item)

botCommands.register("equip", cmd_equip, 0, allowDM=True, helpSection="loadout",
                    signatureStr="**equip <item-type> <item-num>** *[transfer]*",
                    shortHelp="Equip the requested item from your hangar onto your active ship. " \
                                + "Item numbers can be gotten from `hangar`.",
                    longHelp="Equip the requested item from your hangar onto your active ship. Item numbers are shown next " \
                                + "to items in your `hangar`. When equipping a ship, specify `transfer` to move all items " \
                                + "to the new ship.")


async def cmd_unequip(message : discord.Message, args : str, isDM : bool):
    """Unequip the item of the given item type, at the given index, from the user's active ship.

    :param discord.Message message: the discord message calling the command
    :param str args: string containing either "all", or (an item type and either an index number or "all",
                        separated by a single space)
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    argsSplit = args.split(" ")
    unequipAllItems = len(argsSplit) > 0 and argsSplit[0] == "all"

    if isDM:
        prefix = cfg.defaultCommandPrefix
    else:
        prefix = botState.guildsDB.getGuild(message.guild.id).commandPrefix

    if not unequipAllItems and len(argsSplit) < 2:
        await message.reply(mention_author=False, content=":x: Not enough arguments! Please provide both an item type (all/weapon/module/turret) " \
                                    + "and an item number from `" + prefix + "hangar` or `all`.")
        return
    if len(argsSplit) > 2:
        await message.reply(mention_author=False, content=":x: Too many arguments! Please only give an item type (all/weapon/module/turret), " \
                                    + "an item number or `all`.")
        return

    requestedBBUser = botState.usersDB.getOrAddID(message.author.id)

    if unequipAllItems:
        requestedBBUser.unequipAll(requestedBBUser.activeShip)

        await message.reply(mention_author=False, content=":wrench: You unequipped **all items** from your ship.")
        return

    item = argsSplit[0].rstrip("s")
    if item not in cfg.validItemNames:
        await message.reply(mention_author=False, content=":x: Invalid item name! Please choose from: weapon, module or turret.")
        return
    if item == "ship":
        await message.reply(mention_author=False, content=":x: You can't go without a ship! Instead, switch to another one.")
        return

    unequipAll = argsSplit[1] == "all"
    if not unequipAll:
        itemNum = argsSplit[1]
        if not lib.stringTyping.isInt(itemNum):
            await message.reply(mention_author=False, content=":x: Invalid item number!")
            return
        itemNum = int(itemNum)
        if itemNum > len(requestedBBUser.activeShip.getActivesByName(item)):
            await message.reply(mention_author=False, content=":x: Invalid item number! Your ship has " \
                                        + str(len(requestedBBUser.activeShip.getActivesByName(item))) + " " + item + "s.")
            return
        if itemNum < 1:
            await message.reply(mention_author=False, content=":x: Invalid item number! Must be at least 1.")
            return
    else:
        itemNum = None

    if item == "weapon":
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

    elif item == "module":
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

    elif item == "turret":
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
        raise NotImplementedError("Valid but unsupported item name: " + item)

botCommands.register("unequip", cmd_unequip, 0, allowDM=True, helpSection="loadout",
                    signatureStr="**unequip <item-type> <item-num>**",
                    shortHelp="Move an item from your active ship to your hangar. Item numbers can be gotten from `loadout`.",
                    longHelp="Unequip the requested item from your active ship, into your hangar. Item numbers are shown " \
                                + "next to items in your `loadout`.")


async def cmd_nameship(message : discord.Message, args : str, isDM : bool):
    """Set the nickname of the active ship.

    :param discord.Message message: the discord message calling the command
    :param str args: string containing the new nickname.
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    if botState.usersDB.idExists(message.author.id):
        requestedBBUser = botState.usersDB.getUser(message.author.id)
    else:
        requestedBBUser = botState.usersDB.addID(message.author.id)

    if requestedBBUser.activeShip is None:
        await message.reply(mention_author=False, content=":x: You do not have a ship equipped!")
        return

    if args == "":
        await message.reply(mention_author=False, content=":x: Not enough arguments. Please give the new nickname!")
        return

    if (message.author.id not in cfg.developers and len(args) > cfg.maxShipNickLength) or \
            len(args) > cfg.maxDevShipNickLength:
        await message.reply(mention_author=False, content=":x: Nicknames must be " + str(cfg.maxShipNickLength) + " characters or less!")
        return

    requestedBBUser.activeShip.changeNickname(args)
    await message.reply(mention_author=False, content=":pencil: You named your " + requestedBBUser.activeShip.name + ": **" + args + "**.")

botCommands.register("nameship", cmd_nameship, 0, forceKeepArgsCasing=True, allowDM=True, helpSection="loadout",
                    signatureStr="**nameShip <nickname>**", shortHelp="Give your active ship a nickname!",
                    longHelp="Give your active ship a nickname! The character limit for ship nicknames is 30.")


async def cmd_unnameship(message : discord.Message, args : str, isDM : bool):
    """Remove the nickname of the active ship.

    :param discord.Message message: the discord message calling the command
    :param str args: ignored
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    if botState.usersDB.idExists(message.author.id):
        requestedBBUser = botState.usersDB.getUser(message.author.id)
    else:
        requestedBBUser = botState.usersDB.addID(message.author.id)

    if requestedBBUser.activeShip is None:
        await message.reply(mention_author=False, content=":x: You do not have a ship equipped!")
        return

    if not requestedBBUser.activeShip.hasNickname:
        await message.reply(mention_author=False, content=":x: Your active ship does not have a nickname!")
        return

    requestedBBUser.activeShip.removeNickname()
    await message.reply(mention_author=False, content=":pencil: You reset your **" + requestedBBUser.activeShip.name + "**'s nickname.")

botCommands.register("unnameship", cmd_unnameship, 0, allowDM=True, helpSection="loadout", signatureStr="**unnameShip**",
                    shortHelp="Reset your active ship's nickname.")
