from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union, cast
from PIL.Image import Image

from discord import Colour, Embed, File, Guild, HTTPException, Member, User, app_commands, Interaction, ButtonStyle
from discord.abc import Snowflake
from discord.ui import View, Button

from .. import client, botState
from ..cfg import cfg, bbData
from ..cfg.cfg import basicAccessLevels
from ..cfg.bbData import ItemCategory
from ..interactions import basedCommand
from ..interactions.basedApp import BasedCog
from ..interactions.basedComponent import StaticComponents
from ..interactions.commandChecks import homeGuildOnly, guildOnly
from ..users import basedUser
from ..users.basedUser import BasedUser
from .util.CommonAutocomplete import systemAutoComplete, divisionAutoComplete, activeCriminalAutoComplete, inventoryItemNumberAutoComplete
from ..lib.timeUtil import td_format_noYM
from ..lib.gameMaths import calculateUserBountyHuntingLevel, bountyHuntingXPForLevel
from ..lib.discordUtil import BasicScheduler, textChannel, criminalNameOrDiscrim, ImageFile, ZWSP, memberDisplayNameOrUserNameAndDiscrim
from ..lib.stringTyping import commaSplitNum
from ..lib.emojis import BasedEmoji
from ..databases.bountyDB import BountyDB, nameForDivision
from ..gameObjects.bounties.bounty import CheckResult, RewardsMeta, Bounty
from ..gameObjects.battles.duelRequest import fightShips, buildDuelResultsImage, makeDuelStatsEmbed
from ..gameObjects.items.shipItem import Ship
from ..gameObjects.items.gameItem import GameItem
from ..gameObjects.items.tools import toolItemFactory
from ..gameObjects.items.tools.crateTool import CrateTool
from ..gameObjects.items.weapons.primaryWeapon import PrimaryWeapon
from ..logging import LogCategory
from ..views.confirmView import ConfirmView


