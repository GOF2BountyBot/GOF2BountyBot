from typing import Any, Awaitable, Dict, Generic, List, Optional, Protocol, Set, Tuple, Type, TypeVar, Union, cast
from abc import ABC, ABCMeta, abstractmethod
from inspect import signature, _empty # type: ignore[reportPrivateUsage]
from PIL import Image
from ..lib.discordUtil import ZWSP, ImageFile
from ..lib.asyncUtil import Parallel

from discord import Colour, Embed

MAX_EMBED_VALUE_LENGTH = 1024
MAX_EMBED_NAME_LENGTH = 256
MAX_MESSAGE_ATTACHMENTS = 10
MIN_TASKS_IN_PARALLEL = 3

#region types

#region base

# The return value of an embed attribute callback.
TReturnValue = TypeVar("TReturnValue", covariant=True)

class _NoRequiredArgsInstanceMethod(Protocol, Generic[TReturnValue]):
    """Protocol representing an instance method with no required arguments
    """
    __name__: str
    def __call__(protocolSelf, self: Any, /) -> TReturnValue: ... # type: ignore[reportSelfClsParameterName]


class _NoRequiredArgsClassMethod(Protocol, Generic[TReturnValue]):
    """Protocol representing a class method with no required arguments
    """
    __name__: str
    def __call__(protocolSelf, cls: type, /) -> TReturnValue: ... # type: ignore[reportSelfClsParameterName]


class _NoRequiredArgsInstanceMethodAsync(Protocol, Generic[TReturnValue]):
    """Protocol representing an instance method with no required arguments
    """
    __name__: str
    def __call__(protocolSelf, self: Any, /) -> Awaitable[TReturnValue]: ... # type: ignore[reportSelfClsParameterName]


class _NoRequiredArgsClassMethodAsync(Protocol, Generic[TReturnValue]):
    """Protocol representing a class method with no required arguments
    """
    __name__: str
    def __call__(protocolSelf, cls: type, /) -> Awaitable[TReturnValue]: ... # type: ignore[reportSelfClsParameterName]


# Any embed attribute-compatible instance/class member
NoRequiredArgsMethod = Union[_NoRequiredArgsInstanceMethod[Any], _NoRequiredArgsClassMethod[Any]]
NoRequiredArgsCoroutine = Union[_NoRequiredArgsInstanceMethodAsync[Any], _NoRequiredArgsClassMethodAsync[Any]]
AnyEmbedAttributeUnderlyingMethod = Union[property, NoRequiredArgsMethod, NoRequiredArgsCoroutine]

TNoRequiredArgsMethod = TypeVar("TNoRequiredArgsMethod", bound=Union[NoRequiredArgsMethod, NoRequiredArgsCoroutine])
TAnyEmbedAttributeUnderlyingMethod = TypeVar("TAnyEmbedAttributeUnderlyingMethod", bound=AnyEmbedAttributeUnderlyingMethod)


class _BaseEmbedAttribute(ABC, Generic[TAnyEmbedAttributeUnderlyingMethod, TReturnValue]):
    """A record of an instance/class member acting as an embed attribute.
    This is initially assigned to the named member on the class, but `EmbedFillableMixin` will replace this with `inner` on class creation,
    meaning that in practise, if used correctly this class is only present in the class's private embed fields variables

    The `TAnyEmbedAttributeUnderlyingMethod` generic type parameter is the type of the underlying method
    The `TReturnValue` generic type parameter is the return type of `TAnyEmbedAttributeUnderlyingMethod`
    """
    def __init__(self, inner: TAnyEmbedAttributeUnderlyingMethod) -> None:
        self.inner = inner


    async def getValue(self, ownerSelf) -> TReturnValue:
        """Get the value of the attribute from the underlying method (`self.inner`).
        If `self.inner` is a coroutine, this method will await it.

        :param ownerSelf: The calling instance of the owning class, to pass down to the underlying method on that instance
        """
        result = self.value(ownerSelf)
        if isinstance(result, Awaitable):
            result = cast(TReturnValue, await result)
        return result


    @abstractmethod
    def value(self, ownerSelf) -> Union[TReturnValue, Awaitable[TReturnValue]]:
        """Get the value of the attribute from the underlying method (`self.inner`).
        This may or may not be a Coroutine. The result will be awaited automatically.

        :param ownerSelf: The calling instance of the owning class, to pass down to the underlying method on that instance
        """
        raise NotImplementedError()

        
    @abstractmethod
    async def fillEmbed(self, ownerSelf, embed: Embed) -> Optional[ImageFile]:
        """Apply this attribute to an embed.
        This method can optionally return an image that must be sent alongside the embed, for the application to be visible.

        :param ownerSelf: The calling instance of the owning class, to pass down to the underlying method on that instance
        :param Embed embed: The embed to apply the attribute to
        :returns: Optionally, an attachment that must be sent alongside the embed for this attribute to be visible
        """
        raise NotImplementedError()


    @abstractmethod
    def __hash__(self) -> int:
        """A class's embed attributes are stored in a set. This means that the attribute's hash can enforce attribute uniqueness
        within a class. If a duplicate is found, then old attribute is silently replaced.
        """
        return super().__hash__()


class _BaseEmbedFileAttribute(_BaseEmbedAttribute[TAnyEmbedAttributeUnderlyingMethod, TReturnValue], Generic[TAnyEmbedAttributeUnderlyingMethod, TReturnValue]):
    """An embed attribute that returns a file which must be uploaded alongside the embed, in order for
    the attribute's changes to take effect.
    """
    pass


def imageOrPathValue(val: Optional[Union[str, Image.Image]], fileName: str) -> Optional[ImageFile]:
    """Get the Pillow `Image` optionally referenced by `val`, and wrap it in an `ImageFile` to be attached to a message.

    If `val` is `None`, then `None` is returned.
    If `val` is a `str`, it is assumed to represent the path to an image file on disk, and the file is loaded.
    If `val` is itself an `Image`, it is returned directly.

    Currently, if the image is in mode RGBA, the image is sent to discord in PNG format. Otherwise, the image is sent as JPG.

    :param val: Path to the image to load, or the image itself
    :type val: Optional[Union[str, Image.Image]]
    :param fileName: The name of the attachment as it will appear in discord
    :type fileName: str
    :return: An ImageFile wrapping the Image referenced by `val`, or `None` if `val` is `None`
    :rtype: Optional[ImageFile]
    """
    if isinstance(val, str):
        im = Image.open(val)
    elif isinstance(val, Image.Image):
        im = val
    else:
        return None
    
    return ImageFile(im, fileName + (".png" if im.mode == "RGBA" else ".jpg"))


def _validateProperty(prop: property) -> NoRequiredArgsMethod:
    """Make sure `prop` is a valid embed attribute property.

    :param prop: The property to validate
    :type prop: property
    :raises ValueError: If `prop` does not have an underlying method
    :return: The underlying method on `prop`
    :rtype: MethodEmbedAttributeType
    """
    if prop.fget is None:
        raise ValueError(f"Invalid embed attribute '{prop}': Property does not have an underlying method")
    
    return prop.fget


