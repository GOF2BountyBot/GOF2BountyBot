from discord import Interaction
from typing import Optional
from ...cfg import cfg, bbData

async def verifyDivName(interaction: Interaction, division: str, sendError: bool = True, allowAllDivisions: bool = True) -> Optional[bool]:
    """Make sure `division` is either `all` or a valid divison name.
    Returns `True` if `division` is `all` and `allowAllDivisions` is `True`
    Returns `False` if `division` is a valid division name
    Returns `None` if neither of the above
    """
    if division == "all" and allowAllDivisions:
        return True

    if division not in cfg.bountyDivisionNames:
        if sendError:
            await interaction.response.send_message(f":x: Unknown division name. Must be one of: {', '.join(cfg.bountyDivisionNames)}" + ("or all." if allowAllDivisions else "."), ephemeral=True)
        return None
    return False


async def verifySystemName(interaction: Interaction, system: str, sendError: bool = True) -> Optional[bool]:
    """Make sure `system` is a valid solar system name.
    """
    if system not in bbData.builtInSystemObjs:
        if sendError:
            await interaction.response.send_message(f":x: Unknown system name.", ephemeral=True)
        return False
    return True


async def verifyCriminalName(interaction: Interaction, name: str, sendError: bool = True) -> Optional[bool]:
    """Make sure `name` is a valid criminal name.
    """
    if name not in bbData.builtInCriminalObjs:
        if sendError:
            await interaction.response.send_message(f":x: Unknown criminal name.", ephemeral=True)
        return False
    return True


async def verifyFactionName(interaction: Interaction, faction: str, sendError: bool = True, bountyFactionsOnly: bool = True) -> Optional[bool]:
    """Make sure `faction` is a valid faction name.
    """
    if faction not in (bbData.bountyFactions if bountyFactionsOnly else bbData.factions):
        if sendError:
            await interaction.response.send_message(f":x: Unknown faction name.", ephemeral=True)
        return False
    return True
