from typing import Dict, Optional, Set, Union

from enum import Enum
from dataclasses import dataclass

from ..entities.bounties.bounty import Bounty
from ..lib.sql import getSession
from ..cfg import cfg


class RewardsMeta(Enum):
    """Binary flags representing special cases to apply to giving rewards for checking a bounty's route

    none: no flags
    prestige: user has since prestiged, so they dont get xp and their credits are shared to the other contributor(s)
    """
    NONE = 0b0
    USER_PRESTIGED = 0b1

    def __and__(self, other: Union[int, "RewardsMeta"]):
        if isinstance(other, RewardsMeta):
            return self.value & other.value
        else:
            return self.value & other

    
    def __or__(self, other: Union[int, "RewardsMeta"]):
        if isinstance(other, RewardsMeta):
            return self.value | other.value
        else:
            return self.value | other


@dataclass
class BountyUserRewards:
    reward: int
    checked: int
    won: bool
    xp: int


class BountyService():
    def calcRewards(self, bounty: Bounty, classicModeUserIDs: Set[int]) -> Dict[int, BountyUserRewards]:
        """Calculate the winning user and how many credits (and in the future, xp points) to award to which contributing users

        :return: A dictionary of user IDs to rewards. rewards are given as a dict, giving the number of systems checked,
                    the reward credits, and whether this user ID won or not.
        :rtype: dict[int, dict[str, int or bool]]]
        """
        creditsPool = bounty.reward
        rewardPerSys = bounty.rewardPerSys
        rewards: Dict[int, BountyUserRewards] = {}
        checkedSystems = 0
        for system in bounty.route:
            if bounty.systemChecked(system):
                checkedSystems += 1
                if bounty.route[system].checkedByUserId not in rewards:
                    rewards[bounty.route[system].checkedByUserId] = BountyUserRewards(0, 0, False, 0)

        winningUserID = bounty.route[bounty.answerSystemId].checkedByUserId
        if classicModeUserIDs:
            contributors = set(sys.checkedByUserId for sys in bounty.route.values())

            # Winner is classic mode
            if winningUserID in classicModeUserIDs:
                winningUserSystems = [system for system in bounty.route if not bounty.systemChecked(system) \
                                        or bounty.route[system].checkedByUserId == winningUserID]
                rewards[bounty.route[bounty.answerSystemId].checkedByUserId].reward = len(winningUserSystems) * cfg.classic_creditsPerCheck
            
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
            if bounty.systemChecked(system):
                rewards[bounty.route[system].checkedByUserId].checked += 1
                if bounty.route[system].checkedByUserId != winningUserID:
                    # currentReward = int(bounty.reward / len(bounty.route))
                    # currentReward = bbConfig.classic_creditsPerCheck
                    if bounty.route[system].checkedByUserId in classicModeUserIDs:
                        currentReward = cfg.classic_creditsPerCheck
                    else:
                        currentReward = rewardPerSys
                    rewards[bounty.route[system].checkedByUserId].reward += currentReward
                    creditsPool -= currentReward

        if winningUserID not in classicModeUserIDs:
            rewards[bounty.route[bounty.answerSystemId].checkedByUserId].reward = creditsPool
        rewards[bounty.route[bounty.answerSystemId].checkedByUserId].won = True

        for user in rewards:
            rewards[user].xp = int(rewards[user].reward * cfg.bountyRewardToXPGainMult)
        return rewards


    async def escape(self, bounty: Bounty, respawnTT: Optional[TimedTask] = None, dbReload=False):
        """Mark this bounty as escaped, schedule respawning, and register the bounty as escaped in the owning bountyDB.

        :param TimedTask respawnTT: The timedtask responsible for the respawning of the bounty
        :raise ValueError: If the bounty is already marked as escaped
        """
        if bounty.isEscaped:
            raise ValueError(f"Attempted to mark a bounty as escaped that is already escaped: {bounty.criminalId}")

        division = await bounty.division

        if await division.criminalIdExists(bounty.criminalId):
            await division.removeBountyObj(bounty)

        bounty.respawnTime = utcnow() + timedelta(minutes=len(bounty.route))
        bounty.isEscaped = True

        await (await division.guild).bountiesDB.addEscapedBounty(bounty, dbReload=dbReload, ignoreFull=True)


    async def expire(self, bounty: Bounty, dbReload: bool = False):
        """Mark this bounty as expired, and notify both the owning bountyDB and the owning guild in discord.
        
        :param bool dbReload: Give True if this bounty is being expired during bot bootup, False otherwise.
                                This currently toggles whether the passed bounty is checked for existence or not.
                                (Default False)
        :raise ValueError: If the bounty is not currently active, e.g it has already expired
        """
        division = await bounty.division
        bountyBoardChannel = await division.bountyBoardChannel
        if bountyBoardChannel is not None and not bountyBoardChannel.initialized:
            bountyBoardChannel.addPostInitTask(division.announceBountyExpiry(bounty, dbReload=dbReload))
        else:
            await division.announceBountyExpiry(bounty, dbReload=dbReload)
        await bounty._expire(dbReload=dbReload)


    async def _expire(self, bounty: Bounty, dbReload: bool = False, killExpiryTT: bool = True):
        """Mark this bounty as expired, and register the bounty as expired in the owning bountyDB.
        Does not notify the guild in discord.

        :param bool dbReload: Give True if this bounty is being expired during bot bootup, False otherwise.
                                This currently toggles whether the passed bounty is checked for existence or not.
                                (Default False)
        :param bool killExpiryTT: Give True to also expire the bounty's expiryTT, *without* executing the task's
                                expiry function (Default True)
        :raise ValueError: If the bounty is already marked as expired
        """
        session = getSession(bounty)
        query = select(Bounty[Any].id).where(Bounty.id == bounty.id)
        exists = await session.scalar(query) is not None

        if not exists:
            raise ValueError(f"Attempted to mark a bounty as expired that does not exists (may have already expired): {bounty.id} (criminal {bounty.criminalId})")

        division = await bounty.division
        if bounty.isEscaped:
            if await division.escapedCriminalIdExists(bounty.criminalId):
                await division.owningDB.removeEscapedBountyObj(bounty)
        else:
            if bounty.criminal in bounty.division.bounties[bounty.techLevel]:
                bounty.division.owningDB.removeBountyObj(bounty)
        
        if killExpiryTT and bounty.expiryTT is not None and not bounty.expiryTT.isExpired():
            bounty.expiryTT.forceExpire(callExpiryFunc=False)
            bounty.expiryTT = None


    async def _respawn(self, bounty: Bounty):
        if not bounty.isEscapedOld():
            raise ValueError("Attempted to respawn on a bounty that is not awaiting respawn: " + bounty.criminal.name)

        respawnArgs = {"newBounty": bounty,
                        "newConfig": bounty.makeRespawnConfig()}
        await bounty.division.owningDB.owningBasedGuild.spawnAndAnnounceBounty(respawnArgs, isRespawn=True)
        # This is handled by spawnAndAnnounceBounty
        # bounty.division.owningDB.removeEscapedCriminal(bounty.criminal)
        bounty.respawnTT = None

        if bounty.division.bountyBoardChannel is not None:
            await bounty.division.bountyBoardChannel.updateEscapedBountiesMessage()


    def cancelRespawn(self, bounty: Bounty):
        """Cancel the respawning of the bounty, by forcing the expiry of its respawn TimedTask.

        :raise ValueError: If the bounty is not escaped
        """
        if not bounty.isEscapedOld():
            raise ValueError("Attempted to cancelRespawn on a bounty that is not awaiting respawn: " + bounty.criminal.name)
        # Casting here because existence of sef.respawnTT is checked by isEscaped above
        cast(TimedTask, bounty.respawnTT).forceExpire(callExpiryFunc=False)
        bounty.respawnTT = None
        bounty.division.owningDB.removeEscapedCriminal(bounty.criminal)


    def forceRespawn(self, bounty: Bounty):
        """Force the immediate respawning of the bounty, by forcing the expiry of its respawn TimedTask.

        :raise ValueError: If the bounty is not escaped
        """
        if not bounty.isEscapedOld():
            raise ValueError("Attempted to forceRespawn on a bounty that is not awaiting respawn: " + bounty.criminal.name)
        # Casting here because existence of sef.respawnTT is checked by isEscaped above
        cast(TimedTask, bounty.respawnTT).forceExpire(callExpiryFunc=True)


    def makeRespawnConfig(self, bounty: Bounty):
        """Create a new, partially configured, ungenerated BountyConfig object, to be used in the respawning of this bounty.

        :return: A new BountyConfig with the right attributes left ungenerated, to be populated on bounty respawn
        :rtype: BountyConfig
        """
        return BountyConfig(faction=bounty.faction, isPlayer=bounty.criminal.isPlayer, endTime=bounty.endTime,
                            issueTime=bounty.issueTime, activeShip=bounty.activeShip, techLevel=bounty.techLevel)
    

    def respawnReconfigure(self, bounty: Bounty):
        bounty.__init__(bounty, config=bounty.makeRespawnConfig().generate(bounty.division))