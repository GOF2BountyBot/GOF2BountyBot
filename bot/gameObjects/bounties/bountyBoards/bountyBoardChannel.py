from __future__ import annotations
from discord import Embed, HTTPException, Forbidden, NotFound, Client, Message, Colour
from discord.message import MessageReference

from ....databases.bountyDivision import BountyDivision
from ....cfg import bbData, cfg
from .... import lib
from .. import criminal, bounty
from .... import botState
import asyncio
from typing import Any, Awaitable, Callable, Dict, Optional, Protocol, Set, Union, cast
from ....baseClasses import serializable


def makeBountyEmbed(bounty : bounty.Bounty) -> Embed:
    """Construct a discord.Embed for listing in a bountyBoardChannel

    :param Bounty bounty: The bounty to describe in this embed
    :return: A discord.Embed describing statistics about the passed bounty
    :rtype: discord.Embed
    """
    embed = Embed(title=bounty.criminal.name,
                    colour=bbData.factionColours[bounty.faction] if bounty.faction in bbData.factionColours else \
                            bbData.factionColours["neutral"])
    embed.set_footer(text=bounty.faction.title(),
                        icon_url=bbData.factionIcons[bounty.faction] if bounty.faction in bbData.factionIcons else "")
    embed.set_thumbnail(url=bounty.criminal.icon)
    embed.add_field(name="**Reward Pool:**", value=lib.stringTyping.commaSplitNum(bounty.reward) + " Credits")
    embed.add_field(name="**Difficulty:**", value=str(bounty.techLevel))
    # embed = bounty.activeShip.fillLoadoutEmbed(embed, shipEmoji=True)
    embed.add_field(name="**See the culprit's loadout with:**", value="`loadout criminal " + bounty.criminal.name + "`")
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
    return embed


stopwatchIcon = 'https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/twitter/259/stopwatch_23f1.png'
noBountiesEmbed = Embed(description='> Please check back later, or use the `notify bounties` ' \
                        + 'command to be notified when they spawn!', colour=Colour.dark_orange())
noBountiesEmbed.set_author(name='No Bounties Available', icon_url=stopwatchIcon)


async def deleteMessageWithRetry(message: Message, meta: str, *args, **kwargs):
    """Delete a message

    :param Message message: The message to delete
    :param meta: An extra string to describe the message, only used in exceptions
    :type meta: str
    """
    return await lib.discordUtil.asyncOperationWithRetry(message.delete, "delete message", "bountyboards",
                                                        "BBC", meta, *args, **kwargs)


