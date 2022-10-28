from __future__ import annotations
from typing import Union, cast
import random
from typing import Dict, Generic, List, Optional, Type, TypeVar
from discord import Interaction

from . import toolItem
from .... import lib, botState
from ....lib import gameMaths
from ....lib.discordUtil import interactionSend
from ....cfg import cfg, bbData
from .. import gameItem
from ....users import basedUser
from ....baseClasses.hasRarity import HasRarityMixin
from ....baseClasses.serializable import SerializesToSchema
from ....baseClasses.embedFillable import EmbedFillableMixin, embedField
from .... import client
from ....views.confirmView import ConfirmView

class BuiltInSerializedCrateTool(gameItem.BuiltInSerializedGameItem):
    crateType: str
    typeNum: int

TSerializedItem = TypeVar("TSerializedItem", bound=gameItem.TypedSerializedGameItemUnion)

class CustomSerializedCrateTool(toolItem.SerializedToolItem, BuiltInSerializedCrateTool, Generic[TSerializedItem]):
    itemPool: List[TSerializedItem]

class TypedSerializedCrateTool(CustomSerializedCrateTool[TSerializedItem], toolItem.TypedSerializedToolItem, Generic[TSerializedItem]): pass

SerializedCrateToolUnion = Union[CustomSerializedCrateTool[TSerializedItem], TypedSerializedCrateTool[TSerializedItem], BuiltInSerializedCrateTool]


singleTypeCrates: Dict[Type[gameItem.GameItem], Type["CrateTool"]] = {}

TCrateType = TypeVar("TCrateType", bound=Type["CrateTool"]) 

def singleTypeCrate(itemType: Type[gameItem.GameItem]):
    """Registers this CrateTool type as restricted to a single item type in its itemPool.
    This does not on its own enforce the restriction, you must do this in your constructor.
    When a vanilla CrateTool is *deserialized*, if it only contains items of type itemType, your type-restricted CrateTool
    type will be deserialized instead.
    """
    def dec_register(cls : TCrateType) -> TCrateType:
        if itemType in singleTypeCrates:
            raise KeyError("A singleTypeCrate is already registered with this type")
        singleTypeCrates[itemType] = cls
        return cls
    return dec_register


TItemType = TypeVar("TItemType", bound=gameItem.GameItem)

