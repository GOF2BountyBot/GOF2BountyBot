import asyncio
from enum import Enum
from io import BytesIO
import os
from typing import Callable, List, Optional, Set, Tuple, Union, cast
import aiohttp
from discord import Colour, Embed, HTTPException, InteractionType, Member, Message, TextChannel, app_commands, Interaction, ButtonStyle, SelectOption, User
import discord
from discord.abc import Messageable
from discord.ui import View, Button, button, select, Select
from PIL import Image

from .. import client, botState, lib
from bot.lib.discordUtil import textChannel
from ..lib import AEPi
from ..lib.timeUtil import td_format_noYM
from ..lib.tempFolder import TempFolder
from bot.cfg import bbData, cfg
from bot.cfg.cfg import basicAccessLevels
from ..interactions import basedCommand
from ..interactions.basedApp import BasedCog
from .util.CommonAutocomplete import shipAutoComplete, ShipKey
from ..shipRenderer import shipRenderer
from ..views.confirmView import ConfirmView
from ..interactions.basedComponent import StaticComponents
from .util.transformers import BoolYesNo
from ..views.cancelView import CancelView
from ..views.viewBase import ViewBase

ROBOT_ICON = "https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/twitter/259/robot_1f916.png"
CWD = os.getcwd()


class DummyScope:
    def __enter__(self): return self
    def __exit__(self, cls, value, traceback): return False


class RendererReservation:
    def __init__(self, ship: str, queue: List[str]) -> None:
        self.ship = ship
        self.queue = queue


    def __enter__(self):
        # TODO: is this needed?
        if self.ship in self.queue:
            raise KeyError("A reservation for this ship already exists")
        if len(self.queue) >= cfg.maxConcurrentRenders:
            raise KeyError("The queue is full")
        self.queue.append(self.ship)
        return self

    
    def __exit__(self, cls, value, traceback):
        try:
            self.queue.remove(self.ship)
        except ValueError:
            pass
        return False


class TextureFormat(Enum):
    JPG = "0"
    AEI_ETC1 = "1"
    AEI_DXT5 = "2"


class ImageResizeMethod(Enum):
    stretch = "0"
    crop = "1"
    cancelled = "2"


class ImageResizeMethodView(ViewBase):
    def __init__(self, *, timeout: Optional[float] = 180):
        super().__init__(timeout=timeout)
        self.result = ImageResizeMethod.cancelled

    
    @button(emoji="↔", style=ButtonStyle.blurple)
    async def stretchButton(self, interaction: Interaction, _: Button):
        self.result = ImageResizeMethod.stretch
        await self.endView(interaction)


    @button(emoji="✂", style=ButtonStyle.primary)
    async def cropButton(self, interaction: Interaction, _: Button):
        self.result = ImageResizeMethod.stretch
        await self.endView(interaction)

    
    @button(emoji="🇽", style=ButtonStyle.red)
    async def cancelButton(self, interaction: Interaction, _: Button):
        self.result = ImageResizeMethod.cancelled
        await self.endView(interaction)


