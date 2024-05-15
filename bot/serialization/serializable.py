from abc import ABC, abstractmethod
from typing import Any, Callable, ClassVar, Dict, Generic, List, Optional, Set, Tuple, Type, TypeVar, Union, cast, TypedDict, Awaitable, overload
from typing_extensions import NotRequired

from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import MappedColumn
from sqlalchemy.orm.decl_api import DeclarativeAttributeIntercept

from ..lib.typingUtil import getPropertyType

T = TypeVar("T")
TFieldValue = TypeVar("TFieldValue", bound=Any)
TField = TypeVar("TField", bound=Union[property, hybrid_property[Any], MappedColumn[Any]])
TClass = TypeVar("TClass", bound=Type["SqlSerializableMixin"])
TDeserialized = TypeVar("TDeserialized", bound="SqlSerializableMixin")


class _JsonField(Generic[TFieldValue]):
    "Replaced by SerializableMixin at run time with the underlying property"
    def __init__(self,
                 underlying: Union[property, hybrid_property[TFieldValue], MappedColumn[TFieldValue]],
                 serialize: bool,
                 deserialize: bool,
                 primaryKey: bool,
                 polymorphicKey: bool,
                 deserializedType: Type[TFieldValue],
                 name: Optional[str] = None) -> None:
        
        if name is not None:
            self.name = name
        elif isinstance(underlying, MappedColumn):
            self.name = underlying.name

        if isinstance(underlying, (property, hybrid_property)):
            if underlying.fget is None:
                raise ValueError()
        
            if name is None:
                self.name = (underlying.__name__
                    if isinstance(underlying, hybrid_property)
                    else underlying.fget.__name__)
                
        self.underlying = underlying
        self.serializeIgnore = not serialize
        self.deserializeIgnore = not deserialize
        self.isPrimaryKey = primaryKey
        self.isPolymorphicKey = polymorphicKey
        self.deserializedType = deserializedType
        # This needs to be set lazily by _SerializableMeta because _JsonField will always be
        # created as part of class creation
        self.ownerClass: Optional[type] = None


    async def getValue(self, modelSelf: Any) -> Any:
        v: Union[Any, Awaitable[Any]] = self.underlying.__get__(modelSelf, self.ownerClass or type(modelSelf))
        
        if isinstance(v, Awaitable):
            return await v
        return v


class _JsonOptions(TypedDict):
    serializePrimaryKeysOnly: NotRequired[bool]
    polymorphicKeyValue: NotRequired[Any]


# Dictionary of base class to:
#     Dictionary of polymorphic key value to associated child class
POLYMORPHIC_HEIRARCHY: Dict[Type["SqlSerializableMixin"], Dict[Any, Type["SqlSerializableMixin"]]] = {}


def _setPolymorphicBase(baseClass: Type["SqlSerializableMixin"]) -> None:
    if baseClass in POLYMORPHIC_HEIRARCHY:
        raise ValueError(f"Class {baseClass.__name__} is already a polymorphic base")
    POLYMORPHIC_HEIRARCHY[baseClass] = {}


def _setPolymorphicChild(impl: Type["SqlSerializableMixin"], polymorphicKey: Any) -> None:
    for base in impl.mro():
        heirarchy = POLYMORPHIC_HEIRARCHY.get(base, None)
        if heirarchy is None:
            continue
        
        existing = heirarchy.get(polymorphicKey, None)
        if existing is not None:
            raise ValueError(f"Class {existing.__name__} is already registered as the polymorphic"
                           + f" {base.__name__} implementation with key {polymorphicKey}")
        
        heirarchy[polymorphicKey] = impl
        break


