from __future__ import annotations
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING, cast
from typing_extensions import NotRequired
if TYPE_CHECKING:
    from .modules import moduleItem

from discord import Embed

from .gameItem import GameItem, spawnableItem, BuiltInSerializedGameItem, TypedBuiltInSerializedGameItem
from . import moduleItemFactory
from .modules.moduleItem import SerializedModuleItemUnion
from .weapons.primaryWeapon import PrimaryWeapon
from .weapons.turretWeapon import TurretWeapon
from .weapons.weapon import SerializedWeaponUnion
from .. import shipSkin, shipUpgrade
from ...cfg import cfg, bbData
from ...cfg.bbData import ItemCategory
from ...lib.emojis import BasedEmoji, SerializedBasedEmoji
from ...baseClasses.serializable import SerializesToSchema


class BuiltInSerializedShip(BuiltInSerializedGameItem):
    weapons: NotRequired[List[SerializedWeaponUnion]]
    modules: NotRequired[List[SerializedModuleItemUnion]]
    turrets: NotRequired[List[SerializedWeaponUnion]]
    shipUpgrades: NotRequired[List[shipUpgrade.SerializedShipUpgradeUnion]]
    nickname: NotRequired[str]

class TypedBuiltInSerializedShip(BuiltInSerializedShip, TypedBuiltInSerializedGameItem): pass

class SkinnedBuiltInSerializedShip(BuiltInSerializedShip):
    skin: shipSkin.SerializedShipSkinUnion
    icon: str

class TypedSkinnedBuiltInSerializedShip(SkinnedBuiltInSerializedShip, TypedBuiltInSerializedShip): pass

# Really this should inherit from CustomSerializedGameItem, but that requires techLevel to be present.
# Ships are a special case because their techLevel is calculated dynamically based on value
class CustomSerializedShip(BuiltInSerializedShip):
    armour: int
    cargo: int
    maxSecondaries: int
    handling: int
    maxPrimaries: int
    maxTurrets: int
    maxModules: int
    manufacturer: str
    skinnable: bool
    compatibleSkins: NotRequired[List[str]]
    model: str
    normSpec: str
    saveDue: bool
    shopSpawnRate: float
    textureRegions: int
    value: int
    wiki: str
    manufacturer: str
    icon: str
    emoji: SerializedBasedEmoji
    techLevel: int
    path: str

# Really this should inherit from TypedCustomSerializedGameItem, but that requires techLevel to be present.
# Ships are a special case because their techLevel is calculated dynamically based on value
class TypedCustomSerializedShip(CustomSerializedShip):
    type: str

class SkinnedCustomSerializedShip(CustomSerializedShip):
    skin: shipSkin.SerializedShipSkinUnion
    icon: str

class TypedSkinnedCustomSerializedShip(SkinnedCustomSerializedShip, TypedCustomSerializedShip): pass

BuiltInSerializedShipUnion = Union[BuiltInSerializedShip, TypedBuiltInSerializedShip, SkinnedBuiltInSerializedShip, TypedSkinnedBuiltInSerializedShip]
CustomSerializedShipUnion = Union[CustomSerializedShip, TypedCustomSerializedShip, SkinnedCustomSerializedShip, TypedSkinnedCustomSerializedShip]
SerializedShipUnion = Union[BuiltInSerializedShipUnion, CustomSerializedShipUnion]
SkinnedSerializedShipUnion = Union[SkinnedBuiltInSerializedShip, TypedSkinnedBuiltInSerializedShip, SkinnedCustomSerializedShip, TypedSkinnedCustomSerializedShip]