# Unfinished: select-based region selection
# Dynamic updating of options is currently broken... I think sending new selects breaks discord.py's listening because they get new custom IDs
# Might need to make a new class that repeatedly waits for interactions on a view until confirm/select/timeout
# For now I'll just allow anything and provide validation errors
class AutoskinRegionSelectorView(ConfirmView):
    """A view for configuring autoskin, by selecting which additional regions to skin and which regions to disabled
    This view extends ConfirmView, so it will end when submitted, cancelled, or timed out
    """

    def __init__(self, owner: Union[User, Member], ship: str, *, timeout: Optional[float] = 180):
        super().__init__(timeout=timeout, confirmLabel="Submit", confirmRow=3, cancelRow=3, cleanup=None)
        self.ship = ship
        self.owner = owner
        self.skinnedRegions: Set[int] = set()
        self.disabledRegions: Set[int] = set()
        self._updateOptions()


    def _updateOptions(self):
        """Updates the options available in the region selectors with respect to what is currently selected
        """
        regions = bbData.builtInShipData[self.ship]["textureRegions"]
        if regions > len(self.disabledRegions):
            self.skinnedRegionsSelector.options = [
                SelectOption(label=str(i), value=str(i), default=i in self.skinnedRegions)
                for i in range(1, regions+1)
                if i not in self.disabledRegions
            ]
            self.skinnedRegionsSelector.max_values = min(25, len(self.skinnedRegionsSelector.options))
        else:
            self.skinnedRegionsSelector.options = []
            self.skinnedRegionsSelector.disabled = True

        if regions > len(self.skinnedRegions):
            self.disabledRegionsSelector.options = [
                SelectOption(label=str(i), value=str(i), default=i in self.disabledRegions)
                for i in range(1, regions+1)
                if i not in self.skinnedRegions
            ]
            self.disabledRegionsSelector.max_values = min(25, len(self.disabledRegionsSelector.options))
        else:
            self.disabledRegionsSelector.options = []
            self.disabledRegionsSelector.disabled = True


    @select(placeholder="Optional areas to skin...", min_values=0, row=1)
    async def skinnedRegionsSelector(self, interaction: Interaction, selector: Select):
        if interaction.user != self.owner:
            await interaction.response.send_message(f":x: This menu belongs to somebody else.", ephemeral=True)
            return
        self.skinnedRegions = set(int(i) for i in selector.values)
        await interaction.response.defer()
        # self._updateOptions()
        # await interaction.response.edit_message(view=self)


    @select(placeholder="Optional areas to hide...", min_values=0, row=2)
    async def disabledRegionsSelector(self, interaction: Interaction, selector: Select):
        if interaction.user != self.owner:
            await interaction.response.send_message(f":x: This menu belongs to somebody else.", ephemeral=True)
            return
        self.disabledRegions = set(int(i) for i in selector.values)
        await interaction.response.defer()
        # self._updateOptions()
        # await interaction.response.edit_message(view=self)


    # Overriding this from the base class to add validation
    #TODO: remove this once dynamic options updating is fixed
    @button(style=ButtonStyle.green, label="confirm")
    async def confirm(self, interaction: Interaction, b: Button):
        intersection = list(self.disabledRegions.intersection(self.skinnedRegions))
        if intersection:
            regionsStr = (", ".join(str(reg) for reg in intersection[:-1]) + f" and {intersection[-1]} are") if len(intersection) > 1 else f"{intersection[0]} is"
            await interaction.response.send_message(f":x: You can't skin hidden regions!\nRegion{'s' if len(intersection) > 1 else ''} {regionsStr} selected for both hide and reskin.",
                                                    ephemeral=True)
            return
        # I'm casting here because Buttons are actually callable. If I call button.callback, then I get an attribute error 'function has no attribute callback'
        await cast(Callable, super().confirm)(interaction, b)
        await self.endView(interaction)


RENDER_IDENTIFIER_SEPARATOR = "|"

class InvalidRenderIdentifier(Exception):
    pass

class RenderIdentifier:
    def __init__(self, prefix: str, userId: int, guildId: Optional[int], channelId: Optional[int], interactionId: int, ship: str, full: bool, shipModelName: str) -> None:
        self.prefix = prefix
        self.userId = userId
        self.guildId = guildId
        self.channelId = channelId
        self.interactionId = interactionId
        self.ship = ship
        self.full = full
        self.shipModelName = shipModelName
        self.isDm = guildId is None


    def toStr(self) -> str:
        return RENDER_IDENTIFIER_SEPARATOR.join((self.prefix, str(self.userId), str(self.guildId) or "", str(self.channelId) or "", str(self.interactionId), self.ship, "1" if self.full else "0", self.shipModelName))


    @classmethod
    def fromStr(cls, id: str) -> "RenderIdentifier":
        try:
            prefix, userId, guildId, channelId, interactionId, ship, full, shipModelName = id.split(RENDER_IDENTIFIER_SEPARATOR)
        except ValueError as e:
            raise InvalidRenderIdentifier(e)
        return RenderIdentifier(prefix, int(userId), int(guildId) if guildId else None, int(channelId) if channelId else None, int(interactionId), ship, full == "1", shipModelName)


