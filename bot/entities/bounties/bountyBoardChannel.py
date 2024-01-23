from typing import Any, List, Tuple, TypeVar, Dict, Optional, Union, cast

from discord import Embed, Message, Colour, PartialMessage
from discord.message import MessageReference
from discord.enums import ChannelType

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, attribute_keyed_dict
from sqlalchemy import ForeignKey
from sqlalchemy.ext.asyncio import AsyncAttrs

from . import bounty, bountyDivision
from ...baseClasses.serializable import SerializesToSchema
from .bountyBoardChannel_json import SerializedBountyBoardChannel
from ...cfg import bbData, cfg
from ... import client
from ...lib.discordUtil import ImageFile, discordOperationWithRetry, ZWSP, LazyChannel
from ...lib import graphics, asyncUtil, stringUtil
from ..bounties import criminal
from ...logging import LogCategory
from ...database.tables import TableNames


stopwatchIcon = 'https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/twitter/259/stopwatch_23f1.png'
noBountiesEmbed = Embed(description='> Please check back later, or use the `notify bounties` ' \
                        + 'command to be notified when they spawn!', colour=Colour.dark_orange())
noBountiesEmbed.set_author(name='No Bounties Available', icon_url=stopwatchIcon)


async def deleteMessageWithRetry(message: Union[Message, PartialMessage], meta: str, *args: Any, **kwargs: Any):
    """Delete a message

    :param Message message: The message to delete
    :param meta: An extra string to describe the message, only used in exceptions
    :type meta: str
    """
    return await discordOperationWithRetry(message.delete, "delete message", LogCategory.bountyBoards,
                                            "BBC", meta, *args, **kwargs)


TSchema = TypeVar("TSchema", bound=SerializedBountyBoardChannel)


class Base(DeclarativeBase, AsyncAttrs):
    pass


class BountyBoardChannelListing(Base):
    __tablename__ = TableNames.BountyBoardChannelListing.value
    bountyBoardChannelId: Mapped[int] = mapped_column(ForeignKey(f"{TableNames.BountyBoardChannel}.id"), primary_key=True)
    messageId: Mapped[int]
    criminalId: Mapped[int] = mapped_column(ForeignKey(f"{TableNames.Criminal}.id"), primary_key=True)


