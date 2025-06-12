from bot.gameObjects.items.ships.shipBase import ShipBase
from bot.baseClasses.embedFillable import removeEmbedField

# Remove the tech level field. Ships don't have tech levels in GOF2, so this could be misleading.
@removeEmbedField("Tech Level")
class ShipBlueprint(ShipBase):
    """The abstract concept of a ship, outside of player ownership.
    Could also be seen as a representation of the data required to create a ship.
    """
    pass
