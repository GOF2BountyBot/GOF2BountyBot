from typing import Protocol

from .embedFillable import EmbedFillableMixin, embedField

from ..lib.discordUtil import ZWSP
from ..cfg import cfg


class HasName(Protocol):
    @property
    def name(self) -> str: ...


class NamedWikiEntity(EmbedFillableMixin):
    """This mixin can only be used with a class that has a string `name` property/field.
    Adds a `wiki` property as an embed field, linking to the object's wiki page as defined by `cfg.wikiEntityUrlTemplate`. 
    This field will always show last in the embed. It will have a non-unique ZWSP field name.
    """
    @embedField(fieldName=ZWSP, showInline=False, showLast=True, hideWhenNone=True, uniqueFieldName=False)
    @property
    def wikiNamedHyperlink(self: HasName):
        """A markdown hyperlink for this object's wiki, if it has one.
        """
        return f"[Wiki]({cfg.wikiEntityUrlTemplate.format(searchTerm=self.name)})"
