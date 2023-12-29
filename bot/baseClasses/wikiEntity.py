from typing import Optional

from abc import ABC, abstractmethod

from sqlalchemy.orm import Mapped

from .embedFillable import EmbedFillableMixin, embedField
from ..lib.discordUtil import ZWSP
from ..lib.sql import EmbedFillableSqlTableMeta
from ..cfg import cfg


class HasWikiUrl(ABC, EmbedFillableMixin):
    """Adds a `wikiNamedHyperlink` property as a "Wiki" embed field, using the value from the `wikiUrl`
    property on your existing model. 
    This field will always show last in the embed. It will have a non-unique ZWSP field name.
    If a wikiUrl is not present, the field is not shown.

    If your model is a SQL table, make sure to declare your class with `metaclass=EmbedFillableSqlTableMeta`
    from `lib.sql`, since this class comes with `EmbedFillableMixin`.
    """
    @property
    @abstractmethod
    def wikiUrl(self) -> Optional[str]: ...

    @embedField(fieldName=ZWSP, showInline=False, showLast=True, hideWhenNone=True, uniqueFieldName=False)
    @property
    def wikiNamedHyperlink(self) -> Optional[str]:
        """A markdown hyperlink for this object's wiki, if it has one.
        """
        return None if self.wikiUrl is None else f"[Wiki]({self.wikiUrl})"


class NamedWikiEntity(EmbedFillableMixin):
    """This mixin can only be applied to classes with a `name` attribute.
    Adds a `wikiNamedHyperlink` property as a "Wiki" embed field, linking to the object's wiki page as defined by `cfg.wikiEntityUrlTemplate`. 
    This field will always show last in the embed. It will have a non-unique ZWSP field name.

    If your model is a SQL table, make sure to declare your class with `metaclass=EmbedFillableSqlTableMeta`
    from `lib.sql`, since this class comes with `EmbedFillableMixin`.
    """
    name: str
    
    @embedField(fieldName=ZWSP, showInline=False, showLast=True, uniqueFieldName=False)
    @property
    def wikiNamedHyperlink(self) -> Optional[str]:
        """A markdown hyperlink for this object's wiki page.
        """
        return f"[Wiki]({cfg.wikiEntityUrlTemplate.format(searchTerm=self.name)})"


class SqlNamedWikiEntity(EmbedFillableMixin, metaclass=EmbedFillableSqlTableMeta):
    """This mixin can only be applied to SqlAlchemy models with a `name` field. The field is included in the mixin.
    Adds a `wikiNamedHyperlink` property as a "Wiki" embed field, linking to the object's wiki page as defined by `cfg.wikiEntityUrlTemplate`. 
    This field will always show last in the embed. It will have a non-unique ZWSP field name.
    """
    name: Mapped[str]
    
    @embedField(fieldName=ZWSP, showInline=False, showLast=True, uniqueFieldName=False)
    @property
    def wikiNamedHyperlink(self) -> Optional[str]:
        """A markdown hyperlink for this object's wiki page.
        """
        return f"[Wiki]({cfg.wikiEntityUrlTemplate.format(searchTerm=self.name)})"


class PropertyNamedWikiEntity(ABC, EmbedFillableMixin):
    """This mixin can only be applied to classes with a `name` property.
    Adds a `wikiNamedHyperlink` property as a "Wiki" embed field, linking to the object's wiki page as defined by `cfg.wikiEntityUrlTemplate`. 
    This field will always show last in the embed. It will have a non-unique ZWSP field name.

    If your model is a SQL table, make sure to declare your class with `metaclass=EmbedFillableSqlTableMeta`
    from `lib.sql`, since this class comes with `EmbedFillableMixin`.
    """
    @property
    @abstractmethod
    def name(self) -> Optional[str]: ...
    
    @embedField(fieldName=ZWSP, showInline=False, showLast=True, uniqueFieldName=False)
    @property
    def wikiNamedHyperlink(self) -> Optional[str]:
        """A markdown hyperlink for this object's wiki page.
        """
        return f"[Wiki]({cfg.wikiEntityUrlTemplate.format(searchTerm=self.name)})"