class UserAutoskinCog(BasedCog):
#region static components

    @BasedCog.staticComponentCallback(StaticComponents.User_ConvertTexture_EmbedImage)
    async def getRenderedTextureFromEmbed(self, interaction: Interaction, args: str):
        await interaction.response.defer(thinking=True)

        try:
            format = TextureFormat(args)
        except ValueError:
            self.bot.logger.log(UserAutoskinCog.__name__, UserAutoskinCog.getRenderedTextureFromEmbed.__name__,
                                f"static component args '{args}' specifies unknown texture format '{args[0]}'", interaction=interaction)
            return

        if interaction.message is None or interaction.message.embeds is None or len(interaction.message.embeds) == 0 or interaction.message.embeds[0].image is None or interaction.message.embeds[0].image.url is None:
            await interaction.followup.send("🥴 Sorry, this texture menu is no longer valid.", ephemeral=True)
            self.bot.logger.log(UserAutoskinCog.__name__, UserAutoskinCog.getRenderedTexture.__name__,
                                f"Unable to get message for interaction", interaction=interaction)
            return

        async with self.bot.httpClient.get(interaction.message.embeds[0].image.url) as resp:
            try:
                resp.raise_for_status()
            except aiohttp.ClientResponseError as e:
                await interaction.followup.send("🥴 Sorry, an error occurred while downloading this texture.", ephemeral=True)
                self.bot.logger.log(UserAutoskinCog.__name__, UserAutoskinCog.getRenderedTexture.__name__, f"Failed to download texture from embed: {args}", exception=e, interaction=interaction)
                return

            with BytesIO(await resp.read()) as tex:
                tex.seek(0)
                await self.getRenderedTexture(interaction, format, interaction.message, tex, args)


    @BasedCog.staticComponentCallback(StaticComponents.User_ConvertTexture_RenderLookup)
    async def getRenderedTextureFromMediaServer(self, interaction: Interaction, args: str):
        await interaction.response.defer(thinking=True)

        try:
            format = TextureFormat(args[0])
        except ValueError:
            await interaction.followup.send("🥴 Sorry, this texture menu is no longer valid.", ephemeral=True)
            self.bot.logger.log(UserAutoskinCog.__name__, UserAutoskinCog.getRenderedTexture.__name__,
                                f"static component args '{args}' specifies unknown texture format '{args[0]}'", interaction=interaction)
            return

        try:
            msg = await self.bot.showmeRendersChannel.fetch_message(int(args[1:]))
        except HTTPException as e:
            await interaction.followup.send("🥴 Sorry, this texture was not found.", ephemeral=True)
            self.bot.logger.log(UserAutoskinCog.__name__, UserAutoskinCog.getRenderedTexture.__name__, f"Message not found in renders channel: {args}", exception=e, interaction=interaction)
            return
            
        with BytesIO() as texBytes:
            try:
                await msg.attachments[0].save(texBytes)
            except discord.HTTPException as e:
                await interaction.followup.send("🥴 Sorry, an error occurred while downloading this texture.", ephemeral=True)
                self.bot.logger.log(UserAutoskinCog.__name__, UserAutoskinCog.getRenderedTexture.__name__, f"Failed to download texture: {args}", exception=e, interaction=interaction)
                return
            
            texBytes.seek(0)
            await self.getRenderedTexture(interaction, format, msg, texBytes, args)


    async def getRenderedTexture(self, interaction: Interaction, format: TextureFormat, textureMsg: Message, texture: BytesIO, args: str):
        try:
            renderId = self.deconstructRenderIdentifier(textureMsg.content)
            modelName = ".".join(renderId.shipModelName.split(".")[:-1])
            shipName = renderId.ship
        except InvalidRenderIdentifier:
            modelName = "Skin"
            shipName = ""

        if format == TextureFormat.JPG:
            await interaction.followup.send((f"**{shipName}** skin" if shipName else "Skin") + " generated texture (`JPG`):", file=discord.File(texture, filename=f"{modelName}.jpg"))
            return

        with Image.open(texture) as texImg:
            if format == TextureFormat.AEI_ETC1:
                aei = AEPi.makeAEI(texImg, AEPi.Platform.android)
            else:
                aei = AEPi.makeAEI(texImg, AEPi.Platform.PC)

            with aei:
                await interaction.followup.send((f"**{shipName}** skin" if shipName else "Skin") + f" generated texture (`{format.name}`):", file=discord.File(aei, filename=f"{modelName}_{format.name}.aei"))