def _validateMethod(prop: TNoRequiredArgsMethod) -> TNoRequiredArgsMethod:
    """Make sure `prop` is a valid embed attribute method.

    :param prop: The method to validate
    :type prop: MethodEmbedAttributeType
    :raises TypeError: If `prop` does not have exactly one required argument (this should be `self` or `cls`, but this isn't validated)
    :return: `prop`
    :rtype: MethodEmbedAttributeType
    """
    # Make sure that the callback takes exactly one argument. This should be self or cls, but I'm not going to validate that
    if len([i for i in signature(prop).parameters.values() if i.default is _empty]) != 1:
        raise TypeError(f"Invalid embed attribute '{prop}': {embedColour.__name__} decorator can only be applied to properties (@property) or methods with no arguments")

    return prop


class _PropEmbedAttribute(_BaseEmbedAttribute[property, TReturnValue], Generic[TReturnValue]):
    """An embed attribute whose underlying value-providing method is a `property`.
    """
    def value(self, ownerSelf) -> Union[TReturnValue, Awaitable[TReturnValue]]:
        # If __self__ is set, then this is a bound method - e.g the decorator was applied to a method on an already instanced class,
        # or the @classmethod decorator was used
        return self.inner.__get__(getattr(self.inner, "__self__") if hasattr(self.inner, "__self__") else ownerSelf, type(ownerSelf))


class _MethodEmbedAttribute(_BaseEmbedAttribute[Union[_NoRequiredArgsInstanceMethod[TReturnValue], _NoRequiredArgsClassMethod[TReturnValue]], TReturnValue], Generic[TReturnValue]):
    """An embed attribute whose underlying value-providing method is a method with no required arguments, except for `self`/`cls`.

    `__call__` is delegated to the underlying method.
    """
    def __call__(self, *args, **kwargs):
        return self.inner(*args, **kwargs)
    

    def value(self, ownerSelf) -> Union[TReturnValue, Awaitable[TReturnValue]]:
        # If __self__ is set, then this is a bound method - e.g the decorator was applied to a method on an already instanced class,
        # or the @classmethod decorator was used
        return self.inner(getattr(self.inner, "__self__") if hasattr(self.inner, "__self__") else ownerSelf)

#endregion base

#region colour

class _BaseEmbedColour(_BaseEmbedAttribute[TAnyEmbedAttributeUnderlyingMethod, Optional[Colour]], Generic[TAnyEmbedAttributeUnderlyingMethod]):
    """An embed colour setter. The underlying method must return `Colour` or `None`.
    """
    async def fillEmbed(self, ownerSelf, embed: Embed):
        embed.colour = await self.getValue(ownerSelf)

    def __hash__(self) -> int:
        """The hash implementation for _BaseEmbedColour hashes the _BaseEmbedColour class itself.
        This is done to ensure that a class only has one embed colour attribute.
        """
        return hash(_BaseEmbedColour)


class _PropEmbedColour(_BaseEmbedColour[property], _PropEmbedAttribute[Optional[Colour]]): ...
class _MethodEmbedColour(_BaseEmbedColour[Union[_NoRequiredArgsInstanceMethod[Optional[Colour]], _NoRequiredArgsClassMethod[Optional[Colour]]]], _MethodEmbedAttribute[Optional[Colour]]): ...

#endregion
#region thumbnail


class _BaseEmbedUrlThumbnail(_BaseEmbedAttribute[TAnyEmbedAttributeUnderlyingMethod, Optional[str]], Generic[TAnyEmbedAttributeUnderlyingMethod]):
    """An embed thumbnail setter, by url. The underlying method must return `str` (the image url) or `None`.
    """
    async def fillEmbed(self, ownerSelf, embed: Embed):
        val = await self.getValue(ownerSelf)
        if (isinstance(val, str) and val) or val is None:
            embed.set_thumbnail(url=val)

    def __hash__(self) -> int:
        """The hash implementation for _BaseEmbedThumbnail hashes the _BaseEmbedThumbnail class itself.
        This is done to ensure that a class only has one embed thumbnail attribute.
        """
        return hash(_BaseEmbedUrlThumbnail)


class _BaseEmbedFileThumbnail(_BaseEmbedFileAttribute[TAnyEmbedAttributeUnderlyingMethod, Optional[Union[str, Image.Image]]], Generic[TAnyEmbedAttributeUnderlyingMethod]):
    """An embed thumbnail setter, by reference to an image file. The underlying method must return `str` (the path to the file), `Image.Image` or `None`.
    """
    async def fillEmbed(self, ownerSelf, embed: Embed) -> Optional[ImageFile]:
        val = await self.getValue(ownerSelf)
        if not (f := imageOrPathValue(val, "autoFillEmbedThumbnail")):
            return None
        embed.set_thumbnail(url=f"attachment://{f.fileName}")
        return f

    def __hash__(self) -> int:
        """The hash implementation for _BaseEmbedFileThumbnail hashes the _BaseEmbedUrlThumbnail class.
        This is done to ensure that a class only has one embed Thumbnail attribute, whether by file or url.
        """
        return hash(_BaseEmbedUrlThumbnail)

class _PropEmbedUrlThumbnail(_BaseEmbedUrlThumbnail[property], _PropEmbedAttribute[Optional[str]]): ...
class _MethodEmbedUrlThumbnail(_BaseEmbedUrlThumbnail[Union[_NoRequiredArgsInstanceMethod[Optional[str]], _NoRequiredArgsClassMethod[Optional[str]]]], _MethodEmbedAttribute[Optional[str]]): ...

class _PropEmbedFileThumbnail(_BaseEmbedFileThumbnail[property], _PropEmbedAttribute[Optional[Union[str, Image.Image]]]): ...
class _MethodEmbedFileThumbnail(_BaseEmbedFileThumbnail[Union[_NoRequiredArgsInstanceMethod[Optional[Union[str, Image.Image]]], _NoRequiredArgsClassMethod[Optional[Union[str, Image.Image]]]]], _MethodEmbedAttribute[Optional[Union[str, Image.Image]]]): ...

#endregion
#region author

class _BaseEmbedUrlAuthor(_BaseEmbedAttribute[TAnyEmbedAttributeUnderlyingMethod, Optional[Tuple[Optional[str], Optional[str], Optional[str]]]], Generic[TAnyEmbedAttributeUnderlyingMethod]):
    """An embed author setter, setting the author icon by url.
    The underlying method must return `None`, or a tuple of (`str` (author name), `str` (icon_url), `str` (url)). Each tuple member is optional.
    """
    async def fillEmbed(self, ownerSelf, embed: Embed):
        val = await self.getValue(ownerSelf)
        if val is None:
            embed.remove_author()
        elif not isinstance(val, tuple) or len(val) != 3:
            raise ValueError("Embed author attribute must return None or a 3-tuple with 3 optional strings (name, icon_url, url)")
        else:
            embed.set_author(name=val[0], icon_url=val[1], url=val[2])

    def __hash__(self) -> int:
        """The hash implementation for _BaseEmbedAuthor hashes the _BaseEmbedAuthor class itself.
        This is done to ensure that a class only has one embed author attribute.
        """
        return hash(_BaseEmbedUrlAuthor)


