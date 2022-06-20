from ...baseClasses.serializable import Serializable
from ...lib.emojis import BasedEmoji


class Medal(Serializable):
    """A non-functional cosmetic appearing at the top of a user's profile.
    Medals are used to commend users for special achievements which cannot be achieved through
    normal play. E.g contributing to development.

    Medals are not used for normal playing achievements. These will be handled by "achievements" later down the line.

    :var name: The name of the medal
    :vartype name: str
    :var desc: A short description of why the medal was awarded
    :vartype desc: str
    :var icon: An image representing the medal
    :vartype icon: str
    :var emoji: An emoji representing the medal, usually the same appearance as icon
    :vartype emoji: BasedEmoji
    :var wiki: A URL adding extra semantics to the medal
    :vartype wiki: str
    :var hasWiki: Whether or not this medal has a wiki link
    :vartype hasWiki: bool
    """

    def __init__(self, name: str, desc: str, icon: str, emoji: BasedEmoji, wiki: str = ""):
        """
        :param str name: The name of the medal
        :param str desc: A short description of why the medal was awarded
        :param str icon: An image representing the medal
        :param BasedEmoji emoji: An emoji representing the medal, usually the same appearance as icon
        :param str wiki: A URL adding extra semantics to the medal (Default "")
        """
        self.name = name
        self.desc = desc
        self.icon = icon
        self.wiki = wiki
        self.hasWiki = wiki != ""
        self.emoji = emoji


    def serialize(self, **kwargs) -> dict:
        """Serialize this medal into dictionary format.

        :return: A dictionary fully describing this medal and its attriutes
        :rtype: dict
        """
        data = {"name": self.name, "desc": self.desc, "icon": self.icon, "emoji": self.emoji.serialize()}
        if self.hasWiki:
            data["wiki"] = self.wiki
        return data


    @classmethod
    def deserialize(cls, data: dict, **kwargs) -> "Medal":
        """Deserialize a Medal instance.

        :param dict data: A dictionary describing all desired attributes of the Medal
        :return: A new Medal instance with the attributes described in data
        :rtype: Medal
        """
        return Medal(**cls._makeDefaults(data, emoji=BasedEmoji.deserialize(data["emoji"])))
