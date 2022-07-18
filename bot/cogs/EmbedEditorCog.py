from dataclasses import dataclass
from typing import Optional, Protocol, List, Tuple, cast
from .. import client, lib
from ..lib.discordUtil import ZWSP
from discord import Message, Interaction, Embed, TextStyle, Colour, SelectOption
from discord import HTTPException, ClientException, NotFound
from discord.utils import MISSING
from discord.ui import View, Modal, TextInput, Button, Select
from ..cfg import cfg
from ..interactions.basedApp import BasedCog
from ..interactions.basedComponent import StaticComponents
from ..logging import LogCategory
from typing import List, cast
from discord.abc import Snowflake
from .util.EmbedEditorUtil import EmbedTextParams, EMBED_EDIT_TEXT_ARGS_SEPARATOR, AnyEmbedField, interactionErrorString

EMBED_FIELD_INLINE_DEFAULT = "y"

# Type to represent the callback to create an embed editor view
# The first paramater is the ID of the user that the view is restricted to
# The second parameter is an optional current embed
class ViewFactoryType(Protocol):
    def __call__(self, interaction: Interaction, userId: str, embed: Optional[Embed] = None) -> View: ...


@dataclass
class EmbedField(AnyEmbedField):
    name: Optional[str]
    value: Optional[str]
    inline: bool


class EmbedImageParams(Modal):
    authorIcon: TextInput = TextInput(label="Author icon", required=False, max_length=4000)
    thumb: TextInput = TextInput(label="Thumbnail", required=False, max_length=4000)
    img: TextInput = TextInput(label="Image", required=False, max_length=4000)
    footerIcon: TextInput = TextInput(label="Footer icon", required=False, max_length=4000)
    
    def __init__(self, *, title: str = MISSING, timeout: Optional[float] = None, custom_id: str = MISSING,
                    currentEmbed: Optional[Embed] = None):
        super().__init__(title=title, timeout=timeout, custom_id=custom_id)
        if currentEmbed is not None:
            self.authorIcon.default = (currentEmbed.author.icon_url or "") if currentEmbed.author is not None else ""
            self.thumb.default = (currentEmbed.thumbnail.url or "") if currentEmbed.thumbnail is not None else ""
            self.img.default = (currentEmbed.image.url or "") if currentEmbed.image is not None else ""
            self.footerIcon.default = (currentEmbed.footer.icon_url or "") if currentEmbed.footer is not None else ""
    
    async def on_submit(self, interaction: Interaction) -> None:
        await interaction.response.defer(thinking=False)


class EmbedFieldParams(Modal):
    fieldName = TextInput(label="Feld name", required=False)
    fieldValue = TextInput(label="Field value", required=False, style=TextStyle.paragraph)
    fieldInline = TextInput(label="Inline? (y/n)", required=False, max_length=1, placeholder=EMBED_FIELD_INLINE_DEFAULT)

    def __init__(self, *, title: str = MISSING, timeout: Optional[float] = None, custom_id: str = MISSING,
                        currentField: Optional[AnyEmbedField] = None) -> None:
        super().__init__(title=title, timeout=timeout, custom_id=custom_id)
        if currentField is not None:
            self.fieldName.default = currentField.name if currentField.name != ZWSP else ""
            self.fieldValue.default = currentField.value if currentField.value != ZWSP else ""
            self.fieldInline.default = "y" if currentField.inline else "n"
    
    async def on_submit(self, interaction: Interaction) -> None:
        await interaction.response.defer(thinking=False)


class EmbedEditorCog(BasedCog):
    def __init__(self, bot: client.BasedClient, *args, **kwargs):
        self.bot = bot
        super().__init__(*args, **kwargs)

#region util

    async def messageForInteraction(self, interaction: Interaction, funcName: str, staticComponentId: StaticComponents) -> Optional[Message]:
        """TODO: This appears to acknowledge the interaction"""
        if interaction.message is not None: return interaction.message
        # await interaction.response.defer(thinking=False)
        try:
            message = await interaction.original_message()
        except (HTTPException, ClientException, NotFound) as e:
            self.bot.logger.log(type(self).__name__, funcName,
                                "on-message static component triggered for non-message-based interaction: " \
                                    + interactionErrorString(interaction, staticComponentId),
                                category=LogCategory.staticComponents, eventType="MESSAGE_FETCH_FAIL", exception=e)
            await interaction.response.send_message(cfg.defaultEmojis.cancel + " This type of interaction is not valid here.", ephemeral=True)
            return None

        if not message.embeds:
            await interaction.response.send_message(cfg.defaultEmojis.cancel + " The message has no embed!", ephemeral=True)
            return None
        
        return message

