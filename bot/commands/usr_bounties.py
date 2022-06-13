from typing import Dict, List, Optional
import discord
from datetime import datetime, timedelta
from io import BytesIO
from PIL import Image

from . import commandsDB as botCommands
from .. import botState, lib
from ..lib.stringTyping import commaSplitNum
from ..lib.discordUtil import truncateWithEllipse
from ..cfg import cfg, bbData
from ..gameObjects.battles import duelRequest
from ..gameObjects.bounties.bounty import Bounty, CheckResult, RewardsMeta
from ..scheduling import timedTask
from ..reactionMenus import reactionDuelChallengeMenu, expiryFunctions, confirmationReactionMenu
from ..users import basedUser, basedGuild
from ..gameObjects.items import shipItem
from ..gameObjects.items.weapons import primaryWeapon
from ..gameObjects.items.tools import crateTool
from ..databases.bountyDivision import BountyDivision
from ..databases.bountyDB import nameForDivision
from ..lib import gameMaths


botCommands.addHelpSection(0, "bounty hunting")


async def cmd_toggle_classic_mode(message: discord.Message, args: str, isDM: bool):
    """Toggle 'classic mode' for the calling user.

    :param discord.Message message: the discord message calling the command
    :param str args: ignored
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    callingUser: Optional[basedUser.BasedUser] = None
    if botState.client.usersDB.idExists(message.author.id):
        callingUser = botState.client.usersDB.getUser(message.author.id)
        currentStatus = callingUser.classicModeEnabled
    else:
        currentStatus = False

    if currentStatus:
        confirmMsgText = "You currently have classic mode enabled. Disable it to play with exciting new features:\n" \
                        + "• Beat bounties in a duel to win their rewards\n" \
                        + "• Progress through bounty hunter levels and get new customization items\n" \
                        + "• Gain huge rewards for beating tougher bounties\n" \
                        + "\nBy disabling classic mode will keep everything, including items, credits and stats, and you " \
                        + "will begin at bounty hunter level 1. Classic mode can be enabled again at any time."
    else:
        confirmMsgText = "Missing the BountyBot beta? You might prefer classic mode:\n" \
                        + "• No dueling, win bounties by finding the correct system\n" \
                        + "• No XP or levelling\n" \
                        + "• Get a fixed 1000 credits per system check\n" \
                        + f"• Restricted to {cfg.bountyDivisionNames[0]} division bounties, but any shops\n" \
                        + "\nBy enabling classic mode, you will lose all of your XP, but you will keep your " \
                        + "credits and items. Classic mode can be disabled again at any time."

    actionText = "Disable" if currentStatus else "Enable"
    confirmMsg: discord.Message = await message.reply(confirmMsgText, mention_author=False)
    confirmMenu = confirmationReactionMenu.InlineConfirmationMenu(confirmMsg, message.author,
                                    timedelta(**cfg.timeouts.toggleClassicMode).total_seconds(),
                                    desc=f"{actionText} classic mode now?\nThis command can be used again at any time.",
                                    col=discord.Colour.random())
    
    confirmResults = await confirmMenu.doMenu()
    if not confirmResults:
        await confirmMsg.edit(content=":x: Out of time, please try this command again.")
    elif confirmResults[0] == cfg.defaultEmojis.reject:
        await confirmMsg.edit(content="🛑 Classic mode toggle cancelled.", embed=None)

    elif confirmResults[0] == cfg.defaultEmojis.accept:
        if callingUser is None:
            callingUser = botState.client.usersDB.addID(message.author.id)
        if callingUser.classicModeEnabled:
            callingUser.disableClassicMode()
        else:
            callingUser.enableClassicMode()

        await message.reply(f"{cfg.defaultEmojis.submit} You have now {actionText.lower()}d classic mode.")
    
    else:
        raise RuntimeError(f"Unsupported result: {confirmResults}")

botCommands.register("classic", cmd_toggle_classic_mode, 0, aliases=["retro", "classic-mode", "retro-mode"],
                    shortHelp="Toggle \"classic mode\", which emulates the BountyBot beta. " \
                            + "See `help classic` for more info.",
                    longHelp="Toggle BountyBot's \"classic mode\", which emulates the BountyBot beta.\n" \
                            + "In this mode, you win bounties immediately by finding the correct system - you do not need " \
                                + "to duel bounties to win.\n"
                            + f"You will receive a fixed {cfg.classic_creditsPerCheck} credits per system check.\n" \
                            + "XP and levelling are disabled, meaning you will not get level-up, division-up " \
                                + "or prestige bonuses.\n"
                            + "You are restricted to bounties in the lowest division " \
                                + f"({cfg.bountyDivisionNames[0]})\n" \
                            + "Use this command to enable or disable classic mode, at any time.")



async def cmd_check(message : discord.Message, args : str, isDM : bool):
    """Check a system for bounties and handle rewards

    :param discord.Message message: the discord message calling the command
    :param str args: string containing one system to check
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    # Verify that this guild has bounties enabled
    callingGuild: basedGuild.BasedGuild = botState.client.guildsDB.getGuild(message.guild.id)
    if callingGuild.bountiesDisabled:
        await message.reply(mention_author=False, content=":x: This server does not have bounties enabled.")
        return

    # verify this is the calling user's home guild. If no home guild is set, transfer here.
    requestedBBUser: basedUser.BasedUser = botState.client.usersDB.getOrAddID(message.author.id)
    if not requestedBBUser.hasHomeGuild():
        await requestedBBUser.transferGuild(message.guild)
        await message.reply(mention_author=False, content=":airplane_arriving: Your home server has been set.")
    elif requestedBBUser.homeGuildID != message.guild.id:
        await message.reply(mention_author=False, content=":x: This command can only be used from your home server!")
        return

    # verify a system was given
    if args == "":
        await message.reply(mention_author=False, content=":x: Please provide a system to check! E.g: `" \
                                    + callingGuild.commandPrefix + "check Pescal Inartu`")
        return

    requestedSystem = args.title()
    systObj = None

    # attempt to find the requested system in the database
    for syst in bbData.builtInSystemObjs.keys():
        if bbData.builtInSystemObjs[syst].isCalled(requestedSystem):
            systObj = bbData.builtInSystemObjs[syst]

    # reject if the requested system is not in the database
    if systObj is None:
        if len(requestedSystem) < 20:
            await message.reply(mention_author=False,
                                content=f":x: The **{truncateWithEllipse(requestedSystem, 20, 15)}** system is not " \
                                        + "on my star map! :map:")
        return

    requestedSystem = systObj.name

    if not requestedBBUser.activeShip.hasWeaponsEquipped() and not requestedBBUser.activeShip.hasTurretsEquipped():
        await message.reply(mention_author=False, content=":x: Your ship has no weapons equipped!")
        return

    # ensure the calling user is not on checking cooldown
    if datetime.utcfromtimestamp(requestedBBUser.bountyCooldownEnd) < datetime.utcnow():
        bountyWon = False
        bountyLost = False
        systemInBountyRoute = False

        if requestedBBUser.classicModeEnabled:
            btyDivision = callingGuild.bountiesDB.divisionForName(cfg.classic_divisionName)
        else:
            userLevel = gameMaths.calculateUserBountyHuntingLevel(requestedBBUser.bountyHuntingXP)
            btyDivision = callingGuild.bountiesDB.divisionForLevel(userLevel)

        # list of completed bounties to remove from the bounties database
        toPop = []
        toEscape = []
        sightedCriminalsStr = ""
        # The total amount to increase the division's activity temperature by
        divTempDelta = 0
        bounty: Bounty

        for tlBounties in btyDivision.bounties.values():
            for bounty in tlBounties.values():
                # Check the passed system in current bounty
                checkResult = bounty.check(requestedSystem, message.author.id)
                statsEmbed: Optional[discord.Embed] = None
                duelResultsImg: Optional[Image.Image] = None

                # If current bounty resides in the requested system
                if checkResult == CheckResult.CORRECT:
                    if requestedBBUser.classicModeEnabled:
                        duelWon = True
                    else:
                        duelWon = False
                        duelResults = duelRequest.fightShips(requestedBBUser.activeShip, bounty.activeShip,
                                                                cfg.duelVariancePercent)
                        try:
                            duelResultsImg = await duelRequest.buildDuelResultsImage(requestedBBUser,
                                                                                        requestedBBUser.activeShip,
                                                                                        bounty.criminal, bounty.activeShip,
                                                                                        duelResults)
                        except RuntimeError:
                            statsEmbed = lib.discordUtil.makeEmbed(authorName="**Duel Stats**")
                            statsEmbed.add_field(name=f"DPS ({cfg.duelVariancePercent * 100}% RNG)",
                                                    value=message.author.mention + ": " \
                                                        + str(round(duelResults["ship1"]["DPS"]["varied"], 2)) + "\n" \
                                                        + bounty.criminal.name + ": " \
                                                        + str(round(duelResults["ship2"]["DPS"]["varied"], 2)))
                            statsEmbed.add_field(name=f"Health ({cfg.duelVariancePercent * 100}% RNG)",
                                                    value=message.author.mention + ": " \
                                                        + str(round(duelResults["ship1"]["health"]["varied"])) + "\n" \
                                                        + bounty.criminal.name + ": " \
                                                        + str(round(duelResults["ship2"]["health"]["varied"], 2)))
                            statsEmbed.add_field(name="Time To Kill",
                                                    value=message.author.mention + ": " \
                                                        + (str(round(duelResults["ship1"]["TTK"], 2)) \
                                                            if duelResults["ship1"]["TTK"] != -1 else "inf.") + "s\n" \
                                                        + bounty.criminal.name + ": " \
                                                        + (str(round(duelResults["ship2"]["TTK"], 2)) \
                                                            if duelResults["ship2"]["TTK"] != -1 else "inf.") + "s")

                            statsEmbed.set_footer(text="An unexpected error occurred when building your duel results image." \
                                                    + " The error has been logged.")
                            duelResultsImg = None
                        else:
                            statsEmbed = lib.discordUtil.makeEmbed("Duel Results")
                            statsEmbed.set_image(url="attachment://duelResults.png")
                            duelResultsBytes = BytesIO()
                            duelResultsImg.save(duelResultsBytes, "PNG")
                            duelResultsBytes.seek(0)
                            duelResultsFile = discord.File(duelResultsBytes, filename="duelResults.png")
                        

                        if duelResults["winningShip"] is not requestedBBUser.activeShip:
                            toEscape.append(bounty)
                            # bounty.escape()
                            bountyLost = True
                            await message.channel.send(bounty.criminal.name + " got away! ", embed=statsEmbed,
                                                        file=None if duelResultsImg is None else duelResultsFile)
                        else:
                            duelWon = True

                    if duelWon:
                        bountyWon = True

                        basedUsers: Dict[int, basedUser.BasedUser] = \
                            {i: botState.client.usersDB.getOrAddID(i) for i in set(bounty.checked.values())}
                        classicModeUserIDs = set(u.id for u in basedUsers.values() if u.classicModeEnabled)
                        nonClassicModeUserIDs = set(u.id for u in basedUsers.values() if u.id not in classicModeUserIDs)

                        # reward all contributing users
                        rewards = bounty.calcRewards(classicModeUserIDs)
                        rewardsMeta = {i: RewardsMeta.NONE for i in rewards}

                        # userID : reward
                        distributeRewards: Dict[int, int] = {}
                        guildMaxDiv = callingGuild.bountiesDB.divisionForLevel(cfg.maxTechLevel)

                        for userID in nonClassicModeUserIDs:
                            if userID == -1:
                                continue

                            currentBBUser = basedUsers[userID]
                            currentLevel = gameMaths.calculateUserBountyHuntingLevel(currentBBUser.bountyHuntingXP)
                            currentDiv = callingGuild.bountiesDB.divisionForLevel(currentLevel)
                            
                            # If the bounty is in the highest division, but the user has since moved to a new division
                            # (i.e they have prestiged), Share their rewards to the other contributors
                            # https://github.com/GOF2BountyBot/GOF2BountyBot/issues/462
                            if bounty.division == guildMaxDiv and currentDiv != guildMaxDiv:
                                rewardsMeta[userID] = RewardsMeta.USER_PRESTIGED | rewardsMeta[userID]
                                distributeRewards[userID] = rewards[userID]["reward"]
                            
                            # Make sure that xp does not go over the maximum
                            if currentLevel == cfg.maxTechLevel - 1:
                                maxLevelXp = gameMaths.bountyHuntingXPForLevel(cfg.maxTechLevel)
                                if rewards[userID]["xp"] + currentBBUser.bountyHuntingXP > maxLevelXp:
                                    rewards[userID]["xp"] = maxLevelXp - currentBBUser.bountyHuntingXP

                        # share rewards lost due to prestiging
                        if distributeRewards:
                            totalToShare = sum(distributeRewards.values())
                            receiverIDs = [i for i in rewards if i not in distributeRewards and i in nonClassicModeUserIDs]
                            each = int(totalToShare / len(receiverIDs))
                            for receiverID in receiverIDs:
                                rewards[receiverID]["reward"] += each

                        divUpUnlocked: List[int] = []
                        prestigeUnlocked: List[int] = []

                        levelUpMsg = ""
                        for userID in rewards:
                            # If the bounty is in the highest division, but the user has since moved to a new division
                            # (i.e they have prestiged), Share their rewards to the other contributors
                            # https://github.com/GOF2BountyBot/GOF2BountyBot/issues/462
                            if RewardsMeta.USER_PRESTIGED & rewardsMeta[userID]:
                                continue

                            currentBBUser = basedUsers[userID]
                            currentBBUser.credits += rewards[userID]["reward"]
                            currentBBUser.lifetimeBountyCreditsWon += rewards[userID]["reward"]

                            if currentBBUser.classicModeEnabled:
                                continue

                            oldLevel = gameMaths.calculateUserBountyHuntingLevel(currentBBUser.bountyHuntingXP)
                            if oldLevel == cfg.maxTechLevel:
                                continue
                            
                            oldDiv = callingGuild.bountiesDB.divisionForLevel(oldLevel)
                            
                            if oldLevel == oldDiv.maxLevel:
                                if not currentBBUser.canDivUp():
                                    divUpXp = oldDiv.xpToDivUp()
                                    newUserXp = currentBBUser.bountyHuntingXP + rewards[userID]["xp"]
                                    if divUpXp < newUserXp:
                                        currentBBUser.bountyHuntingXP = divUpXp - 1
                                        currentBBUser.bountyHuntingXpSurplus = newUserXp - currentBBUser.bountyHuntingXP
                                        if oldLevel == cfg.maxTechLevel - 1:
                                            prestigeUnlocked.append(userID)
                                        else:
                                            divUpUnlocked.append(userID)
                                    else:
                                        currentBBUser.bountyHuntingXP += rewards[userID]["xp"]
                            else:
                                currentBBUser.bountyHuntingXP += rewards[userID]["xp"]
                                
                            currentDCUser = message.guild.get_member(currentBBUser.id)

                            newLevel = gameMaths.calculateUserBountyHuntingLevel(currentBBUser.bountyHuntingXP)
                            if newLevel > oldLevel:
                                levelUpCrate = bbData.builtInCrateObjs["levelUp"][newLevel]
                                currentBBUser.inactiveTools.addItem(levelUpCrate)
                                
                                levelUpMsg += "\n:arrow_up: **Level Up!**\n" \
                                            + currentDCUser.mention \
                                            + f" reached **Bounty Hunter Level {newLevel}!** :partying_face:\n" \
                                            + f"You got a **{levelUpCrate.name}**."
                                
                                if newLevel == cfg.maxTechLevel:
                                    levelUpMsg += f"\nYou have now unlocked prestiging! " \
                                                + f"Use `{callingGuild.commandPrefix}prestige` to gain special rewards and " \
                                                + "start a new run!"

                        if levelUpMsg != "":
                            await message.channel.send(levelUpMsg)

                        # Announce the bounty has been completed
                        await callingGuild.announceBountyWon(bounty, rewards, message.author, rewardsMeta, divUpUnlocked, prestigeUnlocked)
                        if statsEmbed is not None or duelResultsImg is not None:
                            await message.channel.send(embed=statsEmbed,
                                                        file=None if duelResultsImg is None else duelResultsFile)

                        # Raise guild's activity temperature for this bounty's tl
                        numContributingUsers = len(basedUsers)
                        divTempDelta += numContributingUsers * cfg.activityTempPerPlayer

                        # add this bounty to the list of bounties to be removed
                        toPop.append(bounty)

                # Update routes in this division containing the checked system
                if checkResult in [CheckResult.INCORRECT, CheckResult.CORRECT]:
                    systemInBountyRoute = True
                    await callingGuild.updateBountyBoardChannel(bounty, bountyComplete=checkResult == CheckResult.CORRECT)
                    # Check if any bounties are close to the requested system in their route,
                    # defined by cfg.closeBountyThreshold
                    distanceToAnswer = bounty.route.index(bounty.answer) - bounty.route.index(requestedSystem)
                    if checkResult == CheckResult.INCORRECT and 0 < distanceToAnswer < cfg.closeBountyThreshold:
                        # Print any close bounty names
                        sightedCriminalsStr += "\n**       **• Local security forces spotted **" \
                                                + lib.discordUtil.criminalNameOrDiscrim(bounty.criminal) \
                                                + "** here recently."

        # remove all completed bounties
        for bounty in toPop:
            try:
                btyDivision.removeBountyObj(bounty)
            except OverflowError as e:
                botState.client.logger.log("usr_bounties", "cmd_check", str(e), exception=e)
        # remove all escaped bounties
        for bounty in toEscape:
            bounty.escape()
            if bounty.division.bountyBoardChannel is not None:
                await bounty.division.bountyBoardChannel.updateEscapedBountiesMessage()

        if divTempDelta:
            # Apply the gathered temperature raises to this division
            # This must be done after the bounty ojects are removed from the division, as this is the point at which
            # The division's maxBounties is compared, to see if the new bounty TT needs to be restarted
            btyDivision.raiseTemp(divTempDelta)

        # If a bounty was won, print a congratulatory message
        if bountyWon:
            requestedBBUser.bountyWins += 1
            await message.reply(mention_author=False, content=sightedCriminalsStr + "\n" + ":moneybag: **" + message.author.display_name \
                                        + "**, you now have **" + commaSplitNum(requestedBBUser.credits) + " Credits!**")

        # If no bounty was won, print an error message
        else:
            if not bountyLost:
                await message.reply(mention_author=False, content=":telescope: **" + message.author.display_name \
                                            + "**, you did not find any criminals in **" + requestedSystem.title() \
                                            + "**!\n" + sightedCriminalsStr)
            elif sightedCriminalsStr:
                await message.reply(mention_author=False, content=sightedCriminalsStr)

        # Only put the calling user on checking cooldown and increment systemsChecked stat if the system checked
        # is on an active bounty's route.
        if systemInBountyRoute:
            requestedBBUser.systemsChecked += 1
            # Put the calling user on checking cooldown
            requestedBBUser.bountyCooldownEnd = (datetime.utcnow() \
                                                    + timedelta(minutes=cfg.timeouts.checkCooldown["minutes"])
                                                    + botState.utcOffset).timestamp()

    # If the calling user is on checking cooldown
    else:
        # Print an error message with the remaining time on the calling user's cooldown
        diff = datetime.utcfromtimestamp(botState.client.usersDB.getUser(message.author.id).bountyCooldownEnd) - datetime.utcnow()
        await message.reply(mention_author=False,
                            content=f":stopwatch: **{message.author.display_name}**, your *Khador Drive* is still charging!" \
                                    + f" please wait **{lib.timeUtil.td_format_noYM(diff)}.**")

