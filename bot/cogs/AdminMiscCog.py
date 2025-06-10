from typing import List, Optional, Tuple, Union, cast
from enum import Enum
from time import perf_counter

from discord import ClientUser, Colour, Embed, Guild, HTTPException, Member, Message, Reaction, SelectOption, Role, User, app_commands, Interaction, ButtonStyle
from discord.abc import Snowflake
from discord.ui import View, Button, Select

from .. import client
from bot.cfg import cfg
from bot.cfg.cfg import basicAccessLevels
from ..interactions import basedCommand, basedApp
from ..interactions.basedApp import BasedCog
from ..interactions.basedComponent import StaticComponents
from ..userAlerts import userAlerts
from .. import lib
from ..lib.emojis import randomEmoji
from ..reactionMenus.reactionRolePicker import ReactionRolePicker, ReactionRolePickerOption
from .util.EmbedEditorUtil import EMBED_EDIT_TEXT_ARGS_SEPARATOR, AnyEmbedField, interactionErrorString
from .util.transformers import BoolEnableDisable
from ..logging import LogCategory


class GuildConfigSettings(Enum):
    Bounties = "Bounties"
    Shop = "Shops"


class RoleManagerFlag(Enum):
    NoRoles = "ERR-NOROLES"


def roleMenuForInteraction(interaction: Interaction) -> Optional[ReactionRolePicker]:
    if interaction.message is None:
        return None
    menu = cast(client.BasedClient, interaction.client).reactionMenusDB.get(interaction.message.id, None)
    return menu if isinstance(menu, ReactionRolePicker) else None


# roleMenuCreatorView: "EmbedEditorCog.ViewFactoryType"
def roleMenuCreatorView(interaction: Interaction, userId: Optional[Union[int, str]], embed: Optional[Embed] = None, disableAll: bool = False) -> Optional[View]:
    """This will only work for new role menus, as the submit button creates a new message
    A copy will have to be made for updating role menus
    """
    if interaction.guild is None: return None
    view = View()
    _userId = "" if userId is None else str(userId)

    confirmButton = Button(style=ButtonStyle.green, label="done", row=0 if embed is None else 2, disabled=disableAll)
    confirmButton = StaticComponents.Admin_MakeRoleMenu_Submit_New_Menu(confirmButton, args=_userId)
    cancelButton = Button(style=ButtonStyle.red, label="cancel", row=0 if embed is None else 2, disabled=disableAll)
    cancelButton = StaticComponents.Admin_MakeRoleMenu_Cancel_New_Menu(cancelButton, args=_userId)
    view.add_item(cancelButton).add_item(confirmButton)
    if embed is not None:
        editEmbedTextButton = Button(style=ButtonStyle.blurple, label="edit embed text", row=0, disabled=disableAll)
        editEmbedTextButton = StaticComponents.User_Embed_Edit_Text(editEmbedTextButton, args=f"1{EMBED_EDIT_TEXT_ARGS_SEPARATOR}{_userId}")
        view.add_item(editEmbedTextButton)

        editEmbedImagesButton = Button(style=ButtonStyle.blurple, label="edit embed images", row=0, disabled=disableAll)
        editEmbedImagesButton = StaticComponents.User_Embed_Edit_Images(editEmbedImagesButton, args=_userId)
        view.add_item(editEmbedImagesButton)

        # Replacing this with a 'manage roles' selector
        # removeRoleButton = Button(style=ButtonStyle.blurple, label="remove role", row=1, disabled=disableAll)
        # removeRoleButton = StaticComponents.Admin_MakeRoleMenu_Remove_Role_Select(removeRoleButton, args=_userId)
        # view.add_item(removeRoleButton)

        # TODO: This is currently broken
        reorderRolesButton = Button(style=ButtonStyle.blurple, label="reorder roles", row=1, disabled=disableAll)
        reorderRolesButton = StaticComponents.Admin_MakeRoleMenu_Reorder_Roles_Select(reorderRolesButton, args=_userId)
        view.add_item(reorderRolesButton)

        changeEmojiButton = Button(style=ButtonStyle.blurple, label="change emoji", row=1, disabled=disableAll)
        changeEmojiButton = StaticComponents.Admin_MakeRoleMenu_Change_Emoji_Select(changeEmojiButton, args=_userId)
        view.add_item(changeEmojiButton)
        
        refreshManageRolesButton = Button(style=ButtonStyle.blurple, label="refresh roles selector", row=1, disabled=disableAll)
        refreshManageRolesButton = StaticComponents.Admin_MakeRoleMenu_Manage_Roles_Refresh(refreshManageRolesButton, args=_userId)
        view.add_item(refreshManageRolesButton)

        manageRolesSelector = Select(min_values=0, row=3, disabled=disableAll)
        if interaction.guild.roles:
            menu = roleMenuForInteraction(interaction)

            if menu is None:
                alreadySelectedRoleIds = set()
            else:
                alreadySelectedRoleIds = set(o.role.id for o in menu.options.values())

            manageRolesSelector.placeholder = "Manage roles..."
            manageRolesSelector.options = [
                SelectOption(
                    label=role.name,
                    value=str(role.id),
                    default=role.id in alreadySelectedRoleIds
                )
                for role in interaction.guild.roles if role.is_assignable()
            ]
        else:
            manageRolesSelector.placeholder = "No roles"
            manageRolesSelector.options = [
                SelectOption(
                    emoji=cfg.defaultEmojis.error.sendable,
                    label="Error: No assignable roles! Check your roles and click refresh",
                    description="Make sure that I have permission to assign roles, and that your roles are beneath my role",
                    value=RoleManagerFlag.NoRoles.value,
                    default=True
                )
            ]

        manageRolesSelector.max_values = min(20, len(manageRolesSelector.options))
        manageRolesSelector = StaticComponents.Admin_MakeRoleMenu_Manage_Roles(manageRolesSelector, args=_userId)
        view.add_item(manageRolesSelector)
    
    return view


