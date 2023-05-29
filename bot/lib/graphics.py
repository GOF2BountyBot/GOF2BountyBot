from pathlib import Path
from PIL import Image, ImageDraw, ImageEnhance, ImageChops, ImageFilter
from typing import Dict, Optional, Union, Tuple, List, cast
from typing_extensions import TypeGuard
from ..cfg import cfg
import atexit
import random
import os

# Typing here because, assuming correct usage of this module, the image will always be loaded in as part of _init
MISSING_TEXTURE = cast(Image.Image, None)
EMPTY_DUEL_RESULTS_OVERLAY: Optional[Image.Image] = None

XP_BAR_SILHOUETTE: Optional[Image.Image] = None
USR_PROF_BACKGROUND: Optional[Image.Image] = None
XP_BAR_FILLS: Dict[str, Image.Image] = {}

DUEL_RESULTS_BACKGROUNDS: List[Image.Image] = []
DUEL_RESULTS_OVERLAY: Optional[Image.Image] = None
DUEL_WINNER_OVERLAYS: Dict[str, Image.Image] = {}

MAP_IMAGE: Optional[Image.Image] = None

ColourTuple = Union[
    Tuple[int, int, int],       # RGB
    Tuple[int, int, int, int]   # RGBA
]
AnyColour = Union[
    str,        # name
    int,        # hex
    ColourTuple # channels
]


def imageIsOpen(asset: Optional[Image.Image]) -> TypeGuard[Image.Image]:
    if asset is None: return False
    try:
        asset.im.bands
    except ValueError:
        return False
    return True


def _init():
    """graphics initialization. Loading critical assets that must be present, unlike optional/lazily loaded ones.
    """
    global MISSING_TEXTURE, EMPTY_DUEL_RESULTS_OVERLAY, XP_BAR_SILHOUETTE, USR_PROF_BACKGROUND, DUEL_RESULTS_OVERLAY
    MISSING_TEXTURE = Image.open("resources/MISSING_TEXTURE.jpg").convert("RGBA")
    EMPTY_DUEL_RESULTS_OVERLAY = None
    XP_BAR_SILHOUETTE = None
    USR_PROF_BACKGROUND = None
    XP_BAR_FILLS.clear()
    DUEL_RESULTS_BACKGROUNDS.clear()
    DUEL_RESULTS_OVERLAY = None
    DUEL_WINNER_OVERLAYS.clear()

MAP_IMAGE: Optional[Image.Image] = None


_init()


def _closeAll():
    """Only use this function on shutdown. This function is automatically called on module unimport.
    Close all active graphics.
    """
    if imageIsOpen(XP_BAR_SILHOUETTE):
        XP_BAR_SILHOUETTE.close()
    if imageIsOpen(USR_PROF_BACKGROUND):
        USR_PROF_BACKGROUND.close()
    for im in XP_BAR_FILLS.values():
        if imageIsOpen(im):
            im.close()

    for im in DUEL_RESULTS_BACKGROUNDS:
        if imageIsOpen(im):
            im.close()
    if imageIsOpen(DUEL_RESULTS_OVERLAY):
        DUEL_RESULTS_OVERLAY.close()
    for im in DUEL_WINNER_OVERLAYS.values():
        if imageIsOpen(im):
            im.close()

    if imageIsOpen(MAP_IMAGE):
        MAP_IMAGE.close()


# Automatically close all images when the module is unimported
atexit.register(_closeAll)


