from typing import Awaitable, Callable, cast
import discord

from . import commandsDB as botCommands
from ..cfg import cfg, bbData
from ..gameObjects.items import shipItem
from .. import lib, botState
from ..shipRenderer import shipRenderer
import importlib
cmd_showme_ship = cast(Callable[[discord.Message, str, bool], Awaitable], importlib.import_module("bot.commands.usr_gof2-info").cmd_showme_ship)
from datetime import datetime

import os
CWD = os.getcwd()

PAINTBRUSH_ICON = "https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/twitter/282/paintbrush_1f58c-fe0f.png"


botCommands.addHelpSection(3, "skins")


async def dev_cmd_addSkin(message : discord.Message, args : str, isDM : bool):
    """Make the specified ship compatible with the specified skin.

    :param discord.Message message: the discord message calling the command
    :param str args: string containing a ship name and a skin, prefaced with a + character.
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    # verify a item was given
    if args == "":
        if isDM:
            prefix = cfg.defaultCommandPrefix
        else:
            prefix = botState.client.guildsDB.getGuild(message.guild.id).commandPrefix
        await message.reply(mention_author=False, content=":x: Please provide a ship! Example: `" + prefix + "ship Groza Mk II`")
        return

    if "+" in args:
        if len(args.split("+")) > 2:
            await message.reply(mention_author=False, content=":x: Please only provide one skin, with one `+`!")
            return
        args, skin = args.split("+")
    else:
        skin = ""

    # look up the ship object
    itemName = args.rstrip(" ").title()
    itemObj = None
    for ship in bbData.builtInShipData.values():
        shipObj = shipItem.Ship.deserialize(ship)
        if shipObj.isCalled(itemName):
            itemObj = shipObj

    # report unrecognised ship names
    if itemObj is None:
        if len(itemName) < 20:
            await message.reply(mention_author=False, content=":x: **" + itemName + "** is not in my database! :detective:")
        else:
            await message.reply(mention_author=False, content=":x: **" + itemName[0:15] + "**... is not in my database! :detective:")
        return

    if skin != "":
        skin = skin.lstrip(" ").lower()
        if skin not in bbData.builtInShipSkins:
            if len(skin) < 20:
                await message.reply(mention_author=False, content=":x: The **" + skin + "** skin is not in my database! :detective:")
            else:
                await message.reply(mention_author=False, content=":x: The **" + skin[0:15] + "**... skin is not in my database! :detective:")

        elif skin in bbData.builtInShipData[itemObj.name]["compatibleSkins"]:
            await message.reply(mention_author=False, content=":x: That skin is already compatible with the **" + itemObj.name + "**!")

        else:
            await lib.discordUtil.startLongProcess(message)
            await bbData.builtInShipSkins[skin].addShip(itemObj.name, botState.client.skinStorageChannel)
            await lib.discordUtil.endLongProcess(message)
            await message.reply(mention_author=False, content="Done!")

    else:
        await message.reply(mention_author=False, content=":x: Please provide a skin, prefaced by a `+`!")

botCommands.register("addSkin", dev_cmd_addSkin, 3, helpSection="skins", useDoc=True)


async def dev_cmd_delSkin(message : discord.Message, args : str, isDM : bool):
    """Remove the specified ship's compatibility with the specified skin.

    :param discord.Message message: the discord message calling the command
    :param str args: string containing a ship name and a skin, prefaced with a + character.
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    # verify a item was given
    if args == "":
        if isDM:
            prefix = cfg.defaultCommandPrefix
        else:
            prefix = botState.client.guildsDB.getGuild(message.guild.id).commandPrefix
        await message.reply(mention_author=False, content=":x: Please provide a ship! Example: `" + prefix + "ship Groza Mk II`")
        return

    if "+" in args:
        if len(args.split("+")) > 2:
            await message.reply(mention_author=False, content=":x: Please only provide one skin, with one `+`!")
            return
        args, skin = args.split("+")
    else:
        skin = ""

    # look up the ship object
    itemName = args.rstrip(" ").title()
    itemObj = None
    for ship in bbData.builtInShipData.values():
        shipObj = shipItem.Ship.deserialize(ship)
        if shipObj.isCalled(itemName):
            itemObj = shipObj

    # report unrecognised ship names
    if itemObj is None:
        if len(itemName) < 20:
            await message.reply(mention_author=False, content=":x: **" + itemName + "** is not in my database! :detective:")
        else:
            await message.reply(mention_author=False, content=":x: **" + itemName[0:15] + "**... is not in my database! :detective:")
        return

    if skin != "":
        skin = skin.lstrip(" ").lower()
        if skin not in bbData.builtInShipSkins:
            if len(skin) < 20:
                await message.reply(mention_author=False, content=":x: The **" + skin + "** skin is not in my database! :detective:")
            else:
                await message.reply(mention_author=False, content=":x: The **" + skin[0:15] + "**... skin is not in my database! :detective:")

        elif skin not in bbData.builtInShipData[itemObj.name]["compatibleSkins"]:
            await message.reply(mention_author=False, content=":x: That skin is already incompatible with the **" + itemObj.name + "**!")

        else:
            await bbData.builtInShipSkins[skin].removeShip(itemObj.name, botState.client.skinStorageChannel)
            await message.reply(mention_author=False, content="Done!")

    else:
        await message.reply(mention_author=False, content=":x: Please provide a skin, prefaced by a `+`!")

