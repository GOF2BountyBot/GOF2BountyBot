from typing import Any, List, Dict, Literal, cast, overload, ContextManager

from PIL import Image, ImageChops, ImageOps
import subprocess
import os
from os.path import join
import pathlib
import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, fields
from contextlib import nullcontext

from ..database.constants import ShipSkinRegion, ShipSkinMethod
from ..assetManager import Asset, AssetType
from . import constants

SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))
RENDER_ARGS_PATH = join(SCRIPT_PATH, "render_vars")
BLENDER_FILE_PATH = join(SCRIPT_PATH, "cube.blend")
BLENDER_SCRIPT_PATH = join(SCRIPT_PATH, "_render.py")


class RenderFailed(Exception):
    pass


class InvalidRenderConfiguration(Exception):
    def __init__(self, message: str, *args: object) -> None:
        super().__init__(message, *args)


##### UTIL FUNCTIONS #####


def shipAutoskinMaskFileName(layer: ShipSkinRegion):
    return f"{layer.value}.jpg"


def trim(im: Image.Image):
    """You must `with` the result of this function.*
    
    Crop image to content, written by neouyghur: https://stackoverflow.com/a/48605963/11754606

    :param Image im: The image to crop
    :return: im, with all surrounding empty space removed
    :rtype: Image
    """
    bg = Image.new(im.mode, im.size, im.getpixel((0, 0)))
    diff = ImageChops.difference(im, bg)
    diff = ImageChops.add(diff, diff, 2.0, -100)
    bbox = diff.getbbox()
    if bbox:
        return im.crop(bbox)
    return nullcontext(im)


def ensureMode(tex: Image.Image, mode="RGBA") -> ContextManager[Image.Image]:
    """*You must `with` the result of this function.*
    
    Ensure the passed image is in a given mode. If it is not, convert it.
    https://pillow.readthedocs.io/en/stable/handbook/concepts.html#concept-modes

    :param Image tex: The image whose mode to check
    :param str mode: The mode to ensure and convert to if needed
    :return: tex if it is of the given mode. tex converted to mode otherwise.
    :rtype: Image
    """
    return nullcontext(tex) if tex.mode == mode else tex.convert(mode)


