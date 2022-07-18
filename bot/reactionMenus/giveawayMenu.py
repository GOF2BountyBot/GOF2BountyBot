from datetime import timedelta
from typing import Optional, Set, List
from discord import Member, Message, Colour, Role
from . import reactionMenu, expiryFunctions
from ..gameObjects.items import gameItem
from .. import botState
from ..users import basedUser
from ..scheduling import timedTask
from ..gameObjects.guildShop import StoredItemType


class GiveawayMenu(reactionMenu.ReactionMenu["GiveawayMenuOption"]):
    def __init__(self, msg: Message, items: List[StoredItemType], activeTime: timedelta, titleTxt: str = "", desc: str = "", col: Colour = Colour.blue(), img: str = "", thumb: str = "", icon: str = "", authorName: str = "", targetMember: Optional[Member] = None, targetRole: Optional[Role] = None):
        options = {i.emoji: GiveawayMenuOption(self, i) for i in items}
        timeout = timedTask.TimedTask(expiryDelta=activeTime, expiryFunction=expiryFunctions.markExpiredMenu, expiryFunctionArgs=msg.id, rescheduleOnExpiryFuncFailure=True)
        botState.client.taskScheduler.scheduleTask(timeout)
        super().__init__(msg, options=options, titleTxt=titleTxt, desc=desc, col=col, timeout=timeout, img=img, thumb=thumb, icon=icon, authorName=authorName, targetMember=targetMember, targetRole=targetRole)
        self.givenUsers: Set[Member] = set()
        self.originalDesc = desc


    def hasGivenToUser(self, user: Member) -> bool:
        return user in self.givenUsers


    async def addGivenUser(self, user: Member):
        self.givenUsers.add(user)
        self.desc = f"{self.originalDesc}\n\nNumber of users given to: {len(self.givenUsers)}"
        await self.updateMessage(noRefreshOptions=True)


    @classmethod
    def deserialize(cls, data: dict, **kwargs):
        raise NotImplementedError()


    def serialize(self, **kwargs) -> dict:
        raise NotImplementedError()


class GiveawayMenuOption(reactionMenu.NonSaveableReactionMenuOption):
    def __init__(self, menu: GiveawayMenu, item: StoredItemType):
        super().__init__(item.name, item.emoji, addFunc=self.award)
        self.item = item
        self.menu = menu


    async def award(self, reactingUser: Member):
        if not self.menu.hasGivenToUser(reactingUser):
            bUser: basedUser.BasedUser = botState.client.usersDB.getOrAddID(reactingUser.id)
            # de-serializing and re-serializing here in order to get a copy (if appropriate)
            itemCopy = type(self.item).deserialize(self.item.serialize(saveType=True))
            # itemCopy is StoredItemType here. getInventoryForItem is guaranteed to return the inventory that stores a StoredItemType.
            # Therefore, itemCopy is guaranteed to be compatible with the inventory's addItem method.
            bUser.getInventoryForItem(self.item).addItem(itemCopy) # type: ignore[reportGeneralTypeIssues]
            await self.menu.addGivenUser(reactingUser)
