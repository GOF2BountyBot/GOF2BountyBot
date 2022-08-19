from ... import lib, botState
from ...cfg import cfg
from discord import Embed, Member, User, Message, DiscordException, HTTPException, NotFound, File
from discord.abc import Messageable
from ...users import basedUser
from ...scheduling import timedTask
from ...users import basedGuild
from ..items import shipItem
from ..bounties import criminal
import random
from typing import Dict, Optional, Union, cast
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageOps
import aiohttp
import textwrap


def makeDuelStatsEmbed(duelResults: dict, targetUser: Union[User, Member], sourceUser: Union[User, Member]) -> Embed:
    """Build a discord.Embed displaying the statistics of a completed duel.

    :param dict duelResults: A dictionary describing the results of the duel
                                TODO: This is to be changed to a data class, or a ShipFight
    :param BasedUser targetUser: The BasedUser that the duel challenged was directed at
    :param BasedUser sourceUser: The BasedUser that issued the challenge
    :return: A discord.Embed displaying the information described in duelResults
    :rtype: discord.Embed
    """
    statsEmbed = Embed()
    statsEmbed.set_author(name="Duel Stats")

    statsEmbed.add_field(name="DPS (" + str(cfg.duelVariancePercent * 100) + "% RNG)",
                            value=sourceUser.mention + ": " + str(round(duelResults["ship1"]["DPS"]["varied"], 2)) + "\n" \
                                + targetUser.mention + ": " + str(round(duelResults["ship2"]["DPS"]["varied"], 2)))
    statsEmbed.add_field(name="Health (" + str(cfg.duelVariancePercent * 100) + "% RNG)",
                            value=sourceUser.mention + ": " + str(round(duelResults["ship1"]["health"]["varied"])) + "\n" \
                                + targetUser.mention + ": " + str(round(duelResults["ship2"]["health"]["varied"], 2)))
    statsEmbed.add_field(name="Time To Kill",
                            value=sourceUser.mention + ": " + (str(round(duelResults["ship1"]["TTK"], 2)) \
                                if duelResults["ship1"]["TTK"] != -1 else "inf.") + "s\n" + targetUser.mention + ": " \
                                + (str(round(duelResults["ship2"]["TTK"], 2)) if duelResults["ship2"]["TTK"] != -1 else \
                                    "inf.") + "s")

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
                    duelTimeoutTask: timedTask.TimedTask, sourceBasedGuild: basedGuild.BasedGuild):
        """
        :param BasedUser sourceBasedUser: -- The BasedUser who issued the duel challenge
        :param BasedUser targetBasedUser: -- The BasedUser to accept/reject the challenge
        :param int stakes: -- The amount of credits to move from the winner to the loser
        :param TimedTask duelTimeoutTask: -- the TimedTask responsible for expiring this challenge
        :param BasedGuild sourceBasedGuild: -- The BasedGuild from which the challenge was issued
        """
        self.sourceBasedUser = sourceBasedUser
        self.targetBasedUser = targetBasedUser
        self.stakes = stakes
        self.duelTimeoutTask = duelTimeoutTask
        self.sourceBasedGuild = sourceBasedGuild
        self.menus = []


