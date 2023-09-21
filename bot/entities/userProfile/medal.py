from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from ...database.tables import TableNames
from ...lib.emojis import BasedEmoji

class Base(DeclarativeBase):
    pass


class Medal(Base):
    __tablename__ = TableNames.Medal

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    description: Mapped[str]
    iconUrl: Mapped[str]
    emojiUnicode: Mapped[Optional[str]]
    emojiId: Mapped[Optional[int]]
    wiki: Mapped[Optional[str]]


    @property
    def emoji(self):
        if self.emojiId is not None:
            return BasedEmoji(id=self.emojiId)
            
        if self.emojiUnicode is not None:
            return BasedEmoji(unicode=self.emojiUnicode)
            
        return BasedEmoji.EMPTY
