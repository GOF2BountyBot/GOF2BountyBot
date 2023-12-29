from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from .. import botState
from ..reactionMenus import reactionMenu
from ..logging import LogCategory
from discord.abc import Messageable
from ..baseClasses.serializable import SerializesToType

class ReactionMenuRepository(SnowflakeRepository[reactionMenu.ReactionMenu[Any]]):
    def __init__(self, session: AsyncSession):
        super().__init__(reactionMenu.ReactionMenu[Any], session)