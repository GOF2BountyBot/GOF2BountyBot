from ... import lib, botState, client
from ...cfg import cfg
from discord import Embed, Interaction, Member, User, DiscordException, HTTPException, NotFound, File
from discord.utils import MISSING
from ...users import basedUser
from ...scheduling import timedTask
from ..items.ships import shipItem
from ..bounties import criminal
import random
from typing import Optional, Tuple, Union
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageOps
import aiohttp
import textwrap
from dataclasses import dataclass, field

@dataclass
class FightStats:
    rawHP: int
    variedHP: int
    rawDPS: float
    variedDPS: float
    secondsAlive: float
    dead: bool

    @property
    def TimeAliveStr(self) -> str:
        return f"{round(self.secondsAlive, 2)}s" if self.dead else "still alive"


@dataclass
class FightResults:
    initiatorShip: shipItem.Ship
    receiverShip: shipItem.Ship
    winnerShip: Optional[shipItem.Ship] = None
    initiatorStats: FightStats = field(default_factory = lambda: FightStats(0, 0, 0, 0, -1, True))
    receiverStats: FightStats = field(default_factory = lambda: FightStats(0, 0, 0, 0, -1, True))

    def shipStats(self, ship: shipItem.Ship) -> FightStats:
        if ship is self.initiatorShip: return self.initiatorStats
        elif ship is self.receiverShip: return self.receiverStats
        raise KeyError(f"Ship {ship.name} was not in this duel")


def makeDuelStatsEmbed(duelResults: FightResults, targetUser: Union[User, Member, criminal.Criminal], sourceUser: Union[User, Member]) -> Embed:
    """Build a discord.Embed displaying the statistics of a completed duel.

    :param dict duelResults: A dictionary describing the results of the duel
                                TODO: This is to be changed to a data class, or a ShipFight
    :param BasedUser targetUser: The BasedUser that the duel challenged was directed at
    :param BasedUser sourceUser: The BasedUser that issued the challenge
    :return: A discord.Embed displaying the information described in duelResults
    :rtype: discord.Embed
    """
    targetStr = targetUser.name if isinstance(targetUser, criminal.Criminal) else targetUser.mention
    statsEmbed = Embed()
    
    statsEmbed.add_field(name=f"DPS ({cfg.duelVariancePercent * 100}% RNG)",
                        value=f"{sourceUser.mention}: {round(duelResults.initiatorStats.variedDPS, 2)}\n" \
                            + f"{targetStr         }: {round(duelResults.receiverStats.variedDPS, 2)}")
    statsEmbed.add_field(name=f"Health ({cfg.duelVariancePercent * 100}% RNG)",
                        value=f"{sourceUser.mention}: {round(duelResults.initiatorStats.variedDPS, 2)}\n" \
                            + f"{targetStr         }: {round(duelResults.initiatorStats.variedDPS, 2)}")
    statsEmbed.add_field(name="Time Alive",
                        value=f"{sourceUser.mention}: {duelResults.initiatorStats.TimeAliveStr}\n" \
                            + f"{targetStr         }: {duelResults.receiverStats.TimeAliveStr}")

    return statsEmbed


class DuelRequest:
    """A duel challenge for stakes credits, issued by sourceBasedUser to targetBasedUser in sourceBasedGuild,
    and expiring with duelTimeoutTask.

    :var sourceBasedUser: The BasedUser that issued this challenge
    :vartype sourceBasedUser: BasedUser
    :var targetBasedUser: The BasedUser that this challenge was targetted towards
    :vartype targetBasedUser: BasedUser
    :var stakes: The amount of credits to award the winner of the duel, and take from the loser
    :vartype stakes: int
    :var duelTimeoutTask: The TimedTask responsible for expiring this duel challenge
    :vartype duelTimeoutTask: TimedTask
    :var sourceBasedGuild: The BasedGuild in which this challenge was issued
    :vartype sourceBasedGuild: BasedGuild
    :var menus: A list of ReactionDuelChallengeMenu, each of which may trigger, or be removed by, the expiry or completion
                of this duel request
    :vartype menus: ReactionDuelChallengeMenu
    """
    def __init__(self, sourceBasedUser: basedUser.BasedUser, targetBasedUser: basedUser.BasedUser, stakes: int,
                    duelTimeoutTask: Optional[timedTask.TimedTask]):
        """
        :param BasedUser sourceBasedUser: -- The BasedUser who issued the duel challenge
        :param BasedUser targetBasedUser: -- The BasedUser to accept/reject the challenge
        :param int stakes: -- The amount of credits to move from the winner to the loser
        :param TimedTask duelTimeoutTask: -- the TimedTask responsible for expiring this challenge
        """
        self.sourceBasedUser = sourceBasedUser
        self.targetBasedUser = targetBasedUser
        self.stakes = stakes
        self.duelTimeoutTask = duelTimeoutTask
        self.menus = []


