import asyncio
from typing import Any, ClassVar, Dict, Optional, Set, Tuple, Union, overload, Protocol
from typing_extensions import Never

from readerwriterlock.rwlock_async import RWLockWrite, Lockable
from asyncio import Lock, TimeoutError
from pathlib import Path
from abc import ABC, abstractmethod

from . import asset


class PermanentLeaseReleaseCompleteCallback(Protocol):
    def __call__(self) -> None:
        """Report to the asset lease that the release has completed successfully.
        After calling this, the lease may be reaquired safely.
        """


class StaticPermanentLeaseReaquireCallback(Protocol):
    async def __call__(self, aquireTimeoutMs: Optional[int] = None) -> None:
        """Re-aquire a permanent asset lease, following a forced lease release.

        :param aquireTimeoutMs: An optional timeout for waiting for the lease, defaults to None
        :type aquireTimeoutMs: Optional[int], optional
        :return: A lease granting read access to the requested asset permanently
        :rtype: AssetLock
        :raises asyncio.TimeoutError: When `aquireTimeoutMs` is not `None`, and was exceeded whilst waiting for a lease
        """


class InstancePermanentLeaseReaquireCallback(Protocol):
    async def __call__(cbSelf, self, aquireTimeoutMs: Optional[int] = None) -> None: # type: ignore[reportSelfClsParameterName]
        """Re-aquire a permanent asset lease, following a forced lease release.

        :param aquireTimeoutMs: An optional timeout for waiting for the lease, defaults to None
        :type aquireTimeoutMs: Optional[int], optional
        :return: A lease granting read access to the requested asset permanently
        :rtype: AssetLock
        :raises asyncio.TimeoutError: When `aquireTimeoutMs` is not `None`, and was exceeded whilst waiting for a lease
        """

PermanentLeaseReaquireCallback = Union[StaticPermanentLeaseReaquireCallback, InstancePermanentLeaseReaquireCallback]


class PermanentLeaseReleaseCallback(Protocol):
    async def __call__(self, released: PermanentLeaseReleaseCompleteCallback, reacquire: PermanentLeaseReaquireCallback, deadlineMs: int) -> None:
        """A user-provided callback that the AssetManager will call.
        This callback must release the lease within `deadlineMs`, after which the lease will be revoked.
        Once the lease has been released, `reaquireLease` can be awaited to require it.

        :param releaseDeadlineMs: The allotted time in which the lease must be released
        :type releaseDeadlineMs: int
        :param reacquireLease: A callback to use after the lease has been released, in order to reaquire it
        :type reacquireLease: PermanentLeaseReaquireCallback
        """


class AssetLease(ABC):
    def __init__(self, path: Path, leaseHolder: "AssetLeases", lock: Lockable) -> None:
        self.path = path
        self.holder = leaseHolder
        self.lock = lock
        self._active = True
        self._activeLock = Lock()


    async def revoke(self):
        async with self._activeLock:
            if not self._active:
                return
            self._active = False
        
        await self._revokeInternal()


    async def release(self):
        async with self._activeLock:
            if not self._active:
                return
            self._active = False
        
        await self._revokeInternal()
 

    @property
    async def active(self) -> bool:
        async with self._activeLock:
            return self._active


    @abstractmethod
    async def _revokeInternal(self) -> None:
        raise NotImplementedError()


    @abstractmethod
    async def _releaseInternal(self) -> None:
        raise NotImplementedError()


class PermanentAssetLease(AssetLease):
    reaquire: PermanentLeaseReaquireCallback

    def __init__(self, path: Path, leaseHolder: "AssetLeases", lock: Lockable, releaseCallback: PermanentLeaseReleaseCallback, releaseDeadlineMs: int) -> None:
        super().__init__(path, leaseHolder, lock)
        self.releaseCallback = releaseCallback
        self.releaseDeadlineMs = releaseDeadlineMs


class TransientAssetLease(AssetLease):
    def __init__(self, path: Path, leaseHolder: "AssetLeases", lock: Lockable, lifetimeMs: int) -> None:
        super().__init__(path, leaseHolder, lock)
        self.lifetimeMs = lifetimeMs
        self.lifetimeTask = asyncio.create_task(self._startLifetime())


    async def _startLifetime(self):
        await asyncio.sleep(self.lifetimeMs)
        await self.revoke()


    def _cancelLifetimeTask(self):
        self.lifetimeTask.cancel()


class PermanentReadAssetLease(PermanentAssetLease):
    async def reaquire(self, aquireTimeoutMs: Optional[int] = None):
        await self.holder.aquirePermanentRead(self.releaseCallback, self.releaseDeadlineMs, aquireTimeoutMs=aquireTimeoutMs or -1)


    async def _releaseInternal(self):
        await self.holder.releasePermanentRead(self)


    async def _revokeInternal(self):
        await self.release()


