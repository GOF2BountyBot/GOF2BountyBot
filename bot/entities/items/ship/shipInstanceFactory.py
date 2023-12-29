import random
from typing import Any, Dict, Sequence, Type

from . import shipInstance, shipSpec
from ....repositories.itemRepository import ItemRepository, ItemFilter
from ....repositories.shipSpecRepository import ShipSpecRepository, ShipSpecFilter
from ....cfg import cfg

from ....cfg import cfg
from .... import botState # TODO
from ....logging import LogCategory
from ...items.modules import armourModule, shieldModule, moduleItem
from ...items.ship import shipInstance
from ...items.weapons import primaryWeapon, turretWeapon
from ...items.weapons import weapon
from ....repositories.shipSpecRepository import ShipSpecRepository
from ....repositories.shipInstanceRepository import ShipInstanceRepository
from ....repositories.primaryWeaponRepository import PrimaryWeaponRepository
from ....serialization.jsonSerializer import JsonSerializer

def WeaponHasDpsFilter(tl: int, tlItems: Sequence[weapon.Weapon]) -> bool:
    return any(x.dps for x in tlItems)


class ShipInstanceFactory:
    def __init__(self, serializer: JsonSerializer, itemRepository: ItemRepository, shipSpecRepository: ShipSpecRepository, shipInstanceRepository: ShipInstanceRepository, primaryWeaponRepository: PrimaryWeaponRepository) -> None:
        self.serializer = serializer
        self.itemRepository = itemRepository
        self.shipSpecRepository = shipSpecRepository
        self.primaryWeaponRepository = primaryWeaponRepository
        self.shipInstanceRepository = shipInstanceRepository
        

    async def createForSpec(self, shipSpec: shipSpec.AnyShipSpec) -> shipInstance.AnyShipInstance:
        row = shipInstance.ShipInstance( # TODO
            name=shipSpec.name)
        await self.shipInstanceRepository.create(row)
        return row

    
    async def generateLoadoutForLevel(self, techLevel: int) -> shipInstance.AnyShipInstance:
        shipSpec = await self._pickShipSpec(techLevel)
                                    
        ship = await self.createForSpec(shipSpec)

        if shipSpec.maxPrimaries:
            await self._equipWeapons(techLevel, ship)

        if shipSpec.maxModules:
            await self._equipModules(techLevel, ship)

        if shipSpec.maxTurrets:
            await self._equipTurrets(techLevel, ship)

        return ship


    async def _pickShipSpec(self, techLevel: int) -> shipSpec.AnyShipSpec:
        # First attempt to find a TL for which a ship exists with primary weapon slots
        shipTlChoices = await self.shipSpecRepository.walkingTlSearch(
            techLevel, cfg.minTechLevel - 1, cfg.maxTechLevel - 1,
            cfg.criminalMaxGearUpgrade, ShipSpecFilter.shipSpecTLHasPrimaries)
        
        shipHasPrimary = len(shipTlChoices) > 0
        if shipHasPrimary:
            # If no such TL could be found, settle for a TL for which a ship exists
            shipTlChoices = await self.shipSpecRepository.walkingTlSearch(
                techLevel, cfg.minTechLevel - 1, cfg.maxTechLevel - 1,
                cfg.criminalMaxGearUpgrade, ShipSpecFilter.hasAny)

            # If no such TL could be found, there must be no ships in the game
            if not shipTlChoices:
                raise ValueError("Unable to select ship spec, no ships registered in the game.")
        
        if not shipHasPrimary:
            return random.choice(shipTlChoices)

        return random.choice([s for s in shipTlChoices if s.maxPrimaries > 0])


    async def _equipWeapons(self, techLevel: int, ship: shipInstance.AnyShipInstance):
        # Attempt to find damage-dealing weapons first
        weaponTlChoices = await self.itemRepository.walkingTlSearch(primaryWeapon.PrimaryWeapon,
            techLevel, cfg.minTechLevel - 1, cfg.maxTechLevel - 1, cfg.criminalMaxGearUpgrade, WeaponHasDpsFilter)
        
        dpsWeapons = len(weaponTlChoices) != 0
        
        # Couldn't find a TL with damage dealing weapons
        if not dpsWeapons:
            # Try for TLs with non-damaging weapons
            weaponTlChoices = await self.itemRepository.walkingTlSearch(primaryWeapon.PrimaryWeapon,
                techLevel, cfg.minTechLevel - 1, cfg.maxTechLevel - 1, cfg.criminalMaxGearUpgrade,
                ItemFilter.hasAny)
            
            if len(weaponTlChoices) == 0:
                botState.client.logger.log("BountyConfig", "generate",
                                    "unable to find any TLs containing weapons",
                                    eventType="NO_ITEMS", category=LogCategory.bountyConfig)

        if len(weaponTlChoices) == 0: return

        numWeapons = random.randint(max(1, ship.spec.maxPrimaries - 1), ship.spec.maxPrimaries)
        for _ in range(numWeapons):
            currentWeapon = random.choice(weaponTlChoices)
            # The chosen weapon doesnt deal damage. If the TL has damage-dealing weapons,
            # randomly choose whether or not to ensure a damage-dealing weapon is picked
            if dpsWeapons and not currentWeapon.dps \
                    and random.randint(0, 100) > cfg.criminalEquipDamagelessWeaponChance:
                while not currentWeapon.dps:
                    currentWeapon = random.choice(weaponTlChoices)
            ship.equipWeapon(currentWeapon)


    async def _equipModules(self, techLevel: int, ship: shipInstance.AnyShipInstance):
        moduleTypesToEquip: Dict[Type[moduleItem.ModuleItem[Any]], int] = {armourModule.ArmourModule: 0, shieldModule.ShieldModule: 0}
        reservedSlots = 0
        # ensure criminals above TL 1 have armour
        if techLevel > 1:
            moduleTypesToEquip[armourModule.ArmourModule] = 1
            reservedSlots += 1
        # ensure criminals above TL 3 have shield
        if techLevel > 3:
            moduleTypesToEquip[shieldModule.ShieldModule] = 1
            reservedSlots += 1

        maxExtraModules = ship.spec.maxModules - len(ship.modules) - reservedSlots
        moduleTypesToEquip[moduleItem.ModuleItem[Any]] = random.randint(1, maxExtraModules)

        for moduleType in moduleTypesToEquip:
            while moduleTypesToEquip[moduleType] > 0 and ship.canEquipMoreModules() and ship.canEquipModuleType(moduleType):
                moduleTlChoices = await self.itemRepository.walkingTlSearch(moduleItem.ModuleItem[Any],
                    techLevel, cfg.minTechLevel - 1, cfg.maxTechLevel - 1, cfg.criminalMaxGearUpgrade,
                    ItemFilter.itemTlHasEquippableType, itemType=moduleType, activeShip=ship)
                
                if len(moduleTlChoices) == 0:
                    botState.client.logger.log("BountyConfig", "generate",
                                        "unable to find any TLs containing equippable " + moduleType.__name__ + "s",
                                        eventType="NO_ITEMS", category=LogCategory.bountyConfig)
                    break
                else:
                    itemToEquip = random.choice(moduleTlChoices)
                    while not isinstance(itemToEquip, moduleType):
                        itemToEquip = random.choice(moduleTlChoices)

                    if ship.canEquipModuleType(type(itemToEquip)):
                        ship.equipModule(itemToEquip)
                        moduleTypesToEquip[moduleType] -= 1


    async def _equipTurrets(self, techLevel: int, ship: shipInstance.AnyShipInstance):
        # Attempt to find damage-dealing turrets first
        turretTlChoices = await self.itemRepository.walkingTlSearch(turretWeapon.TurretWeapon,
            techLevel, cfg.minTechLevel - 1, cfg.maxTechLevel - 1, cfg.criminalMaxGearUpgrade, WeaponHasDpsFilter)
        
        dpsTurrets = len(turretTlChoices) != 0
        
        # Couldn't find a TL with damage dealing turrets
        if not dpsTurrets:
            # Try for TLs with non-damaging turrets
            turretTlChoices = await self.itemRepository.walkingTlSearch(turretWeapon.TurretWeapon,
                techLevel, cfg.minTechLevel - 1, cfg.maxTechLevel - 1, cfg.criminalMaxGearUpgrade,
                ItemFilter.hasAny)

            if len(turretTlChoices) == 0:
                botState.client.logger.log("BountyConfig", "generate",
                                    "unable to find any TLs containing turrets",
                                    eventType="NO_ITEMS", category=LogCategory.bountyConfig)

        if len(turretTlChoices) == 0: return

        numTurrets = random.randint(max(0, ship.spec.maxTurrets - 1), ship.spec.maxTurrets)
        for _ in range(numTurrets):
            currentTurret = random.choice(turretTlChoices)
            # The chosen turret doesnt deal damage. If the TL has damage-dealing turrets,
            # randomly choose whether or not to ensure a damage-dealing turret is picked
            if dpsTurrets and not currentTurret.dps \
                    and random.randint(0, 100) > cfg.criminalEquipDamagelessWeaponChance:
                while not currentTurret.dps:
                    currentTurret = random.choice(turretTlChoices)
            ship.equipTurret(currentTurret)
