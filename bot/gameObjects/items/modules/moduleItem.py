from ..gameItem import GameItem
from ....cfg import bbData
from .... import lib
from typing import List


class ModuleItem(GameItem):
    """"An equippable item, providing ships with various stat perks and new functionality.
    All, none, or any combination of a moduleItem's attributes may be populated.

    :var armour: Provides an extra layer of health points ships must fight through before they can damage the ship's hull
    :vartype armour: int
    :var armourMultiplier: A percentage multiplier applied to the capacity of the ship's already active armour
    :vartype armourMultiplier: float
    :var shield: Provides another extra layer of health points ships must fight through before they can damage the ship's hull
    :vartype shield: int
    :var shieldMultiplier: A percentage multiplier applied to the capacity of the ship's already active shield
    :vartype shieldMultiplier: float
    :var dps: Provides an extra outlet of damage which can be directed towards a target.
                This one is unused as of yet, but you never know.
    :vartype dps: int
    :var dpsMultiplier: A percentage multiplier applied to the dps of all primary weapons equipped on the ship
    :vartype dpsMultiplier: float
    :var cargo: An additive increase to the amount of storage space available on the ship
    :vartype cargo: int
    :var cargoMultiplier: A multiplicative increase to the amount of storage space available on the ship
    :vartype cargoMultiplier: float
    :var handling: Provides an additive boost to the driveability of a ship (controls sensitivity)
    :vartype handling: int
    :var handlingMultiplier: A percentage multiplier applied to the ship's base handling
    :vartype handlingMultiplier: float
    """

    def __init__(self, name: str, aliases : List[str], armour : int = 0,
            armourMultiplier : float = 1.0, shield : int = 0, shieldMultiplier : float = 1.0,
            dps : int = 0, dpsMultiplier : float = 1.0, cargo : int = 0,
            cargoMultiplier : float = 1.0, handling : int = 0, handlingMultiplier : float = 1.0,
            value : int = 0, wiki : str = "", manufacturer : str = "", icon : str = "",
            emoji : lib.emojis.BasedEmoji = lib.emojis.BasedEmoji.EMPTY, techLevel : int = -1,
            builtIn : bool = False):
        """
        :param str name: The name of the module. Must be unique. (a model number is a good starting point)
        :param list[str] aliases: A list of alternative names this module may be referred to by.
        :param int armour: Provides an extra layer of health points ships must fight through
                            before they can damage the ship's hull (Default 0)
        :param float armourMultiplier: A percentage multiplier applied to the capacity of the ship's already
                                        active armour (Default 1)
        :param int shield: Provides another extra layer of health points ships must fight through before they
                            can damage the ship's hull (Default 0)
        :param float shieldMultiplier: A percentage multiplier applied to the capacity of the ship's already
                                        active shield (Default 1)
        :param int dps: Provides an extra outlet of damage which can be directed towards a target.
                        This one is unused as of yet, but you never know. (Default 0)
        :param float dpsMultiplier: A percentage multiplier applied to the dps of all primary weapons equipped
                                    on the ship (Default 1)
        :param int cargo: An additive increase to the amount of storage space available on the ship (Default 0)
        :param float cargoMultiplier: A multiplicative increase to the amount of storage space available
                                        on the ship (Default 1)
        :param int handling: Provides an additive boost to the driveability of a ship (controls sensitivity) (Default 0)
        :param float handlingMultiplier: A percentage multiplier applied to the ship's base handling (Default 1)
        :param int value: The number of credits that this module can be bought/sold for at a shop. (Default 0)
        :param str wiki: A web page that is displayed as the wiki page for this module. (Default "")
        :param str manufacturer: The name of the manufacturer of this module (Default "")
        :param str icon: A URL pointing to an image to use for this module's icon (Default "")
        :param lib.emojis.BasedEmoji emoji: The emoji to use for the module's small icon (Default lib.emojis.BasedEmoji.EMPTY)
        :param int techLevel: A rating from 1 to 10 of this item's technical advancement. Used as a measure for its
                                effectiveness compared to other modules of the same type (Default -1)
        :param bool builtIn: Whether this is a BountyBot standard module (loaded in from bbData) or a
                                custom spawned module (Default False)
        """
        super(ModuleItem, self).__init__(name, aliases, value=value, wiki=wiki, manufacturer=manufacturer, icon=icon,
                                            emoji=emoji, techLevel=techLevel, builtIn=builtIn)
        self.armour = armour
        self.armourMultiplier = armourMultiplier
        self.shield = shield
        self.shieldMultiplier = shieldMultiplier
        self.dps = dps
        self.dpsMultiplier = dpsMultiplier
        self.cargo = cargo
        self.cargoMultiplier = cargoMultiplier
        self.handling = handling
        self.handlingMultiplier = handlingMultiplier


    def statsStringShort(self) -> str:
        """Summarise all effects of this module as a string.
        This method should be overriden in any modules that implement custom behaviour, outside of simple stat boosts.

        :return: A string summarising the effects of this module when equipped to a ship
        :rtype: str
        """
        additiveStats = {   "Armour": self.armour, "Shield": self.shield, "Dps": self.dps,
                            "Cargo": self.cargo, "Handling": self.handling}
        multiplierStats = { "Armour": self.armourMultiplier, "Shield": self.shieldMultiplier, "Dps": self.dpsMultiplier,
                            "Cargo": self.cargoMultiplier, "Handling": self.handlingMultiplier}

        statsStr = "*"
        additiveStrs = (statName + ": " + lib.stringTyping.formatAdditive(additiveStats[statName])
                            for statName in additiveStats if additiveStats[statName] != 0)
        multiplierStrs = (statName + ": " + lib.stringTyping.formatMultiplier(multiplierStats[statName])
                            for statName in additiveStats if multiplierStats[statName] != 1)
        statsStr = ", ".join(tuple(additiveStrs) + tuple(multiplierStrs))

        return statsStr if len(statsStr) > 1 else "*No effect*"


    def toDict(self, **kwargs) -> dict:
        """Serialize this moduleItem into dictionary format, for saving to file.
        This method should be overriden and used as a base in any modules that implement
        custom behaviour, outside of simple stat boosts.
        For an example of using this toDict implementation as a base for an overridden implementation,
        please see a moduleItem class (e.g bbMiningDrillModule.py)

        :param bool saveType: When true, include the string name of the object type in the output.
        :return: A dictionary containing all information needed to reconstruct this module.
                    If the module is builtIn, this is only its name.
        :rtype: dict
        """
        if "saveType" not in kwargs:
            kwargs["saveType"] = True

        itemDict = super(ModuleItem, self).toDict(**kwargs)

        if not self.builtIn:
            additiveStats = {   "armour": self.armour, "shield": self.shield, "dps": self.dps,
                                "cargo": self.cargo, "handling": self.handling}
            multiplierStats = { "armour": self.armourMultiplier, "shield": self.shieldMultiplier, "dps": self.dpsMultiplier,
                                "cargo": self.cargoMultiplier, "handling": self.handlingMultiplier}

            for statName in additiveStats:
                if additiveStats[statName] != 0:
                    itemDict[statName] = additiveStats[statName]
            for statName in multiplierStats:
                if multiplierStats[statName] != 1:
                    itemDict[statName] = multiplierStats[statName]

        return itemDict


    @classmethod
    def fromDict(cls, moduleDict : dict, **kwargs):
        """Factory function constructing a new moduleItem object from a dictionary serialised
        representation - the opposite of moduleItem.toDict. This generic module factory function is unlikely
        to ever be called, your module type-specific fromDict should be used instead. Except of course, in the
        case of custom-spawned, custom-typed modules which do not correspond to a BountyBot-known module type.

        :param dict moduleDict: A dictionary containing all information needed to construct the desired moduleItem
        :return: A new moduleItem object as described in moduleDict
        :rtype: moduleItem
        """
        return ModuleItem(**cls._makeDefaults(moduleDict, ignores=("type",),
                                                emoji=lib.emojis.BasedEmoji.fromStr(moduleDict["emoji"]) \
                                                        if "emoji" in moduleDict else lib.emojis.BasedEmoji.EMPTY))