# ⚠⚠⚠ THIS FUNCTION IS MARKED FOR CHANGE
def fightShips(ship1: shipItem.Ship, ship2: shipItem.Ship, variancePercent: float) -> dict:
    """Simulate a duel between two ships.
    Returns a dictionary containing statistics about the duel, as well as a reference to the winning ship.

    :param shipItem ship1: One of the ships partaking in the duel
    :param shipItem ship2: One of the ships partaking in the duel
    :param float variancePercent: The amount of random variance to apply to ship statistics, as a float percentage
                                    (e.g 0.5 for 50% random variance lll)
    :return: A dictionary containing statistics about the duel, as well as a reference to the winning ship.
    :rtype: dict
    """

    # Fetch ship total healths
    ship1HP = ship1.getArmour() + ship1.getShield()
    ship2HP = ship2.getArmour() + ship2.getShield()

    # Vary healths by +=variancePercent
    ship1HPVariance = ship1HP * variancePercent
    ship2HPVariance = ship2HP * variancePercent
    ship1HPVaried = random.randint(int(ship1HP - ship1HPVariance), int(ship1HP + ship1HPVariance))
    ship2HPVaried = random.randint(int(ship2HP - ship2HPVariance), int(ship2HP + ship2HPVariance))

    # Fetch ship total DPSs
    ship1DPS = ship1.getDPS()
    ship2DPS = ship2.getDPS()

    if ship1DPS == 0:
        if ship2DPS == 0:
            return {"winningShip": None,
            "ship1": {   "health": {"stock": ship1HP, "varied": ship1HP},
                        "DPS": {"stock": ship1DPS, "varied": ship1DPS},
                        "TTK": -1},
            "ship2": {   "health": {"stock": ship2HP, "varied": ship2HP},
                        "DPS": {"stock": ship2DPS, "varied": ship2DPS},
                        "TTK": -1}}
        return {"winningShip": ship2,
            "ship1": {   "health": {"stock": ship1HP, "varied": ship1HP},
                        "DPS": {"stock": ship1DPS, "varied": ship1DPS},
                        "TTK": round(ship1HP / ship2DPS, 2)},
            "ship2": {   "health": {"stock": ship2HP, "varied": ship2HP},
                        "DPS": {"stock": ship2DPS, "varied": ship2DPS},
                        "TTK": -1}}
    if ship2DPS == 0:
        if ship1DPS == 0:
            return {"winningShip": None,
            "ship1": {   "health": {"stock": ship1HP, "varied": ship1HP},
                        "DPS": {"stock": ship1DPS, "varied": ship1DPS},
                        "TTK": -1},
            "ship2": {   "health": {"stock": ship2HP, "varied": ship2HP},
                        "DPS": {"stock": ship2DPS, "varied": ship2DPS},
                        "TTK": -1}}
        return {"winningShip": ship1,
            "ship1": {   "health": {"stock": ship1HP, "varied": ship1HP},
                        "DPS": {"stock": ship1DPS, "varied": ship1DPS},
                        "TTK": -1},
            "ship2": {   "health": {"stock": ship2HP, "varied": ship2HP},
                        "DPS": {"stock": ship2DPS, "varied": ship2DPS},
                        "TTK": round(ship2HP / ship1DPS, 2)}}

    # Vary DPSs by +=variancePercent
    ship1DPSVariance = ship1DPS * variancePercent
    ship2DPSVariance = ship2DPS * variancePercent
    ship1DPSVaried = random.randint(int(ship1DPS - ship1DPSVariance), int(ship1DPS + ship1DPSVariance))
    ship2DPSVaried = random.randint(int(ship2DPS - ship2DPSVariance), int(ship2DPS + ship2DPSVariance))

    # Handling to be implemented
    # ship1Handling = ship1.getHandling()
    # ship2Handling = ship2.getHandling()
    # ship1HandlingPenalty =

    # Calculate ship TTKs
    ship1TTK = ship1HPVaried / ship2DPSVaried
    ship2TTK = ship2HPVaried / ship1DPSVaried

    # Return the ship with the longest TTK as the winner
    if ship1TTK > ship2TTK:
        winningShip = ship1
    elif ship2TTK > ship1TTK:
        winningShip = ship2
    else:
        winningShip = None

    return {"winningShip": winningShip,
            "ship1": {"health": {"stock": ship1HP, "varied": ship1HPVaried},
                    "DPS": {"stock": ship1DPS, "varied": ship1DPSVaried},
                    "TTK": ship1TTK},
            "ship2": {"health": {"stock": ship2HP, "varied": ship2HPVaried},
                    "DPS": {"stock": ship2DPS, "varied": ship2DPSVaried},
                    "TTK": ship2TTK}}