class _BaseEmbedFileAuthor(_BaseEmbedFileAttribute[TAnyEmbedAttributeUnderlyingMethod, Optional[Tuple[Optional[str], Optional[Union[str, Image.Image]], Optional[str]]]], Generic[TAnyEmbedAttributeUnderlyingMethod]):
    """An embed author setter, setting the author icon by reference to a file.
    The underlying method must return `None`, or a tuple of (`str` (author name), `str` (path to the icon file) or `Image.Image` (icon), `str` (url)). Each tuple member is optional.
    """
    async def fillEmbed(self, ownerSelf, embed: Embed) -> Optional[ImageFile]:
        val = await self.getValue(ownerSelf)
        if val is None:
            embed.remove_author()
        elif not isinstance(val, tuple) or len(val) != 3:
            raise ValueError("Embed author attribute must return None or a 3-tuple with 3 optional strings (name, [icon Image or icon file path], url)")
        else:
            f = imageOrPathValue(val[1], "autoFillEmbedThumbnail")
            embed.set_author(name=val[0], icon_url=None if f is None else f"attachment://{f.fileName}", url=val[2])
            return f

    def __hash__(self) -> int:
        """The hash implementation for _BaseEmbedFileAuthor hashes the _BaseEmbedUrlAuthor class.
        This is done to ensure that a class only has one embed Author attribute, whether by file or url.
        """
        return hash(_BaseEmbedUrlAuthor)


class _PropEmbedUrlAuthor(_BaseEmbedUrlAuthor[property], _PropEmbedAttribute[Optional[Tuple[Optional[str], Optional[str], Optional[str]]]]): ...
class _MethodEmbedUrlAuthor(_BaseEmbedUrlAuthor[Union[_NoRequiredArgsInstanceMethod[Optional[Tuple[Optional[str], Optional[str], Optional[str]]]], _NoRequiredArgsClassMethod[Optional[Tuple[Optional[str], Optional[str], Optional[str]]]]]], _MethodEmbedAttribute[Optional[Tuple[Optional[str], Optional[str], Optional[str]]]]): ...

class _PropEmbedFileAuthor(_BaseEmbedFileAuthor[property], _PropEmbedAttribute[Optional[Tuple[Optional[str], Optional[Union[str, Image.Image]], Optional[str]]]]): ...
class _MethodEmbedFileAuthor(_BaseEmbedFileAuthor[Union[_NoRequiredArgsInstanceMethod[Optional[Tuple[Optional[str], Optional[Union[str, Image.Image]], Optional[str]]]], _NoRequiredArgsClassMethod[Optional[Tuple[Optional[str], Optional[Union[str, Image.Image]], Optional[str]]]]]], _MethodEmbedAttribute[Optional[Tuple[Optional[str], Optional[Union[str, Image.Image]], Optional[str]]]]): ...

#endregion
#region footer

class _BaseEmbedUrlFooter(_BaseEmbedAttribute[TAnyEmbedAttributeUnderlyingMethod, Optional[Tuple[Optional[str], Optional[str]]]], Generic[TAnyEmbedAttributeUnderlyingMethod]):
    """An embed footer setter, setting the footer icon by url.
    The underlying method must return `None`, or a tuple of (`str` (footer text), `str` (icon_url)). Each tuple member is optional.
    """
    async def fillEmbed(self, ownerSelf, embed):
        val = await self.getValue(ownerSelf)
        if val is None:
            embed.remove_footer()
        elif not isinstance(val, tuple) or len(val) != 2:
            raise ValueError("Embed footer attribute must return None or a 2-tuple with 2 optional strings (text, icon_url)")
        else:
            embed.set_footer(text=val[0] or ZWSP, icon_url=val[1])      

    def __hash__(self) -> int:
        """The hash implementation for _BaseEmbedFooter hashes the _BaseEmbedFooter class itself.
        This is done to ensure that a class only has one embed footer attribute.
        """
        return hash(_BaseEmbedUrlFooter)


class _BaseEmbedFileFooter(_BaseEmbedFileAttribute[TAnyEmbedAttributeUnderlyingMethod, Optional[Tuple[Optional[str], Optional[str], Optional[Union[str, Image.Image]]]]], Generic[TAnyEmbedAttributeUnderlyingMethod]):
    """An embed author setter, setting the footer icon by file reference.
    The underlying method must return `None`, or a tuple of (`str` (footer text), `str` (path to the icon) or `Image.Image` (icon)). Each tuple member is optional.
    """
    async def fillEmbed(self, ownerSelf, embed: Embed) -> Optional[ImageFile]:
        val = await self.getValue(ownerSelf)
        if val is None:
            embed.remove_footer()
        elif not isinstance(val, tuple) or len(val) != 2:
            raise ValueError("Embed footer attribute must return None or a 2-tuple with 2 optional strings (text, [icon Image or icon file path])")
        else:
            f = imageOrPathValue(val[2], "autoFillEmbedFooter")
            embed.set_author(name=val[0] or ZWSP, icon_url=None if f is None else f"attachment://{f.fileName}")
            return f

    def __hash__(self) -> int:
        """The hash implementation for _BaseEmbedFileFooter hashes the _BaseEmbedUrlFooter class.
        This is done to ensure that a class only has one embed Footer attribute, whether by file or url.
        """
        return hash(_BaseEmbedUrlFooter)


class _PropEmbedUrlFooter(_BaseEmbedUrlFooter[property], _PropEmbedAttribute[Optional[Tuple[Optional[str], Optional[str]]]]): ...
class _MethodEmbedUrlFooter(_BaseEmbedUrlFooter[Union[_NoRequiredArgsInstanceMethod[Optional[Tuple[Optional[str], Optional[str]]]], _NoRequiredArgsClassMethod[Optional[Tuple[Optional[str], Optional[str]]]]]], _MethodEmbedAttribute[Optional[Tuple[Optional[str], Optional[str]]]]): ...

class _PropEmbedFileFooter(_BaseEmbedFileFooter[property], _PropEmbedAttribute[Optional[Tuple[Optional[str], Optional[Union[str, Image.Image]]]]]): ...
class _MethodEmbedFileFooter(_BaseEmbedFileFooter[Union[_NoRequiredArgsInstanceMethod[Optional[Tuple[Optional[str], Optional[Union[str, Image.Image]]]]], _NoRequiredArgsClassMethod[Optional[Tuple[Optional[str], Optional[Union[str, Image.Image]]]]]]], _MethodEmbedAttribute[Optional[Tuple[Optional[str], Optional[Union[str, Image.Image]]]]]): ...

#endregion
#region description

class _BaseEmbedDescription(_BaseEmbedAttribute[TAnyEmbedAttributeUnderlyingMethod, Optional[str]], Generic[TAnyEmbedAttributeUnderlyingMethod]):
    """An embed description setter. The underlying method must return `str` or `None`.
    """
    async def fillEmbed(self, ownerSelf, embed: Embed):
        embed.description = await self.getValue(ownerSelf)

    def __hash__(self) -> int:
        """The hash implementation for _BaseEmbedDescription hashes the _BaseEmbedDescription class itself.
        This is done to ensure that a class only has one embed description attribute.
        """
        return hash(_BaseEmbedDescription)


class _PropEmbedDescription(_BaseEmbedDescription[property], _PropEmbedAttribute[Optional[str]]): ...
class _MethodEmbedDescription(_BaseEmbedDescription[Union[_NoRequiredArgsInstanceMethod[Optional[str]], _NoRequiredArgsClassMethod[Optional[str]]]], _MethodEmbedAttribute[Optional[str]]): ...

#endregion
#region title

