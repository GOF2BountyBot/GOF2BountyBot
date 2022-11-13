
from typing import Callable, Iterable, List, TYPE_CHECKING, Sequence, Tuple, cast
from discord import Interaction
from discord import app_commands
import heapq

from ...cfg import cfg, bbData
from ...baseClasses.aliasable import AliasableMixin
from ... import client
from ...users import basedUser
from ...gameObjects.items import gameItem
from ...lib.stringTyping import stringDifference
from ...gameObjects.inventories import inventoryListing

if TYPE_CHECKING:
    from ...databases import bountyDB

MAX_CHOICES = 25

lowerSystems = {}
lowerSystemKeys = []
first25 = []


def _stringAutoComplete(getPossibleChoices: Callable[[], Sequence[str]]):
    async def inner(interaction: Interaction, current: str):
        possibleChoices = getPossibleChoices()
        if current == "":
            bestChoices = possibleChoices[:min(MAX_CHOICES, len(possibleChoices) - 1)]
        elif len(possibleChoices) <= MAX_CHOICES:
            bestChoices = possibleChoices
        else:
            bestChoices = heapq.nsmallest(MAX_CHOICES, possibleChoices, lambda x: stringDifference(x, current))
        return [app_commands.Choice(name=i, value=i) for i in bestChoices]
    return inner



def _aliasableAutoComplete(getPossibleChoices: Callable[[], Sequence[AliasableMixin]]):
    async def inner(interaction: Interaction, current: str) -> List[app_commands.Choice[str]]:
        possibleChoices = getPossibleChoices()
        if current == "":
            bestChoices = possibleChoices[:min(MAX_CHOICES, len(possibleChoices) - 1)]
        else:
            firstLower = current[0].lower()
            matchStartChoices = [i for i in possibleChoices if i.name[0].lower() == firstLower]
            if matchStartChoices:
                possibleChoices = matchStartChoices
            bestChoices = heapq.nsmallest(min(MAX_CHOICES, len(possibleChoices)), possibleChoices, lambda x: x.mostSimilarAlias(current)[0])
        return [app_commands.Choice(name=i.name, value=i.name) for i in bestChoices]
    return inner


"""
def _aliasableAutoComplete(getPossibleChoices: Callable[[], Sequence[AliasableMixin]]):
    async def inner(interaction: Interaction, current: str) -> List[app_commands.Choice[str]]:
        global lowerSystems
        global first25
        global lowerSystemKeys
        if lowerSystems == {}:
            lowerSystems.update({s.name.lower(): s for s in bbData.builtInSystemObjs.values()})
            lowerSystemKeys += list(lowerSystems.keys())
            first25 += lowerSystemKeys[:min(MAX_CHOICES, len(lowerSystemKeys) - 1)]
        if current == "":
            bestChoices = first25
        else:
            firstLower = current[0].lower()
            matchStartChoices = [i for i in lowerSystemKeys if i[0] == firstLower]
            if matchStartChoices:
                possibleChoices = matchStartChoices
            else: possibleChoices = lowerSystemKeys
            if len(possibleChoices) <= MAX_CHOICES:
                bestChoices = possibleChoices
            else:
                bestChoices = heapq.nsmallest(min(MAX_CHOICES, len(possibleChoices)), possibleChoices, lambda x: x.mostSimilarAlias(current)[0])
        return [app_commands.Choice(name=lowerSystems[i].name, value=lowerSystems[i].name) for i in bestChoices]
    return inner
"""

#region division

DIVISION_CHOICES = cfg.bountyDivisionNames

DIVISION_CHOICES_WITH_ALL = DIVISION_CHOICES + ["all"]


def divisionAutoComplete(paramName: str = "division", allowAllDivisions: bool = True):
    """A decorator to add autocomplete for a single-value bounty division parameter, by name.

    :param paramName: The name of the division name parameter
    :type paramName: str
    :param allowAllDivisions: Whether or not "all" is allowed
    :type allowAllDivisions: bool
    """
    def decorator(func: app_commands.Command):
        if allowAllDivisions:
            func.autocomplete(paramName)(_stringAutoComplete(lambda: DIVISION_CHOICES))
        else:
            func.autocomplete(paramName)(_stringAutoComplete(lambda: DIVISION_CHOICES_WITH_ALL))
        return func
    return decorator

#endregion division
#region system

def systemAutoComplete(paramName: str = "system"):
    """A decorator to add autocomplete for a single-value solar system parameter, by name.

    :param paramName: The name of the solar system name parameter
    :type paramName: str
    """
    def decorator(func: app_commands.Command):
        func.autocomplete(paramName)(_aliasableAutoComplete(lambda: list(bbData.builtInSystemObjs.values())))
        return func
    return decorator

