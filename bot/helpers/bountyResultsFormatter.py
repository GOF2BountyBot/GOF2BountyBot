from typing import Any, Dict, Union

from discord import Embed
from discord.utils import utcnow

from ..entities.bounties.routeChecking import RewardsMeta
from ..entities.bounties.bounty import AnyBounty
from ..entities.bounties.criminal import AnyCriminal
from ..lib.stringUtil import commaSplitNum
from ..lib.timeUtil import formatTimeDelta
from ..cfg import cfg

class BountyResultsFormatter:
    @classmethod
    def formatRewardByMeta(cls, reward: str, units: str, flags: RewardsMeta) -> str:
        """Format the value of a checking reward according to meta flags, if any

        :param reward: The reward to format (e.g an amount of credits)
        :type reward: str
        :param str units: The units of the reward, e.g xp/credits/etc
        :param flags: bounty.RewardMeta flags
        :type flags: int
        :return: reward, with any extra formatting added to represent flags
        :rtype: str
        """
        out = f"{reward} {units}"
        if RewardsMeta.USER_PRESTIGED & flags:
            out = f"~~{out}~~"
        return out


    @classmethod
    def bountyResultsFieldKwargs(cls, place: int, userID: int, userRewards: Dict[str, Union[int, bool]], userMeta: RewardsMeta) -> Dict[str, Any]:
        """Build kwargs to create a new field, representing a user's contributions to solving a bounty
        """
        creditsGained = commaSplitNum(userRewards["reward"])
        systemsChecked = userRewards["checked"]
        xpGained = "+" + commaSplitNum(userRewards["xp"])
        winner = userRewards["won"]

        kwargs: Dict[str, Union[str, Any]] = dict(
            name=f"{place}. {'🏆' if winner else ''} {cls.formatRewardByMeta(creditsGained, 'credits', userMeta)}:",
            value=f"<@{userID}> checked {systemsChecked}" \
                + f" system{'s' if int(systemsChecked) != 1 else ''}",
            inline=False
        )

        if RewardsMeta.USER_PRESTIGED & userMeta:
            kwargs["value"] += "\n(user prestiged - credits shared out)"
        else:
            kwargs["value"] += f"\n*{cls.formatRewardByMeta(xpGained, 'xp', userMeta)}*"

        return kwargs


    @classmethod
    def makeBountyExpiredEmbed(cls, bounty: AnyBounty, criminal: AnyCriminal) -> Embed:
        """Build an embed representing the expiry of a bounty.
        The bounty's expiry time is assumed to be now.

        :param b: The bounty that has expired
        :type b: bounty.Bounty
        :return: An embed detailing the expiry of the bounty
        :rtype: Embed
        """
        e = Embed()
        e.set_author(name="Bounty Expired", icon_url=criminal.iconUrl)
        e.description = f"**{criminal.name}**\nOut of time! The bounty has expired."
        e.colour = cfg.factionColourOrDefault(bounty.faction)
        activeTime = utcnow() - bounty.issueTime
        e.set_footer(text=f"Active time: {formatTimeDelta(activeTime)}")
        return e