class _BaseEmbedTitle(_BaseEmbedAttribute[TAnyEmbedAttributeUnderlyingMethod, Optional[str]], Generic[TAnyEmbedAttributeUnderlyingMethod]):
    """An embed title setter. The underlying method must return `str` or `None`.
    """
    async def fillEmbed(self, ownerSelf, embed: Embed):
        embed.title = await self.getValue(ownerSelf)

    def __hash__(self) -> int:
        """The hash implementation for _BaseEmbedTitle hashes the _BaseEmbedTitle class itself.
        This is done to ensure that a class only has one embed title attribute.
        """
        return hash(_BaseEmbedTitle)


class _PropEmbedTitle(_BaseEmbedTitle[property], _PropEmbedAttribute[Optional[str]]): ...
class _MethodEmbedTitle(_BaseEmbedTitle[Union[_NoRequiredArgsInstanceMethod[Optional[str]], _NoRequiredArgsClassMethod[Optional[str]]]], _MethodEmbedAttribute[Optional[str]]): ...

#endregion
#region image

class _BaseEmbedUrlImage(_BaseEmbedAttribute[TAnyEmbedAttributeUnderlyingMethod, Optional[str]]):
    """An embed main image setter, by url.
    The underlying method must return `str` (icon_url) or `None`.
    """
    async def fillEmbed(self, ownerSelf, embed: Embed):
        embed.set_image(url=await self.getValue(ownerSelf))

    def __hash__(self) -> int:
        """The hash implementation for _BaseEmbedUrlImage hashes the _BaseEmbedUrlImage class itself.
        This is done to ensure that a class only has one embed Image attribute.
        """
        return hash(_BaseEmbedUrlImage)


class _BaseEmbedFileImage(_BaseEmbedFileAttribute[TAnyEmbedAttributeUnderlyingMethod, Optional[Union[str, Image.Image]]], Generic[TAnyEmbedAttributeUnderlyingMethod]):
    """An embed main image setter, by file reference.
    The underlying method must return `str` (path to the file), `Image.Image` (the file) or `None`.
    """
    async def fillEmbed(self, ownerSelf, embed: Embed) -> Optional[ImageFile]:
        val = await self.getValue(ownerSelf)
        if not (f := imageOrPathValue(val, "autoFillEmbedImage")):
            return None
        embed.set_image(url=f"attachment://{f.fileName}")
        return f

    def __hash__(self) -> int:
        """The hash implementation for _BaseEmbedFileImage hashes the _BaseEmbedImage class.
        This is done to ensure that a class only has one embed Image attribute, whether by file or url.
        """
        return hash(_BaseEmbedUrlImage)


class _PropEmbedUrlImage(_BaseEmbedUrlImage[property], _PropEmbedAttribute[Optional[str]]): ...
class _MethodEmbedUrlImage(_BaseEmbedUrlImage[Union[_NoRequiredArgsInstanceMethod[Optional[str]], _NoRequiredArgsClassMethod[Optional[str]]]], _MethodEmbedAttribute[Optional[str]]): ...

class _PropEmbedFileImage(_BaseEmbedFileImage[property], _PropEmbedAttribute[Optional[Union[str, Image.Image]]]): ...
class _MethodEmbedFileImage(_BaseEmbedFileImage[Union[_NoRequiredArgsInstanceMethod[Optional[Union[str, Image.Image]]], _NoRequiredArgsClassMethod[Optional[Union[str, Image.Image]]]]], _MethodEmbedAttribute[Optional[Union[str, Image.Image]]]): ...

#endregion
#region url

class _BaseEmbedUrl(_BaseEmbedAttribute[TAnyEmbedAttributeUnderlyingMethod, Optional[str]], Generic[TAnyEmbedAttributeUnderlyingMethod]):
    """An embed url setter. The underlying method must return `str` or `None`.
    """
    async def fillEmbed(self, ownerSelf, embed: Embed):
        embed.url = await self.getValue(ownerSelf)

    def __hash__(self) -> int:
        """The hash implementation for _BaseEmbedUrl hashes the _BaseEmbedUrl class itself.
        This is done to ensure that a class only has one embed Url attribute.
        """
        return hash(_BaseEmbedUrl)


class _PropEmbedUrl(_BaseEmbedUrl[property], _PropEmbedAttribute[Optional[str]]): ...
class _MethodEmbedUrl(_BaseEmbedUrl[Union[_NoRequiredArgsInstanceMethod[Optional[str]], _NoRequiredArgsClassMethod[Optional[str]]]], _MethodEmbedAttribute[Optional[str]]): ...

#endregion
#region field

class _BaseEmbedField(_BaseEmbedAttribute[TAnyEmbedAttributeUnderlyingMethod, Any], Generic[TAnyEmbedAttributeUnderlyingMethod]):
    """An embed field setter. The underlying method can return anything, because discord.py will cast to `str`.
    """
    def __init__(self, name: str, inner: TAnyEmbedAttributeUnderlyingMethod, showFirst: bool = False, showLast: bool = False, showInline: bool = True, hideWhenNone: bool = True, uniqueFieldName: bool = True) -> None:
        super().__init__(inner=inner)
        self.name = name
        self.showFirst = showFirst
        self.showLast = showLast
        self.showInline = showInline
        self.hideWhenNone = hideWhenNone
        self.uniqueFieldName = uniqueFieldName


    async def fillEmbed(self, ownerSelf, embed: Embed):
        val = await self.getValue(ownerSelf)
        if val is not None or not self.hideWhenNone:
            valStr = str(val)
            if len(valStr) > MAX_EMBED_VALUE_LENGTH:
                fieldsExceptExcess = len(valStr) // MAX_EMBED_VALUE_LENGTH
                excess = len(valStr) % MAX_EMBED_VALUE_LENGTH
                for fieldNum in range(fieldsExceptExcess):
                    embed.add_field(name=self.name, value=val[MAX_EMBED_VALUE_LENGTH * fieldNum:MAX_EMBED_VALUE_LENGTH * (fieldNum + 1)], inline=self.showInline)
                if excess:
                    embed.add_field(name=self.name, value=val[-excess:], inline=self.showInline)
            else:
                embed.add_field(name=self.name, value=val, inline=self.showInline)


    def __hash__(self) -> int:
        """If this field has uniqueFieldName set, then the hash of the field is deterministic in the name of the field.
        Otherwise, the hash is the default.
        """
        return hash((_BaseEmbedField, self.name)) if self.uniqueFieldName else super().__hash__()


class _PropEmbedField(_BaseEmbedField[property], _PropEmbedAttribute[Any]): ...
class _MethodEmbedField(_BaseEmbedField[Union[_NoRequiredArgsInstanceMethod[Any], _NoRequiredArgsClassMethod[Any]]], _MethodEmbedAttribute[Any]): ...

#endregion

#endregion types

#region decorators

TEmbedColourMethod = TypeVar("TEmbedColourMethod", bound=Union[property, _NoRequiredArgsInstanceMethod[Optional[Colour]], _NoRequiredArgsClassMethod[Optional[Colour]]])
def embedColour(prop: TEmbedColourMethod) -> TEmbedColourMethod:
    """Mark a method, class method or property as a discord Embed colour setter.
    If the callback is async, then it will be awaited.

    This decorator will only work if:
    - It is the last decorator in the chain
    - It is applied to a method defined on an `EmbedFillableMixin` subclass

    Only one embed colour will be registered for a single class.
    This means that derived classes can override embed colours, but it also means that using @embedColour
    multiple times for the same method on a single class (e.g with typing.overload) will result in only one decorator
    being effective

    :param prop: The method. Must belong to a class (i.e method, classmethod or property) and return Colour or None
    :type prop: TEmbedColourMethod
    :raises TypeError: If `prop` is not a `property` and has a required argument
    :return: `prop`
    :rtype: TEmbedColourMethod
    """
    # See comment on casting in embedField.inner
    if isinstance(prop, property):
        _validateProperty(prop)
        return cast(TEmbedColourMethod, _PropEmbedColour(prop))

    _validateMethod(prop)
    return cast(TEmbedColourMethod, _MethodEmbedColour(prop))


