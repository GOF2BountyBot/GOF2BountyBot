import json
from typing import TYPE_CHECKING, Dict, Optional, Type, Union, List, cast
import traceback
from datetime import datetime, timedelta

from discord import app_commands, Interaction, ButtonStyle, Embed, Colour
from discord.utils import utcnow, MISSING
from discord.ui import View, Button
from discord.abc import Snowflake
import random

from .. import client, lib, botState
from ..lib.discordUtil import ZWSP, textChannel
from..lib.BASED_version import checkForUpdates, getBASEDVersion, nextUpdateCheck
from ..cfg import cfg, bbData
from ..cfg.cfg import basicAccessLevels
from ..interactions import basedCommand
from ..interactions.basedApp import BasedCog
from ..interactions.basedComponent import StaticComponents
from ..users.basedGuild import BasedGuild
from ..users.basedUser import OwnedMenuType
from .util.EmbedEditorUtil import EmbedTextParams, EMBED_EDIT_TEXT_ARGS_SEPARATOR
from .util.transformers import PlayOrAnnounceChannel
from ..scheduling.timedTask import TimedTask
from ..commands import commandsDB as textCommandsDB
from ..interactions.accessLevels import _accessLevels
from ..reactionMenus import reactionMenu
from ..databases.bountyDB import nameForDivision, BountyDB
from .util.CommonAutocomplete import criminalAutoComplete
from .util.parameterVerifiers import verifyCriminalName
from ..logging import LogCategory
from ..baseClasses.basedEnum import BasedEnum
from ..gameObjects.items import shipItem
from ..gameObjects.bounties import solarSystem
from ..gameObjects.bounties.bountyBoards.bountyBoardChannel import BountyBoardChannel

if TYPE_CHECKING:
    from . import BASEDVersionCog


class BountyEditField(BasedEnum):
    activeShip = "activeShip"
    faction = "faction"
    issueTime = "issueTime"
    endTime = "endTime"
    expired = "expired"
    route = "route"
    reward = "reward"
    rewardPerSys = "rewardPerSys"
    checked = "checked"
    answer = "answer"
    techLevel = "techLevel"
    respawnTime = "respawnTime"


def base_editorView(interaction: Interaction, userId: Optional[Union[int, str]], embed: Optional[Embed] = None) -> View:
    view = View()
    _userId = "" if userId is None else str(userId)

    cancelButton = Button(style=ButtonStyle.red, label="cancel", row=0 if embed is None else 3)
    cancelButton = StaticComponents.Clear_View(cancelButton, args=_userId)
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
    
    return view


def send_editorView(interaction: Interaction, userId: Optional[Union[int, str]], embed: Optional[Embed] = None) -> View:
    view = base_editorView(interaction, userId, embed=embed)
    _userId = "" if userId is None else str(userId)

    confirmButton = Button(style=ButtonStyle.green, label="send", row=0 if embed is None else 3)
    confirmButton = StaticComponents.Clone_Message(confirmButton, args=_userId)
    view.add_item(confirmButton)
    if embed is not None:
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


def broadcast_editorView(interaction: Interaction, userId: Optional[Union[int, str]], embed: Optional[Embed] = None) -> View:
    view = base_editorView(interaction, userId, embed=embed)
    _userId = "" if userId is None else str(userId)

    confirmButton = Button(style=ButtonStyle.green, label="send", row=0 if embed is None else 3)
    confirmButton = StaticComponents.Dev_Broadcast_Submit(confirmButton, args=_userId)
    view.add_item(confirmButton)
    if embed is not None:
        removeFieldButton = Button(style=ButtonStyle.blurple, label="remove embed field", row=1)
        removeFieldButton = StaticComponents.Dev_Broadcast_Embed_Remove_Field_Select(removeFieldButton, args=_userId)
        view.add_item(removeFieldButton)

        editFieldButton = Button(style=ButtonStyle.blurple, label="edit embed field", row=2)
        editFieldButton = StaticComponents.Dev_Broadcast_Embed_Edit_Field_Select(editFieldButton, args=_userId)
        view.add_item(editFieldButton)

        swapFieldsButton = Button(style=ButtonStyle.blurple, label="swap fields", row=2)
        swapFieldsButton = StaticComponents.Dev_Broadcast_Embed_Reorder_Fields_Select(swapFieldsButton, args=_userId)
        view.add_item(swapFieldsButton)
    
    return view


def announce_broadcast_editorView(interaction: Interaction, userId: Optional[Union[int, str]], embed: Optional[Embed] = None) -> View:
    view = base_editorView(interaction, userId, embed=embed)
    _userId = "" if userId is None else str(userId)

    confirmButton = Button(style=ButtonStyle.green, label="send", row=0 if embed is None else 3)
    confirmButton = StaticComponents.Dev_Announce_Broadcast_Submit(confirmButton, args=_userId)
    view.add_item(confirmButton)
    if embed is not None:
        removeFieldButton = Button(style=ButtonStyle.blurple, label="remove embed field", row=1)
        removeFieldButton = StaticComponents.Dev_Announce_Broadcast_Embed_Remove_Field_Select(removeFieldButton, args=_userId)
        view.add_item(removeFieldButton)

        editFieldButton = Button(style=ButtonStyle.blurple, label="edit embed field", row=2)
        editFieldButton = StaticComponents.Dev_Announce_Broadcast_Embed_Edit_Field_Select(editFieldButton, args=_userId)
        view.add_item(editFieldButton)

        swapFieldsButton = Button(style=ButtonStyle.blurple, label="swap fields", row=2)
        swapFieldsButton = StaticComponents.Dev_Announce_Broadcast_Embed_Reorder_Fields_Select(swapFieldsButton, args=_userId)
        view.add_item(swapFieldsButton)
    
    return view


class DevMiscCog(BasedCog):
    def __init__(self, bot: client.BasedClient, *args, **kwargs):
        self.bot = bot
        super().__init__(*args, **kwargs)

#region util

    def describeTT(self, tt: Optional[TimedTask], issueTime: bool = True, expiryFunc: bool = True, nextExpiry: bool = True,
                    expiryDelta: bool = True, autoReschedule: bool = True, scheduled: bool = True, sep="\n") -> str:
        """Describe a TimedTask in a human-readable string."""
        if tt is None:
            return "null TT"

        ttStrParts = []
        if issueTime:
            ttStrParts.append(f"Issue time: {'null' if tt.issueTime is None else tt.issueTime.strftime('%d/%m/%Y, %H:%M:%S')}")
        if nextExpiry:
            ttStrParts.append(f"Next expiry: {'null' if tt.expiryTime is None else tt.expiryTime.strftime('%d/%m/%Y, %H:%M:%S')}")
        if expiryDelta:
            ttStrParts.append(f"Expiry delta: {'null' if tt.expiryDelta is None else lib.timeUtil.td_format_noYM(tt.expiryDelta)}")
        if autoReschedule:
            ttStrParts.append(f"Auto-reschedule: {tt.autoReschedule}")
        if expiryFunc:
            ttStrParts.append(f"Function: {'None' if tt.expiryFunction is None else str(tt.expiryFunction)}")
            ttStrParts.append(f"Args: {'None' if tt.expiryFunctionArgs is None else 'Not None'}")
        if scheduled:
            ttStrParts.append(f"Scheduled on taskScheduler: {tt in self.bot.taskScheduler.tasksHeap}")

        return(sep.join(ttStrParts))