class UserBountiesCog(BasedCog):
#region util

    async def fightShips(self, initiator: BasedUser, dcInitiator: Union[User, Member], receiver: Bounty) -> Tuple[Optional[Ship], Embed, Optional[Image]]:
        if receiver.activeShip is None: raise ValueError(f"Receiver {receiver} does not have an active ship")

        duelResults = fightShips(initiator.activeShip,
                                receiver.activeShip,
                                cfg.duelVariancePercent)
        try:
            duelResultsImg = await buildDuelResultsImage(initiator, initiator.activeShip,
                                                        receiver.criminal, receiver.activeShip,
                                                        duelResults)
        except RuntimeError:
            statsEmbed = makeDuelStatsEmbed(duelResults, receiver.criminal, dcInitiator)

            statsEmbed.set_footer(text="An unexpected error occurred when building your duel results image." \
                                    + " The error has been logged.")
            return duelResults.winnerShip, statsEmbed, None
        else:
            statsEmbed = Embed()
            return duelResults.winnerShip, statsEmbed, duelResultsImg


    def setEmbedImageToFile(self, embed: Embed, image: Image, fileName: str) -> ImageFile:
        f = ImageFile(image, fileName)
        embed.set_image(url=f"attachment://{fileName}")
        return f


    def distributeBountyRewards(self, bounty: Bounty, bountyDB: BountyDB, basedUsers: Dict[int, BasedUser]) -> Tuple[Dict[int, Dict[str, Union[int, bool]]], Dict[int, RewardsMeta]]:
        classicModeUserIDs = set(u.id for u in basedUsers.values() if u.classicModeEnabled)
        nonClassicModeUserIDs = set(u.id for u in basedUsers.values() if u.id not in classicModeUserIDs)

        # reward all contributing users
        rewards = bounty.calcRewards(classicModeUserIDs)
        rewardsMeta = {i: RewardsMeta.NONE for i in rewards}

        # userID: reward
        distributeRewards: Dict[int, int] = {}
        guildMaxDiv = bountyDB.divisionForLevel(cfg.maxTechLevel)

        for userID in nonClassicModeUserIDs:
            currentBBUser = basedUsers[userID]
            currentLevel = calculateUserBountyHuntingLevel(currentBBUser.bountyHuntingXP)
            currentDiv = bountyDB.divisionForLevel(currentLevel)
            
            # If the bounty is in the highest division, but the user has since moved to a new division
            # (i.e they have prestiged), Share their rewards equally amongst the other contributors
            # https://github.com/GOF2BountyBot/GOF2BountyBot/issues/462
            if bounty.division == guildMaxDiv and currentDiv != guildMaxDiv:
                rewardsMeta[userID] = RewardsMeta.USER_PRESTIGED | rewardsMeta[userID]
                distributeRewards[userID] = rewards[userID]["reward"]
            
            # Make sure that xp does not go over the maximum
            if currentLevel == cfg.maxTechLevel - 1:
                maxLevelXp = bountyHuntingXPForLevel(cfg.maxTechLevel)
                # Casting here because we know the user does not have classic mode enabled
                if rewards[userID]["xp"] + cast(int, currentBBUser.bountyHuntingXP) > maxLevelXp:
                    rewards[userID]["xp"] = maxLevelXp - cast(int, currentBBUser.bountyHuntingXP)

        # share rewards lost due to prestiging
        if distributeRewards:
            totalToShare = sum(distributeRewards.values())
            receiverIDs = [i for i in rewards if i not in distributeRewards and i in nonClassicModeUserIDs]
            each = int(totalToShare / len(receiverIDs))
            for receiverID in receiverIDs:
                rewards[receiverID]["reward"] += each

        return rewards, rewardsMeta


    def handleLevelUps(self, rewards: Dict[int, Dict[str, Union[int, bool]]], rewardsMeta: Dict[int, RewardsMeta], basedUsers: Dict[int, BasedUser], bountyDB: BountyDB) -> Dict[BasedUser, List[GameItem]]:
        leveledUp: Dict[BasedUser, List[GameItem]] = {}

        for userID in rewards:
            # If the bounty is in the highest division, but the user has since moved to a new division
            # (i.e they have prestiged), Share their rewards equally amongst the other contributors
            # https://github.com/GOF2BountyBot/GOF2BountyBot/issues/462
            if RewardsMeta.USER_PRESTIGED & rewardsMeta[userID]:
                continue

            currentBBUser = basedUsers[userID]
            currentBBUser.credits += rewards[userID]["reward"]
            currentBBUser.lifetimeBountyCreditsWon += rewards[userID]["reward"]

            if currentBBUser.classicModeEnabled:
                continue

            oldLevel = calculateUserBountyHuntingLevel(currentBBUser.bountyHuntingXP)
            if oldLevel == cfg.maxTechLevel:
                continue
            
            oldDiv = bountyDB.divisionForLevel(oldLevel)
            
            if oldLevel == oldDiv.maxLevel:
                if not currentBBUser.canDivUp():
                    divUpXp = oldDiv.xpToDivUp()
                    # Casting here because we know the user does not have classic mode enabled due to the earlier check
                    newUserXp = cast(int, currentBBUser.bountyHuntingXP) + rewards[userID]["xp"]
                    if divUpXp < newUserXp:
                        currentBBUser.bountyHuntingXP = divUpXp - 1
                        currentBBUser.bountyHuntingXpSurplus = newUserXp - currentBBUser.bountyHuntingXP
                    else:
                        # Casting here because we know the user does not have classic mode enabled due to the earlier check
                        currentBBUser.bountyHuntingXP = cast(int, currentBBUser.bountyHuntingXP) + rewards[userID]["xp"]
            else:
                # Casting here because we know the user does not have classic mode enabled due to the earlier check
                currentBBUser.bountyHuntingXP = cast(int, currentBBUser.bountyHuntingXP) + rewards[userID]["xp"]
                
            newLevel = calculateUserBountyHuntingLevel(currentBBUser.bountyHuntingXP)
            if newLevel > oldLevel:
                leveledUp[currentBBUser] = []
                for currentLevel in range(oldLevel+1, newLevel+1):
                    levelUpCrate = bbData.builtInCrateObjs["levelUp"][currentLevel]
                    currentBBUser.inactiveTools.addItem(levelUpCrate)
                    leveledUp[currentBBUser].append(levelUpCrate)

        return leveledUp

#endregion util

#region static components

    BasedCog.staticComponentCallback(StaticComponents.User_ToggleClassicMode_Confirm)
    async def toggleClassicMode(self, interaction: Interaction, userId: str):
        callingUser = self.bot.usersDB.getOrAddID(int(userId))
        if callingUser.classicModeEnabled:
            callingUser.disableClassicMode()
            await interaction.response.send_message(f"{cfg.defaultEmojis.submit} You have now disabled classic mode.")
        else:
            callingUser.enableClassicMode()
            await interaction.response.send_message(f"{cfg.defaultEmojis.submit} You have now enabled classic mode.")

        try:
            await interaction.delete_original_response()
        except HTTPException:
            try:
                await interaction.edit_original_response(view=None)
            except HTTPException:
                pass