async def buildDuelResultsImage(player1: Union[basedUser.BasedUser, criminal.Criminal],
                                ship1: shipItem.Ship,
                                player2: Union[basedUser.BasedUser, criminal.Criminal],
                                ship2: shipItem.Ship,
                                resultsDict: dict) -> Image.Image:
    """
    
    :raise RuntimeError: When failing to fetch the profile image of one of the players
    """
    canvas = Image.new("RGBA", cfg.duelResultsImageDims, (0, 0, 0, 0))
    
    # Load font
    nameFont = ImageFont.truetype(str(cfg.paths.duelResultsFont), cfg.duelResultsNameFontSize)
    statsFont = ImageFont.truetype(str(cfg.paths.duelResultsFont), cfg.duelResultsStatsFontSize)

    params = ((player1, ship1, cfg.duelResultsP1Pos, cfg.duelResultsP1StatsPos, cfg.duelResultsP1ShipPos, "ship1"),
              (player2, ship2, cfg.duelResultsP2Pos, cfg.duelResultsP2StatsPos, cfg.duelResultsP2ShipPos, "ship2"))
    for player, ship, iconPos, statsPos, shipPos, shipKey in params:
        if isinstance(player, basedUser.BasedUser):
            dcUser: User = botState.client.get_user(player.id) or await botState.client.tryFetchUser(player.id)
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

        for attName, attStats in resultsDict[shipKey].items():
            # {"winningShip": winningShip,
            # "ship1": {"health": {"stock": ship1HP, "varied": ship1HPVaried},
            #         "DPS": {"stock": ship1DPS, "varied": ship1DPSVaried},
            #         "TTK": ship1TTK},
            # "ship2": {"health": {"stock": ship2HP, "varied": ship2HPVaried},
            #         "DPS": {"stock": ship2DPS, "varied": ship2DPSVaried},
            #         "TTK": ship2TTK}}
            if attName == "health":
                attStr = f"Total HP: {int(attStats['varied'])}"
            elif attName == "DPS":
                attStr = f"Total Damage/s: {int(attStats['varied'])}"
            elif attName == "TTK":
                attStr = f"Time alive: {attStats:.2f}s"
            elif type(attStats) == dict and "varied" in attStats:
                attStr = f"{attName.title()}: {int(attStats['varied'])}"
            else:
                attStr = f"{attName.title()}: {int(attStats)}"
            
            if len(attStr) <= cfg.duelResultsMaxStatsWidth:
                draw.text((statsPos[0], currentHeight), attStr, cfg.duelResultsStatsFontColour, font=statsFont)
                currentHeight += statsFont.getsize(attStr)[1] + cfg.duelResultsTextLinePadding
            else:
                pxPerLine = statsFont.getsize(attStr)[1] + cfg.duelResultsTextLinePadding
                for line in textwrap.wrap(attStr, cfg.duelResultsMaxStatsWidth):
                    draw.text((statsPos[0], currentHeight), line, cfg.duelResultsStatsFontColour, font=statsFont)
                    currentHeight += pxPerLine

    if cfg.duelResultsShadowOpacity:
        canvas = lib.graphics.dropShadow(canvas, cfg.duelResultsShadowOpacity, cfg.duelResultsShadowOffset, cfg.duelResultsBlurIterations)

    if cfg.paths.duelResultsOverlay:
        overlay = lib.graphics.copyDuelResultsOverlay()
        canvas = Image.composite(overlay, canvas, overlay)

    if resultsDict["winningShip"] is None:
        winnerOverlay = lib.graphics.copyDuelWinnerOverlay("draw")
    elif resultsDict["winningShip"] is ship1:
        winnerOverlay = lib.graphics.copyDuelWinnerOverlay("left")
    else:
        winnerOverlay = lib.graphics.copyDuelWinnerOverlay("right")
        
    canvas = Image.composite(winnerOverlay, canvas, winnerOverlay)

    if cfg.paths.duelResultsBackgrounds:
        canvas = Image.composite(canvas, lib.graphics.copyRandomDuelResultsBackground(), canvas)
    return canvas