TEmbedThumbnailUrlMethod = TypeVar("TEmbedThumbnailUrlMethod", bound=Union[property, _NoRequiredArgsInstanceMethod[Optional[str]], _NoRequiredArgsClassMethod[Optional[str]]])
def embedThumbnailUrl(prop: TEmbedThumbnailUrlMethod) -> TEmbedThumbnailUrlMethod:
    """Mark a method, class method or property as a discord Embed thumbnail setter.
    If the callback is async, then it will be awaited.
    This decorator will only work if:
    - It is the last decorator in the chain
    - It is applied to a method defined on an `EmbedFillableMixin` subclass

    Only one embed thumbnail will be registered for a single class.
    This means that derived classes can override embed thumbnails, but it also means that using @embedThumbnail
    multiple times for the same method on a single class (e.g with typing.overload) will result in only one decorator
    being effective

    :param prop: The method. Must belong to a class (i.e method, classmethod or property) and return str or None
    :type prop: TEmbedThumbnailUrlMethod
    :raises TypeError: If `prop` is not a `property` and has a required argument
    :return: `prop`
    :rtype: TEmbedThumbnailUrlMethod
    """
    # See comment on casting in embedField.inner
    if isinstance(prop, property):
        _validateProperty(prop)
        return cast(TEmbedThumbnailUrlMethod, _PropEmbedUrlThumbnail(prop))

    _validateMethod(prop)
    return cast(TEmbedThumbnailUrlMethod, _MethodEmbedUrlThumbnail(prop))


TEmbedThumbnailFileMethod = TypeVar("TEmbedThumbnailFileMethod", bound=Union[property, _NoRequiredArgsInstanceMethod[Optional[Union[str, Image.Image]]], _NoRequiredArgsClassMethod[Optional[Union[str, Image.Image]]]])
def embedThumbnailFile(prop: TEmbedThumbnailFileMethod) -> TEmbedThumbnailFileMethod:
    """Mark a method, class method or property as a discord Embed thumbnail setter,
    giving the image eithe as the path to a file on disk, or the file itself as a Pillow Image.
    If the callback is async, then it will be awaited.

    This decorator will only work if:
    - It is the last decorator in the chain
    - It is applied to a method defined on an `EmbedFillableMixin` subclass

    Only one embed thumbnail will be registered for a single class.
    This means that derived classes can override embed thumbnails, but it also means that using @embedThumbnailUrl/@embedThumbnailFile
    multiple times for the same method on a single class (e.g with typing.overload) will result in only one decorator
    being effective

    :param prop: The method. Must belong to a class (i.e method, classmethod or property) and return str or None
    :type prop: TEmbedThumbnailFileMethod
    :raises TypeError: If `prop` is not a `property` and has a required argument
    :return: `prop`
    :rtype: TEmbedThumbnailFileMethod
    """
    # See comment on casting in embedField.inner
    if isinstance(prop, property):
        _validateProperty(prop)
        return cast(TEmbedThumbnailFileMethod, _PropEmbedFileThumbnail(prop))

    _validateMethod(prop)
    return cast(TEmbedThumbnailFileMethod, _MethodEmbedFileThumbnail(prop))


TEmbedAuthorUrlMethod = TypeVar("TEmbedAuthorUrlMethod", bound=Union[property, _NoRequiredArgsInstanceMethod[Optional[Tuple[Optional[str], Optional[str], Optional[str]]]], _NoRequiredArgsClassMethod[Optional[Tuple[Optional[str], Optional[str], Optional[str]]]]])
def embedAuthorUrl(prop: TEmbedAuthorUrlMethod) -> TEmbedAuthorUrlMethod:
    """Mark a method, class method or property as a discord Embed Author setter.
    If the callback is async, then it will be awaited.

    This decorator will only work if:
    - It is the last decorator in the chain
    - It is applied to a method defined on an `EmbedFillableMixin` subclass

    Only one embed Author will be registered for a single class.
    This means that derived classes can override embed Authors, but it also means that using @embedAuthor
    multiple times for the same method on a single class (e.g with typing.overload) will result in only one decorator
    being effective

    The method must return None (to clear the footer), or a 3-tuple of optional strings:
    1. The author name
    2. The url for the icon of the author
    3. The url of the author

    Giving either of these as None will clear that information in the embed.

    :param prop: The method. Must belong to a class (i.e method, classmethod or property) and return an optional tuple as above
    :type prop: TEmbedAuthorUrlMethod
    :raises TypeError: If `prop` is not a `property` and has a required argument
    :return: `prop`
    :rtype: TEmbedAuthorUrlMethod
    """
    # See comment on casting in embedField.inner
    if isinstance(prop, property):
        _validateProperty(prop)
        return cast(TEmbedAuthorUrlMethod, _PropEmbedUrlAuthor(prop))

    _validateMethod(prop)
    return cast(TEmbedAuthorUrlMethod, _MethodEmbedUrlAuthor(prop))


TEmbedAuthorFileMethod = TypeVar("TEmbedAuthorFileMethod", bound=Union[property, _NoRequiredArgsInstanceMethod[Optional[Tuple[Optional[str], Optional[Union[str, Image.Image]], Optional[str]]]], _NoRequiredArgsClassMethod[Optional[Tuple[Optional[str], Optional[Union[str, Image.Image]], Optional[str]]]]])
def embedAuthorFile(prop: TEmbedAuthorFileMethod) -> TEmbedAuthorFileMethod:
    """Mark a method, class method or property as a discord Embed Author setter,
    setting the author icon by the path to the file on disk, or by the file itself as a Pillow Image.
    If the callback is async, then it will be awaited.

    This decorator will only work if:
    - It is the last decorator in the chain
    - It is applied to a method defined on an `EmbedFillableMixin` subclass

    Only one embed Author will be registered for a single class.
    This means that derived classes can override embed Authors, but it also means that using @embedAuthorUrl/@embedAuthorFile
    multiple times for the same method on a single class (e.g with typing.overload) will result in only one decorator
    being effective

    The method must return None (to clear the footer), or a 3-tuple:
    1. (optional) The string author name
    2. (optional) The icon of the author, either as the string path to the file, or the file itself as a Pillow Image
    3. (optional) The string url of the author

    Giving either of these as None will clear that information in the embed.

    :param prop: The method. Must belong to a class (i.e method, classmethod or property) and return an optional tuple as above
    :type prop: TEmbedAuthorFileMethod
    :raises TypeError: If `prop` is not a `property` and has a required argument
    :return: `prop`
    :rtype: TEmbedAuthorFileMethod
    """
    # See comment on casting in embedField.inner
    if isinstance(prop, property):
        _validateProperty(prop)
        return cast(TEmbedAuthorFileMethod, _PropEmbedFileAuthor(prop))

    _validateMethod(prop)
    return cast(TEmbedAuthorFileMethod, _MethodEmbedFileAuthor(prop))


