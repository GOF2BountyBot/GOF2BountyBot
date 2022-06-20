from ...cfg import bbData
from .modules import _all as moduleItemClasses
from .modules import ModuleItem

typeConstructors = {cls.__name__: cls.deserialize for cls in moduleItemClasses}


def deserialize(moduleDict):
    """Factory function recreating any moduleItem or moduleItem subtype from a dictionary-serialized representation.
    If implemented correctly, this should act as the opposite to the original object's serialize method.
    If the requested module is builtIn, return the builtIn module object of the same name.

    :param dict moduleDict: A dictionary containg all information necessary to create the desired moduleItem object
    :return: The moduleItem object described in moduleDict
    :rtype: moduleItem
    """
    if moduleDict.get("builtIn", False):
        return bbData.builtInModuleObjs[moduleDict["name"]]
    else:
        if "type" in moduleDict and moduleDict["type"] in typeConstructors:
            return typeConstructors[moduleDict["type"]](moduleDict)
        else:
            return ModuleItem.deserialize(moduleDict)