class BountyBoardChannel(Base, SerializesToSchema[TSchema]):
    """A channel which stores a continuously updating listing message for every active bounty.

    :var listings: A mapping from criminal ID to listing message ID
    :vartype listings: dict[int, int]
    :var int channelId: The discord channel ID  where this BBC is active
    :var int noBountiesMsgId: The id of the message indicating that the BBC is empty, if one exists
    :var int escapedBountiesMsgId: The id of the message listing all escaped bounties, if one exists
    :var int divisionId: The division to which this channel belongs
    """
    __table__ = TableNames.BountyBoardChannel.value

    divisionId: Mapped[int] = mapped_column(ForeignKey(f"{TableNames.BountyDivision}.id"))
    division: Mapped["bountyDivision.AnyBountyDivision"] = relationship()
    noBountiesMessageId: Mapped[Optional[int]]
    escapedBountiesMessageId: Mapped[Optional[int]]
    channelId: Mapped[int]
    _listings: Mapped[Dict[int, BountyBoardChannelListing]] = relationship(
        collection_class=attribute_keyed_dict("messageId"))

    def __init__(self, **kw: Any):
        self._cachedChannel: Optional[LazyChannel] = None
        super().__init__(**kw)


    @property
    async def listings(self) -> Dict[int, BountyBoardChannelListing]:
        return await self.awaitable_attrs._listings
    

    def makeListing(self, msg: Union[int, PartialMessage], crim: Union["criminal.AnyCriminal", int, "bounty.AnyBounty"]) -> BountyBoardChannelListing:
        c = crim if isinstance(crim, int) else crim.id if isinstance(crim, criminal.Criminal) else crim.criminalId
        return BountyBoardChannelListing(
            bountyBoardChannelId=self.channelId,
            messageId=msg if isinstance(msg, int) else msg.id,
            criminalId=c
        ) 


    def _c(self, client: "client.BasedClient") -> LazyChannel:
        """Get a lazy reference to the active channel.
        This is not guaranteed to exist.
        """
        if self._cachedChannel is None:
            self._cachedChannel = LazyChannel(client, self.channelId, guildId=self.division.guildId, type=ChannelType.text)
        return self._cachedChannel
    

    def messageRef(self, client: "client.BasedClient", id: int):
        """Get a reference to a message in the channel.
        This is not guaranteed to exist.
        """
        return self._c(client).partial.get_partial_message(id)


    def escapedBountiesMsgRef(self, client: "client.BasedClient"):
        """Get a reference to the 'escaped bounties' message.
        This is not guaranteed to exist.
        Throws an exception if self.escapedBountiesMessageId is None.
        """
        if self.escapedBountiesMessageId is None:
            raise ValueError("no escaped bounties message set")
        return self.messageRef(client, self.escapedBountiesMessageId)
    

    def noBountiesMsgRef(self, client: "client.BasedClient"):
        """Get a reference to the 'no active bounties' message in the channel.
        This is not guaranteed to exist.
        Throws an exception if self.noBountiesMessageId is None.
        """
        if self.noBountiesMessageId is None:
            raise ValueError("no no bounties message set")
        return self.messageRef(client, self.noBountiesMessageId)


    async def makeBountyEmbed(self, client: "client.BasedClient", bounty: bounty.AnyBounty) -> Embed:
        """Construct a discord.Embed for listing in a bountyBoardChannel

        :param Bounty bounty: The bounty to describe in this embed
        :return: An Embed describing statistics about the passed bounty
        :rtype: discord.Embed
        """
        crim = await bounty.criminal
        embed = Embed(title=crim.name,
                        colour=bbData.factionColours[bounty.faction] if bounty.faction in bbData.factionColours else \
                                bbData.factionColours["neutral"])
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


    def jumpUrl(self, msgId: int) -> str:
        """Construct a jump URL to a message in self.channel

        :param msgId: The ID of the message to construct a URL for
        :type msgId: int
        :return: A jump URL to the identified message
        :rtype: str
        """
        return MessageReference(message_id=msgId, channel_id=self.channelId,
                                guild_id=self.division.guildId,
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


    async def sendMessageWithRetry(self, client: "client.BasedClient", meta: str, *args: Any, **kwargs: Any) -> Optional[Message]:
        """Send a message to self.channel

        :param meta: An extra string to describe the message, only used in exceptions
        :type meta: str
        :return: The message that was created, or None if there was an error
        :rtype: Optional[Message]
        """
        return await self._c(client).withRetry(lambda c: c.send(*args, **kwargs),
                                               "send message", LogCategory.bountyBoards,
                                               "BBC", meta)


    async def editMessageWithRetry(self, message: PartialMessage, meta: str, logUrls: bool = True, *args: Any, **kwargs: Any) -> \
            Optional[Message]:
        """Edit a message. Specify the new content using *args and **kwargs

        :param Message message: The message to edit
        :param meta: An extra string to describe the message, only used in exceptions
        :type meta: str
        :param logUrls: Whether or not to include a jump url to the message in logs (Default True)
        :return: The message after editing, or None if there was an error
        :rtype: Optional[Message]
        """
        meta = self.prependJumpUrl(message.id, logUrls, meta)
        return await discordOperationWithRetry(message.edit, "edit message", LogCategory.bountyBoards,
                                        "BBC", meta, *args, **kwargs)

    
    async def guildAndChannelMeta(self, client: "client.BasedClient") -> str:
        """Construct a string detailing the guild and channel where this BBC lives.

        :return: A string identifying self.channel
        :rtype: str
        """
        c = await self._c(client).fetch()
        return f"g:{c.guild.name}#{c.guild.id} c:{c.name}#{c.id}"


    async def makeEscapedBountiesMsgKwargs(self, ignoredBounties: Optional[Tuple[bounty.Bounty[Any], ...]] = None) -> Dict[str, Union[str, Optional[Embed]]]:
        """Construct an embed listing all escaped bounties in the division.

        :return: A kwargs mapping detailing the content of the BBC's escaped bounties message
        :rtype: Dict[str, Union[str, Embed]]
        """
        ignoredBounties = ignoredBounties or ()
        escaped = await self.division.escapedBounties
        escapedByLevel = {level: [b for b in escaped if b.techLevel == level] for level in self.division.levelRange}
        
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


    async def updateEscapedBountiesMessage(self, client: "client.BasedClient", ignoredBounties: Optional[Tuple[bounty.AnyBounty, ...]] = None):
        """Rebuild the escaped bounties message with new details of any escaped bounties
        """
        ignoredBounties = ignoredBounties or ()
        if self.escapedBountiesMessageId is not None:
            kw = await self.makeEscapedBountiesMsgKwargs(ignoredBounties=ignoredBounties)
            await self.editMessageWithRetry(self.escapedBountiesMsgRef(client),
                                            "escaped bounties", logUrls=True,
                                            **kw)
        if self.escapedBountiesMessageId is None:
            await self.rebuild(client)


    async def _sendNoBountiesMessage(self, client: "client.BasedClient"):
        """Construct and send a 'no active bounties' message to the channel, then save the message ID.
        Does not validate whether now is an appropriate time to send the message.
        """
        m = await self.sendMessageWithRetry(client, f"no bounties {await self.guildAndChannelMeta(client)}",
                                            embed=noBountiesEmbed)
        if m is not None:
            self.noBountiesMessageId = m.id

        return m


    async def _sendBountyMsg(self, client: "client.BasedClient", b: bounty.AnyBounty):
        """Construct and send a bounty listing message to the channel, then save the message ID.
        Does not validate whether now is an appropriate time to send the message.
        """
        msg = await self.sendMessageWithRetry(client,
                                              f"bounty listing: {(await b.criminal).name} "
                                                + await self.guildAndChannelMeta(client),
                                              "",
                                              embed=await self.makeBountyEmbed(client, b))
        if msg is not None:
            (await self.listings)[b.criminalId] = self.makeListing(msg, b)
        
        return msg


    async def rebuild(self, client: "client.BasedClient", logUrls: bool = True):
        """Completely rebuild all messages on the board, deleting existing messages if known.

        :param logUrls: Whether to include message jump urls in logs (Default True)
        :type logUrls: bool
        """
        tasks = asyncUtil.BasicScheduler()
        divEmpty = await self.division.isEmpty(includeEscaped=False)

        if self.escapedBountiesMessageId is not None:
            tasks.add(deleteMessageWithRetry(
                self.escapedBountiesMsgRef(client),
                self.prependJumpUrl(self.escapedBountiesMessageId, logUrls, "escaped bounties")))

        if self.noBountiesMessageId is not None:
            tasks.add(deleteMessageWithRetry(
                self.noBountiesMsgRef(client),
                self.prependJumpUrl(self.noBountiesMessageId, logUrls, "no bounties")))

        for crim, listing in (await self.listings).items():
            tasks.add(deleteMessageWithRetry(
                self.messageRef(client, listing.messageId),
                self.prependJumpUrl(listing.messageId, logUrls, f"bounty listing for {crim}")))

        await tasks.wait()
        tasks.logExceptions(LogCategory.bountyBoards)
        tasks.clear()

        channelMeta = await self.guildAndChannelMeta(client)
        escapedMsg = await self.sendMessageWithRetry(client, f"escaped bounties {channelMeta}",
                                                     **await self.makeEscapedBountiesMsgKwargs())
        
        if escapedMsg is not None:
            self.escapedBountiesMessageId = escapedMsg.id

        if divEmpty:
            noBountiesMsg = await self.sendMessageWithRetry(client, f"no bounties {channelMeta}",
                                                            embed=noBountiesEmbed)
            if noBountiesMsg is not None:
                self.noBountiesMessageId = noBountiesMsg.id

        else:
            for bounty in await self.division.activeBounties:
                tasks.add(self._sendBountyMsg(client, bounty))

        await tasks.wait()
        tasks.logExceptions(LogCategory.bountyBoards)

        if divEmpty:
            (await self.listings).clear()
        elif self.noBountiesMessageId is not None:
            self.noBountiesMessageId = None


    async def hasMessageForCriminal(self, criminal: Union[criminal.AnyCriminal, int]) -> bool:
        """Decide whether this BBC stores a listing for the given criminal 

        :param criminal: The criminal, or the id of the criminal, to check for listing existence
        :type criminal: Union[Criminal, int]
        :return: True if this BBC stores a listing for criminal, False otherwise
        :rtype: bool
        """
        return (criminal if isinstance(criminal, int) else criminal.id) in (await self.listings)


    async def hasMessageForBounty(self, bounty: bounty.AnyBounty) -> bool:
        """Decide whether this BBC stores a listing for the criminal wanted by the given bounty

        :param Bounty bounty: The bounty whose criminal to check for listing existence
        :return: True if this BBC stores a listing for bounty's criminal, False otherwise
        :rtype: bool
        """
        return await self.hasMessageForCriminal(bounty.criminalId)


    async def getMessageForBounty(self, client: "client.BasedClient", bounty: bounty.AnyBounty) -> PartialMessage:
        """Get a reference to the message acting as a listing for the given bounty's criminal

        :param Bounty bounty: The bounty whose criminal to fetch a listing for
        :return: This BBC's message listing the bounty for the given bounty's criminal
        :rtype: discord.PartialMessage
        """
        return self._c(client).partial.get_partial_message((await self.listings)[bounty.criminalId].messageId)


    async def isEmpty(self) -> bool:
        """Decide whether this BBC stores any bounty listings

        :return: False if this BBC stores any bounty listings, True otherwise
        :rtype: bool
        """
        return not bool(await self.listings)


    async def addBounty(self, client: "client.BasedClient", bounty: bounty.AnyBounty, message: Message, logUrls: bool = True):
        """Treat the given message as a listing for the given bounty, and store it in the database.
        If the BBC was previously empty, remove the empty bounty board message if one exists.
        If a HTTP error is thrown when attempting to remove the empty board message,
        wait and retry the removal for the number of times defined in cfg

        :param Bounty bounty: The bounty to associate with the given message
        :param discord.Message message: The message acting as a listing for the given bounty
        :param logUrls: Whether to generate a jump URL, or prepend the ID instead
        """
        removeMsg = False
        if await self.isEmpty():
            removeMsg = True

        if await self.hasMessageForBounty(bounty):
            raise KeyError("BNTY_BRD_CH-ADD-BNTY_EXSTS: Attempted to add a bounty to a bountyboardchannel, " \
                            + "but the bounty is already listed")
        (await self.listings)[bounty.criminalId] = self.makeListing(message, bounty)

        if removeMsg and self.noBountiesMessageId is not None:
            await deleteMessageWithRetry(self.noBountiesMsgRef(client),
                                         self.prependJumpUrl(self.noBountiesMessageId, logUrls, "no bounties"))


    async def removeCriminal(self, client: "client.BasedClient", criminal: Union[criminal.AnyCriminal, int]):
        """Remove the listing message stored for the given criminal from the database,
        and delete its associated message from discord.
        
        If the BBC is now empty, send an empty bounty board message.
        If a HTTP error is thrown when sending the empty BBC message,
        wait and retry the removal for the number of times defined in cfg

        :param Criminal criminal: The criminal whose listing should be removed from the database
        :raise KeyError: If the database does not store a listing for the given criminal
        """
        if not await self.hasMessageForCriminal(criminal):
            raise KeyError("BNTY_BRD_CH-REM-BNTY_NOT_EXST: Attempted to remove a criminal from a bountyboardchannel, " \
                            + "but the criminal is not listed")
        
        crimId = criminal if isinstance(criminal, int) else criminal.id
        await deleteMessageWithRetry(self.messageRef(client, (await self.listings)[crimId].messageId), f"crimil: {crimId}")
        del (await self.listings)[crimId]

        if await self.isEmpty():
            await self._sendNoBountiesMessage(client)


    async def removeBounty(self, client: "client.BasedClient", bounty: bounty.AnyBounty):
        """Remove the listing message stored for the given bounty from the database. 
        his does not attempt to delete the message from discord.

        If the BBC is now empty, send an empty bounty board message.
        If a HTTP error is thrown when sending the empty BBC message,
        wait and retry the removal for the number of times defined in cfg

        :param Bounty bounty: The bounty whose listing should be removed from the database
        :raise KeyError: If the database does not store a listing for the given bounty
        """
        await self.removeCriminal(client, bounty.criminalId)


    async def updateBountyMessage(self, client: "client.BasedClient", bounty: bounty.AnyBounty):
        """Update the embed for the listing associated with the given bounty.
        This includes newly checked and near-correct systems along the route.
        If a HTTP error is thrown when updating the listing, wait and retry the edit for the number of times defined in cfg

        :param Bounty bounty: The bounty whose listing should be updated
        :raise KeyError: If the database does not store a listing for the given bounty
        """
        if not await self.hasMessageForBounty(bounty):
            raise KeyError("BNTY_BRD_CH-UPD-BNTY_NOT_EXST: " \
                            + "Attempted to update a BBC message for a criminal that is not listed")

        m = await self.messageRef(client, (await self.listings)[bounty.criminalId].messageId).fetch()
        await self.editMessageWithRetry(m, f"bounty: {bounty.criminalId}",
                                        content=m.content, embed=await self.makeBountyEmbed(client, bounty))


    async def clear(self, client: "client.BasedClient"):
        """Clear all bounty listings on the board.
        """
        clearTasks = asyncUtil.BasicScheduler()
        for crimId in (await self.listings).keys():
            clearTasks.add(self.removeCriminal(client, crimId))
        if clearTasks:
            await clearTasks.wait()
            clearTasks.logExceptions(LogCategory.bountyBoards, "bountyBoardChannel", "clear")
            await self.updateEscapedBountiesMessage(client)


    async def serialize(self, **kwargs: Any) -> TSchema:
        """Serialise this BBC to dictionary format

        :return: A dictionary containing all data needed to recreate this BBC
        :rtype: dict
        """
        # dict of message id: criminal dict
        listings = {msg.messageId: crim for crim, msg in (await self.listings).items()}
        data: SerializedBountyBoardChannel = {"channel": self.channelId, "listings": listings,
                "division": self.divisionId,
                "noBountiesMsg": self.noBountiesMessageId if self.noBountiesMessageId is not None else -1,
                "escapedBountiesMsg": self.escapedBountiesMessageId if self.escapedBountiesMessageId is not None else -1}
        return cast(TSchema, data)


    @classmethod
    async def deserialize(cls, data: TSchema, **kwargs: Any) -> "BountyBoardChannel[TSchema]":
        """Factory function constructing a new BBC from the information in the provided dictionary
        - the opposite of bountyBoardChannel.serialize

        :param dict BBCDict: a dictionary representation of the BBC, to convert to an object
        :return: The new bountyBoardChannel object
        :rtype: bountyBoardChannel
        """
        return BountyBoardChannel(  channelId=data["channel"],
                                    divisionId=data["division"],
                                    noBountiesMessageId=data.get("noBountiesMsg", -1),
                                    escapedBountiesMessageId=data.get("escapedBountiesMsg", -1),
                                    listings=data["listings"])


AnyBountyBoardChannel = BountyBoardChannel[SerializedBountyBoardChannel]