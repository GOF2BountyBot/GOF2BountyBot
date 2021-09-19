from typing import cast
import discord # type: ignore[import]
import aiohttp
import os
import shutil

from . import commandsDB as botCommands
from .. import botState, lib
from ..cfg import cfg, bbData
from ..gameObjects.userProfile.medal import Medal
from ..users.basedUser import BasedUser
from ..reactionMenus import confirmationReactionMenu


botCommands.addHelpSection(3, "medals")


async def dev_cmd_create_medal(message : discord.Message, args : str, isDM : bool):
    """developer command creating a new medal.
    Args must contain the name of the medal, followed by a new line, followed by the medal description.
    To include new line characters in the medal description, use the keyword `{NL}`.
    If further new lines are included, the following lines are treated as kwargs.
    Kwargs can be one of `icon`, `wiki` or `emoji`.
    At least one of `icon` or `emoji` must be given, *or* these can be specified by attaching an image to message.

    This command has forceKeepArgsCasing ENABLED.

    :param discord.Message message: the discord message calling the command
    :param str args: The medal attributes as specified above
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    lines = args.split("\n")
    if len(lines) < 2:
        await message.reply(":x: Args must be on at least two lines: name followed by description")
        return
    medalName = lines[0]
    if medalName.lower() in bbData.medalObjs:
        await message.reply(":x: A medal with that name already exists")
        return

    medalDesc = lines[1]

    kwargs = {"icon": "", "wiki": "", "emoji": lib.emojis.BasedEmoji.EMPTY}

    if len(lines) == 2 or not any(l.startswith("icon=") or l.startswith("emoji=") for l in lines):
        if not message.attachments:
            await message.reply(":x: You must either attach an image or give at least one of `icon` or `emoji`.")
            return
    if len(lines) > 2:
        for lineNum, line in enumerate(lines[2:]):
            if line.startswith("icon="):
                if kwargs["icon"] != "":
                    await message.reply(":x: You can only specify icon once!")
                    return
                kwargs["icon"] = line[len("icon="):]

            elif line.startswith("emoji="):
                if kwargs["emoji"] != lib.emojis.BasedEmoji.EMPTY:
                    await message.reply(":x: You can only specify emoji once!")
                    return
                try:
                    kwargs["emoji"] = lib.emojis.BasedEmoji.fromStr(line[len("emoji="):], rejectInvalid=True)
                except (lib.exceptions.UnrecognisedEmojiFormat, TypeError) as e:
                    await message.reply(f"Invalid emoji: {line[len('emoji='):]}")
                    return
                except lib.exceptions.UnrecognisedCustomEmoji as e:
                    await message.reply(f"Unrecognised emoji: {line[len('emoji='):]}\nPlease make sure I can access it.")
                    return
            elif line.startswith("wiki="):
                if kwargs["wiki"] != "":
                    await message.reply(":x: You can only specify wiki once!")
                    return
                kwargs["wiki"] = line[len("wiki="):]
            else:
                await message.reply(":x: Unrecognised kwarg on your " \
                                    + f"{lineNum+3}{lib.stringTyping.getNumExtension(lineNum+3)} line.")
                return

    noIcon = kwargs["icon"] == ""
    noEmoji = kwargs["emoji"] == lib.emojis.BasedEmoji.EMPTY

    if not noEmoji and noIcon and cast(lib.emojis.BasedEmoji, kwargs["emoji"]).isUnicode:
        await message.reply(":x: I can't extract icons from unicode emojis.\nPlease either provide a custom emoji, an icon" \
                            + " kwarg, or an attached icon image.")
        return

    if message.attachments:
        if not message.attachments[0].content_type.startswith("image"):
            await message.reply(":x: Your attachment must be an image!")
            return
        
        if not noIcon and not noEmoji:
            await message.reply("icon and emoji already supplied. Ignoring attachment.")
        else:
            iconFile = await message.attachments[0].to_file()
            emojiServer: discord.Guild = botState.client.get_guild(cfg.emojisServer) or \
                                        await botState.client.fetch_guild(cfg.emojisServer)
            if emojiServer is None:
                botState.logger.log("dev_medals", "dev_cmd_create_medal", "Failed to find cfg.emojisServer",
                                    eventType="UKWN_GLD")
                await message.reply(":x: Failed to connect to the emojisServer")
                return
            
            if noIcon:
                medalIconsChannel: discord.TextChannel = emojiServer.get_channel(cfg.medalIconsChannel)
                if medalIconsChannel is None:
                    await emojiServer.fetch_channels()
                medalIconsChannel = emojiServer.get_channel(cfg.medalIconsChannel)
                if medalIconsChannel is None:
                    botState.logger.log("dev_medals", "dev_cmd_create_medal", "Failed to find cfg.medalIconsChannel",
                                        eventType="UKWN_CHN")
                    await message.reply(":x: Failed to connect to the medalIconsChannel")
                    return

                try:
                    iconMsg: discord.Message = await medalIconsChannel.send(f"Medal: {medalName}", file=iconFile)
                except (discord.Forbidden, discord.HTTPException) as e:
                    await message.reply(f":x: Saving the icon to the emojiServer failed: {e}")
                    botState.logger.log("dev_medals", "dev_cmd_create_medal", str(e), exception=e)
                    return
                else:
                    kwargs["icon"] = iconMsg.attachments[0].url

            if noEmoji:
                try:
                    newEmoji: discord.Emoji = await emojiServer.create_custom_emoji(name=medalName.replace(" ", "_"),
                                                                                    image=await message.attachments[0].read(),
                                                                                    reason="dev_cmd_create_medal")
                except (discord.Forbidden, discord.HTTPException) as e:
                    await message.reply(f":x: Failed to create medal emoji: {e}")
                    botState.logger.log("dev_medals", "dev_cmd_create_medal", str(e), exception=e)
                    try:
                        await iconMsg.delete()
                    except (discord.NotFound, discord.HTTPException):
                        pass
                    return
                kwargs["emoji"] = lib.emojis.BasedEmoji(id=newEmoji.id)
            
            iconFile.close()
                    
    else:
        emojiServer = botState.client.get_guild(cfg.emojisServer) or \
                                    await botState.client.fetch_guild(cfg.emojisServer)
        if emojiServer is None:
            botState.logger.log("dev_medals", "dev_cmd_create_medal", "Failed to find cfg.emojisServer",
                                eventType="UKWN_GLD")
            await message.reply(":x: Failed to connect to the emojisServer")
            return

        if noEmoji:
            success = False
            async with botState.httpClient.get(cast(str, kwargs["icon"])) as resp:
                try:
                    resp.raise_for_status()
                except aiohttp.ClientResponseError as e:
                    await message.reply("You gave an invalid icon url. Make sure it points directly to an image!\n" \
                                        + str(e))
                else:
                    if not resp.content_type.startswith("image"):
                        await message.reply(f":x: The icon URL must point to an image, yours is a '{resp.content_type}'")
                        success = False
                    else:
                        iconImg = await resp.read()
                        try:
                            newEmoji = await emojiServer.create_custom_emoji(name=medalName,
                                                                                            image=iconImg,
                                                                                            reason="dev_cmd_create_medal")
                        except (discord.Forbidden, discord.HTTPException) as e:
                            await message.reply(f":x: Failed to create medal emoji: {e}")
                            botState.logger.log("dev_medals", "dev_cmd_create_medal", str(e), exception=e)
                            return
                        kwargs["emoji"] = lib.emojis.BasedEmoji(id=newEmoji.id)
            if not success:
                return
        else:
            # When given an emoji but no icon or message attachment, the emoji is ensured earlier to be custom
            dcEmoji: discord.Emoji = botState.client.get_emoji(cast(lib.emojis.BasedEmoji, kwargs["emoji"]).id)
            if dcEmoji is None:
                await message.reply(":x: Failed to get your requested emoji.")
                botState.logger.log("dev_medals", "dev_cmd_create_medal", f"Failed to get given emoji: {kwargs['emoji']}",
                                    eventType="EMOJI_ERR")
                return
            kwargs["icon"] = dcEmoji.url
    
    if kwargs["icon"] == "":
        await message.reply(":x: Failed to infer medal icon. Please provide it explicitly with kwargs.")
        botState.logger.log("dev_medals", "dev_cmd_create_medal", "Failed to infer medal icon", eventType="INFER_FAIL")
        return
    if kwargs["emoji"] == lib.emojis.BasedEmoji.EMPTY:
        await message.reply(":x: Failed to infer medal emoji. Please provide it explicitly with kwargs.")
        botState.logger.log("dev_medals", "dev_cmd_create_medal", "Failed to infer medal emoji", eventType="INFER_FAIL")
        return

    newIcon = cast(str, kwargs.pop("icon"))
    newEmoji = cast(lib.emojis.BasedEmoji, kwargs.pop("emoji"))
    
    newMedal = Medal(medalName, medalDesc, newIcon, newEmoji)
    bbData.medalsData[medalName.lower()] = newMedal.toDict()
    bbData.medalObjs[medalName.lower()] = newMedal

    dirPath = os.path.join(cfg.paths.bbMedalsMETAFolder, medalName + ".bbMedal")
    if not os.path.isdir(dirPath):
        os.makedirs(dirPath)
    filePath = os.path.join(dirPath, "META.json")
    lib.jsonHandler.writeJSON(filePath, newMedal.toDict(), prettyPrint=True)

    await message.reply(f"{cast(lib.emojis.BasedEmoji, cfg.defaultEmojis.submit).sendable} medal added successfuly: {medalName}")


botCommands.register("create-medal", dev_cmd_create_medal, 3, forceKeepArgsCasing=True, allowDM=True, helpSection="medals", useDoc=True)


async def dev_cmd_give_medal(message : discord.Message, args : str, isDM : bool):
    """Developer command adding a medal to a user's profile
    Provide a user ID or mention followed by the medal name

    :param discord.Message message: the discord message calling the command
    :param str args: A string containing a user ID or mention followed by a medal name
    :param bool isDM: Whether or not the command is being called from a DM channel    
    """
    argsSplit = args.split(" ")
    if len(argsSplit) < 2:
        await message.reply(":x: Supply both a user and a medal")
        return
    if not lib.stringTyping.isInt(argsSplit[0]) or lib.stringTyping.isMention(argsSplit[0]):
        await message.reply(":x: Your first argument must be either a user ID or a user mention")
        return

    medalName = args[len(argsSplit[0])+1:]
    if medalName not in bbData.medalObjs:
        await message.reply(f":x: Unknown medal: '{medalName}'")
        return

    userID = int(argsSplit[0].lstrip("<@!").rstrip(">"))
    requestedUser: discord.User = botState.client.get_user(userID) or await botState.client.fetch_user(userID)
    if requestedUser is None:
        await message.reply(":x: Unrecognisd user. Make sure we share a server.")
        return

    requestedBUser: BasedUser = botState.usersDB.getOrAddID(userID)
    medal: Medal = bbData.medalObjs[medalName]
    if medal in requestedBUser.medals:
        await message.reply(f":x: {requestedUser.display_name} already has the {medal.name} medal.")
        return
    
    requestedBUser.medals.add(medal)
    await message.reply(f"{cfg.defaultEmojis.submit} {requestedUser.display_name} was awarded the {medal.name} medal successfuly.")


botCommands.register("give-medal", dev_cmd_give_medal, 3, allowDM=True, helpSection="medals", useDoc=True)


async def dev_cmd_take_medal(message : discord.Message, args : str, isDM : bool):
    """Developer command removing a medal from a user's profile
    Provide a user ID or mention followed by the medal name

    :param discord.Message message: the discord message calling the command
    :param str args: A string containing a user ID or mention followed by a medal name
    :param bool isDM: Whether or not the command is being called from a DM channel    
    """
    argsSplit = args.split(" ")
    if len(argsSplit) < 2:
        await message.reply(":x: Supply both a user and a medal")
        return
    if not lib.stringTyping.isInt(argsSplit[0]) or lib.stringTyping.isMention(argsSplit[0]):
        await message.reply(":x: Your first argument must be either a user ID or a user mention")
        return

    medalName = args[len(argsSplit[0])+1:]
    if medalName not in bbData.medalObjs:
        await message.reply(f":x: Unknown medal: '{medalName}'")
        return

    userID = int(argsSplit[0].lstrip("<@!").rstrip(">"))
    requestedUser: discord.User = botState.client.get_user(userID) or await botState.client.fetch_user(userID)
    if requestedUser is None:
        await message.reply(":x: Unrecognisd user. Make sure we share a server.")
        return

    requestedBUser: BasedUser = botState.usersDB.getOrAddID(userID)
    medal: Medal = bbData.medalObjs[medalName]
    if medal not in requestedBUser.medals:
        await message.reply(f":x: {requestedUser.display_name} already does not have the {medal.name} medal.")
        return
    
    requestedBUser.medals.remove(medal)
    await message.reply(f"{cfg.defaultEmojis.submit} {requestedUser.display_name} was un-awarded the {medal.name} medal successfuly.")


botCommands.register("take-medal", dev_cmd_take_medal, 3, allowDM=True, helpSection="medals", useDoc=True)


async def dev_cmd_delete_medal(message : discord.Message, args : str, isDM : bool):
    """Developer command deleting a medal from the game.

    :param discord.Message message: the discord message calling the command
    :param str args: A string containing a medal name
    :param bool isDM: Whether or not the command is being called from a DM channel    
    """
    if not args:
        await message.reply(":x: Supply a medal name")
        return

    if args not in bbData.medalObjs:
        await message.reply(f":x: Unknown medal: '{args}'")
        return

    medal = bbData.medalObjs[args]
    
    confirmMsg = await message.channel.send(f"Are you sure you want to completely remove the {medal.name} " \
                                            + "medal from the game? The medal will be lazily removed from all owning users.")
    confirmResult = await confirmationReactionMenu.InlineConfirmationMenu(confirmMsg, message.author, 20).doMenu()

    if cfg.defaultEmojis.accept in confirmResult:
        # locate medal META file
        medalFound = False
        for subdir, dirs, _ in lib.jsonHandler.depthLimitedWalk(cfg.paths.bbMedalsMETAFolder, cfg.gameObjectCfgMaxRecursion):
            for dirname in dirs:
                if dirname.lower().endswith(".bbmedal"):
                    dirpath = subdir + os.sep + dirname

                    # Read in the medal metadata
                    if lib.jsonHandler.readJSON(dirpath + os.sep + "META.json")["name"] == medal.name:
                        medalFound = True
                        shutil.rmtree(dirpath)
            
            if medalFound:
                break
        if medalFound:
            del bbData.medalObjs[args]
            await message.reply(f"{cfg.defaultEmojis.submit} The {medal.name} medal was removed from the game successfuly." \
                                + f"\nThe medal's emoji ({medal.emoji.toDict()}) and icon message (if any) were NOT deleted.")
        else:
            await message.reply(":x: The medal's META file could not be located. Medal deletion cancelled.")
    else:
        await message.reply("Medal deletion cancelled.")


botCommands.register("delete-medal", dev_cmd_delete_medal, 3, allowDM=True, helpSection="medals", useDoc=True)
