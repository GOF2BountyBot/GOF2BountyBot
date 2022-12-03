from typing import Optional
from .shipBase import ShipBase
from ....baseClasses.embedFillable import EmbedFillableMixin
from ..gameItem import spawnableItem
from ... import shipUpgrade

from ..weapons.primaryWeapon import PrimaryWeapon
from ..weapons.turretWeapon import TurretWeapon
from ..modules import moduleItem
from ... import shipSkin, shipUpgrade
from ....baseClasses.embedFillable import EmbedFillableMixin

@spawnableItem
class Ship(ShipBase, EmbedFillableMixin):
    """An equippable and customisable ship for use by players and NPCs.
    """

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


    def transferItemsTo(self, other: "Ship") -> int:
        """Attempt to transfer as many equipped items as possible from this ship to another one.
        If there is not enough space to transfer any items, they will remain on this ship.

        :param shipItem other: The ship to transfer items to
        :return: The number items that could not fit on the new ship, if any
        :rtype: int
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

        return len(self.weapons) + len(self.modules) + len(self.turrets)


    def clearWeapons(self):
        """Delete all weapons equipped on the ship, without saving them.
        """
        self.weapons.clear()


    def clearModules(self):
        """Delete all modules equipped on the ship, without saving them.
        """
        self.modules.clear()


    def clearTurrets(self):
        """Delete all turrets equipped on the ship, without saving them.
        """
        self.turrets.clear()


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
        # Todo: Why do I need to re-type this? skin is already defined on shipBase
        self.skin: Optional[shipSkin.ShipSkin] = skin
        self.isSkinned = True


