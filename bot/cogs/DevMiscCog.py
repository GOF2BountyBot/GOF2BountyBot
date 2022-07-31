import traceback
from typing import Optional, TYPE_CHECKING, Union, List, cast
from .. import client, lib
from ..lib.discordUtil import ZWSP, textChannel
from discord import app_commands, Interaction, ButtonStyle, Embed, Colour
from discord.utils import utcnow
from discord.ui import View, Button
from ..cfg import cfg
from ..cfg.cfg import basicAccessLevels
from ..interactions import basedCommand
from ..interactions.basedApp import BasedCog
from ..interactions.basedComponent import StaticComponents
from typing import List, cast
from discord.abc import Snowflake
if TYPE_CHECKING:
    from .util import EmbedEditorCog
from .util.EmbedEditorUtil import EmbedTextParams, EMBED_EDIT_TEXT_ARGS_SEPARATOR


def messageEditorView(interaction: Interaction, userId: Optional[Union[int, str]], embed: Optional[Embed] = None) -> View:
    view = View()
    _userId = "" if userId is None else str(userId)

    confirmButton = Button(style=ButtonStyle.green, label="send", row=0 if embed is None else 3)
    confirmButton = StaticComponents.Clone_Message(confirmButton, args=_userId)
    cancelButton = Button(style=ButtonStyle.red, label="cancel", row=0 if embed is None else 3)
    cancelButton = StaticComponents.Clear_View(cancelButton, args=_userId)
    view.add_item(cancelButton).add_item(confirmButton)
    if embed is not None:
        editEmbedTextButton = Button(style=ButtonStyle.blurple, label="edit embed text", row=0)
        editEmbedTextButton = StaticComponents.User_Embed_Edit_Text(editEmbedTextButton, args=EMBED_EDIT_TEXT_ARGS_SEPARATOR + _userId)
        view.add_item(editEmbedTextButton)

        editEmbedImagesButton = Button(style=ButtonStyle.blurple, label="edit embed images", row=0)
        editEmbedImagesButton = StaticComponents.User_Embed_Edit_Images(editEmbedImagesButton, args=_userId)
        view.add_item(editEmbedImagesButton)

        addFieldButton = Button(style=ButtonStyle.blurple, label="add embed field", row=1)
        addFieldButton = StaticComponents.User_Embed_Add_Field(addFieldButton, args=_userId)
        view.add_item(addFieldButton)

        removeFieldButton = Button(style=ButtonStyle.blurple, label="remove embed field", row=1)
        removeFieldButton = StaticComponents.Dev_Say_Embed_Remove_Field_Select(removeFieldButton, args=_userId)
        view.add_item(removeFieldButton)

        editFieldButton = Button(style=ButtonStyle.blurple, label="edit embed field", row=2)
        editFieldButton = StaticComponents.Dev_Say_Embed_Edit_Field_Select(editFieldButton, args=_userId)
        view.add_item(editFieldButton)

        swapFieldsButton = Button(style=ButtonStyle.blurple, label="swap fields", row=2)
        swapFieldsButton = StaticComponents.Dev_Say_Embed_Reorder_Fields_Select(swapFieldsButton, args=_userId)
        view.add_item(swapFieldsButton)
    
    return view


class DevMiscCog(BasedCog):
    def __init__(self, bot: client.BasedClient, *args, **kwargs):
        self.bot = bot
        super().__init__(*args, **kwargs)

#region util

    def getEmbedEditorCog(self) -> Optional["EmbedEditorCog.EmbedEditorCog"]:
        embedEditorCog = self.bot.get_cog("EmbedEditorCog")
        if embedEditorCog is None:
            self.bot.logger.log("DevMiscCog", "startRemoveField", f"Unable to find cog on self.bot: EmbedEditorCog", eventType="COG_NOT_FOUND")
            return None
        return cast("EmbedEditorCog.EmbedEditorCog", embedEditorCog)