# ⚠⚠⚠ THIS FUNCTION IS MARKED FOR CHANGE
def fightShips(initiatorShip: shipItem.Ship, receiverShip: shipItem.Ship, variancePercent: float) -> FightResults:
    """Simulate a duel between two ships.
    Returns a dictionary containing statistics about the duel, as well as a reference to the winning ship.

    :param Ship initiatorShip: The ship that initiated this fight
    :param Ship receiverShip: The ship that accepted the duel request
    :param float variancePercent: The amount of random variance to apply to ship statistics, as a float percentage
                                    (e.g 0.5 for 50% random variance)
    :return: Statistics about the duel, as well as a reference to the winning ship.
    :rtype: dict
    """
    fightResults = FightResults(initiatorShip, receiverShip)
    # Fetch ship total healths
    fightResults.initiatorStats.rawHP = initiatorHP = initiatorShip.getArmour() + initiatorShip.getShield()
    fightResults.receiverStats.rawHP = receiverHP = receiverShip.getArmour() + receiverShip.getShield()

    # Vary healths by +=variancePercent
    initiatorHPVariance = initiatorHP * variancePercent
    receiverHPVariance = receiverHP * variancePercent
    fightResults.initiatorStats.variedHP = initiatorHPVaried = random.randint(int(initiatorHP - initiatorHPVariance), int(initiatorHP + initiatorHPVariance))
    fightResults.receiverStats.variedHP = receiverHPVaried = random.randint(int(receiverHP - receiverHPVariance), int(receiverHP + receiverHPVariance))

    # Fetch ship total DPSs
    fightResults.initiatorStats.rawDPS = initiatorDPS = initiatorShip.getDPS()
    fightResults.receiverStats.rawDPS = receiverDPS = receiverShip.getDPS()

    # Vary DPSs by +-variancePercent
    initiatorDPSVariance = initiatorDPS * variancePercent
    receiverDPSVariance = receiverDPS * variancePercent
    fightResults.initiatorStats.variedDPS = initiatorDPSVaried = random.randint(int(initiatorDPS - initiatorDPSVariance), int(initiatorDPS + initiatorDPSVariance))
    fightResults.receiverStats.variedDPS = receiverDPSVaried = random.randint(int(receiverDPS - receiverDPSVariance), int(receiverDPS + receiverDPSVariance))

    # Handling to be implemented
    # ship1Handling = ship1.getHandling()
    # ship2Handling = ship2.getHandling()
    # ship1HandlingPenalty =

    # Handle ships that have no DPS
    if 0 in (initiatorDPS, receiverDPS):
        if receiverDPS != 0:
            fightResults.winnerShip = receiverShip
            fightResults.initiatorStats.secondsAlive = round(initiatorHPVaried / receiverDPSVaried, 2)
            fightResults.receiverStats.secondsAlive = -1
            fightResults.receiverStats.dead = False
        elif initiatorDPS != 0:
            fightResults.winnerShip = initiatorShip
            fightResults.initiatorStats.secondsAlive = -1
            fightResults.initiatorStats.dead = False
            fightResults.receiverStats.secondsAlive = round(receiverHPVaried / initiatorDPSVaried, 2)
        else:
            fightResults.winnerShip = None
            fightResults.initiatorStats.secondsAlive = -1
            fightResults.initiatorStats.dead = False
            fightResults.receiverStats.secondsAlive = -1
            fightResults.receiverStats.dead = False
        return fightResults

    # Calculate ship TTKs
    fightResults.initiatorStats.secondsAlive = initiatorTTK = initiatorHPVaried / receiverDPSVaried
    fightResults.receiverStats.secondsAlive = receiverTTK = receiverHPVaried / initiatorDPSVaried

    # Return the ship with the longest TTK as the winner
    if initiatorTTK > receiverTTK:
        fightResults.winnerShip = initiatorShip
    elif receiverTTK > initiatorTTK:
        fightResults.winnerShip = receiverShip
    else:
        fightResults.winnerShip = None

    return fightResults


