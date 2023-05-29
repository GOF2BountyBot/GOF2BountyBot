from typing import List, Optional, Tuple, Union, cast

from discord import ButtonStyle, Member, User, app_commands, Interaction
from discord.abc import Snowflake
from discord.ui import View, Button

from .. import client, botState
from ..cfg import cfg
from ..cfg.cfg import basicAccessLevels
from ..interactions import basedCommand
from ..interactions.basedApp import BasedCog
from ..interactions.basedComponent import StaticComponents
from ..lib.discordUtil import memberDisplayNameOrUserNameAndDiscrim, timestamp, TimeStampStyle
from ..lib.stringTyping import isInt
from ..gameObjects.battles.duelRequest import DuelRequest, expireAndAnnounceDuelReq, fightDuel
from ..scheduling.timedTask import TimedTask
from ..userAlerts import userAlerts

DUELCHALLENGEMENU_CUSTOMID_ARGS_SEPARATOR = "#"

def packDuelChallengeMenuArgs(sourceUserId: int, targetUserId: int) -> str:
    return f"{sourceUserId}{DUELCHALLENGEMENU_CUSTOMID_ARGS_SEPARATOR}{targetUserId}"

def unpackDuelChallengeMenuArgs(args: str) -> Tuple[int, int]:
    sourceUserId, targetUserId = args.split(DUELCHALLENGEMENU_CUSTOMID_ARGS_SEPARATOR)
    return int(sourceUserId), int(targetUserId)


class UserDuelsCog(BasedCog):
#region util

    async def getDuelChallengeTarget(self, interaction: Interaction, target: Optional[Union[User, Member]], target_id: Optional[str]) -> Optional[Union[User, Member]]:
        if target_id is not None:
            if target is not None:
                await interaction.response.send_message(":x: Please only give one of `target` or `target_id`!", ephemeral=True)
                return None
            if not isInt(target_id):
                await interaction.response.send_message(":x: Invalid `target_id` - must be a number.", ephemeral=True)
                return None

            target = self.bot.get_user(int(target_id))
            if target is None:
                await interaction.response.send_message(":x: Unknown user!", ephemeral=True)
                return None

        elif target is None:
            await interaction.response.send_message(":x: Please give one of `target` or `target_id`!", ephemeral=True)
            return None

        if target == interaction.user:
            await interaction.response.send_message(":x: You can't challenge yourself!", ephemeral=True)
            return None

        return target

    
    async def handleAcceptDuel(self, interaction: Interaction, sourceUserId: int, isMenu: bool):
        if not (self.bot.usersDB.idExists(sourceUserId) and self.bot.usersDB.idExists(interaction.user.id)):
            if sourceDcUser := self.bot.get_user(sourceUserId):                
                await interaction.response.send_message(f":x: **{sourceDcUser}** has not sent you a duel challenge! If they have sent you one in the past, it may have expired.", ephemeral=True)
            else:
                await interaction.response.send_message(":x: I can't find the user that issued this duel, they may have deleted their account.", ephemeral=True)
            if isMenu:
                await interaction.edit_original_response(view=None)
            return

        sourceUser = self.bot.usersDB.getUser(sourceUserId)
        targetUser = self.bot.usersDB.getUser(interaction.user.id)

        duel = sourceUser.duelRequests[targetUser]

        def expireDuel():
            if duel.duelTimeoutTask is not None:
                duel.duelTimeoutTask.forceExpire(callExpiryFunc=False)
            sourceUser.removeDuelChallengeTarget(targetUser)
        
        if not sourceUser.hasDuelChallengeFor(targetUser):
            await interaction.response.send_message(":x: This duel challenge has expired.", ephemeral=True)
            if isMenu:
                await interaction.edit_original_response(view=None)
            return

        sourceDcUser = self.bot.get_user(sourceUser.id)
        if sourceDcUser is None:
            expireDuel()
            await interaction.response.send_message(":x: I can't find the user that issued this duel, they may have deleted their account.", ephemeral=True)
            return

        if isMenu:
            await interaction.response.edit_message(view=None)
        else:
            await interaction.response.send_message("starting duel...", ephemeral=True)

        if sourceUser.credits < duel.stakes:
            expireDuel()
            await sourceUser.tryNotifyTwo(targetUser, self.bot, True, False, f":white_check_mark: **{{meMention}}* accepted **{{otherMention}}'s** duel challenge, but {{otherMention}} does not have enough credits! ({duel.stakes})\nThis challenge has now expired.")
            return

        if targetUser.credits < duel.stakes:
            expireDuel()
            await targetUser.tryNotifyTwo(sourceUser, self.bot, True, False, f":white_check_mark: **{{meMention}}* accepted **{{otherMention}}'s** duel challenge, but {{otherMention}} does not have enough credits! ({duel.stakes})\nThis challenge has now expired.")
            return

        await fightDuel(interaction, sourceDcUser, interaction.user, duel)


    async def handleRejectDuel(self, interaction: Interaction, sourceUserId: int, isMenu: bool):
        if not (self.bot.usersDB.idExists(sourceUserId) and self.bot.usersDB.idExists(interaction.user.id)):
            if sourceDcUser := self.bot.get_user(sourceUserId):                
                await interaction.response.send_message(f":x: **{sourceDcUser}** has not sent you a duel challenge! If they have sent you one in the past, it may have expired.", ephemeral=True)
            else:
                await interaction.response.send_message(":x: I can't find the user that issued this duel, they may have deleted their account.", ephemeral=True)
            if isMenu:
                await interaction.edit_original_response(view=None)
            return

        sourceUser = self.bot.usersDB.getUser(sourceUserId)
        targetUser = self.bot.usersDB.getUser(interaction.user.id)
        
        if not sourceUser.hasDuelChallengeFor(targetUser):
            await interaction.response.send_message(":x: This duel challenge has expired.", ephemeral=True)
            if isMenu:
                await interaction.edit_original_response(view=None)
            return

        duel = sourceUser.duelRequests[targetUser]
        if duel.duelTimeoutTask is not None:
            duel.duelTimeoutTask.forceExpire(callExpiryFunc=False)

        sourceUser.removeDuelChallengeTarget(targetUser)
        if isMenu:
            await interaction.response.edit_message(view=None)
        else:
            sourceDcUser = self.bot.get_user(sourceUserId)
            username = "<unknown user>" if sourceDcUser is None else str(sourceDcUser)
            await interaction.response.send_message(f":white_check_mark: You have rejected **{username}**'s duel challenge.", ephemeral=True)
            
        await sourceUser.tryNotifyTwo(targetUser, self.bot, True, False, ":white_check_mark: **{meMention}* has rejected **{otherMention}'s** duel challenge.")

