from typing import List, Optional, Type, cast

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, Table, Column, Integer, Enum, and_
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.ext.hybrid import hybrid_property

from discord import Embed

from ....database.tables import TableNames
from ....database.constants import StoreableItemType, ShipInstanceEquippedItemType
from ..base.itemBase import ItemBase
from ..base.itemBase_storeable import itemType
from . import shipSkin, shipSpec, shipUpgrade
from ....baseClasses.embedFillable import EmbedFillableMixin, embedField
from ....lib.gameMaths import topThreeItemSpawnRates
from ....cfg import bbData, cfg
from ..weapons.primaryWeapon import PrimaryWeapon
from ..weapons.turretWeapon import TurretWeapon


class Base(DeclarativeBase, AsyncAttrs):
    pass


ShipInstanceHasItemEquipped = Table(
    TableNames.UserHasMedal.value,
    Base.metadata,
    Column("shipInstanceId", Integer, ForeignKey(f"{TableNames.ShipInstance.value}.id"), primary_key=True),
    Column("itemId", Integer, primary_key=True),
    Column("itemType", Enum(ShipInstanceEquippedItemType))
)


@itemType(StoreableItemType.ship)
class ShipInstance(Base, ItemBase, EmbedFillableMixin):
    __tablename__ = TableNames.ShipInstance.value

    nickname: Mapped[str]

    shipId: Mapped[int] = mapped_column(ForeignKey(TableNames.ShipSpec.value))
    spec: Mapped["shipSpec.ShipSpec"] = relationship()
    
    skinId: Mapped[Optional[int]] = mapped_column(ForeignKey(TableNames.ShipSkin.value))
    skin: Mapped[Optional["shipSkin.ShipSkin"]]
    
    # Eager loading means this can be accessed synchronously
    upgradesApplied: Mapped[List["shipUpgrade.ShipUpgrade"]] = relationship(
        secondary=ShipInstanceHasItemEquipped,
        primaryjoin=and_(ShipInstanceHasItemEquipped.c.shipInstanceId == ItemBase.id,
                         ShipInstanceHasItemEquipped.c.itemType == ShipInstanceEquippedItemType.shipUpgrade),
        lazy="joined")
    
    weapons: Mapped[List["PrimaryWeapon"]] = relationship(
        secondary=ShipInstanceHasItemEquipped,
        primaryjoin=and_(ShipInstanceHasItemEquipped.c.shipInstanceId == ItemBase.id,
                         ShipInstanceHasItemEquipped.c.itemType == ShipInstanceEquippedItemType.primaryWeapon),
        lazy="joined")
    
    turrets: Mapped[List["TurretWeapon"]] = relationship(
        secondary=ShipInstanceHasItemEquipped,
        primaryjoin=and_(ShipInstanceHasItemEquipped.c.shipInstanceId == ItemBase.id,
                         ShipInstanceHasItemEquipped.c.itemType == ShipInstanceEquippedItemType.turret),
        lazy="joined")
    
    modules: Mapped[List["moduleItem.ModuleItem"]] = relationship(
        secondary=ShipInstanceHasItemEquipped,
        primaryjoin=and_(ShipInstanceHasItemEquipped.c.shipInstanceId == ItemBase.id,
                         ShipInstanceHasItemEquipped.c.itemType == ShipInstanceEquippedItemType.module),
        lazy="joined")
    
    
    @hybrid_property
    def hasNickname(self):
        return self.nickname is not None
    
    @hybrid_property
    def isSkinned(self):
        return self.skin is not None

#region embed fields
    # upgraded and unupgraded are separated here to fake dynamic field names
#region upgraded
    @embedField("Armour (+)", hideWhenNone=True)
    def formattedUpgradedArmour(self): return self.getArmour() if self.armourIsUpgraded() else None

    @embedField("Cargo (+)", hideWhenNone=True)
    def formattedUpgradedCargo(self): return self.getCargo() if self.cargoIsUpgraded() else None

    @embedField("Handling (+)", hideWhenNone=True)
    def formattedUpgradedHandling(self): return self.getHandling() if self.handlingIsUpgraded() else None

    @embedField("Max Primaries (+)", hideWhenNone=True)
    def formattedUpgradedMaxPrimaries(self): return self.getMaxPrimaries() if self.maxPrimariesIsUpgraded() else None

    @embedField("Max Secondaries (+)", hideWhenNone=True)
    def formattedUpgradedMaxSecondaries(self): return self.getMaxSecondaries() if self.maxSecondariesIsUpgraded() else None

    @embedField("Max Turrets (+)", hideWhenNone=True)
    def formattedUpgradedMaxTurrets(self): return self.getMaxTurrets() if self.maxTurretsIsUpgraded() else None

    @embedField("Max Modules (+)", hideWhenNone=True)
    def formattedUpgradedMaxModules(self): return self.getMaxModules() if self.maxModulesIsUpgraded() else None
