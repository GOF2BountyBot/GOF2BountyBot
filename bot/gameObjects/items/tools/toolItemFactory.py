from bot.gameObjects.items.ships import shipItem
from bot.gameObjects.items.tools import toolItem, shipSkinTool, throwSnowballTool
from bot.gameObjects.items.tools import crateTool
from bot.gameObjects.items.tools.crates import shipSkinCrateTool
from bot.gameObjects.items import moduleItemFactory
from bot.gameObjects.items.weapons import primaryWeapon, turretWeapon
from bot.baseClasses.serializable import Factory

itemConstructors = {shipItem.Ship.__name__: shipItem.Ship,
                        primaryWeapon.PrimaryWeapon.__name__: primaryWeapon.PrimaryWeapon,
                        moduleItemFactory.ModuleItem.__name__: moduleItemFactory.ModuleItemFactory,
                        turretWeapon.TurretWeapon.__name__: turretWeapon.TurretWeapon}


class ToolItemFactory(Factory[toolItem.TypedSerializedToolItem, toolItem.ToolItem]):
    @classmethod
    def deserialize(cls, data: toolItem.TypedSerializedToolItem, **kwargs) -> toolItem.ToolItem:
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
        return toolTypeConstructors[data["type"]].deserialize(data, **kwargs)


toolTypeConstructors = {shipSkinTool.ShipSkinTool.__name__: shipSkinTool.ShipSkinTool,
                        crateTool.CrateTool.__name__: crateTool.CrateTool,
                        "ToolItem": ToolItemFactory,
                        shipSkinCrateTool.ShipSkinCrateTool.__name__: shipSkinCrateTool.ShipSkinCrateTool,
                        throwSnowballTool.ThrowSnowballTool.__name__: throwSnowballTool.ThrowSnowballTool}
itemConstructors.update(toolTypeConstructors)
