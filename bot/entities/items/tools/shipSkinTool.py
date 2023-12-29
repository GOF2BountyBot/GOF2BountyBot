from __future__ import annotations
from typing import Optional, Union, cast, TYPE_CHECKING
from discord import Interaction

from . import toolItem
from .... import lib
from ....lib import gameMaths
from ....lib.discordUtil import interactionSend
from .... import client
from ....cfg import cfg, bbData
from ...shipSkin import ShipSkin, SerializedShipSkinUnion
from .... import botState
from ..gameItem import spawnableItem
from ....baseClasses.hasRarity import HasRarityMixin
from ....baseClasses.serializable import SerializesToSchema
from ....baseClasses.embedFillable import EmbedFillableMixin, embedField
from ....views.confirmView import ConfirmView
from ....views.viewBase import ViewCleanup

if TYPE_CHECKING:
    from ....entities.user import basedUser


class BuiltInSerializedShipSkinTool(toolItem.SerializedToolItem): pass

class TypedBuiltInSerializedShipSkinTool(toolItem.TypedSerializedToolItem): pass

class CustomSerializedShipSkinTool(toolItem.SerializedToolItem):
    skin: SerializedShipSkinUnion

class TypedCustomInSerializedShipSkinTool(CustomSerializedShipSkinTool, TypedBuiltInSerializedShipSkinTool): pass

CustomSerializedShipSkinToolUnion = Union[CustomSerializedShipSkinTool, TypedCustomInSerializedShipSkinTool]
BuiltInSerializedShipSkinToolUnion = Union[BuiltInSerializedShipSkinTool, TypedBuiltInSerializedShipSkinTool]

SerializedShipSkinToolUnion = Union[CustomSerializedShipSkinToolUnion, BuiltInSerializedShipSkinToolUnion]


@spawnableItem
class ShipSkinTool(HasRarityMixin, toolItem.ToolItem, EmbedFillableMixin, SerializesToSchema[SerializedShipSkinToolUnion]):
    """A tool that can be used to apply a skin to a ship.
    This item is named after the skin it applies.
    The manufacturer is set to the skin designer.
    This tool is single use. If a calling user is given, the tool is removed from that user's inventory after use.
    """
    def __init__(self, skin: ShipSkin, value: int = 0, wiki: str = "", icon: str = cfg.defaultShipSkinToolIcon,
            emoji: Optional[lib.emojis.BasedEmoji] = None, techLevel: int = -1, builtIn: bool = False,
            autoUse: bool = False):
        """
        :param shipSkin shipSkin: The skin that this tool applies.
        :param int value: The number of credits that this item can be bought/sold for at a shop. (Default 0)
        :param str wiki: A web page that is displayed as the wiki page for this item. If no wiki is given and shipSkin
                            has one, that will be used instead. (Default "")
        :param str icon: A URL pointing to an image to use for this item's icon (Default cfg.defaultShipSkinToolIcon)
        :param lib.emojis.BasedEmoji emoji: The emoji to use for this item's small icon
                                            (Default cfg.defaultEmojis.shipSkinTool)
        :param int techLevel: A rating from 1 to 10 of this item's technical advancement. Used as a measure for its
                                effectiveness compared to other items of the same type (Default shipSkin.averageTL)
        :param bool builtIn: Whether this is a BountyBot standard item (loaded in from bbData) or a custom spawned
                                item (Default False)
        """
        if emoji is None:
            emoji = cfg.defaultEmojis.shipSkinTool
        super().__init__(name=lib.stringUtil.shipSkinNameToToolName(skin.name.title()),
                            aliases=[skin.name, "Skin: " + skin.name, "Ship Skin " + skin.name, "Skin " + skin.name],
                            value=value, wiki=wiki if wiki else skin.wiki if skin.hasWiki else "",
                            manufacturer=skin.designer, icon=icon, emoji=emoji,
                            techLevel=techLevel if techLevel > -1 else skin.averageTL, builtIn=builtIn,
                            autoUse=autoUse, rarityLevel=skin.rarityLevel)
        self.skin = skin

#region embed fields
    
    @embedField("Skin")
    @property
    def skinName(self): return self.skin.name

    # The following fields were copied from the ShipSkin class

    @embedField("Compatible Ships")
    @property
    def compatibleShipsEmojisOrNames(self):
        if self.skin.allShips:
            return "All skinnable ships"

        compatibleShipStrs = []
        for shipName in self.skin.compatibleShips:
            shipData = bbData.builtInShipData[shipName]
            if "emoji" in shipData:
                try:
                    currentStr = lib.emojis.BasedEmoji.fromStr(shipData["emoji"], rejectInvalid=True).sendable
                except lib.exceptions.UnrecognisedCustomEmoji:
                    currentStr = shipData["name"]
            else:
                currentStr = shipData["name"]

            compatibleShipStrs.append(currentStr)
        
        return " • ".join(compatibleShipStrs[0]) if compatibleShipStrs != [] else "None"

    
    @embedField("Modified Texture Regions", hideWhenNone=True)
    @property
    def modifiedRegionsStr(self):
        return ", ".join(str(i) for i in self.skin.textureRegions) if self.skin.textureRegions else None

    
    @embedField("Disabled Texture Regions", hideWhenNone=True)
    @property
    def disabledRegionsStr(self):
        return ", ".join(str(i) for i in self.skin.disabledRegions) if self.skin.disabledRegions else None


    @embedField("Designed By", hideWhenNone=True)
    @property
    def designerStr(self):
        return lib.discordUtil.userTagOrDiscrim(self.skin.designer)

