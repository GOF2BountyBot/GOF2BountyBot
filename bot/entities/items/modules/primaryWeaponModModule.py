from .moduleItem import ModuleItem
from ..base.item_spawnable import spawnableItem


@spawnableItem
class PrimaryWeaponModModule(ModuleItem):
    """A module providing a DPS multiplier to all equipped weapons
    """