def getPolymorphicChild(base: Type[TDeserialized], polymorphicKey: Any) -> Type[TDeserialized]:
    heirarchy = POLYMORPHIC_HEIRARCHY.get(base, None)
    if heirarchy is None:
        raise ValueError(f"{base.__name__} is not a polymorphic base class. Decorate the field which "
                       + f"will contain your key value using @{JsonSchema.__name__}.{JsonSchema.field.__name__}(polymorphicKey=True)")

    impl = heirarchy.get(polymorphicKey, None)
    if impl is None:
        raise KeyError(f"No json polymorphic {base.__name__} implementation is registered with key {polymorphicKey}")
    
    # Casting here because _setPolymorphicChild can only list subclasses in the heirarchy
    return cast(Type[TDeserialized], impl)


def isPolymorphicBase(base: Type["SqlSerializableMixin"]) -> bool:
    return base in POLYMORPHIC_HEIRARCHY


def deconstructDeserializedType(deserializedType: type) -> Tuple[Union[Type[Optional[Any]], Type[List[Any]], Type[Set[Any]], Type[Tuple[Any, ...]], Type[Dict[str, Any]]], bool, Tuple[type, ...]]:
    if not hasattr(deserializedType, "__origin__"):
        return deserializedType, False, ()
    
    origin: type = getattr(deserializedType, "__origin__")
    genericArgs: Tuple[type, ...] = getattr(deserializedType, "__args__")
    
    if origin == Union:
        isSingleLevelOptional = len(genericArgs) == 2 and type(None) in genericArgs
    else:
        isSingleLevelOptional = False

    if not isSingleLevelOptional and origin not in (list, set, tuple, dict):
        raise ValueError(f"Unsupported typing.Type {deserializedType}, only Optional, List, Set, Tuple and Dict are supported")
    
    return origin, isSingleLevelOptional, genericArgs


class _SerializableMetaBase(ABC, type):
    @abstractmethod
    def makeClass(cls, clsname: str, bases: Tuple[type], attrs: Dict[str, Any]) -> Type["_SerializableMixinBase"]:
        ...


    def SetUpSerializable(cls, clsname: str, bases: Tuple[type], attrs: Dict[str, Any]) -> Type["_SerializableMixinBase"]:
        jsonFields: Dict[str, _JsonField[Any]] = {}
        polymorphicKeyField: Optional[_JsonField[Any]] = None
        inheritedFields: Dict[_JsonField[Any], Type["_SerializableMixinBase"]] = {}
        isPolymorphicBase = False

        # Bubble up unoverridden fields from base classes
        for base in (b for b in bases if issubclass(b, _SerializableMixinBase)):
            for name, field in base._jsonFields.items(): # type: ignore[reportPrivateUsage]
                jsonFields[name] = field
                inheritedFields[field] = base
                if field.isPolymorphicKey:
                    polymorphicKeyField = field

        schema = attrs.get("_jsonSchema", None)
        if schema is not None and not isinstance(schema, JsonSchema):
            raise TypeError(f"_jsonSchema must be of type {JsonSchema.__name__}")
        
        isInheritedSchema = schema._ownerClass is not None # type: ignore[reportPrivateUsage]
        previousSchemaFieldCount = None if isInheritedSchema else \
            len(schema._currentClassFields) # type: ignore[reportPrivateUsage]
        
        # current class did not define a new json schema, don't bother validating fields
        if schema is None or isInheritedSchema:
            field: _JsonField[Any]
            for field in schema._currentClassFields: # type: ignore[reportPrivateUsage]  
                # Ensure uniqueness
                if field.name in jsonFields:
                    inheritedFrom = inheritedFields.get(field, None)
                    if inheritedFrom is None:
                        raise ValueError(f"Class {clsname} defines two json fields with the same name: {field.name}")

                    raise ValueError(f"Class {clsname} defines json field {field.name}, "
                                + f"which conflicts with one inherited from the parent "
                                + f"class {inheritedFrom.__name__}: {field.name}")
                
                jsonFields[field.name] = field

                # Take note of the polymorphic key
                if field.isPolymorphicKey:
                    if polymorphicKeyField is not None:
                        inheritedFrom = inheritedFields.get(field, None)
                        if inheritedFrom is None:
                            raise ValueError(f"Class {clsname} has more than one json polymorphic key field: "
                                        + f"{polymorphicKeyField.name}, {field.name}")
                        
                        raise ValueError(f"Class {clsname} defines a json polymorphic key field: "
                                        + f"{field.name}, which conflicts with one inherited from "
                                        + f"the parent class {inheritedFrom.__name__}: {polymorphicKeyField.name}")
                    
                    polymorphicKeyField = field
                    isPolymorphicBase = True

        o = cls.makeClass(clsname, bases, attrs)
        if isPolymorphicBase:
            _setPolymorphicBase(o)

        if previousSchemaFieldCount is not None \
                and len(schema._currentClassFields) != previousSchemaFieldCount: # type: ignore[reportPrivateUsage]
            raise ValueError(f"Illegal operation: Child class {type(o).__name__} modified the json schema of "
                            + "parent class. This probably means that you reused the inherited _jsonSchema. "
                            + "Make sure that your child class defines a new value for _jsonSchema.")
        
        if not isInheritedSchema:
            schema._ownerClass = type(o) # type: ignore[reportPrivateUsage]
            for field in schema._currentClassFields: # type: ignore[reportPrivateUsage]
                field.ownerClass = type(o)

        o._jsonFields = jsonFields # type: ignore[reportPrivateUsage]
        o._jsonOptions = {} # type: ignore[reportPrivateUsage]
        o._jsonPolymorphicKey = polymorphicKeyField # type: ignore[reportPrivateUsage]

        return o


