from .moduleItem import AnyModuleItem
from ..base.item_spawnable import spawnableItem


@spawnableItem
class ArmourModule(AnyModuleItem):
    """A module providing a ship with an extra layer of defense.
    """
