# Typing imports
from __future__ import annotations
from typing import Dict, Literal, cast

from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase

from .shipSpec import AnyShipSpec
from ....baseClasses.serializable import SerializesToSchema
from ....baseClasses.simpleHash import simpleHash
from ....baseClasses.embedFillable import EmbedFillableMixin, embedField
from ....lib.stringUtil import formattedAdditiveAndOrMultiplierOrNone, formatAdditive, formatMultiplier
from ...base.workshopable import Workshopable
from ...base.workshopable_json import AnySerializedWorkshopable
from ....database.tables import TableNames
from .shipUpgrade_json import SerializedShipUpgradeUnion, SerializedShipUpgrade

AdditiveModifierName = Literal["armour", "cargo", "handling", "maxSecondaries", "maxPrimaries", "maxTurrets", "maxModules"]
MultiplicativeModifierName = Literal["armourMultiplier", "cargoMultiplier", "handlingMultiplier", "maxSecondariesMultiplier", "maxPrimariesMultiplier", "maxTurretsMultiplier", "maxModulesMultiplier"]


class Base(DeclarativeBase):
    pass


'https://stackoverflow.com/a/53519136'
@simpleHash
class ShipUpgrade(Base, Workshopable, EmbedFillableMixin, SerializesToSchema[SerializedShipUpgradeUnion]):
    """A ship upgrade that can be applied to shipItems, but cannot be unapplied again.
    There is no technical reason why a ship upgrade could not be removed, but from a game design perspective,
    it adds extra value and strategy to the decision to apply an upgrade.

    :var name: The name of the upgrade. This must be unique.
    :vartype name: str
    :var shipToUpgradeValueMult: upgrades do not have a value, their value is calculated as a percentage of the value of the
                                    ship to be applied to. shipToUpgradeValueMult is that percentage multiplier.
    :vartype shipToUpgradeValueMult: float
    :var armour: An additive boost to the owning ship's armour
    :vartype armour: int
    :var armourMultiplier: A multiplier to apply to the ship's armour
    :vartype armourMultiplier: float
    :var cargo: An additive boost to the owning ship's cargo storage
    :vartype cargo: int
    :var cargoMultiplier: A multiplier to apply to the ship's cargo storage
    :vartype cargoMultiplier: float
    :var maxSecondaries: An additive boost to the number of secondary weapons equippable by the owning ship
    :vartype maxSecondaries: int
    :var maxSecondariesMultiplier: A multiplier to apply to the number of secondary weapons equippable by the ship
    :vartype maxSecondariesMultiplier: float
    :var handling: An additive boost to the owning ship's handling
    :vartype handling: int
    :var handlingMultiplier: A multiplier to apply to the ship's handling
    :vartype handlingMultiplier: float
    :var maxPrimaries: An additive boost to the number of primary weapons equippable by the owning ship
    :vartype maxPrimaries: int
    :var maxPrimariesMultiplier: A multiplier to apply to the number of primary weapons equippable by the ship
    :vartype maxPrimariesMultiplier: float
    :var maxTurrets: An additive boost to the maximum number of turrets equippable by the owning ship
    :vartype maxTurrets: int
    :var maxTurretsMultiplier: A multiplier to apply to the maximum number of turrets equippable by the ship
    :vartype maxTurretsMultiplier: float
    :var maxModules: An additive boost to the number of modules that the owning ship can equip
    :vartype maxModules: int
    :var maxModulesMultiplier: A multiplier to apply to the number of modules that the ship can equip
    :vartype maxModulesMultiplier: float
    """
    __tablename__ = TableNames.ShipUpgrade.value

    id:                         Mapped[int]
    shipToUpgradeValueMult:     Mapped[float]
    armour:                     Mapped[int] = mapped_column(default=0)
    armourMultiplier:           Mapped[float] = mapped_column(default=1.0)
    cargo:                      Mapped[int] = mapped_column(default=0)
    cargoMultiplier:            Mapped[float] = mapped_column(default=1.0)
    maxSecondaries:             Mapped[int] = mapped_column(default=0)
    maxSecondariesMultiplier:   Mapped[float] = mapped_column(default=1.0)
    handling:                   Mapped[int] = mapped_column(default=0)
    handlingMultiplier:         Mapped[float] = mapped_column(default=1.0)
    maxPrimaries:               Mapped[int] = mapped_column(default=0)
    maxPrimariesMultiplier:     Mapped[float] = mapped_column(default=1.0)
    maxTurrets:                 Mapped[int] = mapped_column(default=0)
    maxTurretsMultiplier:       Mapped[float] = mapped_column(default=1.0)
    maxModules:                 Mapped[int] = mapped_column(default=0)
    maxModulesMultiplier:       Mapped[float] = mapped_column(default=1.0)