class _SerializableMeta(_SerializableMetaBase):
    def makeClass(cls, clsname: str, bases: Tuple[type], attrs: Dict[str, Any]) -> type["_SerializableMixinBase"]:
        return type.__new__(cls, clsname, bases, attrs)
    
    def __new__(cls, clsname: str, bases: Tuple[type], attrs: Dict[str, Any]):
        return cls.SetUpSerializable(cls, clsname, bases, attrs) # type: ignore[reportArgumentType]


class _SerializableSqlMeta(_SerializableMetaBase, DeclarativeAttributeIntercept):
    def makeClass(cls, clsname: str, bases: Tuple[type], attrs: Dict[str, Any]) -> type["_SerializableMixinBase"]:
        return DeclarativeAttributeIntercept.__new__(cls, clsname, bases, attrs) # type: ignore[reportArgumentType]
    
    def __new__(cls, clsname: str, bases: Tuple[type], attrs: Dict[str, Any]):
        return cls.SetUpSerializable(cls, clsname, bases, attrs) # type: ignore[reportArgumentType]
    

class _SerializableMixinBase:
    _jsonFields: ClassVar[Dict[str, _JsonField[Any]]] = {}
    _jsonOptions: ClassVar[_JsonOptions] = {}
    _jsonPolymorphicKey: ClassVar[Optional[_JsonField[Any]]] = None
    _jsonSchema: ClassVar[Optional["JsonSchema"]] = None


class SerializableMixin(_SerializableMixinBase, metaclass=_SerializableMeta):
    pass


class SqlSerializableMixin(_SerializableMixinBase, metaclass=_SerializableSqlMeta):
    pass


