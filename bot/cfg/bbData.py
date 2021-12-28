from discord import Colour
from ..lib.emojis import UninitializedBasedEmoji

# all factions recognised by BB
factions = ["terran", "vossk", "midorian", "nivelian", "neutral"]
# all factions useable in bounties
bountyFactions = ["terran", "vossk", "midorian", "nivelian"]
# Dicord emoji IDs for all factions
bountyFactionEmojis = {"terran": 849316423800979528, "vossk": 849316423595720795,
                        "midorian": 849316424270741504, "nivelian": 849316423808581703}

# levels of security in SolarSystems (SolarSystem security is stored as an index in this list)
securityLevels = ["secure", "average", "risky", "dangerous"]

# map image URLS for cmd_map
mapImageWithGraphLink = "https://cdn.discordapp.com/attachments/700683544103747594/700683693215318076/gof2_coords.png"
mapImageNoGraphLink = 'https://i.imgur.com/TmPgPd3.png'

# icons for factions
factionIcons = {"terran": "https://cdn.discordapp.com/attachments/700683544103747594/711013574331596850/terran.png",
                "vossk": "https://cdn.discordapp.com/attachments/700683544103747594/711013681621893130/vossk.png",
                "midorian": "https://cdn.discordapp.com/attachments/700683544103747594/711013601019691038/midorian.png",
                "nivelian": "https://cdn.discordapp.com/attachments/700683544103747594/711013623257890857/nivelian.png",
                "neutral":
                    "https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/twitter/248/rocket_1f680.png",
                "void": "https://cdn.discordapp.com/attachments/700683544103747594/711013699841687602/void.png"}

errorIcon = "https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/twitter/248/exclamation-mark_2757.png"
winIcon = "https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/twitter/248/trophy_1f3c6.png"
rocketIcon = "https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/twitter/248/rocket_1f680.png"

# colours to use in faction-related embed strips
factionColours = {  "terran": Colour.gold(),
                    "vossk": Colour.dark_green(),
                    "midorian": Colour.dark_red(),
                    "nivelian": Colour.dark_blue(),
                    "neutral": Colour.purple()}

# Data representing all ship items in the game. These are used to create bbShip objects,
# which are stored in builtInShipObjs in a similar dict format.
# Ships to not have tech levels in GOF2, so tech levels will be automaticaly generated
# for the sake of the bot during bot.on_ready.
builtInShipData = {}

def findShipDataByAlias(shipName: str, ignoreCase: bool = True) -> dict:
    """Look up ship data in builtInShipData by name or alias

    :param shipName: The name of the ship to find
    :type shipName: str
    :param ignoreCase: Whether or not to allow casing discrepencies in the ship name (Default True)
    :type ignoreCase: bool, optional
    :raises KeyError: If no ship data could be found withh the given name
    :return: The ship data, which could be deserialized into a Ship object
    :rtype: dict
    """
    try:
        return next(
            i for i in builtInShipData.values()
            if shipName == i["name"].lower() \
            or shipName in \
                ([n.lower() for n in i.get("aliases", [])] \
                if ignoreCase else \
                i.get("aliases", []))
        )
    except StopIteration:
        raise KeyError(f"Unknown ship: {shipName}")


# Data representing all module items in the game. These are used to create bbModule objects,
# which are stored in builtInModuleObjs in a similar dict format.
builtInModuleData = {}

# Data representing all primary weapon items in the game. These are used to create bbWeapon objects,
# which are stored in builtInWeaponObjs in a similar dict format.
builtInWeaponData = {}

# Data representing all ship upgrades in the game. These are used to create bbShipUpgrade objects,
# which are stored in builtInUpgradeObjs in a similar dict format.
builtInUpgradeData = {}

# data for builtIn criminals to be used in Criminal.fromDict
# criminals marked as not builtIn to allow for dictionary init.
# The criminal object is then marked as builtIn during bot.on_ready
builtInCriminalData = {}

# data for builtIn systems to be used in SolarSystem.fromDict
builtInSystemData = {}

# data for builtIn Turrets to be used in bbTurret.fromDict
builtInTurretData = {}

# data for builtIn commodities to be used in bbCommodity.fromDict (unimplemented)
builtInCommodityData = {}

builtInToolData = {}

# data for builtIn secondaries to be used in bbSecondary.fromDict (unimplemented)
builtInSecondariesData = {}

# data for builtIn ShipSkins to be used in ShipSkin.fromDict
builtInShipSkinsData = {}

# data for Medals to be used in Medal.fromDict. builtIn is not applicable to Medals, as custom Medals cannot be created
medalsData = {}


# To be populated during bot.on_ready
# These dicts contain item name: item object for the object described in the variable name.
builtInShipSkins = {}
builtInToolObjs = {}
builtInSystemObjs = {}
builtInCriminalObjs = {}
builtInModuleObjs = {}
builtInWeaponObjs = {}
builtInUpgradeObjs = {}
builtInTurretObjs = {}
medalObjs = {}

# References to the above item objects, sorted by techLevel.
shipKeysByTL = []
moduleObjsByTL = []
weaponObjsByTL = []
turretObjsByTL = []


# names of criminals in builtIn bounties
bountyNames = {}
# the length of the longest criminal name, to be used in padding during cmd_bounties
longestBountyNameLength = 0

shipSkinToolsBySkin = {}
# Dict of crate type (str) : list of crates
builtInCrateObjs = {}


# Profile Customisation items
# XP bar fills
builtInXPBars = {}
