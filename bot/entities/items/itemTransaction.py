from enum import Enum
from types import TracebackType
from typing import Any, Awaitable, List, Optional, Type, TypeVar, Union, Generic, Protocol, runtime_checkable

from contextlib import AbstractAsyncContextManager

from ..inventories.inventoryBase import InventoryBase
from .itemBase import ItemBase
from ...database.constants import StoreableItemType

@runtime_checkable
class SupportsTrading(Protocol):
    @property
    def credits(self) -> int: ...

    @credits.setter
    def credits(self, value: int) -> None: ...

    def getInventory(self, itemType: StoreableItemType) -> InventoryBase: ...


class SupportsItems(Protocol):
    def getInventory(self, itemType: StoreableItemType) -> InventoryBase: ...


TStoredItem = TypeVar("TStoredItem", bound=ItemBase)
TBuyer = TypeVar("TBuyer", bound=Union[SupportsTrading, SupportsItems])
TSeller = TypeVar("TSeller", bound=Union[SupportsTrading, SupportsItems])


class ItemBuyStepCallback(Protocol, Generic[TStoredItem, TBuyer, TSeller]):
    def __call__(self, transaction: "ItemTransactionContext[TStoredItem, TBuyer, TSeller]") -> Any: ...


class ItemBuyStep(Generic[TStoredItem, TBuyer, TSeller]):
    def __init__(self, exec: ItemBuyStepCallback[TStoredItem, TBuyer, TSeller], rollback: Optional[ItemBuyStepCallback[TStoredItem, TBuyer, TSeller]]) -> None:
        self.exec = exec
        self.rollback = rollback
        self.executed = False


class ItemRollbackStep(Generic[TStoredItem, TBuyer, TSeller]):
    def __init__(self, rollback: ItemBuyStepCallback[TStoredItem, TBuyer, TSeller]) -> None:
        self.rollback = rollback


class ItemTransactionState(Enum):
    Active = 0
    Succeeded = 1
    Failed = 2
    Cancelled = 3