#region embed fields

    @embedField("Upgrade Cost", hideWhenNone=True)
    def formattedShipToUpgradeValueMult(self): return f"{self.shipToUpgradeValueMult*100}% of the ship" if self.shipToUpgradeValueMult != 0 else None

    @embedField("Armour", hideWhenNone=True)
    def formattedArmour(self): return formattedAdditiveAndOrMultiplierOrNone(self.armour, self.armourMultiplier)

    @embedField("Cargo", hideWhenNone=True)
    def formattedCargo(self): return formattedAdditiveAndOrMultiplierOrNone(self.cargo, self.cargoMultiplier)

    @embedField("Max Secondaries", hideWhenNone=True)
    def formattedMaxSecondaries(self): return formattedAdditiveAndOrMultiplierOrNone(self.maxSecondaries, self.maxSecondariesMultiplier)

    @embedField("Handling", hideWhenNone=True)
    def formattedHandling(self): return formattedAdditiveAndOrMultiplierOrNone(self.handling, self.handlingMultiplier)

    @embedField("Max Primaries", hideWhenNone=True)
    def formattedMaxPrimaries(self): return formattedAdditiveAndOrMultiplierOrNone(self.maxPrimaries, self.maxPrimariesMultiplier)

    @embedField("Max Turrets", hideWhenNone=True)
    def formattedMaxTurrets(self): return formattedAdditiveAndOrMultiplierOrNone(self.maxTurrets, self.maxTurretsMultiplier)

    @embedField("Max Modules", hideWhenNone=True)
    def formattedMaxModules(self): return formattedAdditiveAndOrMultiplierOrNone(self.maxModules, self.maxModulesMultiplier)

#endregion

    def __eq__(self, other: ShipUpgrade) -> bool:
        """Decide whether two ship upgrades are the same, based purely on their name and object type.

        :param shipUpgrade other: The upgrade to compare this one against.
        :return: True if other is a shipUpgrade instance, and shares the same name as this upgrade
        :rtype: bool
        """
        return type(self) == type(other) and self.name == other.name


    def valueForShip(self, ship: AnyShipSpec) -> int:
        """Calculate the value of this ship upgrade, when it is to be applied to the given ship

        :param ShipSpec ship: The ship that the upgrade is to be applied to
        :return: The number of credits at which this upgrade is valued when being applied to ship
        :rtype: int
        """
        return int(ship.value * self.shipToUpgradeValueMult)


    def _multiplierStats(self) -> Dict[MultiplicativeModifierName, float]:
        return {
            "armourMultiplier": self.armourMultiplier, "cargoMultiplier": self.cargoMultiplier,
            "handlingMultiplier": self.handlingMultiplier,
            "maxSecondariesMultiplier": self.maxSecondariesMultiplier,
            "maxPrimariesMultiplier": self.maxPrimariesMultiplier,
            "maxTurretsMultiplier": self.maxTurretsMultiplier, "maxModulesMultiplier": self.maxModulesMultiplier
        }


    def _additiveStats(self) -> Dict[AdditiveModifierName, int]:
        return {
            "armour": self.armour, "cargo": self.cargo, "handling": self.handling,
            "maxSecondaries": self.maxSecondaries, "maxPrimaries": self.maxPrimaries,
            "maxTurrets": self.maxTurrets, "maxModules": self.maxModules
        }


    def statsStringShort(self) -> str:
        """Get a summary of the effects this upgrade will have on the owning ship, in string format.

        :return: A string summary of the upgrade's effects
        :rtype: str
        """
        additiveStrs = tuple(f"{k}: {formatAdditive(v)}" for k, v in self._additiveStats().items() if v != 0)
        multiplierStrs = tuple(f"{k}: {formatMultiplier(v)}" for k, v in self._multiplierStats().items() if v != 1)
        
        return f'*{ ", ".join(tuple(additiveStrs + multiplierStrs)) }*' \
            if (additiveStrs or multiplierStrs) else "*No effect*"
    

    async def serialize(self, **kwargs) -> SerializedShipUpgradeUnion:
        """Serialize this shipUpgrade into a dictionary for saving to file
        Contains all information needed to reconstruct this upgrade. If the upgrade is builtIn,
        this includes only the upgrade name.

        :return: A dictionary-serialized representation of this upgrade
        :rtype: dict
        """

        baseData = cast(AnySerializedWorkshopable, await super().serialize(**kwargs))

        data: SerializedShipUpgrade = {
            **baseData,
            "shipToUpgradeValueMult": self.shipToUpgradeValueMult
        }

        data["shipToUpgradeValueMult"] = self.shipToUpgradeValueMult

        for k, v in self._additiveStats().items():
            if v != 0:
                data[k] = v

        for k, v in self._multiplierStats().items():
            if v != 1:
                data[k] = v

        return data


    @classmethod
    def deserialize(cls, upgradeDict: SerializedShipUpgradeUnion, **kwargs) -> ShipUpgrade:
        """Factory function reconstructing a shipUpgrade object from its dictionary-serialized representation.
        The opposite of shipUpgrade.serialize
        If the upgrade is builtIn, return a reference to the pre-constructed upgrade object.

        :param dict upgradeDict: A dictionary containing all information needed to produce the required shipUpgrade
        :return: A shipUpgrade object as described by upgradeDict
        :rtype: shipUpgrade
        """
        return ShipUpgrade(**cls._makeDefaults(upgradeDict, ("type",), builtIn=False))