#endregion system
#region criminal

def criminalAutoComplete(paramName: str = "name"):
    """A decorator to add autocomplete for a single-value criminal parameter, by name.

    :param paramName: The name of the criminal name parameter
    :type paramName: str
    """
    def decorator(func: app_commands.Command):
        func.autocomplete(paramName)(_aliasableAutoComplete(lambda: list(bbData.builtInCriminalObjs.values())))
        return func
    return decorator


async def _activeCriminalAutoComplete(interaction: Interaction, current: str) -> List[app_commands.Choice]:
    if not isinstance(interaction.client, client.BasedClient):
        raise TypeError(f"{activeCriminalAutoComplete.__name__} can only be applied to commands which are handled by a {client.BasedClient.__name__}")

    if not interaction.guild: return []
    if not interaction.client.guildsDB.idExists(interaction.guild.id): return []

    guild = interaction.client.guildsDB.getGuild(interaction.guild.id)
    if guild.bountiesDisabled: return []

    # casting here due to the bountiesDisabled check above
    bountiesDB = cast("bountyDB.BountyDB", guild.bountiesDB)
    
    criminals = set()
    choices = []
    
    for div in bountiesDB.divisions.values():
        for bounty in div.allBounties():
            if bounty.criminal in criminals: continue
            criminals.add(bounty.criminal)

            if bounty.criminal.isPlayer:
                userId = int(bounty.criminal.name.lstrip("<@!").rstrip(">"))
                dcUser = interaction.client.get_user(userId) or await interaction.client.tryFetchUser(userId)
                bountyName = f"<Player {userId}>" if dcUser is None else str(dcUser)

            else:
                bountyName = bounty.criminal.name
            
            if current in bountyName:
                choices.append(app_commands.Choice(name=bountyName, value=bountyName))
                if len(choices) == MAX_CHOICES:
                    break

    return choices
    

def activeCriminalAutoComplete(paramName: str = "name"):
    """A decorator to add autocomplete for a single-value criminal parameter, by name.
    This decorator is different to `criminalAutoComplete` because it inspects the active criminals in the guild.
    This is useful for limiting the potential options, but also for allowing selection of players and non-builtIn criminals.
    Criminals will be listed across all divisions.
    
    :param paramName: The name of the criminal name parameter
    :type paramName: str
    """
    def decorator(func: app_commands.Command):
        func.autocomplete(paramName)(_activeCriminalAutoComplete)
        return func
    return decorator

#endregion criminal
#region faction

async def _factionAutoComplete(interaction: Interaction, current: str):
    choices = []
    for faction in bbData.factions:
        if current in faction:
            choices.append(app_commands.Choice(name=faction, value=faction))
            if len(choices) == MAX_CHOICES:
                break
    return choices


async def _factionAutoCompleteBountyFactionsOnly(interaction: Interaction, current: str):
    choices = []
    for faction in bbData.bountyFactions:
        if current in faction:
            choices.append(app_commands.Choice(name=faction, value=faction))
            if len(choices) == MAX_CHOICES:
                break
    return choices


def factionAutoComplete(paramName: str = "faction", bountyFactionsOnly: bool = True):
    """A decorator to add autocomplete for a single-value faction parameter, by name.

    :param paramName: The name of the faction name parameter
    :type paramName: str
    :param bountyFactionsOnly: Whether to use bbData.bountyFactions instead of bbData.factions
    :type allowAllDivisions: bool
    """
    def decorator(func: app_commands.Command):
        if bountyFactionsOnly:
            func.autocomplete(paramName)(_factionAutoCompleteBountyFactionsOnly)
        else:
            func.autocomplete(paramName)(_factionAutoComplete)
        return func
    return decorator

#endregion faction
#region item-ship

ITEM_CHOICES_SHIP: Iterable[app_commands.Choice[str]] = sorted(set(
    [
        app_commands.Choice(name=shipName, value=shipName)
        for shipName in bbData.builtInShipData
    ]),
    key=lambda c: c.name)

# async def _shipAutoComplete(interaction: Interaction, current: str):
#     choices = []
#     for d in ITEM_CHOICES_SHIP:
#         if current in d.name:
#             choices.append(d)
#             if len(choices) == MAX_CHOICES:
#                 break
#     return choices