class JsonSchema:
    def __init__(self) -> None:
        self._currentClassFields: List[_JsonField[Any]] = []
        # This must be set lazily, as JsonSchema is created during construction of the owning class
        self._ownerClass: Optional[type] = None


    @overload
    def field(self, field: Union[property, hybrid_property[Any], MappedColumn[Any]], /, *, serialize: bool = True, deserialize: bool = True, primaryKey: bool = False, polymorphicKey: bool = False, name: Optional[str] = None) -> None:
        """Mark a property or mapped SQL column as a json field.

        :param field: The property or mapped SQL column
        :type field: Union[property, hybrid_property[Any], MappedColumn[Any]]
        :param serialize: Include this field during serialization, defaults to True
        :type serialize: bool, optional
        :param deserialize: Include this field during deserialization, defaults to True
        :type deserialize: bool, optional
        :param primaryKey: The class instance can be identified using only this field, along with all other primary keys, defaults to False
        :type primaryKey: bool, optional
        :param polymorphicKey: This field gives the value for the class's polymorphic key, defaults to False
        :type polymorphicKey: bool, optional
        :param name: Optional json field name override, defaults to None
        :type name: Optional[str], optional
        """

    @overload
    def field(self, *, serialize: bool = True, deserialize: bool = True, primaryKey: bool = False, polymorphicKey: bool = False, name: Optional[str] = None) -> Callable[[TField], TField]:
        """A decorator marking a property or hybrid property as a json field.

        :param serialize: Include this field during serialization, defaults to True
        :type serialize: bool, optional
        :param deserialize: Include this field during deserialization, defaults to True
        :type deserialize: bool, optional
        :param primaryKey: The class instance can be identified using only this field, along with all other primary keys, defaults to False
        :type primaryKey: bool, optional
        :param polymorphicKey: This field gives the value for the class's polymorphic key, defaults to False
        :type polymorphicKey: bool, optional
        :param name: Optional json field name override, defaults to None
        :type name: Optional[str], optional
        """

    def field(self, maybeField: Optional[TField] = None, *, serialize: bool = True, deserialize: bool = True, primaryKey: bool = False, polymorphicKey: bool = False, name: Optional[str] = None) -> Optional[Callable[[TField], TField]]:
        def makeJsonField(field: Union[property, hybrid_property[Any], MappedColumn[Any]]):
            if isinstance(field, (property, hybrid_property)):
                if field.fget is None:
                    raise ValueError("Json field properties must have a getter method. Make sure @jsonField is at the end of your decorator chain")
                
                propertyType = getPropertyType(field)
                if propertyType is None:
                    fieldName = field.__name__ if isinstance(field, hybrid_property) else field.fget.__name__
                    raise ValueError(f"The type for property-mapped json field '{fieldName}' could not be determined. Make sure that your method has an appropriate type hint")
                
                deserializedType = propertyType

            else:
                if not hasattr(field, "type"):
                    raise ValueError(f"The type for SQL-mapped json field '{field.name}' could not be determined. Only directly mapped columns are supported by jsonField currently, please use a property for more complex json field mappings")
                
                deserializedType: Any = getattr(field, "type").python_type

            # Validate deserialized type can be handled
            deconstructDeserializedType(deserializedType)
            return _JsonField(field, serialize, deserialize, primaryKey, polymorphicKey, deserializedType, name=name)
        
        def decorator(field: TField, /) -> TField:
            fieldMeta = makeJsonField(field)
            self._currentClassFields.append(fieldMeta)
            return field
        
        # If we were not given the field, then the method is being used as a decorator
        if maybeField is None:
            return decorator
        
        # If we were given the field, use it directly
        fieldMeta = makeJsonField(maybeField)
        self._currentClassFields.append(fieldMeta)

        return None


def jsonOptions(serializePksOnly: bool = False, polymorphicKey: Any = None):
    """Class decorator configuring special json serializer/deserializer behaviour.
    """
    def decorator(t: TClass) -> TClass:
        t._jsonOptions["serializePrimaryKeysOnly"] = serializePksOnly # type: ignore[reportPrivateUsage]
        if polymorphicKey is None:
            return t
        
        if t._jsonPolymorphicKey is None: # type: ignore[reportPrivateUsage]
            raise ValueError(f"Class {t.__name__} has a polymorphic key value, but no polymorphic "
                           + f"key field. Decorate the field which will contain your key value using "
                           + f"@{JsonSchema.__name__}.{JsonSchema.field.__name__}(polymorphicKey=True)")
        
        t._jsonOptions["polymorphicKeyValue"] = polymorphicKey # type: ignore[reportPrivateUsage]
        _setPolymorphicChild(t, polymorphicKey)
        return t
    
    return decorator