#endregion
#region static components

    @BasedCog.staticComponentCallback(StaticComponents.User_Embed_Add_Field)
    async def addField(self, interaction: Interaction, userId: str) -> Optional[AnyEmbedField]:
        """Add a field to an embed.
        This will return the created field, or `None` if field creation was cancelled for some reason.
        """
        if userId and interaction.user.id != int(userId):
            return

        message = await self.messageForInteraction(interaction, "addField", StaticComponents.User_Embed_Add_Field)
        if message is None: return
        embed = message.embeds[0]

        if len(embed.fields) == 25:
            await interaction.response.send_message(cfg.defaultEmojis.cancel + " Maximum number of fields reached. Please remove one, or edit an existing field.", ephemeral=True)
            return

        modal = EmbedFieldParams(title="Field Parameters")

        await interaction.response.send_modal(modal)
        if await modal.wait(): return
        
        embed.add_field(name=modal.fieldName.value or ZWSP, value=modal.fieldValue.value or ZWSP,
                        inline=(modal.fieldInline.value or EMBED_FIELD_INLINE_DEFAULT).lower() == "y")
        await interaction.edit_original_message(embed=embed)
        return embed.fields[-1]


    async def startRemoveField(self, interaction: Interaction, userId: str, staticComponentId: StaticComponents, makeView: ViewFactoryType, endRemoveField: StaticComponents):
        if userId and interaction.user.id != int(userId):
            return

        message = await self.messageForInteraction(interaction, "startRemoveField", staticComponentId)
        if message is None: return
        embed = message.embeds[0]

        if not embed.fields:
            await interaction.response.send_message(cfg.defaultEmojis.cancel + " The embed has no fields!", ephemeral=True)
            return

        view = makeView(interaction, userId, embed=embed)

        for c in view.children:
            if isinstance(c, Button):
                c.disabled = True

        fieldSelector = Select(options=[SelectOption(label=f"{i + 1}. {field.name}", value=str(i)) for i, field in enumerate(embed.fields)], max_values=min(len(embed.fields), 25))
        fieldSelector = endRemoveField(fieldSelector, args=userId)
        view.add_item(fieldSelector)

        await interaction.response.edit_message(view=view)


    async def endRemoveField(self, interaction: Interaction, userId: str, staticComponentId: StaticComponents, makeView: ViewFactoryType) -> Optional[List[AnyEmbedField]]:
        """Remove any number of fields from an embed.
        `interaction` should be a `select` component interaction. TODO: Genericise
        This will return the removed fields, in the order that they appeared in the embed, or `None` if field removal was cancelled for some reason.
        """
        if userId and interaction.user.id != int(userId):
            return

        message = await self.messageForInteraction(interaction, "endRemoveField", staticComponentId)
        if message is None: return
        embed = message.embeds[0]

        view = makeView(interaction, userId, embed=embed)
        selected: Optional[List[str]] = None if interaction.data is None else interaction.data.get("values", None)

        if not embed.fields:
            await interaction.response.send_message(cfg.defaultEmojis.cancel + " The embed has no fields!", ephemeral=True)
            removedFields: Optional[List[AnyEmbedField]] = None
        elif not selected:
            await interaction.response.send_message(cfg.defaultEmojis.cancel + " This type of interaction is not valid here.", ephemeral=True)
            self.bot.logger.log(type(self).__name__, "endRemoveField",
                                "select-based static component triggered for non-select interaction: " \
                                    + interactionErrorString(interaction, staticComponentId),
                                category=LogCategory.staticComponents, eventType="COMPONENT_NOT_SELECT")
            removedFields = None
        else:
            selectedFieldIndices = sorted([int(i) for i in selected])
            removedFields = [embed.fields[i] for i in selectedFieldIndices]
            for i in selectedFieldIndices[::-1]:
                embed.remove_field(i)

        if lib.discordUtil.embedEmpty(embed):
            embed.description = ZWSP
                
        await interaction.response.edit_message(embed=embed, view=view)
        return removedFields


    async def startEditField(self, interaction: Interaction, userId: str, staticComponentId: StaticComponents, makeView: ViewFactoryType, endEditField: StaticComponents):
        if userId and interaction.user.id != int(userId):
            return

        message = await self.messageForInteraction(interaction, "startEditField", staticComponentId)
        if message is None: return
        embed = message.embeds[0]

        view = makeView(interaction, userId, embed=embed)

        if not embed.fields:
            await interaction.response.send_message("The embed has no fields!", ephemeral=True)
            return

        for c in view.children:
            if isinstance(c, Button):
                c.disabled = True

        fieldSelector: Select = Select(options=[SelectOption(label=f"{i + 1}. {field.name}", value=str(i)) for i, field in enumerate(embed.fields)], max_values=1)

        fieldSelector = endEditField(fieldSelector, args=userId)
        view.add_item(fieldSelector)

        await interaction.response.edit_message(view=view)

    
    async def endEditField(self, interaction: Interaction, userId: str, staticComponentId: StaticComponents, makeView: ViewFactoryType) -> Optional[Tuple[AnyEmbedField, AnyEmbedField]]:
        """Edit a field in an embed.
        `interaction` should be a `select` component interaction. TODO: Genericise
        This will return a tuple (original field, edited field), or `None` if field editing was cancelled for some reason.
        """
        if userId and interaction.user.id != int(userId):
            return

        message = await self.messageForInteraction(interaction, "endEditField", staticComponentId)
        if message is None: return
        embed = message.embeds[0]

        view = makeView(interaction, userId, embed=embed)
        selected: List[str] = [] if interaction.data is None else interaction.data.get("values", [])

        if not embed.fields:
            await interaction.response.send_message("The embed has no fields!", ephemeral=True)
            result: Optional[Tuple[AnyEmbedField, AnyEmbedField]] = None
        elif len(selected) != 1:
            await interaction.response.send_message(cfg.defaultEmojis.cancel + " This type of interaction is not valid here.", ephemeral=True)
            self.bot.logger.log(type(self).__name__, "endEditField",
                                "select-based static component triggered for non-select interaction: " \
                                    + interactionErrorString(interaction, staticComponentId),
                                category=LogCategory.staticComponents, eventType="COMPONENT_NOT_SELECT")
            result = None
        else:
            selectedFieldIndex = int(selected[0])
            field = EmbedField(
                embed.fields[selectedFieldIndex].name,
                embed.fields[selectedFieldIndex].value,
                embed.fields[selectedFieldIndex].inline
            )
            
            modal = EmbedFieldParams(title="Field Parameters")
            if field.name != ZWSP:
                modal.fieldName.default = field.name
            if field.value != ZWSP:
                modal.fieldValue.default = field.value
            modal.fieldInline.default = "y" if field.inline else "n"

            await interaction.response.send_modal(modal)
            if await modal.wait(): view.stop()
        
            embed.set_field_at(selectedFieldIndex, name=modal.fieldName.value or ZWSP, value=modal.fieldValue.value or ZWSP,
                                inline=(modal.fieldInline.value or EMBED_FIELD_INLINE_DEFAULT).lower() == "y")

            result = (field, embed.fields[selectedFieldIndex])

        if lib.discordUtil.embedEmpty(embed):
            embed.description = ZWSP

        await interaction.edit_original_message(embed=embed, view=view)
        return result


    @BasedCog.staticComponentCallback(StaticComponents.User_Embed_Edit_Text)
    async def editEmbedText(self, interaction: Interaction, args: str):
        isReactionMenu, userId = args.split(EMBED_EDIT_TEXT_ARGS_SEPARATOR)
        if userId and interaction.user.id != int(userId):
            return

        message = await self.messageForInteraction(interaction, "editEmbedText", StaticComponents.User_Embed_Edit_Text)
        if message is None: return
        embed = message.embeds[0]

        modal = EmbedTextParams(title="Embed Parameters", currentEmbed=embed)
        if isReactionMenu:
            modal.remove_item(modal.footerText)

        await interaction.response.send_modal(modal)
        if await modal.wait(): return
        
        if modal.titleTxt.value:
            embed.title = modal.titleTxt.value
        else:
            embed.title = None
            
        authorIcon = (embed.author.icon_url or "") if embed.author is not None else ""
        if modal.authorName.value:
            embed.set_author(name=modal.authorName.value, icon_url=authorIcon or None)
        else:
            if authorIcon:
                embed.set_author(name=ZWSP, icon_url=authorIcon)
            else:
                embed.remove_author()

        if modal.desc.value:
            embed.description = modal.desc.value
        else:
            embed.description = None

        footerIcon = (embed.footer.icon_url or "") if embed.footer is not None else ""
        if not isReactionMenu and modal.footerText.value:
            embed.set_footer(text=modal.footerText.value, icon_url=footerIcon or None)
        else:
            if footerIcon:
                embed.set_footer(text=ZWSP, icon_url=footerIcon)
            else:
                embed.remove_footer()

        if modal.colour.value:
            if modal.colour.value.lower() == "random":
                embed.colour = Colour.random()
            else:
                embed.colour = Colour(int(modal.colour.value, base=16))
        else:
            embed.colour = None

        if lib.discordUtil.embedEmpty(embed):
            embed.description = ZWSP
        await interaction.edit_original_message(embed=embed)


    @BasedCog.staticComponentCallback(StaticComponents.User_Embed_Edit_Images)
    async def editEmbedImages(self, interaction: Interaction, userId: str):
        if userId and interaction.user.id != int(userId):
            return

        message = await self.messageForInteraction(interaction, "editEmbedImages", StaticComponents.User_Embed_Edit_Images)
        if message is None: return
        embed = message.embeds[0]

        modal = EmbedImageParams(title="Embed parameters", currentEmbed=embed)
        await interaction.response.send_modal(modal)
        if await modal.wait(): return

        authorName = ("" if embed.author.name in (None, ZWSP) else embed.author.name) if embed.author is not None else ""
        if modal.authorIcon.value:
            embed.set_author(name=authorName or ZWSP, icon_url=modal.authorIcon)
        else:
            if authorName:
                embed.set_author(name=authorName, icon_url=None)
            else:
                embed.remove_author()

        embed.set_thumbnail(url=modal.thumb.value or None)
        embed.set_image(url=modal.img.value or None)

        footerText = ("" if embed.footer.text in (None, ZWSP) else embed.footer.text) if embed.footer is not None else ""
        if modal.footerIcon.value:
            embed.set_footer(text=footerText or ZWSP, icon_url=modal.footerIcon)
        else:
            if footerText:
                embed.set_footer(text=footerText, icon_url=None)
            else:
                embed.remove_footer()

        if lib.discordUtil.embedEmpty(embed):
            embed.description = ZWSP
        await interaction.edit_original_message(embed=embed)


    async def startReorderFields(self, interaction: Interaction, userId: str, staticComponentId: StaticComponents, makeView: ViewFactoryType, endReorderFields: StaticComponents):
        if userId and interaction.user.id != int(userId):
            return

        message = await self.messageForInteraction(interaction, "startReorderFields", staticComponentId)
        if message is None: return
        embed = message.embeds[0]

        if not embed.fields or len(embed.fields) < 2:
            await interaction.response.send_message(cfg.defaultEmojis.cancel + " The embed must have at least 2 fields!", ephemeral=True)
            return

        view = makeView(interaction, userId, embed=embed)

        for c in view.children:
            if isinstance(c, Button):
                c.disabled = True

        fieldSelector = Select(options=[SelectOption(label=f"{i + 1}. {field.name}", value=str(i)) for i, field in enumerate(embed.fields)], max_values=2, min_values=2)
        fieldSelector = endReorderFields(fieldSelector, args=userId)
        view.add_item(fieldSelector)

        await interaction.response.edit_message(view=view)


    async def endReorderFields(self, interaction: Interaction, userId: str, staticComponentId: StaticComponents, makeView: ViewFactoryType) -> Optional[Tuple[AnyEmbedField, AnyEmbedField]]:
        """Swap the position of any two fields in an embed.
        `interaction` should be a `select` component interaction. TODO: Genericise
        This will return the swapped fields, in no guaranteed order, or `None` if field reodering was cancelled for some reason.
        """
        if userId and interaction.user.id != int(userId):
            return

        message = await self.messageForInteraction(interaction, "endReorderFields", staticComponentId)
        if message is None: return
        embed = message.embeds[0]

        view = makeView(interaction, userId, embed=embed)
        selected: Optional[List[str]] = None if interaction.data is None else interaction.data.get("values", None)

        if not embed.fields or len(embed.fields) < 2:
            await interaction.response.send_message(cfg.defaultEmojis.cancel + " The embed must have at least 2 fields!", ephemeral=True)
            swappedFields: Optional[Tuple[AnyEmbedField, AnyEmbedField]] = None
        elif not selected:
            await interaction.response.send_message(cfg.defaultEmojis.cancel + " This type of interaction is not valid here.", ephemeral=True)
            self.bot.logger.log(type(self).__name__, "endReorderFields",
                                "select-based static component triggered for non-select interaction: " \
                                    + interactionErrorString(interaction, staticComponentId),
                                category=LogCategory.staticComponents, eventType="COMPONENT_NOT_SELECT")
            swappedFields = None
        else:
            if len(selected) != 2:
                await interaction.response.send_message(cfg.defaultEmojis.cancel + " Please select exactly two fields to swap.", ephemeral=True)
            selectedFieldIndices = (int(selected[0]), int(selected[1]))
            swappedFields = (embed.fields[selectedFieldIndices[0]], embed.fields[selectedFieldIndices[1]])

            embed.set_field_at(selectedFieldIndices[0], name=swappedFields[1].name, value=swappedFields[1].value, inline=swappedFields[1].inline)
            embed.set_field_at(selectedFieldIndices[1], name=swappedFields[0].name, value=swappedFields[0].value, inline=swappedFields[0].inline)

        if lib.discordUtil.embedEmpty(embed):
            embed.description = ZWSP
                
        await interaction.response.edit_message(embed=embed, view=view)
        return swappedFields


#endregion


async def setup(bot: client.BasedClient):
    # Casting here because for some reason pyright doesn't think SerializableDiscordObject is a Snowflake,
    # even though it extends discord.Object
    await bot.add_cog(EmbedEditorCog(bot), guilds=cast(List[Snowflake], cfg.developmentGuilds))
