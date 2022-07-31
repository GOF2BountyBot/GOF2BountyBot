
from discord import Interaction
from discord import app_commands
from ...cfg import cfg, bbData

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


async def _divisionAutoComplete(interaction: Interaction, current: str):
    choices = []
    for d in DIVISION_CHOICES:
        if current in d.name:
            choices.append(d)
            if len(choices) == 25:
                break
    return choices


async def _divisionAutoCompleteWithAll(interaction: Interaction, current: str):
    choices = []
    for d in DIVISION_CHOICES_WITH_ALL:
        if current in d.name:
            choices.append(d)
            if len(choices) == 25:
                break
    return choices


def divisionAutoComplete(paramName: str = "division", allowAllDivisions: bool = True):
    """A decorator to add autocomplete for a single-value bounty division parameter, by name.

    :param paramName: The name of the division name parameter
    :type paramName: str
    :param allowAllDivisions: Whether or not "all" is allowed
    :type allowAllDivisions: bool
    """
    def decorator(func: app_commands.Command):
        if allowAllDivisions:
            func.autocomplete(paramName)(_divisionAutoCompleteWithAll)
        else:
            func.autocomplete(paramName)(_divisionAutoComplete)
        return func
    return decorator


async def _systemAutoComplete(interaction: Interaction, current: str):
    choices = []
    for system in bbData.builtInSystemObjs.values():
        if system.isCalled(current):
            choices.append(app_commands.Choice(name=system.name, value=system.name))
            if len(choices) == 25:
                break
    return choices


def systemAutoComplete(paramName: str = "division"):
    """A decorator to add autocomplete for a single-value solar system parameter, by name.

    :param paramName: The name of the solar system name parameter
    :type paramName: str
    """
    def decorator(func: app_commands.Command):
        func.autocomplete(paramName)(_systemAutoComplete)
        return func
    return decorator


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
