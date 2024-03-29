from typing import Any, ClassVar

from discord import Embed, Colour
from discord.message import MessageReference

from ..cfg import bbData, cfg
from .. import client
from ..lib.discordUtil import ImageFile, ZWSP
from ..lib import graphics, stringUtil
from ..entities.bounties import bounty
from ..entities.bounties import bountyBoardChannel

class BountyBoardListingFormatter:
    STOPWATCH_ICON: ClassVar = 'https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/twitter/259/stopwatch_23f1.png'
    
    NO_BOUNTIES_EMBED: ClassVar = Embed(
        description='> Please check back later, or use the `notify bounties` command to be notified when they spawn!',
        colour=Colour.dark_orange())
    
    NO_BOUNTIES_EMBED.set_author(name='No Bounties Available', icon_url=STOPWATCH_ICON)

    @classmethod
    async def makeBountyEmbed(cls, client: "client.BasedClient", bounty: bounty.AnyBounty) -> Embed:
        """Construct a discord.Embed for listing in a bountyBoardChannel

        :param Bounty bounty: The bounty to describe in this embed
        :return: An Embed describing statistics about the passed bounty
        :rtype: discord.Embed
        """
        crim = await bounty.criminal
        embed = Embed(title=crim.name,
                        colour=cfg.factionColourOrDefault(bounty.faction))
        embed.set_footer(text=f"{bounty.faction.title()}",
                            icon_url=bbData.factionIcons[bounty.faction] if bounty.faction in bbData.factionIcons else "")

        infoStr = f"**Difficulty:** {bounty.techLevel}\n" \
                + f"**Reward Pool:** {stringUtil.commaSplitNum(bounty.reward)} Credits\n" \
                + f"**Bounty Ends:** <t:{int(bounty.endTime.timestamp())}:R>"
        embed.add_field(name=ZWSP, value=infoStr)

        ship = await bounty.ship

        loadoutFieldValue = ""
        if cfg.bbcShowLoadoutEmojis:
            loadoutFieldName = "**Loadout:**"
            weaponsStr = "".join(i.emoji.sendable for i in ship.weapons if i.emoji is not None)
            modulesStr = "".join(i.emoji.sendable for i in ship.modules if i.emoji is not None)
            turretsStr = "".join(i.emoji.sendable for i in ship.turrets if i.emoji is not None)
            
            statsShown = True
            if cfg.bbcShowHpDps:
                totalHp = ship.getArmour() + ship.getShield()
                duelingStatsStr = f" {totalHp} HP // {ship.getDPS()} DPS"
                statsShown = False
            else:
                duelingStatsStr = ""

            if ship.emoji is not None:
                loadoutFieldValue += f"{ship.emoji.sendable}{'' if statsShown else duelingStatsStr}\n"
                statsShown = True
            else:
                duelingStatsStr += "\n"

            if weaponsStr:
                loadoutFieldValue += f"{weaponsStr}{'' if statsShown else duelingStatsStr}\n"
                statsShown = True
            if modulesStr:
                loadoutFieldValue += f"{modulesStr}{'' if statsShown else duelingStatsStr}\n"
                statsShown = True
            if turretsStr:
                loadoutFieldValue += f"{turretsStr}{'' if statsShown else duelingStatsStr}\n"
                statsShown = True
        else:
            loadoutFieldName = "**See the culprit's loadout with:**"
            if cfg.bbcShowHpDps:
                embed.add_field(name="**Dueling stats:**",
                                value=f"Total health: {ship.getArmour() + ship.getShield()}\n" \
                                    + f"Total DPS: {ship.getDPS()}")

        embed.add_field(name=loadoutFieldName, value=f"{loadoutFieldValue}`/loadout criminal {crim.name}`")

        embed.set_thumbnail(url=crim.iconUrl)
        # embed.add_field(name="**Reward Pool:**", value=stringUtil.commaSplitNum(bounty.reward) + " Credits")
        # embed.add_field(name="**Difficulty:**", value=str(bounty.techLevel))

        routeStr = ""
        answerEntry = bounty.route[bounty.answerSystemId]
        for routeEntry in bounty.orderedRoute:
            if routeEntry.isChecked:
                routeStr += "~~"
                if 0 < answerEntry.index - routeEntry.index < cfg.closeBountyThreshold:
                    routeStr += "**" + routeEntry.system.name + "**"
                else:
                    routeStr += routeEntry.system.name
                routeStr += "~~"
            else:
                routeStr += routeEntry.system.name
            routeStr += ", "
        embed.add_field(name="**Route:**", value=routeStr[:-2], inline=False)
        embed.add_field(name="-", value="> ~~Already checked systems~~\n> **Criminal spotted here recently**")
        # embed.add_field(name="Bounty ends:", value=f"<t:{int(bounty.endTime)}:R>")

        if cfg.bbcShowRouteImage:
            routeImage = graphics.renderRouteMap([s.system for s in bounty.orderedRoute])
            if routeImage is not None:
                with ImageFile(routeImage, "route.png") as routeImageFile:
                    routeImageMessage = await client.bountyRouteImagesChannel.send(file=routeImageFile.file)
                embed.set_image(url=routeImageMessage.attachments[0].url)

        return embed


    @classmethod
    async def listingJumpUrl(cls, channel: bountyBoardChannel.BountyBoardChannel[Any], msgId: int) -> str:
        """Construct a jump URL to a message in self.channel

        :param msgId: The ID of the message to construct a URL for
        :type msgId: int
        :return: A jump URL to the identified message
        :rtype: str
        """
        return MessageReference(message_id=msgId, channel_id=channel.channelId,
                                guild_id=(await channel.division).guildId).jump_url
