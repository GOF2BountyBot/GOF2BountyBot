
from typing import Any, Callable, Dict, List, TYPE_CHECKING, Optional, Sequence, Tuple, TypeVar, cast, Coroutine
from discord import Interaction
from discord import app_commands
from discord.app_commands.commands import CommandCallback, P as TParams, GroupT as TCommandGroup, T as TReturn
from discord.app_commands import Transformer, Transform
import heapq
from functools import wraps

from ...cfg import cfg, bbData
from ...baseClasses.aliasable import AliasableMixin
from ... import client, lib
from ...lib import gameMaths
from ...users import basedUser
from ...gameObjects.items import gameItem
from ...lib.stringTyping import stringDifference
from ...gameObjects.inventories import inventoryListing

if TYPE_CHECKING:
    from ...databases import bountyDB, bountyDivision
    from ...gameObjects.bounties import bounty


MAX_CHOICES = 25

lowerSystems = {}
lowerSystemKeys = []
first25 = []

TCommandCallback = TypeVar("TCommandCallback", bound=CommandCallback)
TCommand = TypeVar("TCommand", bound=app_commands.Command)

#region aliasable utils

TAliasable = TypeVar("TAliasable", bound=AliasableMixin)
def aliasableLookup(items: Dict[str, TAliasable], name: str) -> Optional[str]:
    """Try to find a object in `items` that is called `name`. If one can be found, return that object's key in `items`.
    If none can be found, return `None`.
    This function is very expensive; linear in the number of keys in `items`.

    :param items: The aliasables in which to look for a match
    :type items: Dict[str, TAliasable]
    :param name: The candidate name to look up
    :type name: str
    :return: The dictionary key of the matching item in `items` if one exists, otherwise `None`
    :rtype: Optional[str]
    """
    for k, i in items.items():
        if i.isCalled(name):
            return k
    return None


def _aliasableAutoComplete(getPossibleChoices: Callable[[], Sequence[AliasableMixin]]):
    """Construct an autocomplete callback that finds the `MAX_CHOICES` most similar matches to the input string from a list of candidate aliasables.
    Matches are made based on *aliases*.

    :param getPossibleChoices: A callback to get the list of candidate aliasable objects
    :type getPossibleChoices: Callable[[], Sequence[str]]
    """
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


async def _aliasableVerify(interaction: Interaction, value: str, possibleChoices: Dict[str, TAliasable], objectTypeName: str) -> str:
    """Verify that the given value matches the name of an aliasable in `possibleChoices`.

    The use case for this function is for application to a Command that takes an Aliasable reference as a parameter.
    Aliasable databases are typically too large for use as command *choices*, so instead we use *autocomplete*.
    But autocomplete can be skipped, and any value submitted at all.

    In the case where the user disregards autocomplete, this verifier can be used as a fallback, to look up the unknown string
    as an alias for an item of `possibleChoices`. If a match is found, the correct name is reurned.
    If no match can be found, an error is displayed containing `objectTypeName`, and a `ValueError` is thrown.

    :param Intraction interaction: The interaction that triggered this verification, used to send errors
    :param str value: The value that the user submitted
    :param possibleChoices: The dictionary of possible choices
    :type possibleChoices: Dict[str, TAliasable]
    :param str objectTypeName: A user-friendly name for the types of objects in `possibleChoices`, for use in error messages
    :return: `value` as it appears in `possibleChoices`, with respect to aliases, casing etc.
    :rtype: str
    """
    if value in possibleChoices:
        return value
    if value.lower() in possibleChoices:
        return value.lower()
    if value.title() in possibleChoices:
        return value.title()
    
    matchedCandidate = aliasableLookup(possibleChoices, value)

    if matchedCandidate is None:
        await interaction.response.send_message(f":x: Unknown {objectTypeName}: {value}", ephemeral=True)
        raise ValueError(f":x: Unknown {objectTypeName}: {value}")
    
    return matchedCandidate

#endregion
#region string utils

def _stringAutoComplete(getPossibleChoices: Callable[[], Sequence[str]]):
    """Construct an autocomplete callback that finds the `MAX_CHOICES` most similar matches to the input string from a list of candidate strings.

    :param getPossibleChoices: A callback to get the list of candidate strings
    :type getPossibleChoices: Callable[[], Sequence[str]]
    """
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