#endregion
#region static components

    @BasedCog.staticComponentCallback(StaticComponents.Dev_Say_Embed_Remove_Field_Select)
    async def startRemoveField(self, interaction: Interaction, userId: str):
        if embedEditorCog := self.getEmbedEditorCog():
            await embedEditorCog.startRemoveField(interaction, userId=userId,
                                                    staticComponentId=StaticComponents.Dev_Say_Embed_Remove_Field_Select,
                                                    makeView=messageEditorView,
                                                    endRemoveField=StaticComponents.Dev_Say_Embed_Remove_Field)


    @BasedCog.staticComponentCallback(StaticComponents.Dev_Say_Embed_Remove_Field)
    async def endRemoveField(self, interaction: Interaction, userId: str):
        if embedEditorCog := self.getEmbedEditorCog():
            await embedEditorCog.endRemoveField(interaction, userId=userId, staticComponentId=StaticComponents.Dev_Say_Embed_Remove_Field, makeView=messageEditorView)


    @BasedCog.staticComponentCallback(StaticComponents.Dev_Say_Embed_Edit_Field_Select)
    async def startEditField(self, interaction: Interaction, userId: str):
        if embedEditorCog := self.getEmbedEditorCog():
            await embedEditorCog.startEditField(interaction, userId=userId,
                                                    staticComponentId=StaticComponents.Dev_Say_Embed_Edit_Field_Select,
                                                    makeView=messageEditorView,
                                                    endEditField=StaticComponents.Dev_Say_Embed_Edit_Field)

    
    @BasedCog.staticComponentCallback(StaticComponents.Dev_Say_Embed_Edit_Field)
    async def endEditField(self, interaction: Interaction, userId: str):
        if embedEditorCog := self.getEmbedEditorCog():
            await embedEditorCog.endEditField(interaction, userId=userId,
                                                    staticComponentId=StaticComponents.Dev_Say_Embed_Edit_Field,
                                                    makeView=messageEditorView)


    @BasedCog.staticComponentCallback(StaticComponents.Dev_Say_Embed_Reorder_Fields_Select)
    async def startReorderFields(self, interaction: Interaction, userId: str):
        if embedEditorCog := self.getEmbedEditorCog():
            await embedEditorCog.startReorderFields(interaction, userId=userId,
                                                    staticComponentId=StaticComponents.Dev_Say_Embed_Reorder_Fields_Select,
                                                    makeView=messageEditorView,
                                                    endReorderFields=StaticComponents.Dev_Say_Embed_Reorder_Fields)

    
    @BasedCog.staticComponentCallback(StaticComponents.Dev_Say_Embed_Reorder_Fields)
    async def endReorderFields(self, interaction: Interaction, userId: str):
        if embedEditorCog := self.getEmbedEditorCog():
            await embedEditorCog.endReorderFields(interaction, userId=userId,
                                                    staticComponentId=StaticComponents.Dev_Say_Embed_Reorder_Fields,
                                                    makeView=messageEditorView)


#endregion
#region commands

    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer)
    @app_commands.command(name="sleep",
                            description="Shut down the bot.")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_sleep(self, interaction: Interaction):
        """developer command saving all data to JSON and then shutting down the bot
        """
        self.bot.shutDownState = client.ShutDownState.shutdown
        await interaction.response.send_message("shutting down.")
        await self.bot.shutdown()


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer)
    @app_commands.command(name="save",
                            description="Save all databases to JSON.")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_save(self, interaction: Interaction):
        """developer command saving all databases to JSON
        """
        await interaction.response.defer(ephemeral=True)
        try:
            self.bot.saveAllDBs()
        except Exception as e:
            print("SAVING ERROR", e.__class__.__name__)
            print(traceback.format_exc())
            await interaction.followup.send(f"Saving failed - {type(e).__name__}", ephemeral=True)
            return
        print(utcnow().strftime("%H:%M:%S: Data saved manually!"))
        await interaction.followup.send("saved!", ephemeral=True)


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer)
    @app_commands.command(name="say",
                            description="Say something in this channel.")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_say(self, interaction: Interaction, content: Optional[str] = None, add_embed: bool = False, string_form: Optional[str] = None):
        """developer command sending a message to the same channel as the command is called in
        """
        if string_form is not None:
            await interaction.response.defer(thinking=False)
            await textChannel(interaction).send(**lib.discordUtil.messageArgsFromStr(string_form))
            return

        if content is None and add_embed == False:
            await interaction.response.send_message("Cannot send a message without content or an embed!", ephemeral=True)
            return

        content = content or ""
        embed = None

        if add_embed:
            embed = Embed()

            modal = EmbedTextParams(title="Embed parameters")
            await interaction.response.send_modal(modal)
            if await modal.wait(): return

            if modal.titleTxt.value:
                embed.title = modal.titleTxt.value
            if modal.authorName.value:
                embed.set_author(name=modal.authorName.value, icon_url=None)
            if modal.desc.value:
                embed.description = modal.desc.value
            if modal.footerText.value:
                embed.set_footer(text=modal.footerText.value, icon_url=None)
            if modal.colour.value:
                if modal.colour.value.lower() == "random":
                    embed.colour = Colour.random()
                else:
                    embed.colour = Colour(int(modal.colour.value, base=16))
            else:
                embed.colour = None
        
        view = messageEditorView(interaction, interaction.user.id, embed=embed)

        if embed is not None:
            if lib.discordUtil.embedEmpty(embed):
                embed.description = ZWSP
            await interaction.followup.send(content=content, embed=embed, ephemeral=True, view=view)
        else:
            await interaction.followup.send(content=content, ephemeral=True, view=view)


async def setup(bot: client.BasedClient):
    # Casting here because for some reason pyright doesn't think SerializableDiscordObject is a Snowflake,
    # even though it extends discord.Object
    await bot.add_cog(DevMiscCog(bot), guilds=cast(List[Snowflake], cfg.developmentGuilds))