botCommands.register("delSkin", dev_cmd_delSkin, 3, helpSection="skins", useDoc=True)


async def dev_cmd_makeSkin(message : discord.Message, args : str, isDM : bool):
    """Make the specified ship compatible with the specified skin.

    :param discord.Message message: the discord message calling the command
    :param str args: string containing a ship name and a skin, prefaced with a + character.
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    # verify a item was given
    if args == "":
        if isDM:
            prefix = cfg.defaultCommandPrefix
        else:
            prefix = botState.client.guildsDB.getGuild(message.guild.id).commandPrefix
        await message.reply(mention_author=False, content=":x: Please provide a ship! Example: `" + prefix + "ship Groza Mk II`")
        return

    if "+" in args:
        if len(args.split("+")) > 2:
            await message.reply(mention_author=False, content=":x: Please only provide one skin, with one `+`!")
            return
        args, skin = args.split("+")
    else:
        skin = ""

    # look up the ship object
    itemName = args.rstrip(" ").title()
    itemObj = None
    for ship in bbData.builtInShipData.values():
        shipObj = shipItem.Ship.deserialize(ship)
        if shipObj.isCalled(itemName):
            itemObj = shipObj

    # report unrecognised ship names
    if itemObj is None:
        if len(itemName) < 20:
            await message.reply(mention_author=False, content=":x: **" + itemName + "** is not in my database! :detective:")
        else:
            await message.reply(mention_author=False, content=":x: **" + itemName[0:15] + "**... is not in my database! :detective:")
        return

    if skin != "":
        skin = skin.lstrip(" ").lower()
        if skin not in bbData.builtInShipSkins:
            if len(skin) < 20:
                await message.reply(mention_author=False, content=":x: The **" + skin + "** skin is not in my database! :detective:")
            else:
                await message.reply(mention_author=False, content=":x: The **" + skin[0:15] + "**... skin is not in my database! :detective:")

        elif skin in bbData.builtInShipData[itemObj.name]["compatibleSkins"]:
            await message.reply(mention_author=False, content=":x: That skin is already compatible with the **" + itemObj.name + "**!")

        else:
            await bbData.builtInShipSkins[skin].addShip(itemObj.name, botState.client.skinStorageChannel)
            await message.reply(mention_author=False, content="Done!")

    else:
        await message.reply(mention_author=False, content=":x: Please provide a skin, prefaced by a `+`!")

botCommands.register("makeSkin", dev_cmd_makeSkin, 3, helpSection="skins", useDoc=True)


async def dev_cmd_applySkin(message : discord.Message, args : str, isDM : bool):
    """Apply the specified ship skin to the equipped ship.

    :param discord.Message message: the discord message calling the command
    :param str args: string containing a skin name
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    # verify a item was given
    if args == "":
        await message.reply(mention_author=False, content=":x: Please provide a skin!")
        return

    activeShip = botState.client.usersDB.getOrAddID(message.author.id).activeShip
    if activeShip.isSkinned:
        await message.reply(mention_author=False, content=":x: Your ship already has a skin applied!")
        return

    if args != "":
        skin = args.lower()
        if skin not in bbData.builtInShipSkins:
            if len(skin) < 20:
                await message.reply(mention_author=False, content=":x: The **" + skin + "** skin is not in my database! :detective:")
            else:
                await message.reply(mention_author=False, content=":x: The **" + skin[0:15] + "**... skin is not in my database! :detective:")

        elif skin not in bbData.builtInShipData[activeShip.name]["compatibleSkins"]:
            await message.reply(mention_author=False, content=":x: That skin is incompatible with your active ship! (" + activeShip.name + ")")

        else:
            activeShip.applySkin(bbData.builtInShipSkins[skin])
            await message.reply(mention_author=False, content="Done!")