async def _stringVerify(interaction: Interaction, value: str, possibleChoices: Sequence[str], objectTypeName: str) -> str:
    """Verify that the given value matches a value in `possibleChoices`.

    The use case for this function is for application to a Command that takes a string as a parameter, from a predetermined
    but list of accepted values that is too large for use as command *choices*, so instead we use *autocomplete*.
    But autocomplete can be skipped, and any value submitted at all.

    In the case where the user disregards autocomplete, this verifier can be used as a fallback, to look up the given value
    in `possibleChoices`. If a match is found, ignoring case, the appropriate value is returned, with the expected casing.
    If no match can be found, an error is displayed containing `objectTypeName`, and a `ValueError` is thrown.

    :param Intraction interaction: The interaction that triggered this verification, used to send errors
    :param str value: The value that the user submitted
    :param possibleChoices: The possible choices
    :type possibleChoices: Sequence[str]
    :param objectTypeName: A user-friendly name for the types of objects in `possibleChoices`, for use in error messages
    :type objectTypeName: str
    :return: `value` as it appears in `possibleChoices`, with respect to casing
    :rtype: TCommandCallback
    """
    lowerChoices = {i.lower(): i for i in possibleChoices}

    candidate = value.lower()
    if candidate in lowerChoices:
        return lowerChoices[candidate]

    await interaction.response.send_message(f":x: Unknown {objectTypeName}: {candidate}", ephemeral=True)
    raise ValueError(f":x: Unknown {objectTypeName}: {candidate}")


async def _roughDictStringVerify(interaction: Interaction, value: str, possibleChoices: Dict[str, Any], objectTypeName: str) -> str:
    """`_stringVerify`, but using a dictionary instead.
    This function was made just for ship skins, since they have a dict in bbData, but are not aliasable.
    """
    if value in possibleChoices:
        return value
    if value.lower() in possibleChoices:
        return value.lower()
    if value.title() in possibleChoices:
        return value.title()

    await interaction.response.send_message(f":x: Unknown {objectTypeName}: {value}", ephemeral=True)
    raise ValueError(f":x: Unknown {objectTypeName}: {value}")

#endregion

#region division

def divisionAutoComplete(paramName: str = "division", allowAllDivisions: bool = True):
    """A decorator to add autocomplete for a single-value bounty division parameter, by name.

    :param paramName: The name of the division name parameter
    :type paramName: str
    :param allowAllDivisions: Whether or not "all" is allowed
    :type allowAllDivisions: bool
    """
    def decorator(func: TCommand) -> TCommand:
        if allowAllDivisions:
            func.autocomplete(paramName)(_stringAutoComplete(lambda: cfg.bountyDivisionNames))
        else:
            func.autocomplete(paramName)(_stringAutoComplete(lambda: cfg.bountyDivisionNames + ["all"]))
        return func
    return decorator


class DivisionVerifyTransformer(Transformer):
    async def transform(self, interaction: Interaction, value: str) -> str:
        division = value.lower()
        if division not in cfg.bountyDivisionNames:
            if division == "all":
                await interaction.response.send_message(f":x: This command can only target a single division!", ephemeral=True)
                raise ValueError("'all divisions' specified for command parameter that does not allow it")
            if len(cfg.bountyDivisionNames) > 1:
                divNames = ', '.join(f"`{i}`" for i in cfg.bountyDivisionNames[:-1]) + f" or `{cfg.bountyDivisionNames[-1]}`"
            else:
                divNames = f"`{cfg.bountyDivisionNames[0]}`" if cfg.bountyDivisionNames else f"`<no divisions>`"
            await interaction.response.send_message(f":x: Unknown division: {division}. Please choose from: {divNames}.", ephemeral=True)
            raise ValueError(f"Unknown division: {division}")
        
        return division


class DivisionVerifyAllowAllTransformer(Transformer):
    async def transform(self, interaction: Interaction, value: str) -> str:
        division = value.lower()
        if division not in cfg.bountyDivisionNames and division != "all":
            if len(cfg.bountyDivisionNames) > 1:
                divNames = ', '.join(f"`{i}`" for i in cfg.bountyDivisionNames) + f" or `all`"
            else:
                divNames = f"`{cfg.bountyDivisionNames[0]}` or `all`" if cfg.bountyDivisionNames else f"`<no divisions>`"
            await interaction.response.send_message(f":x: Unknown division: {division}. Please choose from: {divNames}.", ephemeral=True)
            raise ValueError(f"Unknown division: {division}")
        
        return division


DivisionName = Transform[str, DivisionVerifyTransformer]
DivisionNameOrAll = Transform[str, DivisionVerifyAllowAllTransformer]

#endregion division
#region system

