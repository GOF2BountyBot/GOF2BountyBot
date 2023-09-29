from typing import Dict, Literal, TypeVar, Union, cast

from sqlalchemy.orm import Mapped, mapped_column

from .... import lib
from ....lib.gameMaths import topThreeItemSpawnRates
from ....lib.stringUtil import formattedAdditiveAndOrMultiplierOrNone, formatMultiplier, formatAdditive
from ....baseClasses.embedFillable import embedField
from ....cfg import bbData
from .moduleItem_json import SerializedModuleItemUnion
from ..base.item_storeable import itemType, StoreableItemType
from ..base.item import Item
from ...base.workshopable import Workshopable

AdditiveModifierName = Literal["armour", "cargo", "handling", "shield"]
MultiplicativeModifierName = Literal["armourMultiplier", "cargoMultiplier", "handlingMultiplier", "shieldMultiplier", "dpsMultiplier"]

TSchema = TypeVar("TSchema", bound=SerializedModuleItemUnion)


@itemType(StoreableItemType.module)
class ModuleItem(Item[TSchema], Workshopable[TSchema]):
    """An equippable item, providing ships with various stat perks and new functionality.
    All, none, or any combination of a moduleItem's attributes may be populated.

    :var armour: Provides an extra layer of health points ships must fight through before they can damage the ship's hull
    :vartype armour: int
    :var armourMultiplier: A percentage multiplier applied to the capacity of the ship's already active armour
    :vartype armourMultiplier: float
    :var shield: Provides another extra layer of health points ships must fight through before they can damage the ship's hull
    :vartype shield: int
    :var shieldMultiplier: A percentage multiplier applied to the capacity of the ship's already active shield
    :vartype shieldMultiplier: float
    :var dpsMultiplier: A percentage multiplier applied to the dps of all primary weapons equipped on the ship
    :vartype dpsMultiplier: float
    :var cargo: An additive increase to the amount of storage space available on the ship
    :vartype cargo: int
    :var cargoMultiplier: A multiplicative increase to the amount of storage space available on the ship
    :vartype cargoMultiplier: float
    :var handling: Provides an additive boost to the driveability of a ship (controls sensitivity)
    :vartype handling: int
    :var handlingMultiplier: A percentage multiplier applied to the ship's base handling
    :vartype handlingMultiplier: float
    """
    armour: Mapped[int] = mapped_column(default=0)
    armourMultiplier: Mapped[float] = mapped_column(default=1.0)
    shield: Mapped[int] = mapped_column(default=0)
    shieldMultiplier: Mapped[float] = mapped_column(default=1.0)
    dpsMultiplier: Mapped[float] = mapped_column(default=1.0)
    cargo: Mapped[int] = mapped_column(default=0)
    cargoMultiplier: Mapped[float] = mapped_column(default=1.0)
    handling: Mapped[int] = mapped_column(default=0)
    handlingMultiplier: Mapped[float] = mapped_column(default=1.0)
    value: Mapped[int]

#region embed fields

    @embedField("Armour", hideWhenNone=True)
    def formattedArmour(self): return formattedAdditiveAndOrMultiplierOrNone(self.armour, self.armourMultiplier)
    
    @embedField("Shield", hideWhenNone=True)
    def formattedShield(self): return formattedAdditiveAndOrMultiplierOrNone(self.shield, self.shieldMultiplier)

    @embedField("DPS", hideWhenNone=True)
    def formattedDPS(self): return None if self.dpsMultiplier is None else formatMultiplier(self.dpsMultiplier)

    @embedField("Cargo", hideWhenNone=True)
    def formattedCargo(self): return formattedAdditiveAndOrMultiplierOrNone(self.cargo, self.cargoMultiplier)

    @embedField("Handling", hideWhenNone=True)
    def formattedHandling(self): return formattedAdditiveAndOrMultiplierOrNone(self.handling, self.handlingMultiplier)
    
    @embedField("BB Shop Spawn Rate", hideWhenNone=True)
    def formattedShopSpawnRate(self): return topThreeItemSpawnRates(self.techLevel, bbData.moduleObjsByTL)

#endregion

    def _multiplierStats(self) -> Dict[MultiplicativeModifierName, float]:
        return {
            "armourMultiplier": self.armourMultiplier,
            "cargoMultiplier": self.cargoMultiplier,
            "handlingMultiplier": self.handlingMultiplier,
            "shieldMultiplier": self.shieldMultiplier,
            "dpsMultiplier": self.dpsMultiplier
        }


    def _additiveStats(self) -> Dict[AdditiveModifierName, int]:
        return {
            "armour": self.armour,
            "cargo": self.cargo,
            "handling": self.handling,
            "shield": self.shield
        }
    

    async def getValue(self) -> int:
        return self.value
    

    def statsStringShort(self) -> str:
        """Summarise all effects of this module as a string.
        This method should be overriden in any modules that implement custom behaviour, outside of simple stat boosts.

        :return: A string summarising the effects of this module when equipped to a ship
        :rtype: str
        """
        additiveStats = self._additiveStats()
        multiplierStats = self._multiplierStats()

        additiveStrs = (statName + ": " + formatAdditive(stat)
                            for statName, stat in additiveStats.items() if stat != 0)
        
        multiplierStrs = (statName + ": " + formatMultiplier(stat)
                            for statName, stat in multiplierStats.items() if stat != 1)
        
        statsStr = "*" + ", ".join(tuple(additiveStrs) + tuple(multiplierStrs))

        return statsStr if len(statsStr) > 1 else "*No effect*"


    async def serialize(self, saveType: bool = True, **kwargs) -> SerializedModuleItemUnion:
        """Serialize this moduleItem into dictionary format, for saving to file.
        This method should be overriden and used as a base in any modules that implement
        custom behaviour, outside of simple stat boosts.
        For an example of using this serialize implementation as a base for an overridden implementation,
        please see a moduleItem class (e.g MiningDrillModule.py)

        :param bool saveType: When true, include the string name of the object type in the output.
        :return: A dictionary containing all information needed to reconstruct this module.
        :rtype: dict
        """
        itemDict = cast(SerializedModuleItemUnion, await super().serialize(saveType=saveType, **kwargs))

        additiveStats = self._additiveStats()
        multiplierStats = self._multiplierStats()

        for statName, stat in additiveStats.items():
            if stat != 0:
                itemDict[statName] = stat

        for statName, stat in multiplierStats.items():
            if stat != 1:
                itemDict[statName] = stat

        return itemDict


    @classmethod
    async def deserialize(cls, moduleDict: SerializedModuleItemUnion, **kwargs):
        """Factory function constructing a new moduleItem object from a dictionary serialised
        representation - the opposite of moduleItem.serialize. This generic module factory function is unlikely
        to ever be called, your module type-specific deserialize should be used instead. Except of course, in the
        case of custom-spawned, custom-typed modules which do not correspond to a BountyBot-known module type.

        :param dict moduleDict: A dictionary containing all information needed to construct the desired moduleItem
        :return: A new moduleItem object as described in moduleDict
        :rtype: moduleItem
        """
        if "emoji" in moduleDict:
            e = await lib.emojis.BasedEmoji.deserialize(moduleDict["emoji"])
        else:
            e = lib.emojis.BasedEmoji.EMPTY
        return cls(**cls._makeDefaults(moduleDict, ignores=("type",), emoji=e))
