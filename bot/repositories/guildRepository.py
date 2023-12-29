from typing import List, Dict, cast, Awaitable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from discord import Guild, Interaction
from concurrent.futures import ThreadPoolExecutor
import os

from ..entities.guilds import basedGuild
from .snowflakeRepository import SnowflakeRepository
from .. import botState, lib
from .. import lib
from ..logging import LogCategory
from ..baseClasses.serializable import SerializesToType
from ..logging import LogCategory
from ..entities.shops import guildShop


class GuildRepository(SnowflakeRepository["basedGuild.BasedGuild[Any]"]):
    def __init__(self, session: AsyncSession):
        super().__init__(basedGuild.BasedGuild[Any], session)


    def fromInteraction(self, interaction: Interaction) -> Awaitable[basedGuild.BasedGuild]:
        if interaction.guild_id is None:
            raise lib.exceptions.IncorrectInteractionContext("This interaction is only applicable to guild channels")
        return self.getOrThrow(interaction.guild_id)
    