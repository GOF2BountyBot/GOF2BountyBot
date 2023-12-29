from __future__ import annotations
from typing import Any, Collection, Generic, List, Optional, Type, TypeVar, cast

from sqlalchemy.orm import DeclarativeBase, Mapped, relationship, mapped_column, composite
from sqlalchemy.ext.asyncio import AsyncAttrs

from . import shipSkin
from ....cfg import bbData
from ....lib.emojis import BasedEmoji
from ....baseClasses.embedFillable import embedField
from ....baseClasses.aliasable import AliasableMixin
from ....baseClasses.wikiEntity import SqlNamedWikiEntity
from ...base.workshopable import Workshopable
from ...base.workshopable_json import AnySerializedWorkshopable
from .shipSpec_json import SerializedShipSpecUnion, TypedSerializedShipSpec
from ....database.constants import ShipSkinRegion
from ....database.tables import TableNames
from ....lib.gameMaths import topThreeItemSpawnRates

TShip = TypeVar("TShip", bound="ShipSpec[Any]")
TSchema = TypeVar("TSchema", bound=SerializedShipSpecUnion)


class Base(DeclarativeBase, AsyncAttrs):
    pass


REGIONS_LIST_SEPARATOR: str = ";"


# Note that while ShipSpec is in the entities.items namespace, a ShipSpec is *not* an 'item'.
class ShipSpec(Base, AliasableMixin[TSchema], Workshopable[TSchema], SqlNamedWikiEntity, Generic[TSchema]):
    """TODO: All of these 'get total' functions could probably be consolidated into a single function,
    # making use of getActives etc

    :var hasNickname: whether or not this ship has a nickname
    :vartype hasNickname: bool
    :var nickname: A custom name for this ship, assigned by the owning player
    :vartype nickname: str
    :var armour: The amount of HP this ship's hull has - the last line of defence before death.
                    # TODO: Should be renamed to hull or similar
    :vartype armour: int
    :var cargo: The amount of storage space for unequipped items and commodities this ship has
    :vartype cargo: int
    :var maxSecondaries: The maximum number of secondary weapons equippable on this ship (not yet implemented)
                            # TODO: Should probably be renamed to maxSecondaries
    :vartype maxSecondaries: int
    :var handling: A measure of this ship's driveability (controls sensitivity)
    :vartype handling: int
    :var maxPrimaries: The maximum number of primary weapons equippable on this ship
    :vartype maxPrimaries: int
    :var maxTurrets: The maximum number of turrets equippable on this ship
    :vartype maxTurrets: int
    :var maxModules: The maximum number of modules equippable on this ship
    :vartype maxModules: int
    :var weapons: A list containing references to all primary weapon objects equipped by this ship. May contain duplicate
                    references to save on memory.
    :vartype weapons: list[PrimaryWeapon]
    :var modules: A list containing references to all module objects equipped by this ship. May contain duplicate references
                    to save on memory.
    :vartype modules: list[moduleItem]
    :var turrets: A list containing references to all turret objects equipped by this ship. May contain duplicate references
                    to save on memory.
    :vartype turrets: list[TurretWeapon]
    :var upgradesApplied: A list containing references to all shipUpgrades objects applied to this ship. May contain
                    duplicate references to save on memory.
    :vartype upgradesApplied: list[shipUpgrade]
    :var skin: The skin applied to this ship
    :vartype skin: ShipSkin
    """
    __tablename__ = TableNames.ShipSpec.value

    id: Mapped[int] = mapped_column(primary_key=True)
    value: Mapped[int]
    manufacturer: Mapped[Optional[str]]
    iconUrl: Mapped[str]
    techLevel: Mapped[int]
    type: Mapped[str]
    armour: Mapped[int]
    cargo: Mapped[int]
    maxSecondaries: Mapped[int]
    handling: Mapped[int]
    maxPrimaries: Mapped[int]
    maxTurrets: Mapped[int]
    maxModules: Mapped[int]
    skinnable: Mapped[bool]
    _skinnableTextureRegions: Mapped[str] = mapped_column("skinnableTextureRegions")
    _emojiUnicode: Mapped[Optional[str]] = mapped_column()
    _emojiId: Mapped[Optional[int]] = mapped_column()
    
    emoji: Mapped[Optional[BasedEmoji]] = composite(_emojiId, _emojiUnicode)

    _compatibleSkins: Mapped[List["shipSkin.ShipSkin"]] = relationship()

    @property
    def skinnableTextureRegions(self) -> Collection[ShipSkinRegion]:
        """The list of autoskin texture regions that this ship has.
        
        This is currently represented in the database by serializing to a string, and so it is not usable in queries.
        The moment this needs to be available in queries, we will need to put it in another table, and update all refernces
        to instead use AsyncAttrs.
        """
        return [ShipSkinRegion(int(i)) for i in self._skinnableTextureRegions.split(REGIONS_LIST_SEPARATOR)]


    @skinnableTextureRegions.setter
    def set_skinnableTextureRegions(self, value: Collection[ShipSkinRegion]):
        self._skinnableTextureRegions = REGIONS_LIST_SEPARATOR.join(str(i) for i in value)


    def __init__(self, name: str, shopSpawnRate: float = 0, **kwargs: Any):
        """
        :param str name: A name to uniquely identify this model of ship.
        :param float shopSpawnRate: A pre-calculated float indicating the highest spawn rate of this ship
                                    (i.e its spawn probability for a shop of the same techLevel) (Default 0)
        """
        super().__init__(name, **kwargs)
        self.shopSpawnRate = shopSpawnRate


    @property
    async def compatibleSkins(self) -> Collection["shipSkin.ShipSkin"]:
        return await self.awaitable_attrs._compatibleSkins