def paddedScale(baseImage: Image.Image, w: int, h: int, fill: AnyColour,
                offsetMode: Optional[str] = "CENTRE", offset: int = 0, newMode: Optional[str] = None) -> Image.Image:
    """Scale `baseImage` down to (`w`, `h`), but without distorting/stretching the image. Instead, if the image is of a
    different aspect ratio, the empty space around it is filled with `fill` - "black bars".

    offsetMode is a keyword string, being one of:
        "MIN" - Place the image in the top-left
        "MAX" - Place the image in the bottom-right
        "CENTRE" - Place the image in the centre
        "PX" - Place the image `offset` pixels from the top-left.

    :param Image.Image baseImage: The image to scale
    :param int w: The new desired image width
    :param int h: The new desired image height
    :param fill: The colour to fill empty space around the image with
    :type fill: Union[str, int, Tuple[int]]
    :param str offsetMode: Where to place the scaled image with respect to the empty space, as above (Default "CENTRE")
    :param int offset: If `offsetMode` is "PX", the number of pixels from the top-left to place the image (Default 0)
    :param str newMode: Mode override for the new image (Default baseImage.mode)
    :rtype: Image.Image
    """
    # Create new canvas
    if newMode is None:
        newMode = baseImage.mode
    elif baseImage.mode != newMode:
        baseImage = baseImage.convert(newMode)
    newImage = Image.new(newMode, (w, h), fill)

    # Calculate scaled size of baseImage by matching the longest side to the desired length of that side
    if baseImage.width < baseImage.height:
        newSize = (int(baseImage.width * (h / baseImage.height)), h)
    else:
        newSize = (w, int(baseImage.height * (w / baseImage.width)))
    scaledImage = baseImage.resize(newSize)

    # Calculate where to paste the scaled image
    if scaledImage.size == (w, h) or offsetMode == "MIN":
        pasteOrigin = (0, 0)
    elif offsetMode == "MAX":
        pasteOrigin = (w - scaledImage.width, h - scaledImage.height)
    elif offsetMode == "CENTRE":
        pasteOrigin = (int((w - scaledImage.width) / 2), int((h - scaledImage.height) / 2))
    elif offsetMode == "PX":
        if baseImage.width < baseImage.height:
            pasteOrigin = (offset, 0)
        else:
            pasteOrigin = (0, offset)
    else:
        raise ValueError(f"Unknown offsetMode: {offsetMode}")

    # Paste image and return
    scaledImage = padImage(scaledImage, pasteOrigin[1], w - (pasteOrigin[0]+scaledImage.width),
                            h - (pasteOrigin[1]+scaledImage.height), pasteOrigin[0], fill)
    newImage = Image.composite(scaledImage, newImage, scaledImage)
    # newImage.paste(scaledImage, pasteOrigin, scaledImage)
    return newImage


def dropShadow(baseImage: Image.Image, opacity: float, offset: Tuple[int, int], blurIterations: int) -> Image.Image:
    """Return a copy of baseImage with a drop shadow placed beneath.
    If the shadow goes out of bounds of the image, the image is NOT padded to account for this.
    You should isntead pass your image pre-padded.

    :param Image.Image baseImage: Image to apply the shadow to
    :param float opacity: Opacity of the shadow, between 0 and 1
    :param offset: Tuple specifying the x offset of the shadow followed by the y offset
    :type offset: Tuple[int, int]
    :param int blurIterations: The number of times to apply the blur filter to the shadow
    :return: baseImage pasted on top of a drop shadow. The image is "RGBA" mode.
    :rtype: Image.Image
    """
    shadow = ImageEnhance.Brightness(ImageChops.offset(baseImage, offset[0], offset[1])).enhance(0).convert("RGBA")
    if opacity < 1:
        shadowAlpha = ImageEnhance.Brightness(shadow.getchannel("A")).enhance(opacity)
        shadow.putalpha(shadowAlpha)
    for _ in range(blurIterations):
        shadow = shadow.filter(ImageFilter.BLUR)
    return Image.composite(baseImage, shadow, baseImage)

    


def cropAndScale(baseImage: Image.Image, w: int, h: int) -> Image.Image:
    """Crop baseImage to match the aspect ratio of (w, h), and then scale the result to match (w, h).
    Cropping is performed from the top-left of the image. The original image is not altered, a new one is created.

    :param Image.Image baseImage: Image to crop/resize
    :param int w: The desired new image width (px)
    :param int h: The desired new image height (px)
    :return: A copy of baseImage, resized to (w, h), but by cropping instead of stretching
    :rtype: Image.Image
    """
    # If sizes are the same, do nothing
    if baseImage.size == (w, h):
        return baseImage

    # If aspect ratios are different, crop
    if baseImage.width / baseImage.height != w / h:
        # Crop the longest side
        if baseImage.width / baseImage.height > w / h:
            desiredWidth = (w / h) * baseImage.height
            newImage = baseImage.crop((0, 0, int(desiredWidth), baseImage.height))
        else:
            desiredHeight = baseImage.width / (w / h)
            newImage = baseImage.crop((0, 0, baseImage.width, int(desiredHeight)))

        # If no scaling is needed, return cropped image
        if newImage.width == w:
            return newImage
    else:
        newImage = baseImage

    # Scale image
    return newImage.resize((w, h))


