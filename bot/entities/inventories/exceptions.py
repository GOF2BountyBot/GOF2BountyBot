class NotStored(BaseException):
    """Thrown when attempting to find a quantity of an item in an inventory, but not enough is found.
    """

    def __init__(self, inventoryId: int, itemId: int, requestedQuantity: int, foundQuantity: int, *args: object) -> None:
        self.inventoryId = inventoryId
        self.itemId = itemId
        self.requestedQuantity = requestedQuantity
        self.foundQuantity = foundQuantity
        super().__init__(*args)