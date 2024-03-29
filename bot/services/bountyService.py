from typing import Dict, Set, Union

from enum import Enum
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import select

from discord.utils import utcnow

from ..entities.bounties.bounty import Bounty, AnyBounty
from ..entities.bounties.routeChecking import BountyUserRewards
from ..entities.bounties.bountyConfig import BountyConfigFactory
from ..lib.sql import getSession
from ..cfg import cfg
from . import bountyDivisionService, basedGuildService
from ..repositories import bountyRepository


class BountyService():
    def __init__(self,
                 bountyDivisionService: "bountyDivisionService.BountyDivisionService",
                 bountyRepository: "bountyRepository.BountyRepository",
                 basedGuildService: "basedGuildService.BasedGuildService",
                 bountyConfigFactory: "BountyConfigFactory") -> None:
        self.bountyDivisionService = bountyDivisionService
        self.bountyRepository = bountyRepository
        self.basedGuildService = basedGuildService
        self.bountyConfigFactory = bountyConfigFactory


    def calcRewards(self, bounty: AnyBounty, classicModeUserIDs: Set[int]) -> Dict[int, BountyUserRewards]:
        """Calculate the winning user and how many credits (and in the future, xp points) to award to which contributing users

        :return: A dictionary of user IDs to rewards. rewards are given as a dict, giving the number of systems checked,
                    the reward credits, and whether this user ID won or not.
        :rtype: dict[int, dict[str, int or bool]]]
        """
        winningUserID = bounty.route[bounty.answerSystemId].checkedByUserId
        if winningUserID is None:
            raise ValueError("The bounty has not yet been solved")
        
        creditsPool = bounty.reward
        rewardPerSys = bounty.rewardPerSys
        rewards: Dict[int, BountyUserRewards] = {}
        checkedSystems = 0
        for system in bounty.route:
            checkingUser = bounty.route[system].checkedByUserId
            if checkingUser is not None:
                checkedSystems += 1
                if checkingUser not in rewards:
                    rewards[checkingUser] = BountyUserRewards(0, 0, False, 0)

        if classicModeUserIDs:
            contributors = set(sys.checkedByUserId for sys in bounty.route.values() if sys.checkedByUserId is not None)

            # Winner is classic mode
            if winningUserID in classicModeUserIDs:
                winningUserSystems = [system for system in bounty.route if not bounty.systemChecked(system) \
                                        or bounty.route[system].checkedByUserId == winningUserID]
                rewards[winningUserID].reward = len(winningUserSystems) * cfg.classic_creditsPerCheck
            
            # At least one non-classic mode contributor
            if len(contributors) > 1 and \
                    any(i not in (winningUserID, -1) and i not in classicModeUserIDs for i in contributors):
                classicModeSystems = [system for system in bounty.route if bounty.route[system].checkedByUserId in classicModeUserIDs]
                if winningUserID in classicModeUserIDs:
                    classicModeSystems += [system for system in bounty.route if not bounty.systemChecked(system)]
                classicModePool = len(classicModeSystems) * cfg.classic_creditsPerCheck
                numNonClassicModeSystems = len(bounty.route) - len(classicModeSystems)
                if winningUserID not in classicModeUserIDs:
                    numNonClassicModeSystems += len([system for system in bounty.route if not bounty.systemChecked(system)])
                rewardPerSys = int((creditsPool - classicModePool) / numNonClassicModeSystems)

        for system in bounty.route:
            checkingUser = bounty.route[system].checkedByUserId
            if checkingUser is not None:
                rewards[checkingUser].checked += 1
                if checkingUser != winningUserID:
                    # currentReward = int(bounty.reward / len(bounty.route))
                    # currentReward = bbConfig.classic_creditsPerCheck
                    if checkingUser in classicModeUserIDs:
                        currentReward = cfg.classic_creditsPerCheck
                    else:
                        currentReward = rewardPerSys
                    rewards[checkingUser].reward += currentReward
                    creditsPool -= currentReward

        if winningUserID not in classicModeUserIDs:
            rewards[winningUserID].reward = creditsPool
        rewards[winningUserID].won = True

        for user in rewards:
            rewards[user].xp = int(rewards[user].reward * cfg.bountyRewardToXPGainMult)
        return rewards


    async def escape(self, bounty: AnyBounty, dbReload: bool = False):
        """Mark this bounty as escaped, schedule respawning, and register the bounty as escaped in the owning bountyDB.

        :param TimedTask respawnTT: The timedtask responsible for the respawning of the bounty
        :raise ValueError: If the bounty is already marked as escaped
        """
        if bounty.isEscaped:
            raise ValueError(f"Attempted to mark a bounty as escaped that is already escaped: {bounty.criminalId}")

        division = await bounty.division

        if await self.bountyDivisionService.criminalIdExists(division, bounty.criminalId):
            await self.bountyDivisionService.removeBountyObj(division, bounty)

        bounty.respawnTime = utcnow() + timedelta(minutes=len(bounty.route))
        bounty.isEscaped = True

        await self.bountyRepository.addEscapedBounty(division.guildId, bounty, dbReload=dbReload, ignoreFull=True)


    async def expire(self, bounty: AnyBounty, dbReload: bool = False):
        """Mark this bounty as expired, and notify both the owning bountyDB and the owning guild in discord.
        
        :param bool dbReload: Give True if this bounty is being expired during bot bootup, False otherwise.
                                This currently toggles whether the passed bounty is checked for existence or not.
                                (Default False)
        :raise ValueError: If the bounty is not currently active, e.g it has already expired
        """
        division = await bounty.division
        await self.bountyDivisionService.announceBountyExpiry(division, bounty, dbReload=dbReload)
        
        session = getSession(bounty)
        query = select(AnyBounty.id).where(Bounty.id == bounty.id)
        exists = await session.scalar(query) is not None

        if not exists:
            raise ValueError(f"Attempted to mark a bounty as expired that does not exist (may have already expired): {bounty.id} (criminal {bounty.criminalId})")

        division = await bounty.division
        if bounty.isEscaped:
            if await self.bountyDivisionService.escapedCriminalIdExists(division, bounty.criminalId):
                await self.bountyRepository.removeEscapedBountyObj(division.guildId, bounty)
        else:
            if await self.bountyDivisionService.criminalIdExists(division, bounty.criminalId):
                await self.bountyRepository.removeBountyObj(division.guildId, bounty)


    async def respawn(self, bounty: AnyBounty):
        if not bounty.isEscaped:
            raise ValueError(f"Attempted to respawn on a bounty that is not awaiting respawn: {bounty.criminalId}")

        respawnArgs = {"newBounty": bounty,
                        "newConfig": await self.bountyConfigFactory.getRespawnConfig(bounty)}
        
        guildId = (await bounty.division).guildId
        await self.basedGuildService.spawnAndAnnounceBounty(guildId, respawnArgs, isRespawn=True)
        
        # This is handled by spawnAndAnnounceBounty
        # bounty.division.owningDB.removeEscapedCriminal(bounty.criminal)
        bounty.respawnTT = None

        if bounty.division.bountyBoardChannel is not None:
            await bounty.division.bountyBoardChannel.updateEscapedBountiesMessage()


    def cancelRespawn(self, bounty: AnyBounty):
        """Cancel the respawning of the bounty, by forcing the expiry of its respawn TimedTask.

        :raise ValueError: If the bounty is not escaped
        """
        if not bounty.isEscapedOld():
            raise ValueError("Attempted to cancelRespawn on a bounty that is not awaiting respawn: " + bounty.criminal.name)
        # Casting here because existence of sef.respawnTT is checked by isEscaped above
        cast(TimedTask, bounty.respawnTT).forceExpire(callExpiryFunc=False)
        bounty.respawnTT = None
        bounty.division.owningDB.removeEscapedCriminal(bounty.criminal)


    def forceRespawn(self, bounty: AnyBounty):
        """Force the immediate respawning of the bounty, by forcing the expiry of its respawn TimedTask.

        :raise ValueError: If the bounty is not escaped
        """
        if not bounty.isEscapedOld():
            raise ValueError("Attempted to forceRespawn on a bounty that is not awaiting respawn: " + bounty.criminal.name)
        # Casting here because existence of sef.respawnTT is checked by isEscaped above
        cast(TimedTask, bounty.respawnTT).forceExpire(callExpiryFunc=True)


    async def respawnReconfigure(self, bounty: AnyBounty):
        bounty.__init__(bounty, config=bounty.makeRespawnConfig().generate(bounty.division))