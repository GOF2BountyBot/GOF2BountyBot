from .moduleItem import ModuleItem
from ..base.item_spawnable import spawnableItem


@spawnableItem
class ThrusterModule(ModuleItem):
    """A module providing a ship with a boost to its handling.
    """
    