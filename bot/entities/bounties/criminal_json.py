

class BuiltInSerializedCriminal(aliasable.SerializedAliasable, SerializedLoadedObject): pass

class TypedBuiltInSerializedCriminal(BuiltInSerializedCriminal):
    type: str

class CustomSerializedCriminal(BuiltInSerializedCriminal):
    isPlayer: bool
    icon: str
    faction: str
    aliases: List[str]

class TypedCustomSerializedCriminal(CustomSerializedCriminal, TypedBuiltInSerializedCriminal): pass

BuiltInSerializedCriminalUnion = Union[BuiltInSerializedCriminal, TypedBuiltInSerializedCriminal]
CustomSerializedCriminalUnion = Union[CustomSerializedCriminal, TypedCustomSerializedCriminal]
SerializedCriminalUnion = Union[BuiltInSerializedCriminal, TypedBuiltInSerializedCriminal, CustomSerializedCriminal, TypedCustomSerializedCriminal]