def applyProgressBarOutline(progressBar: Image.Image, progress: float, emptyColour: AnyColour,
        lineColour: AnyColour = (255, 255, 255), lineWidth: int = 1):
    """Apply an outline in the shape of a progress bar, over the given image. The operation is performed on a new image,
    the orignal is not modified. The given image should contain only the bar and nothing else,
    as provided by the progressBar function below.

    :param Image.Image progressBar: The image to apply the outline to
    :param float progress: Percentage progress of the bar between 0 and 1
    :param emptyColour: Colour to fill empty space with
    :type emptyColour: Union[str, int, Tuple[int]]
    :param lineColour: The colour of the outline (Default white)
    :type lineColour: Union[str, int, Tuple[int]]
    :param int lineWidth: The width of the outline in pixels (Default 1)
    :return: progressBar, with an outline drawn around the bar
    :rtype: Image.Image
    """
    w, h = progressBar.size
    progressBar = padImage(progressBar, 0, 0, cfg.xpBarOutlineWidth, 0, emptyColour)
    w *= min(1, max(0.01, progress))
    w -= 1
    draw: ImageDraw.ImageDraw = ImageDraw.Draw(progressBar)
    draw.arc(((0, 0),     (h, h)), 90, 270,  fill=lineColour, width=lineWidth)
    draw.arc(((w - h, 0), (w, h)), 270, 450, fill=lineColour, width=lineWidth)
    draw.line(((h / 2, 0), (w - h / 2, 0)), fill=lineColour, width=lineWidth)
    draw.line(((h / 2, h), (w - h / 2, h)), fill=lineColour, width=lineWidth)
    return progressBar


def progressBar(w: int, h: int, progress: float, mode: str = "1", bgColour: AnyColour = 0,
        barColour: AnyColour = 1) -> Image.Image:
    """Create a simple progress bar with a black background. Background fills the image, not limited to the bar shape.
    The default image mode is "1" - single-bit images intended to be used for creating image masks.
    Changes to this should be reflected in bgColour and colour

    Adapted from https://www.programmersought.com/article/71441110786/

    :param int w: The image width
    :param int h: The image height
    :param str mode: The image mode (Default 1)
    :param float progress: Percentage progress of the bar between 0 and 1
    :param bgColour: Colour for the background of the whole image. The type of this parameter depends on pil_image.mode
                        (default black)
    :type bgColour: Union[str, int, Tuple[int]]
    :param barColour: Colour to fill the bar with. The type of this parameter depends on pil_image.mode (default white)
    :type barColour: Union[str, int, Tuple[int]]
    """
    im = Image.new(mode, (w, h), bgColour)
    drawObject = ImageDraw.Draw(im)
    w = int(w * min(1.0, max(0.01, progress)))

    drawObject.ellipse(  ((0, 0),     (h, h)),         fill=barColour)
    drawObject.ellipse(  ((w - h, 0), (w, h)),         fill=barColour)
    drawObject.rectangle(((h / 2, 0), (w - h / 2, h)), fill=barColour)

    return im


def copyXPBarSilhouette() -> Image.Image:
    """Get a copy of the image to place behind XP bars - the "silhouette".
    The image is in "RGBA" mode, and has correct dimensions according to cfg.

    :return: An image containing a full progress bar silhouette, to be pasted behind an XP progress bar.
    :rtype: Image.Image
    """
    global XP_BAR_SILHOUETTE
    if XP_BAR_SILHOUETTE is None:
        XP_BAR_SILHOUETTE = progressBar(cfg.xpBarWidth, cfg.xpBarHeight, 1, "RGBA", 0, cfg.xpBarSilhouetteColour)
    return XP_BAR_SILHOUETTE.copy()


