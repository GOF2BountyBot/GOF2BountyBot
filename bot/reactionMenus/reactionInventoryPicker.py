from __future__ import annotations
from . import reactionMenu
from ..cfg import cfg
from ..gameObjects.items import gameItem
from ..gameObjects.inventories import inventory
from discord import Message, Colour, Member, Role
from .. import lib
from ..scheduling import timedTask

# The maximum number of gameItems displayable per menu page
maxItemsPerPage = len(cfg.defaultEmojis.menuOptions)


class ReactionInventoryPickerOption(reactionMenu.ReactionMenuOption):
    """A reaction menu option that represents a gameItem instance.
    Unless configured otherwise, the option's name and emoji will correspond to the item's name and emoji.

    :var item: The gameItem that this option represents
    :vartype item: gameItem
    """

    def __init__(self, item : gameItem.GameItem, menu : "ReactionInventoryPicker", emoji : lib.emojis.BasedEmoji = None,
            name : str = None):
        """
        :param gameItem item: The gameItem that this option represents
        :param ReactionInventoryPicker menu: The ReactionMenu where this option is active
        :param lib.emojis.BasedEmoji emoji: The emoji that a user must react with in order to trigger this menu option
                                            (Default item.emoji)
        :param str name: The name of this option as shown in the menu (Default item.name)
        :raise ValueError: When an emoji isn't provided and the given gameItem does not have an emoji
                            (TODO: default to cfg.defaultEmojis.menuOptions)
        """

        self.item = item

        if emoji is None:
            if item.hasEmoji:
                emoji = item.emoji
            else:
                raise ValueError("Attempted to create a ReactionInventoryPickerOption without providing an emoji, " \
                                    + "and the provided item has no emoji")
        if name is None:
            name = item.name
            if item.hasEmoji and emoji != item.emoji:
                name += " " + item.emoji.sendable
        super(ReactionInventoryPickerOption, self).__init__(name, emoji, addFunc=menu.selectItem, addArgs=self.item,
                                                            removeFunc=menu.deselectItem, removeArgs=self.item)


    def toDict(self, **kwargs) -> dict:
        """Serialize this menu option to dictionary format for saving.

        :return: A dictionary containing all information needed to reconstruct this menu option instance - the item
                    it represents
        :rtype: dict
        """
        baseDict = super(ReactionInventoryPickerOption, self).toDict(**kwargs)
        baseDict["item"] = self.item.toDict(**kwargs)

        return baseDict


class ReactionInventoryPicker(reactionMenu.CancellableReactionMenu):
    """A reaction menu allowing users to select a gameItem from a inventory.
    TODO: Implement paging
    TODO: Display item counts?
    TODO: Reimplement as a PagedReactionMenu preset

    :var inventory: The inventory to display and select from (TODO: Rename)
    :vartype inventory: inventory
    :var itemsPerPage: The maximum number of items that can be displayed per menu page
    :vartype itemsPerPage: int
    :var page: The current page the menu is displaying from inventory
    :vartype page: int
    """

    def __init__(self, msg : Message, inventory : inventory.Inventory, itemsPerPage : int = maxItemsPerPage,
            titleTxt : str = "", desc : str = "", col : Colour = None, timeout : timedTask.TimedTask = None,
            footerTxt : str = "", img : str = "", thumb : str = "", icon : str = "", authorName : str = "",
            targetMember : Member = None, targetRole : Role = None):
        """
        :param discord.Message msg: The discord message where this menu should be embedded
        :param inventory inventory: The inventory to display and select from (TODO: Rename)
        :param int maxPerPage: The maximum number of items that can be displayed per menu page (Default maxItemsPerPage)
        :param str titleTxt: The content of the embed title (Default "")
        :param str desc: The content of the embed description; appears at the top below the title (Default "")
        :param discord.Colour col: The colour of the embed's side strip (Default None)
        :param TimedTask timeout: The TimedTask responsible for expiring this menu (Default None)
        :param str footerTxt: Secondary description appearing in darker font at the bottom of the embed (Default "")
        :param str img: URL to a large icon appearing as the content of the embed, left aligned like a field (Default "")
        :param str thumb: URL to a larger image appearing to the right of the title (Default "")
        :param str authorName: Secondary, smaller title for the embed (Default "")
        :param str icon: URL to a smaller image to the left of authorName. AuthorName is required for this to be displayed.
                            (Default "")
        :param discord.Member targetMember: The only discord.Member that is able to interact with this menu.
                                            All other reactions are ignored (Default None)
        :param discord.Role targetRole: In order to interact with this menu, users must possess this role.
                                        All other reactions are ignored (Default None)
        :raise ValueError: When itemsPerPage is bigger than maxItemsPerPage
                            (TODO: Is this necessary? options don't currently use the default menu emojis)
        """
        if itemsPerPage > maxItemsPerPage:
            raise ValueError("Tried to instantiate a ReactionItemPicker with more than " + str(maxItemsPerPage) \
                                + " itemsPerPage (requested " + str(itemsPerPage) + ")")

        # TODO: Does inventory actually need to be stored?
        self.inventory = inventory
        self.itemsPerPage = itemsPerPage

        self.page = 1
        itemOptions = {}
        itemPage = inventory.getPage(self.page, self.itemsPerPage)
        for itemNum in range(len(itemPage)):
            optionEmoji = cfg.defaultEmojis.menuOptions[itemNum]
            item = itemPage[itemNum].item
            itemOptions[optionEmoji] = ReactionInventoryPickerOption(item, self, emoji=optionEmoji)

        super(ReactionInventoryPicker, self).__init__(msg, options=itemOptions, titleTxt=titleTxt, desc=desc, col=col,
                                                        footerTxt=footerTxt, img=img, thumb=thumb, icon=icon,
                                                        authorName=authorName, timeout=timeout, targetMember=targetMember,
                                                        targetRole=targetRole)


    def selectItem(self, item : gameItem.GameItem) -> gameItem.GameItem:
        """Pass back the selected gameItem to the calling function.
        This method is called on reaction add that corresponds to a gameItem currently on display

        :param gameItem item: The gameItem that the user just selected
        :return: item
        :rtype: gameItem
        """
        print("picked " + str(item))
        return item


    def deselectItem(self, item : gameItem.GameItem) -> gameItem.GameItem:
        """Pass back the deselected gameItem to the calling function.
        This method is called on reaction remove that corresponds to a gameItem currently on display

        :param gameItem item: The gameItem that the user just deselected
        :return: item
        :rtype: gameItem
        """
        print("unpicked " + str(item))
        return item


    def toDict(self, **kwargs) -> dict:
        """⚠ ReactionInventoryPickers are not currently saveable. Do not use this method.
        Dummy method, once implemented this method will serialize this reactionMenu to dictionary format.

        :return: A dummy dictionary containing basic information about the menu, but not all information needed
                    to reconstruct the menu.
        :rtype: dict
        :raise NotImplementedError: Always.
        """
        raise NotImplementedError("Attempted to call toDict on an unsaveable reaction menu type")


    @classmethod
    def fromDict(cls, rmDict : dict, **kwargs) -> ReactionInventoryPicker:
        """⚠ ReactionInventoryPickers are not currently saveable. Do not use this method.
        When implemented, this function will construct a new ReactionInventoryPicker from a dictionary-serialized
        representation - The opposite of ReactionInventoryPicker.toDict.

        :param dict rmDict: A dictionary containg all information needed to construct the required ReactionInventoryPicker
        :raise NotImplementedError: Always.
        """
        raise NotImplementedError("Attempted to call fromDict on an unsaveable reaction menu type")