#endregion
#region unupgraded
    @embedField("Armour", hideWhenNone=True)
    def formattedArmour(self): return None if self.armourIsUpgraded() else self.spec.armour

    @embedField("Cargo", hideWhenNone=True)
    def formattedCargo(self): return None if self.cargoIsUpgraded() else self.spec.cargo

    @embedField("Handling", hideWhenNone=True)
    def formattedHandling(self): return None if self.handlingIsUpgraded() else self.spec.handling

    @embedField("Max Primaries", hideWhenNone=True)
    def formattedMaxPrimaries(self): return None if self.maxPrimariesIsUpgraded() else self.spec.maxPrimaries

    @embedField("Max Secondaries", hideWhenNone=True)
    def formattedMaxSecondaries(self): return None if self.maxSecondariesIsUpgraded() else self.spec.maxSecondaries

    @embedField("Max Turrets", hideWhenNone=True)
    def formattedMaxTurrets(self): return None if self.maxTurretsIsUpgraded() else self.spec.maxTurrets

    @embedField("Max Modules", hideWhenNone=True)
    def formattedMaxModules(self): return None if self.maxModulesIsUpgraded() else self.spec.maxModules

#endregion
    
    @embedField("Upgrades Applied", hideWhenNone=True)
    def formattedUpgradesApplied(self): return ("- " + "\n- ".join(upgrade.name for upgrade in self.upgradesApplied)) if self.upgradesApplied else None

    @embedField("BB Shop Spawn Rate", hideWhenNone=True)
    def formattedShopSpawnRate(self): return topThreeItemSpawnRates(self.techLevel, bbData.shipKeysByTL)
    
    @embedField("Compatible Skins", showInline=False)
    def compatibleSkinsStr(self):
        shipData = bbData.builtInShipData.get(self.name, None)
        if shipData is None or not shipData.get("skinnable", False):
            return "This ship is not skinnable"
        
        # Include compatible ship skin names
        if compatibleSkins := shipData.get("compatibleSkins", []):
            return " • ".join(compatibleSkins)
        
        return "This ship is skinnable, but currently has no compatible skins"