#endregion util
#region static components
#region dev_cmd_say

    @BasedCog.staticComponentCallback(StaticComponents.Dev_Say_Embed_Remove_Field_Select)
    async def send_startRemoveField(self, interaction: Interaction, userId: str):
        if embedEditorCog := self.getEmbedEditorCog():
            await embedEditorCog.startRemoveField(interaction, userId=userId,
                                                    staticComponentId=StaticComponents.Dev_Say_Embed_Remove_Field_Select,
                                                    makeView=send_editorView,
                                                    endRemoveField=StaticComponents.Dev_Say_Embed_Remove_Field)


    @BasedCog.staticComponentCallback(StaticComponents.Dev_Say_Embed_Remove_Field)
    async def send_endRemoveField(self, interaction: Interaction, userId: str):
        if embedEditorCog := self.getEmbedEditorCog():
            await embedEditorCog.endRemoveField(interaction, userId=userId, staticComponentId=StaticComponents.Dev_Say_Embed_Remove_Field, makeView=send_editorView)


    @BasedCog.staticComponentCallback(StaticComponents.Dev_Say_Embed_Edit_Field_Select)
    async def send_startEditField(self, interaction: Interaction, userId: str):
        if embedEditorCog := self.getEmbedEditorCog():
            await embedEditorCog.startEditField(interaction, userId=userId,
                                                    staticComponentId=StaticComponents.Dev_Say_Embed_Edit_Field_Select,
                                                    makeView=send_editorView,
                                                    endEditField=StaticComponents.Dev_Say_Embed_Edit_Field)

    
    @BasedCog.staticComponentCallback(StaticComponents.Dev_Say_Embed_Edit_Field)
    async def send_endEditField(self, interaction: Interaction, userId: str):
        if embedEditorCog := self.getEmbedEditorCog():
            await embedEditorCog.endEditField(interaction, userId=userId,
                                                    staticComponentId=StaticComponents.Dev_Say_Embed_Edit_Field,
                                                    makeView=send_editorView)


    @BasedCog.staticComponentCallback(StaticComponents.Dev_Say_Embed_Reorder_Fields_Select)
    async def send_startReorderFields(self, interaction: Interaction, userId: str):
        if embedEditorCog := self.getEmbedEditorCog():
            await embedEditorCog.startReorderFields(interaction, userId=userId,
                                                    staticComponentId=StaticComponents.Dev_Say_Embed_Reorder_Fields_Select,
                                                    makeView=send_editorView,
                                                    endReorderFields=StaticComponents.Dev_Say_Embed_Reorder_Fields)

    
    @BasedCog.staticComponentCallback(StaticComponents.Dev_Say_Embed_Reorder_Fields)
    async def send_endReorderFields(self, interaction: Interaction, userId: str):
        if embedEditorCog := self.getEmbedEditorCog():
            await embedEditorCog.endReorderFields(interaction, userId=userId,
                                                    staticComponentId=StaticComponents.Dev_Say_Embed_Reorder_Fields,
                                                    makeView=send_editorView)

#endregion
#region dev_cmd_broadcast
#region play channel

    @BasedCog.staticComponentCallback(StaticComponents.Dev_Broadcast_Embed_Remove_Field_Select)
    async def broadcast_startRemoveField(self, interaction: Interaction, userId: str):
        await self.EmbedEditorCog.startRemoveField(interaction, userId=userId,
                                                    staticComponentId=StaticComponents.Dev_Broadcast_Embed_Remove_Field_Select,
                                                    makeView=broadcast_editorView,
                                                    endRemoveField=StaticComponents.Dev_Broadcast_Embed_Remove_Field)


    @BasedCog.staticComponentCallback(StaticComponents.Dev_Broadcast_Embed_Remove_Field)
    async def broadcast_endRemoveField(self, interaction: Interaction, userId: str):
        await self.EmbedEditorCog.endRemoveField(interaction, userId=userId, staticComponentId=StaticComponents.Dev_Broadcast_Embed_Remove_Field, makeView=send_editorView)


    @BasedCog.staticComponentCallback(StaticComponents.Dev_Broadcast_Embed_Edit_Field_Select)
    async def broadcast_startEditField(self, interaction: Interaction, userId: str):
        await self.EmbedEditorCog.startEditField(interaction, userId=userId,
                                                    staticComponentId=StaticComponents.Dev_Broadcast_Embed_Edit_Field_Select,
                                                    makeView=broadcast_editorView,
                                                    endEditField=StaticComponents.Dev_Broadcast_Embed_Edit_Field)

    
    @BasedCog.staticComponentCallback(StaticComponents.Dev_Broadcast_Embed_Edit_Field)
    async def broadcast_endEditField(self, interaction: Interaction, userId: str):
        await self.EmbedEditorCog.endEditField(interaction, userId=userId,
                                                    staticComponentId=StaticComponents.Dev_Broadcast_Embed_Edit_Field,
                                                    makeView=broadcast_editorView)


    @BasedCog.staticComponentCallback(StaticComponents.Dev_Broadcast_Embed_Reorder_Fields_Select)
    async def broadcast_startReorderFields(self, interaction: Interaction, userId: str):
        await self.EmbedEditorCog.startReorderFields(interaction, userId=userId,
                                                    staticComponentId=StaticComponents.Dev_Broadcast_Embed_Reorder_Fields_Select,
                                                    makeView=broadcast_editorView,
                                                    endReorderFields=StaticComponents.Dev_Broadcast_Embed_Reorder_Fields)

    
    @BasedCog.staticComponentCallback(StaticComponents.Dev_Broadcast_Embed_Reorder_Fields)
    async def broadcast_endReorderFields(self, interaction: Interaction, userId: str):
        await self.EmbedEditorCog.endReorderFields(interaction, userId=userId,
                                                    staticComponentId=StaticComponents.Dev_Broadcast_Embed_Reorder_Fields,
                                                    makeView=broadcast_editorView)

    
    @BasedCog.staticComponentCallback(StaticComponents.Dev_Broadcast_Submit)
    async def broadcast_broadcastMessage(self, interaction: Interaction, userId: str):
        """Send a new copy of `interaction.message` in the play channel of every guild that has one,
        and clear the view from `interaction.message`.
        """
        if userId and interaction.user.id != int(userId):
            return

        message = interaction.message
        if message is None: return
        embed = message.embeds[0] if message.embeds else None
        if embed is not None and lib.discordUtil.embedEmpty(embed):
            embed.description = ZWSP

        await interaction.response.send_message("sending...", ephemeral=True)

        async def announce(guild: BasedGuild):
            if guild.hasPlayChannel():
                await guild.getPlayChannel().send(content=message.content, embed=embed or MISSING)

        await self.GuildsUtilCog.operateOverBasedGuildsAsync(self.broadcast_broadcastMessage.__name__, announce, "", interaction, None, sendSuccess=False, className=type(self).__name__)
        await interaction.edit_original_response(content="Complete! ✅")

#endregion
#region announce channel

    @BasedCog.staticComponentCallback(StaticComponents.Dev_Announce_Broadcast_Embed_Remove_Field_Select)
    async def announce_broadcast_startRemoveField(self, interaction: Interaction, userId: str):
        await self.EmbedEditorCog.startRemoveField(interaction, userId=userId,
                                                    staticComponentId=StaticComponents.Dev_Announce_Broadcast_Embed_Remove_Field_Select,
                                                    makeView=announce_broadcast_editorView,
                                                    endRemoveField=StaticComponents.Dev_Announce_Broadcast_Embed_Remove_Field)


    @BasedCog.staticComponentCallback(StaticComponents.Dev_Announce_Broadcast_Embed_Remove_Field)
    async def announce_broadcast_endRemoveField(self, interaction: Interaction, userId: str):
        await self.EmbedEditorCog.endRemoveField(interaction, userId=userId, staticComponentId=StaticComponents.Dev_Announce_Broadcast_Embed_Remove_Field, makeView=send_editorView)


    @BasedCog.staticComponentCallback(StaticComponents.Dev_Announce_Broadcast_Embed_Edit_Field_Select)
    async def announce_broadcast_startEditField(self, interaction: Interaction, userId: str):
        await self.EmbedEditorCog.startEditField(interaction, userId=userId,
                                                    staticComponentId=StaticComponents.Dev_Announce_Broadcast_Embed_Edit_Field_Select,
                                                    makeView=announce_broadcast_editorView,
                                                    endEditField=StaticComponents.Dev_Announce_Broadcast_Embed_Edit_Field)

    
    @BasedCog.staticComponentCallback(StaticComponents.Dev_Announce_Broadcast_Embed_Edit_Field)
    async def announce_broadcast_endEditField(self, interaction: Interaction, userId: str):
        await self.EmbedEditorCog.endEditField(interaction, userId=userId,
                                                    staticComponentId=StaticComponents.Dev_Announce_Broadcast_Embed_Edit_Field,
                                                    makeView=announce_broadcast_editorView)


    @BasedCog.staticComponentCallback(StaticComponents.Dev_Announce_Broadcast_Embed_Reorder_Fields_Select)
    async def announce_broadcast_startReorderFields(self, interaction: Interaction, userId: str):
        await self.EmbedEditorCog.startReorderFields(interaction, userId=userId,
                                                    staticComponentId=StaticComponents.Dev_Announce_Broadcast_Embed_Reorder_Fields_Select,
                                                    makeView=announce_broadcast_editorView,
                                                    endReorderFields=StaticComponents.Dev_Announce_Broadcast_Embed_Reorder_Fields)

    
    @BasedCog.staticComponentCallback(StaticComponents.Dev_Announce_Broadcast_Embed_Reorder_Fields)
    async def announce_broadcast_endReorderFields(self, interaction: Interaction, userId: str):
        await self.EmbedEditorCog.endReorderFields(interaction, userId=userId,
                                                    staticComponentId=StaticComponents.Dev_Announce_Broadcast_Embed_Reorder_Fields,
                                                    makeView=announce_broadcast_editorView)

    
    @BasedCog.staticComponentCallback(StaticComponents.Dev_Announce_Broadcast_Submit)
    async def announce_broadcast_broadcastMessage(self, interaction: Interaction, userId: str):
        """Send a new copy of `interaction.message` in the play channel of every guild that has one,
        and clear the view from `interaction.message`.
        """
        if userId and interaction.user.id != int(userId):
            return

        message = interaction.message
        if message is None: return
        embed = message.embeds[0] if message.embeds else None
        if embed is not None and lib.discordUtil.embedEmpty(embed):
            embed.description = ZWSP

        await interaction.response.send_message("sending...", ephemeral=True)

        async def announce(guild: BasedGuild):
            if guild.hasAnnounceChannel():
                await guild.getAnnounceChannel().send(content=message.content, embed=embed or MISSING)

        await self.GuildsUtilCog.operateOverBasedGuildsAsync(self.broadcast_broadcastMessage.__name__, announce, "", interaction, None, sendSuccess=False, className=type(self).__name__)
        await interaction.edit_original_response(content="Complete! ✅")