class AdminMiscCog(basedApp.BasedCog):
#region static components

    """These are being replaced with the manage roles selector
    @BasedCog.staticComponentCallback(StaticComponents.Admin_MakeRoleMenu_Remove_Role_Select)
    async def startRemoveRole(self, interaction: Interaction, userId: str):
        if not self.CommonStaticComponentsCog.ensureOwnership(interaction, userId): return
        if interaction.message:
            embed = interaction.message.embeds[0]
            menu = roleMenuForInteraction(interaction)
            if menu is None:
                await interaction.response.send_message(f"{cfg.defaultEmojis.error} This interaction is not valid here. The message is not a role menu.", ephemeral=True)
                return

            if not embed.fields:
                await interaction.response.send_message(cfg.defaultEmojis.cancel + " The menu has no roles!", ephemeral=True)
                return

            view = roleMenuCreatorView(interaction, userId, embed=embed)
            if view:
                for c in view.children:
                    if isinstance(c, Button):
                        c.disabled = True

                fieldSelector = Select(options=[SelectOption(label=f"{i + 1}. {option.name}", value=str(option.role.id)) for i, option in enumerate(menu.options.values())], max_values=min(len(embed.fields), 25))
                fieldSelector = StaticComponents.Admin_MakeRoleMenu_Remove_Role(fieldSelector, args=userId)
                view.add_item(fieldSelector)

            await interaction.response.edit_message(view=view)


    @BasedCog.staticComponentCallback(StaticComponents.Admin_MakeRoleMenu_Remove_Role)
    async def endRemoveRole(self, interaction: Interaction, userId: str):
        if not self.CommonStaticComponentsCog.ensureOwnership(interaction, userId): return
        if embedEditorCog := self.getEmbedEditorCog("endRemoveRole"):
            message = await embedEditorCog.messageForInteraction(interaction, "endRemoveField", StaticComponents.Admin_MakeRoleMenu_Remove_Role)
            if message is None: return
            embed = message.embeds[0]

            view = roleMenuCreatorView(interaction, userId, embed=embed)
            selected: Optional[List[str]] = None if interaction.data is None else interaction.data.get("values", None)

            tasks = lib.discordUtil.BasicScheduler()
            menu = roleMenuForInteraction(interaction)
            if menu is None:
                await interaction.response.send_message(f"{cfg.defaultEmojis.error} This interaction is not valid here. The message is not a role menu.", ephemeral=True)
                return
                
            changed = False

            if not menu.options:
                await interaction.response.send_message(cfg.defaultEmojis.cancel + " The menu has no roles!", ephemeral=True)
            elif not selected:
                await interaction.response.send_message(cfg.defaultEmojis.cancel + " This type of interaction is not valid here.", ephemeral=True)
                self.bot.logger.log(type(self).__name__, "endRemoveField",
                                    "select-based static component triggered for non-select interaction: " \
                                        + interactionErrorString(interaction, StaticComponents.Admin_MakeRoleMenu_Remove_Role),
                                    category=LogCategory.staticComponents, eventType="COMPONENT_NOT_SELECT", interaction=interaction)
            else:
                changed = True
                for roleId in [int(i) for i in selected]:
                    # casting here because field name is guaranteed for fields that already exist in an embed
                    try:
                        option = next(o for o in menu.options.values() if o.role.id == roleId)
                    except StopIteration:
                        await interaction.response.send_message(cfg.defaultEmojis.cancel + " The role could not be removed. Please remove this menu, and create a new one.", ephemeral=True)
                        self.bot.logger.log(type(self).__name__, "endRemoveField",
                                            f"Could not find menu option for selected value '{roleId}': " \
                                                + interactionErrorString(interaction, StaticComponents.Admin_MakeRoleMenu_Remove_Role),
                                            category=LogCategory.staticComponents, eventType="UNKWN_MENU_OPTION", interaction=interaction)
                        return
                    
                    del menu.options[option.emoji]
                    # casting here because role menus can only exist in guilds
                    tasks.add(menu.msg.remove_reaction(option.emoji.sendable, cast(Guild, interaction.guild).me))

            if changed:
                newEmbed = menu.getMenuEmbed()
                if lib.discordUtil.embedEmpty(newEmbed):
                    newEmbed.description = lib.discordUtil.ZWSP
            else:
                newEmbed = embed

            await interaction.response.edit_message(embed=newEmbed, view=view)
    """

    
    # endReorderRoles is currently broken
    @BasedCog.staticComponentCallback(StaticComponents.Admin_MakeRoleMenu_Reorder_Roles_Select)
    async def startReorderRoles(self, interaction: Interaction, userId: str):
        if not self.CommonStaticComponentsCog.ensureOwnership(interaction, userId): return
        raise NotImplementedError() # TODO
        if embedEditorCog := self.getEmbedEditorCog("startReorderRoles"):
            message = await embedEditorCog.messageForInteraction(interaction, "startReorderFields", StaticComponents.Admin_MakeRoleMenu_Reorder_Roles_Select)
            if message is None: return
            embed = message.embeds[0]

            if not embed.fields or len(embed.fields) < 2:
                await interaction.response.send_message(cfg.defaultEmojis.cancel + " The embed must have at least 2 fields!", ephemeral=True)
                return

            view = roleMenuCreatorView(interaction, userId, embed=embed)
            if view:
                for c in view.children:
                    if isinstance(c, Button):
                        c.disabled = True

                fieldSelector = Select(options=[SelectOption(label=f"{i + 1}. {field.name}", value=str(i)) for i, field in enumerate(embed.fields)], max_values=2, min_values=2)
                fieldSelector = StaticComponents.Admin_MakeRoleMenu_Reorder_Roles(fieldSelector, args=userId)
                view.add_item(fieldSelector)

            await interaction.response.edit_message(view=view)


    # This is currently broken
    @BasedCog.staticComponentCallback(StaticComponents.Admin_MakeRoleMenu_Reorder_Roles)
    async def endReorderRoles(self, interaction: Interaction, userId: str):
        if not self.CommonStaticComponentsCog.ensureOwnership(interaction, userId): return
        raise NotImplementedError() # TODO
        if embedEditorCog := self.getEmbedEditorCog("startReorderRoles"):
            message = await embedEditorCog.messageForInteraction(interaction, self.endReorderRoles.__name__, StaticComponents.Admin_MakeRoleMenu_Reorder_Roles)
            if message is None: return
            embed = message.embeds[0]

            view = roleMenuCreatorView(interaction, userId, embed=embed)
            selected: Optional[List[str]] = None if interaction.data is None else interaction.data.get("values", None)

            if not embed.fields or len(embed.fields) < 2:
                await interaction.response.send_message(cfg.defaultEmojis.cancel + " The menu must have at least 2 roles!", ephemeral=True)
                swappedFields: Optional[Tuple[AnyEmbedField, AnyEmbedField]] = None
            elif not selected:
                await interaction.response.send_message(cfg.defaultEmojis.cancel + " This type of interaction is not valid here.", ephemeral=True)
                self.bot.logger.log(type(self).__name__, self.endReorderRoles.__name__,
                                    "select-based static component triggered for non-select interaction: " \
                                        + interactionErrorString(interaction, StaticComponents.Admin_MakeRoleMenu_Reorder_Roles),
                                    category=LogCategory.staticComponents, eventType="COMPONENT_NOT_SELECT", interaction=interaction)
                swappedFields = None
            else:
                if len(selected) != 2:
                    await interaction.response.send_message(cfg.defaultEmojis.cancel + " Please select exactly two roles to swap.", ephemeral=True)
                selectedFieldIndices = (int(selected[0]), int(selected[1]))
                swappedFields = (embed.fields[selectedFieldIndices[0]], embed.fields[selectedFieldIndices[1]])

                embed.set_field_at(selectedFieldIndices[0], name=swappedFields[1].name, value=swappedFields[1].value, inline=swappedFields[1].inline)
                embed.set_field_at(selectedFieldIndices[1], name=swappedFields[0].name, value=swappedFields[0].value, inline=swappedFields[0].inline)

            if lib.discordUtil.embedEmpty(embed):
                embed.description = lib.discordUtil.ZWSP
                    
            await interaction.response.edit_message(embed=embed, view=view)


    @BasedCog.staticComponentCallback(StaticComponents.Admin_MakeRoleMenu_Manage_Roles)
    async def manageRoles(self, interaction: Interaction, userId: str):
        if not self.CommonStaticComponentsCog.ensureOwnership(interaction, userId): return

        if interaction.message is None or interaction.guild is None: return
        menu = self.bot.reactionMenusDB.get(interaction.message.id, None)
        if not isinstance(menu, ReactionRolePicker):
            await interaction.response.send_message(f"{cfg.defaultEmojis.error} This interaction is not valid here. The message is not a role menu.", ephemeral=True)
            return

        embed = interaction.message.embeds[0]

        selectedRaw: Optional[List[str]] = None if interaction.data is None else interaction.data.get("values", None)

        selectedRoles: List[Role] = []
        failed: List[str] = []
        addedEmojis: List[lib.emojis.BasedEmoji] = []
        removedEmojis: List[lib.emojis.BasedEmoji] = []
        
        if selectedRaw is None:
            await interaction.response.send_message(cfg.defaultEmojis.cancel + " This type of interaction is not valid here.", ephemeral=True)
            self.bot.logger.log(type(self).__name__, self.manageRoles.__name__,
                                "select-based static component triggered for non-select interaction: " \
                                    + interactionErrorString(interaction, StaticComponents.Admin_MakeRoleMenu_Manage_Roles),
                                category=LogCategory.staticComponents, eventType="COMPONENT_NOT_SELECT", interaction=interaction)
            return
        else:
            for rawId in selectedRaw:
                if not lib.stringTyping.isInt(rawId):
                    self.bot.logger.log(type(self).__name__, self.manageRoles.__name__,
                                f"Non-int role ID received '{rawId}': " \
                                    + interactionErrorString(interaction, StaticComponents.Admin_MakeRoleMenu_Manage_Roles),
                                category=LogCategory.staticComponents, eventType="ID_NOT_INT", interaction=interaction)
                    failed.append(rawId)
                    continue

                role = interaction.guild.get_role(int(rawId))
                if role is None or not role.is_assignable():
                    failed.append(rawId)
                    continue
                
                selectedRoles.append(role)
                
                if not any(o.role == role for o in menu.options.values()):
                    while (optionEmoji := randomEmoji()) in menu.options: pass
                    menu.options[optionEmoji] = ReactionRolePickerOption(emoji=optionEmoji, role=role, menu=menu)
                    addedEmojis.append(optionEmoji)
            
            removedEmojis = [e for e, o in menu.options.items() if o.role not in selectedRoles]
            for option in removedEmojis:
                del menu.options[option]


        if lib.discordUtil.embedEmpty(embed):
            embed.description = lib.discordUtil.ZWSP
        
        view = roleMenuCreatorView(interaction, userId, embed=embed, disableAll=True)
        # TODO: Why does this think the interaction has already been acknowledged?
        try:
            await interaction.response.edit_message(content=f"{cfg.defaultEmojis.longProcess} Role menu loading..", view=view, embed=None)
        except HTTPException:
            pass

        async def addEmoji(e: lib.emojis.BasedEmoji):
            """This function guarantees that only discord-compatible emojis will be added to the menu, by randomly adding reactions until an emoji is accepted.
            """
            try:
                await cast(Message, interaction.message).add_reaction(e.sendable)
            except HTTPException as ex:
                if ex.code != lib.discordUtil.ApiError.unknown_emoji.value:
                    raise ex
            else:
                return
            
            original = e

            while True:
                while (e := randomEmoji()) in menu.options: pass
                try:
                    await cast(Message, interaction.message).add_reaction(e.sendable)
                except HTTPException as ex:
                    if ex.code != lib.discordUtil.ApiError.unknown_emoji.value:
                        raise ex
                else:
                    break

            menu.options[e] = menu.options[original]
            menu.options[e].emoji = e
            del menu.options[original]

        async def removeEmoji(e: lib.emojis.BasedEmoji):
            try:
                await cast(Message, interaction.message).remove_reaction(e.sendable, cast(ClientUser, self.bot.user))
            except HTTPException:
                pass

        tasks = lib.discordUtil.BasicScheduler()
        for e in addedEmojis:
            tasks.add(addEmoji(e))
        for e in removedEmojis:
            tasks.add(removeEmoji(e))

        await tasks.wait()
        tasks.raiseExceptions()
        
        if view:
            for c in view.children:
                if isinstance(c, (Button, Select)):
                    c.disabled = False

        await interaction.edit_original_response(content=None, view=view, embed=menu.getMenuEmbed())

        if failed:
            await interaction.message.reply("The following roles could not be added. Please try again:",
                                            embed=Embed(description="\n".join(f"<@&{i}>" for i in failed)), ephemeral=True)

    
    @BasedCog.staticComponentCallback(StaticComponents.Admin_MakeRoleMenu_Manage_Roles_Refresh)
    async def refreshManageRolesSelector(self, interaction: Interaction, userId: str):
        if not self.CommonStaticComponentsCog.ensureOwnership(interaction, userId): return
        raise NotImplementedError() # TODO


    @BasedCog.staticComponentCallback(StaticComponents.Admin_MakeRoleMenu_Change_Emoji_Select)
    async def startChangeEmoji(self, interaction: Interaction, userId: str):
        if not self.CommonStaticComponentsCog.ensureOwnership(interaction, userId): return

        if interaction.message is None or interaction.guild is None: return
        menu = roleMenuForInteraction(interaction)
        if menu is None:
            await interaction.response.send_message(f"{cfg.defaultEmojis.error} This interaction is not valid here. The message is not a role menu.", ephemeral=True)
            return

        view = roleMenuCreatorView(interaction, userId, embed=interaction.message.embeds[0])
        if view:
            for c in view.children:
                if isinstance(c, Button):
                    c.disabled = True
                elif isinstance(c, Select):
                    view.remove_item(c)

            emojiSelector = Select(options=[SelectOption(label=option.role.name, value=str(option.role.id)) for option in menu.options.values()])
            emojiSelector = StaticComponents.Admin_MakeRoleMenu_Change_Emoji(emojiSelector, args=userId)
            view.add_item(emojiSelector)

        await interaction.response.edit_message(view=view)

    
    @BasedCog.staticComponentCallback(StaticComponents.Admin_MakeRoleMenu_Change_Emoji)
    async def endChangeEmoji(self, interaction: Interaction, userId: str):
        if not self.CommonStaticComponentsCog.ensureOwnership(interaction, userId): return

        if interaction.message is None or interaction.guild is None: return
        menu = roleMenuForInteraction(interaction)
        if menu is None:
            await interaction.response.send_message(f"{cfg.defaultEmojis.error} This interaction is not valid here. The message is not a role menu.", ephemeral=True)
            return

        selected: Optional[List[str]] = None if interaction.data is None else interaction.data.get("values", None)
        view = roleMenuCreatorView(interaction, userId, embed=interaction.message.embeds[0])

        if not selected:
            errorMsg = cfg.defaultEmojis.cancel + " This type of interaction is not valid here."
            self.bot.logger.log(type(self).__name__, self.endChangeEmoji.__name__,
                                "select-based static component triggered for non-select interaction: " \
                                    + interactionErrorString(interaction, StaticComponents.Admin_MakeRoleMenu_Change_Emoji),
                                category=LogCategory.staticComponents, eventType="COMPONENT_NOT_SELECT", interaction=interaction)
        else:
            rawId = selected[0]
            if not lib.stringTyping.isInt(rawId):
                self.bot.logger.log(type(self).__name__, self.endChangeEmoji.__name__,
                            f"Non-int role ID received '{rawId}': " \
                                + interactionErrorString(interaction, StaticComponents.Admin_MakeRoleMenu_Change_Emoji),
                            category=LogCategory.staticComponents, eventType="ID_NOT_INT", interaction=interaction)
                errorMsg = "That menu option doesn't represent a role!"
            else:
                roleId = int(rawId)
                try:
                    option = next(o for o in menu.options.values() if o.role.id == roleId)
                except StopIteration:
                    errorMsg = "I can't find that role in the menu!"
                else:
                    disabledNoSelects = roleMenuCreatorView(interaction, userId, embed=interaction.message.embeds[0])
                    if disabledNoSelects:
                        for c in disabledNoSelects.children:
                            if isinstance(c, Button):
                                c.disabled = True
                            elif isinstance(c, Select):
                                disabledNoSelects.remove_item(c)

                    await interaction.response.edit_message(view=disabledNoSelects)
                    reactMsg = await interaction.followup.send(f"React with your new emoji, within {lib.timeUtil.td_format_noYM(cfg.timeouts.menuInteractionDefault)}", wait=True)

                    def check(reaction: Reaction, user: Union[Member, User]) -> bool:
                        return reaction.message.id == reactMsg.id and user.id == int(userId)
                    
                    try:
                        reaction, _ = await self.bot.wait_for("reaction_add", check=check, timeout=int(cfg.timeouts.menuInteractionDefault.total_seconds()))
                    except TimeoutError:
                        await interaction.edit_original_response(content=f"~~React with your new emoji, within {lib.timeUtil.td_format_noYM(cfg.timeouts.menuInteractionDefault)}~~\nOut of time!")
                    else:
                        try:
                            newEmoji = lib.emojis.BasedEmoji.fromReaction(reaction.emoji, rejectInvalid=True)
                        except lib.exceptions.UnrecognisedCustomEmoji:
                            await interaction.edit_original_response(content=":x: I can't access that emoji! Please use either a stock emoji, or one from a server that I am a member of.")
                        else:
                            if newEmoji in menu.options:
                                await interaction.edit_original_response(content=":x: That emoji is already in use for another role.")
                            else:
                                menu.options[newEmoji] = option
                                del menu.options[option.emoji]
                                option.emoji = newEmoji
                                await menu.updateMessage(view=view)
                                await reactMsg.delete()
                                return

                    await menu.msg.edit(view=view)
                    return

        await interaction.response.edit_message(view=view)
        if errorMsg is not None:
            await interaction.followup.send(errorMsg, ephemeral=True)

    
    @BasedCog.staticComponentCallback(StaticComponents.Admin_MakeRoleMenu_Submit_New_Menu)
    async def endCreateMenu(self, interaction: Interaction, userId: str):
        if not self.CommonStaticComponentsCog.ensureOwnership(interaction, userId): return
        if interaction.message and (commonStaticComponentsCog := self.getCommonStaticComponentsCog(callingFuncName="endCreatemenu")):
            if await commonStaticComponentsCog.clearViewFromMessage(interaction, userId):
                menu = self.bot.reactionMenusDB[interaction.message.id]
                menuEmbed = interaction.message.embeds[0]
                
                menu.titleTxt = menuEmbed.title or ""
                menu.desc = menuEmbed.description or ""
                menu.col = menuEmbed.color or Colour.blue()
                menu.img = menuEmbed.image.url or ""
                menu.thumb = menuEmbed.thumbnail.url or ""
                menu.icon = menuEmbed.author.icon_url or ""
                menu.authorName = menuEmbed.author.name or ""
                
                await menu.updateMessage()


    @BasedCog.staticComponentCallback(StaticComponents.Admin_MakeRoleMenu_Cancel_New_Menu)
    async def cancelMenu(self, interaction: Interaction, userId: str):
        if not self.CommonStaticComponentsCog.ensureOwnership(interaction, userId): return
        if interaction.message:
            await interaction.response.defer()
            menu = self.bot.reactionMenusDB[interaction.message.id]
            await menu.delete()

