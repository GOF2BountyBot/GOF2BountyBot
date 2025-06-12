from typing import Union, List, Optional

from bot.gameObjects.items import gameItem
from bot.gameObjects.items.tools import crateTool
from bot.gameObjects.items.tools import shipSkinTool
from bot.cfg import cfg
from bot import lib

@gameItem.spawnableItem
@crateTool.singleTypeCrate(shipSkinTool.ShipSkinTool)
class ShipSkinCrateTool(crateTool.CrateTool[shipSkinTool.ShipSkinTool, Union[shipSkinTool.TypedBuiltInSerializedShipSkinTool, shipSkinTool.TypedCustomInSerializedShipSkinTool]]):
    """A crate that only contains ShipSkinTools.
    Has a custom statsStringLong.
    """
    
    def __init__(self, itemPool: List[shipSkinTool.ShipSkinTool], name: str = "", value: int = 0, wiki: str = "",
            manufacturer: str = "", icon: str = cfg.defaultCrateIcon, emoji: Optional[lib.emojis.BasedEmoji] = None,
            techLevel: int = -1, builtIn: bool = False, crateType: str = "", typeNum: int = 0,
            autoUse: bool = False):
        """
        :param List[shipSkinTool.ShipSkinTool] itemPool: List of potential items to win. May contain duplicates.
        :param str name: The name of the crate. Must be unique.
        :param int value: The number of credits that this item can be bought/sold for at a shop. (Default 0)
        :param str wiki: A web page that is displayed as the wiki page for this item. (Default "")
        :param str manufacturer: The name of the manufacturer of this item (Default "")
        :param str icon: A URL pointing to an image to use for this item's icon (Default "")
        :param lib.emojis.BasedEmoji emoji: The emoji to use for this item's small icon (Default lib.emojis.BasedEmoji.EMPTY)
        :param int techLevel: A rating from 1 to 10 of this item's technical advancement, generally for crates this isn't
                                limited, e.g a measure of the rarity of the items, or of the items' TLs maybe (Default -1)
        :param bool builtIn: Whether this is a BountyBot standard crate (loaded in from JSON) or a custom spawned
                                item (Default False)
        :param str crateType: A string identifier for the type of crate, to aid in loading from file in the case of contents
                                changes (Default "")
        :param int typeNum: A sub-type of crateType, e.g where crateType is levelup, typeNum might be the player's new level
                                (Default 0)
        """
        if any(not isinstance(i, shipSkinTool.ShipSkinTool) for i in itemPool):
            raise TypeError(f"all items in itemPool must be of type {shipSkinTool.ShipSkinTool.__name__}")
        
        # ignoring a warning here - pyright thinks ShipSkinTool is not a GameItem, but ShipSkinTool extends ToolItem, which extends GameItem
        super().__init__(itemPool, name=name, value=value, wiki=wiki, # type: ignore[reportGeneralTypeIssues]
            manufacturer=manufacturer, icon=icon, emoji=emoji,
            techLevel=techLevel, builtIn=builtIn, crateType=crateType, typeNum=typeNum, autoUse=autoUse)


    def statsStringLong(self) -> str:
        if self.useRarities:
            largePool = len(self.itemPool) > 30
            itemsByRarity = ""
            for rarityLevel, rarityName in enumerate(cfg.itemRarities):
                itemsForLevel = self.itemPoolByRarity[rarityLevel]
                numItemsInLevel = len(itemsForLevel)
                if numItemsInLevel == 0:
                    continue

                truncateLevel = False
                if largePool and numItemsInLevel > 5:
                    truncateLevel = True
                    itemsForLevel = self.itemPoolByRarity[rarityLevel][:5]

                itemsByRarity += f"\n{getattr(cfg.defaultEmojis, f'rarity_{rarityName}').sendable} " \
                                    + f"{rarityName.title()}: " \
                                    + ", ".join(i.skin.name for i in itemsForLevel)
                if truncateLevel:
                    itemsByRarity += f" +{len(self.itemPoolByRarity[rarityLevel]) - 5} more possible skins" 
                                        
            return f"*Use to open the crate and receive one of the following ship skins:\n{itemsByRarity}*" 

        if len(self.itemPool) > 30:
            return "Use to open the crate and receive one of the following ship skins:\n\n" \
                + f"*{' • '.join(i.skin.name for i in self.itemPool[:30])} +{len(self.itemPool) - 30} more possible skins*"
        else:
            return "Use to open the crate and receive one of the following ship skins:\n\n" \
                + "*" + " • ".join(i.skin.name for i in self.itemPool) + "*"