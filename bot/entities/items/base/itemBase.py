from typing import Any, Dict, Optional, TypeVar, cast

from abc import abstractmethod

from sqlalchemy.orm import DeclarativeBase, declared_attr, Mapped, composite, mapped_column

from ....database.constants import StoreableItemType
from ....database.tables import TableNames
from ....lib.emojis import BasedEmoji
from ....lib.sql import EmbedFillableSqlTableMeta
from ....lib.stringUtil import commaSplitNum
from ....baseClasses.serializable import SerializesToSchema
from ....baseClasses.embedFillable import EmbedFillableMixin, embedField, embedThumbnailUrl, embedColour
from ....baseClasses.aliasable import AliasableMixin
from .itemBase_json import SerializedItemBaseUnion, SerializedItemBase, TypedSerializedItemBase
from ....cfg import bbData


TSelf = TypeVar("TSelf", bound="ItemBase")


class Base(DeclarativeBase): pass

class ItemBase(Base, AliasableMixin, EmbedFillableMixin, SerializesToSchema[SerializedItemBaseUnion], metaclass=EmbedFillableSqlTableMeta):
    """An in-game item.
    Items have name and a credits value, and can be stored in an inventory.
    Items can also optionally have a manufacturer, a wiki page, an icon, an emoji, a tech level, and a list of aliases.
    Comes with EmbedFillableMixin, and the following as embed attributes:
    - icon (thumbnail)
    - manufacturer
    - value
    - tech level
    - colour (manufacturer)
    As well as the follwing, inherited from base classes:
    - name
    - aliases

    Subclasses must be decarated with `itemType`.
    This is the base class in the SQLAlchemy joined table inheritance pattern.

    ```py
    from .itemBase import ItemBase, itemType
    from ..database.constants import StoreableItemType

    @itemType(StoreableItemType.MyItem)
    class MyItem(ItemBase):
        __tablename__ = ...
    ```
    """
    __tablename__ = TableNames.AllItems.value

    _isStoreableBase = True
    _storeableItemType: StoreableItemType
    _polymorphicIdentityOverride: Optional[str] = None

    itemType: Mapped[StoreableItemType]
    id: Mapped[int]
    manufacturer: Mapped[Optional[str]]
    wikiUrl: Mapped[Optional[str]]
    iconUrl: Mapped[Optional[str]]
    techLevel: Mapped[Optional[int]]
    _emojiUnicode: Mapped[Optional[str]] = mapped_column()
    _emojiId: Mapped[Optional[int]] = mapped_column()
    
    emoji: Mapped[Optional[BasedEmoji]] = composite(_emojiId, _emojiUnicode)
    

    @declared_attr.directive
    def __mapper_args__(cls) -> Dict[str, Any]:
        args = {}

        if cls._isStoreableBase:
            args["polymorphic_on"] = cls.itemType
        else:
            if cls._polymorphicIdentityOverride is not None:
                args["polymorphic_identity"] = cls._polymorphicIdentityOverride
            else:    
                args["polymorphic_identity"] = cls._storeableItemType.value

        return args
    

    def __init__(self, name: str, **kw):
        """
        :param str name: The name of the item. Must be unique.
        """
        super().__init__(name, **kw)
        self.shopSpawnRate = 0
    

    def __init_subclass__(cls) -> None:
        """Do not overload this method. It is used to enable the ItemBase inheritance heirarchy.
        Overload _init_subclass instead.
        """
        cls._isStoreableBase = False
        cls._init_subclass()
        super().__init_subclass__()

    
    @classmethod
    def _init_subclass(cls) -> None:
        """This method is called when a class is subclassed.

        The default implementation does nothing. It may be overridden to extend subclasses.
        """


    @abstractmethod
    async def getValue(self) -> int:
        """Calculate the total value of this item.

        :return: The value of the item
        :rtype: int
        """
        raise NotImplementedError()
    

#region embed attributes

    @embedThumbnailUrl
    def iconOrNone(self): return self.iconUrl if self.iconUrl else None

    @embedField("Manufacturer", hideWhenNone=True)
    def formattedManufacturer(self): return self.manufacturer.title() if self.manufacturer else None

    @embedField("Value")
    async def formattedValue(self): return f"{commaSplitNum(await self.getValue())} Credits"

    @embedField("Tech Level", hideWhenNone=True)
    def formattedTechLevel(self): return self.techLevel

    @embedColour
    def manufacturerColour(self): return bbData.factionColours.get(self.manufacturer or "", bbData.factionColours["neutral"])

#endregion


    @abstractmethod
    def statsStringShort(self) -> str:
        """Summarise all the statistics and functionality of this item as a string.

        :return: A string summarising the statistics and functionality of this item
        :rtype: str
        """
        return "*No effect*"


    @abstractmethod
    async def serialize(self, saveType: Optional[bool] = False, **kwargs) -> SerializedItemBaseUnion:
        """Serialize this item into dictionary format.
        This base implementation should be used in itemBase implementations, and custom attributes saved into it.

        :param bool saveType: When true, include the string name of the object type in the output.
        :return: A dictionary containing all information needed to reconstruct this item.
        :rtype: dict
        """
        aliasableData = await super().serialize(**kwargs)

        data: SerializedItemBaseUnion = {
            **aliasableData,
            "id": self.id,
            "value": await self.getValue(),
            "wiki": self.wikiUrl,
            "manufacturer": self.manufacturer,
            "iconUrl": self.iconUrl,
            "emoji": self.emoji.serialize() if self.emoji else None,
            "techLevel": self.techLevel
        }

        if saveType:
            data = cast(TypedSerializedItemBase, data)
            data["type"] = type(self).__name__

        return data
