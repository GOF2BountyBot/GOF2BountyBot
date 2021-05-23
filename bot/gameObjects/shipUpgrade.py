# Typing imports
from __future__ import annotations

from ..cfg import bbData
from .items import shipItem
from ..baseClasses import serializable
from .. import lib


class ShipUpgrade(serializable.Serializable):
    """A ship upgrade that can be applied to shipItems, but cannot be unapplied again.
    There is no technical reason why a ship upgrade could not be removed, but from a game design perspective,
    it adds extra value and strategy to the decision to apply an upgrade.

    :var wiki: A web page to present as the upgrade's wikipedia article in its info page
    :vartype wiki: str
    :var hasWiki: Whether or not this upgrade's wiki attribute is populated
    :vartype hasWiki: bool
    :var name: The name of the upgrade. This must be unique.
    :vartype name: str
    :var shipToUpgradeValueMult: upgrades do not have a value, their value is calculated as a percentage of the value of the
                                    ship to be applied to. shipToUpgradeValueMult is that percentage multiplier.
    :vartype shipToUpgradeValueMult: float
    :var vendor: The manufacturer of this upgrade.
    :vartype vendor: str
    :var hasVendor: Whether or not this upgrade's vendor attribute is populated
    :vartype hasVendor: bool
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
    :var techLevel: A rating from 1 to 10 of this upgrade's technological advancement. Used as a reference to compare
                    against other ship upgrades.
    :vartype techLevel: int
    :var hasTechLevel: whether or not this ship upgrade has a tech level
    :vartype hasTechLevel: bool
    :var builtIn: Whether this upgrade is built into BountyBot (loaded in from bbData) or was custom spawned.
    :vartype builtIn: bool
    """

    def __init__(self, name : str, shipToUpgradeValueMult : float, armour : int = 0.0, armourMultiplier : float = 1.0,
                    cargo : int = 0, cargoMultiplier : float = 1.0, maxSecondaries : int = 0,
                    maxSecondariesMultiplier : float = 1.0, handling : int = 0, handlingMultiplier : float = 1.0,
                    maxPrimaries : int = 0, maxPrimariesMultiplier : float = 1.0, maxTurrets : int = 0,
                    maxTurretsMultiplier : float = 1.0, maxModules : int = 0, maxModulesMultiplier : float = 1.0,
                    vendor : str = "", wiki : str = "", techLevel : int = -1, builtIn : bool = False):
        """
        :param str name: The name of the upgrade. This must be unique.
        :param float shipToUpgradeValueMult: upgrades do not have a value, their value is calculated as a percentage of the
                                                value of the ship to be applied to. shipToUpgradeValueMult is that
                                                percentage multiplier.
        :param str wiki: A web page to present as the upgrade's wikipedia article in its info page
        :param str vendor: The manufacturer of this upgrade.
        :param int armour: An additive boost to the owning ship's armour
        :param float armourMultiplier: A multiplier to apply to the ship's armour
        :param int cargo: An additive boost to the owning ship's cargo storage
        :param float cargoMultiplier: A multiplier to apply to the ship's cargo storage
        :param int maxSecondaries: An additive boost to the number of secondary weapons equippable by the owning ship
        :param float maxSecondariesMultiplier: A multiplier to apply to the number of secondary weapons equippable by the ship
        :param int handling: An additive boost to the owning ship's handling
        :param float handlingMultiplier: A multiplier to apply to the ship's handling
        :param int maxPrimaries: An additive boost to the number of primary weapons equippable by the owning ship
        :param float maxPrimariesMultiplier: A multiplier to apply to the number of primary weapons equippable by the ship
        :param int maxTurrets: An additive boost to the maximum number of turrets equippable by the owning ship
        :param float maxTurretsMultiplier: A multiplier to apply to the maximum number of turrets equippable by the ship
        :param int maxModules: An additive boost to the number of modules that the owning ship can equip
        :param float maxModulesMultiplier: A multiplier to apply to the number of modules that the ship can equip
        :param int techLevel: A rating from 1 to 10 of this upgrade's technological advancement. Used as a reference to
                                compare against other ship upgrades.
        :param bool builtIn: Whether this upgrade is built into BountyBot (loaded in from bbData) or was custom spawned.
        """
        self.name = name
        self.shipToUpgradeValueMult = shipToUpgradeValueMult
        self.vendor = vendor
        self.hasVendor = vendor != ""

        self.armour = armour
        self.armourMultiplier = armourMultiplier

        self.cargo = cargo
        self.cargoMultiplier = cargoMultiplier

        self.maxSecondaries = maxSecondaries
        self.maxSecondariesMultiplier = maxSecondariesMultiplier

        self.handling = handling
        self.handlingMultiplier = handlingMultiplier

        self.maxPrimaries = maxPrimaries
        self.maxPrimariesMultiplier = maxPrimariesMultiplier

        self.maxTurrets = maxTurrets
        self.maxTurretsMultiplier = maxTurretsMultiplier

        self.maxModules = maxModules
        self.maxModulesMultiplier = maxModulesMultiplier

        self.wiki = wiki
        self.hasWiki = wiki != ""

        self.techLevel = techLevel
        self.hasTechLevel = techLevel != -1

        self.builtIn = builtIn


    def __eq__(self, other : ShipUpgrade) -> bool:
        """Decide whether two ship upgrades are the same, based purely on their name and object type.

        :param shipUpgrade other: The upgrade to compare this one against.
        :return: True if other is a shipUpgrade instance, and shares the same name as this upgrade
        :rtype: bool
        """
        return type(self) == type(other) and self.name == other.name


    def valueForShip(self, ship : shipItem.Ship) -> int:
        """Calculate the value of this ship upgrade, when it is to be applied to the given ship

        :param shipItem ship: The ship that the upgrade is to be applied to
        :return: The number of credits at which this upgrade is valued when being applied to ship
        :rtype: int
        """
        return ship.value * self.shipToUpgradeValueMult


    def toDict(self, **kwargs) -> dict:
        """Serialize this shipUpgrade into a dictionary for saving to file
        Contains all information needed to reconstruct this upgrade. If the upgrade is builtIn,
        this includes only the upgrade name.

        :return: A dictionary-serialized representation of this upgrade
        :rtype: dict
        """

        itemDict = {"name": self.name, "builtIn": self.builtIn}

        if not self.builtIn:
            if self.hasVendor:
                itemDict["vendor"] = self.vendor

            if self.shipToUpgradeValueMult != 1.0:
                itemDict["shipToUpgradeValueMult"] = self.shipToUpgradeValueMult

            if not self.builtIn:
                additiveStats = {   "armour": self.armour, "cargo": self.cargo, "handling": self.handling,
                                    "maxSecondaries": self.maxSecondaries, "maxPrimaries": self.maxPrimaries,
                                    "maxTurrets": self.maxTurrets, "maxModules": self.maxModules}
                multiplierStats = { "armour": self.armourMultiplier, "cargo": self.cargoMultiplier,
                                    "handling": self.handlingMultiplier,
                                    "maxSecondaries": self.maxSecondariesMultiplier,
                                    "maxPrimaries": self.maxPrimariesMultiplier,
                                    "maxTurrets": self.maxTurretsMultiplier, "maxModules": self.maxModulesMultiplier}

                for statName in additiveStats:
                    if additiveStats[statName] != 0:
                        itemDict[statName] = additiveStats[statName]
                for statName in multiplierStats:
                    if multiplierStats[statName] != 1:
                        itemDict[statName] = multiplierStats[statName]

        return itemDict


    def statsStringShort(self) -> str:
        """Get a summary of the effects this upgrade will have on the owning ship, in string format.

        :return: A string summary of the upgrade's effects
        :rtype: str
        """
        additiveStats = {   "Max secondaries": self.maxSecondaries, "Max primaries": self.maxPrimaries,
                            "Max turrets": self.maxTurrets, "Max modules": self.maxModules, "Cargo": self.cargo,
                            "Armour": self.armour, "Handling": self.handling}

        multiplierStats = { "Max secondaries": self.maxSecondariesMultiplier, "Max primaries": self.maxPrimariesMultiplier,
                            "Max turrets": self.maxTurretsMultiplier, "Max modules": self.maxModulesMultiplier,
                            "Cargo": self.cargoMultiplier, "Armour": self.armourMultiplier,
                            "Handling": self.handlingMultiplier}

        statsStr = "*"
        additiveStrs = (statName + ": " + lib.stringTyping.formatAdditive(additiveStats[statName])
                            for statName in additiveStats if additiveStats[statName] != 0)
        multiplierStrs = (statName + ": " + lib.stringTyping.formatMultiplier(multiplierStats[statName])
                            for statName in additiveStats if multiplierStats[statName] != 1)
        statsStr = ", ".join(tuple(additiveStrs) + tuple(multiplierStrs))

        return statsStr if len(statsStr) > 1 else "*No effect*"


    @classmethod
    def fromDict(cls, upgradeDict : dict, **kwargs) -> ShipUpgrade:
        """Factory function reconstructing a shipUpgrade object from its dictionary-serialized representation.
        The opposite of shipUpgrade.toDict
        If the upgrade is builtIn, return a reference to the pre-constructed upgrade object.

        :param dict upgradeDict: A dictionary containing all information needed to produce the required shipUpgrade
        :return: A shipUpgrade object as described by upgradeDict
        :rtype: shipUpgrade
        """
        if upgradeDict["builtIn"]:
            return bbData.builtInUpgradeObjs[upgradeDict["name"]]
        else:
            return ShipUpgrade(upgradeDict["name"], upgradeDict["shipToUpgradeValueMult"],
                                    armour=upgradeDict["armour"] if "armour" in upgradeDict else 0.0,
                                    armourMultiplier=upgradeDict["armourMultiplier"] \
                                                        if "armourMultiplier" in upgradeDict else 1.0,
                                    cargo=upgradeDict["cargo"] if "cargo" in upgradeDict else 0,
                                    cargoMultiplier=upgradeDict["cargoMultiplier"] \
                                                        if "cargoMultiplier" in upgradeDict else 1.0,
                                    maxSecondaries=upgradeDict["maxSecondaries"] if "maxSecondaries" in upgradeDict else 0,
                                    maxSecondariesMultiplier=upgradeDict["maxSecondariesMultiplier"] \
                                                                if "maxSecondariesMultiplier" in upgradeDict else 1.0,
                                    handling=upgradeDict["handling"] if "handling" in upgradeDict else 0,
                                    handlingMultiplier=upgradeDict["handlingMultiplier"] \
                                                        if "handlingMultiplier" in upgradeDict else 1.0,
                                    maxPrimaries=upgradeDict["maxPrimaries"] if "maxPrimaries" in upgradeDict else 0,
                                    maxPrimariesMultiplier=upgradeDict["maxPrimariesMultiplier"] \
                                                            if "maxPrimariesMultiplier" in upgradeDict else 1.0,
                                    maxTurrets=upgradeDict["maxTurrets"] if "maxTurrets" in upgradeDict else 0,
                                    maxTurretsMultiplier=upgradeDict["maxTurretsMultiplier"] \
                                                            if "maxTurretsMultiplier" in upgradeDict else 1.0,
                                    maxModules=upgradeDict["maxModules"] if "maxModules" in upgradeDict else 0,
                                    maxModulesMultiplier=upgradeDict["maxModulesMultiplier"] \
                                                            if "maxModulesMultiplier" in upgradeDict else 1.0,
                                    vendor=upgradeDict["vendor"] if "vendor" in upgradeDict else "",
                                    builtIn=False)
