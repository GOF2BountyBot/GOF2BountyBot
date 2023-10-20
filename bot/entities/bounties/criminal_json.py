from ...baseClasses.aliasable_json import SerializedAliasable

class SerializedCriminal(SerializedAliasable):
    id: int
    isPlayer: bool
    iconUrl: str
    faction: str