async def _shipAutoComplete(interaction: Interaction, current: str) -> List[app_commands.Choice[str]]:
    possibleChoices = list(bbData.builtInShipData.values())
    if current == "":
        bestChoices = possibleChoices[:min(MAX_CHOICES, len(possibleChoices) - 1)]
    else:
        firstLower = current[0].lower()
        matchStartChoices = [i for i in possibleChoices if i["name"][0].lower() == firstLower]
        if matchStartChoices:
            possibleChoices = matchStartChoices
        bestChoices = heapq.nsmallest(min(MAX_CHOICES, len(possibleChoices)), possibleChoices, lambda x: stringDifference(x["name"], current))
    return [app_commands.Choice(name=i["name"], value=i["name"]) for i in bestChoices]


def shipAutoComplete(paramName: str = "ship"):
    """A decorator to add autocomplete for a single-value ship parameter, by name.

    :param paramName: The name of the ship name parameter
    :type paramName: str
    """
    def decorator(func: app_commands.Command):
        func.autocomplete(paramName)(_shipAutoComplete)
        return func
    return decorator

#endregion item-ship
#region item-ship-skin

ITEM_CHOICES_SHIP_SKIN: Iterable[app_commands.Choice[str]] = sorted(set(
    [
        app_commands.Choice(name=skinName, value=skinName)
        for skinName in bbData.builtInShipSkins
    ]),
    key=lambda c: c.name)

async def _shipSkinAutoComplete(interaction: Interaction, current: str):
    choices = []
    for d in ITEM_CHOICES_SHIP_SKIN:
        if current in d.name:
            choices.append(d)
            if len(choices) == MAX_CHOICES:
                break
    return choices


def shipSkinAutoComplete(paramName: str = "skin"):
    """A decorator to add autocomplete for a single-value ship skin parameter, by name.

    :param paramName: The name of the ship skin name parameter
    :type paramName: str
    """
    def decorator(func: app_commands.Command):
        func.autocomplete(paramName)(_stringAutoComplete(lambda: list(bbData.builtInShipSkins.keys())))
        # func.autocomplete(paramName)(_shipSkinAutoComplete)
        return func
    return decorator

#endregion item-ship-skin
#region item-module

def moduleAutoComplete(paramName: str = "module"):
    """A decorator to add autocomplete for a single-value module parameter, by name.

    :param paramName: The name of the module name parameter
    :type paramName: str
    """
    def decorator(func: app_commands.Command):
        func.autocomplete(paramName)(_aliasableAutoComplete(lambda: list(bbData.builtInModuleObjs.values())))
        return func
    return decorator

#endregion item-module
#region item-weapon

def weaponAutoComplete(paramName: str = "weapon"):
    """A decorator to add autocomplete for a single-value primary weapon parameter, by name.

    :param paramName: The name of the weapon name parameter
    :type paramName: str
    """
    def decorator(func: app_commands.Command):
        func.autocomplete(paramName)(_aliasableAutoComplete(lambda: list(bbData.builtInWeaponObjs.values())))
        return func
    return decorator

#endregion item-weapon
#region item-turret

def turretAutoComplete(paramName: str = "turret"):
    """A decorator to add autocomplete for a single-value turret parameter, by name.

    :param paramName: The name of the turret name parameter
    :type paramName: str
    """
    def decorator(func: app_commands.Command):
        func.autocomplete(paramName)(_aliasableAutoComplete(lambda: list(bbData.builtInTurretObjs.values())))
        return func
    return decorator

#endregion item-turret
#region item-tool

def toolAutoComplete(paramName: str = "tool"):
    """A decorator to add autocomplete for a single-value tool parameter, by name.

    :param paramName: The name of the tool name parameter
    :type paramName: str
    """
    def decorator(func: app_commands.Command):
        func.autocomplete(paramName)(_aliasableAutoComplete(lambda: list(bbData.builtInToolObjs.values())))
        return func
    return decorator

#endregion item-tool
#region item-medal

def medalAutoComplete(paramName: str = "medal"):
    """A decorator to add autocomplete for a single-value medal parameter, by name.

    :param paramName: The name of the medal name parameter
    :type paramName: str
    """
    def decorator(func: app_commands.Command):
        func.autocomplete(paramName)(_stringAutoComplete(lambda: list(bbData.medalObjs.keys())))
        return func
    return decorator

#endregion item-medal
#region inventory

