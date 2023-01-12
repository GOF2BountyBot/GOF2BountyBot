from __future__ import annotations
from typing import TYPE_CHECKING, Coroutine, List, Tuple
from typing_extensions import NotRequired, TypedDict
from discord import Embed, Client, Message, Colour, File, TextChannel
from discord.message import MessageReference
from PIL import Image, ImageDraw
from io import BytesIO
from ....baseClasses.serializable import SerializesToSchema

if TYPE_CHECKING:
    from ....databases.bountyDivision import BountyDivision
from ....cfg import bbData, cfg
from .... import lib
from .. import criminal, bounty
from .... import botState
from typing import Dict, Optional, Set, Union, cast
from .. import solarSystem
from ....logging import LogCategory


stopwatchIcon = 'https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/twitter/259/stopwatch_23f1.png'
noBountiesEmbed = Embed(description='> Please check back later, or use the `notify bounties` ' \
                        + 'command to be notified when they spawn!', colour=Colour.dark_orange())
noBountiesEmbed.set_author(name='No Bounties Available', icon_url=stopwatchIcon)


def renderRouteMap(routeNames: List[str]) -> Optional[Image.Image]:
    """Render a route through the galaxy onto the map image.

    :param List[str] routeNames: List of system names in the route, in order. If routeNames is empty, return None.
    :return: An `cfg.paths.mapImage` with `routeNames` rendered over it. `null` if the render failed.
    """
    if not routeNames:
        return None

    mapImage = lib.graphics.copyStarMap()
    mapDraw = ImageDraw.Draw(mapImage)
    route: List[solarSystem.SolarSystem] = [bbData.builtInSystemObjs[s] for s in routeNames]

    if len(routeNames) == 1:
        system = route[0]
        mapDraw.ellipse(lib.graphics.circleBoundingBox(system.coordinates, cfg.bbcRouteImageSingleSystemRadius),
                        fill=None, outline=cfg.bbcRouteImageLineColour,
                        width=cfg.bbcRouteImageLineWidth)
    else:
        for systemNum, system in enumerate(route[:-1]):
            nextSystem = route[systemNum+1]
            mapDraw.line((system.coordinates, nextSystem.coordinates),
                            fill=cfg.bbcRouteImageLineColour,
                            width=cfg.bbcRouteImageLineWidth)

        for system in route:
            mapDraw.ellipse(lib.graphics.circleBoundingBox(system.coordinates, cfg.bbcRouteImageNodeRadius),
                            fill=cfg.bbcRouteImageNodeColour, width=0)

    return mapImage


async def deleteMessageWithRetry(message: Message, meta: str, *args, **kwargs):
    """Delete a message

    :param Message message: The message to delete
    :param meta: An extra string to describe the message, only used in exceptions
    :type meta: str
    """
    return await lib.discordUtil.asyncOperationWithRetry(message.delete, "delete message", LogCategory.bountyBoards,
                                                        "BBC", meta, *args, **kwargs)


class SerializedBountyBoardChannel(TypedDict):
    listings: Dict[int, criminal.SerializedCriminalUnion]
    channel: int
    noBountiesMsg: int
    escapedBountiesMsg: int