class ItemTransactionContext(AbstractAsyncContextManager, Generic[TStoredItem, TBuyer, TSeller]):
    """TODO: This class is slated for design reconsideration. Why write our own class when we can just use a SQL transaction? The current issue is that opening a transaction on the AsyncSession raises a 'transaction already open' error.
    TODO: Redesign as a database persisted storage entity, with source and target IDs and discriminators, and committed source and target credits/lists of items. Committed: They must be removed from the source in order for the transaction to be created. This design will allow for later reuse in trade requests, and potentially in marketplace seller boxes
    
    Represents an item-buying transaction between a buyer and a seller.
    If an exception occurs or the transaction is cancelled, then the buyer is not charged.

    The buyer/seller may not necessarily have a credits balance, but both must have item inventories.
    This class will likely later be generalized further into a database-persisted entity covering the full spectrum of item-item/credit-item/item-credit trades.
    
    Pseudocode-esque example:
    ```py
    async with buyer.buyItem() as transaction:
        if input("complete transaction?") == "yes":
            seller.getInventory().addItem(transaction.item)
        else:
            transaction.cancel()
    ```

    The context supports executing independent steps as callbacks:
    - Before the buy begins (at `async with` enter)
    - After the buy succeeds (at `async with` exit)
    - After the buy fails (at exception time, or at `async with` exit when cancelled)

    Steps are executed in the order that they are registered, but they are treated as independant.
    
    ```py
    def preBuy(transaction):
        print("user is about to buy an item")
        transaction.seller.itemsBought += 1

    def preBuyRollback(transaction):
        print("prebuy step rolled back")
        transaction.seller.itemsBought -= 1
        
    def failedStep(transaction):
        print("User bought an item")
        raise ValueError()

    def rollback(transaction):
        print("The transaction was rolled back")

    transaction = ItemTransactionContext(buyer, seller, item)
    transaction.addPreBuyStep(preBuy, preBuyRollback)
               .addPostBuyStep(failedStep, None)
               .addRollbackStep(rollback)

    async with buyer.buyItem() as transaction:
        pass
    ```
    Would print:
    ```py
    user is about to buy an item
    user bought an item
    prebuy step rolled back
    the transaction was rolled back
    ```

    """
    def __init__(self, buyer: TBuyer, seller: TSeller, item: TStoredItem, chargeBuyer: bool = True, pricePerItem: Optional[int] = None, quantity: int = 1) -> None:
        """:param TBuyer buyer: The entity buying the item
        :param TSeller seller: The entity selling the item
        :param TStoredItem item: The item being bought
        :param Optional[bool] chargeBuyer: Adds a rollback-able post-buy step that subtracts the transaction value from the buyer's credits (if supported), and adds it to the seller's credits (if supported). defaults to True
        :param Optional[int] pricePerItem: The credits price per item, defaults to `item.getValue()`
        :param Optional[int] quantity: The quantity being traded, defaults to 1
        """
        self.buyer = buyer
        self.seller = seller
        self.item = item
        self.pricePerItem = pricePerItem
        self.quantity = quantity

        self.state = ItemTransactionState.Active
        self.preSteps: List[ItemBuyStep[TStoredItem, TBuyer, TSeller]] = []
        self.postSteps: List[ItemBuyStep[TStoredItem, TBuyer, TSeller]] = []
        self.rollbackSteps: List[ItemRollbackStep[TStoredItem, TBuyer, TSeller]] = []

        if chargeBuyer:
            async def _exec(transaction):
                value = await self.value()
                if isinstance(self.buyer, SupportsTrading):
                    self.buyer.credits -= value
                if isinstance(self.seller, SupportsTrading):
                    self.seller.credits += value

            async def _rollback(transaction):
                value = await self.value()
                if isinstance(self.buyer, SupportsTrading):
                    self.buyer.credits += value
                if isinstance(self.seller, SupportsTrading):
                    self.seller.credits -= value

            self.addPostBuyStep(_exec, _rollback)

        super().__init__()


    async def value(self):
        """The value of the items being bought.
        This is equivalent to the item price override provided in the constructor, multiplied by the quantity.
        If no override was provided, then it is equivalent to the item value, multiplied by quantity.

        :return: The total value of the item(s) being bought
        :rtype: int
        """
        if self.pricePerItem is None:
            return (await self.item.getValue()) * self.quantity
        return self.pricePerItem * self.quantity


    def addPreBuyStep(self, exec: ItemBuyStepCallback[TStoredItem, TBuyer, TSeller], rollback: Optional[ItemBuyStepCallback[TStoredItem, TBuyer, TSeller]]):
        """Add a step to execute when the transaction begins.
        This is triggered at the point of `async with` enter.
        The rollback step is optional, and will be triggered if an exception occurs, or if the transaction is cancelled.

        :param exec: Callback to execute the pre-buy step
        :type exec: ItemBuyStepCallback[TStoredItem, TBuyer, TSeller]
        :param rollback: Callback to roll back the step
        :type rollback: Optional[ItemBuyStepCallback[TStoredItem, TBuyer, TSeller]]
        :return: Self for chaining
        :rtype: ItemTransactionContext
        """
        self.preSteps.append(ItemBuyStep(exec, rollback))
        return self

    
    def addPostBuyStep(self, exec: ItemBuyStepCallback[TStoredItem, TBuyer, TSeller], rollback: Optional[ItemBuyStepCallback[TStoredItem, TBuyer, TSeller]]):
        """Add a step to execute when the transaction succeeds.
        This is triggered at the point of `async with` exit.
        The rollback step is optional, and will be triggered if an exception occurs in a later post-buy step.

        :param exec: Callback to execute the post-buy step
        :type exec: ItemBuyStepCallback[TStoredItem, TBuyer, TSeller]
        :param rollback: Callback to roll back the step
        :type rollback: Optional[ItemBuyStepCallback[TStoredItem, TBuyer, TSeller]]
        :return: Self for chaining
        :rtype: ItemTransactionContext
        """
        self.postSteps.append(ItemBuyStep(exec, rollback))
        return self


    def addRollbackStep(self, rollback: ItemBuyStepCallback[TStoredItem, TBuyer, TSeller]):
        """Add a rollback step to execute when the transaction is rolled back.
        This is triggered when an exception occurs, or the transaction is cancelled.

        :param rollback: Callback to execute on rollback
        :type rollback: ItemBuyStepCallback[TStoredItem, TBuyer, TSeller]
        :return: Self for chaining
        :rtype: ItemTransactionContext
        """
        self.rollbackSteps.append(ItemRollbackStep(rollback))
        return self


    def cancel(self):
        """Cancel this transaction.
        This will trigger rollback steps once the context is exited (the end of your `async with`)
        """
        self.state = ItemTransactionState.Cancelled


    async def _executePreBuySteps(self):
        for step in self.preSteps:
            result = step.exec(self)
            if isinstance(result, Awaitable):
                await result

    
    async def _executePostBuySteps(self):
        for step in self.postSteps:
            result = step.exec(self)
            if isinstance(result, Awaitable):
                await result


    async def _executeRollbackSteps(self, cancelled: bool):
        for step in self.preSteps:
            if not step.executed or step.rollback is None: continue
            result = step.rollback(self)
            if isinstance(result, Awaitable):
                await result

        if not cancelled:
            for step in self.postSteps:
                if not step.executed or step.rollback is None: continue
                result = step.rollback(self)
                if isinstance(result, Awaitable):
                    await result
        
        for step in self.rollbackSteps:
            result = step.rollback(self)
            if isinstance(result, Awaitable):
                await result


    async def __aenter__(self) -> Any:
        await self._executePreBuySteps()
    

    async def __aexit__(self, __exc_type: Optional[Type[BaseException]], __exc_value: Optional[BaseException], __traceback: Optional[TracebackType]) -> Optional[bool]:
        if __exc_type is not None or __exc_value is not None:
            self.state = ItemTransactionState.Failed
            await self._executeRollbackSteps(False)
            return

        if self.state is ItemTransactionState.Cancelled:
            await self._executeRollbackSteps(True)
            return

        try:
            await self._executePostBuySteps()
        except:
            self.state = ItemTransactionState.Failed
            await self._executeRollbackSteps(False)
            raise
        else:
            self.state = ItemTransactionState.Succeeded