TEmbedFooterUrlMethod = TypeVar("TEmbedFooterUrlMethod", bound=Union[property, _NoRequiredArgsInstanceMethod[Optional[Tuple[Optional[str], Optional[str]]]], _NoRequiredArgsClassMethod[Optional[Tuple[Optional[str], Optional[str]]]]])
def embedFooterUrl(prop: TEmbedFooterUrlMethod) -> TEmbedFooterUrlMethod:
    """Mark a method, class method or property as a discord Embed Footer setter.
    If the callback is async, then it will be awaited.

    This decorator will only work if:
    - It is the last decorator in the chain
    - It is applied to a method defined on an `EmbedFillableMixin` subclass

    Only one embed Footer will be registered for a single class.
    This means that derived classes can override embed Footers, but it also means that using @embedFooter
    multiple times for the same method on a single class (e.g with typing.overload) will result in only one decorator
    being effective

    The method must return None (to clear the footer), or a 2-tuple of optional strings:
    1. The text in the footer
    2. The url for the icon of the footer

    Giving either of these as None will clear that information in the embed.

    :param prop: The method. Must belong to a class (i.e method, classmethod or property) and return an optional tuple as above
    :type prop: TEmbedFooterUrlMethod
    :raises TypeError: If `prop` is not a `property` and has a required argument
    :return: `prop`
    :rtype: TEmbedFooterUrlMethod
    """
    # See comment on casting in embedField.inner
    if isinstance(prop, property):
        _validateProperty(prop)
        return cast(TEmbedFooterUrlMethod, _PropEmbedUrlFooter(prop))

    _validateMethod(prop)
    return cast(TEmbedFooterUrlMethod, _MethodEmbedUrlFooter(prop))


TEmbedFooterFileMethod = TypeVar("TEmbedFooterFileMethod", bound=Union[property, _NoRequiredArgsInstanceMethod[Optional[Tuple[Optional[str], Optional[Union[str, Image.Image]]]]], _NoRequiredArgsClassMethod[Optional[Tuple[Optional[str], Optional[Union[str, Image.Image]]]]]])
def embedFooterFile(prop: TEmbedFooterFileMethod) -> TEmbedFooterFileMethod:
    """Mark a method, class method or property as a discord Embed Footer setter,
    with the footer icon being either the image itself, or a path to the image file on disk.
    If the callback is async, then it will be awaited.

    This decorator will only work if:
    - It is the last decorator in the chain
    - It is applied to a method defined on an `EmbedFillableMixin` subclass

    Only one embed Footer will be registered for a single class.
    This means that derived classes can override embed Footers, but it also means that using @embedFooterUrl/@embedFooterFile
    multiple times for the same method on a single class (e.g with typing.overload) will result in only one decorator
    being effective

    The method must return None (to clear the footer), or a 2-tuple:
    1. (optional) The string text in the footer
    2. (optional) Either the string path to the file on disk, or the file itself as a Pillow image

    Giving either of these as None will clear that information in the embed.

    :param prop: The method. Must belong to a class (i.e method, classmethod or property) and return an optional tuple as above
    :type prop: TEmbedFooterFileMethod
    :raises TypeError: If `prop` is not a `property` and has a required argument
    :return: `prop`
    :rtype: TEmbedFooterFileMethod
    """
    # See comment on casting in embedField.inner
    if isinstance(prop, property):
        _validateProperty(prop)
        return cast(TEmbedFooterFileMethod, _PropEmbedFileFooter(prop))

    _validateMethod(prop)
    return cast(TEmbedFooterFileMethod, _MethodEmbedFileFooter(prop))


TEmbedDescriptionMethod = TypeVar("TEmbedDescriptionMethod", bound=Union[property, _NoRequiredArgsInstanceMethod[Optional[str]], _NoRequiredArgsClassMethod[Optional[str]]])
def embedDescription(prop: TEmbedDescriptionMethod) -> TEmbedDescriptionMethod:
    """Mark a method, class method or property as a discord Embed Description setter.
    If the callback is async, then it will be awaited.

    This decorator will only work if:
    - It is the last decorator in the chain
    - It is applied to a method defined on an `EmbedFillableMixin` subclass

    Only one embed Description will be registered for a single class.
    This means that derived classes can override embed Descriptions, but it also means that using @embedDescription
    multiple times for the same method on a single class (e.g with typing.overload) will result in only one decorator
    being effective

    :param prop: The method. Must belong to a class (i.e method, classmethod or property) and return str or None
    :type prop: TEmbedDescriptionMethod
    :raises TypeError: If `prop` is not a `property` and has a required argument
    :return: `prop`
    :rtype: TEmbedDescriptionMethod
    """
    # See comment on casting in embedField.inner
    if isinstance(prop, property):
        _validateProperty(prop)
        return cast(TEmbedDescriptionMethod, _PropEmbedDescription(prop))

    _validateMethod(prop)
    return cast(TEmbedDescriptionMethod, _MethodEmbedDescription(prop))


TEmbedTitleMethod = TypeVar("TEmbedTitleMethod", bound=Union[property, _NoRequiredArgsInstanceMethod[Optional[str]], _NoRequiredArgsClassMethod[Optional[str]]])
def embedTitle(prop: TEmbedTitleMethod) -> TEmbedTitleMethod:
    """Mark a method, class method or property as a discord Embed Title setter.
    If the callback is async, then it will be awaited.

    This decorator will only work if:
    - It is the last decorator in the chain
    - It is applied to a method defined on an `EmbedFillableMixin` subclass

    Only one embed Title will be registered for a single class.
    This means that derived classes can override embed Titles, but it also means that using @embedTitle
    multiple times for the same method on a single class (e.g with typing.overload) will result in only one decorator
    being effective

    :param prop: The method. Must belong to a class (i.e method, classmethod or property) and return str or None
    :type prop: TEmbedTitleMethod
    :raises TypeError: If `prop` is not a `property` and has a required argument
    :return: `prop`
    :rtype: TEmbedTitleMethod
    """
    # See comment on casting in embedField.inner
    if isinstance(prop, property):
        _validateProperty(prop)
        return cast(TEmbedTitleMethod, _PropEmbedTitle(prop))

    _validateMethod(prop)
    return cast(TEmbedTitleMethod, _MethodEmbedTitle(prop))


TEmbedImageUrlMethod = TypeVar("TEmbedImageUrlMethod", bound=Union[property, _NoRequiredArgsInstanceMethod[Optional[str]], _NoRequiredArgsClassMethod[Optional[str]]])
def embedImageUrl(prop: TEmbedImageUrlMethod) -> TEmbedImageUrlMethod:
    """Mark a method, class method or property as a discord Embed Image setter, by the image's url.
    If the callback is async, then it will be awaited.

    This decorator will only work if:
    - It is the last decorator in the chain
    - It is applied to a method defined on an `EmbedFillableMixin` subclass
    - The method returns a url for the image

    Only one embed Image will be registered for a single class.
    This means that derived classes can override embed Images, but it also means that using @embedImage
    multiple times for the same method on a single class (e.g with typing.overload) will result in only one decorator
    being effective

    :param prop: The method. Must belong to a class (i.e method, classmethod or property) and return str or None
    :type prop: TEmbedImageUrlMethod
    :raises TypeError: If `prop` is not a `property` and has a required argument
    :return: `prop`
    :rtype: TEmbedImageUrlMethod
    """
    # See comment on casting in embedField.inner
    if isinstance(prop, property):
        _validateProperty(prop)
        return cast(TEmbedImageUrlMethod, _PropEmbedUrlImage(prop))

    _validateMethod(prop)
    return cast(TEmbedImageUrlMethod, _MethodEmbedUrlImage(prop))


