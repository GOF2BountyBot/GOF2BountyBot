from datetime import timedelta
from typing import Set, List
from discord import Member, Message, Colour, Role, Embed
from . import reactionMenu, expiryFunctions
from ..gameObjects.items import gameItem
from .. import botState
from ..users import basedUser
from ..scheduling import timedTask


class GiveawayMenu(reactionMenu.ReactionMenu):
    def __init__(self, msg: Message, items: List[gameItem.GameItem], activeTime: timedelta, titleTxt: str = "", desc: str = "", col: Colour = None, footerTxt: str = "", img: str = "", thumb: str = "", icon: str = "", authorName: str = "", targetMember: Member = None, targetRole: Role = None):
        options = {i.emoji: GiveawayMenuOption(self, i) for i in items}
        timeout = timedTask.TimedTask(expiryDelta=activeTime, expiryFunction=expiryFunctions.markExpiredMenu, expiryFunctionArgs=msg.id, rescheduleOnExpiryFuncFailure=True)
        botState.taskScheduler.scheduleTask(timeout)
        super().__init__(msg, options=options, titleTxt=titleTxt, desc=desc, col=col, timeout=timeout, footerTxt=footerTxt, img=img, thumb=thumb, icon=icon, authorName=authorName, targetMember=targetMember, targetRole=targetRole)
        self.givenUsers: Set[Member] = set()
        self.originalDesc = desc


    def hasGivenToUser(self, user: Member) -> bool:
        return user in self.givenUsers


    async def addGivenUser(self, user: Member):
        self.desc = f"{self.originalDesc}\n\nNumber of users given to: {len(self.givenUsers)}"
        await self.updateMessage(noRefreshOptions=True)


    @classmethod
    def fromDict(cls, data: dict, **kwargs):
        raise NotImplementedError()


    def toDict(self, **kwargs) -> dict:
        raise NotImplementedError()


class GiveawayMenuOption(reactionMenu.NonSaveableReactionMenuOption):
    def __init__(self, menu: GiveawayMenu, item: gameItem.GameItem):
        super().__init__(item.name, item.emoji, addFunc=self.award)
        self.item = item
        self.menu = menu


    async def award(self, reactingUser: Member):
        if not self.menu.hasGivenToUser(reactingUser):
            bUser: basedUser.BasedUser = botState.usersDB.getOrAddID(reactingUser.id)
            # de-serializing and re-serializing here in order to get a copy (if appropriate)
            itemCopy = type(self.item).fromDict(self.item.toDict(saveType=True))
            bUser.getInventoryForItem(self.item).addItem(itemCopy)
            self.menu.givenUsers.add(reactingUser)
            await self.menu.addGivenUser(reactingUser)