botCommands.register("check", cmd_check, 0, aliases=["search"], allowDM=False, helpSection="bounty hunting",
                        signatureStr="**check <system>**",
                        shortHelp="Check if any criminals are in the given system, arrest them, and get paid! 💰" \
                        + "\n🌎 This command must be used in your **home server**.")


async def cmd_bounties(message: discord.Message, args: str, isDM: bool):
    """List a summary of all currently active bounties in one division.
    If no division is specified, the calling user's division is used.
    Division can be specified either as a number (a tech level), or a division name as given in cfg.bountyDivisionNames

    :param discord.Message message: the discord message calling the command
    :param str args: string, can be empty or contain a division name or tech level
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    # Verify that this guild has bounties enabled
    callingGuild: basedGuild.BasedGuild = botState.client.guildsDB.getGuild(message.guild.id)
    if callingGuild.bountiesDisabled:
        await message.reply(mention_author=False, content=":x: This server does not have bounties enabled.")
        return

    division: BountyDivision = None

    if not args:
        try:
            callingUser: basedUser.BasedUser = botState.client.usersDB.getUser(message.author.id)
        except KeyError:
            division = callingGuild.bountiesDB.divisionForLevel(0)
        else:
            if callingUser.classicModeEnabled:
                division = callingGuild.bountiesDB.divisionForName(cfg.classic_divisionName)
            else:
                userLevel = gameMaths.calculateUserBountyHuntingLevel(callingUser.bountyHuntingXP)
                division = callingGuild.bountiesDB.divisionForLevel(userLevel)
    else:
        divKeyError = ":x: Unknown division. Give no arguments to see bounties in your division, or to see another division" \
                    + ", give either a difficulty level (1-10), or a division name: " \
                    + ", ".join(i.title() for i in cfg.bountyDivisionNames)[:-1] + " or " + cfg.bountyDivisionNames[-1]

        if lib.stringTyping.isInt(args):
            try:
                division = callingGuild.bountiesDB.divisionForLevel(int(args))
            except KeyError:
                await message.reply(divKeyError)
                return
        else:
            try:
                division = callingGuild.bountiesDB.divisionForName(args)
            except KeyError:
                await message.reply(divKeyError)
                return

    divName = nameForDivision(division).title()

    if division.isEmpty():
        await message.reply(mention_author=False, content=":stopwatch: There are no " + divName \
                                        + " division bounties active currently!")
        return
    
    msgEmbed = discord.Embed(title=f"Active Bounties: {divName} Division",
                                description=f"Difficulty levels {division.minLevel} - {division.maxLevel} ~ " \
                                            + "Times given in UTC",
                                colour=discord.Colour.random())
    msgEmbed.set_footer(icon_url=bbData.rocketIcon,
                        text=f"Track down criminals and win credits using `{callingGuild.commandPrefix}route` " \
                                + f"and {callingGuild.commandPrefix}check`!")

    # Collect and print summaries of all active bounties
    for tl in division.bounties:
        if division.bounties[tl]:
            msgEmbed.add_field(name="​", value=f"__Level {tl}__", inline=False)
            for crim, bounty in division.bounties[tl].items():
                timeLeft = datetime.utcfromtimestamp(bounty.endTime) - datetime.utcnow()
                if bounty.faction in bbData.bountyFactionEmojis:
                    factionEmoji = lib.emojis.BasedEmoji(id=bbData.bountyFactionEmojis[bounty.faction]).sendable + " "
                else:
                    factionEmoji = ""
                msgEmbed.add_field(name=factionEmoji + lib.discordUtil.criminalNameOrDiscrim(crim),
                                    value=f"• {int(bounty.reward)} Credits\n"
                                            + f"• {len(bounty.route)} possible systems\n" \
                                            + f"• Ending in {lib.timeUtil.td_format_noYM(timeLeft)}")
    
    await message.reply(mention_author=False, embed=msgEmbed)


botCommands.register("bounties", cmd_bounties, 0, allowDM=False, helpSection="bounty hunting",
                        signatureStr="**bounties** *[level or division]*",
                        shortHelp="List all active bounties in your division, or the one specified",
                        longHelp="If no division is given, name all currently active bounties. In your division.\n" \
                                    + "If a division is given, show all bountis in that division.\n"
                                    + "Division can be given either as a name, or as a difficulty level in that division.")


async def cmd_route(message : discord.Message, args : str, isDM : bool):
    """Display the current route of the requested criminal

    :param discord.Message message: the discord message calling the command
    :param str args: string containing a criminal name or alias
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    # Verify that this guild has bounties enabled
    callingGuild = botState.client.guildsDB.getGuild(message.guild.id)
    if callingGuild.bountiesDisabled:
        await message.reply(mention_author=False, content=":x: This server does not have bounties enabled.")
        return

    # verify a criminal was specified
    if args == "":
        await message.reply(mention_author=False, content=":x: Please provide the criminal name! " \
                                    + f"E.g: `{callingGuild.commandPrefix}route Kehnor`")
        return

    requestedBountyName = args
    # if the named criminal is wanted
    if callingGuild.bountiesDB.bountyNameExists(requestedBountyName.lower()):
        # display their route
        bounty = callingGuild.bountiesDB.getBounty(requestedBountyName.lower())
        outmessage = "**" + lib.discordUtil.criminalNameOrDiscrim(bounty.criminal) + "**'s current route:\n> "
        for system in bounty.route:
            outmessage += " " + ("~~" if bounty.checked[system] != -1 else "") \
                            + system + ("~~" if bounty.checked[system] != -1 else "") + ","
        outmessage = outmessage[:-1] + ". :rocket:"
        await message.reply(mention_author=False, content=outmessage)
    # if the named criminal is not wanted
    else:
        # display an error
        outmsg = ":x: That pilot isn't on any bounty boards! :clipboard:"
        # accept user name + discrim instead of tags to avoid mention spam
        if lib.stringTyping.isMention(requestedBountyName):
            outmsg += "\n:warning: **Don't tag users**, use their name and ID number like so: `" \
                        + callingGuild.commandPrefix + "route Trimatix#2244`"
        await message.reply(mention_author=False, content=outmsg)

