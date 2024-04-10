from typing import Any, TypeVar, Dict, Optional, Union, cast

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, attribute_keyed_dict
from sqlalchemy import ForeignKey
from sqlalchemy.ext.asyncio import AsyncAttrs

from . import bounty, bountyDivision, bountyBoardChannelListing
from ...baseClasses.serializable import SerializesToSchema
from .bountyBoardChannel_json import SerializedBountyBoardChannel
from ..bounties import criminal
from ...database.tables import TableNames

TSchema = TypeVar("TSchema", bound=SerializedBountyBoardChannel)


class Base(DeclarativeBase, AsyncAttrs):
    pass


class BountyBoardChannel(Base, SerializesToSchema[TSchema]):
    """A channel which stores a continuously updating listing message for every active bounty.

    :var listings: A mapping from criminal ID to listing message ID
    :vartype listings: dict[int, int]
    :var int channelId: The discord channel ID  where this BBC is active
    :var int noBountiesMsgId: The id of the message indicating that the BBC is empty, if one exists
    :var int escapedBountiesMsgId: The id of the message listing all escaped bounties, if one exists
    :var int divisionId: The division to which this channel belongs
    """
    __tablename__ = TableNames.BountyBoardChannel.value

    divisionId: Mapped[int] = mapped_column(ForeignKey(f"{TableNames.BountyDivision}.id"))
    _division: Mapped["bountyDivision.AnyBountyDivision"] = relationship()
    noBountiesMessageId: Mapped[Optional[int]]
    escapedBountiesMessageId: Mapped[Optional[int]]
    channelId: Mapped[int]
    _listings: Mapped[Dict[int, bountyBoardChannelListing.BountyBoardChannelListing]] = relationship(collection_class=attribute_keyed_dict("messageId"))

    def __init__(self,
                 divisionId: Optional[int] = None,
                 division: Optional["bountyDivision.BountyDivision[Any]"] = None,
                 noBountiesMessageId: Optional[int] = None,
                 escapedBountiesMessageId: Optional[int] = None,
                 channelId: Optional[int] = None,
                 listings: Optional[Dict[int, bountyBoardChannelListing.BountyBoardChannelListing]] = None,
                 **kwargs: Any):
        super().__init__(divisionId=divisionId, division=division, noBountiesMessageId=noBountiesMessageId, escapedBountiesMessageId=escapedBountiesMessageId, channelId=channelId, listings=listings, **kwargs)


    @property
    def id(self):
        """Alias for `channelId`."""
        return self.channelId

    @property
    async def listings(self) -> Dict[int, bountyBoardChannelListing.BountyBoardChannelListing]:
        return await self.awaitable_attrs._listings
    

    @property
    async def division(self) -> bountyDivision.AnyBountyDivision:
        return await self.awaitable_attrs._division
    

    async def addListing(self, listing: bountyBoardChannelListing.BountyBoardChannelListing):
        (await self.listings)[listing.criminalId] = listing


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


    async def isEmpty(self) -> bool:
        """Decide whether this BBC stores any bounty listings

        :return: False if this BBC stores any bounty listings, True otherwise
        :rtype: bool
        """
        return not bool(await self.listings)


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
                                    _listings=data["listings"])


AnyBountyBoardChannel = BountyBoardChannel[SerializedBountyBoardChannel]