def systemAutoComplete(paramName: str = "system"):
    """A decorator to add autocomplete for a single-value solar system parameter, by name.

    :param paramName: The name of the solar system name parameter
    :type paramName: str
    """
    def decorator(func: TCommand) -> TCommand:
        func.autocomplete(paramName)(_aliasableAutoComplete(lambda: list(bbData.builtInSystemObjs.values())))
        return func
    return decorator


class SystemVerifyTransformer(Transformer):
    async def transform(self, interaction: Interaction, value: str) -> str:
        return await _aliasableVerify(interaction, value, bbData.builtInSystemObjs, "system")


SystemKey = Transform[str, SystemVerifyTransformer]

class SystemListVerifyTransformer(Transformer):
    async def transform(self, interaction: Interaction, value: str) -> List[str]:
        values = []
        for syst in value.split(","):
            resolved = await _aliasableVerify(interaction, syst.strip(), bbData.builtInSystemObjs, "system")
            values.append(resolved)
        return values


SystemKeyList = Transform[List[str], SystemListVerifyTransformer]

#endregion system
#region criminal

def criminalAutoComplete(paramName: str = "name"):
    """A decorator to add autocomplete for a single-value criminal parameter, by name.

    :param paramName: The name of the criminal name parameter
    :type paramName: str
    """
    def decorator(func: TCommand) -> TCommand:
        func.autocomplete(paramName)(_aliasableAutoComplete(lambda: list(bbData.builtInCriminalObjs.values())))
        return func
    return decorator


class CriminalVerifyTransformer(Transformer):
    async def transform(self, interaction: Interaction, value: str) -> str:
        return await _aliasableVerify(interaction, value, bbData.builtInCriminalObjs, "criminal")


CriminalKey = Transform[str, CriminalVerifyTransformer]


def _make_activeCriminalAutoComplete(useActive: bool, useEscaped: bool, userDivisionOnly: bool):
    """Construct an autocomplete callback for the active criminals in the calling guild.

    :param bool useActive: Show criminals that are active.
    :param bool useEscaped: Show criminals that are escaped.
    :param bool userDivisionOnly: Only show criminals in the calling user's division.
    """
    if not useActive and not useEscaped:
        raise ValueError("At least one of useActive or useEscaped must be True")

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

        async def checkBounties(bounties: List[bounty.Bounty]):
            for bounty in bounties:
                if bounty.criminal in criminals: continue
                criminals.add(bounty.criminal)

                if bounty.criminal.isPlayer:
                    userId = int(bounty.criminal.name.lstrip("<@!").rstrip(">"))
                    dcUser = interaction.client.get_user(userId) or await cast(client.BasedClient, interaction.client).tryFetchUser(userId)
                    bountyName = f"<Player {userId}>" if dcUser is None else str(dcUser)

                else:
                    bountyName = bounty.criminal.name
                
                if current in bountyName:
                    choices.append(app_commands.Choice(name=bountyName, value=bountyName))
                    if len(choices) == MAX_CHOICES:
                        break

        async def checkDivision(div: bountyDivision.BountyDivision):
            if useActive:
                await checkBounties(div.allActiveBounties())
            if useEscaped:
                await checkBounties(div.allEscapedBounties())
        
        if userDivisionOnly:
            if interaction.client.usersDB.idExists(interaction.user.id):
                bUser = interaction.client.usersDB.getUser(interaction.user.id)
                userLevel = cfg.minTechLevel if bUser.classicModeEnabled else gameMaths.calculateUserBountyHuntingLevel(cast(int, bUser.bountyHuntingXP))
            else:
                userLevel = cfg.minTechLevel

            div = bountiesDB.divisionForLevel(userLevel)
            await checkDivision(div)
        else:
            scheduler = lib.discordUtil.BasicScheduler()
            for div in bountiesDB.divisions.values():
                scheduler.add(checkDivision(div))
            await scheduler.wait()
            scheduler.raiseExceptions()

        return choices
    return _activeCriminalAutoComplete
    

def activeCriminalAutoComplete(paramName: str = "name", active: bool = True, escaped: bool = False, userDivisionOnly: bool = False):
    """A decorator to add autocomplete for a single-value criminal parameter, by name.
    This decorator is different to `criminalAutoComplete` because it inspects the active criminals in the guild.
    This is useful for limiting the potential options, but also for allowing selection of players and non-builtIn criminals.
    Criminals will be listed across all divisions.
    
    :param paramName: The name of the criminal name parameter
    :type paramName: str
    :param bool active: Show criminals that are active.
    :param bool escaped: Show criminals that are escaped.
    :param bool userDivisionOnly: Only show criminals in the calling user's division.
    """
    def decorator(func: TCommand) -> TCommand:
        func.autocomplete(paramName)(_make_activeCriminalAutoComplete(active, escaped, userDivisionOnly))
        return func
    return decorator

