from typing import Optional, Tuple, cast, List

from discord import Interaction
from discord.abc import Snowflake
from discord.app_commands import Range

from ...interactions.basedApp import BasedCog
from ... import client, lib
from ...users import basedUser
from ...cfg import cfg
from ...cfg.bbData import ItemCategory
from ...gameObjects.inventories.inventory import Inventory
from ...gameObjects.items.gameItem import GameItem
from ...baseClasses.serializable import JsonType


class UsersUtilCog(BasedCog):
    def __init__(self, bot: client.BasedClient, *args, **kwargs):
        self.bot = bot
        super().__init__(*args, **kwargs)

#region util

    async def getBasedUserOrAuthor(self, interaction: Interaction, user_id: str, sendError: bool = True, errorEphemeral: bool = True) -> Tuple[Optional[basedUser.BasedUser], bool]:
        """Gets a user if one is specified. If not, then get the author. Returns a (Optional[basedUser.BasedUser], bool) tuple, where the first item is the requested
        basedUser, and the second indicates whether the user is the interaction author or not.
        If the result cannot be found in the usersDB, respond to the interaction with an error, and return (..., None).
        """
        if user_id:
            if not lib.stringTyping.isInt(user_id):
                if sendError:
                    await interaction.response.send_message(":x: Invalid user ID!", ephemeral=errorEphemeral)
                return (None, False)
            userId = int(user_id)
            isAuthor = False
        else:
            userId = interaction.user.id
            isAuthor = True

        if not self.bot.usersDB.idExists(userId):
            if sendError:
                await interaction.response.send_message(":x: Unknown user!", ephemeral=errorEphemeral)
            return (None, isAuthor)
        
        return (self.bot.usersDB.getUser(userId), isAuthor)


    async def getUserItemByIndex(self, interaction: Interaction, user: basedUser.BasedUser, item_type: ItemCategory, item_number: Range[int, 1, ...], sendErrors: bool = True, sendErrorsEphemeral: bool = True) -> Optional[Tuple[Inventory, GameItem]]:
        """Get an item from a user's inventory, from the item category name and item number.

        :param interaction: the command usage that triggered this function. Used for sending errors.
        :type interaction: Interaction
        :param user: the BasedUser whose item to get
        :type user: basedUser.BasedUser
        :param item_type: name of the category if items to look in
        :type item_type: ItemCategory
        :param item_number: index of the item in the user's inventory
        :type item_number: Range[int, 1, ...]
        :param sendErrors: if this is true and an error occurs, respond to the interaction with the error (Default True)
        :type sendErrors: bool, optional
        :param sendErrorsEphemeral: if sendErrors is true, send errors as ephemeral (Default True)
        :type sendErrorsEphemeral: bool, optional
        :return: An [Inventory, GameItem] tuple if no errors occurred. None otherwise.
        :rtype: Optional[Tuple[Inventory, GameItem]]
        """
        userItemInactives = user.getInventory(item_type)
        if item_number > userItemInactives.numKeys:
            if sendErrors:
                await interaction.response.send_message(f":x: Invalid item number! {'You only have' if user.id == interaction.user.id else 'The user only has'} {userItemInactives.numKeys} {item_type.value}s.",
                                                        ephemeral=sendErrorsEphemeral)
            return None
        
        return userItemInactives, userItemInactives.itemAtIndex(item_number - 1)


    async def getDefaultUserItemByIndex(self, interaction: Interaction, isAuthor: bool, item_type: ItemCategory, item_number: Range[int, 1, ...], sendErrors: bool = True, sendErrorsEphemeral: bool = True) -> Optional[GameItem]:
        """Get an item from a non-existent user's inventory, from the item category name and item number, using the default user from basedUser.defaultUserDict.

        :param interaction: the command usage that triggered this function. Used for sending errors.
        :type interaction: Interaction
        :param isAuthor: True if requesting an item from the calling user, False if requesting for another user
        :param item_type: name of the category if items to look in
        :type item_type: ItemCategory
        :param item_number: index of the item in the specified inventory
        :type item_number: Range[int, 1, ...]
        :param sendErrors: if this is true and an error occurs, respond to the interaction with the error (Default True)
        :type sendErrors: bool, optional
        :param sendErrorsEphemeral: if sendErrors is true, send errors as ephemeral (Default True)
        :type sendErrorsEphemeral: bool, optional
        :return: The requested item if no errors occurred. None otherwise.
        :rtype: Optional[GameItem]
        """
        userItemInactives = cast(JsonType, basedUser.defaultUserDict.get(basedUser.itemCategoryUserKeys[item_type], {}))

        if item_number > len(userItemInactives):
            if sendErrors:
                await interaction.response.send_message(f":x: Invalid item number! {'You only have' if isAuthor else 'The user only has'} {len(userItemInactives)} {item_type.value}s.",
                                                        ephemeral=sendErrorsEphemeral)
            return None
        
        itemDict = cast(JsonType, userItemInactives[list(userItemInactives.keys())[item_number - 1]])
        return basedUser.itemCategoryStoredTypes[item_type].deserialize(itemDict)

#endregion util


async def setup(bot: client.BasedClient):
    # Casting here because for some reason pyright doesn't think SerializableDiscordObject is a Snowflake,
    # even though it extends discord.Object
    await bot.add_cog(UsersUtilCog(bot), guilds=cast(List[Snowflake], cfg.developmentGuilds))