botCommands.register("applySkin", dev_cmd_applySkin, 3, helpSection="skins", useDoc=True)


async def dev_cmd_unapplySkin(message : discord.Message, args : str, isDM : bool):
    """Remove the applied skin from the active ship.

    :param discord.Message message: the discord message calling the command
    :param str args: ignored
    :param bool isDM: Whether or not the command is being called from a DM channel
    """

    activeShip = botState.client.usersDB.getOrAddID(message.author.id).activeShip
    if not activeShip.isSkinned:
        await message.reply(mention_author=False, content=":x: Your ship has no skin applied!")
    elif not activeShip.builtIn:
        await message.reply(mention_author=False, content=":x: Your ship is not built in, so the original icon cannot be recovered.")
    else:
        activeShip.icon = bbData.builtInShipData[activeShip.name]["icon"]
        activeShip.skin = None
        activeShip.isSkinned = False
        await message.reply(mention_author=False, content="Done!")

botCommands.register("unApplySkin", dev_cmd_unapplySkin, 3, helpSection="skins", useDoc=True)


async def dev_cmd_add_skin_to_all_ships(message : discord.Message, args : str, isDM : bool):
    """Make all ships in the game compatible with the specified skin.

    :param discord.Message message: the discord message calling the command
    :param str args: string containing a skin name
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    # verify a item was given
    if args == "":
        await message.reply(mention_author=False, content=":x: Please provide a skin!")
        return

    skin = args.strip(" ").lower()
    if skin not in bbData.builtInShipSkins:
        if len(skin) < 20:
            await message.reply(mention_author=False, content=":x: The **" + skin + "** skin is not in my database! :detective:")
        else:
            await message.reply(mention_author=False, content=":x: The **" + skin[0:15] + "**... skin is not in my database! :detective:")

    await lib.discordUtil.startLongProcess(message)
    skinStorageChannel = botState.client.get_guild(cfg.mediaServer).get_channel(cfg.skinRendersChannel)

    for shipName in bbData.builtInShipData:
        if bbData.builtInShipData[shipName]["skinnable"] and skin not in bbData.builtInShipData[shipName]["compatibleSkins"]:
            try:
                await bbData.builtInShipSkins[skin].addShip(shipName, skinStorageChannel)
            except shipRenderer.RenderFailed:
                pass

    await lib.discordUtil.endLongProcess(message)
    await message.reply(mention_author=False, content="Done!")

botCommands.register("add-skin-to-all-ships", dev_cmd_add_skin_to_all_ships, 3, helpSection="skins", useDoc=True)


async def dev_cmd_del_skin_from_all_ships(message : discord.Message, args : str, isDM : bool):
    """Make all ships in the game incompatible with the specified skin.

    :param discord.Message message: the discord message calling the command
    :param str args: string containing a skin name
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    # verify a item was given
    if args == "":
        await message.reply(mention_author=False, content=":x: Please provide a skin!")
        return

    skin = args.strip(" ").lower()
    if skin not in bbData.builtInShipSkins:
        if len(skin) < 20:
            await message.reply(mention_author=False, content=":x: The **" + skin + "** skin is not in my database! :detective:")
        else:
            await message.reply(mention_author=False, content=":x: The **" + skin[0:15] + "**... skin is not in my database! :detective:")

    await lib.discordUtil.startLongProcess(message)

    for shipName in bbData.builtInShipData:
        if bbData.builtInShipData[shipName]["skinnable"] and skin in bbData.builtInShipData[shipName]["compatibleSkins"]:
            await bbData.builtInShipSkins[skin].removeShip(shipName, botState.client.skinStorageChannel)

    await lib.discordUtil.endLongProcess(message)
    await message.reply(mention_author=False, content="Done!")

botCommands.register("del-skin-from-all-ships", dev_cmd_del_skin_from_all_ships, 3, helpSection="skins", useDoc=True)