#endregion criminal
#region faction

def factionAutoComplete(paramName: str = "faction", bountyFactionsOnly: bool = True):
    """A decorator to add autocomplete for a single-value faction parameter, by name.

    :param paramName: The name of the faction name parameter
    :type paramName: str
    :param bountyFactionsOnly: Whether to use bbData.bountyFactions instead of bbData.factions
    :type bountyFactionsOnly: bool
    """
    def decorator(func: TCommand) -> TCommand:
        if bountyFactionsOnly:
            func.autocomplete(paramName)(_stringAutoComplete(lambda: bbData.bountyFactions))
        else:
            func.autocomplete(paramName)(_stringAutoComplete(lambda: bbData.factions))
        return func
    return decorator


class FactionVerifyTransformer(Transformer):
    async def transform(self, interaction: Interaction, value: str) -> str:
        return await _stringVerify(interaction, value, bbData.factions, "faction")


FactionName = Transform[str, FactionVerifyTransformer]


class BountyFactionVerifyTransformer(Transformer):
    async def transform(self, interaction: Interaction, value: str) -> str:
        return await _stringVerify(interaction, value, bbData.bountyFactions, "bounty faction")


BountyFactionName = Transform[str, BountyFactionVerifyTransformer]

#endregion faction
#region item-ship

async def _shipAutoComplete(interaction: Interaction, current: str) -> List[app_commands.Choice[str]]:
    """An autocomplete callback for choosing a builtIn ship.
    TODO: This callback could do with refactoring, to use the logic in _stringAutocomplete or _aliasableAutocomplete,
    Perhaps by passing an autocomplete callback constructor a callback to get an item's aliases?

    """
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
    def decorator(func: TCommand) -> TCommand:
        func.autocomplete(paramName)(_shipAutoComplete)
        return func
    return decorator


class ShipVerifyTransformer(Transformer):
    async def transform(self, interaction: Interaction, value: str) -> str:
        if value in bbData.builtInShipData:
            return value
        if value.lower() in bbData.builtInShipData:
            return value.lower()
        if value.title() in bbData.builtInShipData:
            return value.title()

        matchedCandidate = None
        for shipKey, ship in bbData.builtInShipData.items():
            if value.lower() in ship.get("aliases", []):
                matchedCandidate = shipKey
                break

        if matchedCandidate is None:
            await interaction.response.send_message(f":x: Unknown ship: {value}", ephemeral=True)
            raise ValueError("f:x: Unknown ship: {value}")
        
        return matchedCandidate

ShipKey = Transform[str, ShipVerifyTransformer]


#endregion item-ship
#region item-ship-skin

def shipSkinAutoComplete(paramName: str = "skin"):
    """A decorator to add autocomplete for a single-value ship skin parameter, by name.

    :param paramName: The name of the ship skin name parameter
    :type paramName: str
    """
    def decorator(func: TCommand) -> TCommand:
        func.autocomplete(paramName)(_stringAutoComplete(lambda: list(bbData.builtInShipSkins.keys())))
        # func.autocomplete(paramName)(_shipSkinAutoComplete)
        return func
    return decorator


class ShipSkinVerifyTransformer(Transformer):
    async def transform(self, interaction: Interaction, value: str) -> str:
        return await _roughDictStringVerify(interaction, value, bbData.builtInShipSkins, "ship skin")


ShipSkinKey = Transform[str, ShipSkinVerifyTransformer]

#endregion item-ship-skin
#region item-module

def moduleAutoComplete(paramName: str = "module"):
    """A decorator to add autocomplete for a single-value module parameter, by name.

    :param paramName: The name of the module name parameter
    :type paramName: str
    """
    def decorator(func: TCommand) -> TCommand:
        func.autocomplete(paramName)(_aliasableAutoComplete(lambda: list(bbData.builtInModuleObjs.values())))
        return func
    return decorator


class ModuleVerifyTransformer(Transformer):
    async def transform(self, interaction: Interaction, value: str) -> str:
        return await _aliasableVerify(interaction, value, bbData.builtInModuleObjs, "module")


ModuleKey = Transform[str, ModuleVerifyTransformer]

#endregion item-module
#region item-weapon

def weaponAutoComplete(paramName: str = "weapon"):
    """A decorator to add autocomplete for a single-value primary weapon parameter, by name.

    :param paramName: The name of the weapon name parameter
    :type paramName: str
    """
    def decorator(func: TCommand) -> TCommand:
        func.autocomplete(paramName)(_aliasableAutoComplete(lambda: list(bbData.builtInWeaponObjs.values())))
        return func
    return decorator


