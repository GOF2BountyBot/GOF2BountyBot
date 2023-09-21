from abc import abstractmethod
from types import TracebackType
from typing import Any, Collection, Generic, Optional, Tuple, Type, TypeVar, Union, Any

from dataclasses import dataclass
from pathlib import Path
from contextlib import AbstractAsyncContextManager

from . import assetManager
from ..baseClasses.basedEnum import BasedEnum

ASSETS_BASE_PATH = "assets"


class FileType(BasedEnum):
    image = 0
    model = 1
    material = 2
    folder = 3


@dataclass
class _AssetType:
    path: str
    fileType: FileType


class AssetType(BasedEnum):
    shipSkinRender = _AssetType("items/ships/{holderIdentity}skinRenders", FileType.image)
    shipAutoskinMask = _AssetType("items/ships/{holderIdentity}autoskinMasks", FileType.image)
    shipAutoskinComponent = _AssetType("items/ships/{holderIdentity}autoskinTextures", FileType.image)
    shipModel = _AssetType("items/ships/{holderIdentity}", FileType.model)
    
    shipskinAutoskinTexture = _AssetType("items/ship skins/{holderIdentity}", FileType.image)


class AssetHolder:
    def __init__(self, identity: Optional[Union[Any, Collection[Any]]]) -> None:
        self.identity = identity
        self.segments: Tuple[str, ...] = () if identity is None else \
            tuple(str(i) for i in identity) \
            if isinstance(identity, Collection) else identity
        
    
    def path(self, assetType: AssetType, fileName: str) -> Path:
        assetPath: str = assetType.value
        identityPath = "/".join(self.segments)
        return Path(ASSETS_BASE_PATH, assetPath.format(holderIdentity=identityPath), fileName)


TLease = TypeVar("TLease", bound=assetManager.AssetLease)


class _AssetLeaseContextBase(AbstractAsyncContextManager, Generic[TLease]):
    def __init__(self, asset: "Asset"):
        self.asset = asset
        self.lease: Optional[TLease] = None

    
    async def release(self):
        if self.lease is None:
            raise AssertionError("The lease has not yet been aquired")
        await self.lease.release()


    @abstractmethod
    async def aquire(self) -> TLease:
        raise NotImplementedError()


    async def __aenter__(self):
        if self.lease is not None:
            raise AssertionError("The lease has already been aquired")
        self.lease = await self.aquire()
        return self


    async def __aexit__(self, __exc_type: Optional[type[BaseException]], __exc_value: Optional[BaseException], __traceback: Optional[TracebackType]) -> Optional[bool]:
        if self.lease is None:
            raise AssertionError("The lease has not yet been aquired")
        if await self.lease.active:
            await self.release()


class _AssetTransientReadContext(_AssetLeaseContextBase[assetManager.TransientReadAssetLease]):
    def __init__(self, asset: "Asset", lifetimeMs: int, aquireTimeoutMs: Optional[int]):
        super().__init__(asset)
        self.lifetimeMs = lifetimeMs
        self.aquireTimeoutMs = aquireTimeoutMs


    async def aquire(self):
        return await assetManager.AssetManager.waitForTransientRead(self.asset, lifetimeMs=self.lifetimeMs, aquireTimeoutMs=self.aquireTimeoutMs)
    

class _AssetPermanentReadContext(_AssetLeaseContextBase[assetManager.PermanentReadAssetLease]):
    def __init__(self, asset: "Asset", releaseCallback: assetManager.PermanentLeaseReleaseCallback, releaseTimeoutMs: int, aquireTimeoutMs: Optional[int]):
        super().__init__(asset)
        self.releaseCallback = releaseCallback
        self.releaseTimeoutMs = releaseTimeoutMs
        self.aquireTimeoutMs = aquireTimeoutMs


    async def aquire(self):
        return await assetManager.AssetManager.waitForPermanentRead(self.releaseCallback, self.asset, releaseTimeoutMs=self.releaseTimeoutMs, aquireTimeoutMs=self.aquireTimeoutMs)
    

class _AssetTransientReadWriteContext(_AssetLeaseContextBase[assetManager.TransientReadWriteAssetLease]):
    def __init__(self, asset: "Asset", lifetimeMs: int):
        super().__init__(asset)
        self.lifetimeMs = lifetimeMs


    async def aquire(self):
        return await assetManager.AssetManager.waitForTransientReadWrite(self.asset, lifetimeMs=self.lifetimeMs)


class Asset:
    def __init__(self, assetType: AssetType, fileName: str, *holderIdentity: Any) -> None:
        self.holder = AssetHolder(*holderIdentity)
        self.assetType = assetType
        self.fileName = fileName


    def enterTransientRead(self, lifetimeMs: int = 2000, aquireTimeoutMs: Optional[int] = None):
        """Wait asynchronously for a lease to be granted, to read this asset for the next `lifetimeMs`.

        This function returns a context manager. It should be used with an `async with` statement:

        ```py
        async with myAsset.enterTransientRead():
            open(myAsset.path)
        ```
        
        :param lifetimeMs: The lifetime of the lease in milliseconds, defaults to 2000
        :type lifetimeMs: int, optional
        :param aquireTimeoutMs: An optional timeout for waiting for the lease, defaults to None
        :type aquireTimeoutMs: Optional[int], optional
        :raises asyncio.TimeoutError: When `aquireTimeoutMs` is not `None`, and was exceeded whilst waiting for a lease
        """
        return _AssetTransientReadContext(self, lifetimeMs, aquireTimeoutMs)
    

    def enterPermanentRead(self, releaseCallback: assetManager.PermanentLeaseReleaseCallback, releaseTimeoutMs: int = 2000, aquireTimeoutMs: Optional[int] = None):
        """Wait asynchronously for a lease to be granted, to read this asset permanently.
        The asset can be assumed to be loaded into memory permanently.

        This function returns a context manager. It should be used with an `async with` statement:

        ```py
        files = []

        def read():
            files.append(open(myAsset.path))

        async def release(released, reacquire, deadlineMs):
            files[0].close()
            released()
            await reacquire()
        
        async with myAsset.enterPermanentRead(release):
            read()
        ```

        :param PermanentLeaseReleaseCallback releaseCallback: A callback to release the lease, and optionally reaquire it
        :param aquireTimeoutMs: An optional timeout for waiting for the lease, defaults to None
        :type aquireTimeoutMs: Optional[int], optional
        :param releaseTimeoutMs: The amount of time in milliseconds, allotted to release the lease during `releaseCallback`, defaults to 2000
        :type releaseTimeoutMs: int, optional
        :raises asyncio.TimeoutError: When `aquireTimeoutMs` is not `None`, and was exceeded whilst waiting for a lease
        """
        return _AssetPermanentReadContext(self, releaseCallback, releaseTimeoutMs, aquireTimeoutMs)
    

    def enterTransientReadWrite(self, lifetimeMs: int = 2000):
        return _AssetTransientReadWriteContext(self, lifetimeMs)
    

    @property
    def path(self):
        return self.holder.path(self.assetType, self.fileName)