# ⚠⚠⚠ THIS FUNCTION IS MARKED FOR CHANGE
async def fightDuel(sourceUser: User, targetUser: Union[User, Member], duelReq: DuelRequest, acceptMsg: Message) -> dict:
    """Simulate a duel between two users.
    Returns a dictionary containing statistics about the duel, as well as references to the winning and losing BasedUsers.

    :param BasedUser sourceUser: The BasedUser that issued this challenge
    :param BasedUser targetUser: The BasedUser that this challenge was targetted towards
    :param DuelRequest duelReq: The duel request that this duel simulation satisfies
    :param discord.message acceptMsg: The message tha triggered this duel simulation
    :return: A dictionary containing statistics about the duel, as well as references to the winning and losing BasedUsers
    :rtype: dict
    """
    for menu in duelReq.menus:
        await menu.delete()

    sourceBasedUser = duelReq.targetBasedUser
    targetBasedUser = duelReq.sourceBasedUser

    # fight = ShipFight.ShipFight(sourceBasedUser.activeShip, targetBasedUser.activeShip)
    # duelResults = fight.fightShips(cfg.duelVariancePercent)
    duelResults = fightShips(sourceBasedUser.activeShip, targetBasedUser.activeShip, cfg.duelVariancePercent)
    winningShip = duelResults["winningShip"]

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

    async def send(channel: Messageable, msg: str, embed: Embed, duelResultsFile: Optional[File]):
        if duelResultsFile is None:
            return await channel.send(msg, embed=embed)
        else:
            return await channel.send(msg, embed=embed, file=duelResultsFile)

    if acceptMsg.guild is None:
        raise ValueError("fightDuel can only be used from a guild context")

    if winningBasedUser is None:
        await send(acceptMsg.channel, f":crossed_swords: **Stalemate!** {targetUser} and {sourceUser.mention} drew in a duel!",
                    statsEmbed, duelResultsFile)
        
        if acceptMsg.guild.get_member(targetUser.id) is None:
            targetDCGuild = lib.discordUtil.findBUserDCGuild(targetBasedUser)
            if targetDCGuild is not None:
                targetBasedGuild = botState.client.guildsDB.getGuild(targetDCGuild.id)
                if targetBasedGuild.hasPlayChannel():
                    await send(targetBasedGuild.getPlayChannel(),
                                f":crossed_swords: **Stalemate!** {targetUser.mention} " \
                                f"and {sourceUser} drew in a duel!",
                                statsEmbed, duelResultsFile)
        else:
            await send(acceptMsg.channel,
                        f":crossed_swords: **Stalemate!** {targetUser.mention} and {sourceUser.mention} drew in a duel!",
                        statsEmbed, duelResultsFile)
    else:
        if losingBasedUser is None or winningDcUser is None or losingDcUser is None:
            raise RuntimeError("Bug! If one of winningBasedUser and losingBasedUser is None, they must both be None.")
        winningBasedUser.duelWins += 1
        losingBasedUser.duelLosses += 1
        winningBasedUser.duelCreditsWins += duelReq.stakes
        losingBasedUser.duelCreditsLosses += duelReq.stakes

        winningBasedUser.credits += duelReq.stakes
        losingBasedUser.credits -= duelReq.stakes
        creditsMsg = "The stakes were **" \
                        + str(duelReq.stakes) + "** credit" \
                        + ("s" if duelReq.stakes != 1 else "") + ":"

        # Only display the new player balances if the duel stakes are greater than zero.
        if duelReq.stakes > 0:
            creditsMsg += ".\n**" + winningDcUser.name + "** now has **" \
                + str(winningBasedUser.credits) + " credits**.\n**" + losingDcUser.name \
                + "** now has **" + str(losingBasedUser.credits) + " credits**."

        if acceptMsg.guild.get_member(winningBasedUser.id) is None:
            await send(acceptMsg.channel, ":crossed_swords: **Fight!** " + str(winningDcUser) \
                                            + " beat " + losingDcUser.mention \
                                            + " in a duel!\n" + creditsMsg, embed=statsEmbed, duelResultsFile=duelResultsFile)

            winnerDCGuild = lib.discordUtil.findBUserDCGuild(winningBasedUser)
            if winnerDCGuild is not None:
                winnerBasedGuild = botState.client.guildsDB.getGuild(winnerDCGuild.id)
                if winnerBasedGuild.hasPlayChannel():
                    await send(winnerBasedGuild.getPlayChannel(),
                                f":crossed_swords: **Fight!** {winningDcUser.mention} beat {losingDcUser} in a duel!\n{creditsMsg}",
                                embed=statsEmbed, duelResultsFile=duelResultsFile)
        else:
            if acceptMsg.guild.get_member(losingBasedUser.id) is None:
                await send(acceptMsg.channel,
                            f":crossed_swords: **Fight!** {winningDcUser.mention} beat {losingDcUser} in a duel!\n{creditsMsg}",
                            embed=statsEmbed, duelResultsFile=duelResultsFile)

                loserDCGuild = lib.discordUtil.findBUserDCGuild(losingBasedUser)
                if loserDCGuild is not None:
                    loserBasedGuild = botState.client.guildsDB.getGuild(loserDCGuild.id)
                    if loserBasedGuild.hasPlayChannel():
                        await send(loserBasedGuild.getPlayChannel(),
                                f":crossed_swords: **Fight!** {winningDcUser} beat {losingDcUser.mention} in a duel!\n{creditsMsg}",
                                embed=statsEmbed, duelResultsFile=duelResultsFile)
            else:
                await send(acceptMsg.channel,
                            f":crossed_swords: **Fight!** {winningDcUser.mention} beat {losingDcUser.mention} in a duel!\n{creditsMsg}",
                            embed=statsEmbed, duelResultsFile=duelResultsFile)

    await targetBasedUser.duelRequests[sourceBasedUser].duelTimeoutTask.forceExpire(callExpiryFunc=False)
    targetBasedUser.removeDuelChallengeObj(duelReq)

    return duelResults
    # logStr = ""
    # for s in duelResults["battleLog"]:
    #     logStr += s.replace("{PILOT1NAME}",sourceUser.name).replace("{PILOT2NAME}",targetUser.name) + "\n"
    # await acceptMsg.channel.send(logStr)


