from typing import Any, List, Dict, TypeVar, cast

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.orm.collections import attribute_keyed_dict
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.associationproxy import AssociationProxy

from .basedGuild_json import SerializedBasedGuild
from ...baseClasses.serializable import SerializesToSchema
from ..shops import guildShop
from ..bounties import bountyDivision
from ...database.constants import GameChannelType, GuildRoleUserAlertType
from ...database.tables import TableNames
from ._base import Base
from .guildHasGameChannel import GameChannels, GuildHasGameChannel
from .guildHasUserAlertRole import GuildUserAlertRoles, GuildHasUserAlertRole

TSchema = TypeVar("TSchema", bound=SerializedBasedGuild)


class BasedGuild(Base, SerializesToSchema[TSchema]):
    """A class representing a guild in discord, and storing extra bot-specific information about it.

    :var id: The ID of the guild, directly corresponding to a discord guild's ID.
    :vartype id: int
    :var dcGuild: This guild's corresponding discord.Guild object
    :vartype dcGuild: discord.Guild
    :var announceChannel: The discord.channel object for this guild's announcements chanel.
                            None when no announce channel is set for this guild.
    :vartype announceChannel: TextChannel
    :var playChannel: The discord.channel object for this guild's bounty playing chanel.
                        None when no bounty playing channel is set for this guild.
    :vartype playChannel: TextChannel
    :var rendersChannel: The discord.channel which showme ship renders should be limited to. None when no channel is set.
    :vartype rendersChannel: Union[TextChannel, None]
    :var shop: This guild's guildShop object
    :vartype shop: guildShop
    :var alertRoles: A dictionary of user alert IDs to guild role IDs.
    :vartype alertRoles: dict[str, int]
    :var hasBountyBoardChannels: Whether this guild has bounty board channels for each of its divisions or not
    :vartype hasBountyBoardChannel: bool
    :var ownedRoleMenus: The number of ReactionRolePickers present in this guild
    :vartype ownedRoleMenus: int
    :var bounties: This guild's active bounties
    :vartype bounties: BountyDB
    :var bountiesDisabled: Whether or not to disable this guild's bountyDB and bounty spawning
    :vartype bountiesDisabled: bool
    :var shopsDisabled: Whether or not to disable this guild's guildShop and shop refreshing
    :vartype shopsDisabled: bool
    :var hasBountyAlertRoles: True if the guild has alert roles for each of its divisions, False otherwise
    :vartype hasBountyAlertRoles: bool
    """
    __tablename__ = TableNames.Guild

    id: Mapped[int]
    activeRoleMenusCount: Mapped[int] = mapped_column(default=0)
    bountiesDisabled: Mapped[bool] = mapped_column(default=False)
    shopsDisabled: Mapped[bool] = mapped_column(default=False)
    
    #region associations

    _divisions: Mapped[List["bountyDivision.AnyBountyDivision"]] = relationship(back_populates="_guild")
    _divisionShops: Mapped[List["guildShop.TechLeveledShop"]] = relationship(back_populates="_guild")

    _gameChannelAssociations: Mapped[Dict[GameChannelType, GuildHasGameChannel]] = relationship(
        back_populates="guildId",
        # Ignoring sqlalchemy issue, this generic function doesn't accept the generic type parameter as an argument
        collection_class=attribute_keyed_dict("gameChannelType"), # type: ignore[reportUnknownArgumentType]
        cascade="all, delete-orphan",
        lazy="joined"
    )

    def _guildHasChannelFactory(self, gameChannelType: GameChannelType, channelId: int):
        return GuildHasGameChannel(gameChannelType=gameChannelType, channelId=channelId, guildId=self.id)

    _gameChannelsDict: AssociationProxy[Dict[GameChannelType, int]] = association_proxy(
        "_gameChannelAssociations",
        "channelId",
        creator=_guildHasChannelFactory)
    

    _userAlertRoleAssociations: Mapped[Dict[GuildRoleUserAlertType, GuildHasUserAlertRole]] = relationship(
        back_populates="guildId",
        # Ignoring sqlalchemy issue, this generic function doesn't accept the generic type parameter as an argument
        collection_class=attribute_keyed_dict("userAlertType"), # type: ignore[reportUnknownArgumentType]
        cascade="all, delete-orphan",
        lazy="joined"
    )

    def _guildHasUserAlertRoleFactory(self, userAlertType: GuildRoleUserAlertType, roleId: int):
        return GuildHasUserAlertRole(userAlertType=userAlertType, roleId=roleId, guildId=self.id)

    _userAlertRolesDict: AssociationProxy[Dict[GuildRoleUserAlertType, int]] = association_proxy(
        "_userAlertRoleAssociations",
        "roleId",
        creator=_guildHasUserAlertRoleFactory)
    
    #endregion associations

    @property
    def gameChannels(self):
        return GameChannels(self._gameChannelsDict, self.id)
    
    
    @property
    def userAlertRoles(self):
        return GuildUserAlertRoles(self._userAlertRolesDict, self.id)    


    @property
    async def divisions(self):
        if self.bountiesDisabled:
            raise ValueError("This guild has bounties disabled")
        return cast(List[bountyDivision.AnyBountyDivision], await self.awaitable_attrs._divisions)
    

    @property
    async def divisionShops(self):
        if self.shopsDisabled:
            raise ValueError("This guild has shops disabled")
        return cast(List[guildShop.TechLeveledShop], await self.awaitable_attrs._divisionShops)


    async def serialize(self, **kwargs: Any) -> TSchema:
        """Serialize this BasedGuild into dictionary format to be saved to file.

        :return: A dictionary containing all information needed to reconstruct this BasedGuild
        :rtype: dict
        """
        baseData = await super().serialize(**kwargs)
        
        data: SerializedBasedGuild = {
            "id": self.id,
            "alertRoles": await self.userAlertRoles.serialize(**kwargs),
            "bountiesDisabled": self.bountiesDisabled,
            "shopsDisabled": self.shopsDisabled,
            "gameChannels": await self.gameChannels.serialize(**kwargs),
            "activeRoleMenusCount": self.activeRoleMenusCount,
            "divisions": [] if self.bountiesDisabled else
                [await d.serialize(**kwargs) for d in await self.divisions],
            "divisionShops": {} if self.shopsDisabled else
                {shop.divisionId: await shop.serialize(**kwargs) for shop in await self.divisionShops}
        }

        baseData.update(data)

        return baseData


    @classmethod
    async def deserialize(cls, data: TSchema, **kwargs: Any) -> "BasedGuild[TSchema]":
        """Factory function constructing a new BasedGuild object from the information
        in the provided guildDict - the opposite of BasedGuild.serialize

        :param int guildID: The discord ID of the guild
        :param dict guildDict: A dictionary containing all information required to build the BasedGuild object
        :return: A BasedGuild according to the information in guildDict
        :rtype: BasedGuild
        """
        if serializedGameChannels := data.get("gameChannels", None):
            gameChannelIds = await GameChannels.deserializeIds(serializedGameChannels)
        else:
            gameChannelIds = {}

        if serializedUserAlertRoles := data.get("alertRoles", None):
            gameChannelIds = await GuildUserAlertRoles.deserializeIds(serializedUserAlertRoles)
        else:
            gameChannelIds = {}

        if bountiesDisabled := data.get("bountiesDisabled", False):
            divisions = []
        else:
            divisions = [await bountyDivision.BountyDivision.deserialize(v) for v in data.get("divisions", [])]

        if shopsDisabled := data.get("shopsDisabled", False):
            divisionShops = []
        else:
            divisionShops = [await guildShop.TechLeveledShop.deserialize(v) for v in data.get("divisionShops", []).values()]

        return BasedGuild(
            id=data["id"],
            activeRoleMenusCount=data.get("activeRoleMenusCount", 0),
            bountiesDisabled=bountiesDisabled,
            shopsDisabled=shopsDisabled,
            _gameChannelsDict=gameChannelIds,
            _userAlertRolesDict=serializedUserAlertRoles,
            _divisions=divisions,
            _divisionShops=divisionShops,
        )

AnyBasedGuild = BasedGuild[SerializedBasedGuild]