#endregion

    @toolItem.singleUse
    async def use(self, *args, callingBUser: "basedUser.BasedUser", **_) -> bool:
        """Apply the skin to the given ship.
        After use, the tool will be removed from callingBUser's inventory. To disable this, pass callingBUser as None.
        """
        if not isinstance(callingBUser, "basedUser.BasedUser"):
            raise TypeError("Required kwarg calingBUser is of the wrong type. Expected BasedUser, received " \
                            + type(callingBUser).__name__)

        ship = callingBUser.activeShip

        if ship.isSkinned:
            raise ValueError("Attempted to apply a skin to an already-skinned ship")
        if not self.skin.compatibleWithShip(ship):
            raise TypeError("The given skin is not compatible with this ship")

        ship.applySkin(self.skin)
        return True


    @toolItem.userFriendlySingleUse
    async def userFriendlyUse(self, interaction: Interaction, respond: bool, followup: bool, *args, **_) -> bool:
        """Apply the skin to the given ship.
        After use, the tool will be removed from callingBUser's inventory. To disable this, pass callingBUser as None.

        :param interaction Interaction: The discord interaction that triggered this tool use
        :returns: Whether or not the use was successful
        :rtype: bool
        """
        callingBUser = client.onboardInteractionBasedUser(interaction)
        ship = callingBUser.activeShip

        if ship.isSkinned:
            await interactionSend(interaction, respond, followup,
                                    ":x: This ship already has a skin applied! Please equip a different ship.",
                                    ephemeral=True)
            return False
        if not self.skin.compatibleWithShip(ship):
            await interactionSend(interaction, respond, followup,
                                    f":x: Your ship is not compatible with this skin! Use `/info skin {self.skin.name}` to see what ships are compatible with this skin.")
            return False

        view = ConfirmView(timeout=60, cleanup=ViewCleanup.disableAll, respondOnCleanup=True)

        confirmContent = f"Are you sure you want to apply the {self.skin.name} skin to your {ship.getNameAndNick()}?"
        await interactionSend(interaction, respond, followup, confirmContent, view=view)
        
        if await view.wait():
            await view.interaction.edit_original_response(content=confirmContent + "\n\n🛑 Skin application cancelled - out of time!")
        elif not view.confirmed:
            await view.interaction.edit_original_response(content=confirmContent + "\n\n🛑 Skin application cancelled.")
        else:
            ship.applySkin(self.skin)
            if self in callingBUser.inactiveTools:
                callingBUser.inactiveTools.removeItem(self)

            await view.interaction.edit_original_response(content="🎨 Success! Your skin has been applied.")
            return True
            
        return False


    def statsStringShort(self) -> str:
        """Summarise all the statistics and functionality of this item as a string.

        :return: A string summarising the statistics and functionality of this item
        :rtype: str
        """
        # The designer field has been hidden until the community workshop becomes available.
        return f"*{self.rarityLevelStr}*"
        if self.skin.designerId != -1 and (user := botState.client.get_user(self.skin.designerId)):
            return f"*Designer: {user.display_name}*"
        return "*Designer: user #" + str(self.manufacturer) + "*"


    def serialize(self, **kwargs) -> SerializedShipSkinToolUnion:
        """

        :param bool saveType: When true, include the string name of the object type in the output.
        """
        data = super().serialize(**kwargs)
        if self.builtIn:
            data["name"] = self.skin.name
        else:
            # Casting here because we know that the tool is not builtIn
            data = cast(CustomSerializedShipSkinTool, data)
            data["skin"] = self.skin.serialize(**kwargs)
        return data


    @classmethod
    def deserialize(cls, toolDict: SerializedShipSkinToolUnion, **kwargs) -> ShipSkinTool:
        """Construct a shipSkinTool from its dictionary-serialized representation.

        :param dict toolDict: A dictionary containing all information needed to construct the required shipSkinTool.
                                Critically, a name and builtIn specifier.
        :return: A new shipSkinTool object as described in toolDict
        :rtype: shipSkinTool
        """
        if toolDict["builtIn"]:
            m = bbData.builtInToolObjs[lib.stringUtil.shipSkinNameToToolName(toolDict["name"])]
            if isinstance(m, ShipSkinTool): return m
            raise TypeError(f"tool {m.name} is not a {ShipSkinTool.__name__}, it is a {type(m).__name__}")
        
        # Casting here because we know that the tool is not builtIn
        toolDict = cast(CustomSerializedShipSkinToolUnion, toolDict)
        skin = ShipSkin.deserialize(toolDict["skin"])
        return ShipSkinTool(skin, value=gameMaths.shipSkinValueForTL(skin.averageTL), builtIn=False)