async def compositeTextures(shipId: int, outTexPath: str, diffusePaths: Dict[ShipSkinRegion, str], diffuseDisabled: List[ShipSkinRegion]):
    """Combine a list of textures into a single image, with respect to masks provided in shipPath.

    :param int shipId: The ID of the ShipSpec whose texture components to use.
    :param str outTexPath: Path to which the resulting texture should be saved, including file name and extension
    :param diffusePaths: The paths to the images to composite together.
    :type diffusePaths: Dict[ShipSkinRegion, str]
    :param List[ShipSkinRegion] diffusePaths: Dictionary associating mask indices to texture file paths to composite.
                                    If a mask index is not in textures or disabledLayers, the default texture for that region
                                    will be used. Textures are overlayed onto the default texture with respect to the ship's
                                    texture region masks.
    :param List[int] diffuseDisabled: List of texture regions to 'disable' - setting them to the first provided texture.
                                    TODO: Instead of doing this by recompositing the bottom texture, just iterate through
                                    disabled layers and apply masks. Apply bottom texture at the end.
    """
    if not diffusePaths:
        raise InvalidRenderConfiguration("At least one diffuse texture must be provided")
    
    if set(diffusePaths.keys()).intersection(set(diffuseDisabled)):
        raise InvalidRenderConfiguration("One or more regions was requested to be both skinned and disabled")
    
    background = Asset(AssetType.shipAutoskinComponent, constants.AUTOSKIN_BACKGROUND_FILENAME, shipId)
    foreground = Asset(AssetType.shipAutoskinComponent, constants.AUTOSKIN_FOREGROUND_FILENAME, shipId)

    # Aquire asset locks
    async with background, foreground:
        # Open background image and convert to RGBA if needed
        # Unfortunately we need a new using here, since this one is synchronous
        with Image.open(background.path) as _bg:
            workingTex = ensureMode(_bg)
            nextTex = None
            
            #region Apply skinned regions
            for layer, layerPath in diffusePaths.items():
                with workingTex as workingTex:
                    nextTex = None

                    maskAsset = Asset(AssetType.shipAutoskinMask, shipAutoskinMaskFileName(layer), shipId)

                    # Make sure this ship has the requested texture region
                    if not maskAsset.path.exists():
                        print(f"WARNING: Attempted to render texture region {layer.value} but the mask does not exist: {maskAsset.path}")
                        continue
                    
                    # Aquire mask asset lock
                    async with maskAsset:

                        # Open the given diffuse and the mask for this layer
                        with Image.open(layerPath) as _ltex, ensureMode(_ltex) as layerTex, \
                                Image.open(maskAsset.path) as _mTex, ensureMode(_mTex, "L") as maskTex:
                            
                            # Gimp and pillow use opposite shades to represent opacity in a mask, so invert the mask
                            maskTex = ImageOps.invert(maskTex)

                            # Apply the texture with respect to the mask
                            nextTex = Image.composite(workingTex, layerTex, maskTex)

                # We need to swap out working textures before processing each layer,
                # because applying a layer will change the working texture reference.
                # Not sure why this cast is necessary!
                workingTex = nextTex if nextTex is not None else cast(ContextManager[Image.Image], nullcontext(workingTex))

            #endregion
            #region Apply disabled regions
            if diffuseDisabled:
                # get first mask
                maskAsset = Asset(AssetType.shipAutoskinMask, shipAutoskinMaskFileName(diffuseDisabled[0]), shipId)
                async with maskAsset:
                    with Image.open(maskAsset.path) as _mTex:
                        # This time, the mask must be RGBA in order to enable alpha compositing, to combine the masks
                        maskTex = ensureMode(_mTex)

                # Combine all 'disabled layer' masks into a single mask
                if len(diffuseDisabled) > 1:
                    for layer in diffuseDisabled[1:]:
                        with maskTex as maskTex:
                            nextTex = None
                            maskAsset = Asset(AssetType.shipAutoskinMask, shipAutoskinMaskFileName(layer), shipId)
                            async with maskAsset:
                                with Image.open(maskAsset.path) as _mTex, ensureMode(_mTex) as currentMask:
                                    # Gimp and pillow use opposite shades to represent opacity in a mask, so invert the mask
                                    maskTex = ImageOps.invert(maskTex)
                                    # Stick this mask on top of the current one
                                    nextTex = Image.composite(maskTex, currentMask, currentMask)

                        # We need to swap out working textures before processing each layer,
                        # because applying a layer will change the working texture reference.
                        # Not sure why this cast is necessary
                        maskTex = nextTex if nextTex is not None else cast(ContextManager[Image.Image], nullcontext(maskTex))
                
                # Load up the first diffuse that we were given
                # The mask is currently RGBA to enable compositing, so convert it back to L
                firstLayer = list(diffusePaths.keys())[0]
                with workingTex as workingTex, \
                        Image.open(diffusePaths[firstLayer]) as _ltex, ensureMode(_ltex) as layerTex, \
                        maskTex as _mTex, ensureMode(_mTex, "L") as maskTex:
                    # Apply the diffuse with our final 'disabled layers' mask
                    nextTex = Image.composite(workingTex, layerTex, maskTex)
                workingTex = nextTex
            #endregion Apply disabled regions

            # Apply foreground elements
            with workingTex as workingTex, Image.open(foreground.path) as _fg, ensureMode(_fg) as foregroundTex:
                nextTex = Image.alpha_composite(workingTex, foregroundTex)

            parent = pathlib.Path(outTexPath).parent
            # Make sure the enclosing folder exists
            if not parent.is_dir():
                os.makedirs(parent)

            with nextTex as nextTex, nextTex.convert("RGB") as workingTex:
                # Save result
                workingTex.save(outTexPath)


def setRenderArgs(*args: str):
    """Pass arguments to the render via the arguments file

    :param List[str] args: List of arguments to write to file
    """
    with open(RENDER_ARGS_PATH, "w") as f:
        for arg in args:
            f.write(arg + "\n")


def start_render():
    subprocess.call(f"blender -b \"{BLENDER_FILE_PATH}\" -P \"{BLENDER_SCRIPT_PATH}\"", shell=True)


@overload
async def renderShip(
    method: Literal[ShipSkinMethod.autoskin], shipId: int,
    res_x: int, res_y: int, numSamples: int,
    renderOutputPath: str, *, textureOutputPath: str,
    diffusePaths: Dict[ShipSkinRegion, str], diffuseDisabled: List[ShipSkinRegion]
):
    """Composite together a single ship texture from the provided texture regions, and render the provided
    model with the final texture.

    The resulting image is cropped to content and saved to `renderOutputPath`.
    TODO: Add 'useBaseTexture' argument. Pass to render_vars. If true, should bypass skinBase
    (for 'full' skins that don't use skinBase)

    :param ShipSkinMethod method: The texture compositing method. For this overload, give ShipSkinMethod.direct.
    :param int shipId: The ID of the ShipSpec to render.
    :param int res_x: The width in pixels of the render resolution. This is not the the width of the final image, as empty
                        space around the rendered object is cropped out automatically.
    :param int res_y: The height in pixels of the render resolution. This is not the the height of the final image, as empty
                        space around the rendered object is cropped out automatically.
    :param int numSamples: The number of samples to render per pixel.
    :param str renderOutputPath: The path to the image file in which to save the render result. Should probably be PNG.
    :param str textureOutputPath: The path to the image file in which to save the generated diffuse texture file. Should probably be JPG.
    :param diffusePaths: The paths to the images to composite together.
    :type diffusePaths: Dict[ShipSkinRegion, str]
    :param List[ShipSkinRegion] diffuseDisabled: The list of texture regions to disable during compositing.
    """