def copyXPBarFill(divName: str) -> Image.Image:
    """Get a copy of the image to mask when filling an XP progress bar.
    The image is in "RGBA" mode, and has correct dimensions according to cfg.

    :param str divName: The name of the division whose image to fetch
    :return: An image containing the file referenced in cfg for the named division, but scaled to the correct dimensions.
    :rtype: Image.Image
    """
    global XP_BAR_FILLS
    if XP_BAR_FILLS == {}:
        pathsDone: Dict[str, Image.Image] = {}
        for i, div in enumerate(cfg.bountyDivisionNames):
            fillPath = cfg.xpBarFillsByDivision[i]
            if fillPath in pathsDone:
                XP_BAR_FILLS[div] = pathsDone[fillPath]
            else:
                if not os.path.isfile(fillPath):
                    XP_BAR_FILLS[div] = MISSING_TEXTURE
                else:
                    XP_BAR_FILLS[div] = Image.open(fillPath)
                XP_BAR_FILLS[div] = XP_BAR_FILLS[div].resize((cfg.xpBarWidth, cfg.xpBarHeight))
                pathsDone[div] = XP_BAR_FILLS[div]

    return XP_BAR_FILLS[divName].copy()


def copyUserProfileBackground() -> Image.Image:
    """Get a copy of the image to place behind user profile images.
    The image is in "RGBA" mode, and has correct dimensions according to cfg.

    :return: An image to use as a user profile background.
    :rtype: Image.Image
    """
    global USR_PROF_BACKGROUND
    if USR_PROF_BACKGROUND is None:
        if not os.path.isfile(cfg.paths.userProfileBackground):
            USR_PROF_BACKGROUND = MISSING_TEXTURE
        else:
            USR_PROF_BACKGROUND = Image.open(cfg.paths.userProfileBackground)
        USR_PROF_BACKGROUND = USR_PROF_BACKGROUND.resize((cfg.userProfileImgWidth, cfg.userProfileImgHeight))

    return USR_PROF_BACKGROUND.copy()


def copyRandomDuelResultsBackground() -> Image.Image:
    """Get a copy of a random image to display behind duel results.
    The image is in "RGBA" mode, and has correct dimensions according to cfg.
    The image has the cfg.paths.duelResultsUnderlay already applied to it, if one was given.

    :return: A random image selected from cfg.paths.duelResultsBackgrounds, but scaled to the right dimensions
    :rtype: Image.Image
    """
    global DUEL_RESULTS_BACKGROUNDS
    if DUEL_RESULTS_BACKGROUNDS == []:
        if not cfg.paths.duelResultsBackgrounds:
            return MISSING_TEXTURE.resize(cfg.duelResultsImageDims)

        if os.path.isfile(cfg.paths.duelResultsUnderlay):
            underlayImg = cropAndScale(Image.open(cfg.paths.duelResultsUnderlay), cfg.duelResultsImageDims[0],
                                        cfg.duelResultsImageDims[1]).convert("RGBA")
        else:
            underlayImg = None

        pathsDone: Dict[Union[str, Path], Image.Image] = {}
        for imgPath in cfg.paths.duelResultsBackgrounds:
            if imgPath in pathsDone:
                DUEL_RESULTS_BACKGROUNDS.append(pathsDone[imgPath])
            else:
                if not os.path.isfile(imgPath):
                    DUEL_RESULTS_BACKGROUNDS.append(MISSING_TEXTURE.resize(cfg.duelResultsImageDims))
                else:
                    DUEL_RESULTS_BACKGROUNDS.append(cropAndScale(Image.open(imgPath), cfg.duelResultsImageDims[0],
                                                                    cfg.duelResultsImageDims[1]).convert("RGBA"))
                if underlayImg is not None:
                    DUEL_RESULTS_BACKGROUNDS[-1] = Image.composite(underlayImg, DUEL_RESULTS_BACKGROUNDS[-1],
                                                                    underlayImg)
                pathsDone[imgPath] = DUEL_RESULTS_BACKGROUNDS[-1]

    return random.choice(DUEL_RESULTS_BACKGROUNDS).copy()


def copyDuelResultsOverlay() -> Image.Image:
    """Get a copy of the image to place on top of duel results images.
    The image is in "RGBA" mode, and has correct dimensions according to cfg.

    :return: An image to use as the overlay for duel results.
    :rtype: Image.Image
    """
    global DUEL_RESULTS_OVERLAY
    global EMPTY_DUEL_RESULTS_OVERLAY
    if DUEL_RESULTS_OVERLAY is None:
        if not os.path.isfile(cfg.paths.duelResultsOverlay):
            if EMPTY_DUEL_RESULTS_OVERLAY is None:
                EMPTY_DUEL_RESULTS_OVERLAY = Image.new("RGBA", (cfg.duelResultsImageDims), (0, 0, 0, 0))
            DUEL_RESULTS_OVERLAY = EMPTY_DUEL_RESULTS_OVERLAY
        else:
            DUEL_RESULTS_OVERLAY = Image.open(cfg.paths.duelResultsOverlay)
        DUEL_RESULTS_OVERLAY = cropAndScale(DUEL_RESULTS_OVERLAY, cfg.duelResultsImageDims[0],
                                            cfg.duelResultsImageDims[1])

    return DUEL_RESULTS_OVERLAY.copy()


