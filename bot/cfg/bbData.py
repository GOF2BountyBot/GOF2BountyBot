from discord import Colour
from ..lib.emojis import UninitializedBasedEmoji
from datetime import timedelta

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

drinkMessages = [
    "An Aquila Cocktail, just for you. <:Aquila:925539224445407324>",
    "Augmenta Fizz good enough? <:Augmenta:925539224793513994>",
    "Can I interest you in a Buntta Aperitif? <:Bunatta:925539224931938344>",
    "An Eanya Tonic, straight up. <:Eanya:925539224608985129>",
    "K'ontrr Dishwater? It tastes better than it sounds, I assure you. <:Kontrr:925539225007435828>",
    "Fancy a Magnetar Juice? <:Magnetar:925539225192005642>",
    "Some Mido Distillate might wake you up. <:MidoDist:925539225066160159>",
    "Nesla Brandy? Only the finest! <:Nesla:925539225250693170>",
    "I have some Ni'mrodd Muck for you. Careful, it's... thick. <:Nimrodd:925539225133264936>",
    "Oom'bak Gin. Puts lead in your T'yool. <:Oombak:925539224936149054>",
    "Have a Prospero Flip, you could use it. <:Prospero:925539225120682076>",
    "Looks like you need a Suteo Liquor. Don't drink to much though. Seriously. <:Sueto:925539225384931418>",
    "Ahh, S'kolptorr Rum. Drink, up... pirate. <:Skolptorr:925539225221345352>",
    "A Union Draught for you. <:Union:925539225456234496>",
    "Ah, Pescal Inartu brew. Love the sound of it. <:Pescal:925539225221333063>",
    "Here, have some Weymire Punch. Just one, remember. <:Weymire:925539225405882398>",
    "Since you are a guest... V'ikka Moonshine, on the house. Just this once though. <:Vikka:925539225317814312>",
    "Can I offer some fresh Vulpes Soup? Still hot! <:Vulpes:925539225389133824>",
    "One Loma Rum! Enjoy your stay. <:Loma:925539224994873365>",
    "Have a Shima Vapour on the house. Only at Kaamo! <:Shima:925539225426862090>",
    "I think the real reason behind the mining plant at Coromesk is to create Skavac Mercury. What a great drink. <:Skavac:925539226253140029>",
    "Wah'norr Glop. Way nicer than it sounds, promise. <:Glop:925539226198622208>",
    "The Skor Terpa Surprise was named after the suprise you get when you arrive at Skor Terpa. Surprise! <:Terpa:925539225489784832>",
    "M’Kali Slime isn’t so common with bipeds, but the Octopods love it. Be sure to have some K’mirrk Toad Mutagen nearby. <:mkali:925805795013193839>",
    "Porros Tea. Shatteringly delicious. <:porros:925806114971459645>"
]

premiumDrinkMessages = [
    "Here we are. A Flabbergaster speciality, with a side of Mutagen. Be careful! <:flabbergaster:925806889537781781> <:Kmirrk:925539224961318944>",
    "Beidan Champagne is very rare and exclusive. An extra 3000$ has been billed to your account. Enjoy! <:Beidan:925539224852254800>",
    "I'm not even sure where Wolf-Reiser is, but I hear their brandy is excellent. Try it! <:Wolf:925539225556885565>",
    "Alda... poison? I'm sure it's just a fancy name for... water. Bottoms up! <:Alda:925539225674342420>",
    "Y'mirr Schnapps is said to be quite pungent. You'll love it...! <:Ymirr:925539225410097182>",
    "Would a Pan Whiskey interest you? <:Pan:925539225183596575>",
    "Behen wine, good sir? <:Behen:925539224994865153>",
    "Ginoya Firewater. Concentrated and liquified ore from the asteroi-- oh, I'm sure you don't care. Drink this with caution. <:Ginoya:925808087871418428>",
    "Talidor Mist? A fine choice. 10x clearer than regular H2O! <:Talidor:925808443191877682>",
    "Her Jaza Java is possibly the strongest coffee in the galaxy. Rumour has it that it could power an entire station if there was a large enough quantity. <:Jaza:925539224973877348>",
    "Ah, one tasty Pareáh Prism coming up-- <:Pareah:925539227154935859> wait, that's not for you... how did this get here? Sorry about that, can I get you another drink?",
    "Trim on Ice is the actual name for this drink. It’s cold, like space. Try it! <:Trim:925808882390011944>",
    "Ah, Void Euphorium. This stuff is the good stuff. Drink too much and you might see the entire universe... literally! <:VoidDrink:925539225452027935>",
    "I recommend the Rigant Mix. Looks a bit weird, but it really sucks you in. <:rigant:925809129539371008>"
]

premiumTimeoutMessage = "I'm sorry, we've run out for just now! Please wait for stocks to be refilled. Maybe ten minutes or so."
nextPremium = None
premiumTimeout = timedelta(minutes=10)
