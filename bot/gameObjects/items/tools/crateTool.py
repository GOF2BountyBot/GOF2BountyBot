from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ....users import basedUser
import random
from typing import Dict, Generic, List, Optional, Type, TypeVar
from . import toolItem
from .... import lib, botState
from ....lib import gameMaths
from discord import Message
from ....cfg import cfg, bbData
from .. import gameItem
from ....reactionMenus.confirmationReactionMenu import InlineConfirmationMenu
from ....users.basedUser import BasedUser
from . import shipSkinTool
from ....baseClasses.hasRarity import HasRarity


singleTypeCrates: Dict[Type[gameItem.GameItem], Type["CrateTool"]] = {}

def singleTypeCrate(itemType: Type[gameItem.GameItem]):
    """Registers this CrateTool type as restricted to a single item type in its itemPool.
    This does not on its own enforce the restriction, you must do this in your constructor.
    When a vanilla CrateTool is *deserialized*, if it only contains items of type itemType, your type-restricted CrateTool
    type will be deserialized instead.
    """
    def dec_register(cls: Type["CrateTool"]):
        if itemType in singleTypeCrates:
            raise KeyError("A singleTypeCrate is already registered with this type")
        singleTypeCrates[itemType] = cls
        return cls
    return dec_register


@gameItem.spawnableItem
class CrateTool(toolItem.ToolItem):
    """A tool containing a pool of GameItems which, when used, gives the user a single random item from the pool.
    Also automatically removes itself from the user's inventory upon use.

    :var itemPool: List of potential items to win. May contain duplicates.
    :vartype itemPool: List[gameItem.GameItem]
    :var crateType: A string identifier for the type of crate, to aid in loading from file in the case of contents changes
    :vartype crateType: str
    :var typeNum: A sub-type of crateType, e.g where crateType is levelup, typeNum might be the player's new level
    :vartype typeNum: int
    :var useRarities: True if all items in itemPool have a rarityLevel. Items will then be drawn according to
                        cfg.itemRaritiesDistribution. If False, then items will be drawn uniformally.
    :vartype useRarities: bool
    """

    def __init__(self, itemPool: List[gameItem.GameItem], name : str = "", value : int = 0, wiki : str = "",
            manufacturer : str = "", icon : str = cfg.defaultCrateIcon, emoji : lib.emojis.BasedEmoji = None,
            techLevel : int = -1, builtIn : bool = False, crateType : str = "", typeNum : int = 0,
            autoUse: bool = False):
        """
        :param List[gameItem.GameItem] itemPool: List of potential items to win. May contain duplicates.
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

        if emoji is None:
            emoji = cfg.defaultEmojis.defaultCrate


        super().__init__(name, [], value=value, wiki=wiki,
            manufacturer=manufacturer, icon=icon, emoji=emoji,
            techLevel=techLevel, builtIn=builtIn, autoUse=autoUse)

        try:
            item = next(i for i in itemPool if not gameItem.isSpawnableItemInstance(i))
        except StopIteration:
            self.itemPool = itemPool
        else:
            raise RuntimeError("Attempted to create a crateTool with something other than a spawnableItem " \
                                + "in its itemPool: " + str(item))
        
        self.crateType = crateType
        self.typeNum = typeNum

        self.useRarities = False
        for index, item in enumerate(self.itemPool):
            # Make sure all items have rarity
            if not isinstance(item, HasRarity):
                self.useRarities = False
                break
            # Make sure there are at least two rarity levels
            if not self.useRarities \
                    and index != len(self.itemPool) - 1 \
                    and item.rarityLevel != self.itemPool[index + 1].rarityLevel:
                self.useRarities = True

        if self.useRarities:
            self._itemPoolByRarity = [
                [i for i in self.itemPool if i.rarityLevel == rarityLevel]
                for rarityLevel in range(len(cfg.itemRarities))
            ]
        else:
            self._itemPoolByRarity = None


    @property
    def itemPoolByRarity(self) -> List[List[gameItem.GameItem]]:
        """A read-only list, with lists containing the items in the crates item pool for each rarity level
        defined in `cfg.itemRarities`. This property is only valid when `self.useRarities` is `True`.

        :return: `self.itemPool` sorted into separate lists by their `rarityLevel`
        :rtype: gameItem.GameItem
        """
        if not self.useRarities:
            raise ValueError("itemPoolByRarity is not valid for this crate, as useRarities = False")
        return self._itemPoolByRarity


    def pickItem(self) -> gameItem.GameItem:
        """Select an item from the crate, accounting for self.useRarities

        :return: A randomly selected item from the item pool
        :rtype: gameItem.GameItem
        """
        if not self.useRarities:
            return random.choice(self.itemPool)

        rarityLevel = gameMaths.pickRandomItemRarityLevel()
        while not any(i.rarityLevel == rarityLevel for i in self.itemPool):
            rarityLevel = gameMaths.pickRandomItemRarityLevel()

        return random.choice(self.itemPoolByRarity[rarityLevel])


    async def use(self, *args, **kwargs):
        """Behaviour function which adds a random item from the pool and adds it to the owner's inventory,
        then removes the crate from their inventory. For use in a command, use userFriendlyUse

        :param BasedUser callingBUser: The user who owns the crate
        """
        if "callingBUser" not in kwargs:
            raise NameError("Required kwarg not given: callingBUser")
        if not isinstance(kwargs["callingBUser"], BasedUser):
            raise TypeError("Required kwarg is of the wrong type. Expected BasedUser or None, received " \
                            + type(kwargs["callingBUser"]).__name__)

        callingBUser = kwargs["callingBUser"]
        newItem = self.pickItem()
        callingBUser.getInventoryForItem(newItem).addItem(newItem)
        callingBUser.inactiveTools.removeItem(self)


    async def userFriendlyUse(self, message: Message, argsStr: str, *args, **kwargs) -> str:
        """A version of self.use intended to be called by users, where exceptions are never thrown in the case of
        user error, and results strings to send in response are always returned.
        First asks for user confirmation, then adds a random single item from the item pool to the user inventory,
        and finally removes the crate from the user inventory.

        :param Message message: The discord message that triggered this tool use
        :param str argsStr: Ignored
        :return: A user-friendly message summarising the result of the tool use.
        :rtype: str
        """
        if "callingBUser" not in kwargs:
            raise NameError("Required kwarg not given: callingBUser")
        if kwargs["callingBUser"] is not None and type(kwargs["callingBUser"]).__name__ != "BasedUser":
            raise TypeError("Required kwarg is of the wrong type. Expected BasedUser or None, received " \
                            + type(kwargs["callingBUser"]).__name__)

        callingBUser = kwargs["callingBUser"]
        confirmMsg = await message.reply(mention_author=False,
                                        content=f"Are you sure you want to open your '{self.name}' crate?")
        confirmation = await InlineConfirmationMenu(confirmMsg, message.author,
                                                    cfg.toolUseConfirmTimeoutSeconds).doMenu()

        if cfg.defaultEmojis.accept in confirmation:
            newItem = random.choice(self.itemPool)
            callingBUser.getInventoryForItem(newItem).addItem(newItem)
            callingBUser.inactiveTools.removeItem(self)

            return "🎉 Success! You got a " + newItem.name + "!"
        else:
            return "🛑 Crate open cancelled."


    def statsStringShort(self) -> str:
        """Summarise all the statistics and functionality of this item as a string.
        For small item pools, list all possible item names. For large item pools, give the number of possible items.

        :return: A string summarising the statistics and functionality of this item
        :rtype: str
        """
        if self.useRarities:
            itemsByRarity = '\n'.join(f"{getattr(cfg.defaultEmojis, f'rarity_{rarityName}').sendable} " \
                                    + f"{len(self.itemPoolByRarity[rarityLevel])} {rarityName.title()}" \
                                        for rarityLevel, rarityName in enumerate(cfg.itemRarities))
                                        
            return f"*{len(self.itemPool)} possible items:\n{itemsByRarity}*"

        if len(self.itemPool) > 9:
            return "*" + str(len(self.itemPool)) + " possible items*"
        else:
            return "*" + " • ".join(i.name for i in self.itemPool) + "*"


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
                                    + ", ".join(i.name for i in itemsForLevel)
                if truncateLevel:
                    itemsByRarity += f" +{len(self.itemPoolByRarity[rarityLevel]) - 5} more possible items" 
                                        
            return f"*Use to open the crate and receive one of the following:\n\n{itemsByRarity}*" 

        if len(self.itemPool) > 30:
            return "Use to open the crate and receive one of the following:\n\n" \
                + f"*{' • '.join(i.name for i in self.itemPool[:30])} +{len(self.itemPool) - 30} more possible items*"
        else:
            return "Use to open the crate and receive one of the following:\n\n" \
                + "*" + " • ".join(i.name for i in self.itemPool) + "*"


    def toDict(self, **kwargs) -> dict:
        """Serialize this crate into dictionary format.

        :return: A dictionary fully describing this crate instance
        :rtype: dict
        """
        data = super().toDict(**kwargs)
        if "aliases" in data:
            del data["aliases"]
        if self.builtIn:
            data["crateType"] = self.crateType
            data["typeNum"] = self.typeNum
        else:
            if "saveType" not in kwargs:
                kwargs["saveType"] = True

            data["itemPool"] = []
            for item in self.itemPool:
                data["itemPool"].append(item.toDict(**kwargs))
        return data


    @classmethod
    def fromDict(cls, crateDict: dict, **kwargs) -> CrateTool:
        """Deserialize a CrateTool instance from its dictionary representation.

        :param dict crateDict: A dictionary fully describing the CrateDict instance to create. Must contain itemPool.
        :return: A new CrateTool instance as described by crateDict
        :rtype: CrateTool
        """
        skipInvalidItems = kwargs.get("skipInvalidItems", False)

        if "builtIn" in crateDict and crateDict["builtIn"]:
            if "crateType" in crateDict:
                if crateDict["crateType"] in bbData.builtInCrateObjs:
                    return bbData.builtInCrateObjs[crateDict["crateType"]][crateDict["typeNum"]]
                else:
                    raise ValueError("Unknown crateType: " + str(crateDict["crateType"]))
            else:
                raise ValueError("Attempted to spawn builtIn CrateTool with no given crateType")
        else:
            crateToSpawn = crateDict

        itemPool = []
        singleType: Optional[Type[gameItem.GameItem]] = None
        allSingleType = True
        if "itemPool" in crateToSpawn:
            for itemDict in crateToSpawn["itemPool"]:
                errorStr = ""
                errorType = ""
                if "type" not in itemDict:
                    errorStr = "Invalid itemPool entry, missing type. Data: " + itemDict
                    errorType = "NO_TYPE"
                elif itemDict["type"] not in gameItem.subClassNames:
                    errorStr = "Invalid itemPool entry, attempted to add something other than a spawnableItem. " \
                                + "Has the module been imported yet? Data: " + str(itemDict)
                    errorType = "BAD_TYPE"
                if errorStr:
                    if skipInvalidItems:
                        botState.logger.log("crateTool", "fromDict", errorStr, eventType=errorType)
                    else:
                        raise ValueError(errorStr)
                else:
                    newItem = gameItem.spawnItem(itemDict)
                    itemPool.append(newItem)
                    if allSingleType:
                        if singleType is None:
                            singleType = type(newItem)
                        elif type(newItem) is not singleType:
                            singleType = None
                            allSingleType = False

        else:
            botState.logger.log("crateTool", "fromDict", "fromDict-ing a crateTool with no itemPool.")

        if allSingleType and singleType in singleTypeCrates:
            return singleTypeCrates[singleType](**cls._makeDefaults(crateDict, ("type",), itemPool=itemPool,
                                                emoji=lib.emojis.BasedEmoji.fromDict(crateDict["emoji"]) \
                                                        if "emoji" in crateDict else lib.emojis.BasedEmoji.EMPTY))

        return CrateTool(**cls._makeDefaults(crateDict, ("type", "aliases"), itemPool=itemPool,
                                            emoji=lib.emojis.BasedEmoji.fromDict(crateDict["emoji"]) \
                                                    if "emoji" in crateDict else lib.emojis.BasedEmoji.EMPTY))


@gameItem.spawnableItem
@singleTypeCrate(shipSkinTool.ShipSkinTool)
class ShipSkinCrateTool(CrateTool):
    """A crate that only contains ShipSkinTools.
    Has a custom statsStringLong.
    """
    
    def __init__(self, itemPool: List[shipSkinTool.ShipSkinTool], name : str = "", value : int = 0, wiki : str = "",
            manufacturer : str = "", icon : str = cfg.defaultCrateIcon, emoji : lib.emojis.BasedEmoji = None,
            techLevel : int = -1, builtIn : bool = False, crateType : str = "", typeNum : int = 0,
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
        super().__init__(itemPool, name=name, value=value, wiki=wiki,
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
                                        
            return f"*Use to open the crate and receive one of the following:\n\n{itemsByRarity}*" 

        if len(self.itemPool) > 30:
            return "Use to open the crate and receive one of the following ship skins:\n\n" \
                + f"*{' • '.join(i.skin.name for i in self.itemPool[:30])} +{len(self.itemPool) - 30} more possible skins*"
        else:
            return "Use to open the crate and receive one of the following ship skins:\n\n" \
                + "*" + " • ".join(i.skin.name for i in self.itemPool) + "*"