TEmbedImageFileMethod = TypeVar("TEmbedImageFileMethod", bound=Union[property, _NoRequiredArgsInstanceMethod[Optional[Union[str, Image.Image]]], _NoRequiredArgsClassMethod[Optional[Union[str, Image.Image]]]])
def embedImageFile(prop: TEmbedImageFileMethod) -> TEmbedImageFileMethod:
    """Mark a method, class method or property as a discord Embed Image setter, by the image itself or the path to the image.
    If the callback is async, then it will be awaited.

    This decorator will only work if:
    - It is the last decorator in the chain
    - It is applied to a method defined on an `EmbedFillableMixin` subclass
    - The method returns a path to the image, or the image itself

    Only one embed Image will be registered for a single class.
    This means that derived classes can override embed Images, but it also means that using both @embedImage and @embedImageFile,
    or using them multiple times for the same method on a single class (e.g with typing.overload) will result in only one decorator
    being effective

    :param prop: The method. Must belong to a class (i.e method, classmethod or property) and return str, Image or None
    :type prop: TEmbedImageFileMethod
    :raises TypeError: If `prop` is not a `property` and has a required argument
    :return: `prop`
    :rtype: TEmbedImageFileMethod
    """
    # See comment on casting in embedField.inner
    if isinstance(prop, property):
        _validateProperty(prop)
        return cast(TEmbedImageFileMethod, _PropEmbedFileImage(prop))

    _validateMethod(prop)
    return cast(TEmbedImageFileMethod, _MethodEmbedFileImage(prop))


TEmbedUrlMethod = TypeVar("TEmbedUrlMethod", bound=Union[property, _NoRequiredArgsInstanceMethod[Optional[str]], _NoRequiredArgsClassMethod[Optional[str]]])
def embedUrl(prop: TEmbedUrlMethod) -> TEmbedUrlMethod:
    """Mark a method, class method or property as a discord Embed Url setter.
    If the callback is async, then it will be awaited.

    This decorator will only work if:
    - It is the last decorator in the chain
    - It is applied to a method defined on an `EmbedFillableMixin` subclass

    Only one embed Url will be registered for a single class.
    This means that derived classes can override embed Urls, but it also means that using @embedUrl
    multiple times for the same method on a single class (e.g with typing.overload) will result in only one decorator
    being effective

    :param prop: The method. Must belong to a class (i.e method, classmethod or property) and return str or None
    :type prop: TEmbedUrlMethod
    :raises TypeError: If `prop` is not a `property` and has a required argument
    :return: `prop`
    :rtype: TEmbedUrlMethod
    """
    # See comment on casting in embedField.inner
    if isinstance(prop, property):
        _validateProperty(prop)
        return cast(TEmbedUrlMethod, _PropEmbedUrl(prop))

    _validateMethod(prop)
    return cast(TEmbedUrlMethod, _MethodEmbedUrl(prop))


TEmbedFieldMethod = TypeVar("TEmbedFieldMethod", bound=Union[property, _NoRequiredArgsInstanceMethod[Any], _NoRequiredArgsClassMethod[Any]])
def embedField(fieldName: Optional[str] = None, showFirst: bool = False, showLast: bool = False, showInline: bool = True, hideWhenNone: bool = True, uniqueFieldName: bool = False):
    """Mark a method, class method or property as a discord Embed field.
    If the callback is async, then it will be awaited.

    This decorator will only work if:
    - It is the last decorator in the chain
    - It is applied to a method defined on an `EmbedFillableMixin` subclass

    If `uniqueFieldName` is True, only one embed field will be registered on the class for the given name.
    This means that derived classes can override embed fields, but it also means that using @embedField
    multiple times for the same method on a single class (e.g with typing.overload) will result in only one decorator
    being effective

    :param prop: The method. Must belong to a class (i.e method, classmethod or property)
    :type prop: TEmbedFieldMethod
    :param fieldName: Optional override for the name of the field. Defaults to the name of the method
    :type fieldname: Optional[str]
    :param bool showFirst: If `True`, this field will be at the top of the embed, along with others with this flag set (Default False)
    :param bool showLast: If `True`, this field will be at the bottom of the embed, along with others with this flag set (Default False)
    :param bool showInline: If `False`, this field will appear on its own line in the embed (Default True)
    :param bool hideWhenNone: If `True`, when the value of the field is `None`, the field will not be added to the embed (Default True)
    :param bool uniqueFieldName: If `True`, enforce only one field to be present with this name (Default False)
    :raises TypeError: If `prop` is not a `property` and has a required argument
    :raises ValueError: When simultaneously given values for mutually exclusive arguments, or when a field name is longer than 256 characters
    :return: `prop`
    :rtype: TEmbedFieldMethod
    """
    if showFirst and showLast: raise ValueError("showFirst and showLast are mutually exclusive")
    def inner(prop: TEmbedFieldMethod) -> TEmbedFieldMethod:
        # In this decorator I'm pretending to return prop but instead returning a wrapper class
        # I'm doing this because, assuming that the owning class is an EmbedFillableMixin, the metaclass
        # will replace this field with its inner, so at run time this type will actually be true
        
        if isinstance(prop, property):
            underlying = _validateProperty(prop)

            name = fieldName or underlying.__name__.title()
            if len(name) > MAX_EMBED_NAME_LENGTH:
                raise ValueError(f"Maximum embed field name length exceeded. Must be {MAX_EMBED_NAME_LENGTH} characters or less.")
            return cast(TEmbedFieldMethod, _PropEmbedField(name, prop,
                                                    showFirst=showFirst, showLast=showLast,
                                                    showInline=showInline, hideWhenNone=hideWhenNone,
                                                    uniqueFieldName=uniqueFieldName))

        underlying = _validateMethod(prop)
        
        name = fieldName or prop.__name__.title()
        if len(name) > MAX_EMBED_NAME_LENGTH:
            raise ValueError(f"Maximum embed field name length exceeded. Must be {MAX_EMBED_NAME_LENGTH} characters or less.")
        return cast(TEmbedFieldMethod, _MethodEmbedField(name, prop,
                                                showFirst=showFirst, showLast=showLast,
                                                showInline=showInline, hideWhenNone=hideWhenNone,
                                                    uniqueFieldName=uniqueFieldName))
    return inner

TClass = TypeVar("TClass", bound=Type["EmbedFillableMixin"])

def removeEmbedField(fieldName: str):
    """This decorator is applied to your class, not to its methods.
    Remove any embed fields from this class with the given name.
    This is useful for excluding an inherited field in a child class.
    Note that ALL fields with the given name will be removed.

    :param fieldName: The name of the field to remove
    :type fieldName: str
    """
    def inner(cls: TClass) -> TClass:
        fields = cls._embedFields.get(fieldName, None)
        if fields:
            del cls._embedFields[fieldName]
            for field in fields:
                cls._embedAttributes.remove(field)
        return cls
    return inner

#endregion decorators

