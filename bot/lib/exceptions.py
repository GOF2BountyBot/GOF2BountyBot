import traceback
from typing import Optional

def formatExceptionTrace(e: BaseException) -> str:
    """Formats the trace for an exception into a string.
    Great for debugging errors that are swallowed by the event loop.

    :param Exception e: The exception whose stack trace to format
    :return: The stack trace for e, formatted into a string
    :rtype: str
    """
    return "".join(traceback.format_exception(type(e), e, e.__traceback__))


class UnrecognisedCustomEmoji(Exception):
    """Exception raised when creating a BasedEmoji instance, but the client could not match an emoji to the given ID.

    :var id: The ID that could not be matched
    :vartype id: int
    """

    def __init__(self, comment: str, id: int):
        """
        :param str comment: Description of the exception
        :param int id: The ID that could not be matched
        """
        super().__init__(comment)
        self.id = id


class UnrecognisedEmojiFormat(Exception):
    """Exception raised when creating a BasedEmoji from a string,
    but the string could not be pattern-matched as an emoji.
    Unfortunately this will also get raised when using an emoji that is not registered with the emoji consortium,
    because I can't disambiguate this case.

    :var char: The string that does not look like an emoji
    :vartype char: str
    """

    def __init__(self, comment: str, char: str):
        """
        :param str comment: Description of the exception
        :param str char: The string which does not look like an emoji
        """
        super().__init__(comment)
        self.char = char


class IncorrectCommandCallContext(Exception):
    """Exception used to indicate when a non-DMable command is called from DMs.
    May be used in the future to indicate the opposite; a command that can only be called from DMs is
    called from outside of DMs.
    """
    pass


class IncorrectInteractionContext(Exception):
    """Exception used to indicate when an interaction is triggered from somewhere it shouldn't, e.g in DMs,
    or in a non-messageable channel.
    """
    pass


class NoneDCGuildObj(Exception):
    """Raised when constructing a guild object, but the corresponding dcGuild was either not given or invalid.
    """
    pass


class InvalidGameObjectFolder(Exception):
    """Raised when attempting to load in a game object configuration folder with
    """
    def __init__(self, filePath, reason):
        super().__init__("Invalid game object configuration folder (" + reason + "): " + str(filePath))
        self.filePath = filePath
        self.reason = reason


class NoLongerExists(Exception):
    """Raised when initializing a bountyboardchannel but couldnt find the channel to load
    """
    pass


class NotReady(Exception):
    """Raised when attempting to perform an action on the client when the client is not ready yet.
    E.g:
    - databases not loaded yet
    - client not logged in yet
    """
    pass


class ClientInitFailed(Exception):
    """Raised when initialization of the discord client fails.
    """
    def __init__(self, inner: Exception) -> None:
        self.inner = inner
        super().__init__("Initialization of the discord client failed due to the following exception:\n" \
                        + formatExceptionTrace(inner))


class SharedCogNotLoaded(Exception):
    """Raised when trying to use a utility cog that is not loaded. This is a special-case exception, because it shouldn't really happen.
    """
    def __init__(self, cogName: str):
        super().__init__("Shared cog is not loaded: " + cogName)


class UnknownItem(Exception):
    """Raised when attempting to look up an item in the database, but it was not found.
    """
    def __init__(self, itemId: Optional[int] = None, itemType: Optional[str] = None, itemName: Optional[str] = None, *args: object) -> None:
        super().__init__(*args)
        self.itemType = itemType
        self.itemName = itemName
        self.itemId = itemId