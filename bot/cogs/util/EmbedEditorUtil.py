from discord.ui import Modal, TextInput
from discord import Interaction, Embed, TextStyle
from discord.utils import MISSING
from typing import Optional, Protocol

from bot.interactions.basedComponent import StaticComponents

EMBED_EDIT_TEXT_ARGS_SEPARATOR = "%"

# I can't get this imported from discord, so I copy-pasted it.
class AnyEmbedField(Protocol):
    name: Optional[str]
    value: Optional[str]
    inline: bool

class EmbedTextParams(Modal):
    authorName: TextInput = TextInput(label="Author name", required=False, max_length=256)
    titleTxt: TextInput = TextInput(label="Title", required=False, max_length=256)
    desc: TextInput = TextInput(label="Description", required=False, style=TextStyle.paragraph, max_length=4000)
    footerText: TextInput = TextInput(label="Footer text", required=False, max_length=2048)
    colour: TextInput = TextInput(label="Colour (hex or RANDOM)", required=False, max_length=8)
    
    def __init__(self, *, title: str = MISSING, timeout: Optional[float] = None, custom_id: str = MISSING,
                    currentEmbed: Optional[Embed] = None):
        super().__init__(title=title, timeout=timeout, custom_id=custom_id)
        if currentEmbed is not None:
            self.titleTxt.default = currentEmbed.title or ""
            self.authorName.default = (currentEmbed.author.name or "") if currentEmbed.author is not None else ""
            self.desc.default = currentEmbed.description or ""
            self.footerText.default = (currentEmbed.footer.text or "") if currentEmbed.footer is not None else ""
            self.colour.default = hex(currentEmbed.colour.value) if currentEmbed.colour is not None else ""

    async def on_submit(self, interaction: Interaction) -> None:
        await interaction.response.defer(thinking=False)

def interactionErrorString(interaction: Interaction, staticComponentId: StaticComponents) -> str:
    return f"static component {'None' if interaction.data is None else interaction.data.get('custom_id', None)} ({staticComponentId.name}), " \
            f"interaction {interaction.id}, " \
            f"type {interaction.type}, " \
            f"user {interaction.user.name if interaction.user is not None else None} " \
                f"({interaction.user.id if interaction.user is not None else None})"