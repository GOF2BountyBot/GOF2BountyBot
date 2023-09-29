from .moduleItem import ModuleItem
from ..base.item_spawnable import spawnableItem


@spawnableItem
class JumpDriveModule(ModuleItem):
    """"A module providing a ship with the ability to jump anywhere within the galaxy, without the need to use jumpgates
    """