#region embed fields
    @embedField("Armour", hideWhenNone=True)
    def formattedArmour(self): return self.armour

    @embedField("Cargo", hideWhenNone=True)
    def formattedCargo(self): return self.cargo

    @embedField("Handling", hideWhenNone=True)
    def formattedHandling(self): return self.handling

    @embedField("Max Primaries", hideWhenNone=True)
    def formattedMaxPrimaries(self): return self.maxPrimaries

    @embedField("Max Secondaries", hideWhenNone=True)
    def formattedMaxSecondaries(self): return self.maxSecondaries

    @embedField("Max Turrets", hideWhenNone=True)
    def formattedMaxTurrets(self): return self.maxTurrets

    @embedField("Max Modules", hideWhenNone=True)
    def formattedMaxModules(self): return self.maxModules

    @embedField("BB Shop Spawn Rate", hideWhenNone=True)
    def formattedShopSpawnRate(self): return topThreeItemSpawnRates(self.techLevel, bbData.shipKeysByTL) # TODO
    
    @embedField("Compatible Skins", showInline=False)
    async def compatibleSkinsStr(self):
        if not self.skinnable:
            return "This ship is not skinnable"
        
        # Include compatible ship skin names
        compatibleSkins = await self.compatibleSkins
        if compatibleSkins:
            return " • ".join(s.name for s in compatibleSkins)
        
        return "No compatible skins"

#endregion


    async def serialize(self, **kwargs: Any) -> TSchema:
        """Serialize this shipItem into dictionary format, for saving to file. Includes all equiped items and upgrades

        :param bool saveType: When true, include the string name of the object type in the output.
        :return: A dictionary containing all information needed to reconstruct this ship. If the module is builtIn,
                    several statistics are omitted to save space.
        :rtype: dict
        """
        aliasableData = await AliasableMixin[TSchema].serialize(self, **kwargs)
        workshoppableData = cast(AnySerializedWorkshopable, await Workshopable[TSchema].serialize(self, **kwargs))

        data: SerializedShipSpecUnion = {
            **workshoppableData,
            **aliasableData,
            "armour": self.armour,
            "cargo": self.cargo,
            "maxSecondaries": self.maxSecondaries,
            "handling": self.handling,
            "maxPrimaries": self.maxPrimaries,
            "maxTurrets": self.maxTurrets,
            "maxModules": self.maxModules,
            "skinnable": self.skinnable,
            "id": self.id,
            "value": self.value,
            "iconUrl": self.iconUrl,
            "techLevel": self.techLevel,
            "compatibleSkins": [{"name": s.name, "id": s.id} for s in await self.compatibleSkins],
            "skinnableTextureRegions": [{"name": r.name, "id": r.value} for r in self.skinnableTextureRegions]
        }

        if self.manufacturer:
            data["manufacturer"] = self.manufacturer

        if self.emoji is not None:
            data["emoji"] = await self.emoji.serialize(**kwargs)

        if kwargs.get("saveType", False):
            cast(TypedSerializedShipSpec, data)["type"] = type(self).__name__

        return data


    @classmethod
    async def deserialize(cls: Type[TShip], data: SerializedShipSpecUnion, **kwargs: Any) -> TShip:
        """Factory function constructing a new shipItem object from the given dictionary representation -
        the opposite of shipItem.serialize
        As with most other item deserialize functions, all missing information for builtIn ships is replaced
        by data from the corresponding bbData entry.

        :param dict shipDict: A dictionary containing all information required to construct the requested ship
        :return: A new shipItem object as described in shipDict
        :rtype: shipItem
        """
        ignoredData = ("model","compatibleSkins", "normSpec", \
                        "saveDue", "skinnable", "textureRegions", "path", "type",
                        "weapons", "modules", "turrets", "shipUpgrades", "emoji",
                        "numSecondaries", "skin")
        
        compatibleSkins: List[shipSkin.ShipSkin] = []
        skinnableTextureRegions: List[ShipSkinRegion] = []

        if "compatibleSkins" in data:
            for serializedSkin in data["compatibleSkins"]:
                compatibleSkins.append(shipSkin.ShipSkin(-1, id=serializedSkin["id"]))

        if regionsData := data.get("skinnableTextureRegions", None):
            for region in regionsData:
                skinnableTextureRegions.append(ShipSkinRegion(region["id"]))

        if emojiData := data.get("emoji", None):
            emoji = await BasedEmoji.deserialize(emojiData, **kwargs)
        else:
            emoji = BasedEmoji.EMPTY

        return cls(**cls._makeDefaults(data, ignoredData,
                                        emoji=emoji, compatibleSkins=compatibleSkins,
                                        skinnableTextureRegions=skinnableTextureRegions))


AnyShipSpec = ShipSpec[SerializedShipSpecUnion]