botCommands.register("route", cmd_route, 0, allowDM=False, helpSection="bounty hunting",
                        signatureStr="**route <criminal name>**",
                        shortHelp="Get the named criminal's current route.",
                        longHelp="Get the named criminal's current route.\n" \
                                    + "For a list of aliases for a given criminal, see `info criminal`.")


async def cmd_duel(message : discord.Message, args : str, isDM : bool):
    """⚠ WARNING: MARKED FOR CHANGE ⚠
    The following function is provisional and marked as planned for overhaul.
    Details: Overhaul is part-way complete, with a few fighting algorithm provided in gameObjects.items.battles.
    However, printing the fight details is yet to be implemented.
    This is planned to be done using simple message editing-based animation of player ships and progress bars for health etc.
    This command is functional for now, but the output is subject to change.

    Challenge another player to a duel, with an amount of credits as the stakes.
    The winning user is given stakes credits, the loser has stakes credits taken away.
    give 'challenge' to create a new duel request.
    give 'cancel' to cancel an existing duel request.
    give 'accept' to accept another user's duel request targetted at you.

    :param discord.Message message: the discord message calling the command
    :param str args: string containing the action (challenge/cancel/accept), a target user (mention or ID), and the stakes
                        (int amount of credits). stakes are only required when "challenge" is specified.
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    argsSplit = args.split(" ")
    if len(argsSplit) == 0:
        await message.reply(":x: Please provide an action (`challenge`/`cancel`/`accept`/`reject or decline`), " \
                                    + "a user, and the stakes (an amount of credits)!", mention_author=False)
        return
    action = argsSplit[0]
    if action not in ["challenge", "cancel", "accept", "reject", "decline"]:
        await message.reply(":x: Invalid action! please choose from `challenge`, `cancel`, " \
                                    + "`reject/decline` or `accept`.", mention_author=False)
        return

    if action == "challenge":
        if len(argsSplit) < 3:
            await message.reply(":x: Please provide a user and the stakes (an amount of credits)!", mention_author=False)
            return
        if not lib.stringTyping.isInt(argsSplit[-1]) or int(argsSplit[-1]) < 0:
            await message.reply(":x: Invalid stakes! The duel stakes must be a number at least 0.")
            return
        stakes = int(argsSplit[-1])
        requestedUser = lib.discordUtil.getMemberByRefOverDB(" ".join(argsSplit[1:-1]), dcGuild=message.guild)

    else:
        if len(argsSplit) < 2:
            await message.reply(mention_author=False, content=":x: Please provide a user!")
            return
        requestedUser = lib.discordUtil.getMemberByRefOverDB(" ".join(argsSplit[1:]), dcGuild=message.guild)

    if requestedUser is None:
        await message.reply(mention_author=False, content=":x: User not found!")
        return
    if requestedUser.id == message.author.id:
        await message.reply(mention_author=False, content=":x: You can't challenge yourself!")
        return
    if action == "challenge" and (not lib.stringTyping.isInt(argsSplit[2]) or int(argsSplit[2]) < 0):
        await message.reply(mention_author=False, content=":x: Invalid stakes (amount of credits)!")
        return

    sourceBBUser: basedUser.BasedUser = botState.client.usersDB.getOrAddID(message.author.id)
    targetBBUser: basedUser.BasedUser = botState.client.usersDB.getOrAddID(requestedUser.id)

    # await duelRequest.buildDuelResultsImage(sourceBBUser, sourceBBUser.activeShip, targetBBUser, targetBBUser.activeShip, {"winningShip": sourceBBUser.activeShip if int((sourceBBUser.activeShip.getArmour() + sourceBBUser.activeShip.getShield()) / targetBBUser.activeShip.getDPS()) > int((targetBBUser.activeShip.getArmour() + targetBBUser.activeShip.getShield()) / sourceBBUser.activeShip.getDPS()) else targetBBUser.activeShip,
    #         "ship1": {"health": {"stock": int(sourceBBUser.activeShip.getArmour() + sourceBBUser.activeShip.getShield()), "varied": int(sourceBBUser.activeShip.getArmour() + sourceBBUser.activeShip.getShield())},
    #                 "DPS": {"stock": sourceBBUser.activeShip.getDPS(), "varied": sourceBBUser.activeShip.getDPS()},
    #                 "TTK": int((sourceBBUser.activeShip.getArmour() + sourceBBUser.activeShip.getShield()) / targetBBUser.activeShip.getDPS())},
    #         "ship2": {"health": {"stock": int(targetBBUser.activeShip.getArmour() + targetBBUser.activeShip.getShield()), "varied": int(targetBBUser.activeShip.getArmour() + targetBBUser.activeShip.getShield())},
    #                 "DPS": {"stock": targetBBUser.activeShip.getDPS(), "varied": targetBBUser.activeShip.getDPS()},
    #                 "TTK": int((targetBBUser.activeShip.getArmour() + targetBBUser.activeShip.getShield()) / sourceBBUser.activeShip.getDPS())}})
    # return

    callingGuild = botState.client.guildsDB.getGuild(message.guild.id)

    if action == "challenge":
        if sourceBBUser.hasDuelChallengeFor(targetBBUser):
            await message.reply(mention_author=False, content=":x: You already have a duel challenge pending for " \
                                        + lib.discordUtil.userOrMemberName(requestedUser, message.guild) \
                                        + "! To make a new one, cancel it first. (see `" + callingGuild.commandPrefix \
                                        + "help duel`)")
            return

        try:
            newDuelReq = duelRequest.DuelRequest(
                sourceBBUser, targetBBUser, stakes, None, botState.client.guildsDB.getGuild(message.guild.id))
            duelTT = timedTask.TimedTask(expiryDelta=timedelta(**cfg.timeouts.duelRequest),
                                            expiryFunction=duelRequest.expireAndAnnounceDuelReq,
                                            expiryFunctionArgs={"duelReq": newDuelReq})
            newDuelReq.duelTimeoutTask = duelTT
            botState.client.taskScheduler.scheduleTask(duelTT)
            sourceBBUser.addDuelChallenge(newDuelReq)
        except KeyError:
            await message.reply(mention_author=False, content=":x: User not found! Did they leave the server?")
            return
        except Exception:
            await message.reply(mention_author=False, content=":woozy_face: An unexpected error occurred! Tri, what did you do...")
            return

        expiryTimesSplit = duelTT.expiryTime.strftime("%d %B %H %M").split(" ")
        duelExpiryTimeString = "This duel request will expire on the **" + expiryTimesSplit[0].lstrip('0') \
                                + lib.stringTyping.getNumExtension(int(expiryTimesSplit[0])) + "** of **" \
                                + expiryTimesSplit[1] + "**, at **" + expiryTimesSplit[2] + ":" + expiryTimesSplit[3] \
                                + "** UTC."

        sentMsgs = []

        async def queueChallengeMsg(channel, challengerStr, targetStr):
            sentMsgs.append(await channel.send(":crossed_swords: **" + challengerStr + "** challenged " + targetStr \
                                                + " to duel for **" + str(stakes) + " Credits!**\nType `" \
                                                + callingGuild.commandPrefix + "duel accept " + str(message.author.id) \
                                                + "` (or `" + callingGuild.commandPrefix + "duel accept @" \
                                                + message.author.name + "` if you're in the same server) " \
                                                + "To accept the challenge!\n" + duelExpiryTimeString))

        if message.guild.get_member(requestedUser.id) is None:
            targetUserDCGuild = lib.discordUtil.findBBUserDCGuild(targetBBUser)
            if targetUserDCGuild is None:
                await message.reply(mention_author=False, content=":x: User not found! Did they leave the server?")
                return
            else:
                targetUserBBGuild = botState.client.guildsDB.getGuild(targetUserDCGuild.id)
                if targetUserBBGuild.hasPlayChannel():
                    targetUserNameOrTag = lib.discordUtil.IDAlertedUserMentionOrName("duels_challenge_incoming_new",
                                                                                        dcGuild=targetUserDCGuild,
                                                                                        basedGuild=targetUserBBGuild,
                                                                                        dcUser=requestedUser,
                                                                                        basedUser=targetBBUser)
                    await queueChallengeMsg(targetUserBBGuild.getPlayChannel(), str(message.author), targetUserNameOrTag)
            await queueChallengeMsg(message.channel, message.author.mention, str(requestedUser))
        else:
            targetUserNameOrTag = lib.discordUtil.IDAlertedUserMentionOrName("duels_challenge_incoming_new",
                                                                                dcGuild=message.guild, dcUser=requestedUser,
                                                                                basedUser=targetBBUser)
            await queueChallengeMsg(message.channel, message.author.mention, targetUserNameOrTag)

        for msg in sentMsgs:
            menuTT = timedTask.TimedTask(expiryDelta=timedelta(**cfg.timeouts.duelChallengeMenuExpiry),
                                            expiryFunction=expiryFunctions.removeEmbedAndOptions, expiryFunctionArgs=msg.id)
            botState.client.taskScheduler.scheduleTask(menuTT)
            newMenu = reactionDuelChallengeMenu.ReactionDuelChallengeMenu(msg, newDuelReq, timeout=menuTT)
            newDuelReq.menus.append(newMenu)
            await newMenu.updateMessage()
            botState.client.reactionMenusDB[msg.id] = newMenu


    elif action == "cancel":
        if not sourceBBUser.hasDuelChallengeFor(targetBBUser):
            await message.reply(mention_author=False, content=":x: You do not have an active duel challenge for this user! Did it already expire?")
            return

        if message.guild.get_member(requestedUser.id) is None:
            await message.reply(mention_author=False, content=":white_check_mark: You have cancelled your duel challenge for **" \
                                        + str(requestedUser) + "**.")
            targetUserGuild = lib.discordUtil.findBBUserDCGuild(targetBBUser)
            if targetUserGuild is not None:
                targetUserBBGuild = botState.client.guildsDB.getGuild(targetUserGuild.id)
                if targetUserBBGuild.hasPlayChannel() and \
                        targetBBUser.isAlertedForID("duels_challenge_incoming_cancel", targetUserGuild, targetUserBBGuild,
                                                    targetUserGuild.get_member(targetBBUser.id)):
                    await targetUserBBGuild.getPlayChannel().send(":shield: " + requestedUser.mention + ", " \
                                                                    + str(message.author) \
                                                                    + " has cancelled their duel challenge.")
        else:
            if targetBBUser.isAlertedForID("duels_challenge_incoming_cancel", message.guild,
                                            botState.client.guildsDB.getGuild(message.guild.id),
                                            message.guild.get_member(targetBBUser.id)):
                await message.reply(mention_author=False, content=":white_check_mark: You have cancelled your duel challenge for " \
                                            + requestedUser.mention + ".")
            else:
                await message.reply(mention_author=False, content=":white_check_mark: You have cancelled your duel challenge for **" \
                                            + str(requestedUser) + "**.")

        # IDAlertedUserMentionOrName(alertType, dcUser=None, basedUser=None, basedGuild=None, dcGuild=None)
        for menu in sourceBBUser.duelRequests[targetBBUser].menus:
            await menu.delete()
        await sourceBBUser.duelRequests[targetBBUser].duelTimeoutTask.forceExpire(callExpiryFunc=False)
        sourceBBUser.removeDuelChallengeTarget(targetBBUser)

    elif action in ["reject", "decline"]:
        if not targetBBUser.hasDuelChallengeFor(sourceBBUser):
            await message.reply(mention_author=False, content=":x: This user does not have an active duel challenge for you! Did it expire?")
            return

        duelReq = targetBBUser.duelRequests[sourceBBUser]
        await duelRequest.rejectDuel(duelReq, message, requestedUser, message.author)

    elif action == "accept":
        if not targetBBUser.hasDuelChallengeFor(sourceBBUser):
            await message.reply(mention_author=False, content=":x: This user does not have an active duel challenge for you! Did it expire?")
            return

        requestedDuel = targetBBUser.duelRequests[sourceBBUser]

        if sourceBBUser.credits < requestedDuel.stakes:
            await message.reply(mention_author=False, content=":x: You do not have enough credits to accept this duel request! (" \
                                        + str(requestedDuel.stakes) + ")")
            return
        if targetBBUser.credits < requestedDuel.stakes:
            await message.reply(mention_author=False, content=":x:" + str(requestedUser) + " does not have enough credits to fight this duel! (" \
                                        + str(requestedDuel.stakes) + ")")
            return

        await duelRequest.fightDuel(message.author, requestedUser, requestedDuel, message)

botCommands.register("duel", cmd_duel, 0, forceKeepArgsCasing=True, allowDM=False, helpSection="bounty hunting",
                        signatureStr="**duel [action] [user]** *<stakes>*",
                        shortHelp="Fight other players! Action can be `challenge`, `cancel`, `accept` or `reject`.",
                        longHelp="Fight other players! Action can be `challenge`, `cancel`, `accept` or `reject`. " \
                                    + "When challenging another user to a duel, you must give the amount of credits " \
                                    + "you will win - the 'stakes'.")


async def cmd_use(message : discord.Message, args : str, isDM : bool):
    """Use the specified tool from the user's inventory.

    :param discord.Message message: the discord message calling the command
    :param str args: a single integer indicating the index of the tool to use
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    callingBUser: basedUser.BasedUser = botState.client.usersDB.getOrAddID(message.author.id)
    callingGuild: basedGuild.BasedGuild = botState.client.guildsDB.getGuild(message.guild.id)

    if not args:
        await message.reply(mention_author=False, content=":x: Please give the number of the tool you would like to use! e.g: `" \
                                    + callingGuild.commandPrefix + "use 1`")
    else:
        argsSplit = args.split(" ")
        toolNumStr = argsSplit[0]
        if len(argsSplit) == 1:
            args = ""
        else:
            args = args[len(toolNumStr)+1:]

        if not lib.stringTyping.isInt(toolNumStr):
            await message.reply(f":x: {truncateWithEllipse(toolNumStr, 15, 10)} is not a number!",
                                mention_author=False)
            return

        toolNum = int(toolNumStr)
        if toolNum < 1:
            await message.reply(mention_author=False, content=":x: Tool number must be at least 1!")
        elif callingBUser.inactiveTools.isEmpty():
            await message.reply(mention_author=False, content=":x: You don't have any tools to use!")
        elif toolNum > callingBUser.inactiveTools.numKeys:
            await message.reply(mention_author=False, content=":x: Tool number too big - you only have " + str(callingBUser.inactiveTools.numKeys) \
                                        + " tool" + ("" if callingBUser.inactiveTools.numKeys == 1 else "s") + "!")
        else:
            result = await callingBUser.inactiveTools[toolNum - 1].item.userFriendlyUse(message, args, ship=callingBUser.activeShip,
                                                                                        callingBUser=callingBUser)
            if result:
                await message.reply(mention_author=False, content=result)