class BountyBoardChannel(serializable.Serializable):
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

    def __init__(self, division: BountyDivision, channelIDToBeLoaded : int, messagesToBeLoaded : Dict[int, dict],
                    noBountiesMsgToBeLoaded : Union[int, None], escapedBountiesMsgToBeLoaded: Union[int, None]):
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
        self.channel = None


    def jumpUrl(self, msgId: int) -> str:
        """Construct a jump URL to a message in self.channel

        :param msgId: The ID of the message to construct a URL for
        :type msgId: int
        :return: A jump URL to the identified message
        :rtype: str
        """
        channelID = self.channelIDToBeLoaded if self.channel is None else self.channel.id
        guildID = None if self.channel is None else self.channel.guild.id
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


    async def loadMessageWithRetry(self, id: int, meta: str, logUrls: bool = True) -> Optional[Message]:
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
        if self.channel is None:
            raise ValueError(f"Attempted loadMessageWithRetry before initializing self.channel")

        meta = self.prependJumpUrl(id, logUrls, meta)
        return await lib.discordUtil.asyncOperationWithRetry(self.channel.fetch_message, "load message", "bountyboards",
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

        return await lib.discordUtil.asyncOperationWithRetry(self.channel.send, "send message", "bountyboards",
                                                            "BBC", meta, *args, **kwargs)

    
    def guildAndChannelMeta(self) -> str:
        """Construct a string detailing the guild and channel where this BBC lives.

        :return: A string identifying self.channel
        :rtype: str
        :raises ValueError: If self.channel has not yet been initialized
        """
        if self.channel is None:
            raise ValueError("Attempted to guildAndChannelMeta before initializing self.channel")

        return f"g:{self.channel.guild.name}#{self.channel.guild.id} c:{self.channel.name}#{self.channel.id}"


    def makeEscapedBountiesEmbed(self) -> Embed:
        """Construct an embed listing all escaped bounties in the division.

        :return: An embed with details of all escaped bounties in the division
        :rtype: Embed
        """
        embed = Embed()
        embed.colour = Colour.random()
        embed.title = "Escaped Bounties"
        if any(self.division.escapedBounties.values()):
            embed.description = "Escaped bounties respawn with the same loadout and a new route after a fixed amount of time."
            for level, bounties in self.division.escapedBounties.items():
                embed.add_field(name=f"Level {level}", value=", ".join(c.name for c in bounties))
        else:
            embed.description = "No escaped bounties currently, the galaxy is safe for a little longer."


    async def _loadEscapedBountiesMessage(self, logUrls: bool):
        self.escapedBountiesMessage = await self.loadMessageWithRetry(self.escapedBountiesMsgToBeLoaded,
                                                                        "escaped bounties", logUrls)

    async def _loadNoBountiesMessage(self, logUrls: bool):
        self.noBountiesMessage = await self.loadMessageWithRetry(self.noBountiesMsgToBeLoaded,
                                                                        "no bounties", logUrls)

    async def _sendNoBountiesMessage(self):
        self.noBountiesMessage = await self.sendMessageWithRetry(f"no bounties {self.guildAndChannelMeta()}",
                                                                    embed=noBountiesEmbed)

    async def _loadCriminalMsg(self, crimDict: dict, msgId: int, logUrls: bool = True):
        crim = criminal.Criminal.fromDict(crimDict)
        if self.division.criminalObjExists(crim):
            msg = await self.loadMessageWithRetry(msgId,
                                                    f"criminal: {crim.name}", logUrls)
            if msg is not None:
                self.bountyMessages[crim] = msg

    async def _sendBountyMsg(self, b: bounty.Bounty):
        msg = await self.sendMessageWithRetry(f"bounty listing: {b.criminal.name} {self.guildAndChannelMeta()}",
                                                embed=makeBountyEmbed(b))
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

        for crim, listing in self.bountyMessages.values():
            if listing is not None:
                tasks.add(deleteMessageWithRetry(listing,
                                                self.prependJumpUrl(listing.id, logUrls, f"bounty listing for {crim}")))

        await tasks.wait()
        tasks.logExceptions("bountyBoards")
        tasks.clear()
        self.escapedBountiesMessage = await self.sendMessageWithRetry(f"escaped bounties {self.guildAndChannelMeta()}",
                                                                        embed=self.makeEscapedBountiesEmbed())
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

        tasks.logExceptions("bountyBoards")


    async def init(self, client : Client, logUrls: bool = True):
        """Initialise the BBC's attributes to allow it to function.
        Initialisation is done here rather than in the constructor as initialisation can only be done asynchronously.

        :param discord.Client client: A logged in client instance used to fetch the BBC's message and channel instances
        :param logUrls: Whether to include message jump urls in logs (Default True)
        """
        self.channel = client.get_channel(self.channelIDToBeLoaded) or await client.fetch_channel(self.channelIDToBeLoaded)
        if self.channel is None:
            raise lib.exceptions.NoLongerExists(f"Failed to load requested channel: {self.channelIDToBeLoaded}")

        tasks = lib.discordUtil.BasicScheduler()
        # True if the channel configuration is invalid and needs to be rebuilt
        doReload = False

        if self.escapedBountiesMsgToBeLoaded == -1:
            doReload = True
        else:
            tasks.add(self._loadEscapedBountiesMessage(logUrls))

        if not self.messagesToBeLoaded:
            if self.noBountiesMsgToBeLoaded != -1:
                tasks.add(self._loadNoBountiesMessage(logUrls))
            else:
                tasks.add(self._sendNoBountiesMessage())
        else:
            for id, crimDict in self.messagesToBeLoaded.items():
                tasks.add(self._loadCriminalMsg(crimDict, id, logUrls))
            
        # del self.messagesToBeLoaded
        # del self.channelIDToBeLoaded
        # del self.noBountiesMsgToBeLoaded

        await tasks.wait()
        tasks.logExceptions("bountyBoards")

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
                tasks.logExceptions("bountyBoards")


    def hasMessageForCriminal(self, criminal : criminal.Criminal) -> bool:
        """Decide whether this BBC stores a listing for the given criminal 

        :param Criminal criminal: The criminal to check for listing existence
        :return: True if this BBC stores a listing for criminal, False otherwise
        :rtype: bool
        """
        return criminal in self.bountyMessages


    def hasMessageForBounty(self, bounty : bounty.Bounty) -> bool:
        """Decide whether this BBC stores a listing for the criminal wanted by the given bounty

        :param Bounty bounty: The bounty whose criminal to check for listing existence
        :return: True if this BBC stores a listing for bounty's criminal, False otherwise
        :rtype: bool
        """
        return self.hasMessageForCriminal(bounty.criminal)


    def getMessageForBounty(self, bounty : bounty.Bounty) -> Message:
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


    async def addBounty(self, bounty : bounty.Bounty, message : Message):
        """Treat the given message as a listing for the given bounty, and store it in the database.
        If the BBC was previously empty, remove the empty bounty board message if one exists.
        If a HTTP error is thrown when attempting to remove the empty board message,
        wait and retry the removal for the number of times defined in cfg

        :param Bounty bounty: The bounty to associate with the given message
        :param discord.Message message: The message acting as a listing for the given bounty
        """
        removeMsg = False
        if self.isEmpty():
            removeMsg = True

        if self.hasMessageForBounty(bounty):
            raise KeyError("BNTY_BRD_CH-ADD-BNTY_EXSTS: Attempted to add a bounty to a bountyboardchannel, " \
                            + "but the bounty is already listed")
            botState.logger.log("BBC", "addBty",
                        "Attempted to add a bounty to a bountyboardchannel, but the bounty is already listed: " \
                        + bounty.criminal.name, category='bountyBoards', eventType="LISTING_ADD-EXSTS")
        self.bountyMessages[bounty.criminal] = message

        if removeMsg:
            try:
                await self.noBountiesMessage.delete()
            except HTTPException:
                succeeded = False
                for tryNum in range(cfg.httpErrRetries):
                    try:
                        await self.noBountiesMessage.delete()
                        succeeded = True
                    except HTTPException:
                        await asyncio.sleep(cfg.httpErrRetryDelaySeconds)
                        continue
                    break
                if not succeeded:
                    print("addBounty HTTPException")
            except Forbidden:
                print("addBounty Forbidden")
            except AttributeError:
                print("addBounty no message")


    async def removeCriminal(self, criminal : criminal.Criminal):
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
            botState.logger.log("BBC", "remCrim",
                                "Attempted to remove a criminal from a bountyboardchannel, but the criminal is not listed: " \
                                    + criminal.name,
                                category='bountyBoards', eventType="LISTING_REM-NO_EXST")
        # listingMsg = await self.channel.fetch_message(self.bountyMessages[criminal])
        try:
            await self.bountyMessages[criminal].delete()
        except HTTPException:
            botState.logger.log("BountyBoardChannel", "removeCriminal",
                                "HTTPException thrown when removing bounty listing message for criminal: " \
                                + criminal.name, category='bountyBoards', eventType="RM_LISTING-HTTPERR")
        except Forbidden:
            botState.logger.log("BountyBoardChannel", "removeCriminal",
                                "Forbidden exception thrown when removing bounty listing message for criminal: " \
                                + criminal.name, category='bountyBoards', eventType="RM_LISTING-FORBIDDENERR")
        except NotFound:
            botState.logger.log("BountyBoardChannel", "removeCriminal",
                                "Bounty listing message no longer exists, BBC entry removed: " + criminal.name,
                                category='bountyBoards', eventType="RM_LISTING-NOT_FOUND")
        del self.bountyMessages[criminal]

        if self.isEmpty():
            try:
                self.noBountiesMessage = await self.channel.send(embed=noBountiesEmbed)

            except HTTPException:
                succeeded = False
                for tryNum in range(cfg.httpErrRetries):
                    try:
                        self.noBountiesMessage = await self.channel.send(embed=noBountiesEmbed)
                        succeeded = True
                    except HTTPException:
                        await asyncio.sleep(cfg.httpErrRetryDelaySeconds)
                        continue
                    break
                if not succeeded:
                    botState.logger.log("BBC", "remBty", "HTTPException thrown when sending no bounties message",
                                category='bountyBoards', eventType="NOBTYMSG_LOAD-HTTPERR")
                self.noBountiesMessage = None
            except Forbidden:
                botState.logger.log("BBC", "remBty", "Forbidden exception thrown when sending no bounties message",
                            category='bountyBoards', eventType="NOBTYMSG_LOAD-FORBIDDENERR")
                self.noBountiesMessage = None


    async def removeBounty(self, bounty : bounty.Bounty):
        """Remove the listing message stored for the given bounty from the database. 
        his does not attempt to delete the message from discord.

        If the BBC is now empty, send an empty bounty board message.
        If a HTTP error is thrown when sending the empty BBC message,
        wait and retry the removal for the number of times defined in cfg

        :param Bounty bounty: The bounty whose listing should be removed from the database
        :raise KeyError: If the database does not store a listing for the given bounty
        """
        await self.removeCriminal(bounty.criminal)


    async def updateBountyMessage(self, bounty : bounty.Bounty):
        """Update the embed for the listing associated with the given bounty.
        This includes newly checked and near-correct systems along the route.
        If a HTTP error is thrown when updating the listing, wait and retry the edit for the number of times defined in cfg

        :param Bounty bounty: The bounty whose listing should be updated
        :raise KeyError: If the database does not store a listing for the given bounty
        """
        if not self.hasMessageForBounty(bounty):
            raise KeyError("BNTY_BRD_CH-UPD-BNTY_NOT_EXST: " \
                            + "Attempted to update a BBC message for a criminal that is not listed")
            botState.logger.log("BBC", "remBty", "Attempted to update a BBC message for a criminal that is not listed: " \
                        + bounty.criminal.name, category='bountyBoards', eventType="LISTING_UPD-NO_EXST")

        content = self.bountyMessages[bounty.criminal].content
        try:
            await self.bountyMessages[bounty.criminal].edit(content=content, embed=makeBountyEmbed(bounty))
        except HTTPException:
            succeeded = False
            for tryNum in range(cfg.httpErrRetries):
                try:
                    await self.bountyMessages[bounty.criminal].edit(content=content, embed=makeBountyEmbed(bounty))
                    succeeded = True
                except HTTPException:
                    await asyncio.sleep(cfg.httpErrRetryDelaySeconds)
                    continue
                break
            if not succeeded:
                botState.logger.log("BBC", "updBtyMsg", "HTTPException thrown when updating bounty listing for criminal: " \
                            + bounty.criminal.name, category='bountyBoards', eventType="UPD_LSTING-HTTPERR")
        except Forbidden:
            botState.logger.log("BBC", "updBtyMsg", "Forbidden exception thrown when updating bounty listing for criminal: " \
                        + bounty.criminal.name, category='bountyBoards', eventType="UPD_LSTING-FORBIDDENERR")
        except NotFound:
            botState.logger.log("BBC", "updBtyMsg", "Bounty listing message no longer exists, BBC entry removed: " \
                        + bounty.criminal.name, category='bountyBoards', eventType="UPD_LSTING-NOT_FOUND")
            await self.removeBounty(bounty)


    async def clear(self):
        """Clear all bounty listings on the board.
        """
        clearTasks = lib.discordUtil.BasicScheduler()
        for criminal in self.bountyMessages.keys():
            clearTasks.add(self.removeCriminal(criminal))
        if clearTasks:
            await clearTasks.wait()
            clearTasks.logExceptions("bountyBoards", "bountyBoardChannel", "clear")


    def toDict(self, **kwargs) -> dict:
        """Serialise this BBC to dictionary format

        :return: A dictionary containing all data needed to recreate this BBC
        :rtype: dict
        """
        # dict of message id: criminal dict
        listings = {msg.id: crim.toDict(**kwargs) for crim, msg in self.bountyMessages.items()}
        return {"channel": self.channel.id, "listings": listings,
                "noBountiesMsg": self.noBountiesMessage.id if self.noBountiesMessage is not None else -1,
                "escapedBountiesMsg": self.escapedBountiesMsg.id if self.escapedBountiesMsg is not None else -1}


    @classmethod
    def fromDict(cls, BBCDict : dict, division: BountyDivision, **kwargs) -> BountyBoardChannel:
        """Factory function constructing a new BBC from the information in the provided dictionary
        - the opposite of bountyBoardChannel.toDict

        :param dict BBCDict: a dictionary representation of the BBC, to convert to an object
        :return: The new bountyBoardChannel object
        :rtype: bountyBoardChannel
        """
        if BBCDict is None:
            return None
        return BountyBoardChannel(division, BBCDict["channel"], BBCDict["listings"],
                                    BBCDict.get("noBountiesMsg", -1),
                                    BBCDict.get("escapedBountiesMsg", -1))