@gameItem.spawnableItem
class CrateTool(toolItem.ToolItem, Generic[TItemType, TSerializedItem], SerializesToSchema[Union[CustomSerializedCrateTool[TSerializedItem], TypedSerializedCrateTool[TSerializedItem], BuiltInSerializedCrateTool]]):
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

    def __init__(self, itemPool: List[TItemType], name: str = "", value: int = 0, wiki: str = "",
            manufacturer: str = "", icon: str = cfg.defaultCrateIcon, emoji: Optional[lib.emojis.BasedEmoji] = None,
            techLevel: int = -1, builtIn: bool = False, crateType: str = "", typeNum: int = 0,
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
            if not isinstance(item, HasRarityMixin):
                self.useRarities = False
                break
            # Make sure there are at least two rarity levels
            # Ignoring a warning here because all items are guaranteed to have a rarity if useRarities is True due to the above check
            if not self.useRarities \
                    and index != len(self.itemPool) - 1 \
                    and item.rarityLevel != self.itemPool[index + 1].rarityLevel: # type: ignore[reportGeneralTypeIssues]
                self.useRarities = True

        if self.useRarities:
            self._itemPoolByRarity = [
                # Ignoring a warning here because all items are guaranteed to have a rarity if useRarities is True due to the above check
                [i for i in self.itemPool if i.rarityLevel == rarityLevel] # type: ignore[reportGeneralTypeIssues]
                for rarityLevel in range(len(cfg.itemRarities))
            ]
        else:
            self._itemPoolByRarity = None


    @property
    def itemPoolByRarity(self) -> List[List[TItemType]]:
        """A read-only list, with lists containing the items in the crates item pool for each rarity level
        defined in `cfg.itemRarities`. This property is only valid when `self.useRarities` is `True`.

        :return: `self.itemPool` sorted into separate lists by their `rarityLevel`
        :rtype: gameItem.GameItem
        """
        if not self.useRarities:
            raise ValueError("itemPoolByRarity is not valid for this crate, as useRarities = False")
        return cast(List[List[TItemType]], self._itemPoolByRarity)


    def pickItem(self) -> TItemType:
        """Select an item from the crate, accounting for self.useRarities

        :return: A randomly selected item from the item pool
        :rtype: gameItem.GameItem
        """
        if not self.useRarities:
            return random.choice(self.itemPool)

        rarityLevel = gameMaths.pickRandomItemRarityLevel()
        # Ignoring a warning here because all items are guaranteed to have a rarity if useRarities is True
        while not any(i.rarityLevel == rarityLevel for i in self.itemPool): # type: ignore[reportGeneralTypeIssues]
            rarityLevel = gameMaths.pickRandomItemRarityLevel()

        return random.choice(self.itemPoolByRarity[rarityLevel])


    @toolItem.singleUse
    async def use(self, *, callingBUser: "basedUser.BasedUser", **_) -> bool:
        """Behaviour function which adds a random item from the pool and adds it to the owner's inventory,
        then removes the crate from their inventory. For use in a command, use userFriendlyUse

        :param BasedUser callingBUser: The user who owns the crate
        :returns: Whether or not the use was successful
        :rtype: bool
        """
        if not isinstance(callingBUser, basedUser.BasedUser):
            raise TypeError("Required kwarg is of the wrong type. Expected BasedUser, received " \
                            + type(callingBUser).__name__)

        newItem = self.pickItem()
        # Ignoring a warning here because pyright is complaining about potentially adding a GameItem to a UserToolInventory
        # But this can only happen if newItem is in fact a tool, due to the getInventoryForItem check
        callingBUser.getInventoryForItem(newItem).addItem(newItem) # type: ignore[reportGeneralTypeIssues]
        return True


    @toolItem.userFriendlySingleUse
    async def userFriendlyUse(self, interaction: Interaction, respond: bool, followup: bool, *args, **kwargs) -> bool:
        """A version of self.use intended to be called by users, where exceptions are never thrown in the case of
        user error, and results strings to send in response are always returned.
        First asks for user confirmation, then adds a random single item from the item pool to the user inventory,
        and finally removes the crate from the user inventory.

        :param interaction Interaction: The discord interaction that triggered this tool use
        :returns: Whether or not the use was successful
        :rtype: bool
        """
        callingBUser = client.onboardInteractionBasedUser(interaction)

        view = ConfirmView(timeout=60, clearView=True, respond=False)

        await interactionSend(interaction, respond, followup,
                                f"Are you sure you want to open your '{self.name}' crate? Respond within 60s.",
                                ephemeral=True, view=view)

        if await view.wait():
            await view.interaction.response.send_message("🛑 Crate open cancelled - out of time!", ephemeral=True)
        elif not view.confirmed:
            await view.interaction.response.send_message("🛑 Crate open cancelled.", ephemeral=True)
        else:
            newItem = self.pickItem()
            callingBUser.getInventoryForItem(newItem).addItem(newItem)

            await view.interaction.response.send_message(f"🎉 Success! You got a {newItem.name}!")
            return True

        return False


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


    @embedField("Item Pool")
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
                                        
            return f"*Use to open the crate and receive one of the following:\n{itemsByRarity}*" 

        if len(self.itemPool) > 30:
            return "Use to open the crate and receive one of the following:\n\n" \
                + f"*{' • '.join(i.name for i in self.itemPool[:30])} +{len(self.itemPool) - 30} more possible items*"
        else:
            return "Use to open the crate and receive one of the following:\n\n" \
                + "*" + " • ".join(i.name for i in self.itemPool) + "*"


    def serialize(self, **kwargs) -> Union[CustomSerializedCrateTool[TSerializedItem], TypedSerializedCrateTool[TSerializedItem], BuiltInSerializedCrateTool]:
        """Serialize this crate into dictionary format.

        :return: A dictionary fully describing this crate instance
        :rtype: dict
        """
        data = super().serialize(**kwargs)
        if "aliases" in data:
            del data["aliases"]
        if self.builtIn:
            # Casting here because I know that the crate is builtIn
            data = cast(BuiltInSerializedCrateTool, data)
            data["crateType"] = self.crateType
            data["typeNum"] = self.typeNum
        else:
            # Casting here because I know that the crate is not builtIn, so it will have all fields
            data = cast(CustomSerializedCrateTool[TSerializedItem], data)
            if "saveType" not in kwargs:
                kwargs["saveType"] = True

            data["itemPool"] = []
            for item in self.itemPool:
                # Casting with the assumption that TSerializedItem is the serialized for of TSerialized
                data["itemPool"].append(cast(TSerializedItem, item.serialize(**kwargs)))
        return data


    @classmethod
    def crateTypeExists(cls, crateType: str) -> bool:
        """Decide whether a crateType exists.
        """
        return crateType in bbData.builtInCrateObjs


    @classmethod
    def crateTypeNumExists(cls, crateType: str, typeNum: int) -> bool:
        """Decide whether a typeNum exists for a given crateType.
        crateType must exist (see `crateTypeExists`)
        """
        return typeNum >= 0 and typeNum < len(bbData.builtInCrateObjs[crateType])


    @classmethod
    def deserialize(cls, crateDict: dict, **kwargs) -> CrateTool:
        """Deserialize a CrateTool instance from its dictionary representation.

        :param dict crateDict: A dictionary fully describing the CrateDict instance to create. Must contain itemPool.
        :return: A new CrateTool instance as described by crateDict
        :rtype: CrateTool
        """
        skipInvalidItems = kwargs.get("skipInvalidItems", False)

        if "builtIn" in crateDict and crateDict["builtIn"]:
            if "crateType" in crateDict:
                if cls.crateTypeExists(crateDict["crateType"]):
                    if cls.crateTypeNumExists(crateDict["crateType"], crateDict["typeNum"]):
                        return bbData.builtInCrateObjs[crateDict["crateType"]][crateDict["typeNum"]]
                    raise KeyError(f"typeNum {crateDict['typeNum']} does not exist for crateType {crateDict['crateType']}")
                raise KeyError("Unknown crateType: " + str(crateDict["crateType"]))
            raise ValueError("Attempted to spawn builtIn CrateTool with no given crateType")

        itemPool = []
        singleType: Optional[Type[gameItem.GameItem]] = None
        allSingleType = True
        if "itemPool" in crateDict:
            for itemDict in crateDict["itemPool"]:
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
                        botState.client.logger.log("crateTool", "deserialize", errorStr, eventType=errorType)
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
            botState.client.logger.log("crateTool", "deserialize", "deserialize-ing a crateTool with no itemPool.")

        if allSingleType and singleType in singleTypeCrates:
            return singleTypeCrates[singleType](**cls._makeDefaults(crateDict, ("type",), itemPool=itemPool,
                                                emoji=lib.emojis.BasedEmoji.deserialize(crateDict["emoji"]) \
                                                        if "emoji" in crateDict else lib.emojis.BasedEmoji.EMPTY))

        return CrateTool(**cls._makeDefaults(crateDict, ("type", "aliases"), itemPool=itemPool,
                                            emoji=lib.emojis.BasedEmoji.deserialize(crateDict["emoji"]) \
                                                    if "emoji" in crateDict else lib.emojis.BasedEmoji.EMPTY))
