import random
from . import toolItem
from .... import lib
from discord import Message
from ....cfg import cfg
from .. import gameItem
from ....botState import logger
from ....reactionMenus.confirmationReactionMenu import InlineConfirmationMenu


@gameItem.spawnableItem
class CrateTool(toolItem.ToolItem):
    def __init__(self, itemPool, name : str = "", value : int = 0, wiki : str = "",
            manufacturer : str = "", icon : str = "", emoji : lib.emojis.BasedEmoji = lib.emojis.BasedEmoji.EMPTY,
            techLevel : int = -1, builtIn : bool = False):

        super().__init__(name, [], value=value, wiki=wiki,
            manufacturer=manufacturer, icon=icon, emoji=emoji,
            techLevel=techLevel, builtIn=builtIn)

        for item in itemPool:
            if not gameItem.isSpawnableItemInstance(item):
                raise RuntimeError("Attempted to create a crateTool with something other than a spawnableItem " \
                                    + "in its itemPool.")
        self.itemPool = itemPool


    async def use(self, *args, **kwargs):
        """This item's behaviour function. Intended to be very generic at this level of implementation.
        """
        if "callingBUser" not in kwargs:
            raise NameError("Required kwarg not given: callingBUser")
        if kwargs["callingBUser"] is not None and type(kwargs["callingBUser"]).__name__ != "BasedUser":
            raise TypeError("Required kwarg is of the wrong type. Expected BasedUser or None, received " \
                            + type(kwargs["callingBUser"]).__name__)

        callingBUser = kwargs["callingBUser"]
        newItem = random.choice(self.itemPool)
        callingBUser.getInventoryForItem(newItem).addItem(newItem)
        callingBUser.inactiveTools.removeItem(self)


    async def userFriendlyUse(self, message : Message, *args, **kwargs) -> str:
        """A version of self.use intended to be called by users, where exceptions are never thrown in the case of
        user error, and results strings are always returned.

        :param Message message: The discord message that triggered this tool use
        :return: A user-friendly messge summarising the result of the tool use.
        :rtype: str
        """
        if "callingBUser" not in kwargs:
            raise NameError("Required kwarg not given: callingBUser")
        if kwargs["callingBUser"] is not None and type(kwargs["callingBUser"]).__name__ != "BasedUser":
            raise TypeError("Required kwarg is of the wrong type. Expected BasedUser or None, received " \
                            + type(kwargs["callingBUser"]).__name__)

        callingBUser = kwargs["callingBUser"]
        confirmMsg = await message.channel.send("Are you sure you want to open this crate?")
        confirmation = await InlineConfirmationMenu(confirmMsg, message.author,
                                                    cfg.toolUseConfirmTimeoutSeconds).doMenu()

        if cfg.defaultEmojis.reject in confirmation:
            return "🛑 Crate open cancelled."
        elif cfg.defaultEmojis.accept in confirmation:
            newItem = random.choice(self.itemPool)
            callingBUser.getInventoryForItem(newItem).addItem(newItem)
            callingBUser.inactiveTools.removeItem(self)

            return "🎉 Success! You got a " + newItem.name + "!"


    def statsStringShort(self) -> str:
        """Summarise all the statistics and functionality of this item as a string.

        :return: A string summarising the statistics and functionality of this item
        :rtype: str
        """
        return "*" + str(len(self.itemPool)) + " possible items*"


    def toDict(self, **kwargs) -> dict:
        """Serialize this tool into dictionary format.
        This step of implementation adds a 'type' string indicating the name of this tool's subclass.

        :return: The default gameItem toDict implementation, with an added 'type' field
        :rtype: dict
        """
        data = super().toDict(**kwargs)
        if "saveType" not in kwargs:
            kwargs["saveType"] = True

        data["itemPool"] = []
        for item in self.itemPool:
            data["itemPool"].append(item.toDict(**kwargs))
        return data


    @classmethod
    def fromDict(cls, crateDict, **kwargs):
        skipInvalidItems = kwargs["skipInvalidItems"] if "skipInvalidItems" in kwargs else False

        itemPool = []
        if "itemPool" in crateDict:
            for itemDict in crateDict["itemPool"]:
                errorStr = ""
                errorType = ""
                if "type" not in itemDict:
                    errorStr = "Invalid itemPool entry, missing type. Data: " + itemDict
                    errorType = "NO_TYPE"
                elif itemDict["type"] not in gameItem.subClassNames:
                    errorStr = "Invalid itemPool entry, attempted to add something other than a spawnableItem. Data: " \
                                + str(itemDict)
                    errorType = "BAD_TYPE"
                if errorStr:
                    if skipInvalidItems:
                        logger.log("crateTool", "fromDict", errorStr, eventType=errorType)
                    else:
                        raise ValueError(errorStr)
                else:
                    itemPool.append(gameItem.spawnItem(itemDict))
        else:
            logger.log("crateTool", "fromDict", "fromDict-ing a crateTool with no itemPool.")

        return CrateTool(itemPool, name=crateDict["name"] if "name" in crateDict else "",
            value=crateDict["value"] if "value" in crateDict else 0,
            wiki=crateDict["wiki"] if "wiki" in crateDict else "",
            manufacturer=crateDict["manufacturer"] if "manufacturer" in crateDict else "",
            icon=crateDict["icon"] if "icon" in crateDict else "",
            emoji=lib.emojis.BasedEmoji.fromDict(crateDict["emoji"]) if "emoji" in crateDict else lib.emojis.BasedEmoji.EMPTY,
            techLevel=crateDict["techLevel"] if "techLevel" in crateDict else -1,
            builtIn=crateDict["builtIn"] if "builtIn" in crateDict else False)
