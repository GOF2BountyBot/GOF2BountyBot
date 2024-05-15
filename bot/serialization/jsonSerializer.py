from typing import Any, Dict, Type, TypeVar, cast

import asyncio

from ..database.unitOfWork import UnitOfWork
from .serializable import SqlSerializableMixin, isPolymorphicBase, getPolymorphicChild, deconstructDeserializedType, _JsonField # type: ignore[reportPrivateUsage]

T = TypeVar("T")
TField = TypeVar("TField", bound=property)
TClass = TypeVar("TClass", bound=Type["SqlSerializableMixin"])
TDeserialized = TypeVar("TDeserialized", bound="SqlSerializableMixin")

class JsonSerializer:
    async def serialize(self, o: SqlSerializableMixin) -> Dict[str, Any]:
        data: Dict[str, Any] = {}
        if o._jsonFields.get("serializePrimaryKeysOnly", False): # type: ignore[reportPrivateUsage]
            fields = (f for f in o._jsonFields.values() if f.isPrimaryKey) # type: ignore[reportPrivateUsage]
        else:
            fields = o._jsonFields.values() # type: ignore[reportPrivateUsage]

        async def handleField(field: _JsonField[Any]):
            v = await field.getValue(o)
            data[field.name] = self._serializeValue(field.deserializedType, v)

        await asyncio.wait((handleField(f) for f in fields if not f.serializeIgnore))

        return data


    def deserialize(self, T: Type[TDeserialized], data: Dict[str, Any], unitOfWork: UnitOfWork) -> TDeserialized:
        impl: Type[T] = T
        if isPolymorphicBase(T):
            polymorphicKey = data.get(T._jsonPolymorphicKey.name, None) # type: ignore[reportPrivateUsage]
            if polymorphicKey is not None:
                impl = getPolymorphicChild(T, polymorphicKey)

        params: Dict[str, Any] = {}
        pks = {f: data.get(f.name, None) for f in impl._jsonFields.values() if f.isPrimaryKey} # type: ignore[reportPrivateUsage]
        
        if not any(v is None for v in pks.values()):
            for field, fieldData in pks.items():
                params[field.name] = self._deserializeValue(field.deserializedType, fieldData, unitOfWork)

            # todo: impl should intersect SerializableMixin and DbSnowflake
            existing = unitOfWork.repository(impl).get(**params)
            if existing is not None:
                return existing

        remainingFields = (
            f for f in impl._jsonFields.values() # type: ignore[reportPrivateUsage]
            if f.name in data
            and not f.deserializeIgnore
            and f.name not in params
        )
        
        for field in remainingFields:
            params[field.name] = self._deserializeValue(field.deserializedType, data[field.name], unitOfWork)

        return impl(**params)
    

    def _serializeValue(self, deserializedType: type, o: Any) -> Any:
        implType, isOptional, genericParams = deconstructDeserializedType(deserializedType)

        if issubclass(implType, SqlSerializableMixin):
            return cast(Any, self.serialize(o))
        
        if isOptional:
            if o is None:
                return None
            
            nextType = next(t for t in genericParams if t is not type(None))
            return self._serializeValue(nextType, o)
        
        if issubclass(implType, list):
            nextType = genericParams[0]
            return [self._serializeValue(nextType, item) for item in o]
        
        if issubclass(implType, set):
            nextType = genericParams[0]
            return set(self._serializeValue(nextType, item) for item in o)
        
        if issubclass(implType, tuple):
            nextType = genericParams[0]
            return tuple(self._serializeValue(genericParams[i], item) for i, item in enumerate(o))
        
        if issubclass(implType, dict):
            keyType = genericParams[0]
            valueType = genericParams[1]
            return {
                self._serializeValue(keyType, k): self._serializeValue(valueType, v)
                for k, v in o.items()
            }
        
        return o

    
    def _deserializeValue(self, T: Type[T], data: Any, unitOfWork: UnitOfWork) -> T:
        implType, isOptional, genericParams = deconstructDeserializedType(T)

        if issubclass(implType, SqlSerializableMixin):
            return cast(T, self.deserialize(implType, data, unitOfWork))
        
        if isOptional:
            if data is None:
                return cast(T, None)
            
            nextType = cast(Type[T], next(t for t in genericParams if t is not type(None)))
            return self._deserializeValue(nextType, data, unitOfWork)
        
        if issubclass(implType, list):
            nextType = cast(Any, genericParams[0])
            return cast(T, [self._deserializeValue(nextType, item, unitOfWork) for item in data])
        
        if issubclass(implType, set):
            nextType = cast(Any, genericParams[0])
            return cast(T, set(self._deserializeValue(nextType, item, unitOfWork) for item in data))
        
        if issubclass(implType, tuple):
            nextType = cast(Any, genericParams[0])
            return cast(T, tuple(self._deserializeValue(cast(Any, genericParams[i]), item, unitOfWork) for i, item in enumerate(data)))
        
        if issubclass(implType, dict):
            keyType = cast(Any, genericParams[0])
            valueType = cast(Any, genericParams[1])
            return cast(T, {
                self._deserializeValue(keyType, k, unitOfWork): self._deserializeValue(valueType, v, unitOfWork)
                for k, v in data.items()
            })
        
        return data
    