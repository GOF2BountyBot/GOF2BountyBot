from . import toolItem, shipSkinTool, crateTool
from .. import shipItem, moduleItemFactory
from ..weapons import primaryWeapon, turretWeapon
from .... import lib


def fromDict(toolDict : dict) -> toolItem.ToolItem:
    """Construct a toolItem from its dictionary-serialized representation.
    This method decodes which tool constructor is appropriate based on the 'type' attribute of the given dictionary.

    :param dict toolDict: A dictionary containing all information needed to construct the required toolItem. Critically,
                            a name, type, and builtIn specifier.
    :return: A new toolItem object as described in toolDict
    :rtype: toolItem.toolItem
    :raise NameError: When toolDict does not contain a 'type' attribute.
    """

    itemConstructors = {"Ship": shipItem.Ship.fromDict,
                        "PrimaryWeapon": primaryWeapon.PrimaryWeapon.fromDict,
                        "ModuleItem": moduleItemFactory.fromDict,
                        "TurretWeapon": turretWeapon.TurretWeapon.fromDict,
                        "ToolItem": fromDict}

    def crateFromDict(crateDict):
        if "itemPool" not in crateDict:
            raise RuntimeError("Attempted to fromDict a crate with no itemPool field: " + str(crateDict))
        itemPool = []
        for itemDict in crateDict["itemPool"]:
            if "itemType" in itemDict:
                itemPool.append(itemConstructors[itemDict["itemType"]](itemDict))
            else:
                itemPool.append(itemConstructors[itemDict["type"]](itemDict))

        return crateTool.CrateTool(itemPool, name=crateDict["name"] if "name" in crateDict else "",
            value=crateDict["value"] if "value" in crateDict else 0,
            wiki=crateDict["wiki"] if "wiki" in crateDict else "",
            manufacturer=crateDict["manufacturer"] if "manufacturer" in crateDict else "",
            icon=crateDict["icon"] if "icon" in crateDict else "",
            emoji=lib.emojis.BasedEmoji.fromDict(crateDict["emoji"]) if "emoji" in crateDict else lib.emojis.BasedEmoji.EMPTY,
            techLevel=crateDict["techLevel"] if "techLevel" in crateDict else -1,
            builtIn=crateDict["builtIn"] if "builtIn" in crateDict else False)

    toolTypeConstructors = {"ShipSkinTool": shipSkinTool.ShipSkinTool.fromDict,
                        "CrateTool": crateFromDict}

    if "type" not in toolDict:
        raise NameError("Required dictionary attribute missing: 'type'")
    return toolTypeConstructors[toolDict["type"]](toolDict)