async def dev_cmd_show_incompatible_skin(message : discord.Message, args : str, isDM : bool):
    """Return the URL of the image bountybot uses to represent the specified inbuilt ship

    :param discord.Message message: the discord message calling the command
    :param str args: string containing a ship name and optionally a skin, prefaced with a + character.
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    commandPrefix = cfg.defaultCommandPrefix if isDM else botState.client.guildsDB.getGuild(message.guild.id).commandPrefix
    # verify a item was given
    if args == "":
        await message.channel.send(":x: Please provide a ship! Example: `" + commandPrefix + "ship Groza Mk II`")
        return
    if "+" in args:
        if len(args.split("+")) > 2:
            await message.channel.send(":x: Please only provide one skin, with one `+`!")
            return
        elif args.split("+")[1] == "":
            await message.channel.send(":x: Please either give a skin name after your `+`")
            return
        else:
            args, skin = args.split("+")
    else:
        skin = ""

    # look up the ship object
    itemName = args.rstrip(" ").title()
    itemObj = None
    for ship in bbData.builtInShipData.values():
        shipObj = shipItem.Ship.deserialize(ship)
        if shipObj.isCalled(itemName):	
            itemObj = shipObj
    # report unrecognised ship names
    if itemObj is None:
        if len(itemName) < 20:
            await message.channel.send(":x: **" + itemName + "** is not in my database! :detective:")
        else:
            await message.channel.send(":x: **" + itemName[0:15] + "**... is not in my database! :detective:")
        return

    shipData = bbData.builtInShipData[itemObj.name]

    if not shipData["skinnable"]:
        await message.channel.send(":x: That ship is not skinnable!")
        return
    else:
        skin = skin.lstrip(" ").lower()
        if skin not in bbData.builtInShipSkins:
            if len(itemName) < 20:
                await message.channel.send(":x: The **" + skin + "** skin is not in my database! :detective:")
            else:
                await message.channel.send(":x: The **" + skin[0:15] + "**... skin is not in my database! :detective:")

        elif skin in bbData.builtInShipData[itemObj.name]["compatibleSkins"]:
            itemEmbed = lib.discordUtil.makeEmbed(col=discord.Colour.random(),
                                                    img=bbData.builtInShipSkins[skin].shipRenders[itemObj.name][0],
                                                    titleTxt=itemObj.name, footerTxt="Custom skin: " + skin.capitalize())
            await message.channel.send(embed=itemEmbed)

        else:
            skinRendersChannel = botState.client.get_guild(cfg.mediaServer).get_channel(cfg.skinRendersChannel)
            await lib.discordUtil.startLongProcess(message)
            await bbData.builtInShipSkins[skin].addShip(itemObj.name, skinRendersChannel)
            itemEmbed = lib.discordUtil.makeEmbed(col=discord.Colour.random(),
                                                    img=bbData.builtInShipSkins[skin].shipRenders[itemObj.name][0],
                                                    titleTxt=itemObj.name, footerTxt="Custom skin: " + skin.capitalize())
            await message.channel.send(embed=itemEmbed)
            await bbData.builtInShipSkins[skin].removeShip(itemObj.name, skinRendersChannel)
            await lib.discordUtil.endLongProcess(message)


botCommands.register("show-incompatible-skin", dev_cmd_show_incompatible_skin, 3, helpSection="skins", useDoc=True)


async def dev_cmd_try_all_skins(message : discord.Message, args : str, isDM : bool):
    """Return the URL of the image bountybot uses to represent the specified inbuilt ship
    :param discord.Message message: the discord message calling the command
    :param str args: string containing a ship name and optionally a skin, prefaced with a + character.
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    commandPrefix = cfg.defaultCommandPrefix if isDM else botState.client.guildsDB.getGuild(message.guild.id).commandPrefix

    # verify a item was given
    if args == "":
        await message.channel.send(":x: Please provide a ship! Example: `" + commandPrefix + "ship Groza Mk II`")
        return

    # look up the ship object
    itemName = args.rstrip(" ").title()
    itemObj = None
    for ship in bbData.builtInShipData.values():
        shipObj = shipItem.Ship.deserialize(ship)
        if shipObj.isCalled(itemName):	
            itemObj = shipObj
    # report unrecognised ship names
    if itemObj is None:
        if len(itemName) < 20:
            await message.channel.send(":x: **" + itemName + "** is not in my database! :detective:")
        else:
            await message.channel.send(":x: **" + itemName[0:15] + "**... is not in my database! :detective:")
        return

    shipData = bbData.builtInShipData[itemObj.name]

    if not shipData["skinnable"]:
        await message.channel.send(":x: That ship is not skinnable!")
        return
    else:
        for skin in bbData.builtInShipSkins:
            if skin not in bbData.builtInShipSkins:
                await message.channel.send("Ignoring unrecognised skin: " + skin)

            elif skin in bbData.builtInShipData[itemObj.name]["compatibleSkins"]:
                itemEmbed = lib.discordUtil.makeEmbed(col=discord.Colour.random(),
                                                        img=bbData.builtInShipSkins[skin].shipRenders[itemObj.name][0],
                                                        titleTxt=itemObj.name, footerTxt="Custom skin: " + skin.capitalize())
                await message.channel.send(embed=itemEmbed)

            else:
                skinRendersChannel = botState.client.get_guild(cfg.mediaServer).get_channel(cfg.skinRendersChannel)
                await bbData.builtInShipSkins[skin].addShip(itemObj.name, skinRendersChannel)
                itemEmbed = lib.discordUtil.makeEmbed(col=discord.Colour.random(),
                                                        img=bbData.builtInShipSkins[skin].shipRenders[itemObj.name][0],
                                                        titleTxt=itemObj.name, footerTxt="Custom skin: " + skin.capitalize())
                await message.channel.send(embed=itemEmbed)
                await bbData.builtInShipSkins[skin].removeShip(itemObj.name, skinRendersChannel)

    await message.channel.send("ALL SKINS SENT")