#endregion

    def armourIsUpgraded(self) -> bool:
        return any(upgrade.armour or (upgrade.armourMultiplier != 1) for upgrade in self.upgradesApplied)


    def cargoIsUpgraded(self) -> bool:
        return any(upgrade.cargo or (upgrade.cargoMultiplier != 1) for upgrade in self.upgradesApplied)


    def handlingIsUpgraded(self) -> bool:
        return any(upgrade.handling or (upgrade.handlingMultiplier != 1) for upgrade in self.upgradesApplied)


    def maxPrimariesIsUpgraded(self) -> bool:
        return any(upgrade.maxPrimaries or (upgrade.maxPrimariesMultiplier != 1) for upgrade in self.upgradesApplied)


    def maxSecondariesIsUpgraded(self) -> bool:
        return any(upgrade.maxSecondaries or (upgrade.maxSecondariesMultiplier != 1) for upgrade in self.upgradesApplied)


    def maxTurretsIsUpgraded(self) -> bool:
        return any(upgrade.maxTurrets or (upgrade.maxTurretsMultiplier != 1) for upgrade in self.upgradesApplied)


    def maxModulesIsUpgraded(self) -> bool:
        return any(upgrade.maxModules or (upgrade.maxModulesMultiplier != 1) for upgrade in self.upgradesApplied)


    def equippedWeaponsCount(self) -> int:
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
        return self.equippedWeaponsCount() < self.getMaxPrimaries()


    def equippedModulesCount(self) -> int:
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
        return self.equippedModulesCount() < self.getMaxModules()


    def equippedTurretsCount(self) -> int:
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
        return self.equippedTurretsCount() < self.getMaxTurrets()


    def equippedPrimariesCount(self) -> bool:
        """Decide whether or not this ship has any Weapons equipped

        :return: True if at least one Weapon is equipped on this ship, False otherwise
        :rtype: bool
        """
        return self.equippedWeaponsCount() > 0


    def hasModulesEquipped(self) -> bool:
        """Decide whether or not this ship has any Modules equipped

        :return: True if at least one Module is equipped on this ship, False otherwise
        :rtype: bool
        """
        return self.equippedModulesCount() > 0


    def hasTurretsEquipped(self) -> bool:
        """Decide whether or not this ship has any Turrets equipped

        :return: True if at least one Turret is equipped on this ship, False otherwise
        :rtype: bool
        """
        return self.equippedTurretsCount() > 0


    def getWeaponAtIndex(self, index: int) -> PrimaryWeapon:
        """Fetch the weapon object equipped at the given index

        :param int index: The index of the weapon object to fetch
        :return: The weapon object equipped at the given index
        :rtype: PrimaryWeapon
        """
        return self.weapons[index]


    def canEquipModuleType(self, moduleType: Type[ModuleItem]) -> bool:
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


    def getModuleAtIndex(self, index: int) -> moduleItem.ModuleItem:
        """Fetch the moduleItem object reference that is equipped at the given index

        :param int index: The index of the module to fetch
        :return: The module reference equipped at the given index
        :rtype: moduleItem
        """
        return self.modules[index]


    def getTurretAtIndex(self, index: int) -> TurretWeapon:
        """Fetch the turret object equipped at the given index

        :param int index: The index of the turret object to fetch
        :return: The turret object equipped at the given index
        :rtype: TurretWeapon
        """
        return self.turrets[index]


    def getDPS(self) -> float:
        """Get the total DPS provided by the equipped items and upgrades.
        If shipUpgradesOnly is given as True, then only applied shipUpgrades will be included in the calculation.
        This is used to give a 'base' measurement, as ship upgrades cannot be removed and are considered part of the
        ship once applied.

        :return: The ship's total DPS, including bonuses/penalties from ship upgrades (and potentially equipped items)
        :rtype: int
        """
        total = 0
        multiplier = 1

        for weapon in self.weapons:
            total += weapon.dps
        for turret in self.turrets:
            total += turret.dps
        for module in self.modules:
            total += module.dps
            multiplier *= module.dpsMultiplier

        return total * multiplier


    def getShield(self) -> int:
        """Get the total Shield provided by the equipped items and upgrades.
        If shipUpgradesOnly is given as True, then only applied shipUpgrades will be included in the calculation.
        This is used to give a 'base' measurement, as ship upgrades cannot be removed and are considered part
        of the ship once applied.

        :return: The ship's total Shield, including bonuses/penalties from ship upgrades (and potentially equipped items)
        :rtype: int
        """
        total = 0
        multiplier = 1

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
        total = self.spec.armour
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
        total = self.spec.cargo
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
        total = self.spec.handling
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
        total = self.spec.maxSecondaries
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
        total = self.spec.maxPrimaries
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
        total = self.spec.maxTurrets
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
        total = self.spec.maxModules
        multiplier = 1

        for upgrade in self.upgradesApplied:
            total += upgrade.maxModules
            multiplier *= upgrade.maxModulesMultiplier
        return int(total * multiplier)


    async def getValue(self, shipUpgradesOnly: bool = False) -> int:
        """Get the total Value provided by the equipped items and upgrades.
        If shipUpgradesOnly is given as True, then only applied shipUpgrades will be included in the calculation.
        This is used to give a 'base' measurement, as ship upgrades cannot be removed and are considered part of the
        ship once applied.

        :param bool shipUpgradesOnly: Whether to include all equipped items, or only the base ship Value and that
                                        granted by applied shipUpgrades (Default False)
        :return: The ship's total Value, including bonuses/penalties from ship upgrades (and potentially equipped items)
        :rtype: int
        """
        total = self.spec.value

        if not shipUpgradesOnly:
            for module in self.modules:
                total += await module.getValue()
            for weapon in self.weapons:
                total += await weapon.getValue()
            for turret in self.turrets:
                total += await turret.getValue()
        for upgrade in self.upgradesApplied:
            total += upgrade.valueForShip(self.spec)

        return total


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
        return self.name if not self.hasNickname else f"{self.nickname}  ({self.name})"


    def getActives(self, itemType: bbData.ShipEquippableItemCategoryType) -> List[shipSpec.ShipEquippableItemType]:
        """Get the all of the ship's equipped items of the given type.
        The given list is mutable, and can alter the ship's equipped items.

        :param ItemCategory itemType: The item type whose equips to get
        :return: A list containing all of the ships's equipped items of the named type.
        :rtype: List[GameItem]
        :raise NotImplementedError: When requesting a valid item type but one that is not yet implemented (e.g commodity)
        """
        #TODO: Casting here because I can't convince pyright that the types match
        if itemType == bbData.ItemCategory.weapon:
            return cast(List[shipSpec.ShipEquippableItemType], self.weapons)
        if itemType == bbData.ItemCategory.module:
            return cast(List[shipSpec.ShipEquippableItemType], self.modules)
        if itemType == bbData.ItemCategory.turret:
            return cast(List[shipSpec.ShipEquippableItemType], self.turrets)
        raise NotImplementedError("Unrecognised item type: " + itemType.value)


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
                                if self.getArmour(shipUpgradesOnly=True) > self.spec.armour else "") + "*\n"
        # stats += "Cargo hold: " + str(self.cargo) + ", "
        # stats += "Handling: " + str(self.handling) + ", "
        stats += "• *Primaries: " + str(len(self.weapons)) + "/" + str(self.getMaxPrimaries(shipUpgradesOnly=True)) \
                    + ("(+)" if self.getMaxPrimaries(shipUpgradesOnly=True) > self.spec.maxPrimaries else "") + "*\n"
        if len(self.weapons) > 0:
            stats += "*["
            for weapon in self.weapons:
                stats += weapon.name + ", "
            stats = stats[:-2] + "]*\n"
        # stats += "Max secondaries: " + str(self.maxSecondaries) + ", "
        stats += "• *Turrets: " + str(len(self.turrets)) + "/" + str(self.getMaxTurrets(shipUpgradesOnly=True)) \
                        + ("(+)" if self.getMaxTurrets(shipUpgradesOnly=True) > self.spec.maxTurrets else "") + "*\n"
        if len(self.turrets) > 0:
            stats += "*["
            for turret in self.turrets:
                stats += turret.name + ", "
            stats = stats[:-2] + "]*\n"
        stats += "• *Modules: " + str(len(self.modules)) + "/" + str(self.getMaxModules(shipUpgradesOnly=True)) \
                        + ("(+)" if self.getMaxModules(shipUpgradesOnly=True) > self.spec.maxModules else "") + "*\n"
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
                                if self.getArmour(shipUpgradesOnly=True) > self.spec.armour else "") + ", "
        stats += "Cargo hold: " + str(self.getCargo(shipUpgradesOnly=True)) + ("(+)" \
                                if self.getCargo(shipUpgradesOnly=True) > self.spec.cargo else "") + ", "
        stats += "Handling: " + str(self.getHandling(shipUpgradesOnly=True)) + ("(+)" \
                                if self.getHandling(shipUpgradesOnly=True) > self.spec.handling else "") + ", "
        stats += "Max secondaries: " + str(self.getMaxSecondaries(shipUpgradesOnly=True)) + ("(+)" \
                                if self.getMaxSecondaries(shipUpgradesOnly=True) > self.spec.maxSecondaries else "")
        return stats + "*"


    def fillLoadoutEmbed(self, baseEmbed: Embed, shipEmoji: bool = False, titlePrefix: str = "Active Ship: "):
        """Populate a discord.embed with information describing the ship.
        :param discord.Embed baseEmbed: The embed to add fields to
        :param bool shipEmoji: whether or not to use the ship's emoji next to its name.
                                You may wish to leave this as false and instead use the ship's icon
                                in the embed icon (Default False)
        """
        baseEmbed.add_field(name=titlePrefix + (self.emoji.sendable if shipEmoji and self.emoji is not None else "") + self.getNameAndNick(),
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
    
