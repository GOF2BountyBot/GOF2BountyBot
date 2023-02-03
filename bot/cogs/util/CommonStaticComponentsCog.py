from typing import Optional
from ... import client, lib
from ...lib.discordUtil import ZWSP, textChannel
from discord import Interaction, Message, Embed
from ...interactions.basedApp import BasedCog
from ...interactions.basedComponent import StaticComponents

class CommonStaticComponentsCog(BasedCog):
    @BasedCog.staticComponentCallback(StaticComponents.Clear_View)
    async def clearViewFromMessage(self, interaction: Interaction, userId: str) -> bool:
        "Returns True if the operation succeeded, or False if it didn't (e.g unmatched userId)"
        if userId and interaction.user.id != int(userId):
            return False

        if interaction.response.is_done():
            await interaction.edit_original_response(view=None)
        else:
            await interaction.response.edit_message(view=None)

        return True


    @BasedCog.staticComponentCallback(StaticComponents.Delete_Message)
    async def deleteMessage(self, interaction: Interaction, userId: str) -> bool:
        "Returns True if the operation succeeded, or False if it didn't (e.g unmatched userId)"
        if userId and interaction.user.id != int(userId):
            return False

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
        if userId and interaction.user.id != int(userId):
            return

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
        if userId and interaction.user.id != int(userId):
            return

        message = interaction.message
        if message is None: return
        if not message.embeds: return
        embed = message.embeds[0]
        
        thumb = embed.thumbnail.url if embed.thumbnail is not None else None
        img = embed.image.url if embed.image is not None else None
        
        embed.set_image(url=thumb)
        embed.set_thumbnail(url=img)
            
        await interaction.response.edit_message(embed=embed)


async def setup(bot: client.BasedClient):
    await bot.add_cog(CommonStaticComponentsCog(bot))