class TransientReadAssetLease(TransientAssetLease):
    async def _releaseInternal(self):
        try:
            self._cancelLifetimeTask()
        finally:
            await self.holder.releaseTransientRead(self)


    async def _revokeInternal(self):
        return await self.release()


class TransientReadWriteAssetLease(TransientAssetLease):
    async def _releaseInternal(self):
        try:
            self._cancelLifetimeTask()
        finally:
            await self.holder.releaseTransientReadWrite(self)


    async def _revokeInternal(self):
        return await self.release()


class AssetLeases:
    def __init__(self, path: Path) -> None:
        # For information on RWLockWrite, see the package's GitHub page: https://github.com/elarivie/pyReaderWriterLock
        # and wikipedia: https://github.com/elarivie/pyReaderWriterLock
        # I do want writers to be allowed to execute as soon as possible, but I expect writes to be very very rare, so it won't
        # be possible for a reader to be starved. No need for a fair wrlock, so let's go for the simpler writers-preference lock.
        # Once a file is written to, it could be read from again - for example, generating an image and then sending it in a message.
        # This is a good use case for the 'downgradeable' variant of the lock, but I don't want to have to add extra logic
        # to the asset manager. Maybe we'll implement this in the future for better efficiency.
        self.lockFactory = RWLockWrite()
        self.permanentReads: Set[PermanentReadAssetLease] = set()
        self.count = 0
        self.countLock = Lock()
        self.path = path
        self._active = True


    def _ensureActive(self):
        if not self._active:
            raise AssertionError(f"This lease manager for asset {self.path} is expired. Make sure that you only request leases via the static {AssetManager.__name__} class.")

    
    async def aquireTransientRead(self, lifetimeMs: int, aquireTimeoutMs: int = -1) -> TransientReadAssetLease:
        self._ensureActive()
        lock = await self.lockFactory.gen_rlock()
        await lock.acquire(timeout=aquireTimeoutMs)
        async with self.countLock:
            self.count += 1
        return TransientReadAssetLease(self.path, self, lock, lifetimeMs)


    async def releaseTransientRead(self, lease: TransientReadAssetLease):
        await lease.lock.release()
        async with self.countLock:
            self.count -= 1
            if self._active and self.count == 0:
                await self._dispose()


    async def aquirePermanentRead(self, releaseCallback: PermanentLeaseReleaseCallback, releaseDeadlineMs: int, aquireTimeoutMs: int = -1) -> PermanentReadAssetLease:
        self._ensureActive()
        lock = await self.lockFactory.gen_rlock()
        await lock.acquire(timeout=aquireTimeoutMs)

        lease = PermanentReadAssetLease(self.path, self, lock, releaseCallback, releaseDeadlineMs)
        self.permanentReads.add(lease)
        
        async with self.countLock:
            self.count += 1

        return lease


    async def releasePermanentRead(self, lease: PermanentReadAssetLease):
        await lease.lock.release()
        if lease in self.permanentReads:
            self.permanentReads.remove(lease)
        async with self.countLock:
            self.count -= 1
            if self._active and self.count == 0:
                await self._dispose()


    async def notifyPermanentReads(self, deadlineMs: int):
        leaseTasks = {
            asyncio.create_task(lease.releaseCallback(lambda: self.permanentReads.remove(lease), lease.reaquire, deadlineMs))
                : lease
            for lease in self.permanentReads    
        }
        
        await asyncio.wait(leaseTasks.keys(), timeout=deadlineMs)
        await asyncio.wait((releaseTask for releaseTask, lease in leaseTasks.items() if lease not in self.permanentReads))
        self.permanentReads.clear()


    async def aquireTransientReadWrite(self, lifetimeMs: int) -> TransientReadWriteAssetLease:
        self._ensureActive()
        deadlineMs = max(lease.releaseDeadlineMs for lease in self.permanentReads)
        _ = self.notifyPermanentReads(deadlineMs)
        
        lock = await self.lockFactory.gen_wlock()
        success = await lock.acquire(timeout=deadlineMs)
        if not success:
            raise TimeoutError()
            
        async with self.countLock:
            self.count += 1
        
        return TransientReadWriteAssetLease(self.path, self, lock, lifetimeMs)
        

    async def releaseTransientReadWrite(self, lease: TransientReadWriteAssetLease):
        await lease.lock.release()
        async with self.countLock:
            self.count -= 1
            if self._active and self.count == 0:
                await self._dispose()


    async def _dispose(self):
        await AssetManager._leaseHolderExpired(self) # type: ignore[reportPrivateUsage]



