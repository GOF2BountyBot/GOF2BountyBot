from typing import cast
from . import toolItem, shipSkinTool, throwSnowballTool
from . import crateTool
from .. import shipItem, moduleItemFactory
from ..weapons import primaryWeapon, turretWeapon
from ....baseClasses.serializable import FromJsonFactory, JsonType

itemConstructors = {shipItem.Ship.__name__: shipItem.Ship,
                        primaryWeapon.PrimaryWeapon.__name__: primaryWeapon.PrimaryWeapon,
                        moduleItemFactory.ModuleItem.__name__: moduleItemFactory.ModuleItemFactory,
                        turretWeapon.TurretWeapon.__name__: turretWeapon.TurretWeapon}


class ToolItemFactory(FromJsonFactory[toolItem.ToolItem]):
    @classmethod
    def deserialize(cls, data: JsonType, **kwargs) -> toolItem.ToolItem:
        """Construct a toolItem from its dictionary-serialized representation.
        This method decodes which tool constructor is appropriate based on the 'type' attribute of the given dictionary.

        :param dict toolDict: A dictionary containing all information needed to construct the required toolItem. Critically,
                                a name, type, and builtIn specifier.
        :return: A new toolItem object as described in toolDict
        :rtype: toolItem.toolItem
        :raise NameError: When toolDict does not contain a 'type' attribute.
        """
        if "type" not in data:
            raise NameError("Required dictionary attribute missing: 'type'")
        elif data["type"] == "ToolItem":
            raise ValueError("Cannot deserialize abstract type 'ToolItem'")
        # Casting here because pyright cannot know the structure of the dict
        return toolTypeConstructors[cast(str, data["type"])].deserialize(data, **kwargs)


toolTypeConstructors = {shipSkinTool.ShipSkinTool.__name__: shipSkinTool.ShipSkinTool,
                        crateTool.CrateTool.__name__: crateTool.CrateTool,
                        "ToolItem": ToolItemFactory,
                        crateTool.ShipSkinCrateTool.__name__: crateTool.ShipSkinCrateTool,
                        throwSnowballTool.ThrowSnowballTool.__name__: throwSnowballTool.ThrowSnowballTool}
itemConstructors.update(toolTypeConstructors)