#endregion
#region commands

    @basedCommand.basedCommand(accessLevel=basicAccessLevels.serverAdmin)
    @app_commands.command(name="ping",
                            description="Measure the latency between the bot sending a message, and receiving a response from discord.")
    async def admin_cmd_ping(self, interaction: Interaction):
        """admin command testing bot latency.

        :param discord.Message message: the discord message calling the command
        :param str args: ignored
        :param bool isDM: Whether or not the command is being called from a DM channel
        """
        start = perf_counter()
        await interaction.response.send_message("Ping...")
        end = perf_counter()
        duration = (end - start) * 1000
        msg = await interaction.original_response()
        await msg.edit(content='Pong! {:.2f}ms'.format(duration))

    
    @app_commands.guild_only
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.serverAdmin,
                                formattedDesc="Set various settings for how bountybot will function in this server. Currently, " \
                                        + "`setting` can be either 'bounties' or 'shop', and `value` can either " \
                                        + "'enable' or 'disable', all with a few handy aliases. This command is lets you enable " \
                                        + "or disable large amounts of functionality all together.")
    @app_commands.command(name="config",
                            description="Set various settings for how bountybot will function in this server.")
    async def admin_cmd_config(self, interaction: Interaction, setting: GuildConfigSettings, value: BoolEnableDisable):
        """Apply various bountybot configuration settings for the calling guild.
        TODO: Refactor - change this into a UI kind of like the SDB deck master menu
        """
        callingBBGuild = self.bot.guildsDB.fromInteraction(interaction)
        newVal = bool(value)

        act = {
            GuildConfigSettings.Bounties: {True: callingBBGuild.enableBounties, False: callingBBGuild.disableBounties},
            GuildConfigSettings.Shop: {True: callingBBGuild.enableShops, False: callingBBGuild.disableShops}
        }
        check = {
            GuildConfigSettings.Bounties: {True: lambda: callingBBGuild.bountiesDisabled, False: lambda: not callingBBGuild.bountiesDisabled},
            GuildConfigSettings.Shop: {True: lambda: callingBBGuild.shopsDisabled, False: lambda: not callingBBGuild.shopsDisabled}
        }

        if check[setting][newVal]():
            act[setting][newVal]()
            await interaction.response.send_message(f":white_check_mark: {setting.value.title()} are now {value.value.lower()}d on this server!", ephemeral=True)
        else: 
            await interaction.response.send_message(f":x: {setting.value.title()} are already {value.value.lower()}d on this server!", ephemeral=True)


    @app_commands.guild_only
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.serverAdmin,
                                formattedDesc="Remove the specified reaction menu. You can also just delete the message," \
                                            + " if you have permissions.\n" \
                                            + "To get the ID of a reaction menu, enable discord's " \
                                            + "developer mode, right click on the menu, and click Copy ID.")
    @app_commands.command(name="del-reaction-menu",
                            description="Remove the specified reaction menu. Menu IDs are usually shown in the bottom of menus.")
    async def admin_cmd_del_reaction_menu(self, interaction: Interaction, menu_id: str):
        """Force the expiry of the specified reaction menu message, regardless of reaction menu type.
        """
        if not lib.stringTyping.isInt(menu_id):
            await interaction.response.send_message(":x: Invalid `menu_id`! Must be a number. These are usually visible at the bottom of the menu.", ephemeral=True)
            return

        msgID = int(menu_id)
            
        if msgID in self.bot.reactionMenusDB:
            await self.bot.reactionMenusDB[msgID].delete()
            await interaction.response.send_message(":white_check_mark: Menu deleted.", ephemeral=True)
        else:
            await interaction.response.send_message(":x: Unrecognised reaction menu!", ephemeral=True)


    @app_commands.guild_only
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.serverAdmin)
    @app_commands.choices(
        alert_type=[
            app_commands.Choice(name=alertType.userFriendlyName, value=alertId)
            for alertId, alertType in userAlerts.userAlertsIDsTypes.items() \
                if issubclass(alertType, userAlerts.GuildRoleUserAlert)
        ]
    )
    @app_commands.command(name="set-notify-role",
                            description="Set a role to ping when various events occur.")
    async def admin_cmd_set_notify_role(self, interaction: Interaction, alert_type: str, role: Role):
        """For the current guild, set a role to mention when certain events occur.
        """
        requestedBBGuild = self.bot.guildsDB.fromInteraction(interaction)
        alertCls = userAlerts.userAlertsIDsTypes[alert_type]

        requestedBBGuild.setUserAlertRoleID(alert_type, role.id)
        await interaction.response.send_message(":white_check_mark: Role set for " + alertCls.userFriendlyName \
                                                + " notifications!", ephemeral=True)


    @app_commands.guild_only
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.serverAdmin)
    @app_commands.choices(
        alert_type=[
            app_commands.Choice(name=alertType.userFriendlyName, value=alertId)
            for alertId, alertType in userAlerts.userAlertsIDsTypes.items() \
                if issubclass(alertType, userAlerts.GuildRoleUserAlert)
        ]
    )
    @app_commands.command(name="remove-notify-role",
                            description="Disable role pings for various events.")
    async def admin_cmd_remove_notify_role(self, interaction: Interaction, alert_type: str):
        """For the current guild, remove role mentioning when certain events occur.
        """
        requestedBBGuild = self.bot.guildsDB.fromInteraction(interaction)
        alertCls = userAlerts.userAlertsIDsTypes[alert_type]

        requestedBBGuild.removeUserAlertRoleID(alert_type)
        await interaction.response.send_message(":white_check_mark: Role pings disabled for " + alertCls.userFriendlyName \
                                                + " notifications.", ephemeral=True)

    
    @app_commands.guild_only
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.serverAdmin,
                                formattedDesc=f"Automatically create {len(cfg.bountyDivisionNames)} new roles, one for each division. " \
                                            + "When a bounty spawns into a division, that division's notify role is pinged. " \
                                            + "Users can self-assign and self-unassign these roles with the `notify` command. " \
                                            + "Moving the user between roles as they level up is handled automatically. " \
                                            + "Once created, feel free to edit the roles, but please do not delete them, " \
                                            + "and they must remain pingable by the bot.")
    @app_commands.command(name="make-bounty-notify-roles",
                            description=f"Make {len(cfg.bountyDivisionNames)} roles, one for each division, " \
                                        + "which the bot will ping when new bounties are spawned.")
    async def admin_cmd_make_bounty_notify_roles(self, interaction: Interaction):
        """For the current guild, create 10 notify-able roles, one for each user tech level.
        These roles will be used to alert users when new bounties spawn at each tech level.
        """
        # Casting here because message.guild can be none, but this command has AllowDM set to False, so it will never be None
        dcGuild = cast(Guild, interaction.guild)
        requestedBBGuild = self.bot.guildsDB.fromInteraction(interaction)
        if requestedBBGuild.hasBountyAlertRoles:
            await interaction.response.send_message(":x: This server already has new bounty alert roles!", ephemeral=True)
        elif requestedBBGuild.bountiesDisabled:
            await interaction.response.send_message(":x: Bounties are disabled in this server!", ephemeral=True)
        elif not dcGuild.me.guild_permissions.manage_roles:
            await interaction.response.send_message(":x: I do not have the 'Manage Roles' permission in this server!", ephemeral=True)
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            await requestedBBGuild.makeBountyAlertRoles()
            await interaction.followup.send(":white_check_mark: New roles have been created for new bounties notifications!", ephemeral=True)

    
    @app_commands.guild_only
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.serverAdmin)
    @app_commands.command(name="remove-bounty-notify-roles",
                            description="Disable new bounty notifications, and remove all new bounty alert roles from the server.")
    async def admin_cmd_remove_bounty_notify_roles(self, interaction: Interaction):
        """Remove all new bounty alert roles in the calling guild.
        """
        # Casting here because message.guild can be none, but this command has AllowDM set to False, so it will never be None
        dcGuild = cast(Guild, interaction.guild)
        requestedBBGuild = self.bot.guildsDB.fromInteraction(interaction)
        if not requestedBBGuild.hasBountyAlertRoles:
            await interaction.response.send_message(":x: This server does not have new bounty alert roles!", ephemeral=True)
        elif not dcGuild.me.guild_permissions.manage_roles:
            await interaction.response.send_message(":x: I do not have the 'Manage Roles' permission in this server!", ephemeral=True)
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            await requestedBBGuild.deleteBountyAlertRoles()
            await interaction.followup.send(":white_check_mark: New bounties notifications have been disabled, and their roles removed!", ephemeral=True)


    @app_commands.guild_only
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.serverAdmin,
                                formattedDesc="Create a reaction role menu, allowing users to self-assign or remove roles by adding and removing reactions."
                                                f"\nEach server may have a maximum of {cfg.maxRoleMenusPerGuild} role menus active at any one time.")
    @app_commands.command(name="make-role-menu",
                            description="Create a reaction role menu, allowing users to self-assign roles by adding and removing reactions.")
    async def admin_cmd_make_role_menu(self, interaction: Interaction):
        """Create a reaction role menu, allowing users to self-assign or remove roles by adding and removing reactions.
        Each guild may have a maximum of cfg.maxRoleMenusPerGuild role menus active at any one time.

        Reaction menus can be forced to run forever. To do this, specify ALL run time kwargs as 'off'.

        TODO: Support target IDs
        TODO: Implement single choice/grouped roles
        TODO: Change non-expiring menu specification from all kwargs 'off' to a special kwarg 'on'
        """
        # Casting here because this command is decorated with @guild_only
        dcGuild = cast(Guild, interaction.guild)
        if not dcGuild.roles:
            await interaction.response.send_message(f"{cfg.defaultEmojis.cancel} This server has no roles!", ephemeral=True)
            return

        requestedBBGuild = self.bot.guildsDB.fromInteraction(interaction)
        if requestedBBGuild.ownedRoleMenus >= cfg.maxRoleMenusPerGuild:
            await interaction.response.send_message(f":x: This server has reached the maximum number of active role menus ({cfg.maxRoleMenusPerGuild}). Please deactivate one, and then try this command again.", ephemeral=True)
            return
        requestedBBGuild.ownedRoleMenus += 1

        await interaction.response.send_message(f"{cfg.defaultEmojis.longProcess} Loading...")
        menuMsg = await interaction.original_response()

        embed = Embed(description="React to this message to choose your role(s):", title="Role Menu")
        embed.set_footer(text=f"Menu ID: {menuMsg.id}")
        view = roleMenuCreatorView(interaction, interaction.user.id, embed=embed)

        await menuMsg.edit(content=None, embed=embed, view=view)
        menu = ReactionRolePicker(menuMsg, {}, dcGuild, timeout=None)
        self.bot.reactionMenusDB[menuMsg.id] = menu


    @app_commands.guild_only
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.serverAdmin)
    @app_commands.command(name="add-role",
                            description="Add a role to a role menu.")
    async def admin_cmd_add_role_menu_role(self, interaction: Interaction, emoji: str, role: Role, menu_id: str):
        if not lib.stringTyping.isInt(menu_id.strip()):
            await interaction.response.send_message(":x: Invalid `menu_id`! Must be a number. These are usually visible at the bottom of the menu.", ephemeral=True)
            return

        menu = self.bot.reactionMenusDB.get(int(menu_id.strip()), None)

        if not isinstance(menu, ReactionRolePicker):
            await interaction.response.send_message(":x: That message is not a role menu.", ephemeral=True)
            return

        try:
            parsedEmoji = lib.emojis.BasedEmoji.fromStr(emoji.strip())
        except lib.exceptions.UnrecognisedEmojiFormat:
            await interaction.response.send_message(":x: Please give one valid emoji.", ephemeral=True)
            return
        except lib.exceptions.UnrecognisedCustomEmoji:
            await interaction.response.send_message(":x: I can't access that emoji! Please use either a stock emoji, or one from a server that I am a member of.", ephemeral=True)
            return

        if parsedEmoji in menu.options:
            await interaction.response.send_message(":x: That emoji is already in use for another role.", ephemeral=True)
            return
        
        if not role.is_assignable():
            await interaction.response.send_message(f":x: I can't grant the **{role.name}** role!\nMake sure it's below my role in the server roles list.", ephemeral=True)
            return

        menu.options[parsedEmoji] = ReactionRolePickerOption(parsedEmoji, role, menu)
        await menu.msg.add_reaction(parsedEmoji.sendable)
        await menu.updateMessage(noRefreshOptions=True)
        await interaction.response.send_message(":white_check_mark: Role Added!", ephemeral=True)
        

#endregion

async def setup(bot: client.BasedClient):
    await bot.add_cog(AdminMiscCog(bot))
