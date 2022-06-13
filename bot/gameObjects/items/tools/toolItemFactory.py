from . import toolItem, shipSkinTool, throwSnowballTool
from . import crateTool
from .. import shipItem, moduleItemFactory
from ..weapons import primaryWeapon, turretWeapon

itemConstructors = {"Ship": shipItem.Ship.deserialize,
                        "PrimaryWeapon": primaryWeapon.PrimaryWeapon.deserialize,
                        "ModuleItem": moduleItemFactory.deserialize,
                        "TurretWeapon": turretWeapon.TurretWeapon.deserialize}


def deserialize(toolDict : dict) -> toolItem.ToolItem:
    """Construct a toolItem from its dictionary-serialized representation.
    This method decodes which tool constructor is appropriate based on the 'type' attribute of the given dictionary.

    :param dict toolDict: A dictionary containing all information needed to construct the required toolItem. Critically,
                            a name, type, and builtIn specifier.
    :return: A new toolItem object as described in toolDict
    :rtype: toolItem.toolItem
    :raise NameError: When toolDict does not contain a 'type' attribute.
    """
    if "type" not in toolDict:
        raise NameError("Required dictionary attribute missing: 'type'")
    elif toolDict["type"] == "ToolItem":
        raise ValueError("Cannot deserialize abstract type 'ToolItem'")
    return toolTypeConstructors[toolDict["type"]](toolDict)


toolTypeConstructors = {"ShipSkinTool": shipSkinTool.ShipSkinTool.deserialize,
                        "CrateTool": crateTool.CrateTool.deserialize,
                        "ToolItem": deserialize,
                        "ShipSkinCrateTool": crateTool.ShipSkinCrateTool.deserialize,
                        "ThrowSnowballTool": throwSnowballTool.ThrowSnowballTool.deserialize}
itemConstructors.update(toolTypeConstructors)
