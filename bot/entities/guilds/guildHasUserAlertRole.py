from typing import Dict, Optional, Any
from typing_extensions import Never

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey

from ._base import Base
from ...baseClasses.serializable import SerializesToType
from ...database.tables import TableNames
from ...database.constants import GuildRoleUserAlertType

class GuildHasUserAlertRole(Base):
    guildId: Mapped[int] = mapped_column(ForeignKey(f"{TableNames.Guild}.id"))
    userAlertType: Mapped[GuildRoleUserAlertType]
    roleId: Mapped[int]


class GuildUserAlertRoles(SerializesToType[Dict[str, Optional[int]]]):
    def __init__(self, roleIds: Dict[GuildRoleUserAlertType, int], guildId: int) -> None:
        self.guildId = guildId
        self.roleIds = roleIds


    def __contains__(self, item: GuildRoleUserAlertType) -> bool:
        return item in self.roleIds


    def get(self, alert: GuildRoleUserAlertType) -> Optional[int]:
        """Get the ID of this guild's alerts role for the given alert ID.

        :param str alertID: The alert ID for which the role ID should be fetched
        :return: The ID of the discord role that this guild mentions for the given alert ID.
        :rtype: int
        """
        return self.roleIds.get(alert, None)


    def set(self, alert: GuildRoleUserAlertType, roleId: Optional[int]):
        """Set the ID of this guild's alerts role for the given alert ID.

        :param str alertID: The alert ID for which the role ID should be set
        :param int roleID: The ID of the role which this guild should mention when alerting alertID
        """
        if roleId is None:
            self.remove(alert)
        else:
            self.roleIds[alert] = roleId


    def remove(self, alert: GuildRoleUserAlertType):
        """Remove the stored role and deactivate alerts for the given alertID

        :param str alertID: The alert ID for which the role ID should be removed
        """
        self.roleIds.pop(alert, None)

    
    @property
    def shopRefresh(self):
        return self.get(GuildRoleUserAlertType.shopRefresh)


    @shopRefresh.setter
    def shopRefresh(self, v: Optional[int]):
        self.set(GuildRoleUserAlertType.shopRefresh, v)


    @property
    def botUpdatesMajor(self):
        return self.get(GuildRoleUserAlertType.botUpdatesMajor)


    @botUpdatesMajor.setter
    def botUpdatesMajor(self, v: Optional[int]):
        self.set(GuildRoleUserAlertType.botUpdatesMajor, v)
    
        
    @property
    def botUpdatesMinor(self):
        return self.get(GuildRoleUserAlertType.botUpdatesMinor)


    @botUpdatesMinor.setter
    def botUpdatesMinor(self, v: Optional[int]):
        self.set(GuildRoleUserAlertType.botUpdatesMinor, v)

        
    @property
    def botAnnouncements(self):
        return self.get(GuildRoleUserAlertType.botAnnouncements)


    @botAnnouncements.setter
    def botAnnouncements(self, v: Optional[int]):
        self.set(GuildRoleUserAlertType.botAnnouncements, v)
        

    async def serialize(self, **kwargs: Any) -> Dict[str, Optional[int]]:
        return {k.name: self.roleIds[k] for k in GuildRoleUserAlertType if k in self.roleIds}

    
    @classmethod
    async def deserialize(cls, data: Dict[str, Optional[int]], **kwargs: Any) -> Never:
        raise NotImplementedError()
    

    @classmethod
    async def deserializeIds(cls, data: Dict[str, Optional[int]]) -> Dict[GuildRoleUserAlertType, int]:
        ids: Dict[GuildRoleUserAlertType, int] = {}
        for k, v in data.items():
            if v is None: continue
            channelType = GuildRoleUserAlertType.fromStr(k)
            if channelType is None:
                continue
            ids[channelType] = v
        return ids
