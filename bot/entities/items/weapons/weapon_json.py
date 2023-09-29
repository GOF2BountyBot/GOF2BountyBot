from ..base.item_json import AnySerializedItem
from ...base.workshopable_json import AnySerializedWorkshopable

class SerializedWeapon(AnySerializedWorkshopable, AnySerializedItem):
    dps: int