async def buildDuelResultsImage(player1: Union[basedUser.BasedUser, criminal.Criminal],
                                ship1: shipItem.Ship,
                                player2: Union[basedUser.BasedUser, criminal.Criminal],
                                ship2: shipItem.Ship,
                                duelResults: FightResults) -> Image.Image:
    """
    
    :raise RuntimeError: When failing to fetch the profile image of one of the players
    """
    canvas = Image.new("RGBA", cfg.duelResultsImageDims, (0, 0, 0, 0))
    
    # Load font
    nameFont = ImageFont.truetype(str(cfg.paths.duelResultsFont), cfg.duelResultsNameFontSize)
    statsFont = ImageFont.truetype(str(cfg.paths.duelResultsFont), cfg.duelResultsStatsFontSize)

    params = ((player1, ship1, cfg.duelResultsP1Pos, cfg.duelResultsP1StatsPos, cfg.duelResultsP1ShipPos),
              (player2, ship2, cfg.duelResultsP2Pos, cfg.duelResultsP2StatsPos, cfg.duelResultsP2ShipPos))
    for player, ship, iconPos, statsPos, shipPos in params:
        if isinstance(player, basedUser.BasedUser):
            dcUser = botState.client.get_user(player.id) or await botState.client.tryFetchUser(player.id)
            if dcUser is None:
                raise ValueError(f"Failed to find discord User for BasedUser {player}")

            try:
                profileSize = next(2**i for i in range(4,11) if 2**i >= cfg.duelResultsPlayerWidth)
            except StopIteration:
                profileSize = 1024
            icon = BytesIO()

            try:
                await (dcUser.display_avatar.with_size(profileSize)).save(icon, seek_begin=True)
            except (DiscordException, HTTPException, NotFound) as e:
                botState.client.logger.log("duelRequest", "buildDuelResultsImage",
                                    f"Failed to fetch profile image for user {player}: {e}", exception=e)
                raise RuntimeError(f"Failed to fetch profile image for user {player}")
            except Exception as e:
                raise e

            name = str(dcUser)
        else:
            async with botState.client.httpClient.get(player.icon) as resp:
                try:
                    resp.raise_for_status()
                except aiohttp.ClientResponseError as e:
                    botState.client.logger.log("duelRequest", "buildDuelResultsImage",
                                    f"Failed to fetch profile image for criminal {player}: {e}", exception=e)
                    raise RuntimeError(f"Failed to fetch profile image for criminal {player}")
                if not resp.content_type.startswith("image"):
                    errStr = f"Criminal '{player.name}' icon url does not point to an image, " \
                            + f"it points to a {resp.content_type}"
                    botState.client.logger.log("duelRequest", "buildDuelResultsImage", errStr)
                    raise RuntimeError(errStr)

                icon = BytesIO(await resp.read())

            name = player.name.title()
            
        # icon = lib.graphics.cropAndScale(Image.open(icon), cfg.duelResultsPlayerWidth, cfg.duelResultsPlayerWidth).convert("RGBA")
        icon = lib.graphics.paddedScale(Image.open(icon), cfg.duelResultsPlayerWidth, cfg.duelResultsPlayerWidth,
                                        (0, 0, 0, 0), "CENTRE", newMode="RGBA")
        # canvas = Image.composite().paste(icon, iconPos, icon)
        icon = lib.graphics.padImage(icon, iconPos[1], canvas.width - (iconPos[0]+cfg.duelResultsPlayerWidth),
                                        canvas.height - (iconPos[1]+cfg.duelResultsPlayerWidth), iconPos[0], (0, 0, 0, 0))
        canvas = Image.composite(icon, canvas, icon)

        if ship.hasIcon:
            async with botState.client.httpClient.get(ship.icon) as resp:
                try:
                    resp.raise_for_status()
                except aiohttp.ClientResponseError as e:
                    botState.client.logger.log("duelRequest", "buildDuelResultsImage",
                                    f"Failed to fetch ship icon for ship {ship.name}: {e}", exception=e)
                    raise RuntimeError(f"Failed to fetch ship icon for ship {ship.name}")
                if not resp.content_type.startswith("image"):
                    errStr = f"Ship '{ship.name}' icon url does not point to an image, " \
                            + f"it points to a {resp.content_type}"
                    botState.client.logger.log("duelRequest", "buildDuelResultsImage", errStr)
                    raise RuntimeError(errStr)

                shipIcon = lib.graphics.paddedScale(Image.open(BytesIO(await resp.read())),
                                                    cfg.duelResultsShipDims[0], cfg.duelResultsShipDims[1],
                                                    (0, 0, 0, 0))
                if ship is ship1:
                    shipIcon = ImageOps.mirror(shipIcon)
                canvas.paste(shipIcon, shipPos, shipIcon)

        draw: ImageDraw.ImageDraw = ImageDraw.Draw(canvas)
        currentHeight = statsPos[1]
        if len(name) <= cfg.duelResultsMaxNameWidth:
            draw.text(statsPos, name, cfg.duelResultsNameFontColour, font=nameFont)
            currentHeight += nameFont.getsize(name)[1] + cfg.duelResultsTextLinePadding
        else:
            pxPerLine = nameFont.getsize(name)[1] + cfg.duelResultsTextLinePadding
            for line in textwrap.wrap(name, cfg.duelResultsMaxNameWidth):
                draw.text((statsPos[0], currentHeight), line, cfg.duelResultsNameFontColour, font=nameFont)
                currentHeight += pxPerLine

        def drawStat(attStr, currentHeight) -> int:
            if len(attStr) <= cfg.duelResultsMaxStatsWidth:
                draw.text((statsPos[0], currentHeight), attStr, cfg.duelResultsStatsFontColour, font=statsFont)
                currentHeight += statsFont.getsize(attStr)[1] + cfg.duelResultsTextLinePadding
            else:
                pxPerLine = statsFont.getsize(attStr)[1] + cfg.duelResultsTextLinePadding
                for line in textwrap.wrap(attStr, cfg.duelResultsMaxStatsWidth):
                    draw.text((statsPos[0], currentHeight), line, cfg.duelResultsStatsFontColour, font=statsFont)
                    currentHeight += pxPerLine
            return currentHeight

        shipStats = duelResults.shipStats(ship)
        currentHeight = drawStat(f"Total HP: {int(shipStats.variedHP)}", currentHeight)
        currentHeight = drawStat(f"Total Damage/s: {shipStats.variedDPS}", currentHeight)
        currentHeight = drawStat(f"Time alive: {shipStats.secondsAlive:.2f}s", currentHeight)
            
            
    if cfg.duelResultsShadowOpacity:
        canvas = lib.graphics.dropShadow(canvas, cfg.duelResultsShadowOpacity, cfg.duelResultsShadowOffset, cfg.duelResultsBlurIterations)

    if cfg.paths.duelResultsOverlay:
        overlay = lib.graphics.copyDuelResultsOverlay()
        canvas = Image.composite(overlay, canvas, overlay)

    if duelResults.winnerShip is None:
        winnerOverlay = lib.graphics.copyDuelWinnerOverlay("draw")
    elif duelResults.winnerShip is ship1:
        winnerOverlay = lib.graphics.copyDuelWinnerOverlay("left")
    else:
        winnerOverlay = lib.graphics.copyDuelWinnerOverlay("right")
        
    canvas = Image.composite(winnerOverlay, canvas, winnerOverlay)

    if cfg.paths.duelResultsBackgrounds:
        canvas = Image.composite(canvas, lib.graphics.copyRandomDuelResultsBackground(), canvas)
    return canvas


