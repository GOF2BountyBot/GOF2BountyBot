from typing import Optional, Union
import asyncio

from discord import Interaction, Message, Embed

from bot import client, lib
from bot.lib.discordUtil import ZWSP, textChannel
from bot.interactions.basedApp import BasedCog
from bot.interactions.basedComponent import StaticComponents
from bot.cfg import cfg

class CommonStaticComponentsCog(BasedCog):
#region util

    def ensureOwnership(self, interaction: Interaction, userId: Union[int, str, None] = None) -> bool:
        """Make sure that `userId`, if provided, matches the Id of the interacting user.
        If not, send a user friendly error. This is not awaited.

        :param interaction: The interaction to check
        :type interaction: Interaction
        :param userId: The id of the owning user, defaults to None
        :type userId: Union[int, str, None], optional
        :return: `True` if `userId` is not provided or matches `interaction.user`, False otherwise
        :rtype: bool
        """
        if userId and int(userId) != interaction.user.id:
            asyncio.create_task(interaction.response.send_message(f"{cfg.defaultEmojis.cancel} This menu does not belong to you.", ephemeral=True))
            return False
        return True

#endregion
    @BasedCog.staticComponentCallback(StaticComponents.Clear_View)
    async def clearViewFromMessage(self, interaction: Interaction, userId: str) -> bool:
        "Returns True if the operation succeeded, or False if it didn't (e.g unmatched userId)"
        if not self.ensureOwnership(interaction, userId): return False

        if interaction.response.is_done():
            await interaction.edit_original_response(view=None)
        else:
            await interaction.response.edit_message(view=None)

        return True


    @BasedCog.staticComponentCallback(StaticComponents.Delete_Message)
    async def deleteMessage(self, interaction: Interaction, userId: str) -> bool:
        "Returns True if the operation succeeded, or False if it didn't (e.g unmatched userId)"
        if not self.ensureOwnership(interaction, userId): return False

        if not interaction.response.is_done():
            await interaction.response.defer(thinking=False)
        await interaction.delete_original_response()

        return True


    @BasedCog.staticComponentCallback(StaticComponents.Clone_Message)
    async def cloneMessage(self, interaction: Interaction, userId: str) -> Optional[Message]:
        """Send a new copy of `interaction.message` in the same channel, and clear the view from `interaction.message`.
        `interaction` must have occurred in a text channel.
        Returns the created message, unless the operation was cancelled for some reason.
        """
        if not self.ensureOwnership(interaction, userId): return

        message = interaction.message
        if message is None: return
        embed = message.embeds[0] if message.embeds else None

        await interaction.response.edit_message(content="sent!", view=None)

        if embed is not None:
            if lib.discordUtil.embedEmpty(embed):
                embed.description = ZWSP
            created = await textChannel(interaction).send(content=message.content, embed=embed)
        else:
            created = await textChannel(interaction).send(content=message.content)

        return created
    
    
    @BasedCog.staticComponentCallback(StaticComponents.Swap_Embed_Image_And_Thumbnail)
    async def swapEmbedImageAndThumbnail(self, interaction: Interaction, userId: str) -> Optional[Embed]:
        """Swap the images in the thumbnail and image slots of the embed.
        Returns the new embed if the operation suceeded, or None if it did not, eg unmatched user id.
        """
        if not self.ensureOwnership(interaction, userId): return

        message = interaction.message
        if message is None: return
        if not message.embeds: return
        embed = message.embeds[0]
        
        thumb = embed.thumbnail.url if embed.thumbnail is not None else None
        img = embed.image.url if embed.image is not None else None
        
        embed.set_image(url=thumb)
        embed.set_thumbnail(url=img)
            
        await interaction.response.edit_message(embed=embed)
        return embed


async def setup(bot: client.BasedClient):
    await bot.add_cog(CommonStaticComponentsCog(bot))