def copyDuelWinnerOverlay(winner: str) -> Image.Image:
    """Get a copy of the image to overlay onto duel results, indicating the winner of the duel.
    The image is in "RGBA" mode, and has correct dimensions according to cfg.

    :param str winner: "left", "right" or "draw"
    :return: An image containing the file referenced in cfg for the named winner, but scaled to the correct dimensions.
    :rtype: Image.Image
    """
    global DUEL_WINNER_OVERLAYS
    global EMPTY_DUEL_RESULTS_OVERLAY
    if DUEL_WINNER_OVERLAYS == {}:
        pathsDone: Dict[str, Image.Image] = {}
        for side, imgPath in (("left", cfg.paths.duelResultsLeftWinner), ("right", cfg.paths.duelResultsRightWinner), ("draw", cfg.paths.duelResultsDraw)):
            if imgPath in pathsDone:
                DUEL_WINNER_OVERLAYS[side] = pathsDone[imgPath]
            else:
                if not os.path.isfile(imgPath):
                    if EMPTY_DUEL_RESULTS_OVERLAY is None:
                        EMPTY_DUEL_RESULTS_OVERLAY = Image.new("RGBA", (cfg.duelResultsImageDims), (0, 0, 0, 0))
                    DUEL_WINNER_OVERLAYS[side] = EMPTY_DUEL_RESULTS_OVERLAY
                else:
                    DUEL_WINNER_OVERLAYS[side] = cropAndScale(Image.open(imgPath), cfg.duelResultsImageDims[0], cfg.duelResultsImageDims[1])
                pathsDone[side] = DUEL_WINNER_OVERLAYS[side]

    return DUEL_WINNER_OVERLAYS[winner].copy()


def padImage(pil_img: Image.Image, top: int, right: int, bottom: int, left: int,
        colour: AnyColour) -> Image.Image:
    """Pads an image, placing extra space around it and filling that space with the given colour.
    This is done by creating a new image, the original is not modified.

    https://note.nkmk.me/en/python-pillow-add-margin-expand-canvas/

    :param Image.Image pil_Image: The original image
    :param int top: Amount of extra space to add on top of the image, in pixels
    :param int right: Amount of extra space to add on the right of the image, in pixels
    :param int bottom: Amount of extra space to add beneith the image, in pixels
    :param int left: Amount of extra space to add on the left of the image, in pixels
    :param colour: Colour to fill the new empty space with. The type of this parameter depends on pil_image.mode
    :type colour: Union[str, int, Tuple[int]]
    """
    result = Image.new(pil_img.mode, (pil_img.size[0] + right + left, pil_img.size[1] + top + bottom), colour)
    result.paste(pil_img, (left, top))
    return result


def copyStarMap() -> Image.Image:
    """Get a copy of the galactic map image.
    The image is in "RGBA" mode. Image dimensions are not guaranteed.

    :return: A copy of the galactic map image specified in `cfg.paths.mapImage`
    :rtype: Image.Image
    """
    global MAP_IMAGE
    if MAP_IMAGE is None:
        if os.path.isfile(cfg.paths.mapImage):
            MAP_IMAGE = Image.open(cfg.paths.mapImage)
        else:
            MAP_IMAGE = MISSING_TEXTURE
        if MAP_IMAGE.mode != "RGBA":
            MAP_IMAGE = MAP_IMAGE.convert("RGBA")

    return MAP_IMAGE.copy()


def circleBoundingBox(centre: Tuple[int, int], radius: int) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    """Get the bounding box coordinates for a circle centred at `centre`, of radius `radius`.

    :param centre: Coordinates for the centre of the circle
    :type centre: Tuple[int, int]
    :param int radius: The radius of the circle.
    :return: Coordinates for the bounding box of the circle of the given radius and centre.
    :rtype: Tuple[Tuple[int, int], Tuple[int, int]]
    """
    return ((centre[0] - radius, centre[1] - radius),
            (centre[0] + radius, centre[1] + radius))
