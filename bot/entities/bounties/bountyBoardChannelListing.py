from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped
from sqlalchemy import ForeignKey

from ...database.tables import TableNames


class Base(DeclarativeBase):
    pass


class BountyBoardChannelListing(Base):
    __tablename__ = TableNames.BountyBoardChannelListing
    bountyBoardChannelId: Mapped[int] = mapped_column(ForeignKey(f"{TableNames.BountyBoardChannel}.id"))
    messageId: Mapped[int]
    criminalId: Mapped[int] = mapped_column(ForeignKey(f"{TableNames.Criminal}.id"))
