# Typing imports
from __future__ import annotations
from typing import Any, Dict, List, Tuple, TypeVar

from abc import abstractmethod
from diff_match_patch import diff_match_patch # type: ignore[reportMissingTypeStubs]

from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, declared_attr, Mapped, relationship, mapped_column
from sqlalchemy.ext.associationproxy import association_proxy, AssociationProxy
from sqlalchemy.ext.asyncio import AsyncAttrs

from ..lib.stringUtil import stringDifference
from ..lib.sql import EmbedFillableSqlTableMeta
from .serializable import SerializesToSchema
from .embedFillable import EmbedFillableMixin, embedField, embedTitle
from ..database.tables import TableNames
from .aliasable_json import SerializedAliasable

DMP = diff_match_patch()


class Base(DeclarativeBase, AsyncAttrs): pass


class _ObjectAlias(Base):
    __tablename__ = TableNames.ObjectAlias.value
    alias: Mapped[str] = mapped_column(primary_key=True)
    objectAliasesId: Mapped[int] = mapped_column(ForeignKey(f'{TableNames.ObjectAliases}.id'))
    def __init__(self, alias: str):
        self.value = alias


TSchema = TypeVar("TSchema", bound=SerializedAliasable)


class AliasableMixin(Base, EmbedFillableMixin, SerializesToSchema[TSchema], metaclass=EmbedFillableSqlTableMeta):
    """An abstract class allowing subtype instances to be identified and compared by any list of names (aliases).
    A great example and common use case is in BountyBot's Criminal class. Criminals are NPCs that each have a unique name.
    These names usually consist of a forename and sirname, for example 'Ganfor Kant'. Providing 'Ganfor' and 'Kant' as aliases
    allows the Ganfor Kant object to be identified by any of 'Ganfor', 'Kant', or 'Ganfor Kant', for user convenience.

    This class comes with `EmbedFillableMixin`, and the object's name and aliases as embed fields

    :var name: The main identifier for the object
    :vartype name: str
    :var aliases: A list of alternative identifiers for the object
    :vartype aliases: list[str]
    """
    __tablename__ = TableNames.ObjectAliases.value
    
    name: Mapped[str]
    objectAliasesId: Mapped[int] = mapped_column(ForeignKey(f"{TableNames.ObjectAliases}.id"))

    @declared_attr
    def _aliasesAssociation(cls) -> Mapped[_ObjectAlias]:
        return relationship(_ObjectAlias)

    _aliases: AssociationProxy[List[str]] = association_proxy("_aliasesAssociation", "alias")
    # @declared_attr
    # def aliases(cls) -> AssociationProxy[List[str]]:
    #     return association_proxy(cls._aliasesAssociation.__name__, 'alias')
    

    def __init__(self, name: str, aliases: List[str] = [], *args: Any, forceAllowEmpty: bool = False, _aliases: List[str] = [], **kwargs: Any):
        """
        :param str name: The main identifier for the object
        :param list[str] aliases: A list of alternative identifiers for the object
        :param bool forceAllowEmpty: By default, "" is disallowed as an alias. Give True to force allow it (Default False)
        """
        if not name and not forceAllowEmpty:
            raise RuntimeError("ALIAS_CONS_NONAM: Attempted to create an aliasable with an empty name")
        self.name = name

        aliases = aliases or _aliases

        for alias in range(len(aliases)):
            if not aliases[alias] and not forceAllowEmpty:
                raise RuntimeError("ALIAS_CONS_EMPTALIAS: Attempted to create an aliasable with an empty alias")
            aliases[alias] = aliases[alias].lower()
        self._aliases = aliases

        if name.lower() not in aliases:
            self._aliases += [name.lower()]
        
        super().__init__(*args, name=name, **kwargs)


    @property
    async def aliases(self) -> List[str]:
        """A list of alternative identifiers for the object. This property must be awaited.

        :rtype: List[str]
        """
        return await self.awaitable_attrs.aliases
    

    @aliases.setter
    def setAliases(self, value: List[str]):
        self._aliases = value


    @embedTitle
    @property
    def formattedName(self):
        """The main name for this aliasable object.
        """
        return self.name.title()


    @embedField("Aliases", showLast=True, showInline=False, uniqueFieldName=True, hideWhenNone=True)
    @property
    async def formattedAliases(self):
        """A list of other names by which this object may be referred.
        """
        return ", ".join(
            i.title() for i in
                await self.aliases
                if i.lower() != self.name.lower()
            ) or None


    async def mostSimilarAlias(self, cmp: str, deadlinePerDiff: int = 2, ignoreCase: bool = True) -> Tuple[int, str]:
        changes = [(
            stringDifference(
                alias.lower() if ignoreCase else alias,
                cmp.lower() if ignoreCase else cmp,
                deadline=deadlinePerDiff),
            alias)
            for alias in await self.aliases]
        
        return min(changes, key=lambda x: x[0])


    async def isCalled(self, name: str) -> bool:
        """Decide whether the provided name is one of this object's aliases.

        :param str name: The name to look up in this object's aliases
        :return: True if name is either this object's name, or is one of this object's aliases.
        :rtype: bool
        """
        return name.lower() == self.name.lower() \
            or name.lower() in await self.aliases


    def removeAlias(self, name: str):
        """Remove the given name from this object's aliases. This does not affect the object's main name.

        :param str name: The alias to remove
        """
        try:
            self._aliases.remove(name.lower())
        except ValueError:
            pass


    async def addAlias(self, name: str):
        """Add the given name to this object's aliases.

        :param str name: The alias to add
        """
        if await self.isCalled(name):
            self._aliases.append(name.lower())


    @abstractmethod
    async def serialize(self, **kwargs: Dict[str, Any]) -> TSchema:
        """Serialize this object into dictionary format, to be recreated completely.

        :return: A dictionary containing all information needed to recreate this object
        :rtype: dict
        """
        data = await super().serialize(**kwargs)
        data["name"] = self.name
        if self._aliases:
            data["aliases"] = await self.aliases
        return data