#endregion
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
        
        view = send_editorView(interaction, interaction.user.id, embed=embed)

        if embed is not None:
            if lib.discordUtil.embedEmpty(embed):
                embed.description = ZWSP
            await interaction.followup.send(content=content, embed=embed, ephemeral=True, view=view)
        else:
            await interaction.followup.send(content=content, ephemeral=True, view=view)


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer)
    @app_commands.command(name="broadcast",
                            description="send a message to the playChannel of all guilds that have one.")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_broadcast(self, interaction: Interaction, content: Optional[str] = None, add_embed: bool = False, string_form: Optional[str] = None, channel: PlayOrAnnounceChannel = PlayOrAnnounceChannel.bountyPlay):
        """developer command sending a message to the playChannel of all guilds that have one
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
        
        if channel is PlayOrAnnounceChannel.bountyPlay:
            view = broadcast_editorView(interaction, interaction.user.id, embed=embed)
        else:
            view = announce_broadcast_editorView(interaction, interaction.user.id, embed=embed)

        if embed is not None:
            if lib.discordUtil.embedEmpty(embed):
                embed.description = ZWSP
            await interaction.followup.send(content=content, embed=embed, ephemeral=True, view=view)
        else:
            await interaction.followup.send(content=content, ephemeral=True, view=view)


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer)
    @app_commands.command(name="reset-has-poll",
                            description="Clear a user's 'poll owned' flag")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_reset_has_poll(self, interaction: Interaction, user_id: str = ""):
        """developer command resetting the poll ownership of the calling user, or the specified user if one is given.
        """
        requestedBUser, _, _ = await self.UsersUtilCog.getBasedUserOrAuthor(interaction, user_id)
        if requestedBUser is None: return

        menusRemoved = requestedBUser.removeAllOwnedMenusOfTypeID(OwnedMenuType.poll)
        if menusRemoved:
            await interaction.response.send_message(f"Ownership of {menusRemoved} removed successfuly.", ephemeral=True)
        else:
            await interaction.response.send_message("This user has no polls!", ephemeral=True)


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer)
    @app_commands.command(name="restart-task-scheduler",
                            description="Restart the global task scheduler. This does not block new tasks from being scheduled.")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_restart_task_checker(self, interaction: Interaction):
        """developer command that restarts the global timedtask scheduler
        """
        self.bot.taskScheduler.stopTaskChecking()
        self.bot.taskScheduler.startTaskChecking()
        await interaction.response.send_message(f"✅ Done!", ephemeral=True)


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer)
    @app_commands.command(name="bot-status",
                            description="Send a DM with various debug info about the bot's current status")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_bot_status(self, interaction: Interaction):
        """developer command sending a DM containing various info about the bot's current status
        """
        await interaction.response.defer(ephemeral=True)

        embed = Embed(title="Bot Status", colour=Colour.random())

        embed.add_field(name="Client",          value=f"{self.bot.user} ({self.bot.user.id if self.bot.user is not None else 'Not logged in'})")
        embed.add_field(name="Shutdown Mode",   value=f"{self.bot.shutDownState}")

        embed.add_field(name="HttpClient",
                        value=f"State: {'Closed' if self.bot.httpClient.closed else 'Open'}\n" \
                            + f"Cookies: {len(self.bot.httpClient.cookie_jar)}")

        embed.add_field(name="GitHub",          value=f"Repo: [{self.bot.githubRepo.html_url}]({self.bot.githubRepo.html_url})")
        embed.add_field(name="Shop Refresh TT", value=self.describeTT(botState.shopRefreshTT))

        if self.bot.taskScheduler is None:
            schedulerStr = "null"
        else:
            if len(self.bot.taskScheduler.tasksHeap) == 0:
                nextTaskStr = "No tasks"
            else:
                nextTask = self.bot.taskScheduler.tasksHeap[0]
                nextTaskStr = "- " + self.describeTT(nextTask, sep="\n- ")

            asyncIOLoopStr = f"{'running' if self.bot.taskScheduler.loop.is_running() else 'not running'}/" \
                            + ('closed' if self.bot.taskScheduler.loop.is_closed() else 'not closed')

            if self.bot.taskScheduler.sleepTask is None:
                sleepTaskStr = "None"
            else:
                if self.bot.taskScheduler.sleepTask.done() or self.bot.taskScheduler.sleepTask.cancelled():
                    if e := self.bot.taskScheduler.sleepTask.exception():
                        exceptionStr = str(e)
                    else:
                        exceptionStr = "None"

                    returnStr = "None" if self.bot.taskScheduler.sleepTask.result is None else "Not None"
                else:
                    exceptionStr = "Still executing"
                    returnStr = "Still executing"

                sleepTaskStr = f"{'done' if self.bot.taskScheduler.sleepTask.done() else 'not done'}/" \
                            + f"{'cancelled' if self.bot.taskScheduler.sleepTask.cancelled() else 'not cancelled'}\n" \
                            + f"Exception: {exceptionStr}\nResult: {returnStr}"

            schedulerStr = f"Active: {self.bot.taskScheduler.active}\n" \
                        + f"Asyncio Loop: {asyncIOLoopStr}\n" \
                        + f"Tasks: {len(self.bot.taskScheduler.tasksHeap)}\n" \
                        + f"Next task: {nextTaskStr}\n" \
                        + f"Sleep task: {sleepTaskStr}"

        embed.add_field(name="Task Scheduler", value=schedulerStr, inline=False)

        basedUpdatesCog = cast(Optional["BASEDVersionCog.BASED_VersionCog"], self.bot.get_cog("BASEDVersionCog"))
        if basedUpdatesCog is not None:
            checkingForUpdates = basedUpdatesCog.BASED_updatesCheck.is_running()
            nextUpdateCheckerIteration = None if not checkingForUpdates else basedUpdatesCog.BASED_updatesCheck.next_iteration
        else:
            checkingForUpdates = False
            nextUpdateCheckerIteration = None
            
        newestBASED = await checkForUpdates(self.bot.httpClient)
        nextUpdate = nextUpdateCheck().strftime("%d/%m/%Y, %H:%M:%S") if cfg.BASED_checkForUpdates else "disabled"

        embed.add_field(name="BASED",
                        value=f"Current: {getBASEDVersion().BASED_version}\n Newest: {newestBASED}\n Next check: {nextUpdate}\n- " \
                            + (f"Next checker iteration: {nextUpdateCheckerIteration}" if checkingForUpdates else "Not checking for updates"))

        embed.add_field(name="Text Commands",
                        value=f"Modules: {', '.join(cfg.includedCommandModules)}\n" \
                            + f"Total commands: {sum(len(i) for i in textCommandsDB.commands)}\n"
                                + "\n".join(f"- {level}: {len(commands)}" for level, commands in enumerate(textCommandsDB.commands)),
                        inline=False)

        commandsStr = ""
        for accessLevelName, accessLevel in _accessLevels.items():
            accessLevelCommands = self.bot.helpSectionsForAccessLevel(accessLevel)
            commandsStr += f"\n- {accessLevelName}: {sum(len(category) for category in accessLevelCommands.values())}"

        embed.add_field(name="Slash Commands",
                        value=f"Cogs: {', '.join(self.bot.cogs)}\n" \
                            + f"Total commands: {sum(1 for _ in self.walk_commands())}{commandsStr}",
                        inline=False)

        menuTypeCounts: Dict[Type[reactionMenu.ReactionMenu], int] = {}
        for menu in self.bot.reactionMenusDB.values():
            menuTypeCounts[type(menu)] = menuTypeCounts.get(type(menu), 0) + 1

        embed.add_field(name="Reaction Menus",
                        value=f"{len(self.bot.reactionMenusDB)} Menus\n" \
                            + "\n".join(f"- {menuType.__name__}: {numMenus}" for menuType, numMenus in menuTypeCounts.items()))
        embed.add_field(name="Users",
                        value=f"Guilds: {len(self.bot.guildsDB.guilds)} registered/{len(self.bot.guilds)} total\n" \
                            + f"Users: {len(self.bot.usersDB.users)} Users/0 Depracated Users *(UNIMPLEMENTED)*")

        embed.add_field(name="Logger",
                        value=f"Unsaved logs:\n" \
                            + "\n".join(f"{c.value}: {len(l.values())}" for c, l in self.bot.logger.logs.items() if l))

        embed.add_field(name="DB Save TT",      value=self.describeTT(botState.dbSaveTT))
        embed.add_field(name="Temps Delay TT",  value=self.describeTT(botState.temperatureDecayTT))

        embed.add_field(name="New Bounty Fixed Delta Changed",  value=botState.newBountyFixedDeltaChanged)

        embed.add_field(name="Current Renders",     value=", ".join(botState.currentRenders) if botState.currentRenders else 'Empty')
        embed.add_field(name="System UTC Offset",   value=lib.timeUtil.td_format_noYM(botState.utcOffset) if botState.utcOffset else 'No offset')
                    
        embed.add_field(name="$premium Cooldown End",
                        value='Null TT' if botState.premiumCooldownEnd is None else \
                                botState.premiumCooldownEnd.strftime("%d/%m/%Y, %H:%M:%S"))

        await interaction.user.send(embed=embed)
        await interaction.followup.send("DM sent.", ephemeral=True)


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer)
    @app_commands.command(name="item-status",
                            description="Send a DM with various debug info about the bot's loaded game objects")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_item_status(self, interaction: Interaction):
        """developer command sending a DM containing info about the loaded game objects
        """
        embed = Embed(title="Bot Status", colour=Colour.random())

        embed.add_field(name="Built-in GameObjects",
                        value=lib.stringTyping.matchIndentation([
                            ("`Ships",      f" | {len(bbData.builtInShipData)} data/{len(bbData.shipKeysByTL)} sorted/{sum(len(i) for i in bbData.shipKeysByTL)} sorted (total)`"),
                            ("`Modules",    f" | {len(bbData.builtInModuleData)} data/{len(bbData.builtInModuleObjs)} objs/{len(bbData.moduleObjsByTL)} sorted/{sum(len(i) for i in bbData.moduleObjsByTL)} sorted (total)`"),
                            ("`Weapons",    f" | {len(bbData.builtInWeaponData)} data/{len(bbData.builtInWeaponObjs)} objs/{len(bbData.weaponObjsByTL)} sorted/{sum(len(i) for i in bbData.weaponObjsByTL)} sorted (total)`"),
                            ("`Upgrades",   f" | {len(bbData.builtInUpgradeData)} data/{len(bbData.builtInUpgradeObjs)} objs/{len(bbData.shipUpgradeToolsByUpgrade)} tools`"),
                            ("`Criminals",  f" | {len(bbData.builtInCriminalData)} data/{len(bbData.builtInCriminalObjs)} objs`"),
                            ("`Systems",    f" | {len(bbData.builtInSystemData)} data/{len(bbData.builtInSystemObjs)} objs`"),
                            ("`Turrets",    f" | {len(bbData.builtInTurretData)} data/{len(bbData.builtInTurretObjs)} objs/{len(bbData.turretObjsByTL)} sorted/{sum(len(i) for i in bbData.turretObjsByTL)} sorted (total)`"),
                            ("`Commodities",f" | {len(bbData.builtInCommodityData)} data/{len(bbData.builtInCommodityObjs)} objs`"),
                            ("`Tools",      f" | {len(bbData.builtInToolData)} data/{len(bbData.builtInToolObjs)} objs`"),
                            ("`Secondaries",f" | {len(bbData.builtInSecondariesData)} data/{len(bbData.builtInSecondaryObjs)} objs`"),
                            ("`ShipSkins",  f" | {len(bbData.builtInShipSkinsData)} data/{len(bbData.builtInShipSkins)} objs/{len(bbData.shipSkinToolsBySkin)} tools`"),
                            ("`Medals",     f" | {len(bbData.medalsData)} data/{len(bbData.medalObjs)} objs`"),
                            ("`Crates",     f" | {len(bbData.builtInCrateObjs)} types/{', '.join(f'{t}: {len(v)}' for t, v in bbData.builtInCrateObjs.items())}`")
                        ]))
        
        await interaction.user.send(embed=embed)
        await interaction.response.send_message("DM sent.", ephemeral=True)


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer)
    @app_commands.command(name="guild-status",
                            description="Send a DM with various debug info about the status of a guild")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_guild_status(self, interaction: Interaction, guild_id: str = "here"):
        """developer command sending a DM containing info about the specified guild
        """
        _, bGuild = await self.GuildsUtilCog.guildByIdOrAllOrContext(interaction, guild_id, allowAllGuilds=False)
        if bGuild is None: return

        await interaction.response.defer(ephemeral=True)

        embed = Embed(title="Guild Status", colour=Colour.random())
        
        embed.add_field(name=str(bGuild.id), value=bGuild.dcGuild.name)

        embed.add_field(name="Channels",
                        value=(f"announceChannel: {bGuild.getAnnounceChannel().mention} ({bGuild.getAnnounceChannel().id})\n" if bGuild.hasAnnounceChannel() else f"announceChannel: None\n") \
                        + (f"playChannel: {bGuild.getPlayChannel().mention} ({bGuild.getPlayChannel().id})\n" if bGuild.hasPlayChannel() else f"playChannel: None\n") \
                        + (f"rendersChannel: {bGuild.hasRendersChannel.mention} ({bGuild.hasRendersChannel.id})" if bGuild.hasRendersChannel() else f"rendersChannel: None\n"))

        if bGuild.shopsDisabled:
            shopsStr = "Disabled"
        elif bGuild.divisionShops is None:
            shopsStr = "⚠ Unexpected `None`"
        else:
            shopsStr = "\n".join(f"{divName}: Level {shop.currentTechLevel}" \
                                + f"\n- Ships: {shop.shipsStock.totalItems}\n-  > " \
                                    + ", ".join(s.item.name for s in shop.shipsStock.items.values()) \
                                + f"\n- Weapons: {shop.weaponsStock.totalItems}\n-  > " \
                                    + ", ".join(str(s.count) + "x " + s.item.name for s in shop.weaponsStock.items.values() if shop.weaponsStock.totalItems) \
                                + f"\n- Modules: {shop.modulesStock.totalItems}\n-  > " \
                                    + ", ".join(str(s.count) + "x " + s.item.name for s in shop.modulesStock.items.values() if shop.modulesStock.totalItems) \
                                + f"\n- Turrets: {shop.turretsStock.totalItems}\n-  > " \
                                    + ", ".join(str(s.count) + "x " + s.item.name for s in shop.turretsStock.items.values() if shop.turretsStock.totalItems) \
                                + f"\n- Tools: {shop.toolsStock.totalItems}\n-  > " \
                                    + ", ".join(str(s.count) + "x " + s.item.name for s in shop.toolsStock.items.values() if shop.toolsStock.totalItems)
                                for divName, shop in bGuild.divisionShops.items())

        embed.add_field(name="Shops", value=shopsStr, inline=False)

        if bGuild.bountiesDisabled:
            bountiesStr = "Disabled"
        elif bGuild.bountiesDB is None:
            bountiesStr = "⚠ Unexpected `None`"
        else:
            bountiesStr = "\n".join(f"{nameForDivision(div)}: " \
                                + str(sum(len(i) for i in div.bounties.values()) \
                                    + sum(len(i) for i in div.escapedBounties.values())) \
                                    + " Bounties\n" \
                                + f"temperature: {div.temperature} ({'active' if div.isActive else 'not active'})\n"
                                + f"latest bounty: {'None' if div.latestBounty is None else div.latestBounty.criminal.name}\n"
                                + f"Active: {sum(len(i) for i in div.bounties.values())}\n-  > " \
                                    + ", ".join(", ".join(d.criminal.name for d in s.values()) for s in div.bounties.values() if any(s.values())) \
                                + f"\nEscaped: {sum(len(i) for i in div.escapedBounties.values())}\n-  > " \
                                    + ", ".join(", ".join(d.criminal.name for d in s.values()) for s in div.escapedBounties.values() if any(s.values())) \
                                for div in bGuild.bountiesDB.divisions.values())

        embed.add_field(name="Bounties", value=bountiesStr, inline=False)

        if bGuild.bountiesDisabled:
            newBountyTTsStr = "Disabled"
        elif bGuild.bountiesDB is None:
            newBountyTTsStr = "⚠ Unexpected `None` bountiesDB"
        else:
            newBountyTTsStr = "\n".join(f"{nameForDivision(div)}: \n- " \
                                + self.describeTT(div.newBountyTT, sep="\n- ") \
                                for div in bGuild.bountiesDB.divisions.values())

        embed.add_field(name="New Bounty TTs", value=newBountyTTsStr, inline=False)
        
        if bGuild.alertRoles:
            alertRolesStr = "\n".join(f"{name}: <@&{roleId}> ({roleId})" if roleId != -1 else f"{name}: None" \
                                        for name, roleId in bGuild.alertRoles.items())
        else:
            alertRolesStr = "None"

        embed.add_field(name="Alert Roles", value=alertRolesStr)

        if bGuild.bountiesDisabled:
            bountyBoardChannelsStr = "Bounties disabled"
        elif bGuild.bountiesDB is None:
            bountyBoardChannelsStr = "⚠ Unexpected `None` bountiesDB"
        else:
            if not bGuild.hasBountyBoardChannels:
                bountyBoardChannelsStr = "BBCs disabled"
            else:
                bountyBoardChannelsStr = ""

        if bGuild.bountiesDB and any(div.bountyBoardChannel for div in bGuild.bountiesDB.divisions.values()):
            bountyBoardChannelsStr += "\n- " \
                + "\n- ".join(f"{nameForDivision(div)}: {div.bountyBoardChannel.channel.mention} ({div.bountyBoardChannel.channel.id})"
                            + (("\n-  > " + "\n-  > ".join(f"[{c.name}]({m.jump_url})" for c, m in div.bountyBoardChannel.bountyMessages.items())) \
                                if div.bountyBoardChannel.bountyMessages else "") \
                            for div in bGuild.bountiesDB.divisions.values() if div.bountyBoardChannel)
        
        embed.add_field(name="BountyBoardChannels", value=bountyBoardChannelsStr)
        embed.add_field(name="Role Menus",          value=str(bGuild.ownedRoleMenus))

        if bGuild.bountiesDisabled:
            bountyAlertRolesStr = "Bounties disabled"
        elif bGuild.bountiesDB is None:
            bountyAlertRolesStr = "⚠ Unexpected `None` bountiesDB"
        else:
            if not bGuild.hasBountyAlertRoles:
                bountyAlertRolesStr = "Disabled"
            else:
                bountyAlertRolesStr = ""

        if bGuild.bountiesDB and any(div.alertRoleID != -1 for div in bGuild.bountiesDB.divisions.values()):
            bountyAlertRolesStr += "\n" \
                + "\n".join(f"{nameForDivision(div)}: <@&{div.alertRoleID}> ({div.alertRoleID})" if div.alertRoleID != -1 else \
                    f"{nameForDivision(div)}: None" for div in bGuild.bountiesDB.divisions.values())
        
        embed.add_field(name="Bounty Alert Roles", value=bountyAlertRolesStr)
        
        await interaction.user.send(embed=embed)
        await interaction.followup.send("DM sent.", ephemeral=True)


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer)
    @app_commands.command(name="user-status",
                            description="Send a DM with various debug info about the status of a user")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_user_status(self, interaction: Interaction, user_id: str = ""):
        """developer command sending a DM containing info about the specified user
        """
        bUser, _, _ = await self.UsersUtilCog.getBasedUserOrAuthor(interaction, user_id)
        if bUser is None: return

        await interaction.response.defer(ephemeral=True)
        dcUser = self.bot.get_user(bUser.id) or await self.bot.tryFetchUser(bUser.id)
        embed = Embed(title="User Status", colour=Colour.random())

        embed.add_field(name=bUser.id,      value=str(dcUser) if dcUser is not None else "Unknown")
        embed.add_field(name="Credits",     value=f"Current: {bUser.credits}\nlifetimeBountyCreditsWon: {bUser.lifetimeBountyCreditsWon}")
        embed.add_field(name="Bounty Wins", value=str(bUser.bountyWins))
        
        embed.add_field(name="$check Cooldown", value=datetime.utcfromtimestamp(bUser.bountyCooldownEnd).strftime("%d/%m/%Y, %H:%M:%S"))
        embed.add_field(name="Systems Checked", value=str(bUser.systemsChecked))

        shipStr = f"{bUser.activeShip.name}\nNickname: {bUser.activeShip.nickname if bUser.activeShip.hasNickname else ''}\n" \
                + f"Armour: {bUser.activeShip.armour}\n" \
                + f"Cargo: {bUser.activeShip.cargo}\n" \
                + f"Handling: {bUser.activeShip.handling}\n" \
                + f"Max secondaries: {bUser.activeShip.maxSecondaries}\n" \
                + f"Primaries: {len(bUser.activeShip.weapons)}/{bUser.activeShip.maxPrimaries}:\n" \
                    + ((f"- " + ", ".join(i.name for i in bUser.activeShip.weapons) + "\n") if bUser.activeShip.weapons else '') \
                + f"Modules: {len(bUser.activeShip.modules)}/{bUser.activeShip.maxModules}:\n" \
                    + ((f"- " + ", ".join(i.name for i in bUser.activeShip.modules) + "\n") if bUser.activeShip.modules else '') \
                + f"Turrets: {len(bUser.activeShip.turrets)}/{bUser.activeShip.maxTurrets}:\n" \
                    + ((f"- " + ", ".join(i.name for i in bUser.activeShip.turrets) + "\n") if bUser.activeShip.turrets else '') \
                + f"Upgrades: " + ", ".join(i.name for i in bUser.activeShip.upgradesApplied) + "\n" \
                + f"Skin: " + (bUser.activeShip.skin.name if bUser.activeShip.skin is not None else 'None')

        embed.add_field(name="Active Ship", value=shipStr)
        
        embed.add_field(name="Ships",   value=f"Total: {bUser.inactiveShips.totalItems}\n-  > " \
                    + ", ".join(s.item.name for s in bUser.inactiveShips.items.values()))
        
        embed.add_field(name="Weapons", value=f"Total: {bUser.inactiveWeapons.totalItems}\n-  > " \
            + ", ".join(str(s.count) + "x " + s.item.name for s in bUser.inactiveWeapons.items.values() if bUser.inactiveWeapons.totalItems))
        embed.add_field(name="Modules", value=f"Total: {bUser.inactiveModules.totalItems}\n-  > " \
            + ", ".join(str(s.count) + "x " + s.item.name for s in bUser.inactiveModules.items.values() if bUser.inactiveModules.totalItems))
        embed.add_field(name="Turrets", value=f"Total: {bUser.inactiveTurrets.totalItems}\n-  > " \
            + ", ".join(str(s.count) + "x " + s.item.name for s in bUser.inactiveTurrets.items.values() if bUser.inactiveTurrets.totalItems))
        embed.add_field(name="Tools",   value=f"Total: {bUser.inactiveTools.totalItems}\n-  > " \
            + ", ".join(str(s.count) + "x " + s.item.name for s in bUser.inactiveTools.items.values() if bUser.inactiveTools.totalItems))

        embed.add_field(name="Duel Requests", value="\n".join(f"{target.id}: {request.stakes}" for target, request in bUser.duelRequests.items()) if bUser.duelRequests else "None")
        embed.add_field(name="Duels", value=f"Wins: {bUser.duelWins}\nLosses: {bUser.duelLosses}\nCredits won: {bUser.duelCreditsWins}\nCredits lost: {bUser.duelCreditsLosses}")
        
        if bUser.hasHomeGuild() and (homeGuild := botState.client.guildsDB.getGuild(bUser.homeGuildID)):
            if dcUser is None:
                userAlertsStr = "States unknown, dcUser unavailable.\n" + ", ".join(t.__name__ for t in bUser.userAlerts)
            else:
                userAlertsStr = "\n".join(f"{t.__name__}: {a.getState(homeGuild.dcGuild, homeGuild, homeGuild.dcGuild.get_member(dcUser.id))}" for t, a in bUser.userAlerts.items())
        else:
            userAlertsStr = "States unknown, no homeguild.\n" + ", ".join(t.__name__ for t in bUser.userAlerts)


        embed.add_field(name="User Alerts", value=userAlertsStr)
        embed.add_field(name="Home Guild",  value=f"{bUser.homeGuildID} - {botState.client.get_guild(bUser.homeGuildID)}")
        embed.add_field(name="$transfer Cooldown", 
                        value=bUser.guildTransferCooldownEnd.strftime("%d/%m/%Y, %H:%M:%S") if bUser.guildTransferCooldownEnd is not None else "None")

        if bUser.kaamo is None:
            kaamoStr = "None"
        else:
            kaamoStr = f"\n- Ships: {bUser.kaamo.shipsStock.totalItems}\n-  > " \
                            + ", ".join(s.item.name for s in bUser.kaamo.shipsStock.items.values()) \
                        + f"\n- Weapons: {bUser.kaamo.weaponsStock.totalItems}\n-  > " \
                            + ", ".join(str(s.count) + "x " + s.item.name for s in bUser.kaamo.weaponsStock.items.values() if bUser.kaamo.weaponsStock.totalItems) \
                        + f"\n- Modules: {bUser.kaamo.modulesStock.totalItems}\n-  > " \
                            + ", ".join(str(s.count) + "x " + s.item.name for s in bUser.kaamo.modulesStock.items.values() if bUser.kaamo.modulesStock.totalItems) \
                        + f"\n- Turrets: {bUser.kaamo.turretsStock.totalItems}\n-  > " \
                            + ", ".join(str(s.count) + "x " + s.item.name for s in bUser.kaamo.turretsStock.items.values() if bUser.kaamo.turretsStock.totalItems) \
                        + f"\n- Tools: {bUser.kaamo.toolsStock.totalItems}\n-  > " \
                            + ", ".join(str(s.count) + "x " + s.item.name for s in bUser.kaamo.toolsStock.items.values() if bUser.kaamo.toolsStock.totalItems)

        embed.add_field(name="Kaamo", value=kaamoStr, inline=False)


        if bUser.loma is None:
            lomaStr = "None"
        else:
            lomaStr = f"\n- Ships: {bUser.loma.shipsStock.totalItems}\n-  > " \
                            + ", ".join((s.item.name + (f"*{s.discounts[0].mult}" if s.discounts else "")) for s in bUser.loma.shipsStock.items.values()) \
                        + f"\n- Weapons: {bUser.loma.weaponsStock.totalItems}\n-  > " \
                            + ", ".join((str(s.count) + "x " + s.item.name + (f"*{s.discounts[0].mult}" if s.discounts else "")) for s in bUser.loma.weaponsStock.items.values() if bUser.loma.weaponsStock.totalItems) \
                        + f"\n- Modules: {bUser.loma.modulesStock.totalItems}\n-  > " \
                            + ", ".join((str(s.count) + "x " + s.item.name + (f"*{s.discounts[0].mult}" if s.discounts else "")) for s in bUser.loma.modulesStock.items.values() if bUser.loma.modulesStock.totalItems) \
                        + f"\n- Turrets: {bUser.loma.turretsStock.totalItems}\n-  > " \
                            + ", ".join((str(s.count) + "x " + s.item.name + (f"*{s.discounts[0].mult}" if s.discounts else "")) for s in bUser.loma.turretsStock.items.values() if bUser.loma.turretsStock.totalItems) \
                        + f"\n- Tools: {bUser.loma.toolsStock.totalItems}\n-  > " \
                            + ", ".join((str(s.count) + "x " + s.item.name + (f"*{s.discounts[0].mult}" if s.discounts else "")) for s in bUser.loma.toolsStock.items.values() if bUser.loma.toolsStock.totalItems)

        embed.add_field(name="Loma", value=lomaStr, inline=False)

        embed.add_field(name="Prestiges", value=str(bUser.prestiges))
        embed.add_field(name="Owned Menus", value="\n".join(f"{t}: {', '.join(str(i) for i in m)}" for t, m in bUser.ownedMenus.items()) if bUser.ownedMenus else "None")

        embed.add_field(name="Medals", value=", ".join(i.name for i in bUser.medals) if bUser.medals else "None")
        embed.add_field(name="Classic Mode", value="Enabled" if bUser.classicModeEnabled else "Disabled")

        await interaction.user.send(embed=embed)
        await interaction.followup.send("DM sent.", ephemeral=True)


    @criminalAutoComplete("criminal")
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer)
    @app_commands.command(name="bounty-status",
                            description="Send a DM with various debug info about the status of an active bounty")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_bounty_status(self, interaction: Interaction, criminal: str, guild_id: str = "here"):
        """developer command sending a DM containing info about the specified bounty
        """
        if not await verifyCriminalName(interaction, criminal): return
        _, bGuild = await self.GuildsUtilCog.guildWithBountiesByIdOrAllOrContext(interaction, guild_id, allowAllGuilds=False)
        if bGuild is None: return
        # Casting here because bountiesDB is guaranteed after guildWithBountiesByIdOrAllOrContext
        bountiesDB = cast(BountyDB, bGuild.bountiesDB)

        await interaction.response.defer(ephemeral=True)

        # look up the criminal object
        criminalObj = bbData.builtInCriminalObjs[criminal]

        try:
            b = bountiesDB.getBountyByCrim(criminalObj)
        except KeyError:
            try:
                b = bountiesDB.getEscapedBountyByCrim(criminalObj)
            except KeyError:
                await interaction.followup.send("Bounty is not wanted in this server", ephemeral=True)
                return

        embed = Embed(title="Bounty Status", colour=Colour.random())

        embed.add_field(name="Criminal", value="\n".join([
            f"Name: {b.criminal.name}",
            f"Faction: {b.criminal.faction}",
            f"Wiki: {b.criminal.wiki}",
            f"Is Player: {b.criminal.isPlayer}",
            f"Built-In: {b.criminal.builtIn}",
            f"Is escaped: {b.isEscaped()}"
        ]))

        embed.add_field(name="Stats", value=f"Faction: {b.faction}\nTech level/Difficulty: {b.techLevel}\n" \
                                            + f"Reward: {b.reward}\nReward per check: {b.rewardPerSys}")

        embed.add_field(name="Times", value=f"Issued: {datetime.utcfromtimestamp(b.issueTime).strftime('%d/%m/%Y, %H:%M:%S')}\n" \
                                        + f"ExpiryTT: {self.describeTT(b.expiryTT)}\n" \
                                        + f"RespawnTT: {self.describeTT(b.respawnTT)}")
        
        embed.add_field(name="Route", value="\n".join(f"{s}: " + (f"{botState.client.get_user(u)} ({u})" if u != -1 else "unchecked") for s, u in b.checked.items()))
        embed.add_field(name="Answer", value=b.answer)

        botState.client.logger.log("dev_misc", "dev_cmd_bounty_status",
                            f"Bounty answer revealed to user {interaction.user} ({interaction.user.id}). " \
                            + f"Bounty: {b.criminal.name} in {bGuild.dcGuild} ({bGuild.id})",
                            category=LogCategory.bountiesDB, eventType="CHEAT")

        if b.activeShip is None:
            shipStr = "None"
        else:
            shipStr = f"{b.activeShip.name}\nNickname: {b.activeShip.nickname if b.activeShip.hasNickname else ''}\n" \
                    + f"Armour: {b.activeShip.armour}\n" \
                    + f"Cargo: {b.activeShip.cargo}\n" \
                    + f"Handling: {b.activeShip.handling}\n" \
                    + f"Max secondaries: {b.activeShip.maxSecondaries}\n" \
                    + f"Primaries: {len(b.activeShip.weapons)}/{b.activeShip.maxPrimaries}:\n" \
                        + ((f"- " + ", ".join(i.name for i in b.activeShip.weapons) + "\n") if b.activeShip.weapons else '') \
                    + f"Modules: {len(b.activeShip.modules)}/{b.activeShip.maxModules}:\n" \
                        + ((f"- " + ", ".join(i.name for i in b.activeShip.modules) + "\n") if b.activeShip.modules else '') \
                    + f"Turrets: {len(b.activeShip.turrets)}/{b.activeShip.maxTurrets}:\n" \
                        + ((f"- " + ", ".join(i.name for i in b.activeShip.turrets) + "\n") if b.activeShip.turrets else '') \
                    + f"Upgrades: " + ", ".join(i.name for i in b.activeShip.upgradesApplied) + "\n" \
                    + f"Skin: " + (b.activeShip.skin.name if b.activeShip.skin is not None else 'None')

        embed.add_field(name="Active Ship", value=f"Has ship: {b.hasShip}\n{shipStr}")
        
        await interaction.user.send(embed=embed)
        await interaction.followup.send("DM sent.", ephemeral=True)


    @criminalAutoComplete("criminal")
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer)
    @app_commands.command(name="edit-bounty",
                            description="Edit an active bounty")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_edit_bounty(self, interaction: Interaction, criminal: str, field: BountyEditField, new_value: str, guild_id: str = "here", update_bountyboards: bool = True):
        """developer command editing some data on a bounty
        """
        if not await verifyCriminalName(interaction, criminal): return
        _, bGuild = await self.GuildsUtilCog.guildWithBountiesByIdOrAllOrContext(interaction, guild_id, allowAllGuilds=False)
        if bGuild is None: return
        # Casting here because bountiesDB is guaranteed after guildWithBountiesByIdOrAllOrContext
        bountiesDB = cast(BountyDB, bGuild.bountiesDB)

        # look up the criminal object
        criminalObj = bbData.builtInCriminalObjs[criminal]

        try:
            b = bountiesDB.getBountyByCrim(criminalObj)
        except KeyError:
            try:
                b = bountiesDB.getEscapedBountyByCrim(criminalObj)
            except KeyError:
                await interaction.response.send_message("Bounty is not wanted in this server", ephemeral=True)
                return

        await interaction.response.defer(ephemeral=True)

        if field is field.activeShip:
            oldTL = b.techLevel
            if new_value.lower() in ["null", "none"]:
                if b.hasShip:
                    b.unequipShip()
            else:
                try:
                    shipDict = json.loads(new_value)
                    newShip = shipItem.Ship.deserialize(shipDict)
                except Exception as e:
                    await interaction.followup.send(f"{type(e).__name__} when deserializing new ship: {e}", ephemeral=True)
                    botState.client.logger.log("dev_misc", "dev_cmd_edit_bounty", exception=e, event="")
                    return

                if b.hasShip:
                    b.unequipShip()
                b.equipShip(newShip)
            b.techLevel = oldTL

        elif field is BountyEditField.faction:
            if new_value not in bbData.bountyFactions:
                await interaction.followup.send(f"Unknown faction. This parameter is case sensitive. Possible values:\n{', '.join(bbData.bountyFactions)}", ephemeral=True)
                return
            
            if new_value == b.faction:
                await interaction.followup.send("No change. Writing anyway.", ephemeral=True)
            b.faction = new_value

        elif field is BountyEditField.issueTime:
            try:
                newTime = datetime.utcfromtimestamp(float(new_value))
            except Exception as e:
                await interaction.followup.send(f"{type(e).__name__} error converting timestamp str to datetime: {e}", ephemeral=True)
                botState.client.logger.log("dev_misc", "dev_cmd_edit_bounty", exception=e, event="")
                return

            if newTime == b.issueTime:
                await interaction.followup.send("No change. Writing anyway.", ephemeral=True)
            b.issueTime = newTime.timestamp()

        elif field is BountyEditField.endTime:
            try:
                newTime = datetime.utcfromtimestamp(float(new_value))
            except Exception as e:
                await interaction.followup.send(f"{type(e).__name__} error converting timestamp str to datetime: {e}", ephemeral=True)
                botState.client.logger.log("dev_misc", "dev_cmd_edit_bounty", exception=e, event="")
                return

            if newTime == b.endTime:
                await interaction.followup.send("No change. Writing anyway.", ephemeral=True)
                
            if b.expiryTT is not None:
                b.expiryTT.forceExpire(callExpiryFunc=False)

            if newTime < datetime.utcnow():
                b.expiryTT = None
                await b.expire(dbReload=True)
            else:
                b.expiryTT = TimedTask(datetime.utcnow(), newTime, None, b.expire)
                botState.client.taskScheduler.scheduleTask(b.expiryTT)

            b.endTime = newTime.timestamp()

        elif field is BountyEditField.expired:
            if new_value.lower() == "false":
                newExpired = False
            elif new_value.lower() == "true":
                newExpired = True
            else:
                await interaction.followup.send("Unknown value for expired. Must be boolean.", ephemeral=True)
                return

            if newExpired == b.expired:
                await interaction.followup.send("No change.", ephemeral=True)
                return
            elif newExpired:
                await b.expire()
            else:
                endDT = datetime.utcfromtimestamp(b.endTime)
                if endDT < datetime.utcnow():
                    await interaction.followup.send("bounty expiry time is in the past. Set a new expiry time to unexpire bounty.", ephemeral=True)
                    return
                b.expiryTT = TimedTask(datetime.utcnow(), endDT, None, b.expire)
                botState.client.taskScheduler.scheduleTask(b.expiryTT)
        

        elif field is BountyEditField.route:
            routeSplit = list(map(str.strip, new_value.split(",")))
            if len(routeSplit) == 0:
                await interaction.followup.send("invalid route. Give as a comma-separated list of system names.", ephemeral=True)
                return

            parsedRoute = []
            for s in routeSplit:
                try:
                    syst: solarSystem.SolarSystem = next(i for i in bbData.builtInSystemObjs.values() if i.isCalled(s))
                except StopIteration:
                    await interaction.followup.send(f"Unknown system: '{s}'", ephemeral=True)
                    return
                parsedRoute.append(syst.name)

            if parsedRoute == b.route:
                await interaction.followup.send("No change.", ephemeral=True)
                return

            if b.answer not in parsedRoute:
                b.answer = random.choice(parsedRoute)
                await interaction.followup.send("Answer randomized", ephemeral=True)

            b.route = parsedRoute
            b.checked = {s: b.checked.get(s, -1) for s in parsedRoute}

        elif field is BountyEditField.reward:
            if not lib.stringTyping.isInt(new_value) or int(new_value) < 0:
                await interaction.followup.send(f"Invalid reward: {new_value}", ephemeral=True)
                return
            newReward = int(new_value)
            if newReward == b.reward:
                await interaction.followup.send("No change. Writing anyway.", ephemeral=True)
                
            b.rewardPerSys = newReward // len(b.route)
            b.reward = newReward

        elif field is BountyEditField.rewardPerSys:
            if not lib.stringTyping.isInt(new_value) or int(new_value) < 0:
                await interaction.followup.send(f"Invalid reward per sys: {new_value}", ephemeral=True)
                return
            newReward = int(new_value)
            if newReward == b.reward:
                await interaction.followup.send("No change. Writing anyway.", ephemeral=True)
                
            b.rewardPerSys = newReward
            b.rewardPerSys = newReward * len(b.route)

        elif field is BountyEditField.checked:
            checkedSplit = new_value.split("\n")
            if len(checkedSplit) == 0:
                await interaction.followup.send("invalid checked. Give as a newline-separated list of system names: user ids.", ephemeral=True)
                return

            parsedChecked: Dict[str, int] = {}
            for pair in checkedSplit:
                pairSplit = list(map(str.strip, pair.split(":")))
                if len(pairSplit) != 2:
                    await interaction.followup.send(f"Invalid mapping: '{pair}'. Must be <system>: <user id>", ephemeral=True)
                    return
                s, u = pairSplit
                if not lib.stringTyping.isInt(u) or int(u) == 0 or int(u) < -1:
                    await interaction.followup.send(f"invalid user ID: {u}", ephemeral=True)
                    return
                try:
                    syst = next(i for i in bbData.builtInSystemObjs if i.isCalled(s))
                except StopIteration:
                    await interaction.followup.send(f"Unknown system: '{s}'", ephemeral=True)
                    return
                parsedChecked[syst.name] = int(u)

            if parsedChecked == b.checked:
                await interaction.followup.send("No change.", ephemeral=True)
                return

            b.route = list(parsedChecked.keys())
            b.checked = parsedChecked

            if b.answer not in parsedChecked:
                b.answer = random.choice(b.route)
                await interaction.followup.send("Answer randomized", ephemeral=True)

        elif field is BountyEditField.answer:
            try:
                syst = next(i for i in bbData.builtInSystemObjs.values() if i.isCalled(new_value))
            except StopIteration:
                await interaction.followup.send(f"Unknown system: '{new_value}'", ephemeral=True)
                return

            if syst.name == b.answer:
                await interaction.followup.send("No change.", ephemeral=True)
                return
            elif syst.name not in b.route:
                await interaction.followup.send("that system is not in the bounty's route. cancelled.", ephemeral=True)
                return
            b.answer = syst.name
            locationStr = "DMs" if interaction.guild is None else f"{interaction.guild} ({interaction.guild.id})"
            botState.client.logger.log("dev_misc", "dev_cmd_edit_bounty",
                            f"Bounty answer revealed to user {interaction.user} ({interaction.user.id}). " \
                            + f"Bounty: {b.criminal.name} in {locationStr}",
                            category=LogCategory.bountiesDB, eventType="CHEAT")

        elif field is BountyEditField.techLevel:
            if not lib.stringTyping.isInt(new_value) or int(new_value) < 0 or int(new_value) > cfg.maxTechLevel:
                await interaction.followup.send(f"invalid TL: {new_value}", ephemeral=True)
                return

            newLevel = int(new_value)

            if newLevel == b.techLevel:
                await interaction.followup.send("No change. Writing anyway.", ephemeral=True)

            if newLevel < b.division.minLevel or newLevel > b.division.maxLevel:
                try:
                    newDiv = b.division.owningDB.divisionForLevel(newLevel)
                except KeyError:
                    await interaction.followup.send("tech level is out of division range, but can't find a new division")
                    b.techLevel = newLevel
                else:
                    if b.division.bountyBoardChannel is not None and b.division.bountyBoardChannel.hasMessageForBounty(b):
                        await b.division.bountyBoardChannel.removeBounty(b)
                    
                    if b.isEscaped():
                        b.division.removeEscapedBountyObj(b)
                        b.techLevel = newLevel
                        newDiv._addEscapedBounty(b)
                    else:
                        b.division.removeBountyObj(b)
                        if b.division.bountyBoardChannel is not None:
                            if b.division.isEmpty(includeEscaped=False) and b.division.bountyBoardChannel.noBountiesMessage is None:
                                b.division.bountyBoardChannel.noBountiesMessage = await b.division.bountyBoardChannel._sendNoBountiesMessage()
                            if newDiv.bountyBoardChannel is not None and newDiv.isEmpty(includeEscaped=False) and newDiv.bountyBoardChannel.noBountiesMessage is not None:
                                await newDiv.bountyBoardChannel.noBountiesMessage.delete()
                                newDiv.bountyBoardChannel.noBountiesMessage = None
                        b.techLevel = newLevel
                        newDiv._addBounty(b, dbReload=True)
                        
                    b.division = newDiv
                    await interaction.followup.send("moved division", ephemeral=True)
            else:
                b.techLevel = newLevel


        elif field is BountyEditField.respawnTime:
            try:
                newTime = datetime.utcfromtimestamp(float(new_value))
            except Exception as e:
                await interaction.followup.send(f"{type(e).__name__} error converting timestamp str to datetime: {e}", ephemeral=True)
                botState.client.logger.log("dev_misc", "dev_cmd_edit_bounty", exception=e, event="")
                return

            if b.respawnTT is not None and newTime == b.respawnTT.expiryTime:
                await interaction.followup.send("No change. Writing anyway.", ephemeral=True)
            
            if b.respawnTT is not None:
                b.respawnTT.forceExpire(callExpiryFunc=False)

            respawnTT = TimedTask(expiryDelta=timedelta(minutes=len(b.route)), 
                                            expiryFunction=b._respawn,
                                            rescheduleOnExpiryFuncFailure=True)

            if not b.isEscaped():
                b.escape()
                if b.division.bountyBoardChannel is not None:
                    await bGuild.updateBountyBoardChannel(b, bountyComplete=True)
                    await b.division.bountyBoardChannel.updateEscapedBountiesMessage()

            b.respawnTT = respawnTT
            botState.client.taskScheduler.scheduleTask(b.respawnTT)
            b.endTime = newTime.timestamp()

        else:
            await interaction.followup.send(f"Unknown field: {field.value}")

        await interaction.followup.send("Success!", ephemeral=True)
        if update_bountyboards and b.division.bountyBoardChannel is not None:
            if b.isEscaped():
                await b.division.bountyBoardChannel.updateEscapedBountiesMessage()
                if b.division.bountyBoardChannel.hasMessageForBounty(b):
                    await b.division.bountyBoardChannel.removeBounty(b)
            else:
                if b.division.bountyBoardChannel.hasMessageForBounty(b):
                    await b.division.bountyBoardChannel.updateBountyMessage(b)
                else:
                    await b.division.bountyBoardChannel._sendBountyMsg(b)


    @criminalAutoComplete("criminal")
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer)
    @app_commands.command(name="force-update-listing",
                            description="Force a bounty board channel listing to refresh")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_force_update_listing(self, interaction: Interaction, criminal: str, guild_id: str = "here"):
        """developer command forcing a BBC listing update on a bounty
        """
        if not await verifyCriminalName(interaction, criminal): return
        _, bGuild = await self.GuildsUtilCog.guildWithBountiesByIdOrAllOrContext(interaction, guild_id)

        criminalObj = bbData.builtInCriminalObjs[criminal]

        async def updateCriminalForGuild(guild: BasedGuild):
            if not guild.hasBountyBoardChannels:
                return

            try:
                b = cast(BountyDB, guild.bountiesDB).getBountyByCrim(criminalObj)
            except KeyError:
                try:
                    b = cast(BountyDB, guild.bountiesDB).getEscapedBountyByCrim(criminalObj)
                except KeyError:
                    return
            
            bbc = cast(BountyBoardChannel, b.division.bountyBoardChannel)
            if bbc.hasMessageForBounty(b):
                await bbc.updateBountyMessage(b)
            else:
                await bbc._sendBountyMsg(b)

        await self.GuildsUtilCog.operateOverBasedGuildsAsync(self.dev_cmd_force_update_listing.callback.__name__, updateCriminalForGuild, f"Bountyboard channel listing(s) updated for {criminalObj.name}", interaction, bGuild)


async def setup(bot: client.BasedClient):
    # Casting here because for some reason pyright doesn't think SerializableDiscordObject is a Snowflake,
    # even though it extends discord.Object
    await bot.add_cog(DevMiscCog(bot), guilds=cast(List[Snowflake], cfg.developmentGuilds))