@overload
async def renderShip(
    method: Literal[ShipSkinMethod.direct], shipId: int,
    res_x: int, res_y: int, numSamples: int,
    renderOutputPath: str, *, diffusePath: str
):
    """Render a ship using the provided diffuse texture directly.
    The resulting image is cropped to content and saved to `renderOutputPath`.
    TODO: Add 'useBaseTexture' argument. Pass to render_vars. If true, should bypass skinBase
    (for 'full' skins that don't use skinBase)

    :param ShipSkinMethod method: The texture compositing method. For this overload, give ShipSkinMethod.direct.
    :param int shipId: The ID of the ShipSpec to render.
    :param int res_x: The width in pixels of the render resolution. This is not the the width of the final image, as empty
                        space around the rendered object is cropped out automatically.
    :param int res_y: The height in pixels of the render resolution. This is not the the height of the final image, as empty
                        space around the rendered object is cropped out automatically.
    :param int numSamples: The number of samples to render per pixel.
    :param str renderOutputPath: The path to the image file in which to save the render result. Should probably be PNG.
    :param str diffusePath: The path to the diffuse image file to render.
    :raises InvalidRenderConfiguration:
    :raises RenderFailed:
    """

async def renderShip(
    method: ShipSkinMethod, shipId: int,
    res_x: int, res_y: int, numSamples: int,
    renderOutputPath: str, *, textureOutputPath: str = "",
    diffusePath: str = "", diffusePaths: Dict[ShipSkinRegion, str] = {}, diffuseDisabled: List[ShipSkinRegion] = []
):
    if res_x > 1920:
        raise InvalidRenderConfiguration(f"Attempted to render an image above 1080p (width={res_x})")
    if res_y > 1080:
        raise InvalidRenderConfiguration(f"Attempted to render an image above 1080p (height={res_y})")
    if res_x < 352:
        raise InvalidRenderConfiguration(f"Attempted to render an image below 240p (width={res_x})")
    if res_y < 240:
        raise InvalidRenderConfiguration(f"Attempted to render an image below 240p (height={res_y})")
    
    if numSamples < 1:
        raise InvalidRenderConfiguration("numSamples must be at least 1")
    if numSamples > 128:
        raise InvalidRenderConfiguration("maximum numSamples is 128")

    renderResolution = f"{res_x}x{res_y}"
    renderOutputPath = os.path.abspath(renderOutputPath)

    if method is ShipSkinMethod.autoskin:
        await compositeTextures(shipId, textureOutputPath, diffusePaths, diffuseDisabled)

    # Pass the arguments to the renderer
    modelAsset = Asset(AssetType.shipModel, constants.SHIP_MODEL_FILENAME, shipId)
    async with modelAsset:
        setRenderArgs(
            renderResolution,
            renderOutputPath,
            str(modelAsset.path),
            diffusePath if method is ShipSkinMethod.direct else textureOutputPath,
            str(numSamples)
        )

        # Render the requested model
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(ThreadPoolExecutor(), start_render)

        # Load the newly rendered image
        try:
            renderResult = Image.open(renderOutputPath)
        except FileNotFoundError:
            raise RenderFailed()
        
        # Crop it to content
        with renderResult, trim(renderResult) as trimmed:
            # Save it back to file
            trimmed.save(renderOutputPath)


@dataclass
class _ShipRendererArgsBase:
    # Adding these methods to make the class unpackable
    def keys(self) -> List[str]:
        return [i.name for i in fields(self)]

    def __getitem__(self, k: str) -> Any:
        """Get a config setting by name

        :param k: Name of the parameter to read
        :type k: str
        :return: The current value of the parameter
        :rtype: Any
        """
        return getattr(self, k)

@dataclass
class AutoskinShipRendererArgs(_ShipRendererArgsBase):
    """A dataclass representation of the arguments required for renderShip.
    This class is compatible with variadic function parameter unpacking:
    ```
    >>> x = AutoskinArgs(...)
    >>> renderShip(**x)
    """
    shipId: int
    res_x: int
    res_y: int
    numSamples: int
    renderOutputPath: str
    textureOutputPath: str
    diffusePaths: Dict[ShipSkinRegion, str]
    diffuseDisabled: List[ShipSkinRegion]
    method: Literal[ShipSkinMethod.autoskin] = ShipSkinMethod.autoskin


@dataclass
class DirectShipRendererArgs(_ShipRendererArgsBase):
    """A dataclass representation of the arguments required for renderShip.
    This class is compatible with variadic function parameter unpacking:
    ```
    >>> x = AutoskinArgs(...)
    >>> renderShip(**x)
    """
    shipId: int
    res_x: int
    res_y: int
    numSamples: int
    renderOutputPath: str
    diffusePath: str
    method: Literal[ShipSkinMethod.direct] = ShipSkinMethod.direct
