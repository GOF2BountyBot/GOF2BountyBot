
from typing import Callable, Iterable
from discord import Interaction
from discord import app_commands

from ...cfg import cfg, bbData
from ...baseClasses.aliasable import AliasableMixin

def _stringAutoComplete(possibleChoices: Iterable[app_commands.Choice[str]]):
    async def inner(interaction: Interaction, current: str):
        choices = []
        for choice in possibleChoices:
            if current in choice.name:
                choices.append(choice)
                if len(choices) == 25:
                    break
        return choices
    return inner


def _aliasableAutoComplete(getPossibleChoices: Callable[[], Iterable[AliasableMixin]]):
    async def inner(interaction: Interaction, current: str):
        choices = []
        for choice in getPossibleChoices():
            if choice.isCalled(current):
                choices.append(app_commands.Choice(name=choice.name, value=choice.name))
                if len(choices) == 25:
                    break
        return choices
    return inner

#region division

DIVISION_CHOICES = sorted(set(
    [
        app_commands.Choice(name=division, value=division)
        for division in cfg.bountyDivisionNames
    ] \
        + [app_commands.Choice(name="all", value="all")]),
    key=lambda c: c.name)

DIVISION_CHOICES_WITH_ALL = sorted(set(
    DIVISION_CHOICES + [app_commands.Choice(name="all", value="all")]),
    key=lambda c: c.name)


def divisionAutoComplete(paramName: str = "division", allowAllDivisions: bool = True):
    """A decorator to add autocomplete for a single-value bounty division parameter, by name.

    :param paramName: The name of the division name parameter
    :type paramName: str
    :param allowAllDivisions: Whether or not "all" is allowed
    :type allowAllDivisions: bool
    """
    def decorator(func: app_commands.Command):
        if allowAllDivisions:
            func.autocomplete(paramName)(_stringAutoComplete(DIVISION_CHOICES))
        else:
            func.autocomplete(paramName)(_stringAutoComplete(DIVISION_CHOICES_WITH_ALL))
        return func
    return decorator

#endregion division
#region system

def systemAutoComplete(paramName: str = "division"):
    """A decorator to add autocomplete for a single-value solar system parameter, by name.

    :param paramName: The name of the solar system name parameter
    :type paramName: str
    """
    def decorator(func: app_commands.Command):
        func.autocomplete(paramName)(_aliasableAutoComplete(bbData.builtInSystemObjs.values()))
        return func
    return decorator

#endregion system
#region criminal

async def _criminalAutoComplete(interaction: Interaction, current: str):
    choices = []
    for criminal in bbData.builtInCriminalObjs.values():
        if criminal.isCalled(current):
            choices.append(app_commands.Choice(name=criminal.name, value=criminal.name))
            if len(choices) == 25:
                break
    return choices


def criminalAutoComplete(paramName: str = "name"):
    """A decorator to add autocomplete for a single-value criminal parameter, by name.

    :param paramName: The name of the criminal name parameter
    :type paramName: str
    """
    def decorator(func: app_commands.Command):
        func.autocomplete(paramName)(_criminalAutoComplete)
        return func
    return decorator

#endregion criminal
#region faction

async def _factionAutoComplete(interaction: Interaction, current: str):
    choices = []
    for faction in bbData.factions:
        if current in faction:
            choices.append(app_commands.Choice(name=faction, value=faction))
            if len(choices) == 25:
                break
    return choices


async def _factionAutoCompleteBountyFactionsOnly(interaction: Interaction, current: str):
    choices = []
    for faction in bbData.bountyFactions:
        if current in faction:
            choices.append(app_commands.Choice(name=faction, value=faction))
            if len(choices) == 25:
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

async def _shipAutoComplete(interaction: Interaction, current: str):
    choices = []
    for d in ITEM_CHOICES_SHIP:
        if current in d.name:
            choices.append(d)
            if len(choices) == 25:
                break
    return choices


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
#region item-module

async def _moduleAutoComplete(interaction: Interaction, current: str):
    choices = []
    for module in bbData.builtInModuleObjs.values():
        if module.isCalled(current):
            choices.append(app_commands.Choice(name=module.name, value=module.name))
            if len(choices) == 25:
                break
    return choices


def moduleAutoComplete(paramName: str = "name"):
    """A decorator to add autocomplete for a single-value criminal parameter, by name.

    :param paramName: The name of the criminal name parameter
    :type paramName: str
    """
    def decorator(func: app_commands.Command):
        func.autocomplete(paramName)(_criminalAutoComplete)
        return func
    return decorator

#endregion item-module
#