class AssetManager:
    """Static class guaranteeing access to on-disk resources with a leases mechanism, to ensure that
    an asset is not simultaneously read from and written to.

    In the future, this class will also provide empty fallback versions of assets, when they are unavailable.
    
    A 'read' lease can be transient or permanent.
    A transient lease has a lifetime, after which the lease is revoked.
    A permanent lease does not have a lifetime, but the accessor must also specify a 'release' callback,
    whereupon the accessor must relinquish the asset within a given timeframe.

    A 'read-write' lease must be transient, and is guaranteed to be the only active lease on the asset.
    """
    def __new__(cls) -> Never:
        raise TypeError(f"{cls.__name__} is static and cannot be instanciated")
    
    _assets: ClassVar[Dict[Path, AssetLeases]] = {}
    _assetsLock = Lock()

    @classmethod
    async def _getLeaseHolder(cls, assetOrType: Union[asset.AssetType, asset.Asset], fileName: str, holderIdentity: Tuple[Any, ...]):
        if not isinstance(assetOrType, asset.Asset):
            assetOrType = asset.Asset(assetOrType, fileName, *holderIdentity)

        async with cls._assetsLock:
            state = cls._assets.get(assetOrType.path, None)
            if state is None:
                cls._assets[assetOrType.path] = state = AssetLeases(assetOrType.path)
            return state
    

    @classmethod
    async def _leaseHolderExpired(cls, leaseHolder: AssetLeases):
        async with cls._assetsLock:
            cls._assets.pop(leaseHolder.path, None)
    

    @overload
    @classmethod
    async def waitForTransientRead(cls, asset: asset.Asset, /, *, lifetimeMs: int = 2000, aquireTimeoutMs: Optional[int] = None) -> TransientReadAssetLease:
        """Wait asynchronously for a lease to be granted, to read this asset for the next `lifetimeMs`.

        :param asset: The asset to lease
        :type asset: asset.Asset
        :param lifetimeMs: The lifetime of the lease in milliseconds, defaults to 2000
        :type lifetimeMs: int, optional
        :param aquireTimeoutMs: An optional timeout for waiting for the lease, defaults to None
        :type aquireTimeoutMs: Optional[int], optional
        :return: A lease granting read access to the requested asset for the next `lifetimeMs`
        :rtype: TransientReadAssetLease
        :raises asyncio.TimeoutError: When `aquireTimeoutMs` is not `None`, and was exceeded whilst waiting for a lease
        """

    @overload
    @classmethod
    async def waitForTransientRead(cls, assetType: asset.AssetType, fileName: str, /, *holderIdentity: Any, lifetimeMs: int = 2000, aquireTimeoutMs: Optional[int] = None) -> TransientReadAssetLease:
        """Wait asynchronously for a lease to be granted, to read this asset for the next `lifetimeMs`.

        :param assetType: The type of asset to lease
        :type asset: asset.AssetType
        :param str fileName: The name of the file on disk to lease. Only the file name, not the path
        :param Any holderIdentity: Identifiers for the holder of the asset. These are used when building the file path
        :param lifetimeMs: The lifetime of the lease in milliseconds, defaults to 2000
        :type lifetimeMs: int, optional
        :param aquireTimeoutMs: An optional timeout for waiting for the lease, defaults to None
        :type aquireTimeoutMs: Optional[int], optional
        :return: A lease granting read access to the requested asset for the next `lifetimeMs`
        :rtype: TransientReadAssetLease
        :raises asyncio.TimeoutError: When `aquireTimeoutMs` is not `None`, and was exceeded whilst waiting for a lease
        """

    @classmethod
    async def waitForTransientRead(cls, assetOrType: Union[asset.AssetType, asset.Asset], fileName: str = "", /, *holderIdentity: Any, lifetimeMs: int = 2000, aquireTimeoutMs: Optional[int] = None) -> TransientReadAssetLease:
        leaseHolder = await cls._getLeaseHolder(assetOrType, fileName, holderIdentity)
        return await leaseHolder.aquireTransientRead(lifetimeMs, aquireTimeoutMs or -1)
    

    @overload
    @classmethod
    async def waitForPermanentRead(cls, releaseCallback: PermanentLeaseReleaseCallback, asset: asset.Asset, /, *, releaseTimeoutMs: int = 2000, aquireTimeoutMs: Optional[int] = None) -> PermanentReadAssetLease:
        """Wait asynchronously for a lease to be granted, to read this asset permanently.
        The asset can be assumed to be loaded into memory permanently.

        :param PermanentLeaseReleaseCallback releaseCallback: A callback to release the lease, and optionally reaquire it
        :param assetType: The type of asset to lease
        :type asset: asset.AssetType
        :param str fileName: The name of the file on disk to lease. Only the file name, not the path
        :param Any holderIdentity: Identifiers for the holder of the asset. These are used when building the file path
        :param aquireTimeoutMs: An optional timeout for waiting for the lease, defaults to None
        :type aquireTimeoutMs: Optional[int], optional
        :param releaseTimeoutMs: The amount of time in milliseconds, allotted to release the lease during `releaseCallback`, defaults to 2000
        :type releaseTimeoutMs: int, optional
        :return: A lease granting read access to the requested asset permanently
        :rtype: PermanentReadAssetLease
        :raises asyncio.TimeoutError: When `aquireTimeoutMs` is not `None`, and was exceeded whilst waiting for a lease
        """

    @overload
    @classmethod
    async def waitForPermanentRead(cls, releaseCallback: PermanentLeaseReleaseCallback, assetType: asset.AssetType, fileName: str, /, *holderIdentity: Any, releaseTimeoutMs: int = 2000, aquireTimeoutMs: Optional[int] = None) -> PermanentReadAssetLease:
        """Wait asynchronously for a lease to be granted, to read this asset permanently.
        The asset can be assumed to be loaded into memory permanently.

        :param PermanentLeaseReleaseCallback releaseCallback: A callback to release the lease, and optionally reaquire it
        :param assetType: The type of asset to lease
        :type asset: asset.AssetType
        :param str fileName: The name of the file on disk to lease. Only the file name, not the path
        :param Any holderIdentity: Identifiers for the holder of the asset. These are used when building the file path
        :param aquireTimeoutMs: An optional timeout for waiting for the lease, defaults to None
        :type aquireTimeoutMs: Optional[int], optional
        :param releaseTimeoutMs: The amount of time in milliseconds, allotted to release the lease during `releaseCallback`, defaults to 2000
        :type releaseTimeoutMs: int, optional
        :return: A lease granting read access to the requested asset permanently
        :rtype: PermanentReadAssetLease
        :raises asyncio.TimeoutError: When `aquireTimeoutMs` is not `None`, and was exceeded whilst waiting for a lease
        """

    @classmethod
    async def waitForPermanentRead(cls, releaseCallback: PermanentLeaseReleaseCallback, assetOrType: Union[asset.AssetType, asset.Asset], fileName: str = "", /, *holderIdentity: Any, releaseTimeoutMs: int = 2000, aquireTimeoutMs: Optional[int] = None) -> PermanentReadAssetLease:
        leaseHolder = await cls._getLeaseHolder(assetOrType, fileName, holderIdentity)
        return await leaseHolder.aquirePermanentRead(releaseCallback, releaseTimeoutMs, aquireTimeoutMs or -1)
    

    @overload
    @classmethod
    async def waitForTransientReadWrite(cls, asset: asset.Asset, /, *, lifetimeMs: int = 2000) -> TransientReadWriteAssetLease:
        """Wait asynchronously for a lease to be granted, to read from and write to this asset on disk for the next `lifetimeMs`.
        For a read-write lease to be granted, all other leases of any kind for that asset must first be released by the AssetManager.
        FOr this reason, you cannot specify an aquire timeout for this lease type.

        :param asset: The asset to lease
        :type asset: asset.Asset
        :param lifetimeMs: The lifetime of the lease in milliseconds, defaults to 2000
        :type lifetimeMs: int, optional
        :return: A lease granting read and write access to the requested asset for the next `lifetimeMs`
        :rtype: TransientReadWriteAssetLease
        """

    @overload
    @classmethod
    async def waitForTransientReadWrite(cls, assetType: asset.AssetType, fileName: str, /, *holderIdentity: Any, lifetimeMs: int = 2000) -> TransientReadWriteAssetLease:
        """Wait asynchronously for a lease to be granted, to read from and write to this asset on disk for the next `lifetimeMs`.
        For a read-write lease to be granted, all other leases of any kind for that asset must first be released by the AssetManager.
        FOr this reason, you cannot specify an aquire timeout for this lease type.

        :param assetType: The type of asset to lease
        :type asset: asset.AssetType
        :param str fileName: The name of the file on disk to lease. Only the file name, not the path
        :param Any holderIdentity: Identifiers for the holder of the asset. These are used when building the file path
        :param lifetimeMs: The lifetime of the lease in milliseconds, defaults to 2000
        :type lifetimeMs: int, optional
        :return: A lease granting read and write access to the requested asset for the next `lifetimeMs`
        :rtype: TransientReadWriteAssetLease
        """

    @classmethod
    async def waitForTransientReadWrite(cls, assetOrType: Union[asset.AssetType, asset.Asset], fileName: str = "", /, *holderIdentity: Any, lifetimeMs: int = 2000) -> TransientReadWriteAssetLease:
        leaseHolder = await cls._getLeaseHolder(assetOrType, fileName, holderIdentity)
        return await leaseHolder.aquireTransientReadWrite(lifetimeMs)
    