# ⚠⚠⚠ THIS FUNCTION IS MARKED FOR CHANGE
async def fightDuel(interaction: Interaction, sourceUser: User, targetUser: Union[User, Member], duelReq: DuelRequest) -> FightResults:
    """Simulate a duel between two users.
    Returns a dictionary containing statistics about the duel, as well as references to the winning and losing BasedUsers.

    :param BasedUser sourceUser: The BasedUser that issued this challenge
    :param BasedUser targetUser: The BasedUser that this challenge was targetted towards
    :param DuelRequest duelReq: The duel request that this duel simulation satisfies
    :return: statistics about the duel, as well as references to the winning and losing BasedUsers
    :rtype: dict
    """
    if not isinstance(interaction.client, client.BasedClient):
        raise TypeError("fightDuel can only handle interactions handled by a BasedClient")

    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=False, thinking=True)

    for menu in duelReq.menus:
        await menu.delete()

    sourceBasedUser = duelReq.targetBasedUser
    targetBasedUser = duelReq.sourceBasedUser

    # fight = ShipFight.ShipFight(sourceBasedUser.activeShip, targetBasedUser.activeShip)
    # duelResults = fight.fightShips(cfg.duelVariancePercent)
    duelResults = fightShips(sourceBasedUser.activeShip, targetBasedUser.activeShip, cfg.duelVariancePercent)
    winningShip = duelResults.winnerShip

    if winningShip is sourceBasedUser.activeShip:
        winningBasedUser = sourceBasedUser
        winningDcUser = sourceUser
        losingBasedUser = targetBasedUser
        losingDcUser = targetUser
    elif winningShip is targetBasedUser.activeShip:
        winningBasedUser = targetBasedUser
        winningDcUser = targetUser
        losingBasedUser = sourceBasedUser
        losingDcUser = sourceUser
    else:
        winningBasedUser = None
        winningDcUser = None
        losingBasedUser = None
        losingDcUser = None

    try:
        duelResultsImg = await buildDuelResultsImage(sourceBasedUser, sourceBasedUser.activeShip,
                                                    targetBasedUser, targetBasedUser.activeShip,
                                                    duelResults)
    except RuntimeError:
        statsEmbed = makeDuelStatsEmbed(duelResults, sourceUser, targetUser)
        statsEmbed.set_author(name="Duel Stats")
        statsEmbed.set_footer(text="An unexpected error occurred when building your duel results image. The error has been logged.")
        duelResultsImg = None
        duelResultsFile = None
    else:
        statsEmbed = lib.discordUtil.makeEmbed("Duel Results")
        statsEmbed.set_image(url="attachment://duelResults.png")
        duelResultsBytes = BytesIO()
        duelResultsImg.save(duelResultsBytes, "PNG")
        duelResultsBytes.seek(0)
        duelResultsFile = File(duelResultsBytes, filename="duelResults.png")

    # battleMsg =

    # winningBasedUser = sourceBasedUser if winningShip is sourceBasedUser.activeShip else \
    #                     (targetBasedUser if winningShip is targetBasedUser.activeShip else None)
    # losingBasedUser = None if winningBasedUser is None else \
    #                     (sourceBasedUser if winningBasedUser is targetBasedUser else targetBasedUser)

    if winningBasedUser is None:
        await sourceBasedUser.tryNotifyTwo(targetBasedUser, interaction.client, True, False,
                                            ":crossed_swords: **Stalemate!** {otherMention} and {meMention} drew in a duel!",
                                            embed=statsEmbed, file=duelResultsFile or MISSING)
        
    else:
        if losingBasedUser is None or winningDcUser is None or losingDcUser is None:
            raise RuntimeError("Bug! If one of winningBasedUser and losingBasedUser is None, they must both be None.")
        winningBasedUser.duelWins += 1
        losingBasedUser.duelLosses += 1
        winningBasedUser.duelCreditsWins += duelReq.stakes
        losingBasedUser.duelCreditsLosses += duelReq.stakes

        winningBasedUser.credits += duelReq.stakes
        losingBasedUser.credits -= duelReq.stakes
        creditsMsg = f"The stakes were **{duelReq.stakes}** credit{'s' if duelReq.stakes != 1 else ''}:"

        winnerTemplate = "{meMention}" if winningBasedUser == sourceBasedUser else "{otherMention}"
        loserTemplate = "{otherMention}" if winningBasedUser == sourceBasedUser else "{meMention}"

        # Only display the new player balances if the duel stakes are greater than zero.
        if duelReq.stakes > 0:
            creditsMsg += f".\n**{winningDcUser.name}** now has **{winningBasedUser.credits} credits**.\n**" \
                        + f"{losingDcUser.name}** now has **{losingBasedUser.credits} credits**."

        await sourceBasedUser.tryNotifyTwo(targetBasedUser, interaction.client, True, False,
                                            f":crossed_swords: **Fight!** {winnerTemplate} beat {loserTemplate} in a duel!\n{creditsMsg}",
                                            embed=statsEmbed, file=duelResultsFile or MISSING)
    
    if duelReq.duelTimeoutTask is not None:
        duelReq.duelTimeoutTask.forceExpire(callExpiryFunc=False)
    targetBasedUser.removeDuelChallengeObj(duelReq)

    return duelResults
    # logStr = ""
    # for s in duelResults["battleLog"]:
    #     logStr += s.replace("{PILOT1NAME}",sourceUser.name).replace("{PILOT2NAME}",targetUser.name) + "\n"
    # await acceptMsg.channel.send(logStr)
    

async def expireAndAnnounceDuelReq(args: Tuple["client.BasedClient", DuelRequest]):
    """Foce the expiry of a given DuelRequest. The duel expiry will be announced to the issuing user.
    TODO: Announce duel expiry to target user, if they have the UA.

    :param DuelRequest duelReqDict: The duel request to expire
    """
    client, duelReq = args
    if duelReq.duelTimeoutTask is not None:
        duelReq.duelTimeoutTask.forceExpire(callExpiryFunc=False)
    duelReq.sourceBasedUser.removeDuelChallengeObj(duelReq)

    await duelReq.sourceBasedUser.individualNotify(client, f":stopwatch: {{meMention}}, your duel challenge for **{client.get_user(duelReq.targetBasedUser.id)}** has now expired.")
