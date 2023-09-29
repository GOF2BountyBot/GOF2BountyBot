from sqlalchemy.orm import Mapped

from .moduleItem import ModuleItem
from ..base.item_spawnable import spawnableItem


@spawnableItem
class SignatureModule(ModuleItem):
    """A module allowing a the owner to disguise themselves as a member of th faction that manufactured this signature.
    """
    manufacturer: Mapped[str]

    def statsStringShort(self):
        return "*Faction: " + self.manufacturer + "*"
