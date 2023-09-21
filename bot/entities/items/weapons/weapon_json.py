from ..base.itemBase_json import AnySerializedItemBase
from ...base.workshopable_json import AnySerializedWorkshopable

class SerializedWeapon(AnySerializedWorkshopable, AnySerializedItemBase):
    dps: int