#endregion
#region util

    def checkImageAspectRatio(self, image: discord.Attachment, filePath: str) -> bool:
        """Check whether an image is of the correct aspect ratio.
        If it is, it will be scaled up to be square, and `True` returned.
        If it is not, nothing will happen, and `False` will be returned.
        It is intended that in this case, you follow up with `fixImageAspectRatio`.

        The `image` parameter is just provided to avoid loading the image into memory unnecessarily.

        :param image: Attachment referencing the image
        :type image: discord.Attachment
        :param filePath: Path to the image on disk
        :type filePath: str
        :return: `True` if the image is now square, `False` if the aspect ratio is incorrect and must be correct some other way
        :rtype: bool
        """
        if image.width is None or image.height is None:
            raise ValueError("The attachment has no dimensions")
        
        # See if the image is square
        aspectRatioDiff = 0 if image.width == image.height else abs(1 - (image.width / image.height))
        
        # if the dimensions are not "square enough" then we need to ask the user how to handle it
        # otherwize, some light stretching won't be noticeable
        if aspectRatioDiff > cfg.aspectRatioTolerance:
            return False
        
        # TODO: get image dimension requirements from ship texture
        if image.width != 2048 or image.height != 2048:
            # Stretch to the correct size
            with Image.open(filePath) as workingSF:
                with workingSF.resize((2048, 2048)) as resizedSF:
                    resizedSF.save(filePath)
                    
        return True


    async def fixImageAspectRatio(self, skinPath: str, message: discord.Message,
                                    menuMsg: Optional[discord.Message] = None) -> Tuple[bool, discord.Message]:
        """Given a path to an image that is not square, ask the user whether they would like it to be cropped or
        stretched to become square, and perform the correction.
        The user can also cancel the operation entirely, which will return `True`.
        Alongside the `bool` result, the `Message` used for reaction menus is also returned for reuse in other menus.

        :param skinPath: Path to the image on disc
        :type skinPath: str
        :param message: Message that contained the image
        :type message: discord.Message
        :return: True if the operation was cancelled by the user, False if it succeeded to completion, followed by
                the message used for reaction menus
        :rtype: Tuple[bool, discord.Message]
        """
        view = ImageResizeMethodView(timeout=cfg.timeouts.selectImageSizeHandling.total_seconds())
        embed = Embed(colour=Colour.random(),
                        description=f"↔ : Stretch\n\n" + \
                                    f"✂ : Crop\n\n" + \
                                    f"🇽 : Cancel")

        if menuMsg is None:
            menuMsg = await message.reply("Your image is not square, should I crop it or stretch it?",
                                            embed=embed, view=view, mention_author=False)
        else:
            await menuMsg.edit(content="Your image is not square, should I crop it or stretch it?",
                                embed=embed, view=view)

        for child in view.children:
            if isinstance(child, (Button, Select)):
                child.disabled = True

        if await view.wait():
            await view.interaction.response.edit_message(content="🛑 Out of time! Please try this command again.", view=view, embed=None)
            return True, menuMsg
        
        if view.result == ImageResizeMethod.cancelled:
            await view.interaction.response.edit_message(content="🛑 Operation cancelled.", view=view, embed=None)
            return True, menuMsg

        await view.interaction.response.edit_message(view=view)

        with Image.open(skinPath) as workingSF:
            # TODO: get from ship texture
            # side = max(workingSF.width, workingSF.height)
            side = 2048
        
            if view.result == ImageResizeMethod.crop:
                resizedSF = lib.graphics.cropAndScale(workingSF, side, side)
            else:
                resizedSF = workingSF.resize((side, side))

            with resizedSF:
                resizedSF.save(skinPath)

        return False, menuMsg


    async def downloadImage(self, message: Message, fileName: str, folder: TempFolder) -> Optional[str]:
        """Download the file that was attached to `message` into `folder`, calling it `fileName` (plus some extension)

        :param message: The message containing the image
        :type message: Message
        :param fileName: The name to give to the saved file
        :type fileName: str
        :param folder: The folder in which to save the file
        :type folder: TempFolder
        :return: The path to the file, or `None` if the attachment is not an image, or the image could not be downloaded
        :rtype: Optional[str]
        """
        skinFile = message.attachments[0]
        if skinFile.content_type is None or not skinFile.content_type.startswith("image"):
            await message.reply(f":x: Please only attach images! That's a `{skinFile.content_type}`.\n🛑 Render cancelled.")
            return None
        
        with BytesIO() as texBytes:
            try:
                await skinFile.save(texBytes)
            except discord.HTTPException:
                await message.reply(":x: I couldn't download your image. Was it deleted?\n🛑 Render cancelled.")
                return None

            texBytes.seek(0)
            baseTex = Image.open(texBytes)

            if baseTex.mode == "RGBA":
                ext = "png"
                convertedTex = baseTex
                baseTex = DummyScope()
            else:
                convertedTex = baseTex.convert("RGB")
                ext = "jpg"
            
            with baseTex, convertedTex:
                path = os.path.join(folder.folderPath, f"{fileName}.{ext}")
                convertedTex.save(path)
            return path

    
    async def requestSquareImage(self, user: Union[User, Member], trigger: Union[Interaction, Message], friendlyName: str, fileName: str, folder: TempFolder) -> Tuple[Optional[str], Optional[Message]]:
        """As a response to an interaction or message, request a square image. Wait for the image to be provided, download it, and ensure it is square.
        If it is not square, ask the user how to proceed, and rescale the image to be square as necessary.

        If `trigger` is an interaction, it will be responded to, not followed up.

        Returns a tuple containing the path to the file, if one was downloaded, and a message that was used for reaction menus, if any.
        Both of these can be `None`. If the file path is `None`, then the operation was cancelled.

        :param user: The user from whom to request an image
        :type user: Union[User, Member]
        :param trigger: The interaction or message that triggered this request
        :type trigger: Union[Interaction, Message]
        :param friendlyName: The name of the file, to display to users
        :type friendlyName: str
        :param fileName: The actual name to give to the file on disk, without an extension
        :type fileName: str
        :param folder: The folder in which to download the image
        :type folder: TempFolder
        :return: The path to the image (or `None` of the operation was cancelled), and a `Message` that was used for menus (or `None` if no menus were used)
        :rtype: Tuple[Optional[str], Optional[Message]]
        """
        view = CancelView()
        if isinstance(trigger, Interaction):
            try:
                await trigger.response.send_message(f"Please send your image for {friendlyName}," \
                                                    + f" within {td_format_noYM(cfg.timeouts.menuInteractionDefault)}.",
                                                    view=view)
            except Exception as e:
                raise e
            imgRequestMessage = None
        else:
            imgRequestMessage = await trigger.reply(f"Please send your image for {friendlyName}," \
                                                    + f" within {td_format_noYM(cfg.timeouts.menuInteractionDefault)}.",
                                                    view=view, mention_author=False)

        def textureUploadCheck(response: Union[Message, Interaction]) -> bool:
            if isinstance(response, Message):
                return response.author == user and len(response.attachments) > 0
            response = cast(Interaction, response)
            # TODO: I don't check that the interaction was on the message created above! It could be any button with this CustomID.
            return response.user == user and response.type == InteractionType.component \
                and response.data is not None and response.data.get("custom_id", None) == view.cancel.custom_id

        try:
            imgMsg: Union[Interaction, Message]
            imgMsg = await self.bot.multiWaitFor(["message", "interaction"], check=textureUploadCheck,
                                                    timeout=cfg.timeouts.menuInteractionDefault.total_seconds())
        except asyncio.TimeoutError:
            if isinstance(trigger, Interaction):
                await trigger.edit_original_response(content="This menu has now expired, please try the command again.\n🛑 Render cancelled.")
            elif imgRequestMessage is not None:
                await imgRequestMessage.edit(content="This menu has now expired, please try the command again.\n🛑 Render cancelled.")
            else:
                raise RuntimeError("trigger is not an interaction, but no imgRqeuestMessage is present")
            return None, None

        if isinstance(imgMsg, Interaction):
            await imgMsg.response.edit_message(content="🛑 Render cancelled.", view=None)
            return None, None

        result = await self.downloadImage(imgMsg, fileName, folder)
        if result is None:
            return None, None

        menuMsg = None
        correctShape = self.checkImageAspectRatio(imgMsg.attachments[0], result)
        if not correctShape:
            cancelled, menuMsg = await self.fixImageAspectRatio(result, imgMsg, None)
            if cancelled:
                return None, None

        return result, menuMsg
        

    async def collectAutoskinArgs(self, interaction: Interaction, ship: str,
                                    full: bool, res_x: int, res_y: int, numSamples: int,
                                    folder: TempFolder) -> Optional[shipRenderer.AutoskinArgs]:
        """Collect the necessary images from a user to perform a render, possibly with autoskin.
        Will respond to `Interaction`.

        :param interaction: The interaction that triggered this
        :type interaction: Interaction
        :param ship: The name of the ship to render
        :type ship: str
        :param reservation: The renderer reservation for this operation, if any
        :type reservation: Optional[RendererReservation]
        :param full: Whether autoskin will be performed, or the collected base texture will be applied directly
        :type full: bool
        :param res_x: The width of the render
        :type res_x: int
        :param res_y: The height of the render
        :type res_y: int
        :param numSamples: The number of samples for the render
        :type numSamples: int
        :param folder: The folder in which to download textures
        :type folder: TempFolder
        :return: The collected AutoSkinArgs, or `None` if it was cancelled
        :rtype: Optional[shipRenderer.AutoskinArgs]
        """
        shipData = bbData.builtInShipData[ship]
        skinPaths = {}

        path, menuMsg = await self.requestSquareImage(interaction.user, interaction, "the main texture", "0", folder)
        if path is None: return None
        
        skinPaths[0] = path

        if full or shipData["textureRegions"] == 0:
            return shipRenderer.AutoskinArgs(str(interaction.id), shipData["path"], shipData["model"], skinPaths,
                                            [], res_x, res_y, numSamples, full=full)

        view = AutoskinRegionSelectorView(interaction.user, ship, timeout=cfg.timeouts.menuInteractionDefault.total_seconds())
        content = f"This ship has **{shipData['textureRegions']}** optional texture regions. These will appear with the default texture.\n" \
                + "Alternatively, you can use the menus below to hide these regions, or provide new textures for them."
        
        if menuMsg is None:
            menuMsg = await textChannel(interaction).send(content, view=view)
        else:
            await menuMsg.edit(content=content, view=view, embed=None)

        timedOut = await view.wait()
        view.disableAll()

        if timedOut:
            await view.interaction.response.edit_message(content="🛑 Autoskin cancelled - out of time!", embed=None, view=view)
            await menuMsg.delete()
            return None

        if not view.confirmed:
            await view.interaction.response.edit_message(content="🛑 Autoskin cancelled.", embed=None, view=view)
            return None

        await view.interaction.response.edit_message(view=view)

        newMenu = None
        for regionNum in view.skinnedRegions:
            path, newMenu  = await self.requestSquareImage(interaction.user, newMenu or menuMsg,
                                                    f"texture region #{regionNum}",
                                                    str(regionNum), folder)
            if path is None: return None
            skinPaths[regionNum] = path
        
        return shipRenderer.AutoskinArgs(str(interaction.id), shipData["path"], shipData["model"], skinPaths,
                                        list(view.disabledRegions), res_x, res_y, numSamples, full=full)

    
    def constructRenderIdentifier(self, interaction: Interaction, ship: str, rendererArgs: shipRenderer.AutoskinArgs, prefix: str = ""):
        return RenderIdentifier(prefix,
                                interaction.user.id,
                                None if interaction.guild is None else interaction.guild.id,
                                None if interaction.channel is None else interaction.channel.id,
                                interaction.id,
                                ship,
                                rendererArgs.full,
                                rendererArgs.shipModelName)

    
    def deconstructRenderIdentifier(self, id: str) -> RenderIdentifier:
        return RenderIdentifier.fromStr(id)


    async def doAutoSkin(self, interaction: Interaction, channel: Messageable, rendererArgs: shipRenderer.AutoskinArgs, shipName: str, folder: TempFolder, renderIdentifierPrefix: str = ""):
        """Call shipRenderer following a render command.
        If `trigger` is an interaction, it will be responded to, not followed up.

        :param Interaction interaction: The interaction that triggered the render
        :param TextChannel channel: The channel in which to send the results
        :param rendererArgs: The parameters to pass to the renderer
        :type rendererArgs: shipRenderer.AutoskinArgs
        :param renderIdentifierPrefix: Prefix for the render ID, which will be posted to the renders channel (Default ")
        :type renderIdentifierPrefix: str, optional
        """
        waitMsg = await channel.send("🤖 Render started! I'll ping you when I'm done.")

        renderPath = os.path.join(folder.folderPath, f"{interaction.id}-RENDER.png")
        outSkinPath = os.path.join(folder.folderPath, f"{interaction.id}-GENTEX.jpg")

        renderIdentifier = self.constructRenderIdentifier(interaction, shipName, rendererArgs, prefix=renderIdentifierPrefix).toStr()

        try:
            await shipRenderer.renderShip(  renderOutputPath=renderPath,
                                            compositesTexturePath=outSkinPath,
                                            shipPath=rendererArgs.shipPath,
                                            shipModelName=rendererArgs.shipModelName,
                                            textures=rendererArgs.textures,
                                            disabledLayers=rendererArgs.disabledLayers,
                                            res_x=rendererArgs.res_x,
                                            res_y=rendererArgs.res_y,
                                            numSamples=rendererArgs.numSamples,
                                            full=rendererArgs.full)
        except shipRenderer.RenderFailed:
            await waitMsg.reply(f"{interaction.user.mention} 🥺 Render failed! The error has been logged, please try a different ship.")
            argsStr = ", ".join(f'{k}={rendererArgs[k]}' for k in rendererArgs.keys())
            botState.client.logger.log(UserAutoskinCog.__name__, UserAutoskinCog.doAutoSkin.__name__, f"Ship render failed. Identifer: {renderIdentifier} Args: {argsStr}", interaction=interaction)
        else:
            with open(rendererArgs.textures[0] if rendererArgs.full else outSkinPath, "rb") as textureFile:
                textureMsg = await self.bot.showmeRendersChannel.send(renderIdentifier, file=discord.File(textureFile, filename=f"{interaction.id}.png"))

            view = View(timeout=None) \
                .add_item(StaticComponents.User_ConvertTexture_RenderLookup(Button(emoji="🖼", style=ButtonStyle.blurple), f"{TextureFormat.JPG.value}{textureMsg.id}")) \
                .add_item(StaticComponents.User_ConvertTexture_RenderLookup(Button(emoji="🤖", style=ButtonStyle.blurple), f"{TextureFormat.AEI_ETC1.value}{textureMsg.id}")) \
                .add_item(StaticComponents.User_ConvertTexture_RenderLookup(Button(emoji="🖥", style=ButtonStyle.blurple), f"{TextureFormat.AEI_DXT5.value}{textureMsg.id}"))

            renderEmbed = lib.discordUtil.makeEmbed(desc=f"Select a format to get the generated texture file.\n> *🖼 JPG 🤖 AEI (android) 🖥 AEI (PC)*",
                                                    col=discord.Colour.random(),
                                                    img="attachment://render.png",
                                                    authorName="Skin Render Complete!",
                                                    icon=ROBOT_ICON,
                                                    footerTxt=f"Custom skinned {shipName.capitalize()}")

            with open(renderPath, "rb") as renderFile:
                await waitMsg.reply(interaction.user.mention, embed=renderEmbed, view=view, file=discord.File(renderFile, filename="render.png"))

        try:
            os.remove(renderPath)
        except FileNotFoundError:
            pass

        try:
            os.remove(outSkinPath)
        except FileNotFoundError:
            pass
        
