from typing import Dict, Optional, Any, Union
from typing_extensions import Never

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey

import discord
from discord import Client
from discord import TextChannel

from ._base import Base
from ...baseClasses.serializable import SerializesToType
from ...database.tables import TableNames
from ...database.constants import GameChannelType
from ...lib.discordUtil import LazyChannel

class GuildHasGameChannel(Base):
    guildId: Mapped[int] = mapped_column(ForeignKey(f"{TableNames.Guild}.id"))
    gameChannelType: Mapped[GameChannelType]
    channelId: Mapped[int]


class GameChannels(SerializesToType[Dict[str, Optional[int]]]):
    def __init__(self, channelIds: Dict[GameChannelType, int], guildId: int):
        self.guildId = guildId
        self.channelIds = channelIds


    def __contains__(self, item: GameChannelType) -> bool:
        return item in self.channelIds

    
    def getId(self, channelType: GameChannelType) -> Optional[int]:
        return self.channelIds.get(channelType, None)
    
    
    def get(self, client: Client, channelType: GameChannelType) -> Optional[LazyChannel]:
        c = self.channelIds.get(channelType, None)
        return None if c is None else \
            LazyChannel(client, c, guildId=self.guildId, type=discord.ChannelType.text)
    

    def set(self, channelType: GameChannelType, channelOrId: Optional[Union[TextChannel, int]]):
        if channelOrId is None:
            self.remove(channelType)
        else:
            self.channelIds[channelType] = channelOrId if isinstance(channelOrId, int) else channelOrId.id
            

    def remove(self, channelType: GameChannelType):
        self.channelIds.pop(channelType, None)


    @property
    def bountyPlay(self):
        return self.getId(GameChannelType.BountyPlay)


    @bountyPlay.setter
    def bountyPlay(self, v: Optional[Union[int, TextChannel]]):
        self.set(GameChannelType.BountyPlay, v)


    @property
    def announcements(self):
        return self.getId(GameChannelType.Announcements)


    @announcements.setter
    def announcements(self, v: Optional[Union[int, TextChannel]]):
        self.set(GameChannelType.Announcements, v)
    
        
    @property
    def renders(self):
        return self.getId(GameChannelType.Renders)


    @renders.setter
    def renders(self, v: Optional[Union[int, TextChannel]]):
        self.set(GameChannelType.Renders, v)


    async def serialize(self, **kwargs: Any) -> Dict[str, Optional[int]]:
        return {k.name: self.channelIds[k] for k in GameChannelType if k in self.channelIds}

    
    @classmethod
    async def deserialize(cls, data: Dict[str, Optional[int]], **kwargs: Any) -> Never:
        raise NotImplementedError()
    
    
    @classmethod
    async def deserializeIds(cls, data: Dict[str, Optional[int]]) -> Dict[GameChannelType, int]:
        ids: Dict[GameChannelType, int] = {}
        for k, v in data.items():
            if v is None: continue
            channelType = GameChannelType.fromStr(k)
            if channelType is None:
                continue
            ids[channelType] = v
        return ids