class _EmbedFillableMeta(ABCMeta):
    """Metaclass that discovers the embed fields set on a class.
    Only use this metaclass with EmbedFillableMixin.
    
    This class is currently configured for use with EmbedFillableMixin subclasses that inherit from an abstract base class.
    If pylance gives you the following error, then you must make a copy of this that derives from your class's other metaclass,
    and a copy of EmbedFillableMixin using the new metaclass:
    `The metaclass of a derived class must be a subclass of the metaclasses of all its base classes`
    """
    def __new__(cls, clsname: str, bases: Tuple[type], attrs: Dict[str, Any]):
        unorderedEmbedAttributes: Set[_BaseEmbedAttribute] = set()
        unorderedEmbedFields: Dict[str, List[_BaseEmbedField]] = {}

        for name, att in attrs.items():
            if isinstance(att, _BaseEmbedAttribute):
                if att in unorderedEmbedAttributes:
                    # Ensure attribute-defined uniqueness if applicable
                    unorderedEmbedAttributes.remove(att)
                    
                unorderedEmbedAttributes.add(att)
                attrs[name] = att.inner

                if isinstance(att, _BaseEmbedField):
                    # Enforce field name uniqueness if applicable
                    if att.uniqueFieldName:
                        unorderedEmbedFields[att.name] = [att]
                    else:
                        unorderedEmbedFields[att.name] = unorderedEmbedFields.get(att.name, []) + [att]

        numFileEmbedAttributes = sum(1 for i in unorderedEmbedAttributes if isinstance(i, _BaseEmbedFileAttribute))
        if numFileEmbedAttributes > MAX_MESSAGE_ATTACHMENTS:
            raise ValueError(f"A maximum of {MAX_MESSAGE_ATTACHMENTS} attachments can be sent with a message, but {clsname} has {numFileEmbedAttributes} embed attributes that would require attachments. Consider using url-based image decorators instead of file-based image decorators.")

        # TODO: surely this should be Type["EmbedFillableMixin"] ?
        o = cast("EmbedFillableMixin", super().__new__(cls, clsname, bases, attrs))
        
        for base in bases:
            if issubclass(base, EmbedFillableMixin):
                for att in base._embedAttributes:
                    if att not in unorderedEmbedAttributes:
                        unorderedEmbedAttributes.add(att)
                for name, fields in base._embedFields.items():
                    if len(fields) == 0:
                        continue

                    if unorderedEmbedFields.get(name, False):
                        if unorderedEmbedFields[name][0].uniqueFieldName:
                            continue

                    # Enforce field name uniqueness if applicable
                    if fields[0].uniqueFieldName:
                        unorderedEmbedFields[name] = [fields[0]]
                    else:
                        unorderedEmbedFields[name] = unorderedEmbedFields.get(name, []) + fields

        done: Set[_BaseEmbedAttribute] = set()
        o._embedAttributes = []
        o._embedFields = {}

        # Add fields marked as showFirst
        for fields in unorderedEmbedFields.values():
            for field in fields:
                if field.showFirst:
                    o._embedFields[field.name] = o._embedFields.get(field.name, []) + [field]
                    o._embedAttributes.append(field)
                    done.add(field)
    
        # Add fields not marked as showFirst or showLast
        for fields in unorderedEmbedFields.values():
            for field in fields:
                if field not in done and not field.showFirst and not field.showLast:
                    o._embedFields[field.name] = o._embedFields.get(field.name, []) + [field]
                    o._embedAttributes.append(field)
                    done.add(field)

        # Add fields marked as showLast
        for fields in unorderedEmbedFields.values():
            for field in fields:
                if field not in done:
                    o._embedFields[field.name] = o._embedFields.get(field.name, []) + [field]
                    o._embedAttributes.append(field)
                    done.add(field)

        # Add all other embed attributes
        for att in unorderedEmbedAttributes:
            if att not in done:
                o._embedAttributes.append(att)

        return o


class EmbedFillableMixin(metaclass=_EmbedFillableMeta):
    """Mixin to allow for definition of any attribute of a discord embed,
    for example with @embedField, @embedTitle, @embedThumbnailUrl, etc.

    This method can optionally return a list of `ImageFile`s. These represent attachments that must be sent alongside
    the embed in order for any images to appear.
    Don't forget to call `.closeAll` on each of the `ImageFile`s, to avoid any memory leaks.
    
    This class is currently configured for use with subclasses that inherit from an abstract base class.
    If pylance gives you the following error, then you must make a copy of `_EmbedFillableMeta` that derives from
    your class's other metaclass, and a copy of this class that uses the new metaclass:
    `The metaclass of a derived class must be a subclass of the metaclasses of all its base classes`
    """
    _embedAttributes: List[_BaseEmbedAttribute] = []
    _embedFields: Dict[str, List[_BaseEmbedField]] = {}
    _embedColour: Optional[_BaseEmbedColour] = None

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)


    @property
    def embedFieldNames(self) -> List[str]:
        """All embed fields that this class will auto-fill onto an embed
        """
        return list(self._embedFields.keys())


    async def embedFieldValue(self, fieldName: str) -> List[Any]:
        """The current value(s) of the embed field(s) with the name `fieldName`.
        If the embedField is marked as `uniqueFieldName`, then this will return a list with one value.
        """
        if fieldName in self._embedFields:
            # If there aren't many fields with this name, read them one after another to save on overhead
            if len(self._embedFields[fieldName]) < MIN_TASKS_IN_PARALLEL:
                return [await f.getValue(self) for f in self._embedFields[fieldName]]
            
            # If there are lots of fields with this name, read them in parallel
            result = []
            tasks = Parallel()

            async def wait(f: _BaseEmbedField):
                result.append(await f.getValue(self))
            
            for f in self._embedFields[fieldName]:
                tasks.add(wait(f))

            await tasks.wait()
            tasks.raiseExceptions()
            return result
            
        raise KeyError(f"Unknown field: {fieldName}")


    async def embedColour(self) -> Colour:
        """The colour of this class's auto-fill embed.
        If no `@embedColour` is set, this currently defaults to blue.
        """
        if self._embedColour is None: return Colour.blue()
        return await self._embedColour.getValue(self) or Colour.blue()

    
    async def fillEmbed(self, embed: Embed) -> Optional[List[ImageFile]]:
        """Auto-fill this object into `embed`.

        This method can optionally return a list of `ImageFile`s. These represent attachments that must be sent alongside
        the embed in order for any images to appear.
        Don't forget to call `.closeAll` on each of the `ImageFile`s, to avoid any memory leaks.
        """
        files: List[ImageFile] = []
        
        try:
            # If there aren't many attributes, invoke them one after another to save on overhead
            if len(self._embedAttributes) < MIN_TASKS_IN_PARALLEL:
                for att in self._embedAttributes:
                    f = await att.fillEmbed(self, embed)
                    if f is not None:
                        files.append(f)

            # If there are lots of attributes, invoke them in parallel
            else:
                tasks = Parallel()

                async def wait(att: _BaseEmbedAttribute):
                    f = await att.fillEmbed(self, embed)
                    if f is not None:
                        files.append(f)
                
                for att in self._embedAttributes:
                    tasks.add(wait(att))

                await tasks.wait()
                tasks.raiseExceptions()
                
        except Exception as e:
            if files:
                for file in files:
                    file.closeAll()
            raise e
        
        return files or None