botCommands.register("use", cmd_use, 0, allowDM=False, helpSection="bounty hunting", signatureStr="**use [tool number]**",
                        shortHelp="Use the tool in your hangar with the given number. See `hangar` for tool numbers.",
                        longHelp="Use the tool in your hangar with the given number. Tool numbers can be seen next your " \
                                    + "items in `hangar tool`. For example, if tool number `1` is a ship skin, `use 1` will" \
                                    + " apply the skin to your active ship.")


async def cmd_prestige(message : discord.Message, args : str, isDM : bool):
    """Reset the calling user's bounty hunter xp to zero and remove all of their items.
    Can only be used by level 10 bounty hunters.

    :param discord.Message message: the discord message calling the command
    :param str args: ignored
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    if not botState.client.usersDB.idExists(message.author.id):
        await message.channel.send(":x: This command can only be used by level 10 bounty hunters!")
        return

    callingBBUser: basedUser.BasedUser = botState.client.usersDB.getUser(message.author.id)
    if callingBBUser.classicModeEnabled:
        await message.reply(":x: This command is not available in classic mode!", mention_author=False)
        return
    if gameMaths.calculateUserBountyHuntingLevel(callingBBUser.bountyHuntingXP) < 10:
        await message.channel.send(":x: This command can only be used by level 10 bounty hunters!")
        return

    commandPrefix = cfg.defaultCommandPrefix if isDM else botState.client.guildsDB.getGuild(message.guild.id).commandPrefix

    confirmMsg = await message.channel.send("Are you sure you want to prestige now? Your bounty hunter level, loadout, " \
                                            + "balance, hangar and loma will all be **reset**.\n" \
                                            + "You will be awarded with a ship upgrade, and a special skins crate!\n" \
                                            + "You can save items from being removed by storing them in `" \
                                            + commandPrefix + "kaamo`, but you will not be able to retreive your " \
                                            + "items until you reach level 10.")
    confirmResult = await confirmationReactionMenu.InlineConfirmationMenu(confirmMsg, message.author,
                                                                            cfg.prestigeConfirmTimeoutSeconds).doMenu()

    if cfg.defaultEmojis.accept in confirmResult:
        callingBBUser.bountyHuntingXP = gameMaths.bountyHuntingXPForLevel(1)
        callingBBUser.activeShip = shipItem.Ship.deserialize(basedUser.defaultShipLoadoutDict)
        callingBBUser.credits = 0
        callingBBUser.inactiveShips.clear()
        callingBBUser.inactiveModules.clear()
        callingBBUser.inactiveWeapons.clear()
        for weaponDict in basedUser.defaultUserDict["inactiveWeapons"]:
            callingBBUser.inactiveWeapons.addItem(primaryWeapon.PrimaryWeapon.deserialize(weaponDict["item"]),
                                                    quantity=weaponDict["count"])
        callingBBUser.inactiveTurrets.clear()
        callingBBUser.inactiveTools.clear()
        if callingBBUser.loma is not None:
            callingBBUser.loma.shipsStock.clear()
            callingBBUser.loma.weaponsStock.clear()
            callingBBUser.loma.modulesStock.clear()
            callingBBUser.loma.turretsStock.clear()
            callingBBUser.loma.toolsStock.clear()

        callingBBUser.prestiges += 1
        newCrate = crateTool.CrateTool.deserialize({"type": "bbCrate", "crateType": "special", "typeNum": 0, "builtIn": True})
        callingBBUser.inactiveTools.addItem(newCrate)

        if callingBBUser.hasHomeGuild():
            homeGuild: basedGuild.BasedGuild = botState.client.guildsDB.getGuild(callingBBUser.homeGuildID)
            oldDiv = homeGuild.bountiesDB.divisionForLevel(cfg.maxTechLevel)
            oldDivName = nameForDivision(oldDiv)
            newDiv = homeGuild.bountiesDB.divisionForLevel(cfg.minTechLevel)
            newDivName = nameForDivision(newDiv)

            if homeGuild.hasBountyAlertRoles:
                oldRole = message.guild.get_role(oldDiv.alertRoleID)
                newRole = None
                if oldRole is None:
                    await message.channel.send(f":woozy_face: I can't find the {oldDivName.title()}" \
                                                + " division bounty alerts role, did it get deleted?")
                                                
                elif oldRole in message.author.roles:
                    newRole = message.guild.get_role(newDiv.alertRoleID)
                    if newRole is None:
                        await message.channel.send(":woozy_face: I can't find the " \
                                                + f"{newDivName.title()} division's bounty alerts " \
                                                + "role, did it get deleted?")
                
                if oldRole is not None or newRole is not None:
                    await homeGuild.levelUpSwapRoles(message.author, message.channel, oldRole, newRole,
                                                        actionOverride="prestiged")

        callingBBUser.bountyHuntingXpSurplus = -1

        await message.channel.send(":astronaut: **" + lib.discordUtil.userOrMemberName(message.author, message.guild) \
                                    + " prestiged!** :tada:\n • You got a **" + newCrate.name + "!**")
    else:
        await message.channel.send("🛑 Prestige cancelled.")


botCommands.register("prestige", cmd_prestige, 0, helpSection="bounty hunting", signatureStr="**prestige**",
                        shortHelp="Reset your items and bounty hunting XP, in exchange for a ship upgrade! " \
                            + "Command unlocked at level 10. Kaamo items are saved.",
                        longHelp="Reset your save data, including your bounty hunter level, loadout, balance, hangar and " \
                            + "loma. You will be awarded with a ship upgrade available in Loma!\n\n" \
                            + "You can save items from being removed by first storing them in `Kaamo`. Items stored in " \
                            + "`Kaamo` will be made accessible again once you reach level 10!")


async def cmd_div_up(message : discord.Message, args : str, isDM : bool):
    """Ascend to the next division.

    :param discord.Message message: the discord message calling the command
    :param str args: ignored
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    if not botState.client.usersDB.idExists(message.author.id):
        await message.reply(":x: You don't have enough XP to go to the next division!", mention_author=False)
        return

    callingBBUser: basedUser.BasedUser = botState.client.usersDB.getUser(message.author.id)
    if callingBBUser.classicModeEnabled:
        await message.reply(":x: This command is not available in classic mode!", mention_author=False)
        return

    commandPrefix = cfg.defaultCommandPrefix if isDM else botState.client.guildsDB.getGuild(message.guild.id).commandPrefix

    if not callingBBUser.hasHomeGuild():
        await message.reply(f":x: You must have a **home server** to use this command (see `{commandPrefix}transfer`).",
                            mention_author=False)
        return

    userLevel = gameMaths.calculateUserBountyHuntingLevel(callingBBUser.bountyHuntingXP)
    if userLevel == cfg.maxTechLevel:
        await message.reply(f":x: You have reached the highest division! (see `{commandPrefix}prestige`)",
                            mention_author=False)
        return

    if not callingBBUser.canDivUp():
        await message.reply(":x: You don't have enough XP to go to the next division!", mention_author=False)
        return
    
    homeGuild: basedGuild.BasedGuild = botState.client.guildsDB.getGuild(callingBBUser.homeGuildID)

    newLevel = userLevel + 1
    newDiv = homeGuild.bountiesDB.divisionForLevel(newLevel)
    confirmMsg = await message.reply(f"Ascend to the {nameForDivision(newDiv).title()} division? " \
                                    + "Make sure you can defeat bounties there first!",
                                    mention_author=False)
    confirmResult = await confirmationReactionMenu.InlineConfirmationMenu(confirmMsg, message.author,
                                                                            cfg.prestigeConfirmTimeoutSeconds).doMenu()

    if cfg.defaultEmojis.accept in confirmResult:
        oldDiv = homeGuild.bountiesDB.divisionForLevel(userLevel)
        oldDivName, newDivName = nameForDivision(oldDiv), nameForDivision(newDiv)

        callingBBUser.bountyHuntingXP += callingBBUser.bountyHuntingXpSurplus
        callingBBUser.bountyHuntingXpSurplus = -1

        levelUpCrate = bbData.builtInCrateObjs["levelUp"][newLevel]
        callingBBUser.inactiveTools.addItem(levelUpCrate)

        await confirmMsg.reply(":arrow_double_up: **New Division Reached!** :sparkles:\n" \
                            + f"{message.author.mention} hit **Bounty Hunter Level {newLevel}**, and reached the " \
                            + f"**{newDivName.title()} Division!** :partying_face:\n" \
                            + f"You got a **{levelUpCrate.name}**.")
    
        if homeGuild.hasBountyAlertRoles:
            oldRole = message.guild.get_role(oldDiv.alertRoleID)
            newRole = None
            if oldRole is None:
                await message.channel.send(f":woozy_face: I can't find the {oldDivName.title()}" \
                                            + " division bounty alerts role, did it get deleted?")
                                            
            elif oldRole in message.author.roles:
                newRole = message.guild.get_role(newDiv.alertRoleID)
                if newRole is None:
                    await message.channel.send(":woozy_face: I can't find the " \
                                            + f"{newDivName.title()} division's bounty alerts " \
                                            + "role, did it get deleted?")
            
            if oldRole is not None or newRole is not None:
                await homeGuild.levelUpSwapRoles(message.author, message.channel, oldRole, newRole)
    else:
        await confirmMsg.edit(content="🛑 Div-up cancelled.")