def _make_inventoryCategoryItemNumberAutoComplete(category: bbData.ItemCategory, fallbackOnDefaultUser: bool):
    async def _inventoryCategoryItemNumberAutoComplete(interaction: Interaction, current: str) -> List[app_commands.Choice[str]]:
        if not isinstance(interaction.client, client.BasedClient):
            raise TypeError(f"This decorator can only be applied to commands which are managed by a BasedClient")

        choices: List[app_commands.Choice[str]] = []
        if interaction.client.usersDB.idExists(interaction.user.id):
            bUser = interaction.client.usersDB.getUser(interaction.user.id)
            for itemNum, item in enumerate(bUser.getInventory(category).items.keys()):
                if current in item.name:
                    choices.append(app_commands.Choice(name=item.name, value=str(itemNum)))
                    if len(choices) == MAX_CHOICES:
                        break
        
        elif fallbackOnDefaultUser:
            defaultItems = cast(List[gameItem.SerializedGameItemUnion], basedUser.defaultUserDict.get(basedUser.itemCategoryUserKeys[category], []))
            for itemNum, item in enumerate(defaultItems):
                if current in item["name"]:
                    choices.append(app_commands.Choice(name=item["name"], value=str(itemNum)))
                    if len(choices) == MAX_CHOICES:
                        break
        
        return choices
    return _inventoryCategoryItemNumberAutoComplete


def inventoryItemNumberAutoComplete(paramName: str, itemCategory: bbData.ItemCategory):
    """A decorator to add autocomplete for a single-value item reference parameter.
    The items will appear as names in discord, but returned to code as item indices.
    Only applies to a single inventory on the user (or default user) at this time.

    Discord requires that autocomplete return Choices with str values, but item indices are int.
    TODO: This is untested, but you might need to convert to int before usage in the command.
    I would just use List[Choice[int]], but pyright complains saying it has to be str

    :param paramName: The name of the item number parameter
    :type paramName: str
    :param itemCategory: The inventory to select items from
    :type itemCategory: ItemCategory
    """
    def decorator(func: app_commands.Command):
        autocomplete = _make_inventoryCategoryItemNumberAutoComplete(itemCategory, True)
        # TODO: Apparently my autocomplete is of the wrong type?
        func.autocomplete(paramName)(autocomplete)
        return func
    return decorator


ITEM_TYPE_IDS = {
    bbData.ItemCategory.module: "0",
    bbData.ItemCategory.ship: "1",
    bbData.ItemCategory.tool: "2",
    bbData.ItemCategory.turret: "3",
    bbData.ItemCategory.weapon: "4"
}

ID_ITEM_TYPES = {v: k for k, v in ITEM_TYPE_IDS.items()}

def anyUserHangerItemAutoComplete_decodeValue(v: str) -> Tuple[bbData.ItemCategory, int]:
    return ID_ITEM_TYPES[v[0]], int(v[1:])

def _make_anyUserHangerItemAutoComplete(fallbackOnDefaultUser: bool):
    async def _anyUserHangerItemAutoComplete(interaction: Interaction, current: str) -> List[app_commands.Choice[str]]:
        if not isinstance(interaction.client, client.BasedClient):
            raise TypeError(f"This decorator can only be applied to commands which are managed by a BasedClient")

        choices: List[app_commands.Choice[str]] = []
        if interaction.client.usersDB.idExists(interaction.user.id):
            bUser = interaction.client.usersDB.getUser(interaction.user.id)
            for category in ITEM_TYPE_IDS.keys():
                for itemNum, item in enumerate(bUser.getInventory(category).items.keys()):
                    if current in item.name:
                        choices.append(app_commands.Choice(name=f"{category.value.title()}: {item.name}", value=f"{ITEM_TYPE_IDS[category]}{itemNum+1}"))
                        if len(choices) == MAX_CHOICES:
                            break
        
        elif fallbackOnDefaultUser:
            for category in ITEM_TYPE_IDS.keys():
                defaultItems = cast(List[inventoryListing.SerializedInventoryListing[gameItem.SerializedGameItemUnion]], basedUser.defaultUserDict.get(basedUser.itemCategoryUserKeys[category], []))
                for itemNum, listing in enumerate(defaultItems):
                    if current in listing["item"]["name"]:
                        choices.append(app_commands.Choice(name=f"{category.value.title()}: {listing['item']['name']}", value=f"{ITEM_TYPE_IDS[category]}{itemNum+1}"))
                        if len(choices) == MAX_CHOICES:
                            break
        
        return choices
    return _anyUserHangerItemAutoComplete


def anyUserHangerItemAutoComplete(paramName: str = "item"):
    """A decorator to add autocomplete for a single-value item reference parameter.
    The items will appear as names in discord, but returned to code as an encoded (item type (ItemCategory), item index (int)) tuple.
    Retrieve this tuple with the anyUserHangerItemAutoComplete_decodeValue function.

    Will always show all items of all categories on the user (or default user) at this time.

    :param paramName: The name of the item number parameter
    :type paramName: str
    """
    def decorator(func: app_commands.Command):
        autocomplete = _make_anyUserHangerItemAutoComplete(True)
        func.autocomplete(paramName)(autocomplete)
        return func
    return decorator

#endregion inventory