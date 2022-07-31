from typing import Optional, cast, List

from discord import Interaction
from discord.abc import Snowflake

from ...interactions.basedApp import BasedCog
from ... import client, lib
from ...users import basedUser
from ...cfg import cfg


class UsersUtilCog(BasedCog):
    def __init__(self, bot: client.BasedClient, *args, **kwargs):
        self.bot = bot
        super().__init__(*args, **kwargs)

#region util

    async def getUserOrAuthor(self, interaction: Interaction, user_id: str, sendError: bool = True) -> Optional[basedUser.BasedUser]:
        """Gets a user if one is specified. If not, then get the author.
        If the result cannot be found in the usersDB, respond to the interaction with an error, and return None.
        """
        if user_id:
            if not lib.stringTyping.isInt(user_id):
                if sendError:
                    await interaction.response.send_message("Invalid user ID.", ephemeral=True)
                return None
            userId = int(user_id)
        else:
            userId = interaction.user.id

        if not self.bot.usersDB.idExists(userId):
            if sendError:
                await interaction.response.send_message("Unknown user.", ephemeral=True)
            return None
        
        return self.bot.usersDB.getUser(userId)
    
#endregion util


async def setup(bot: client.BasedClient):
    # Casting here because for some reason pyright doesn't think SerializableDiscordObject is a Snowflake,
    # even though it extends discord.Object
    await bot.add_cog(UsersUtilCog(bot), guilds=cast(List[Snowflake], cfg.developmentGuilds))
