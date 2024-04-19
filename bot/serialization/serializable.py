from typing import Any, ClassVar, Dict, List, Optional, Set, Tuple, Type, TypeVar, Union, cast, TypedDict
from typing_extensions import NotRequired
from sqlmock import UnitOfWork

T = TypeVar("T")
TField = TypeVar("TField", bound=property)
TClass = TypeVar("TClass", bound=Type["SerializableMixin"])
TDeserialized = TypeVar("TDeserialized", bound="SerializableMixin")

class _JsonField:
    "Replaced by SerializableMixin at run time with the underlying property"
    def __init__(self,
                 underlying: property,
                 serialize: bool,
                 deserialize: bool,
                 primaryKey: bool,
                 polymorphicKey: bool,
                 deserializedType: Type[Any]) -> None:
        getter = underlying.fget
        if getter is None:
            raise ValueError()
        self.getter = getter
        self.underlying = underlying
        self.name = getter.__name__
        self.serializeIgnore = not serialize
        self.deserializeIgnore = not deserialize
        self.isPrimaryKey = primaryKey
        self.isPolymorphicKey = polymorphicKey
        self.deserializedType = deserializedType


class _JsonOptions(TypedDict):
    serializePrimaryKeysOnly: NotRequired[bool]
    polymorphicKeyValue: NotRequired[Any]


# Dictionary of base class to:
#     Dictionary of polymorphic key value to associated child class
POLYMORPHIC_HEIRARCHY: Dict[Type["SerializableMixin"], Dict[Any, Type["SerializableMixin"]]] = {}


def _setPolymorphicBase(baseClass: Type["SerializableMixin"]) -> None:
    if baseClass in POLYMORPHIC_HEIRARCHY:
        raise ValueError(f"Class {baseClass.__name__} is already a polymorphic base")
    POLYMORPHIC_HEIRARCHY[baseClass] = {}


def _setPolymorphicChild(impl: Type["SerializableMixin"], polymorphicKey: Any) -> None:
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
                       + f"will contain your key value using @{jsonField.__name__}(polymorphicKey=True)")

    impl = heirarchy.get(polymorphicKey, None)
    if impl is None:
        raise KeyError(f"No json polymorphic {base.__name__} implementation is registered with key {polymorphicKey}")
    
    # Casting here because _setPolymorphicChild can only list subclasses in the heirarchy
    return cast(Type[TDeserialized], impl)


def isPolymorphicBase(base: Type["SerializableMixin"]) -> bool:
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


class _SerializableMeta(type):
    def __new__(cls, clsname: str, bases: Tuple[type], attrs: Dict[str, Any]) -> Type["SerializableMixin"]:
        jsonFields: Dict[str, _JsonField] = {}
        polymorphicKeyField: Optional[_JsonField] = None
        inherited: Dict[_JsonField, Type["SerializableMixin"]] = {}
        isPolymorphicBase = False

        # Bubble up unoverridden fields from base classes
        for base in (b for b in bases if issubclass(b, SerializableMixin)):
            for name, field in base._jsonFields.items(): # type: ignore[reportPrivateUsage]    
                jsonFields[name] = field
                inherited[field] = base
                if field.isPolymorphicKey:
                    polymorphicKeyField = field

        for name, field in ((n, f) for n, f in attrs.items() if isinstance(f, _JsonField)):
            # Ensure uniqueness
            if field.name in jsonFields:
                inheritedFrom = inherited.get(field, None)
                if inheritedFrom is None:
                    raise ValueError(f"Class {clsname} defines two json fields with the same name: {field.name}")

                raise ValueError(f"Class {clsname} defines json field {field.name}, "
                               + f"which conflicts with one inherited from the parent "
                               + f"class {inheritedFrom.__name__}: {field.name}")
            
            jsonFields[field.name] = field

            # Take note of the polymorphic key
            if field.isPolymorphicKey:
                if polymorphicKeyField is not None:
                    inheritedFrom = inherited.get(field, None)
                    if inheritedFrom is None:
                        raise ValueError(f"Class {clsname} has more than one json polymorphic key field: "
                                       + f"{polymorphicKeyField.name}, {field.name}")
                    
                    raise ValueError(f"Class {clsname} defines a json polymorphic key field: "
                                    + f"{field.name}, which conflicts with one inherited from "
                                    + f"the parent class {inheritedFrom.__name__}: {polymorphicKeyField.name}")
                
                polymorphicKeyField = field
                isPolymorphicBase = True

            # Unwrap the JsonFieldMarker, replacing the field on the object with the underlying property
            attrs[name] = field.underlying

        o = cast(Type["SerializableMixin"], super().__new__(cls, clsname, bases, attrs))
        if isPolymorphicBase:
            _setPolymorphicBase(o)

        o._jsonFields = jsonFields # type: ignore[reportPrivateUsage]
        o._jsonOptions = {} # type: ignore[reportPrivateUsage]
        o._jsonPolymorphicKey = polymorphicKeyField # type: ignore[reportPrivateUsage]

        return o

class SerializableMixin(metaclass=_SerializableMeta):
    _jsonFields: ClassVar[Dict[str, _JsonField]] = {}
    _jsonOptions: ClassVar[_JsonOptions] = {}
    _jsonPolymorphicKey: ClassVar[Optional[_JsonField]] = None


def jsonField(deserializedType: Type[Any], serialize: bool = True, deserialize: bool = True, primaryKey: bool = False, polymorphicKey: bool = False):
    def decorator(field: TField) -> TField:
        # Validate deserialized type can be handled
        deconstructDeserializedType(deserializedType)
        return cast(TField, _JsonField(field, serialize, deserialize, primaryKey, polymorphicKey, deserializedType))
    return decorator


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
                           + f"@{jsonField.__name__}(polymorphicKey=True)")
        
        t._jsonOptions["polymorphicKeyValue"] = polymorphicKey # type: ignore[reportPrivateUsage]
        _setPolymorphicChild(t, polymorphicKey)
        return t
    
    return decorator