#endregion
#region static components

    @BasedCog.staticComponentCallback(StaticComponents.User_DuelChallenge_Reject)
    async def rejectDuelComponent(self, interaction: Interaction, args: str):
        sourceUserId, targetUserId = unpackDuelChallengeMenuArgs(args)
        if not self.CommonStaticComponentsCog.ensureOwnership(interaction, targetUserId): return

        await self.handleRejectDuel(interaction, sourceUserId, True)


    @BasedCog.staticComponentCallback(StaticComponents.User_DuelChallenge_Accept)
    async def acceptDuelComponent(self, interaction: Interaction, args: str):
        sourceUserId, targetUserId = unpackDuelChallengeMenuArgs(args)
        if not self.CommonStaticComponentsCog.ensureOwnership(interaction, targetUserId): return

        await self.handleAcceptDuel(interaction, sourceUserId, True)


#endregion

    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="duels",
                                formattedDesc="Challenge another player to a duel!\n"
                                            + "The loser pays `stakes` credits to the winner.\n"
                                            + "If there are no `stakes`, then no credits will be paid.")
    @app_commands.describe(
        target="The user to challenge.",
        target_id="The id of the user to challenge. Useful if they are in another server.",
        stakes="The number of credits the loser must pay the winner. Can be 0."
    )
    @app_commands.command(name="duel-challenge", description="Challenge another player to a duel!")
    async def cmd_duel_send_challenge(self, interaction: Interaction, target: Optional[Union[User, Member]] = None, target_id: Optional[str] = None, stakes: app_commands.Range[int, 0] = 0):
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
        target = await self.getDuelChallengeTarget(interaction, target, target_id)
        if target is None: return

        sourceBBUser = self.bot.usersDB.getOrAddID(interaction.user.id)
        targetBBUser = self.bot.usersDB.getOrAddID(target.id)

        if sourceBBUser.hasDuelChallengeFor(targetBBUser):
            await interaction.response.send_message(":x: You already have a duel challenge pending for " \
                                                    + memberDisplayNameOrUserNameAndDiscrim(target, interaction.guild) \
                                                    + "! To make a new one, cancel it first. (see `/help duel`)",
                                                    ephemeral=True)
            return

        newDuelReq = DuelRequest(sourceBBUser, targetBBUser, stakes, None)
        duelTT = TimedTask(expiryDelta=cfg.timeouts.duelRequest,
                            expiryFunction=expireAndAnnounceDuelReq,
                            expiryFunctionArgs=(self.bot, newDuelReq))
        newDuelReq.duelTimeoutTask = duelTT
        botState.client.taskScheduler.scheduleTask(duelTT)
        sourceBBUser.addDuelChallenge(newDuelReq)

        view = View()
        acceptButton = Button(style=ButtonStyle.green, label="accept")
        acceptButton = StaticComponents.User_DuelChallenge_Accept(acceptButton)
        view.add_item(acceptButton)

        rejectButton = Button(style=ButtonStyle.red, label="reject")
        rejectButton = StaticComponents.User_DuelChallenge_Reject(rejectButton)
        view.add_item(rejectButton)

        expiryTs = timestamp(duelTT.expiryTime, TimeStampStyle.LongDateTime)

        try:
            msgShared, _, targetMsg = \
                await sourceBBUser.tryNotifyTwo(targetBBUser, self.bot,
                                                targetBBUser.isAlertedForStatefulType(userAlerts.UA_Duels_Challenge_Incoming_New),
                                                True,
                                                ":crossed_swords: **{meMention}** challenged {otherMention}" \
                                                    + f" to duel for **{stakes} Credits!**\n" \
                                                    + f"Respond with `/accept-duel` or `/reject-duel`!\n" \
                                                    + f"This duel request will expire: **{expiryTs}** UTC.")
        except IndexError:
            await interaction.response.send_message(":x: I can't DM you! Please enable DMs from users who are not friends.")
            sourceBBUser.removeDuelChallengeObj(newDuelReq)
            duelTT.forceExpire(callExpiryFunc=False)
            return
        
        if not msgShared and targetMsg is None:
            await interaction.response.send_message(f"Duel chalenge created! I was unable to tell {target} that you've sent it, so contact them if you can!", ephemeral=True)
        else:
            await interaction.response.send_message("Duel challenge sent!", ephemeral=True)


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="duels")
    @app_commands.describe(
        target="The user that you challenged.",
        target_id="The id of the user who was challenged. Useful if they are in another server.",
    )
    @app_commands.command(name="duel-cancel", description="Cancel an active duel challenge")
    async def cmd_duel_cancel_challenge(self, interaction: Interaction, target: Optional[Union[User, Member]] = None, target_id: Optional[str] = None):
        target = await self.getDuelChallengeTarget(interaction, target, target_id)
        if target is None: return
        
        if not self.bot.usersDB.idExists(target.id) or not self.bot.usersDB.idExists(interaction.user.id):
            await interaction.response.send_message(":x: You have not sent any duel challenges! See `/duel-challenge`.", ephemeral=True)
            return

        sourceBBUser = self.bot.usersDB.getUser(interaction.user.id)
        targetBBUser = self.bot.usersDB.getUser(target.id)

        if not sourceBBUser.hasDuelChallengeFor(targetBBUser):
            await interaction.response.send_message(":x: You do not have an active duel challenge for this user! If you have sent one before, it may have expired.", ephemeral=True)
            return
        
        duelReq = sourceBBUser.duelRequests[targetBBUser]
        if duelReq.duelTimeoutTask is not None:
            duelReq.duelTimeoutTask.forceExpire(callExpiryFunc=False)
        sourceBBUser.removeDuelChallengeTarget(targetBBUser)
        
        if sourceBBUser.findSharedGuildWithPlayChannel(self.bot, targetBBUser) is None:
            await interaction.response.send_message(f":white_check_mark: You have cancelled your duel challenge for **{target}**.", ephemeral=True)
            notification = f"{target.mention}, " if targetBBUser.isAlertedForStatefulType(userAlerts.UA_Duels_Challenge_Incoming_Cancel) else ""
            await targetBBUser.individualNotify(self.bot, f":x: {notification}**{interaction.user}** has cancelled their duel challenge.")
        else:
            notification = target.mention if targetBBUser.isAlertedForStatefulType(userAlerts.UA_Duels_Challenge_Incoming_Cancel) else str(target)
            await interaction.response.send_message(f":white_check_mark: {interaction.user.mention} has cancelled their duel challenge for **{notification}**.")


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="duels")
    @app_commands.describe(
        challenger="The user that challenged you.",
        challenger_id="The id of the user who challenged you. Useful if they are in another server.",
    )
    @app_commands.command(name="duel-reject", description="Reject someone's duel challenge")
    async def cmd_duel_reject_challenge(self, interaction: Interaction, challenger: Optional[Union[User, Member]] = None, challenger_id: Optional[str] = None):
        challenger = await self.getDuelChallengeTarget(interaction, challenger, challenger_id)
        if challenger is None: return
        
        await self.handleRejectDuel(interaction, challenger.id, False)


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="duels")
    @app_commands.describe(
        challenger="The user that challenged you.",
        challenger_id="The id of the user who challenged you. Useful if they are in another server.",
    )
    @app_commands.command(name="duel-accept", description="Accept someone's duel challenge")
    async def cmd_duel_accept_challenge(self, interaction: Interaction, challenger: Optional[Union[User, Member]] = None, challenger_id: Optional[str] = None):
        challenger = await self.getDuelChallengeTarget(interaction, challenger, challenger_id)
        if challenger is None: return
        
        await self.handleAcceptDuel(interaction, challenger.id, False)


async def setup(bot: client.BasedClient):
    await bot.add_cog(UserDuelsCog(bot))