#endregion static components

    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="bounty hunting",
                                formattedDesc="Toggle BountyBot's \"classic mode\", which emulates the BountyBot beta.\n" \
                                                + "In this mode, you win bounties immediately by finding the correct system - " \
                                                + "you do not need to duel bounties to win.\n"
                                            + f"You will receive a fixed **{cfg.classic_creditsPerCheck} credits** per system check.\n" \
                                            + "XP and levelling are disabled, meaning you will not get level-up, division-up " \
                                                + "or prestige bonuses.\n"
                                            + f"You are restricted to bounties in the lowest division ({cfg.bountyDivisionNames[0]}).\n" \
                                            + "Use this command to enable or disable classic mode, at any time.")
    @app_commands.command(name="classic-mode",
                            description="Toggle \"classic mode\", which emulates the BountyBot beta. " \
                                        + "See /help for more info.")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guilds(*cfg.developmentGuilds)
    async def cmd_toggle_classic_mode(self, interaction: Interaction):
        """Toggle 'classic mode' for the calling user.
        """
        callingUser: Optional[BasedUser] = None
        if self.bot.usersDB.idExists(interaction.user.id):
            callingUser = self.bot.usersDB.getUser(interaction.user.id)
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

        view = View()

        confirmButton = Button(style=ButtonStyle.primary, label=f"Toggle Classic Mode")
        confirmButton = StaticComponents.User_ToggleClassicMode_Confirm(confirmButton, args=str(interaction.user.id))
        view.add_item(confirmButton)
        
        cancelButton = Button(style=ButtonStyle.danger, label=f"Cancel")
        cancelButton = StaticComponents.Clear_View(cancelButton, args=str(interaction.user.id))
        view.add_item(cancelButton)

        menuEmbed = Embed(description="Toggle classic mode now?\nThis command can be used again at any time.", colour=Colour.random())

        await interaction.response.send_message(confirmMsgText, embed=menuEmbed, ephemeral=True)


    @homeGuildOnly()
    @guildOnly(bountiesEnabled=True)
    @systemAutoComplete()
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="bounty hunting",
                                formattedDesc="Check if any criminals are in the given system, arrest them, and get paid! 💰" \
                                            + "\n🌎 This command must be used in your **home server**.")
    @app_commands.command(name="check",
                            description="🌎 Check if any criminals are in the given system, and fight them! (home server only)")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def cmd_check(self, interaction: Interaction, system: str):
        """Check a system for bounties and handle rewards
        """
        requestedBBUser = self.bot.usersDB.getUser(interaction.user.id)

        # If the calling user is on checking cooldown
        if datetime.utcfromtimestamp(requestedBBUser.bountyCooldownEnd) < datetime.utcnow():
            diff = datetime.utcfromtimestamp(requestedBBUser.bountyCooldownEnd) - datetime.utcnow()
            await interaction.response.send_message(":stopwatch: Your *Khador Drive* is still charging!" \
                                                    + f" please wait **{td_format_noYM(diff)}.**")
            return

        # Casting here because this command uses the guildOnly decorator
        dcGuild = cast(Guild, interaction.guild)
        callingGuild = self.bot.guildsDB.getGuild(dcGuild.id)
        # Casting here because this command requires the calling guild to have bounties enabled in the guildOnly decorator
        bountyDB = cast(BountyDB, callingGuild.bountiesDB)

        if requestedBBUser.classicModeEnabled:
            btyDivision = bountyDB.divisionForName(cfg.classic_divisionName)
        else:
            userLevel = calculateUserBountyHuntingLevel(requestedBBUser.bountyHuntingXP)
            btyDivision = bountyDB.divisionForLevel(userLevel)

        divisionBounties = btyDivision.allBountiesForSystem(system)
        if not divisionBounties:
            await interaction.response.send_message(f":telescope: **{interaction.user.display_name}**, you did not find any criminals in **{system}**!")
            return

        await interaction.response.defer(ephemeral=False, thinking=True)

        bountyWon = False
        bountyLost = False
        systemInBountyRoute = False

        # list of completed bounties to remove from the bounties database
        toPop: List[Bounty] = []
        toEscape: List[Bounty] = []
        sightedCriminalsStr = ""
        # The total amount to increase the division's activity temperature by
        divTempDelta = 0

        resultsEmbeds: List[Embed] = []
        resultsImages: List[ImageFile] = []
        resultsFiles: List[File] = []

        announcementsTasks = BasicScheduler()
        async def clearAnnouncementsTasks(logCategory: Optional[LogCategory] = None):
            await announcementsTasks.wait()
            announcementsTasks.logExceptions(logCategory=logCategory)
            announcementsTasks.clear()

        for bountyNum, bounty in enumerate(divisionBounties):
            # Check the passed system in current bounty
            checkResult = bounty.check(system, requestedBBUser.id)
            if checkResult == CheckResult.NOT_FOUND: continue

            # If current bounty resides in the requested system
            if checkResult == CheckResult.CORRECT:
                if requestedBBUser.classicModeEnabled or not bounty.hasShip:
                    duelWon = True
                else:
                    winnerShip, statsEmbed, duelResultsImg = await self.fightShips(requestedBBUser, interaction.user, bounty)
                    if duelResultsImg:
                        duelResultsFile = self.setEmbedImageToFile(statsEmbed, duelResultsImg, f"duelResults{bountyNum}.png")
                        resultsFiles.append(duelResultsFile.file)
                        resultsImages.append(duelResultsFile)
                    
                    resultsEmbeds.append(statsEmbed)

                    if winnerShip is not requestedBBUser.activeShip:
                        statsEmbed.title = f"{bounty.criminal.name} escaped!"
                        toEscape.append(bounty)
                        bountyLost = True
                        duelWon = False
                    else:
                        duelWon = True

                if duelWon:
                    if not bountyWon: bountyWon = True

                    basedUsers = {i: self.bot.usersDB.getOrAddID(i) for i in set(bounty.checked.values()) if i != -1}

                    rewards, rewardsMeta = self.distributeBountyRewards(bounty, bountyDB, basedUsers)
                    levelUpRewards = self.handleLevelUps(rewards, rewardsMeta, basedUsers, bountyDB)

                    # Announce the bounty has been completed
                    announcementsTasks.add(callingGuild.announceBountyWon(bounty, rewards, interaction.user, rewardsMeta, levelUpRewards))

                    # Raise guild's activity temperature for this bounty's tl
                    divTempDelta += len(basedUsers) * cfg.activityTempPerPlayer

                    # add this bounty to the list of bounties to be removed
                    toPop.append(bounty)

            # Update routes in this division containing the checked system
            if checkResult != CheckResult.ALREADY_CHECKED:
                systemInBountyRoute = True
                announcementsTasks.add(callingGuild.updateBountyBoardChannel(bounty, bountyComplete=checkResult == CheckResult.CORRECT))
                # Check if any bounties are close to the requested system in their route,
                # defined by cfg.closeBountyThreshold
                distanceToAnswer = bounty.route.index(bounty.answer) - bounty.route.index(system)
                if checkResult == CheckResult.INCORRECT and 0 < distanceToAnswer < cfg.closeBountyThreshold:
                    # Print any close bounty names
                    sightedCriminalsStr += "\n**       **• Local security forces spotted **" \
                                            + criminalNameOrDiscrim(bounty.criminal) \
                                            + "** here recently."

        if announcementsTasks.any(): await clearAnnouncementsTasks(logCategory=LogCategory.bountiesDB)

        # remove all completed bounties
        for bounty in toPop:
            try:
                btyDivision.removeBountyObj(bounty)
            except (OverflowError, KeyError) as e:
                self.bot.logger.log("usr_bounties", "cmd_check", str(e), exception=e)

        # remove all escaped bounties
        for bounty in toEscape:
            bounty.escape()
            if bounty.division.bountyBoardChannel is not None:
                announcementsTasks.add(bounty.division.bountyBoardChannel.updateEscapedBountiesMessage())

        if announcementsTasks.any(): await clearAnnouncementsTasks(logCategory=LogCategory.bountyBoards)

        if divTempDelta:
            # Apply the gathered temperature raises to this division
            # This must be done after the bounty ojects are removed from the division, as this is the point at which
            # The division's maxBounties is compared, to see if the new bounty TT needs to be restarted
            btyDivision.raiseTemp(divTempDelta)

        # If a bounty was won, print a congratulatory message
        if bountyWon:
            requestedBBUser.bountyWins += 1
            content = f"{sightedCriminalsStr}\n:moneybag: **{interaction.user.display_name}**, you now have **{commaSplitNum(requestedBBUser.credits)} Credits!**"

        # If no bounty was won, print an error message
        else:
            if not bountyLost:
                content = f":telescope: **{interaction.user.display_name}**, you did not find any criminals in **{system}**!\n{sightedCriminalsStr}"

            else:
                content = sightedCriminalsStr

        # Batch in groups of 10 to keep within discord's limitations
        numResults = len(resultsEmbeds)
        if numResults > 10:
            await interaction.followup.send(content=content, files=resultsFiles[0:10], embeds=resultsEmbeds[0:10])
            currentResult = 10
            while currentResult < numResults:
                nextMaxResult = min(numResults, currentResult + 10)
                await textChannel(interaction).send(files=resultsFiles[currentResult:nextMaxResult], embeds=resultsEmbeds[currentResult:nextMaxResult])
                currentResult = nextMaxResult
        
        else:
            await interaction.followup.send(content=content, files=resultsFiles, embeds=resultsEmbeds)

        # Only put the calling user on checking cooldown and increment systemsChecked stat if the system checked
        # is on an active bounty's route.
        if systemInBountyRoute:
            requestedBBUser.systemsChecked += 1
            # Put the calling user on checking cooldown
            requestedBBUser.bountyCooldownEnd = (datetime.utcnow() \
                                                    + cfg.timeouts.checkCooldown
                                                    + botState.utcOffset).timestamp()

        for i in resultsImages: i.closeAll()


    @guildOnly(bountiesEnabled=True)
    @divisionAutoComplete(allowAllDivisions=False)
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="bounty hunting",
                                formattedDesc="If no division is given, name all currently active bounties in your division.\n" \
                                            + "If a division is given, show all bountis in that division.\n")
    @app_commands.command(name="bounties",
                            description="List all active bounties in your division, or the one specified")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def cmd_bounties(self, interaction: Interaction, division: Optional[str] = None):
        """List a summary of all currently active bounties in one division.
        If no division is specified, the calling user's division is used.
        """
        # Casting here because this command is decorated with guildOnly
        callingGuild = self.bot.guildsDB.getGuild(cast(Guild, interaction.guild).id)
        # Casting here because this command is decorated with guildOnly with bountiesEnabled=True
        bountiesDB = cast(BountyDB, callingGuild.bountiesDB)

        if division is None:
            if self.bot.usersDB.idExists(interaction.user.id):
                bUser = self.bot.usersDB.getUser(interaction.user.id)
                userLevel = calculateUserBountyHuntingLevel(bUser.bountyHuntingXP)
            else:
                userLevel = cfg.minTechLevel
            divisionObj = bountiesDB.divisionForLevel(userLevel)
        else:
            divisionObj = bountiesDB.divisionForName(division)

        divName = nameForDivision(divisionObj).title()

        if divisionObj.isEmpty():
            await interaction.response.send_message(f":stopwatch: There are no {divName} division bounties active currently!")
            return
        
        msgEmbed = Embed(title=f"Active Bounties: {divName} Division",
                        description=f"Difficulty levels {divisionObj.minLevel} - {divisionObj.maxLevel} ~ " \
                                    + "Times given in UTC",
                        colour=Colour.random())
        msgEmbed.set_footer(icon_url=bbData.rocketIcon,
                            text=f"Track down criminals and win credits using /route " \
                                    + f"and /check!")

        # Collect and print summaries of all active bounties
        for tl, tlBounties in divisionObj.bounties.items():
            if not tlBounties: continue
            msgEmbed.add_field(name=ZWSP, value=f"__Level {tl}__", inline=False)

            for crim, bounty in tlBounties.items():
                timeLeft = datetime.utcfromtimestamp(bounty.endTime) - datetime.utcnow()
                if bounty.faction in bbData.bountyFactionEmojis:
                    factionEmoji = BasedEmoji(id=bbData.bountyFactionEmojis[bounty.faction]).sendable + " "
                else:
                    factionEmoji = ""
                msgEmbed.add_field(name=factionEmoji + criminalNameOrDiscrim(crim),
                                    value=f"• {int(bounty.reward)} Credits\n"
                                        + f"• {len(bounty.route)} possible systems\n" \
                                        + f"• Ending in {td_format_noYM(timeLeft)}")
        
        await interaction.response.send_message(embed=msgEmbed)


    @guildOnly(bountiesEnabled=True)
    @activeCriminalAutoComplete(paramName="criminal")
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="bounty hunting")
    @app_commands.command(name="route", description="Get the named criminal's current route.")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def cmd_route(self, interaction: Interaction, criminal: str):
        """Display the current route of the requested criminal
        """
        # Casting here because this command is decorated with guildOnly
        callingGuild = self.bot.guildsDB.getGuild(cast(Guild, interaction.guild).id)
        # Casting here because this command is decorated with guildOnly with bountiesEnabled=True
        bountiesDB = cast(BountyDB, callingGuild.bountiesDB)

        # The bounty name came from activeCriminalAutoComplete, so it should exist on the board
        bounty = bountiesDB.getBounty(criminal)
        await interaction.response.send_message(f"**{criminalNameOrDiscrim(bounty.criminal)}**'s current route:\n> " \
                                                + ", ".join((f"~~{system}~~" if bounty.systemChecked(system) else system) for system in bounty.route) \
                                                + ". :rocket:")

    
    @inventoryItemNumberAutoComplete("tool", ItemCategory.tool)
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="bounty hunting")
    @app_commands.command(name="use", description="Use a tool from your tools inventory.")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def cmd_use(self, interaction: Interaction, tool: int):
        """Use the specified tool from the user's inventory.
        """
        if self.bot.usersDB.idExists(interaction.user.id):
            callingBUser = self.bot.usersDB.getOrAddID(interaction.user.id)
            await callingBUser.inactiveTools.itemAtIndex(tool).userFriendlyUse(interaction, True, False)
        else:
            # Ignoring here because inactiveTools is not guaranteed, but inventoryItemNumberAutoComplete ensures that it exists
            toolObj = toolItemFactory.ToolItemFactory.deserialize(basedUser.defaultUserDict["inactiveTools"][tool]["item"]) # type: ignore[reportTypedDictNotRequiredAccess]
            await toolObj.userFriendlyUse(interaction, True, False)


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="bounty hunting",
                                formattedDesc="Reset your save data, including your bounty hunter level, loadout, balance, hangar and " \
                                            + "loma. You will be awarded with a ship upgrade available in Loma!\n\n" \
                                            + "You can save items from being removed by first storing them in `Kaamo`. Items stored in " \
                                            + "`Kaamo` will be made accessible again once you reach level 10!")
    @app_commands.command(name="prestige", description="Reset your items and bounty hunting XP, in exchange for a ship upgrade! See /help for more details.")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def cmd_prestige(self, interaction: Interaction):
        """Reset the calling user's bounty hunter xp to zero and remove all of their items.
        Can only be used by level 10 bounty hunters.
        """
        if not self.bot.usersDB.idExists(interaction.user.id):
            await interaction.response.send_message(":x: This command can only be used by level 10 bounty hunters!", ephemeral=True)
            return

        callingBBUser = self.bot.usersDB.getUser(interaction.user.id)
        if callingBBUser.classicModeEnabled:
            await interaction.response.send_message(":x: This command is not available in classic mode!", ephemeral=False)
            return

        if calculateUserBountyHuntingLevel(callingBBUser.bountyHuntingXP) < 10:
            await interaction.response.send_message(":x: This command can only be used by level 10 bounty hunters!", ephemeral=True)
            return

        view = ConfirmView(timeout=cfg.prestigeConfirmTimeoutSeconds)

        await interaction.response.send_message("Are you sure you want to prestige now? Your bounty hunter level, loadout, " \
                                                + "balance, hangar and loma will all be **reset**.\n" \
                                                + "You will be awarded with a ship upgrade, and a special skins crate!\n" \
                                                + "You can save items from being removed by storing them in `/" \
                                                + "kaamo`, but you will not be able to retreive your " \
                                                + "items until you reach level 10.",
                                                view=view)

        if await view.wait():
            await view.interaction.response.send_message("🛑 Prestige cancelled - out of time!", ephemeral=True)
            return

        if not view.confirmed:
            await view.interaction.response.send_message("🛑 Prestige cancelled.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)

        callingBBUser.bountyHuntingXP = bountyHuntingXPForLevel(1)
        callingBBUser.activeShip = Ship.deserialize(basedUser.defaultShipLoadoutDict)
        callingBBUser.credits = 0
        callingBBUser.inactiveShips.clear()
        callingBBUser.inactiveModules.clear()
        callingBBUser.inactiveWeapons.clear()
        for weaponDict in basedUser.defaultUserDict[basedUser.itemCategoryUserKeys[ItemCategory.weapon]]:
            callingBBUser.inactiveWeapons.addItem(PrimaryWeapon.deserialize(weaponDict["item"]),
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
        newCrate = CrateTool.deserialize({"type": "bbCrate", "crateType": "special", "typeNum": 0, "builtIn": True})
        callingBBUser.inactiveTools.addItem(newCrate)

        errors: List[str] = []
        if callingBBUser.hasHomeGuild():
            homeGuild = self.bot.guildsDB.getGuild(callingBBUser.homeGuildID)
            if (member := homeGuild.dcGuild.get_member(interaction.user.id)) and not homeGuild.bountiesDisabled:
                bountiesDB = cast(BountyDB, homeGuild.bountiesDB)
                oldDiv = bountiesDB.divisionForLevel(cfg.maxTechLevel)
                oldDivName = nameForDivision(oldDiv)
                newDiv = bountiesDB.divisionForLevel(cfg.minTechLevel)
                newDivName = nameForDivision(newDiv)

                if homeGuild.hasBountyAlertRoles:
                    oldRole = homeGuild.dcGuild.get_role(oldDiv.alertRoleID)
                    newRole = None
                    if oldRole is None:
                        errors.append(f"I was unable to update your bounty alerts role, because I can't find the {oldDivName.title()} division bounty alerts role.")
                                                    
                    elif oldRole in member.roles:
                        newRole = homeGuild.dcGuild.get_role(newDiv.alertRoleID)
                        if newRole is None:
                            errors.append(f"I was unable to update your bounty alerts role, because I can't find the {newDivName.title()} division bounty alerts role.")
                    
                    if oldRole is not None or newRole is not None:
                        errors += await homeGuild.levelUpSwapRoles(member, oldRole, newRole,
                                                            actionOverride="prestiged")

        callingBBUser.bountyHuntingXpSurplus = -1

        msg = f":astronaut: **{memberDisplayNameOrUserNameAndDiscrim(interaction.user, interaction.guild)}" + \
            f" prestiged!** :tada:\n • You got a **{newCrate.name}!**"
        
        if errors:
            msg += f"\n\nThe following error(s) occurred when updating your bounty alert role:\n" \
                + "\n".join(f"• {error}" for error in errors)
        await interaction.followup.send(msg)


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="bounty hunting",
                                formattedDesc="Once you complete the highest level in your division, you can level up into the next " \
                                            + "division, unlocking higher level bounties. You will no longer be " \
                                            + "able to fight bounties in your current division.\nHigher level bounties are stronger, " \
                                            + "but give bigger rewards.\n\nBefore you div-up, have a look at bounties in the division " \
                                            + "that you are entering - it may be worth staying in your current division to save up for " \
                                            + "some better gear first!\nIf you decide that you are not strong enough after you div-up, " \
                                            + "you can drop back down a division with the `div-down` command, though you'll have to " \
                                            + "work your way back up again.")
    @app_commands.command(name="div-up", description="Level up into the next division of bounties, and unlock tougher bounties with bigger rewards!")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def cmd_div_up(self, interaction: Interaction):
        """Ascend to the next division.
        """
        if not self.bot.usersDB.idExists(interaction.user.id):
            await interaction.response.send_message(":x: You don't have enough XP to go to the next division!", ephemeral=True)
            return

        callingBBUser = self.bot.usersDB.getUser(interaction.user.id)
        if callingBBUser.classicModeEnabled:
            await interaction.response.send_message(":x: This command is not available in classic mode!", ephemeral=True)
            return

        if not callingBBUser.hasHomeGuild():
            await interaction.response.send_message(f":x: You must have a **home server** to use this command (see `/transfer`).",
                                                    ephemeral=True)
            return

        userLevel = calculateUserBountyHuntingLevel(callingBBUser.bountyHuntingXP)
        if userLevel == cfg.maxTechLevel:
            await interaction.response.send_message(f":x: You have reached the highest division! (see `/prestige`)",
                                                    ephemeral=True)
            return

        if not callingBBUser.canDivUp():
            await interaction.response.send_message(":x: You don't have enough XP to go to the next division!", ephemeral=True)
            return
        
        homeGuild = self.bot.guildsDB.getGuild(callingBBUser.homeGuildID)
        if homeGuild.bountiesDisabled:
            await interaction.response.send_message(":x: Bounties are disabled in your home server!", ephemeral=True)
            return

        bountiesDB = cast(BountyDB, homeGuild.bountiesDB)
        newLevel = userLevel + 1
        newDiv = bountiesDB.divisionForLevel(newLevel)

        view = ConfirmView(timeout=cfg.prestigeConfirmTimeoutSeconds)

        await interaction.response.send_message(f"Ascend to the {nameForDivision(newDiv).title()} division? " \
                                                + "Make sure you can defeat bounties there first!",
                                                ephemeral=False, view=view)

        if await view.wait():
            await interaction.response.send_message("🛑 Div-up cancelled - out of time!", ephemeral=True)
            return

        if not view.confirmed:
            await interaction.response.send_message("🛑 Div-up cancelled.", ephemeral=True)
            return

        oldDiv = bountiesDB.divisionForLevel(userLevel)
        oldDivName, newDivName = nameForDivision(oldDiv), nameForDivision(newDiv)
        
        # Casting here because we already know the user does not have classic mode enabled
        callingBBUser.bountyHuntingXP = cast(int, callingBBUser.bountyHuntingXP) + callingBBUser.bountyHuntingXpSurplus
        callingBBUser.bountyHuntingXpSurplus = -1

        levelUpCrate = bbData.builtInCrateObjs["levelUp"][newLevel]
        callingBBUser.inactiveTools.addItem(levelUpCrate)

        await interaction.response.defer(ephemeral=True, thinking=True)
        errors: List[str] = []

        if homeGuild.hasBountyAlertRoles and (member := homeGuild.dcGuild.get_member(interaction.user.id)):
            oldRole = homeGuild.dcGuild.get_role(oldDiv.alertRoleID)
            newRole = None
            if oldRole is None:
                errors.append(f"I can't find the {oldDivName.title()} division bounty alerts role, was it deleted?")
                                            
            elif oldRole in member.roles:
                newRole = homeGuild.dcGuild.get_role(newDiv.alertRoleID)
                if newRole is None:
                    errors.append(f"I can't find the {newDivName.title()} division's bounty alerts role, was it deleted?")
            
            if oldRole is not None or newRole is not None:
                errors += await homeGuild.levelUpSwapRoles(member, oldRole, newRole)

        msg = ":arrow_double_up: **New Division Reached!** :sparkles:\n" \
            + f"{interaction.user.mention} hit **Bounty Hunter Level {newLevel}**, and reached the " \
            + f"**{newDivName.title()} Division!** :partying_face:\n" \
            + f"You got a **{levelUpCrate.name}**."

        if errors:
            msg += "\n\nThe following error(s) occurred when updating your bounty alert role:" \
                    + "\n".join(f"- {error}" for error in errors)

        await interaction.followup.send(msg)


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="bounty hunting",
                                formattedDesc="After moving to a new division, you may find that the lowest level of bounties are too" \
                                            + " strong to fight with your current gear. This command will drop your bounty hunter level" \
                                            + " to the highest level of the next lowest division, allowing you to save up some credits" \
                                            + " on easier bounties and build up your gear.\nYou will need to work your way back up to " \
                                            + "your current division again before you can return!")
    @app_commands.command(name="div-down", description="Drop to the top of the next lowest division of bounties, to work your way back up again.")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def cmd_div_down(self, interaction: Interaction):
        """Descend a division.
        """
        if not self.bot.usersDB.idExists(interaction.user.id):
            await interaction.response.send_message(":x: You are already in the lowest division!", ephemeral=True)
            return

        callingBBUser = self.bot.usersDB.getUser(interaction.user.id)
        if callingBBUser.classicModeEnabled:
            await interaction.response.send_message(":x: This command is not available in classic mode!", ephemeral=True)
            return

        if not callingBBUser.hasHomeGuild():
            await interaction.response.send_message(f":x: You must have a **home server** to use this command (see `/transfer`).",
                                                    ephemeral=True)
            return
        
        homeGuild = self.bot.guildsDB.getGuild(callingBBUser.homeGuildID)
        if homeGuild.bountiesDisabled:
            await interaction.response.send_message(":x: Bounties are disabled in your home server!", ephemeral=True)
            return

        bountiesDB = cast(BountyDB, homeGuild.bountiesDB)

        userLevel = calculateUserBountyHuntingLevel(callingBBUser.bountyHuntingXP)
        oldDiv = bountiesDB.divisionForLevel(userLevel)

        if oldDiv == bountiesDB.divisionForLevel(cfg.minTechLevel):
            await interaction.response.send_message(":x: You are already in the lowest division!", ephemeral=True)
            return

        newLevel = oldDiv.minLevel - 1
        newDiv = bountiesDB.divisionForLevel(newLevel)
        newXP = bountyHuntingXPForLevel(newDiv.maxLevel)

        view = ConfirmView(timeout=cfg.prestigeConfirmTimeoutSeconds)

        await interaction.response.send_message(f"Are you sure you want to descend to the {nameForDivision(newDiv).title()}" \
                                                + f" division?\nAfter moving to level {newLevel}, you will need to earn " \
                                                + f"{commaSplitNum(newDiv.xpToDivUp() - newXP)} xp to return to the " \
                                                + f"{nameForDivision(oldDiv).title()} division.", ephemeral=True, view=view)

        if await view.wait():
            await interaction.response.send_message("🛑 Div-down cancelled - out of time!", ephemeral=True)
            return

        if not view.confirmed:
            await interaction.response.send_message("🛑 Div-down cancelled.", ephemeral=True)
            return

        oldDivName, newDivName = nameForDivision(oldDiv), nameForDivision(newDiv)

        callingBBUser.bountyHuntingXP = newXP
        callingBBUser.bountyHuntingXpSurplus = -1

        levelUpCrate = bbData.builtInCrateObjs["levelUp"][newLevel]
        callingBBUser.inactiveTools.addItem(levelUpCrate)

        await interaction.response.defer(ephemeral=True, thinking=True)
        errors: List[str] = []

        if homeGuild.hasBountyAlertRoles and (member := homeGuild.dcGuild.get_member(interaction.user.id)):
            oldRole = homeGuild.dcGuild.get_role(oldDiv.alertRoleID)
            newRole = None
            if oldRole is None:
                errors.append(f"I can't find the {oldDivName.title()} division bounty alerts role, was it deleted?")
                                            
            elif oldRole in member.roles:
                newRole = homeGuild.dcGuild.get_role(newDiv.alertRoleID)
                if newRole is None:
                    errors.append(f"I can't find the {newDivName.title()} division's bounty alerts role, was it deleted?")
            
            if oldRole is not None or newRole is not None:
                errors += await homeGuild.levelUpSwapRoles(member, oldRole, newRole,
                                                            actionOverride="descended")

        msg = f"⏬ {interaction.user.mention} descended to **Bounty Hunter Level {newLevel}**, " \
            + f"reaching the **{newDivName.title()} Division.**"

        if errors:
            msg += "\n\nThe following error(s) occurred when updating your bounty alert role:" \
                    + "\n".join(f"- {error}" for error in errors)

        await interaction.followup.send(msg)


async def setup(bot: client.BasedClient):
    # Casting here because for some reason pyright doesn't think SerializableDiscordObject is a Snowflake,
    # even though it extends discord.Object
    await bot.add_cog(UserBountiesCog(bot), guilds=cast(List[Snowflake], cfg.developmentGuilds))
