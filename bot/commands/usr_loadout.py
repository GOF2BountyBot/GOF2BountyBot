from typing import cast
import discord

from ..gameObjects.items.ships import shipItem

from . import commandsDB as textCommandsDB
from .. import lib, botState
from ..cfg import cfg, bbData
from ..cfg.bbData import ItemCategory, ItemCategoryOrAll
from ..users import basedUser
from ..gameObjects.items import gameItem
from ..gameObjects.inventories import inventory


textCommandsDB.addHelpSection(0, "loadout")


async def cmd_unequip(message: discord.Message, args: str, isDM: bool):
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
        prefix = botState.client.guildsDB.getGuild(message.guild.id).commandPrefix

    if not unequipAllItems and len(argsSplit) < 2:
        await message.reply(mention_author=False, content=":x: Not enough arguments! Please provide both an item type (all/weapon/module/turret) " \
                                    + "and an item number from `" + prefix + "hangar` or `all`.")
        return
    if len(argsSplit) > 2:
        await message.reply(mention_author=False, content=":x: Too many arguments! Please only give an item type (all/weapon/module/turret), " \
                                    + "an item number or `all`.")
        return

    requestedBBUser = botState.client.usersDB.getOrAddID(message.author.id)

    if unequipAllItems:
        requestedBBUser.unequipAll(requestedBBUser.activeShip)

        await message.reply(mention_author=False, content=":wrench: You unequipped **all items** from your ship.")
        return

    _item = argsSplit[0].rstrip("s")
    if not ItemCategory.hasValue(_item):
        await message.reply(":x: Invalid item name! Please choose from: ship, weapon, module or turret.",
                            mention_author=False)
        return
    item = ItemCategory(_item)

    if item is ItemCategory.ship:
        await message.reply(mention_author=False, content=":x: You can't go without a ship! Instead, switch to another one.")
        return

    unequipAll = argsSplit[1] == "all"
    if not unequipAll:
        itemNum = argsSplit[1]
        if not lib.stringTyping.isInt(itemNum):
            await message.reply(mention_author=False, content=":x: Invalid item number!")
            return
        itemNum = int(itemNum)
        if itemNum > len(requestedBBUser.activeShip.getActives(item)):
            await message.reply(mention_author=False, content=":x: Invalid item number! Your ship has " \
                                        + str(len(requestedBBUser.activeShip.getActives(item))) + " " + item.value + "s.")
            return
        if itemNum < 1:
            await message.reply(mention_author=False, content=":x: Invalid item number! Must be at least 1.")
            return
    else:
        itemNum = None

    if item is ItemCategory.weapon:
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

    elif item is ItemCategory.module:
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

    elif item is ItemCategory.turret:
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
        raise NotImplementedError("Valid but unsupported item name: " + item.value)

textCommandsDB.register("unequip", cmd_unequip, 0, allowDM=True, helpSection="loadout",
                    signatureStr="**unequip <item-type> <item-num>**",
                    shortHelp="Move an item from your active ship to your hangar. Item numbers can be gotten from `loadout`.",
                    longHelp="Unequip the requested item from your active ship, into your hangar. Item numbers are shown " \
                                + "next to items in your `loadout`.")


async def cmd_nameship(message: discord.Message, args: str, isDM: bool):
    """Set the nickname of the active ship.

    :param discord.Message message: the discord message calling the command
    :param str args: string containing the new nickname.
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    if botState.client.usersDB.idExists(message.author.id):
        requestedBBUser = botState.client.usersDB.getUser(message.author.id)
    else:
        requestedBBUser = botState.client.usersDB.addID(message.author.id)

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

textCommandsDB.register("nameship", cmd_nameship, 0, forceKeepArgsCasing=True, allowDM=True, helpSection="loadout",
                    signatureStr="**nameShip <nickname>**", shortHelp="Give your active ship a nickname!",
                    longHelp="Give your active ship a nickname! The character limit for ship nicknames is 30.")


async def cmd_unnameship(message: discord.Message, args: str, isDM: bool):
    """Remove the nickname of the active ship.

    :param discord.Message message: the discord message calling the command
    :param str args: ignored
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    if botState.client.usersDB.idExists(message.author.id):
        requestedBBUser = botState.client.usersDB.getUser(message.author.id)
    else:
        requestedBBUser = botState.client.usersDB.addID(message.author.id)

    if requestedBBUser.activeShip is None:
        await message.reply(mention_author=False, content=":x: You do not have a ship equipped!")
        return

    if not requestedBBUser.activeShip.hasNickname:
        await message.reply(mention_author=False, content=":x: Your active ship does not have a nickname!")
        return

    requestedBBUser.activeShip.removeNickname()
    await message.reply(mention_author=False, content=":pencil: You reset your **" + requestedBBUser.activeShip.name + "**'s nickname.")

textCommandsDB.register("unnameship", cmd_unnameship, 0, allowDM=True, helpSection="loadout", signatureStr="**unnameShip**",
                    shortHelp="Reset your active ship's nickname.")
