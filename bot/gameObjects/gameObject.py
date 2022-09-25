from typing import TypedDict, TypeVar, Type
from abc import abstractmethod

from ..baseClasses.serializable import SerializesToSchema

TSelf = TypeVar("TSelf", bound="LoadedObject")

class SerializedLoadedObject(TypedDict):
    builtIn: bool


class LoadedObject(SerializesToSchema[SerializedLoadedObject]):
    """ABC for objects that were loaded into the game from file.
    To allow for loading from config files, this must be serializable to JSON, and have a `builtIn` bool
    to indicate whether the object is BB official or custom.
    """
    def __init__(self, builtIn: bool = False):
        self.builtIn = builtIn

    @abstractmethod
    def serialize(self, **kwargs) -> SerializedLoadedObject: ...

    @classmethod
    @abstractmethod
    def deserialize(cls: Type[TSelf], data: SerializedLoadedObject, **kwargs) -> TSelf: ...