class PrimaryWeaponVerifyTransformer(Transformer):
    async def transform(self, interaction: Interaction, value: str) -> str:
        return await _aliasableVerify(interaction, value, bbData.builtInWeaponObjs, "primary weapon")


PrimaryWeaponKey = Transform[str, PrimaryWeaponVerifyTransformer]

#endregion item-weapon
#region item-turret

def turretAutoComplete(paramName: str = "turret"):
    """A decorator to add autocomplete for a single-value turret parameter, by name.

    :param paramName: The name of the turret name parameter
    :type paramName: str
    """
    def decorator(func: TCommand) -> TCommand:
        func.autocomplete(paramName)(_aliasableAutoComplete(lambda: list(bbData.builtInTurretObjs.values())))
        return func
    return decorator


class TurretVerifyTransformer(Transformer):
    async def transform(self, interaction: Interaction, value: str) -> str:
        return await _aliasableVerify(interaction, value, bbData.builtInTurretObjs, "turret")


TurretKey = Transform[str, TurretVerifyTransformer]

#endregion item-turret
#region item-tool

def toolAutoComplete(paramName: str = "tool"):
    """A decorator to add autocomplete for a single-value tool parameter, by name.

    :param paramName: The name of the tool name parameter
    :type paramName: str
    """
    def decorator(func: TCommand) -> TCommand:
        func.autocomplete(paramName)(_aliasableAutoComplete(lambda: list(bbData.builtInToolObjs.values())))
        return func
    return decorator


class ToolVerifyTransformer(Transformer):
    async def transform(self, interaction: Interaction, value: str) -> str:
        return await _aliasableVerify(interaction, value, bbData.builtInToolObjs, "tool")


ToolKey = Transform[str, ToolVerifyTransformer]

#endregion item-tool
#region item-medal

def medalAutoComplete(paramName: str = "medal"):
    """A decorator to add autocomplete for a single-value medal parameter, by name.

    :param paramName: The name of the medal name parameter
    :type paramName: str
    """
    def decorator(func: TCommand) -> TCommand:
        func.autocomplete(paramName)(_stringAutoComplete(lambda: list(bbData.medalObjs.keys())))
        return func
    return decorator


class MedalVerifyTransformer(Transformer):
    async def transform(self, interaction: Interaction, value: str) -> str:
        return await _roughDictStringVerify(interaction, value, bbData.medalObjs, "medal")


MedalKey = Transform[str, MedalVerifyTransformer]

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
    def decorator(func: TCommand) -> TCommand:
        autocomplete = _make_inventoryCategoryItemNumberAutoComplete(itemCategory, True)
        # TODO: Apparently my autocomplete is of the wrong type?
        func.autocomplete(paramName)(autocomplete)
        return func
    return decorator


class InventoryItemVerifyTransformer(Transformer):
    async def transform(self, interaction: Interaction, value: str) -> int:
        """`Verify that the given item number is an integer. If it is not, then display an error and raise `ValueError`.
        """
        if not lib.stringTyping.isInt(value):
            await interaction.response.send_message(":x: Unknown item, please select an item from the list, or give an item number.", ephemeral=True)
            raise ValueError(f"Unknown item or item number: {value}")

        return int(value)


InventoryItemNumber = Transform[int, InventoryItemVerifyTransformer]


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

def anyUserHangerItemAutoComplete_verify(v: str) -> bool:
    return v[0] in ID_ITEM_TYPES and lib.stringTyping.isInt(v[1:])

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
    def decorator(func: TCommand) -> TCommand:
        autocomplete = _make_anyUserHangerItemAutoComplete(True)
        func.autocomplete(paramName)(autocomplete)
        return func
    return decorator


class AnyUserHangarItemVerifyTransformer(Transformer):
    async def transform(self, interaction: Interaction, value: str) -> Tuple[bbData.ItemCategory, int]:
        """`Verify that the given value is an item reference. If it is not, then display an error and raise `ValueError`.
        """
        if not anyUserHangerItemAutoComplete_verify(value):
            await interaction.response.send_message(":x: Unknown item, please select an item from the list.", ephemeral=True)
            raise ValueError(f"Invalid inventory hangar reference: {value}")

        return anyUserHangerItemAutoComplete_decodeValue(value)


AnyUserHangarItem = Transform[Tuple[bbData.ItemCategory, int], AnyUserHangarItemVerifyTransformer]

#endregion inventory