@spawnableItem
class Ship(GameItem, SerializesToSchema[SerializedShipUnion]):
    """An equippable and customisable ship for use by players and NPCs.

    TODO: All of these 'get total' functions could probably be consolidated into a single function,
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

    def __init__(self, name: str, maxPrimaries: int, maxTurrets: int,
                    maxModules: int, manufacturer: str = "", armour: int = 0,
                    cargo: int = 0, maxSecondaries: int = 0, handling: int = 0,
                    value: int = 0, aliases: List[str] = [], weapons: List[PrimaryWeapon] = [],
                    modules: List[moduleItem.ModuleItem] = [], turrets: List[TurretWeapon] = [],
                    wiki: str = "", upgradesApplied: List[shipUpgrade.ShipUpgrade] = [], nickname: str = "",
                    icon: str = "", emoji: BasedEmoji = BasedEmoji.EMPTY, techLevel: int = -1,
                    shopSpawnRate: float = 0, builtIn: bool = False, skin: Optional["shipSkin.ShipSkin"] = None):
        """
        :param str name: A name to uniquely identify this model of ship.
        :param str nickname: A custom name for this ship, assigned by the owning player
        :param int armour: The amount of HP this ship's hull has - the last line of defence before death. (Default 0)
                            # TODO: Should be renamed to hull or similar
        :param int cargo: The amount of storage space for unequipped items and commodities this ship has (Default 0)
        :param int maxSecondaries: The maximum number of secondary weapons equippable on this ship
                                    (not yet implemented) (Default 0)
        :param int handling: A measure of this ship's driveability (controls sensitivity) (Default 0)
        :param int maxPrimaries: The maximum number of primary weapons equippable on this ship
        :param int maxTurrets: The maximum number of turrets equippable on this ship
        :param int maxModules: The maximum number of modules equippable on this ship
        :param list[PrimaryWeapon] weapons: A list containing references to all primary weapon objects equipped by this ship.
                                            May contain duplicate references to save on memory. (Default [])
        :param list[moduleItem] modules: A list containing references to all module objects equipped by this ship.
                                            May contain duplicate references to save on memory. (Default [])
        :param list[TurretWeapon] turrets: A list containing references to all turret objects equipped by this ship.
                                            May contain duplicate references to save on memory. (Default [])
        :param list[shipUpgrade] upgradesApplied: A list containing references to all shipUpgrades objects applied to this
                                                    ship. May contain duplicate references to save on memory. (Default [])
        :param int value: The number of credits this ship can be bought/sold for at base value at a shop. does not
                            include any modifications or equipped items. (Default 0)
        :param list[str] aliases: Alternative name that can be used to refer to this type of ship (Default [])
        :param str wiki: A web page that is displayed as the wiki page for this ship. (Default "")
        :param str manufacturer: The name of the manufacturer of this ship (Default "")
        :param str icon: A URL pointing to an image to use for this ship's icon (Default "")
        :param BasedEmoji emoji: The emoji to use for this ship's small icon (Default BasedEmoji.EMPTY)
        :param int techLevel: A rating from 1 to 10 of this ship's technical advancement. Used as a rough and arbitrary
                                measure for its effectiveness compared to other ships. (Default -1)
        :param bool builtIn: Whether this is a BountyBot standard ship (loaded in from bbData) or a custom spawned
                                ship (Default False)
        :param float shopSpawnRate: A pre-calculated float indicating the highest spawn rate of this ship
                                    (i.e its spawn probability for a shop of the same techLevel) (Default 0)
        :param ShipSkin skin: The skin applied to the ship
        """
        super(Ship, self).__init__(name, aliases, value=value, wiki=wiki, manufacturer=manufacturer, icon=icon, emoji=emoji,
                                        techLevel=techLevel, builtIn=builtIn)

        # TODO: Log to bbLogger in these cases
        if len(weapons) > maxPrimaries:
            ValueError("passed more weapons than can be stored on this ship - maxPrimaries")
        if len(modules) > maxModules:
            ValueError("passed more modules than can be stored on this ship - maxModules")
        if len(turrets) > maxTurrets:
            ValueError("passed more turrets than can be stored on this ship - maxTurrets")

        # if self.name in bbData.builtInShipData:
        #     self.shopSpawnRate = bbData.shipKeySpawnRates[self.name]
        # else:
        #     self.shopSpawnRate = 0

        self.armour = armour
        self.cargo = cargo
        self.maxSecondaries = maxSecondaries
        self.handling = handling

        self.maxPrimaries = maxPrimaries
        self.maxTurrets = maxTurrets
        self.maxModules = maxModules

        self.weapons = weapons
        self.modules = modules
        self.turrets = turrets

        self.nickname = ""
        self.hasNickname = False
        if nickname != "":
            self.changeNickname(nickname)

        self.upgradesApplied = upgradesApplied

        self.shopSpawnRate = shopSpawnRate

        self.skin = skin
        self.isSkinned = skin is not None


    def getNumWeaponsEquipped(self) -> int:
        """Fetch the number of weapons this ship currently has equipped

        :return: The number of primary weapons equipped on the ship
        :rtype: int
        """
        return len(self.weapons)


    def canEquipMoreWeapons(self) -> bool:
        """Decide whether or not this ship has any free primary weapon slots

        :return: True if at least one primary weapon slot is free, False otherwise
        :rtype: bool
        """
        return self.getNumWeaponsEquipped() < self.getMaxPrimaries()


    def getNumModulesEquipped(self) -> int:
        """Fetch the number of modules this ship currently has equipped

        :return: The number of modules equipped on the ship
        :rtype: int
        """
        return len(self.modules)


    def canEquipMoreModules(self) -> bool:
        """Decide whether or not this ship has any free module slots

        :return: True if at least one module slot is free, False otherwise
        :rtype: bool
        """
        return self.getNumModulesEquipped() < self.getMaxModules()


    def getNumTurretsEquipped(self) -> int:
        """Fetch the number of turrets this ship currently has equipped

        :return: The number of turrets equipped on the ship
        :rtype: int
        """
        return len(self.turrets)


    def canEquipMoreTurrets(self) -> bool:
        """Decide whether or not this ship has any free turret slots

        :return: True if at least one turret slot is free, False otherwise
        :rtype: bool
        """
        return self.getNumTurretsEquipped() < self.getMaxTurrets()


    def hasWeaponsEquipped(self) -> bool:
        """Decide whether or not this ship has any Weapons equipped

        :return: True if at least one Weapon is equipped on this ship, False otherwise
        :rtype: bool
        """
        return self.getNumWeaponsEquipped() > 0


    def hasModulesEquipped(self) -> bool:
        """Decide whether or not this ship has any Modules equipped

        :return: True if at least one Module is equipped on this ship, False otherwise
        :rtype: bool
        """
        return self.getNumModulesEquipped() > 0


    def hasTurretsEquipped(self) -> bool:
        """Decide whether or not this ship has any Turrets equipped

        :return: True if at least one Turret is equipped on this ship, False otherwise
        :rtype: bool
        """
        return self.getNumTurretsEquipped() > 0


    def equipWeapon(self, weapon: PrimaryWeapon):
        """Equip the given weapon onto the ship

        :param PrimaryWeapon weapon: The weapon object to equip
        :raise OverflowError: If no weapon slots are available on the ship
        """
        if not self.canEquipMoreWeapons():
            raise OverflowError("Attempted to equip a weapon but all weapon slots are full")
        self.weapons.append(weapon)


    def unequipWeaponObj(self, weapon: PrimaryWeapon):
        """Unequip the given weapon object reference from the ship

        :param PrimaryWeapon weapon: The weapon object to unequip
        """
        self.weapons.remove(weapon)


    def unequipWeaponIndex(self, index: int):
        """Unequip a weapon by its index in the weapons array.

        :param int index: The index of the weapon to unequip from the ship
        """
        self.weapons.pop(index)


    def getWeaponAtIndex(self, index: int) -> PrimaryWeapon:
        """Fetch the weapon object equipped at the given index

        :param int index: The index of the weapon object to fetch
        :return: The weapon object equipped at the given index
        :rtype: PrimaryWeapon
        """
        return self.weapons[index]


    def canEquipModuleType(self, moduleType: type) -> bool:
        """Decide whether or not the ship has space for a module of the given type.
        This also accounts for module type limits, for example only allowing players to equip one shield module at a time.

        :param type moduleType: The moduleItem subclass to test for free equip space
        :return: True if at least one module slot is free for the given moduleItem type, False otherwise.
        :rtype: bool
        """
        if moduleType.__name__ in cfg.maxModuleTypeEquips and cfg.maxModuleTypeEquips[moduleType.__name__] != -1:
            numFound = 1
            for equippedModule in self.modules:
                if type(equippedModule) == moduleType:
                    numFound += 1
                    if numFound > cfg.maxModuleTypeEquips[moduleType.__name__]:
                        return False
        return True


    def equipModule(self, module: moduleItem.ModuleItem):
        """Equip the given moduleItem onto the ship.

        :param moduleItem module: The moduleItem object to equip
        :raise OverflowError: When no module slots are free
        :raise ValueError: When the ship already has the maximum number of modules equipped of the given type.
        """
        if not self.canEquipMoreModules():
            raise OverflowError("Attempted to equip a module but all module slots are full")
        if not self.canEquipModuleType(type(module)):
            raise ValueError("Attempted to equip a module of a type that is already at its maximum capacity: " + str(module))

        self.modules.append(module)


    def unequipModuleObj(self, module: moduleItem.ModuleItem):
        """Unequip the given module object reference

        :param moduleItem module: The module to unequip
        """
        self.modules.remove(module)


    def unequipModuleIndex(self, index: int):
        """Unequip the module equipped at the given index in the modules array

        :param int index: The index of the module to unequip
        """
        self.modules.pop(index)


    def getModuleAtIndex(self, index: int) -> moduleItem.ModuleItem:
        """Fetch the moduleItem object reference that is equipped at the given index

        :param int index: The index of the module to fetch
        :return: The module reference equipped at the given index
        :rtype: moduleItem
        """
        return self.modules[index]


    def equipTurret(self, turret: TurretWeapon):
        """Equip the given turret onto the ship

        :param TurretWeapon turret: The turret object to equip
        :raise OverflowError: If no turret slots are available on the ship
        """
        if not self.canEquipMoreTurrets():
            raise OverflowError("Attempted to equip a turret but all turret slots are full")
        self.turrets.append(turret)


    def unequipTurretObj(self, turret: TurretWeapon):
        """Unequip the given turret object reference from the ship

        :param TurretWeapon turret: The turret object to unequip
        """
        self.turrets.remove(turret)


    def unequipTurretIndex(self, index: int):
        """Unequip a turret by its index in the turrets array.

        :param int index: The index of the turret to unequip from the ship
        """
        self.turrets.pop(index)


    def getTurretAtIndex(self, index: int) -> TurretWeapon:
        """Fetch the turret object equipped at the given index

        :param int index: The index of the turret object to fetch
        :return: The turret object equipped at the given index
        :rtype: TurretWeapon
        """
        return self.turrets[index]


    def getDPS(self, shipUpgradesOnly: bool = False) -> float:
        """Get the total DPS provided by the equipped items and upgrades.
        If shipUpgradesOnly is given as True, then only applied shipUpgrades will be included in the calculation.
        This is used to give a 'base' measurement, as ship upgrades cannot be removed and are considered part of the
        ship once applied.

        :param bool shipUpgradesOnly: Whether to include all equipped items, or only the base ship DPS and that granted
                                        by applied shipUpgrades (Default False)
        :return: The ship's total DPS, including bonuses/penalties from ship upgrades (and potentially equipped items)
        :rtype: int
        """
        total = 0
        multiplier = 1
        if not shipUpgradesOnly:
            for weapon in self.weapons:
                total += weapon.dps
            for turret in self.turrets:
                total += turret.dps
            for module in self.modules:
                total += module.dps
                multiplier *= module.dpsMultiplier

        return total * multiplier


    def getShield(self, shipUpgradesOnly: bool = False) -> int:
        """Get the total Shield provided by the equipped items and upgrades.
        If shipUpgradesOnly is given as True, then only applied shipUpgrades will be included in the calculation.
        This is used to give a 'base' measurement, as ship upgrades cannot be removed and are considered part
        of the ship once applied.

        :param bool shipUpgradesOnly: Whether to include all equipped items, or only the base ship Shield and that
                                        granted by applied shipUpgrades (Default False)
        :return: The ship's total Shield, including bonuses/penalties from ship upgrades (and potentially equipped items)
        :rtype: int
        """
        total = 0
        multiplier = 1
        if not shipUpgradesOnly:
            for module in self.modules:
                total += module.shield
                multiplier *= module.shieldMultiplier

        return int(total * multiplier)


    def getArmour(self, shipUpgradesOnly: bool = False) -> int:
        """Get the total Armour provided by the equipped items and upgrades.
        If shipUpgradesOnly is given as True, then only applied shipUpgrades will be included in the calculation.
        This is used to give a 'base' measurement, as ship upgrades cannot be removed and are considered part of the
        ship once applied.

        :param bool shipUpgradesOnly: Whether to include all equipped items, or only the base ship Armour and that
                                        granted by applied shipUpgrades (Default False)
        :return: The ship's total Armour, including bonuses/penalties from ship upgrades (and potentially equipped items)
        :rtype: int
        """
        total = self.armour
        multiplier = 1
        if not shipUpgradesOnly:
            for module in self.modules:
                total += module.armour
                multiplier *= module.armourMultiplier

        for upgrade in self.upgradesApplied:
            total += upgrade.armour
            multiplier *= upgrade.armourMultiplier
        return int(total * multiplier)


    def getCargo(self, shipUpgradesOnly: bool = False) -> int:
        """Get the total Cargo provided by the equipped items and upgrades.
        If shipUpgradesOnly is given as True, then only applied shipUpgrades will be included in the calculation.
        This is used to give a 'base' measurement, as ship upgrades cannot be removed and are considered part of the
        ship once applied.

        :param bool shipUpgradesOnly: Whether to include all equipped items, or only the base ship Cargo and that
                                        granted by applied shipUpgrades (Default False)
        :return: The ship's total Cargo, including bonuses/penalties from ship upgrades (and potentially equipped items)
        :rtype: int
        """
        total = self.cargo
        multiplier = 1
        if not shipUpgradesOnly:
            for module in self.modules:
                total += module.cargo
                multiplier *= module.cargoMultiplier

        for upgrade in self.upgradesApplied:
            total += upgrade.cargo
            multiplier *= upgrade.cargoMultiplier
        return int(total * multiplier)


    def getHandling(self, shipUpgradesOnly: bool = False) -> int:
        """Get the total Handling provided by the equipped items and upgrades.
        If shipUpgradesOnly is given as True, then only applied shipUpgrades will be included in the calculation.
        This is used to give a 'base' measurement, as ship upgrades cannot be removed and are considered part of the
        ship once applied.

        :param bool shipUpgradesOnly: Whether to include all equipped items, or only the base ship Handling and that
                                        granted by applied shipUpgrades (Default False)
        :return: The ship's total Handling, including bonuses/penalties from ship upgrades (and potentially equipped items)
        :rtype: int
        """
        total = self.handling
        multiplier = 1
        if not shipUpgradesOnly:
            for module in self.modules:
                total += module.handling
                multiplier *= module.handlingMultiplier

        for upgrade in self.upgradesApplied:
            total += upgrade.handling
            multiplier *= upgrade.handlingMultiplier
        return int(total * multiplier)


    def getMaxSecondaries(self, shipUpgradesOnly: bool = False) -> int:
        """Get the total maxSecondaries provided by the equipped items and upgrades.
        If shipUpgradesOnly is given as True, then only applied shipUpgrades will be included in the calculation.
        This is used to give a 'base' measurement, as ship upgrades cannot be removed and are considered part of the
        ship once applied.

        :param bool shipUpgradesOnly: Whether to include all equipped items, or only the base ship maxSecondaries and that
                                        granted by applied shipUpgrades (Default False)
        :return: The ship's total maxSecondaries, including bonuses/penalties from ship upgrades
                    (and potentially equipped items)
        :rtype: int
        """
        total = self.maxSecondaries
        multiplier = 1

        for upgrade in self.upgradesApplied:
            total += upgrade.maxSecondaries
            multiplier *= upgrade.maxSecondariesMultiplier
        return int(total * multiplier)


    def getMaxPrimaries(self, shipUpgradesOnly: bool = False) -> int:
        """Get the total MaxPrimaries provided by the equipped items and upgrades.
        If shipUpgradesOnly is given as True, then only applied shipUpgrades will be included in the calculation.
        This is used to give a 'base' measurement, as ship upgrades cannot be removed and are considered part of the
        ship once applied.

        :param bool shipUpgradesOnly: Whether to include all equipped items, or only the base ship MaxPrimaries and
                                        that granted by applied shipUpgrades (Default False)
        :return: The ship's total MaxPrimaries, including bonuses/penalties from ship upgrades
                    (and potentially equipped items)
        :rtype: int
        """
        total = self.maxPrimaries
        multiplier = 1

        for upgrade in self.upgradesApplied:
            total += upgrade.maxPrimaries
            multiplier *= upgrade.maxPrimariesMultiplier
        return int(total * multiplier)


    def getMaxTurrets(self, shipUpgradesOnly: bool = False) -> int:
        """Get the total MaxTurrets provided by the equipped items and upgrades.
        If shipUpgradesOnly is given as True, then only applied shipUpgrades will be included in the calculation.
        This is used to give a 'base' measurement, as ship upgrades cannot be removed and are considered part of the
        ship once applied.

        :param bool shipUpgradesOnly: Whether to include all equipped items, or only the base ship MaxTurrets and that
                                        granted by applied shipUpgrades (Default False)
        :return: The ship's total MaxTurrets, including bonuses/penalties from ship upgrades
                    (and potentially equipped items)
        :rtype: int
        """
        total = self.maxTurrets
        multiplier = 1

        for upgrade in self.upgradesApplied:
            total += upgrade.maxTurrets
            multiplier *= upgrade.maxTurretsMultiplier
        return int(total * multiplier)


    def getMaxModules(self, shipUpgradesOnly: bool = False) -> int:
        """Get the total MaxModules provided by the equipped items and upgrades.
        If shipUpgradesOnly is given as True, then only applied shipUpgrades will be included in the calculation.
        This is used to give a 'base' measurement, as ship upgrades cannot be removed and are considered part of the
        ship once applied.

        :param bool shipUpgradesOnly: Whether to include all equipped items, or only the base ship MaxModules and that
                                        granted by applied shipUpgrades (Default False)
        :return: The ship's total MaxModules, including bonuses/penalties from ship upgrades (and potentially equipped items)
        :rtype: int
        """
        total = self.maxModules
        multiplier = 1

        for upgrade in self.upgradesApplied:
            total += upgrade.maxModules
            multiplier *= upgrade.maxModulesMultiplier
        return int(total * multiplier)


    def getValue(self, shipUpgradesOnly: bool = False) -> int:
        """Get the total Value provided by the equipped items and upgrades.
        If shipUpgradesOnly is given as True, then only applied shipUpgrades will be included in the calculation.
        This is used to give a 'base' measurement, as ship upgrades cannot be removed and are considered part of the
        ship once applied.

        :param bool shipUpgradesOnly: Whether to include all equipped items, or only the base ship Value and that
                                        granted by applied shipUpgrades (Default False)
        :return: The ship's total Value, including bonuses/penalties from ship upgrades (and potentially equipped items)
        :rtype: int
        """
        total = self.value

        if not shipUpgradesOnly:
            for module in self.modules:
                total += module.getValue()
            for weapon in self.weapons:
                total += weapon.getValue()
            for turret in self.turrets:
                total += turret.getValue()
        for upgrade in self.upgradesApplied:
            total += upgrade.valueForShip(self)

        return total


    def applyUpgrade(self, upgrade: shipUpgrade.ShipUpgrade):
        """Apply the given ship upgrade, locking it and its stats into the ship.
        Ship upgrades cannot be removed.

        :param shipUpgrade upgrade: the upgrade to apply
        """
        self.upgradesApplied.append(upgrade)


    def changeNickname(self, nickname: str):
        """Change the ship's custom nickname.
        giving nickname = "" is equivilent to a call to removeNickname

        :param str nickname: The new nickname to set
        """
        self.nickname = nickname
        if nickname != "":
            self.hasNickname = True


    def removeNickname(self):
        """Remove the ship's custom nickname, setting BB to display the ship type instead where needed.
        """
        if self.hasNickname:
            self.nickname = ""
            self.hasNickname = False


    def getNameOrNick(self) -> str:
        """Return the ship's nickname if it has one, or the name of the ship.

        :return: The ship's nickname if it has one, the ship's name otherwise
        :rtype: str
        """
        return self.nickname if self.hasNickname else self.name


    def getNameAndNick(self) -> str:
        """If the ship has a nickname, return the nickname followed by the ship name in brackets. Otherwise, just return the
        ship's name.

        :return: If the ship has a nickname, the nickname followed by the original name in brackets.
                    The ship name on its own otherwise.
        :rtype: str
        """
        return self.name if not self.hasNickname else (self.nickname + " (" + self.name + ")")


    def transferItemsTo(self, other: Ship):
        """Attempt to transfer as many equipped items as possible from this ship to another one.
        If there is not enough space to transfer any items, they will remain on this ship.

        :param shipItem other: The ship to transfer items to
        :raise TypeError: When given any type other than shipItem
        """
        if not isinstance(other, Ship):
            raise TypeError("Can only transfer items to another shipItem. Given " + str(type(other)))

        while self.hasWeaponsEquipped() and other.canEquipMoreWeapons():
            other.equipWeapon(self.weapons.pop(0))

        leftoverModules = []
        while self.hasModulesEquipped() and other.canEquipMoreModules():
            if other.canEquipModuleType(type(self.modules[0])):
                other.equipModule(self.modules.pop(0))
            else:
                leftoverModules.append(self.modules.pop(0))

        for leftoverModule in leftoverModules:
            self.modules.append(leftoverModule)

        while self.hasTurretsEquipped() and other.canEquipMoreTurrets():
            other.equipTurret(self.turrets.pop(0))


    def getActives(self, item: ItemCategory) -> Union[List[PrimaryWeapon], List[moduleItem.ModuleItem], List[TurretWeapon]]:
        """Return a requested array of equipped items, specified by string name.

        :param str item: one of weapon, module or turret.
        :return: An array of equipped items of the named typed.
        :rtype: list[PrimaryWeapon or moduleItem or TurretWeapon]
        :raise ValueError: If the requested item type is invalid
        """
        if item is ItemCategory.weapon:
            return self.weapons
        elif item is ItemCategory.module:
            return self.modules
        elif item is ItemCategory.turret:
            return self.turrets
        else:
            raise ValueError("unrecognised item type: " + item.value)


    def clearWeapons(self):
        """Delete all weapons equipped on the ship, without saving them.
        """
        self.weapons = []


    def clearModules(self):
        """Delete all modules equipped on the ship, without saving them.
        """
        self.modules = []


    def clearTurrets(self):
        """Delete all turrets equipped on the ship, without saving them.
        """
        self.turrets = []


    def applySkin(self, skin: shipSkin.ShipSkin):
        """Applies the given skin to this ship.
        Must be compatible with this ship.
        This ship must not be skinned already.

        :param shipSkin.shipSkin skin: The skin to apply
        :raise ValueError: If this ship already has a skin applied
        :raise TypeError: If the given skin is not compatible with this ship
        """
        if self.isSkinned:
            return ValueError("Attempted to apply a skin to an already-skinned ship")
        if not skin.compatibleWithShip(self):
            return TypeError("The given skin is not compatible with this ship")
        self.icon = skin.shipRenders[self.name][0]
        self.skin = skin
        self.isSkinned = True


    def statsStringShort(self) -> str:
        """Summarise all of the ship's statistics as a string, including equipped item names.

        :return: A summary of all of the ship's attributes and equipped items
        :rtype: str
        """
        stats = ""
        if self.isSkinned:
            # Casting here because self.skin being None is checked for with the isSkinned check
            rarityEmoji = getattr(cfg.defaultEmojis, f'rarity_{cfg.itemRarities[cast(shipSkin.ShipSkin, self.skin).rarityLevel]}').sendable
            stats += f"> {rarityEmoji}`Ship Skin: {cast(shipSkin.ShipSkin, self.skin).name.title()}`\n"
        stats += "• *Armour: " + str(self.getArmour(shipUpgradesOnly=True)) + ("(+)" \
                                if self.getArmour(shipUpgradesOnly=True) > self.armour else "") + "*\n"
        # stats += "Cargo hold: " + str(self.cargo) + ", "
        # stats += "Handling: " + str(self.handling) + ", "
        stats += "• *Primaries: " + str(len(self.weapons)) + "/" + str(self.getMaxPrimaries(shipUpgradesOnly=True)) \
                    + ("(+)" if self.getMaxPrimaries(shipUpgradesOnly=True) > self.maxPrimaries else "") + "*\n"
        if len(self.weapons) > 0:
            stats += "*["
            for weapon in self.weapons:
                stats += weapon.name + ", "
            stats = stats[:-2] + "]*\n"
        # stats += "Max secondaries: " + str(self.maxSecondaries) + ", "
        stats += "• *Turrets: " + str(len(self.turrets)) + "/" + str(self.getMaxTurrets(shipUpgradesOnly=True)) \
                        + ("(+)" if self.getMaxTurrets(shipUpgradesOnly=True) > self.maxTurrets else "") + "*\n"
        if len(self.turrets) > 0:
            stats += "*["
            for turret in self.turrets:
                stats += turret.name + ", "
            stats = stats[:-2] + "]*\n"
        stats += "• *Modules: " + str(len(self.modules)) + "/" + str(self.getMaxModules(shipUpgradesOnly=True)) \
                        + ("(+)" if self.getMaxModules(shipUpgradesOnly=True) > self.maxModules else "") + "*\n"
        if len(self.modules) > 0:
            stats += "*["
            for module in self.modules:
                stats += module.name + ", "
            stats = stats[:-2] + "]*\n"
        return stats


    def statsStringNoItems(self) -> str:
        """Return a shorter summary of the ship's statistics, ignoring any equipped items.

        :return: A string summary of the ship's statistics, ignoring any equipped items.
        :rtype: str
        """
        stats = ""
        if self.isSkinned:
            # Casting here because self.skin being None is checked for with the isSkinned check
            rarityEmoji = getattr(cfg.defaultEmojis, f'rarity_{cfg.itemRarities[cast(shipSkin.ShipSkin, self.skin).rarityLevel]}').sendable
            stats += f"> {rarityEmoji}`Ship Skin: {cast(shipSkin.ShipSkin, self.skin).name.title()}`\n"
        stats += "*Armour: " + str(self.getArmour(shipUpgradesOnly=True)) + ("(+)" \
                                if self.getArmour(shipUpgradesOnly=True) > self.armour else "") + ", "
        stats += "Cargo hold: " + str(self.getCargo(shipUpgradesOnly=True)) + ("(+)" \
                                if self.getCargo(shipUpgradesOnly=True) > self.cargo else "") + ", "
        stats += "Handling: " + str(self.getHandling(shipUpgradesOnly=True)) + ("(+)" \
                                if self.getHandling(shipUpgradesOnly=True) > self.handling else "") + ", "
        stats += "Max secondaries: " + str(self.getMaxSecondaries(shipUpgradesOnly=True)) + ("(+)" \
                                if self.getMaxSecondaries(shipUpgradesOnly=True) > self.maxSecondaries else "")
        return stats + "*"


    def fillLoadoutEmbed(self, baseEmbed: Embed, shipEmoji: bool = False, titlePrefix: str = "Active Ship: "):
        """Populate a discord.embed with information describing the ship.
        :param discord.Embed baseEmbed: The embed to add fields to
        :param bool shipEmoji: whether or not to use the ship's emoji next to its name.
                                You may wish to leave this as false and instead use the ship's icon
                                in the embed icon (Default False)
        """
        baseEmbed.add_field(name=titlePrefix + (self.emoji.sendable if shipEmoji and self.hasEmoji else "") + self.getNameAndNick(),
                            value=self.statsStringNoItems(),
                            inline=False)

        for name, maxEquip, equipped in (   ("Weapons", self.getMaxPrimaries(), self.weapons),
                                            ("Modules", self.getMaxModules(), self.modules),
                                            ("Turrets", self.getMaxTurrets(), self.turrets)):
            if maxEquip > 0:
                baseEmbed.add_field(name="‎",
                                    value="__**Equipped " + name + "**__ *" + str(len(equipped)) + "/" \
                                        + str(maxEquip) + "*",
                                    inline=False)
                for itemNum in range(1, len(equipped) + 1):
                    baseEmbed.add_field(name=str(itemNum) + ". " + equipped[itemNum - 1].name,
                                        value=(equipped[itemNum - 1].emoji.sendable \
                                                if equipped[itemNum - 1].hasEmoji else "") \
                                            + equipped[itemNum - 1].statsStringShort(),
                                        inline=True)

        return baseEmbed


    def serialize(self, **kwargs) -> SerializedShipUnion:
        """Serialize this shipItem into dictionary format, for saving to file. Includes all equiped items and upgrades

        :param bool saveType: When true, include the string name of the object type in the output.
        :return: A dictionary containing all information needed to reconstruct this ship. If the module is builtIn,
                    several statistics are omitted to save space.
        :rtype: dict
        """
        # Casting here so that I can add the new fields
        itemDict = cast(SerializedShipUnion, super(Ship, self).serialize(**kwargs))

        weaponsList = [weapon.serialize(**kwargs) for weapon in self.weapons]
        modulesList = [module.serialize(**kwargs) for module in self.modules]
        turretsList = [turret.serialize(**kwargs) for turret in self.turrets]
        upgradesList = [upgrade.serialize(**kwargs) for upgrade in self.upgradesApplied]

        itemDict["weapons"] = weaponsList
        itemDict["modules"] = modulesList
        itemDict["turrets"] = turretsList
        itemDict["shipUpgrades"] = upgradesList
        itemDict["nickname"] = self.nickname
        if self.isSkinned:
            # Casting here because we know the ship is skinned
            itemDict = cast(SkinnedSerializedShipUnion, itemDict)
            # Casting here because self.skin being None is checked for with the isSkinned check
            itemDict["skin"] = cast(shipSkin.ShipSkin, self.skin).serialize(**kwargs)
            itemDict["icon"] = self.icon

        if not self.builtIn:
            # Casting here because we know the ship is not builtIn
            itemDict = cast(CustomSerializedShipUnion, itemDict)
            itemDict["armour"] = self.armour
            itemDict["cargo"] = self.cargo
            itemDict["maxSecondaries"] = self.maxSecondaries
            itemDict["handling"] = self.handling
            itemDict["maxPrimaries"] = self.maxPrimaries
            itemDict["maxTurrets"] = self.maxTurrets
            itemDict["maxModules"] = self.maxModules
            itemDict["manufacturer"] = self.manufacturer

        return itemDict


    def __str__(self) -> str:
        """Get a short string identifying the ship. Currenly only includes the ship name (type)

        :return: A short string identifying this shipItem object
        :rtype: str
        """
        return "<shipItem: " + self.name + ">"


    @classmethod
    def deserialize(cls, shipDict: SerializedShipUnion, **kwargs) -> Ship:
        """Factory function constructing a new shipItem object from the given dictionary representation -
        the opposite of shipItem.serialize
        As with most other item deserialize functions, all missing information for builtIn ships is replaced
        by data from the corresponding bbData entry.

        :param dict shipDict: A dictionary containing all information required to construct the requested ship
        :return: A new shipItem object as described in shipDict
        :rtype: shipItem
        """
        weapons = [PrimaryWeapon.deserialize(d) for d in shipDict.get("weapons", [])]
        modules = [moduleItemFactory.ModuleItemFactory.deserialize(d) for d in shipDict.get("modules", [])]
        turrets = [TurretWeapon.deserialize(d) for d in shipDict.get("turrets", [])]
        shipUpgrades = [shipUpgrade.ShipUpgrade.deserialize(d) for d in shipDict.get("shipUpgrades", [])]
        ignoredData = ("model","compatibleSkins", "normSpec", \
                        "saveDue", "skinnable", "textureRegions", "path", "type",
                        "weapons", "modules", "turrets", "shipUpgrades", "emoji",
                        "numSecondaries", "skin")

        if "numSecondaries" in shipDict:
            # Casting here so that I can reassign the legacy field
            shipDict = cast(CustomSerializedShipUnion, shipDict)
            # Ignoring here because I'm accessing the legacy schema so that I can port to the new schema
            shipDict["maxSecondaries"] = shipDict["numSecondaries"] # type: ignore[CustomSerializedShipUnion]
            del shipDict["numSecondaries"] # type: ignore[CustomSerializedShipUnion]

        if "skin" in shipDict:
            # Casting here because we know the ship has a skin
            shipDict = cast(SkinnedSerializedShipUnion, shipDict)
            skin = shipSkin.ShipSkin.deserialize(shipDict["skin"])
        else:
            skin = None

        if shipDict["builtIn"]:
            # TODO: casting here because bbData is so far not type hinted fully
            builtInDict = cast(CustomSerializedShipUnion, bbData.builtInShipData[shipDict["name"]])

            # Ignoring here because pyright doesn't know the structure of a serialized ship
            builtInWeapons = [PrimaryWeapon.deserialize(d) for d in builtInDict.get("weapons", [])]
            builtInModules = [moduleItemFactory.ModuleItemFactory.deserialize(d) for d in builtInDict.get("modules", [])]
            builtInTurrets = [TurretWeapon.deserialize(d) for d in builtInDict.get("turrets", [])]
            builtInShipUpgrades = [shipUpgrade.ShipUpgrade.deserialize(d) for d in builtInDict.get("shipUpgrades", [])]

            # casting here because shipArgs is to be used as function arguments, not as a serialized ship
            shipArgs = cast(Dict[str, Any], builtInDict.copy())
            shipArgs.update(shipDict)
            for k in ignoredData:
                if k in shipArgs:
                    del shipArgs[k]

            emojiStr = cast(Optional[str], shipDict.get("emoji", builtInDict.get("emoji", None)))

            newShip = Ship(**cls._makeDefaults(shipArgs, ignoredData,
                                                weapons=weapons if "weapons" in shipDict else builtInWeapons,
                                                modules=modules if "modules" in shipDict else builtInModules,
                                                turrets=turrets if "turrets" in shipDict else builtInTurrets,
                                                upgradesApplied=shipUpgrades if "shipUpgrades" in shipDict \
                                                                else builtInShipUpgrades,
                                                emoji=BasedEmoji.fromStr(emojiStr) if emojiStr else BasedEmoji.EMPTY,
                                                skin=skin))
            return newShip

        else:
            # Casting here because we know the ship is not builtIn
            shipDict = cast(CustomSerializedShipUnion, shipDict)
            return Ship(**cls._makeDefaults(shipDict, ignoredData,
                                            weapons=weapons, modules=modules, turrets=turrets,
                                            upgradesApplied=shipUpgrades, builtIn=False,
                                            emoji=BasedEmoji.fromStr(shipDict["emoji"])
                                                    if "emoji" in shipDict else BasedEmoji.EMPTY,
                                            skin=skin))
