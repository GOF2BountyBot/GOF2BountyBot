from typing import Protocol, Generic, TypeVar

T = TypeVar("T", covariant=True)

class Factory(Protocol, Generic[T]):
    def create(self) -> T: ...


class AsyncFactory(Protocol, Generic[T]):
    async def create(self) -> T: ...