botCommands.register("try-all-skins", dev_cmd_try_all_skins, 3, helpSection="skins", useDoc=True)


async def dev_cmd_set_autoskin_resolution(message : discord.Message, args : str, isDM : bool):
    """Configure the resolution that cmd_showme_ship will render to.

    :param discord.Message message: the discord message calling the command
    :param str args: string containing the x resolution followed by the y resolution split by a space
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    argsSplit = args.split(" ")
    if len(argsSplit) < 2 or "" in argsSplit:
        await message.reply(":x: Please provide an x and y resolution split by a space", mention_author=False)
        return

    resX, resY = argsSplit
    if not lib.stringTyping.isInt(resX):
        await message.reply(f":x: '{resX}' is not an integer.", mention_author=False)
        return
    if not lib.stringTyping.isInt(resY):
        await message.reply(f":x: '{resY}' is not an integer.", mention_author=False)
        return

    cfg.skinRenderShowmeResolution = [int(resX), int(resY)]
    await message.reply(f"✅ Done!", mention_author=False)

botCommands.register("set-showme-res", dev_cmd_set_autoskin_resolution, 3, helpSection="skins", useDoc=True)


async def dev_cmd_set_autoskin_samples(message : discord.Message, args : str, isDM : bool):
    """Configure the samples that cmd_showme_ship will render to.

    :param discord.Message message: the discord message calling the command
    :param str args: string containing the samples
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    if not lib.stringTyping.isInt(args):
        await message.reply(f":x: '{args}' is not an integer.", mention_author=False)
        return

    cfg.skinRenderShowmeSamples = int(args)
    await message.reply(f"✅ Done!", mention_author=False)

botCommands.register("set-showme-samples", dev_cmd_set_autoskin_samples, 3, helpSection="skins", useDoc=True)


async def dev_cmd_get_autoskin_configuration(message : discord.Message, args : str, isDM : bool):
    """Get the current configuration for rendering with cmd_showme_ship

    :param discord.Message message: the discord message calling the command
    :param str args: ignored
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    e = lib.discordUtil.makeEmbed(authorName="Ship Renderer Configuration",
                                    icon=PAINTBRUSH_ICON, desc="For command: `$showme ship`",
                                    col=discord.Colour.random())
    e.add_field(name="Samples", value=str(cfg.skinRenderShowmeSamples))
    e.add_field(name="Resolution", value=f"x: {cfg.skinRenderShowmeResolution[0]}\ny: {cfg.skinRenderShowmeResolution[1]}")
    await message.reply(mention_author=False, embed=e)

botCommands.register("showme-config", dev_cmd_get_autoskin_configuration, 3, helpSection="skins", useDoc=True)


async def dev_cmd_timed_showme_ship(message : discord.Message, args : str, isDM : bool):
    """Perform cmd_showme_ship, but also send the amount of time taken to execute

    :param discord.Message message: the discord message calling the command
    :param str args: same as showme_ship but without "ship"
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    now = datetime.utcnow()
    await cmd_showme_ship(message, args, isDM)
    await message.reply(f"This command took: {lib.timeUtil.td_format_noYM(datetime.utcnow() - now)}", mention_author=False)
    

botCommands.register("timed-showme-ship", dev_cmd_timed_showme_ship, 3, helpSection="skins", useDoc=True)
