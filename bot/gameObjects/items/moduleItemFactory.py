from typing import cast
from bot.cfg import bbData
from bot.gameObjects.items.modules import _all as moduleItemClasses
from bot.gameObjects.items.modules import ModuleItem
from bot.gameObjects.items.modules.moduleItem import SerializedModuleItemUnion, TypedSerializedModuleItemUnion
from bot.baseClasses.serializable import Factory

typeConstructors = {cls.__name__: cls.deserialize for cls in moduleItemClasses}


class ModuleItemFactory(Factory[SerializedModuleItemUnion, ModuleItem]):
    @classmethod
    def deserialize(cls, data: SerializedModuleItemUnion, **kwargs) -> ModuleItem:
        """Factory function recreating any moduleItem or moduleItem subtype from a dictionary-serialized representation.
        If implemented correctly, this should act as the opposite to the original object's serialize method.
        If the requested module is builtIn, return the builtIn module object of the same name.

        :param dict moduleDict: A dictionary containg all information necessary to create the desired moduleItem object
        :return: The moduleItem object described in moduleDict
        :rtype: moduleItem
        """
        if data.get("builtIn", False):
            return bbData.builtInModuleObjs[data["name"]]

        if "type" in data:
            # Casting here because we know the data is typed
            data = cast(TypedSerializedModuleItemUnion, data)
            if data["type"] in typeConstructors:
                return typeConstructors[data["type"]](data)
        return ModuleItem.deserialize(data)
