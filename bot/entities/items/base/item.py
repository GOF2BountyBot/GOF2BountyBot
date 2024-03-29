from typing import Any, Dict, Optional, TypeVar, cast

from abc import abstractmethod

from sqlalchemy.orm import DeclarativeBase, declared_attr, Mapped, composite, mapped_column
from sqlalchemy import ForeignKey
from sqlalchemy.ext.asyncio import AsyncAttrs

from ....database.constants import StoreableItemType
from ....database.tables import TableNames
from ....lib.emojis import BasedEmoji
from ....lib.sql import EmbedFillableSqlTableMeta
from ....lib.stringUtil import commaSplitNum
from ....baseClasses.embedFillable import EmbedFillableMixin, embedField, embedThumbnailUrl, embedColour
from ....baseClasses.aliasable import AliasableMixin
from ....baseClasses.aliasable_json import SerializedAliasable
from .item_json import SerializedItemUnion, TypedSerializedItem
from ....cfg import cfg


class ItemDeclarativeBase(DeclarativeBase, AsyncAttrs): pass


class AnyItem(ItemDeclarativeBase):
    """Do not inherit from this class. Instead use `Item`.
    This is the base class in the SQLAlchemy joined table inheritance pattern.

    This class acts as a union over all items in the game. For all items in the game, the table contains:
    - item ID
    - item category (StoreableItemType)
    - concrete class identifier
    """
    __tablename__ = TableNames.AllItems.value

    _isStoreableBase = True

    id: Mapped[int] = mapped_column(primary_key=True)
    itemType: Mapped[StoreableItemType]
    _mappedType: Mapped[str]
    

    @declared_attr.directive
    def __mapper_args__(cls) -> Dict[str, Any]:
        args: Dict[str, Any] = {}

        if cls._isStoreableBase:
            args["polymorphic_on"] = cls._mappedType
        else:
            args["polymorphic_identity"] = cls.__name__

        return args
    

TSchema = TypeVar("TSchema", bound=SerializedItemUnion)


class Item(AnyItem, AliasableMixin[TSchema], EmbedFillableMixin, metaclass=EmbedFillableSqlTableMeta):
    """Base class for in-game items.

    Direct `Item` subclasses MUST:
    - be decorated with `item_storeable.itemType`

    Direct or indirect `Item` subclasses MUST:
    - NOT define any primary keys.
    - NOT define their own `DeclarativeBase`.

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

    Note that Item does not include a mapped field called `value` - it only defines an abstract method getValue.
    Note that Item does not include Workshoppable.

    Items each belong to a category defined by the StoreableItemType enum.
    When an inventory receives an item from the database, it needs to know what type of item it is,
    in order to keep the item in the correct section of the inventory.

    For this reason, direct Item subclasses must be decarated with `itemType`.
    Indirect subclasses will inherit the parent's item type, and therefore be categorized the same in inventories.

    ```py
    from .item import Item
    from .item_storeable import itemType
    from ..database.constants import StoreableItemType
    from .myItem_json import SerializedMyItem
    
    TSchema = TypeVar("TSchema", bound=SerializedMyItem)

    @itemType(StoreableItemType.MyItem)
    class MyItem(Item[TSchema]):
        __tablename__ = ...

        async def getValue(self) -> int:
            ...

        async def statsStringShort(self) -> str:
            return super().statsStringShort()

        async def serialize(self, **kwargs: Any) -> MyItem[TSchema]:
            data = await super().serialize(**kwargs)
            ...
    ```
    """
    id: Mapped[int] = mapped_column(ForeignKey(f"{TableNames.AllItems.value}.id"), primary_key=True)
    _storeableItemType: StoreableItemType
    manufacturer: Mapped[Optional[str]]
    wikiUrl: Mapped[Optional[str]]
    iconUrl: Mapped[str]
    techLevel: Mapped[Optional[int]]
    _emojiUnicode: Mapped[Optional[str]] = mapped_column()
    _emojiId: Mapped[Optional[int]] = mapped_column()
    
    emoji: Mapped[Optional[BasedEmoji]] = composite(_emojiId, _emojiUnicode)

    def __init__(self, name: str, **kw: Any):
        """
        :param str name: The name of the item. Must be unique.
        """
        super().__init__(name, **kw)
        self.shopSpawnRate = 0
    

    def __init_subclass__(cls) -> None:
        """Do not overload this method. It is used to enable the Item inheritance heirarchy.
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
    def manufacturerColour(self): return cfg.factionColourOrDefault(self.manufacturer)

#endregion


    @abstractmethod
    async def statsStringShort(self) -> str:
        """Summarise all the statistics and functionality of this item as a string.

        :return: A string summarising the statistics and functionality of this item
        :rtype: str
        """
        return "*No effect*"


    @abstractmethod
    async def serialize(self, **kwargs: Any) -> TSchema:
        """Serialize this item into dictionary format.
        This base implementation should be used in item implementations, and custom attributes saved into it.

        :param bool saveType: When true, include the string name of the object type in the output.
        :return: A dictionary containing all information needed to reconstruct this item.
        :rtype: dict
        """
        aliasableData: SerializedAliasable = await super().serialize(**kwargs)

        data: SerializedItemUnion = {
            **aliasableData,
            "id": self.id,
            "value": await self.getValue(),
            "iconUrl": self.iconUrl
        }

        if self.manufacturer is not None:
            data["manufacturer"] = self.manufacturer

        if self.wikiUrl is not None:
            data["wikiUrl"] = self.wikiUrl

        if self.emoji is not None:
            data["emoji"] = await self.emoji.serialize()

        if self.techLevel is not None:
            data["techLevel"] = self.techLevel

        if kwargs.get("saveType", False):
            data = cast(TypedSerializedItem, data)
            data["type"] = type(self).__name__

        return data