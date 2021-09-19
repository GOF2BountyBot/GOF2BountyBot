# TODO: Remake most of these with regex
from typing import Union


def isInt(x) -> bool:
    """Decide whether or not something is either an integer, or is castable to integer.

    :param x: The object to type-check
    :return: True if x is an integer or if x can be casted to integer. False otherwise
    :rtype: bool
    """
    try:
        int(x)
    except (TypeError, ValueError):
        return False
    return True


def isMention(m: str) -> bool:
    """Decide whether the given string is a discord user mention,
    being either <@USERID> or <@!USERID> where USERID is an integer discord user id.

    :param str mention: The string to check
    :return: True if mention matches the formatting of a discord user mention, False otherwise
    :rtype: bool
    """
    return m.endswith(">") and ((m.startswith("<@") and isInt(m[2:-1])) or \
                                (m.startswith("<@!") and isInt(m[3:-1])))


def isRoleMention(m: str) -> bool:
    """Decide whether the given string is a discord role mention, being <@&ROLEID> where ROLEID is an integer discord role id.

    :param str mention: The string to check
    :return: True if mention matches the formatting of a discord role mention, False otherwise
    :rtype: bool
    """
    return all((m.endswith(">"), m.startswith("<@&"), isInt(m[3:-1])))


def commaSplitNum(num: int) -> str:
    """Convert an number to a string with commas in every third position. Also accepts floats.
    For example: 3 -> "3", 30000 -> "30,000", and 561928301 -> "561,928,301"
    https://stackoverflow.com/a/10742904

    :param int num: string to insert commas into. probably just containing digits
    :return: num, but split with commas at every third digit
    :rtype: str
    """
    return f"{num:,}"


# string extensions for numbers, e.g 11th, 1st, 23rd...
numExtensions = ["th", "st", "nd", "rd", "th", "th", "th", "th", "th", "th"]


def getNumExtension(num: int) -> str:
    """Return the string extension for an integer, e.g 'th' or 'rd'.
    https://stackoverflow.com/a/50992575

    :param int num: The integer to find the extension for
    :return: string containing a number extension from numExtensions
    :rtype: str
    """
    return "th" if 11 <= (num % 100) <= 13 else ("th", "st", "nd", "rd", "th")[min(num % 10, 4)]


def shipSkinNameToToolName(skinName : str) -> str:
    """Construct a name of a shipSkinTool from the name of the skin of the skin.

    :param str skinName: The name of the skin this tool name should reference
    :return: The name that should be given to a shipSkinTool that applies the named shipSkin
    """
    return f"Ship Skin: {skinName}"


def formatAdditive(stat : Union[float, int]) -> str:
    """Format a module effect attribute into a string, including a sign symbol.

    :param stat: The statistic to format into a string
    :type stat: Union[float, int]
    :return: A sign symbol, followed by stat
    """
    return f"{'+' if stat > 0 else '-'}{stat}"


def formatMultiplier(stat : float) -> str:
    """Format a module effect attribute into a string, including a sign symbol and percentage symbol.

    :param stat: The statistic to format into a string
    :type stat: float
    :return: A sign symbol, followed by stat, followed by a percentage sign.
    """
    return f"{'+' if stat >= 1 else '-'}{round(((stat - 1) if stat > 1 else (1 - stat)) * 100)}%"
