from .moduleItem import ModuleItem
from ..base.item_spawnable import spawnableItem


@spawnableItem
class ShieldModule(ModuleItem):
    """A module providing a ship with a self-repairing layer of protection, over the ship's hull and armour (if equipped)
    """