#endregion util
#region commands

    @shipAutoComplete()
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="Autoskin")
    @app_commands.describe(
        ship="The ship to render",
        autoskin="Give No to disable skin generation and use your texture as is (defaults to Yes)"
    )
    @app_commands.command(name="render-skin",
                            description="Generate a ship skin, and render it.")
    async def usr_cmd_render(self, interaction: Interaction, ship: ShipKey, autoskin: BoolYesNo = BoolYesNo.Yes):
        """user command rendering an autoskin-generated texture onto a ship model.
        """
        _autoskin = bool(autoskin)
        shipData = bbData.builtInShipData[ship]
        if not shipData["skinnable"]:
            await interaction.response.send_message(":x: That ship is not skinnable!", ephemeral=True)
            return

        if len(botState.currentRenders) >= cfg.maxConcurrentRenders:
            await interaction.response.send_message(":x: My rendering queue is full currently. Please try this command again once someone " \
                                                    + "else's render has completed.", ephemeral=True)
            return

        with RendererReservation(ship, botState.currentRenders) as reservation, TempFolder(str(interaction.id)) as folder:
            rendererArgs = await self.collectAutoskinArgs(interaction, ship, not _autoskin, cfg.skinRenderShowmeResolution[0],
                                                            cfg.skinRenderShowmeResolution[1],
                                                            cfg.skinRenderShowmeSamples, folder)
            if rendererArgs is None:
                return
                
            # Casting here because slash commands can only be used in text channels
            # Fallback on the user, because the interaction channel is None if the channel is DMs
            await self.doAutoSkin(interaction, cast(Optional[TextChannel], interaction.channel) or interaction.user, rendererArgs, ship, folder)


    @shipAutoComplete()
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.user, helpSection="Autoskin")
    @app_commands.describe(
        ship="The ship to generate a texture for",
        autoskin="Give No to disable skin generation and use your texture as is (defaults to Yes)"
    )
    @app_commands.command(name="make-skin-texture",
                            description="Generate a ship skin, and get the generated texture.")
    async def usr_cmd_make_texture(self, interaction: Interaction, ship: ShipKey, autoskin: BoolYesNo = BoolYesNo.Yes):
        """user command generating a texture and returning it.
        """
        _autoskin = bool(autoskin)
        shipData = bbData.builtInShipData[ship]
        if not shipData["skinnable"]:
            await interaction.response.send_message(":x: That ship is not skinnable!", ephemeral=True)
            return

        if len(botState.currentRenders) >= cfg.maxConcurrentRenders:
            await interaction.response.send_message(":x: My rendering queue is full currently. Please try this command again once someone " \
                                                    + "else's render has completed.", ephemeral=True)
            return

        with TempFolder(str(interaction.id)) as folder:
            rendererArgs = await self.collectAutoskinArgs(interaction, ship, not _autoskin, cfg.skinRenderShowmeResolution[0],
                                                            cfg.skinRenderShowmeResolution[1],
                                                            cfg.skinRenderShowmeSamples, folder)
            if rendererArgs is None:
                return

            if _autoskin:
                texPath = os.path.join(folder.folderPath, f"{interaction.id}-GENTEX.jpg")
                shipRenderer.compositeTextures(texPath, shipData["path"], rendererArgs.textures, rendererArgs.disabledLayers)
            else:
                texPath = os.path.join(folder.folderPath, rendererArgs.textures[0])

            renderEmbed = lib.discordUtil.makeEmbed(desc=f"Select a format to get the generated texture file.\n> *🖼 JPG 🤖 AEI (android) 🖥 AEI(PC)*",
                                                    col=discord.Colour.random(),
                                                    img=f"attachment://{interaction.id}.jpg",
                                                    authorName="Texture Generated!",
                                                    icon=ROBOT_ICON,
                                                    footerTxt=f"Custom skinned {ship.capitalize()} texture")

            with open(texPath, "rb") as textureFile:
                textureMsg = await textChannel(interaction).send(interaction.user.mention, file=discord.File(textureFile, filename=f"{interaction.id}.jpg"), embed=renderEmbed)

        view = View(timeout=None) \
            .add_item(StaticComponents.User_ConvertTexture_EmbedImage(Button(emoji="🤖", style=ButtonStyle.blurple), TextureFormat.AEI_ETC1.value)) \
            .add_item(StaticComponents.User_ConvertTexture_EmbedImage(Button(emoji="🖥", style=ButtonStyle.blurple), TextureFormat.AEI_DXT5.value))

        await textureMsg.edit(view=view)

#endregion


async def setup(bot: client.BasedClient):
    await bot.add_cog(UserAutoskinCog(bot))
