# Typing imports
from __future__ import annotations
from typing import Any, Dict, List, Tuple
from typing_extensions import NotRequired, TypedDict
from abc import abstractmethod
from diff_match_patch import diff_match_patch

from ..lib.stringTyping import stringDifference
from .serializable import SerializesToSchema
from .embedFillable import EmbedFillableMixin, embedField, embedTitle

DMP = diff_match_patch()

class SerializedAliasable(TypedDict):
    name: str
    aliases: NotRequired[List[str]]


class AliasableMixin(EmbedFillableMixin, SerializesToSchema[SerializedAliasable]):
    """An abstract class allowing subtype instances to be identified and compared by any list of names (aliases).
    A great example and common use case is in BountyBot's Criminal class. Criminals are NPCs that each have a unique name.
    These names usually consist of a forename and sirname, for example 'Ganfor Kant'. Providing 'Ganfor' and 'Kant' as aliases
    allows the Ganfor Kant object to be identified by any of 'Ganfor', 'Kant', or 'Ganfor Kant', for user convenience.

    This class comes with `EmbedFillableMixin`, and the class's name and aliases as embed fields

    :var name: The main identifier for the object
    :vartype name: str
    :var aliases: A list of alternative identifiers for the object
    :vartype aliases: list[str]
    """

    def __init__(self, name: str, aliases: List[str] = [], *args, forceAllowEmpty: bool = False, **kwargs):
        """
        :param str name: The main identifier for the object
        :param list[str] aliases: A list of alternative identifiers for the object
        :param bool forceAllowEmpty: By default, "" is disallowed as an alias. Give True to force allow it (Default False)
        """
        if not name and not forceAllowEmpty:
            raise RuntimeError("ALIAS_CONS_NONAM: Attempted to create an aliasable with an empty name")
        self.name = name

        for alias in range(len(aliases)):
            if not aliases[alias] and not forceAllowEmpty:
                raise RuntimeError("ALIAS_CONS_EMPTALIAS: Attempted to create an aliasable with an empty alias")
            aliases[alias] = aliases[alias].lower()
        self.aliases = aliases

        if name.lower() not in aliases:
            self.aliases += [name.lower()]
        
        super().__init__(*args, name=name, **kwargs)


    @embedTitle
    @property
    def formattedName(self):
        """The main name for this aliasable object.
        """
        return self.name.title()


    @embedField("Aliases", showLast=True, showInline=False, uniqueFieldName=True, hideWhenNone=True)
    @property
    def formattedAliases(self):
        """A list of other names by which this object may be referred.
        """
        return ", ".join(i.title() for i in self.aliases if i.lower() != self.name.lower()) or None


    def mostSimilarAlias(self, cmp: str, deadline: int = 2, ignoreCase: bool = True) -> Tuple[int, str]:
        changes = [(stringDifference(alias.lower() if ignoreCase else alias, cmp.lower() if ignoreCase else cmp), alias) for alias in self.aliases]
        return min(changes, key=lambda x: x[0])


    def isCalled(self, name: str) -> bool:
        """Decide whether the provided name is one of this object's aliases.

        :param str name: The name to look up in this object's aliases
        :return: True if name is either this object's name, or is one of this object's aliases.
        :rtype: bool
        """
        return name.lower() == self.name.lower() or name.lower() in self.aliases


    def removeAlias(self, name: str):
        """Remove the given name from this object's aliases. This does not affect the object's main name.

        :param str name: The alias to remove
        """
        if name.lower() in self.aliases:
            self.aliases.remove(name.lower())


    def addAlias(self, name: str):
        """Add the given name to this object's aliases.

        :param str name: The alias to add
        """
        if name.lower() not in self.aliases:
            self.aliases.append(name.lower())


    @abstractmethod
    def serialize(self, **kwargs: Dict[str, Any]) -> SerializedAliasable:
        """Serialize this object into dictionary format, to be recreated completely.

        :return: A dictionary containing all information needed to recreate this object
        :rtype: dict
        """
        data: SerializedAliasable = {"name": self.name}
        if self.aliases:
            data["aliases"] = self.aliases
        return data