# ⚠⚠⚠ THIS FUNCTION IS MARKED FOR CHANGE
async def rejectDuel(duelReq: DuelRequest, rejectMsg: Message, challenger: Optional[Union[User, Member]], recipient: Optional[Union[User, Member]]):
    """Reject a duel request, including expiring the DuelReq object and its TimedTask,
    announcing the request cancellation to both participants, and expiring all related ReactionDuelChallengeMenus.

    :param DuelRequest duelReq: The duel request associated with this duel
    :param discord.message rejectMsg: The message that triggered the rejection of this duel challenge
    :param discord.User challenger: The user or member that issued this challenge
    :param discord.User recipient: The user or member that this challenge was targetted towards
    """
    for menu in duelReq.menus:
        await menu.delete()

    if rejectMsg.guild is None:
        raise ValueError("rejectDuel can only be used from a guild context")

    duelReq.duelTimeoutTask.forceExpire(callExpiryFunc=False)
    duelReq.sourceBasedUser.removeDuelChallengeTarget(duelReq.targetBasedUser)

    if challenger is None:
        await rejectMsg.channel.send(":white_check_mark: Duel challenge rejected.")
    else:    
        await rejectMsg.channel.send(":white_check_mark: You have rejected **" + str(challenger) + "**'s duel challenge.")
    
    if rejectMsg.guild.get_member(duelReq.sourceBasedUser.id) is None:
        targetDCGuild = lib.discordUtil.findBUserDCGuild(duelReq.sourceBasedUser)
        if targetDCGuild is not None:
            targetBasedGuild = botState.client.guildsDB.getGuild(targetDCGuild.id)
            if targetBasedGuild.hasPlayChannel():
                await targetBasedGuild.getPlayChannel().send(":-1: <@" + str(duelReq.sourceBasedUser.id) + ">, **" \
                                                                + ('<unknown user>' if recipient is None else str(recipient)) \
                                                                + "** has rejected your duel request!")


async def expireAndAnnounceDuelReq(duelReqDict: Dict[str, DuelRequest]):
    """Foce the expiry of a given DuelRequest. The duel expiry will be announced to the issuing user.
    TODO: Announce duel expiry to target user, if they have the UA.

    :param DuelRequest duelReqDict: The duel request to expire
    """
    duelReq = duelReqDict["duelReq"]
    duelReq.duelTimeoutTask.forceExpire(callExpiryFunc=False)
    if duelReq.sourceBasedGuild.hasPlayChannel():
        playCh = duelReq.sourceBasedGuild.getPlayChannel()
        if playCh is not None:
            await playCh.send(":stopwatch: <@" + str(duelReq.sourceBasedUser.id) + ">, your duel challenge for **" \
                                + str(botState.client.get_user(duelReq.targetBasedUser.id)) + "** has now expired.")
    duelReq.sourceBasedUser.removeDuelChallengeObj(duelReq)