botCommands.register("div-up", cmd_div_up, 0, helpSection="bounty hunting", signatureStr="**div-up**",
                        aliases=["divup", "division-up", "divisionup"],
                        shortHelp="Level up into the next division of bounties. Higher level bounties are stronger, but" \
                                + " give bigger rewards.",
                        longHelp="Once you complete the highest level in your division, you can level up into the next " \
                                + "division, unlocking higher level bounties. You will no longer be " \
                                + "able to fight bounties in your current division.\nHigher level bounties are stronger, " \
                                + "but give bigger rewards.\n\nBefore you div-up, have a look at bounties in the division " \
                                + "that you are entering - it may be worth staying in your current division to save up for " \
                                + "some better gear first!\nIf you decide that you are not strong enough after you div-up, " \
                                + "you can drop back down a division with the `div-down` command, though you'll have to " \
                                + "work your way back up again.")


async def cmd_div_down(message : discord.Message, args : str, isDM : bool):
    """Descend a division.

    :param discord.Message message: the discord message calling the command
    :param str args: ignored
    :param bool isDM: Whether or not the command is being called from a DM channel
    """
    if not botState.client.usersDB.idExists(message.author.id):
        await message.reply(":x: You are already in the lowest division!", mention_author=False)
        return

    callingBBUser: basedUser.BasedUser = botState.client.usersDB.getUser(message.author.id)
    if callingBBUser.classicModeEnabled:
        await message.reply(":x: This command is not available in classic mode!", mention_author=False)
        return

    commandPrefix = cfg.defaultCommandPrefix if isDM else botState.client.guildsDB.getGuild(message.guild.id).commandPrefix

    if not callingBBUser.hasHomeGuild():
        await message.reply(f":x: You must have a **home server** to use this command (see `{commandPrefix}transfer`).",
                            mention_author=False)
        return
    
    homeGuild: basedGuild.BasedGuild = botState.client.guildsDB.getGuild(callingBBUser.homeGuildID)
    userLevel = gameMaths.calculateUserBountyHuntingLevel(callingBBUser.bountyHuntingXP)
    oldDiv = homeGuild.bountiesDB.divisionForLevel(userLevel)

    if oldDiv == homeGuild.bountiesDB.divisionForLevel(cfg.minTechLevel):
        await message.reply(":x: You are already in the lowest division!", mention_author=False)
        return

    newLevel = oldDiv.minLevel - 1
    newDiv = homeGuild.bountiesDB.divisionForLevel(newLevel)
    newXP = gameMaths.bountyHuntingXPForLevel(newDiv.maxLevel)

    confirmMsg = await message.reply(f"Are you sure you want to descend to the {nameForDivision(newDiv).title()}" \
                                    + f" division?\nAfter moving to level {newLevel}, you will need to earn " \
                                    + f"{commaSplitNum(newDiv.xpToDivUp() - newXP)} xp to return to the " \
                                    + f"{nameForDivision(oldDiv).title()} division.", mention_author=False)
    confirmResult = await confirmationReactionMenu.InlineConfirmationMenu(confirmMsg, message.author,
                                                                            cfg.prestigeConfirmTimeoutSeconds).doMenu()

    if cfg.defaultEmojis.accept in confirmResult:
        oldDivName, newDivName = nameForDivision(oldDiv), nameForDivision(newDiv)

        callingBBUser.bountyHuntingXP = newXP
        callingBBUser.bountyHuntingXpSurplus = -1

        levelUpCrate = bbData.builtInCrateObjs["levelUp"][newLevel]
        callingBBUser.inactiveTools.addItem(levelUpCrate)

        await confirmMsg.edit(content=f"⏬ {message.author.mention} descended to **Bounty Hunter Level {newLevel}**, " \
                                    + f"reaching the **{newDivName.title()} Division.**", embed=None)
    
        if homeGuild.hasBountyAlertRoles:
            oldRole = message.guild.get_role(oldDiv.alertRoleID)
            newRole = None
            if oldRole is None:
                await message.channel.send(f":woozy_face: I can't find the {oldDivName.title()}" \
                                            + " division bounty alerts role, did it get deleted?")
                                            
            elif oldRole in message.author.roles:
                newRole = message.guild.get_role(newDiv.alertRoleID)
                if newRole is None:
                    await message.channel.send(":woozy_face: I can't find the " \
                                            + f"{newDivName.title()} division's bounty alerts " \
                                            + "role, did it get deleted?")
            
            if oldRole is not None or newRole is not None:
                await homeGuild.levelUpSwapRoles(message.author, message.channel, oldRole, newRole,
                                                actionOverride="descended")
    else:
        await confirmMsg.edit(content="🛑 Div-down cancelled.", embed=None)


botCommands.register("div-down", cmd_div_down, 0, helpSection="bounty hunting", signatureStr="**div-down**",
                        aliases=["divdown", "division-down", "divisiondown",
                                "drop-div", "dropdiv", "drop-division", "dropdivision"],
                        shortHelp="Drop to the top of the next lowest division of bounties, to work your way back up again." \
                                + " This command is useful if you cannot fight bounties in your division.",
                        longHelp="After moving to a new division, you may find that the lowest level of bounties are too" \
                                + " strong to fight with your current gear. This command will drop your bounty hunter level" \
                                + " to the highest level of the next lowest division, allowing you to save up some credits" \
                                + " on easier bounties and build up your gear.\nYou will need to work your way back up to " \
                                + "your current division again before you can return!")
