from typing import Any, List, Tuple, Dict, Optional, Union

from discord import Embed, Message, Colour, PartialMessage
from discord.enums import ChannelType

from ..entities.bounties import bounty
from ..entities.bounties.bountyBoardChannel import AnyBountyBoardChannel
from ..entities.bounties.bountyBoardChannelListing import BountyBoardChannelListing
from .. import client
from ..lib.discordUtil import discordOperationWithRetry, LazyChannel
from ..lib import asyncUtil
from ..entities.bounties import criminal
from ..logging import LogCategory
from ..helpers.bountyBoardListingFormatter import BountyBoardListingFormatter
from . import bountyDivisionService


class BountyBoardChannelService:
    def __init__(self, divisionService: "bountyDivisionService.BountyDivisionService", client: "client.BasedClient"):
        self._cachedChannel: Optional[LazyChannel] = None
        self._cachedChannelId: Optional[int] = None
        self.divisionService = divisionService
        self.client = client


    async def _prependJumpUrl(self, bbc: AnyBountyBoardChannel, id: int, logUrls: bool, content: str) -> str:
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
        jump = await BountyBoardListingFormatter.listingJumpUrl(bbc, id) if logUrls else id
        return f"[{jump}]{f' {content}' if content else ''}"
    
    
    async def getMessageForBounty(self, bbc: AnyBountyBoardChannel, bounty: bounty.AnyBounty) -> PartialMessage:
        """Get a reference to the message acting as a listing for the given bounty's criminal

        :param Bounty bounty: The bounty whose criminal to fetch a listing for
        :return: This BBC's message listing the bounty for the given bounty's criminal
        :rtype: discord.PartialMessage
        """
        return self._c(bbc).partial.get_partial_message((await bbc.listings)[bounty.criminalId].messageId)
    

    def makeListing(self, bbc: AnyBountyBoardChannel, msg: Union[int, PartialMessage], crim: Union["criminal.AnyCriminal", int, "bounty.AnyBounty"]) -> BountyBoardChannelListing:
        c = crim if isinstance(crim, int) else crim.id if isinstance(crim, criminal.Criminal) else crim.criminalId
        return BountyBoardChannelListing(
            bountyBoardChannelId=bbc.channelId,
            messageId=msg if isinstance(msg, int) else msg.id,
            criminalId=c
        ) 


    def _c(self, bbc: AnyBountyBoardChannel) -> LazyChannel:
        """Get a lazy reference to the active channel.
        This is not guaranteed to exist.
        """
        if self._cachedChannel is None or self._cachedChannelId != bbc.channelId:
            # should really be passing bbc.division.guildId here as well, but I want to avoid making this method async
            self._cachedChannel = LazyChannel(self.client, bbc.channelId, type=ChannelType.text)
            self._cachedChannelId = bbc.channelId
        return self._cachedChannel
    

    def messageRef(self, bbc: AnyBountyBoardChannel, id: int):
        """Get a reference to a message in the channel.
        This is not guaranteed to exist.
        """
        return self._c(bbc).partial.get_partial_message(id)


    def escapedBountiesMsgRef(self, bbc: AnyBountyBoardChannel):
        """Get a reference to the 'escaped bounties' message.
        This is not guaranteed to exist.
        Throws an exception if bbc.escapedBountiesMessageId is None.
        """
        if bbc.escapedBountiesMessageId is None:
            raise ValueError("no escaped bounties message set")
        return self.messageRef(bbc, bbc.escapedBountiesMessageId)
    

    def noBountiesMsgRef(self, bbc: AnyBountyBoardChannel):
        """Get a reference to the 'no active bounties' message in the channel.
        This is not guaranteed to exist.
        Throws an exception if bbc.noBountiesMessageId is None.
        """
        if bbc.noBountiesMessageId is None:
            raise ValueError("no no bounties message set")
        return self.messageRef(bbc, bbc.noBountiesMessageId)

    async def deleteMessageWithRetry(self, bbc: AnyBountyBoardChannel, message: Union[Message, PartialMessage], meta: str, *args: Any, **kwargs: Any):
        """Delete a message

        :param Message message: The message to delete
        :param meta: An extra string to describe the message, only used in exceptions
        :type meta: str
        """
        return await discordOperationWithRetry(message.delete, "delete message", LogCategory.bountyBoards,
                                                "BBC", meta, *args, **kwargs)


    async def sendMessageWithRetry(self, bbc: AnyBountyBoardChannel, meta: str, *args: Any, **kwargs: Any) -> Optional[Message]:
        """Send a message to bbc.channel

        :param meta: An extra string to describe the message, only used in exceptions
        :type meta: str
        :return: The message that was created, or None if there was an error
        :rtype: Optional[Message]
        """
        return await self._c(bbc).withRetry(lambda c: c.send(*args, **kwargs),
                                               "send message", LogCategory.bountyBoards,
                                               "BBC", meta)


    async def editMessageWithRetry(self, bbc: AnyBountyBoardChannel, message: PartialMessage, meta: str, logUrls: bool = True, *args: Any, **kwargs: Any) -> \
            Optional[Message]:
        """Edit a message. Specify the new content using *args and **kwargs

        :param Message message: The message to edit
        :param meta: An extra string to describe the message, only used in exceptions
        :type meta: str
        :param logUrls: Whether or not to include a jump url to the message in logs (Default True)
        :return: The message after editing, or None if there was an error
        :rtype: Optional[Message]
        """
        meta = await self._prependJumpUrl(bbc, message.id, logUrls, meta)
        return await discordOperationWithRetry(message.edit, "edit message", LogCategory.bountyBoards,
                                        "BBC", meta, *args, **kwargs)

    
    async def guildAndChannelMeta(self, bbc: AnyBountyBoardChannel) -> str:
        """Construct a string detailing the guild and channel where this BBC lives.

        :return: A string identifying bbc.channel
        :rtype: str
        """
        c = await self._c(bbc).fetch()
        return f"g:{c.guild.name}#{c.guild.id} c:{c.name}#{c.id}"
    

    async def makeEscapedBountiesMsgKwargs(self, bbc: AnyBountyBoardChannel, ignoredBounties: Optional[Tuple[bounty.Bounty[Any], ...]] = None) -> Dict[str, Union[str, Optional[Embed]]]:
        """Construct an embed listing all escaped bounties in the division.

        :return: A kwargs mapping detailing the content of the BBC's escaped bounties message
        :rtype: Dict[str, Union[str, Embed]]
        """
        ignoredBounties = ignoredBounties or ()
        division = await bbc.division
        escaped = await self.divisionService.escapedBounties(division)
        escapedByLevel = {level: [b for b in escaped if b.techLevel == level] for level in division.levelRange}
        
        if ignoredBounties:
            validBounties: Dict[int, List[bounty.Bounty[Any]]] = {}
            for level, bounties in escapedByLevel.items():
                validBounties.update({level: [b for b in bounties if b not in ignoredBounties]})
        else:
            validBounties = {l: [b for b in bounties] for l, bounties in escapedByLevel.items()}
        
        if any(validBounties.items()):
            embed = Embed()
            embed.colour = Colour.random()
            embed.title = "Escaped Bounties"
            embed.description = "Escaped bounties respawn with the same loadout and a new route after a fixed "\
                                + "amount of time."
            for level, newBounties in validBounties.items():
                if newBounties:
                    embed.add_field(
                        name=f"Level {level}",
                        value=", ".join([(await b.criminal).name for b in newBounties]))
        else:
            embed = None

        return {"embed": embed, "content": "‎"}


    async def updateEscapedBountiesMessage(self, bbc: AnyBountyBoardChannel, ignoredBounties: Optional[Tuple[bounty.AnyBounty, ...]] = None):
        """Rebuild the escaped bounties message with new details of any escaped bounties
        """
        ignoredBounties = ignoredBounties or ()
        if bbc.escapedBountiesMessageId is not None:
            kw = await self.makeEscapedBountiesMsgKwargs(bbc, ignoredBounties=ignoredBounties)
            await self.editMessageWithRetry(bbc, self.escapedBountiesMsgRef(bbc),
                                            "escaped bounties", logUrls=True,
                                            **kw)
        if bbc.escapedBountiesMessageId is None:
            await self.rebuild(bbc)


    async def _sendNoBountiesMessage(self, bbc: AnyBountyBoardChannel):
        """Construct and send a 'no active bounties' message to the channel, then save the message ID.
        Does not validate whether now is an appropriate time to send the message.
        """
        m = await self.sendMessageWithRetry(bbc, f"no bounties {await self.guildAndChannelMeta(bbc)}",
                                            embed=BountyBoardListingFormatter.NO_BOUNTIES_EMBED)
        if m is not None:
            bbc.noBountiesMessageId = m.id

        return m


    async def _sendBountyMsg(self, bbc: AnyBountyBoardChannel, b: bounty.AnyBounty):
        """Construct and send a bounty listing message to the channel, then save the message ID.
        Does not validate whether now is an appropriate time to send the message.
        """
        msg = await self.sendMessageWithRetry(bbc,
                                              f"bounty listing: {(await b.criminal).name} "
                                                + await self.guildAndChannelMeta(bbc),
                                              "",
                                              embed=await BountyBoardListingFormatter.makeBountyEmbed(self.client, b))
        if msg is not None:
            listing = self.makeListing(bbc, msg, b)
            await bbc.addListing(listing)
        
        return msg


    async def rebuild(self, bbc: AnyBountyBoardChannel, logUrls: bool = True):
        """Completely rebuild all messages on the board, deleting existing messages if known.

        :param logUrls: Whether to include message jump urls in logs (Default True)
        :type logUrls: bool
        """
        tasks = asyncUtil.Parallel()
        div = await bbc.division
        divEmpty = await self.divisionService.isEmpty(div, includeEscaped=False)

        if bbc.escapedBountiesMessageId is not None:
            tasks.add(self.deleteMessageWithRetry(bbc,
                self.escapedBountiesMsgRef(bbc),
                await self._prependJumpUrl(bbc, bbc.escapedBountiesMessageId, logUrls, "escaped bounties")))

        if bbc.noBountiesMessageId is not None:
            tasks.add(self.deleteMessageWithRetry(bbc,
                self.noBountiesMsgRef(bbc),
                await self._prependJumpUrl(bbc, bbc.noBountiesMessageId, logUrls, "no bounties")))

        for crim, listing in (await bbc.listings).items():
            tasks.add(self.deleteMessageWithRetry(bbc,
                self.messageRef(bbc, listing.messageId),
                await self._prependJumpUrl(bbc, listing.messageId, logUrls, f"bounty listing for {crim}")))

        await tasks.wait()
        tasks.logExceptions(LogCategory.bountyBoards)
        tasks.clear()

        channelMeta = await self.guildAndChannelMeta(bbc)
        escapedMsg = await self.sendMessageWithRetry(bbc, f"escaped bounties {channelMeta}",
                                                     **await self.makeEscapedBountiesMsgKwargs(bbc))
        
        if escapedMsg is not None:
            bbc.escapedBountiesMessageId = escapedMsg.id

        if divEmpty:
            noBountiesMsg = await self.sendMessageWithRetry(bbc, f"no bounties {channelMeta}",
                                                            embed=BountyBoardListingFormatter.NO_BOUNTIES_EMBED)
            if noBountiesMsg is not None:
                bbc.noBountiesMessageId = noBountiesMsg.id

        else:
            for bounty in await self.divisionService.activeBounties(div):
                tasks.add(self._sendBountyMsg(bbc, bounty))

        await tasks.wait()
        tasks.logExceptions(LogCategory.bountyBoards)

        if divEmpty:
            (await bbc.listings).clear()

        elif bbc.noBountiesMessageId is not None:
            bbc.noBountiesMessageId = None


    async def addBounty(self, bbc: AnyBountyBoardChannel, bounty: bounty.AnyBounty, message: Message, logUrls: bool = True):
        """Treat the given message as a listing for the given bounty, and store it in the database.
        If the BBC was previously empty, remove the empty bounty board message if one exists.
        If a HTTP error is thrown when attempting to remove the empty board message,
        wait and retry the removal for the number of times defined in cfg

        :param Bounty bounty: The bounty to associate with the given message
        :param discord.Message message: The message acting as a listing for the given bounty
        :param logUrls: Whether to generate a jump URL, or prepend the ID instead
        """
        removeMsg = False
        if await bbc.isEmpty():
            removeMsg = True

        if await bbc.hasMessageForBounty(bounty):
            raise KeyError("BNTY_BRD_CH-ADD-BNTY_EXSTS: Attempted to add a bounty to a bountyboardchannel, " \
                            + "but the bounty is already listed")
        
        await bbc.addListing(self.makeListing(bbc, message, bounty))

        if removeMsg and bbc.noBountiesMessageId is not None:
            await self.deleteMessageWithRetry(bbc, self.noBountiesMsgRef(bbc),
                                         await self._prependJumpUrl(bbc, bbc.noBountiesMessageId, logUrls, "no bounties"))


    async def removeCriminal(self, bbc: AnyBountyBoardChannel, criminal: Union[criminal.AnyCriminal, int]):
        """Remove the listing message stored for the given criminal from the database,
        and delete its associated message from discord.
        
        If the BBC is now empty, send an empty bounty board message.
        If a HTTP error is thrown when sending the empty BBC message,
        wait and retry the removal for the number of times defined in cfg

        :param Criminal criminal: The criminal whose listing should be removed from the database
        :raise KeyError: If the database does not store a listing for the given criminal
        """
        if not await bbc.hasMessageForCriminal(criminal):
            raise KeyError("BNTY_BRD_CH-REM-BNTY_NOT_EXST: Attempted to remove a criminal from a bountyboardchannel, " \
                            + "but the criminal is not listed")
        
        crimId = criminal if isinstance(criminal, int) else criminal.id
        await self.deleteMessageWithRetry(bbc, self.messageRef(bbc, (await bbc.listings)[crimId].messageId), f"crimil: {crimId}")
        del (await bbc.listings)[crimId]

        if await bbc.isEmpty():
            await self._sendNoBountiesMessage(bbc)


    async def removeBounty(self, bbc: AnyBountyBoardChannel, bounty: bounty.AnyBounty):
        """Remove the listing message stored for the given bounty from the database. 
        his does not attempt to delete the message from discord.

        If the BBC is now empty, send an empty bounty board message.
        If a HTTP error is thrown when sending the empty BBC message,
        wait and retry the removal for the number of times defined in cfg

        :param Bounty bounty: The bounty whose listing should be removed from the database
        :raise KeyError: If the database does not store a listing for the given bounty
        """
        await self.removeCriminal(bbc, bounty.criminalId)


    async def updateBountyMessage(self, bbc: AnyBountyBoardChannel, bounty: bounty.AnyBounty):
        """Update the embed for the listing associated with the given bounty.
        This includes newly checked and near-correct systems along the route.
        If a HTTP error is thrown when updating the listing, wait and retry the edit for the number of times defined in cfg

        :param Bounty bounty: The bounty whose listing should be updated
        :raise KeyError: If the database does not store a listing for the given bounty
        """
        if not await bbc.hasMessageForBounty(bounty):
            raise KeyError("BNTY_BRD_CH-UPD-BNTY_NOT_EXST: " \
                            + "Attempted to update a BBC message for a criminal that is not listed")

        m = await self.messageRef(bbc, (await bbc.listings)[bounty.criminalId].messageId).fetch()
        await self.editMessageWithRetry(bbc, m, f"bounty: {bounty.criminalId}",
                                        content=m.content, embed=await BountyBoardListingFormatter.makeBountyEmbed(self.client, bounty))


    async def clear(self, bbc: AnyBountyBoardChannel):
        """Clear all bounty listings on the board.
        """
        clearTasks = asyncUtil.Parallel()
        for crimId in (await bbc.listings).keys():
            clearTasks.add(self.removeCriminal(bbc, crimId))
        if clearTasks:
            await clearTasks.wait()
            clearTasks.logExceptions(LogCategory.bountyBoards, "bountyBoardChannel", "clear")
            await self.updateEscapedBountiesMessage(bbc)


    async def makeBountyBoardChannelMessage(self, bounty: bounty.AnyBounty, msg: str = "", embed: Optional[Embed] = None) -> Message:
        """Create a new bountyBoardChannel listing for the given bounty, in the given guild.
        guild must own a bountyBoardChannel.

        :param bounty.Bounty bounty: The bounty for which to create a listing
        :param str msg: The text to display in the listing message content (Default "")
        :param discord.Embed embed: The embed to display in the listing message - this will be removed immediately in place
                                    of the embed generated during bountyBoardChannel.updateBountyMessage,
                                    so is only really useful in case updateBountyMessage fails. (Default None)
        :return: The new discord message containing the BBC listing
        :rtype: discord.Message
        :raise ValueError: If guild does not own a bountyBoardChannel
        """
        if not self.hasBountyBoardChannels:
            raise ValueError("The requested BasedGuild has no bountyBoardChannel")
        
        # Casting here because division.bountyBoardChannel is guaranteed for every division, if the guild has hasBountyBoardChannels as True
        bbc = cast(bountyBoardChannel.BountyBoardChannel, bounty.division.bountyBoardChannel)
        bountyListing = await bbc.channel.send(msg, embed=embed if embed is not None else MISSING)
        await bbc.addBounty(bounty, bountyListing)
        await bbc.updateBountyMessage(bounty)
        return bountyListing


    async def removeBountyBoardChannelMessage(self, bounty: bounty.Bounty):
        """Remove guild's bountyBoardChannel listing for bounty.

        :param bounty bounty: The bounty whose BBC listing should be removed
        :raise ValueError: If guild does not own a BBC
        :raise KeyError: If the guild's BBC does not have a listing for bounty
        """
        if not self.hasBountyBoardChannels:
            raise ValueError("The requested BasedGuild has no bountyBoardChannel")

        # Casting here because division.bountyBoardChannel is guaranteed for every division, if the guild has hasBountyBoardChannels as True
        bbc = cast(bountyBoardChannel.BountyBoardChannel, bounty.division.bountyBoardChannel)
        if bbc.hasMessageForBounty(bounty):
            try:
                await bbc.getMessageForBounty(bounty).delete()
            except Forbidden:
                botState.client.logger.log("Main", "rmBBCMsg",
                                    "Forbidden exception thrown when removing bounty listing message for criminal: " \
                                    + bounty.criminal.name, category=LogCategory.bountyBoards, eventType="RM_LISTING-FORBIDDENERR")
            except NotFound:
                botState.client.logger.log("Main", "rmBBCMsg",
                                    "Bounty listing message no longer exists, BBC entry removed: " + bounty.criminal.name,
                                    category=LogCategory.bountyBoards, eventType="RM_LISTING-NOT_FOUND")
            except HTTPException:
                botState.client.logger.log("Main", "rmBBCMsg",
                                    "HTTPException thrown when removing bounty listing message for criminal: " \
                                    + bounty.criminal.name, category=LogCategory.bountyBoards, eventType="RM_LISTING-HTTPERR")
            await bbc.removeBounty(bounty)
        else:
            raise KeyError("The requested BasedGuild (" + str(self.id) \
                            + ") does not have a bountyBoardChannel listing for the given bounty: " + bounty.criminal.name)


    async def updateBountyBoardChannel(self, bounty: bounty.Bounty, bountyComplete: bool = False):
        """Update the BBC listing for the given bounty in the given server.

        :param bounty bounty: The bounty whose listings should be updated
        :param bool bountyComplete: Whether or not the bounty has now been completed.
                                    When True, bounty listings will be removed rather than updated. (Default False)
        """
        if self.hasBountyBoardChannels:
            # Casting here because division.bountyBoardChannel is guaranteed for every division, if the guild has hasBountyBoardChannels as True
            bbc = cast(bountyBoardChannel.BountyBoardChannel, bounty.division.bountyBoardChannel)
            if bountyComplete:
                if bbc.hasMessageForBounty(bounty):
                    await self.removeBountyBoardChannelMessage(bounty)
            else:
                if not bbc.hasMessageForBounty(bounty):
                    await self.makeBountyBoardChannelMessage(bounty, "A new bounty is now available from **" \
                                                                    + bounty.faction.title() + "** central command:")
                else:
                    await bbc.updateBountyMessage(bounty)
                    