class BountyBoardChannel(SerializesToSchema[SerializedBountyBoardChannel]):
    """A channel which stores a continuously updating listing message for every active bounty.

    Initialisation atts: These attributes are used only when loading in the BBC from dictionary-serialised format.
                            They must be used to initialise the BBC before the BBC can be used.
    :var messagesToBeLoaded: A dictionary of bounty listings to be loaded into the BBC, where keys are message IDs,
                                and values are criminal dicts
    :vartype messagesToBeLoaded: dict[int, dict]
    :var channelIDToBeLoaded: The discord channel ID of the channel where this BBC is active, to be loaded into the BBC
    :vartype channelIDToBeLoaded: int
    :var noBountiesMsgToBeLoaded: The id of the message to be loaded indicating that the BBC is empty, if one exists
    :vartype noBountiesMsgToBeLoaded: int
    :var escapedBountiesMsgToBeLoaded: The id of the message to be loaded listing all escaped bounties, if one exists
    :vartype escapedBountiesMsgToBeLoaded: int

    Runtime atts: These are the attributes that contribute to the BBC's runtime functionality, unlike initialisation atts.
    :var division: The division that this BBC represents
    :vartype division: BountyDivision
    :var bountyMessages: A dictionary associating criminals to their listing discord.Messages.
    :vartype bountyMessages: dict[criminal, Message]
    :var noBountiesMessage: Either a reference to a discord.message indicating that the BBC is empty,
                            or None if no empty board message exists
    :vartype noBountiesMessage: discord.message or None
    :var escapedBountiesMessage: A reference to a discord.message listing all escaped bounties. This *should* always exist.
    :vartype escapedBountiesMessage: discord.message
    :var channel: The channel where this BBC's listings are to be posted
    :vartype channel: discord.TextChannel
    """
    def __init__(self, division: "BountyDivision", channelIDToBeLoaded: int, messagesToBeLoaded: Dict[int, criminal.SerializedCriminalUnion],
                    noBountiesMsgToBeLoaded: Union[int, None], escapedBountiesMsgToBeLoaded: Union[int, None]):
        """
        :param BountyDivision division: The division that this BBC represents
        :param int channelIDToBeLoaded: The discord channel ID of the channel where this BBC is active,
                                        to be loaded into the BBC
        :param messagesToBeLoaded: A dictionary of bounty listings to be loaded into the BBC, where keys are message IDs,
                                    and values are criminal dicts
        :type messagesToBeLoaded: dict[int, dict]
        :param int noBountiesMsgToBeLoaded: The id of the message to be loaded indicating that the BBC is empty, if one exists
        """
        self.division = division
        self.messagesToBeLoaded = messagesToBeLoaded
        self.channelIDToBeLoaded = channelIDToBeLoaded
        self.noBountiesMsgToBeLoaded = noBountiesMsgToBeLoaded
        self.escapedBountiesMsgToBeLoaded = escapedBountiesMsgToBeLoaded

        self.bountyMessages: Dict[criminal.Criminal, Message] = {}
        # discord message object to be filled when no bounties exist
        self.noBountiesMessage = None
        # discord message object to list all escaped bounties. Active even when there are no escaped bounties.
        self.escapedBountiesMessage = None
        # discord channel object
        # This will be None if the BBC has not yet been initialized
        self._channel: Optional[TextChannel] = None
        # A list of coroutines to await after init is complete
        self.postInitTasks: Optional[Set[Coroutine]] = None
        
        self.initialized = False

    
    @property
    def channel(self):
        if self._channel is None:
            raise lib.exceptions.NotReady("Attempted to access BountyBoardChannel.channel before the BBC was initialized")
        return cast(TextChannel, self._channel)


    async def makeBountyEmbed(self, bounty: bounty.Bounty) -> Embed:
        """Construct a discord.Embed for listing in a bountyBoardChannel

        :param Bounty bounty: The bounty to describe in this embed
        :return: An Embed describing statistics about the passed bounty
        :rtype: discord.Embed
        """
        embed = Embed(title=bounty.criminal.name,
                        colour=bbData.factionColours[bounty.faction] if bounty.faction in bbData.factionColours else \
                                bbData.factionColours["neutral"])
        embed.set_footer(text=f"{bounty.faction.title()}",
                            icon_url=bbData.factionIcons[bounty.faction] if bounty.faction in bbData.factionIcons else "")

        infoStr = f"**Difficulty:** {bounty.techLevel}\n" \
                + f"**Reward Pool:** {lib.stringTyping.commaSplitNum(bounty.reward)} Credits\n" \
                + f"**Bounty Ends:** <t:{int(bounty.endTime)}:R>"
        embed.add_field(name="​", value=infoStr)

        if bounty.activeShip is not None:
            loadoutFieldValue = ""
            if cfg.bbcShowLoadoutEmojis:
                loadoutFieldName = "**Loadout:**"
                weaponsStr = "".join(i.emoji.sendable for i in bounty.activeShip.weapons if i.hasEmoji)
                modulesStr = "".join(i.emoji.sendable for i in bounty.activeShip.modules if i.hasEmoji)
                turretsStr = "".join(i.emoji.sendable for i in bounty.activeShip.turrets if i.hasEmoji)
                
                statsShown = True
                if cfg.bbcShowHpDps:
                    totalHp = bounty.activeShip.getArmour() + bounty.activeShip.getShield()
                    duelingStatsStr = f" {totalHp} HP // {bounty.activeShip.getDPS()} DPS"
                    statsShown = False
                else:
                    duelingStatsStr = ""

                if bounty.activeShip.hasEmoji:
                    loadoutFieldValue += f"{bounty.activeShip.emoji.sendable}{'' if statsShown else duelingStatsStr}\n"
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
                                    value=f"Total health: {bounty.activeShip.getArmour() + bounty.activeShip.getShield()}\n" \
                                        + f"Total DPS: {bounty.activeShip.getDPS()}")

            prefix = self.division.owningDB.owningBasedGuild.commandPrefix
            embed.add_field(name=loadoutFieldName, value=f"{loadoutFieldValue}`{prefix}loadout criminal {bounty.criminal.name}`")

        embed.set_thumbnail(url=bounty.criminal.icon)
        # embed.add_field(name="**Reward Pool:**", value=lib.stringTyping.commaSplitNum(bounty.reward) + " Credits")
        # embed.add_field(name="**Difficulty:**", value=str(bounty.techLevel))

        routeStr = ""
        for system in bounty.route:
            if bounty.systemChecked(system):
                routeStr += "~~"
                if 0 < bounty.route.index(bounty.answer) - bounty.route.index(system) < cfg.closeBountyThreshold:
                    routeStr += "**" + system + "**"
                else:
                    routeStr += system
                routeStr += "~~"
            else:
                routeStr += system
            routeStr += ", "
        embed.add_field(name="**Route:**", value=routeStr[:-2], inline=False)
        embed.add_field(name="-", value="> ~~Already checked systems~~\n> **Criminal spotted here recently**")
        # embed.add_field(name="Bounty ends:", value=f"<t:{int(bounty.endTime)}:R>")

        if cfg.bbcShowRouteImage:
            routeImage = renderRouteMap(bounty.route)
            if routeImage is not None:
                routeImageBytes = BytesIO()
                routeImage.save(routeImageBytes, "PNG")
                routeImageBytes.seek(0)
                routeResultsFile = File(routeImageBytes, filename="route.png")
                routeImageMessage: Message = await botState.client.bountyRouteImagesChannel.send(file=routeResultsFile)
                routeImage.close()
                routeImageBytes.close()
                routeResultsFile.close()
                embed.set_image(url=routeImageMessage.attachments[0].url)

        return embed


    def jumpUrl(self, msgId: int) -> str:
        """Construct a jump URL to a message in self.channel

        :param msgId: The ID of the message to construct a URL for
        :type msgId: int
        :return: A jump URL to the identified message
        :rtype: str
        """
        if self.channel is not None:
            channelID = self.channelIDToBeLoaded
            guildID = None
        else:
            channelID = self.channel.id
            guildID = self.channel.guild.id
        return MessageReference(message_id=msgId, channel_id=channelID, guild_id=guildID,
                                fail_if_not_exists=False).jump_url


    def prependJumpUrl(self, id: int, logUrls: bool, content: str) -> str:
        """Prepend the jump url for the identified message, if instructed to. Otherwise prepend the message ID.

        :param id: The ID of the message
        :type id: int
        :param logUrls: Whether to generate a jump URL, or prepend the ID instead
        :type logUrls: bool
        :param content: The content to appear after the url/id
        :type content: str
        :return: content, with a link or id of the message prepended
        :rtype: str
        """
        return f"[{self.jumpUrl(id) if logUrls else id}]{f' {content}' if content else ''}"


    async def loadMessageWithRetry(self, id: int, meta: str, logUrls: bool = True, initializing: bool = False) -> Optional[Message]:
        """Load a message from self.channel by id

        :param id: The id of the message to load
        :type id: int
        :param meta: An extra string to describe the message, only used in errors
        :type meta: str
        :param logUrls: Whether or not to include a jump url to the message in logs (Default True)
        :raises ValueError: If self.channel has not be set yet
        :return: A message if one is found, None if an error occurred
        :rtype: Optional[Message]
        """
        if not self.initialized and not initializing:
            raise ValueError(f"Attempted loadMessageWithRetry before initializing self.channel")

        meta = self.prependJumpUrl(id, logUrls, meta)
        return await lib.discordUtil.asyncOperationWithRetry(self.channel.fetch_message, "load message", LogCategory.bountyBoards,
                                                            "BBC", meta, id)


    async def sendMessageWithRetry(self, meta: str, *args, **kwargs) -> Optional[Message]:
        """Send a message to self.channel

        :param meta: An extra string to describe the message, only used in exceptions
        :type meta: str
        :raises ValueError: If self.channel has not yet been initialized
        :return: The message that was created, or None if there was an error
        :rtype: Optional[Message]
        """
        if self.channel is None:
            raise ValueError("Attempted to sendMessageWithRetry before initializing self.channel")

        return await lib.discordUtil.asyncOperationWithRetry(self.channel.send, "send message", LogCategory.bountyBoards,
                                                            "BBC", meta, *args, **kwargs)


    async def editMessageWithRetry(self, message: Message, meta: str, logUrls: bool = True, *args, **kwargs) -> \
            Optional[Message]:
        """Edit a message. Specify the new content using *args and **kwargs

        :param Message message: The message to edit
        :param meta: An extra string to describe the message, only used in exceptions
        :type meta: str
        :param logUrls: Whether or not to include a jump url to the message in logs (Default True)
        :raises ValueError: If self.channel has not yet been initialized
        :return: The message after editing, or None if there was an error
        :rtype: Optional[Message]
        """
        if self.channel is None:
            raise ValueError("Attempted to sendMessageWithRetry before initializing self.channel")

        meta = self.prependJumpUrl(message.id, logUrls, meta)
        await lib.discordUtil.asyncOperationWithRetry(message.edit, "edit message", LogCategory.bountyBoards,
                                                        "BBC", meta, *args, **kwargs)
        return message

    
    def guildAndChannelMeta(self) -> str:
        """Construct a string detailing the guild and channel where this BBC lives.

        :return: A string identifying self.channel
        :rtype: str
        :raises ValueError: If self.channel has not yet been initialized
        """
        if self.channel is None:
            raise ValueError("Attempted to guildAndChannelMeta before initializing self.channel")

        return f"g:{self.channel.guild.name}#{self.channel.guild.id} c:{self.channel.name}#{self.channel.id}"


    def makeEscapedBountiesMsgKwargs(self, ignoredBounties: Tuple[bounty.Bounty, ...] = ()) -> Dict[str, Union[str, Optional[Embed]]]:
        """Construct an embed listing all escaped bounties in the division.

        :return: A kwargs mapping detailing the content of the BBC's escaped bounties message
        :rtype: Dict[str, Union[str, Embed]]
        """
        if ignoredBounties:
            validBounties: Dict[int, List[bounty.Bounty]] = {}
            for level, bounties in self.division.escapedBounties.items():
                validBounties.update({level: [b for b in bounties.values() if b not in ignoredBounties]})
        else:
            validBounties = {l: [b for b in bounties.values()] for l, bounties in self.division.escapedBounties.items()}
        
        if any(validBounties.items()):
            embed = Embed()
            embed.colour = Colour.random()
            embed.title = "Escaped Bounties"
            embed.description = "Escaped bounties respawn with the same loadout and a new route after a fixed "\
                                + "amount of time."
            for level, newBounties in validBounties.items():
                if newBounties:
                    embed.add_field(name=f"Level {level}", value=", ".join(b.criminal.name for b in newBounties))
        else:
            embed = None

        return {"embed": embed, "content": "‎"}


    async def updateEscapedBountiesMessage(self, ignoredBounties: Tuple[bounty.Bounty, ...] = ()):
        """Rebuild the escaped bounties message with new details of any escaped bounties
        """
        if self.escapedBountiesMessage is not None:
            self.escapedBountiesMessage = await self.editMessageWithRetry(self.escapedBountiesMessage,
                                                                            "escaped bounties",
                                                                            **self.makeEscapedBountiesMsgKwargs(ignoredBounties=ignoredBounties))
        if self.escapedBountiesMessage is None:
            await self.rebuild()


    async def _loadEscapedBountiesMessage(self, logUrls: bool, initializing: bool = False):
        if self.escapedBountiesMsgToBeLoaded is None:
            raise ValueError("escapedBountiesMsgToBeLoaded not supplied")
        self.escapedBountiesMessage = await self.loadMessageWithRetry(self.escapedBountiesMsgToBeLoaded,
                                                                        "escaped bounties", logUrls, initializing=initializing)


    async def _loadNoBountiesMessage(self, logUrls: bool, initializing: bool = False):
        if self.noBountiesMsgToBeLoaded is None:
            raise ValueError("noBountiesMsgToBeLoaded not supplied")
        self.noBountiesMessage = await self.loadMessageWithRetry(self.noBountiesMsgToBeLoaded,
                                                                    "no bounties", logUrls, initializing=initializing)


    async def _sendNoBountiesMessage(self):
        self.noBountiesMessage = await self.sendMessageWithRetry(f"no bounties {self.guildAndChannelMeta()}",
                                                                    embed=noBountiesEmbed)


    async def _loadCriminalMsg(self, crimDict: criminal.SerializedCriminalUnion, msgId: int, logUrls: bool = True, initializing: bool = False):
        crim = criminal.Criminal.deserialize(crimDict)
        if self.division.criminalObjExists(crim):
            msg = await self.loadMessageWithRetry(msgId, f"criminal: {crim.name}", logUrls, initializing=initializing)
            if msg is not None:
                self.bountyMessages[crim] = msg


    async def _sendBountyMsg(self, b: bounty.Bounty):
        msg = await self.sendMessageWithRetry(f"bounty listing: {b.criminal.name} {self.guildAndChannelMeta()}",
                                                embed=await self.makeBountyEmbed(b))
        if msg is not None:
            self.bountyMessages[b.criminal] = msg


    async def rebuild(self, logUrls: bool = True):
        """Completely rebuild all messages on the board, deleting existing messages if known.

        :param logUrls: Whether to include message jump urls in logs (Default True)
        :type logUrls: bool
        """
        tasks = lib.discordUtil.BasicScheduler()
        divEmpty = self.division.isEmpty(includeEscaped=False)

        if self.escapedBountiesMessage is not None:
            tasks.add(deleteMessageWithRetry(self.escapedBountiesMessage,
                                                self.prependJumpUrl(self.escapedBountiesMessage.id, logUrls,
                                                                    "escaped bounties")))

        if self.noBountiesMessage is not None:
            tasks.add(deleteMessageWithRetry(self.noBountiesMessage,
                                                self.prependJumpUrl(self.noBountiesMessage.id, logUrls,
                                                                    "no bounties")))

        for crim, listing in self.bountyMessages.items():
            if listing is not None:
                tasks.add(deleteMessageWithRetry(listing,
                                                self.prependJumpUrl(listing.id, logUrls, f"bounty listing for {crim}")))

        await tasks.wait()
        tasks.logExceptions(LogCategory.bountyBoards)
        tasks.clear()
        self.escapedBountiesMessage = await self.sendMessageWithRetry(f"escaped bounties {self.guildAndChannelMeta()}",
                                                                        **self.makeEscapedBountiesMsgKwargs())
        if divEmpty:
            self.noBountiesMessage = await self.sendMessageWithRetry(f"no bounties {self.guildAndChannelMeta()}",
                                                                        embed=noBountiesEmbed)
        else:
            for registry in self.division.bounties.values():
                for bounty in registry.values():
                    tasks.add(self._sendBountyMsg(bounty))

        await tasks.wait()
        if divEmpty:
            self.bountyMessages.clear()
        elif self.noBountiesMessage is not None:
            self.noBountiesMessage = None

        tasks.logExceptions(LogCategory.bountyBoards)


    async def init(self, client: Client, logUrls: bool = True):
        """Initialise the BBC's attributes to allow it to function.
        Initialisation is done here rather than in the constructor as initialisation can only be done asynchronously.

        :param discord.Client client: A logged in client instance used to fetch the BBC's message and channel instances
        :param logUrls: Whether to include message jump urls in logs (Default True)
        """
        chan = client.get_channel(self.channelIDToBeLoaded) or await client.fetch_channel(self.channelIDToBeLoaded)
        if chan is None:
            raise lib.exceptions.NoLongerExists(f"Failed to load requested channel: {self.channelIDToBeLoaded}")
        if not isinstance(chan, TextChannel):
            raise ValueError(f"Channel is not a TextChannel: {self.channelIDToBeLoaded}")
        
        self._channel = chan

        tasks = lib.discordUtil.BasicScheduler()
        # True if the channel configuration is invalid and needs to be rebuilt
        doReload = False

        if self.escapedBountiesMsgToBeLoaded == -1:
            doReload = True
        else:
            await self._loadEscapedBountiesMessage(logUrls, initializing=True)
            doReload = self.escapedBountiesMessage is None

        if not self.messagesToBeLoaded:
            if self.noBountiesMsgToBeLoaded != -1:
                tasks.add(self._loadNoBountiesMessage(logUrls, initializing=True))
            else:
                tasks.add(self._sendNoBountiesMessage())
        else:
            for id, crimDict in self.messagesToBeLoaded.items():
                tasks.add(self._loadCriminalMsg(crimDict, id, logUrls, initializing=True))
            
        # del self.messagesToBeLoaded
        # del self.channelIDToBeLoaded
        # del self.noBountiesMsgToBeLoaded

        await tasks.wait()
        tasks.logExceptions(LogCategory.bountyBoards)

        if doReload:
            await self.rebuild(logUrls)
        else:
            tasks.clear()
            for tlBounties in self.division.bounties.values():
                for b in tlBounties.values():
                    if b.criminal not in self.bountyMessages:
                        tasks.add(self._sendBountyMsg(b))
            if tasks:
                await tasks.wait()
                tasks.logExceptions(LogCategory.bountyBoards)

        self.initialized = True
        
        if self.postInitTasks:
            t = lib.discordUtil.BasicScheduler()
            for task in self.postInitTasks:
                t.add(task)
            await t.wait()
            t.logExceptions(logCategory=LogCategory.bountyBoards)
            del self.postInitTasks
            self.postInitTasks = None

    
    def addPostInitTask(self, coro: Coroutine):
        if self.postInitTasks is None:
            self.postInitTasks = {coro}
        else:
            self.postInitTasks.add(coro)


    def hasMessageForCriminal(self, criminal: criminal.Criminal) -> bool:
        """Decide whether this BBC stores a listing for the given criminal 

        :param Criminal criminal: The criminal to check for listing existence
        :return: True if this BBC stores a listing for criminal, False otherwise
        :rtype: bool
        """
        return criminal in self.bountyMessages


    def hasMessageForBounty(self, bounty: bounty.Bounty) -> bool:
        """Decide whether this BBC stores a listing for the criminal wanted by the given bounty

        :param Bounty bounty: The bounty whose criminal to check for listing existence
        :return: True if this BBC stores a listing for bounty's criminal, False otherwise
        :rtype: bool
        """
        return self.hasMessageForCriminal(bounty.criminal)


    def getMessageForBounty(self, bounty: bounty.Bounty) -> Message:
        """Return the message acting as a listing for the given bounty's criminal

        :param Bounty bounty: The bounty whose criminal to fetch a listing for
        :return: This BBC's message listing the bounty for the given bounty's criminal
        :rtype: discord.Message
        """
        return self.bountyMessages[bounty.criminal]


    def isEmpty(self) -> bool:
        """Decide whether this BBC stores any bounty listings

        :return: False if this BBC stores any bounty listings, True otherwise
        :rtype: bool
        """
        return not bool(self.bountyMessages)


    async def addBounty(self, bounty: bounty.Bounty, message: Message, logUrls: bool = True):
        """Treat the given message as a listing for the given bounty, and store it in the database.
        If the BBC was previously empty, remove the empty bounty board message if one exists.
        If a HTTP error is thrown when attempting to remove the empty board message,
        wait and retry the removal for the number of times defined in cfg

        :param Bounty bounty: The bounty to associate with the given message
        :param discord.Message message: The message acting as a listing for the given bounty
        :param logUrls: Whether to generate a jump URL, or prepend the ID instead
        """
        removeMsg = False
        if self.isEmpty():
            removeMsg = True

        if self.hasMessageForBounty(bounty):
            raise KeyError("BNTY_BRD_CH-ADD-BNTY_EXSTS: Attempted to add a bounty to a bountyboardchannel, " \
                            + "but the bounty is already listed")
            botState.client.logger.log("BBC", "addBty",
                        "Attempted to add a bounty to a bountyboardchannel, but the bounty is already listed: " \
                        + bounty.criminal.name, category='bountyBoards', eventType="LISTING_ADD-EXSTS")
        self.bountyMessages[bounty.criminal] = message

        if removeMsg and self.noBountiesMessage is not None:
            await deleteMessageWithRetry(self.noBountiesMessage,
                                        self.prependJumpUrl(self.noBountiesMessage.id, logUrls, "no bounties"))


    async def removeCriminal(self, criminal: criminal.Criminal):
        """Remove the listing message stored for the given criminal from the database,
        and delete its associated message from discord.
        
        If the BBC is now empty, send an empty bounty board message.
        If a HTTP error is thrown when sending the empty BBC message,
        wait and retry the removal for the number of times defined in cfg

        :param Criminal criminal: The criminal whose listing should be removed from the database
        :raise KeyError: If the database does not store a listing for the given criminal
        """
        if not self.hasMessageForCriminal(criminal):
            raise KeyError("BNTY_BRD_CH-REM-BNTY_NOT_EXST: Attempted to remove a criminal from a bountyboardchannel, " \
                            + "but the criminal is not listed")
            botState.client.logger.log("BBC", "remCrim",
                                "Attempted to remove a criminal from a bountyboardchannel, but the criminal is not listed: " \
                                    + criminal.name,
                                category='bountyBoards', eventType="LISTING_REM-NO_EXST")
        # listingMsg = await self.channel.fetch_message(self.bountyMessages[criminal])
        await deleteMessageWithRetry(self.bountyMessages[criminal], f"bounty: {criminal.name}")
        del self.bountyMessages[criminal]

        if self.isEmpty():
            await self._sendNoBountiesMessage()


    async def removeBounty(self, bounty: bounty.Bounty):
        """Remove the listing message stored for the given bounty from the database. 
        his does not attempt to delete the message from discord.

        If the BBC is now empty, send an empty bounty board message.
        If a HTTP error is thrown when sending the empty BBC message,
        wait and retry the removal for the number of times defined in cfg

        :param Bounty bounty: The bounty whose listing should be removed from the database
        :raise KeyError: If the database does not store a listing for the given bounty
        """
        await self.removeCriminal(bounty.criminal)


    async def updateBountyMessage(self, bounty: bounty.Bounty):
        """Update the embed for the listing associated with the given bounty.
        This includes newly checked and near-correct systems along the route.
        If a HTTP error is thrown when updating the listing, wait and retry the edit for the number of times defined in cfg

        :param Bounty bounty: The bounty whose listing should be updated
        :raise KeyError: If the database does not store a listing for the given bounty
        """
        if not self.hasMessageForBounty(bounty):
            raise KeyError("BNTY_BRD_CH-UPD-BNTY_NOT_EXST: " \
                            + "Attempted to update a BBC message for a criminal that is not listed")
            botState.client.logger.log("BBC", "remBty", "Attempted to update a BBC message for a criminal that is not listed: " \
                        + bounty.criminal.name, category='bountyBoards', eventType="LISTING_UPD-NO_EXST")

        content = self.bountyMessages[bounty.criminal].content
        await self.editMessageWithRetry(self.bountyMessages[bounty.criminal], f"bounty: {bounty.criminal.name}",
                                        content=content, embed=await self.makeBountyEmbed(bounty))


    async def clear(self):
        """Clear all bounty listings on the board.
        """
        clearTasks = lib.discordUtil.BasicScheduler()
        for criminal in self.bountyMessages.keys():
            clearTasks.add(self.removeCriminal(criminal))
        if clearTasks:
            await clearTasks.wait()
            clearTasks.logExceptions(LogCategory.bountyBoards, "bountyBoardChannel", "clear")
            await self.updateEscapedBountiesMessage()


    def serialize(self, **kwargs) -> SerializedBountyBoardChannel:
        """Serialise this BBC to dictionary format

        :return: A dictionary containing all data needed to recreate this BBC
        :rtype: dict
        """
        # dict of message id: criminal dict
        listings = {msg.id: crim.serialize(**kwargs) for crim, msg in self.bountyMessages.items()}
        return {"channel": self.channel.id, "listings": listings,
                "noBountiesMsg": self.noBountiesMessage.id if self.noBountiesMessage is not None else -1,
                "escapedBountiesMsg": self.escapedBountiesMessage.id if self.escapedBountiesMessage is not None else -1}


    @classmethod
    def deserialize(cls, BBCDict: SerializedBountyBoardChannel, division: "BountyDivision", **kwargs) -> BountyBoardChannel:
        """Factory function constructing a new BBC from the information in the provided dictionary
        - the opposite of bountyBoardChannel.serialize

        :param dict BBCDict: a dictionary representation of the BBC, to convert to an object
        :return: The new bountyBoardChannel object
        :rtype: bountyBoardChannel
        """
        return BountyBoardChannel(division, BBCDict["channel"], BBCDict["listings"],
                                    BBCDict.get("noBountiesMsg", -1),
                                    BBCDict.get("escapedBountiesMsg", -1))
