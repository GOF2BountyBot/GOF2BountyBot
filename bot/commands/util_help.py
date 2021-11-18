import discord
from datetime import timedelta

from . import commandsDB as botCommands
from .. import botState, lib
from ..cfg import cfg
from ..reactionMenus import pagedReactionMenu, expiryFunctions
from ..scheduling import timedTask
from ..users.basedUser import BasedUser


async def util_autohelp(message: discord.Message, args: str, isDM: bool, userAccessLevel: int):
    """Print command help strings for the given access level as an embed.
    If a command is provided in args, the associated help string for just that command is printed.

    :param discord.Message message: the discord message calling the command
    :param str args: empty, or a single command name
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    sendChannel = None
    sendDM = True

    if message.author.dm_channel is None:
        await message.author.create_dm()
    sendChannel = message.author.dm_channel

    if sendChannel == message.channel:
        sendDM = False

    if lib.stringTyping.isInt(args):
        if int(args) < 1 or int(args) > len(botCommands.helpSectionEmbeds[userAccessLevel]):
            await message.reply(mention_author=False, content=":x: Section number must be between 1 and " \
                                        + str(len(botCommands.helpSectionEmbeds[userAccessLevel])) + "!")
            return
        args = list(botCommands.helpSectionEmbeds[userAccessLevel].keys())[int(args) - 1]
    elif args == "misc":
        args = "miscellaneous"

    helpMenuTimeoutStr = lib.timeUtil.td_format_noYM(timedelta(**cfg.timeouts.helpMenu))

    owningUser: BasedUser = None
    newMenu: pagedReactionMenu.PagedReactionMenu = None

    try:
        if args == "":
            owningUser = botState.usersDB.getOrAddID(message.author.id)
            if owningUser.hasMenuOfTypeID("help"):
                await message.reply(mention_author=False,
                                    content=":x: Please close your existing help menu before making a new one!\n" \
                                            + f"In case you can't find it, help menus auto exire after **" \
                                            + helpMenuTimeoutStr + "**.")
                return
            menuMsg = await sendChannel.send("‎")
            helpTT = timedTask.TimedTask(expiryDelta=timedelta(**cfg.timeouts.helpMenu),
                                        expiryFunction=expiryFunctions.expireHelpMenu, expiryFunctionArgs=menuMsg.id)
            botState.taskScheduler.scheduleTask(helpTT)
            indexEmbed = lib.discordUtil.makeEmbed(titleTxt=cfg.userAccessLevels[userAccessLevel].title() + " Commands",
                                                    desc="Select " + cfg.defaultEmojis.next.sendable + " to go to page one.",
                                                    thumb=botState.client.user.avatar_url_as(size=64),
                                                    footerTxt="This menu will expire in " + helpMenuTimeoutStr + ".")
            sectionsStr = ""
            pages = {indexEmbed: {}}
            for sectionNum in range(len(botCommands.helpSectionEmbeds[userAccessLevel])):
                sectionsStr += "\n" + str(sectionNum + 1) + ") " \
                                + list(botCommands.helpSectionEmbeds[userAccessLevel].keys())[sectionNum].title()
                # sectionsStr += "\n" + cfg.defaultEmojis.menuOptions[sectionNum + 1].sendable + " : " +
                #                 list(botCommands.helpSectionEmbeds[userAccessLevel].keys())[sectionNum].title()
                # pages[indexEmbed][cfg.defaultEmojis.menuOptions[sectionNum + 1]] =
                #                 ReactionMenu.NonSaveableReactionMenuOption(list(
                #                     botCommands.helpSectionEmbeds[userAccessLevel].keys())[sectionNum].title(),
                #                     cfg.defaultEmojis.menuOptions[sectionNum + 1], addFunc=pagedReactionMenu.menuJumpToPage,
                #                     addArgs={"menuID": menuMsg.id, "pageNum": sectionNum})
            indexEmbed.add_field(name="Contents", value=sectionsStr)
            pageNum = 0
            for helpSectionEmbedList in botCommands.helpSectionEmbeds[userAccessLevel].values():
                for helpEmbed in helpSectionEmbedList:
                    pageNum += 1
                    newEmbed = helpEmbed.copy()
                    newEmbed.set_footer(text="Page " + str(pageNum) + " of " + str(botCommands.totalEmbeds[userAccessLevel]) \
                                            + " | This menu will expire in " + helpMenuTimeoutStr + ".")
                    pages[newEmbed] = {}
            newMenu = pagedReactionMenu.PagedReactionMenu(
                menuMsg, pages, timeout=helpTT, targetMember=message.author, owningBasedUser=owningUser)
            await newMenu.updateMessage()
            botState.reactionMenusDB[menuMsg.id] = newMenu
            owningUser.addOwnedMenu("help", newMenu)

        elif args in botCommands.helpSectionEmbeds[userAccessLevel]:
            if len(botCommands.helpSectionEmbeds[userAccessLevel][args]) == 1:
                await sendChannel.send(embed=botCommands.helpSectionEmbeds[userAccessLevel][args][0])
            else:
                owningUser = botState.usersDB.getOrAddID(message.author.id)
                if owningUser.hasMenuOfTypeID("help"):
                    await message.reply(mention_author=False,
                                        content=":x: Please close your existing help menu before making a new one!\n" \
                                                + "In case you can't find it, help menus auto exire after **" \
                                                + helpMenuTimeoutStr + "**.")
                    return
                menuMsg = await sendChannel.send("‎")
                helpTT = timedTask.TimedTask(expiryDelta=timedelta(**cfg.timeouts.helpMenu),
                                            expiryFunction=expiryFunctions.expireHelpMenu, expiryFunctionArgs=menuMsg.id)
                botState.taskScheduler.scheduleTask(helpTT)
                pages = {}
                for helpEmbed in botCommands.helpSectionEmbeds[userAccessLevel][args]:
                    newEmbed = helpEmbed.copy()
                    newEmbed.set_footer(text=helpEmbed.footer.text + " | This menu will expire in " \
                                        + helpMenuTimeoutStr + ".")
                    pages[newEmbed] = {}
                newMenu = pagedReactionMenu.PagedReactionMenu(
                    menuMsg, pages, timeout=helpTT, targetMember=message.author, owningBasedUser=owningUser)
                await newMenu.updateMessage()
                botState.reactionMenusDB[menuMsg.id] = newMenu
                owningUser.addOwnedMenu("help", newMenu)

        elif args in botCommands.commands[userAccessLevel] and botCommands.commands[userAccessLevel][args].allowHelp:
            cmdObj = botCommands.commands[userAccessLevel][args]
            helpEmbed = lib.discordUtil.makeEmbed(titleTxt=cfg.userAccessLevels[userAccessLevel].title() + " Commands",
                                                    desc=cfg.helpIntro + "\n__" \
                                                        + cmdObj.helpSection.title() \
                                                        + "__", col=discord.Colour.blue(),
                                                    thumb=botState.client.user.avatar_url_as(size=64))
            helpEmbed.add_field(name=cmdObj.signatureStr,
                                value=cmdObj.longHelp, inline=False)
            helpEmbed.add_field(name="DMable", value="Yes" if cmdObj.allowDM else "No")
            if cmdObj.aliases:
                aliasesStr = ""
                for alias in cmdObj.aliases[:-1]:
                    aliasesStr += alias + ", "
                aliasesStr += cmdObj.aliases[-1]
                helpEmbed.add_field(name="Alaises", value=aliasesStr)
            helpEmbed.set_footer(text=f"Section: {cmdObj.helpSection.title()} | [optional args] <required args>")
            await message.reply(mention_author=False, embed=helpEmbed)

        else:
            await message.reply(mention_author=False, content=":x: Unknown command/section! See `help help` for a list of help sections.")

    except discord.Forbidden:
        await message.reply(mention_author=False, content=":x: I can't DM you, " + message.author.display_name \
                                    + "! Please enable DMs from users who are not friends.")
        if owningUser is not None and owningUser.hasMenuOfTypeID("help") and newMenu is not None:
            owningUser.removeOwnedMenu("help", newMenu)
        return
    else:
        if sendDM:
            await message.add_reaction(cfg.defaultEmojis.dmSent.sendable)
