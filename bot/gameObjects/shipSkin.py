import os
from os.path import join
from typing import Dict, List, Union, cast
from typing_extensions import NotRequired
from discord import Colour, File

from .. import lib, botState
from ..baseClasses.hasRarity import HasRarityMixin, SerializedWithRarity
from ..baseClasses.serializable import JsonType, SerializesToSchema
from ..baseClasses.embedFillable import embedColour, embedField, embedFooterUrl, embedThumbnailUrl, embedTitle
from bot.cfg import bbData, cfg
from ..shipRenderer import shipRenderer
from .gameObject import LoadedObject, SerializedLoadedObject
from .items.ships import shipBase


class BuiltInSerializedShipSkin(SerializedLoadedObject, SerializedWithRarity):
    ships: NotRequired[Dict[str, str]]

class TypedBuiltInSerializedShipSkin(BuiltInSerializedShipSkin):
    type: str

class CustomSerializedShipSkin(BuiltInSerializedShipSkin):
    textureRegions: List[int]
    designer: NotRequired[str]
    designerId: NotRequired[int]
    disabledRegions: NotRequired[List[int]]
    allShips: NotRequired[bool]

class TypedCustomSerializedShipSkin(CustomSerializedShipSkin, TypedBuiltInSerializedShipSkin): pass

SerializedShipSkinUnion = Union[BuiltInSerializedShipSkin, TypedBuiltInSerializedShipSkin, CustomSerializedShipSkin, TypedCustomSerializedShipSkin]


def _saveShip(ship):
    shipData = bbData.builtInShipData[ship]
    shipTL = shipData.get("techLevel", None)
    shipPath = shipData.get("path", None)
    if shipPath is None:
        raise KeyError("Missing path for ship " + ship.name)
    # TODO: Ignoring for these fields because they are dynamically generated when loaded, and so they are not stored to file
    # This will be solved by the introduction of some 'ShipBlueprint' type to represent stored ship configurations
    del shipData["techLevel"] # type: ignore[reportGeneralTypeIssues]
    del shipData["path"] # type: ignore[reportGeneralTypeIssues]
    shipData["builtIn"] = False
    # TODO: "CustomSerializedShip" is incompatible with "JsonType"
    lib.jsonHandler.writeJSON(join(shipPath, "META.json"), cast(JsonType, shipData), prettyPrint=True)
    shipData["builtIn"] = True
    if shipTL is not None:
        shipData["techLevel"] = shipTL
    shipData["saveDue"] = False
    shipData["path"] = shipPath


class ShipSkin(HasRarityMixin, LoadedObject, SerializesToSchema[SerializedShipSkinUnion]):
    def __init__(self, name: str, textureRegions: List[int], shipRenders: Dict[str, str],
                    path: str, designer: str, wiki: str = "", disabledRegions: List[int] = [],
                    allShips: bool = False, rarityLevel: int = 0, builtIn: bool = False,
                    designerId: int = -1):

        self.allShips = allShips
        self.textureRegions = textureRegions
        self.compatibleShips = list(shipRenders.keys())
        self.shipRenders = shipRenders
        self.path = path

        if len(self.compatibleShips) > 0:
            self.averageTL = sum(bbData.builtInShipData[i]["techLevel"] \
                                for i in self.compatibleShips \
                                if i in bbData.builtInShipData)
            self.averageTL = int(self.averageTL / len(self.compatibleShips))
        else:
            self.averageTL = -1

        self.designer = designer
        self.designerId = designerId
        self.disabledRegions = disabledRegions
        for region in disabledRegions:
            if region < 1:
                raise ValueError("Attempted to disable an invalid region number: " + str(region) + ", skin " + name)
        
        super().__init__(rarityLevel, builtIn=builtIn, wiki=wiki, name=name)

    
    @embedField("Compatible Ships")
    def compatibleShipsEmojisOrNames(self):
        if self.allShips:
            return "All skinnable ships"

        compatibleShipStrs = []
        for shipName in self.compatibleShips:
            shipData = bbData.builtInShipData[shipName]
            if "emoji" in shipData:
                try:
                    currentStr = lib.emojis.BasedEmoji.fromStr(shipData["emoji"], rejectInvalid=True).sendable
                except lib.exceptions.UnrecognisedCustomEmoji:
                    currentStr = shipData["name"]
            else:
                currentStr = shipData["name"]

            compatibleShipStrs.append(currentStr)
        
        return " • ".join(compatibleShipStrs) if compatibleShipStrs != [] else "None"

    
    @embedField("Modified Texture Regions", hideWhenNone=True)
    @property
    def modifiedRegionsStr(self):
        return (f"Region{'' if len(self.textureRegions) == 1 else 's'} " + ", ".join(str(i) for i in self.textureRegions)) if self.textureRegions else None

    
    @embedField("Disabled Texture Regions", hideWhenNone=True)
    @property
    def disabledRegionsStr(self):
        return ", ".join(str(i) for i in self.disabledRegions) if self.disabledRegions else None


    @embedField("Designed By", hideWhenNone=True)
    @property
    def designerStr(self):
        user = botState.client.get_user(self.designerId)
        return self.designer if user is None else f"{user.name}#{user.discriminator}"

    
    @embedThumbnailUrl
    @property
    def embedThumbnail(self): return cfg.defaultShipSkinToolIcon

    
    @embedFooterUrl
    @property
    def embedFooter(self): return ("Preview this skin with the /showme command.", None)

    
    @embedTitle
    @property
    def formattedName(self): return self.name.title()

    
    @embedColour
    def embedColour(self): return Colour(cfg.itemRarityColours[self.rarityLevel])


    def serialize(self, ignoreBuiltIn: bool = False, **kwargs) -> SerializedShipSkinUnion:
        """Serialize this ship skin to dictionary.

        :param bool ignoreBuiltIn: When True, the serializer will serialize fully, ignoring
                                    potential field-savings from the builtIn field (Default False)
        :return: A dictionary which can be deserialized into a copy of this ShipSkin object
        :rtype: dict
        """
        data: SerializedShipSkinUnion = {"name": self.name, "builtIn": self.builtIn, "rarityLevel": self.rarityLevel}

        if ignoreBuiltIn or not self.builtIn:
            # casting here so I can add the new fields
            data = cast(CustomSerializedShipSkin, data)
            data.update({"name": self.name, "textureRegions": self.textureRegions,
                    "ships": self.shipRenders, "rarityLevel": self.rarityLevel,
                    "builtIn": self.builtIn})

            if self.designer:
                data["designer"] = self.designer

            if self.designerId != -1:
                data["designerId"] = self.designerId

            if self.hasWiki:
                data["wiki"] = self.wiki
            
            if self.disabledRegions:
                data["disabledRegions"] = self.disabledRegions
            
            if self.allShips:
                data["allShips"] = True

        return data


    def _updateItemMETA(self, **kwargs):
        data = self.serialize(ignoreBuiltIn=True, **kwargs)
        # TODO: casting here because TypedDicts are not JsonType
        lib.jsonHandler.writeJSON(join(self.path, "META.json"), cast(JsonType, data),
                                    prettyPrint=True)

    
    def compatibleWithShip(self, ship: "shipBase.ShipBase") -> bool:
        """Decide whether this skin is compatible with a given ship.

        :param ship: The ship to check for compatibility
        :type ship: baseShip.BaseShip
        :return: True if ship is skinnable and compatible with this skin, False otherwise
        :rtype: bool
        """
        if ship.name not in bbData.builtInShipData:
            return ship.name in self.compatibleShips

        return bbData.builtInShipData[ship.name]["skinnable"] and (self.allShips or ship.name in self.compatibleShips)


    async def addShip(self, ship, rendersChannel):
        if ship not in bbData.builtInShipData:
            raise KeyError("Ship not found: '" + str(ship) + "'")

        shipData = bbData.builtInShipData[ship]

        if not shipData["skinnable"]:
            raise ValueError("Attempted to render a skin onto an non-skinnable ship: '" + str(ship) + "'")

        if ship not in self.shipRenders:
            _outputSkinFile = join(shipData["path"], "skins", self.name)
            renderPath = _outputSkinFile + "-RENDER.png"
            # emojiRenderPath = _outputSkinFile + "_emoji-RENDER.png"
            texPath = _outputSkinFile + ".jpg"
            # emojiTexPath = _outputSkinFile + "_emoji.jpg"

            # if not os.path.isfile(renderPath):
            textureFiles = {0: join(self.path, "1.jpg")}

            for textureNum in self.textureRegions:
                if textureNum <= shipData["textureRegions"]:
                    textureFiles[textureNum] = join(self.path, str(textureNum + 1) + ".jpg")

            regionsToDisable = []
            if "textureRegions" in shipData and shipData["textureRegions"] > 0:
                for disabledRegionNum in self.disabledRegions:
                    if disabledRegionNum <= shipData["textureRegions"]:
                        regionsToDisable.append(disabledRegionNum)

            await shipRenderer.renderShip(shipData["path"], shipData["model"], textureFiles, regionsToDisable,
                                            cfg.skinRenderIconResolution[0], cfg.skinRenderIconResolution[1],
                                            cfg.skinRenderIconSamples, renderPath, texPath)

            # == Scrapped code for creating custom emojis for each ship reskin ==
            # await shipRenderer.renderShip(self.name + "_emoji", shipData["path"], shipData["model"], [texPath],
            #                               cfg.skinRenderEmojiResolution[0], cfg.skinRenderEmojiResolution[1])
            # os.remove(emojiTexPath)

            # with open(emojiRenderPath, "rb") as f:
            #     newEmoji = await rendersChannel.guild.create_custom_emoji(name=ship + "_+" + self.name, image=f.read(),
            #                                                               reason="New skin '" + self.name \
            #                                                                       + "' registered for ship '" + ship + "'")

            with open(renderPath, "rb") as f:
                renderMsg = await rendersChannel.send(ship + " +" + self.name, file=File(f))
                # If saving emoji renders of skins, also save the emoji in here: str(newEmoji)
                self.shipRenders[ship] = renderMsg.attachments[0].url
            os.remove(renderPath)
            os.remove(texPath)

        if ship not in self.compatibleShips:
            self.compatibleShips.append(ship)

        if self.name not in shipData.get("compatibleSkins", []):
            shipData["compatibleSkins"] = shipData.get("compatibleSkins", []) + [self.name.lower()]

        _saveShip(ship)
        self._updateItemMETA()


    async def removeShip(self, ship, rendersChannel):
        if ship not in bbData.builtInShipData:
            raise KeyError("Ship not found: '" + str(ship) + "'")

        shipData = bbData.builtInShipData[ship]

        if ship in self.compatibleShips:
            self.compatibleShips.remove(ship)

        if self.name in shipData.get("compatibleSkins", []):
            try:
                os.remove(join(shipData["path"], "skins", self.name + ".png"))
            except FileNotFoundError:
                pass
            shipData["compatibleSkins"] = shipData.get("compatibleSkins", [])
            shipData["compatibleSkins"].remove(self.name.lower())

        if ship in self.shipRenders:
            # renderMsg = await rendersChannel.fetch_message(self.shipRenders[ship][1])
            # await renderMsg.delete()
            del self.shipRenders[ship]

        _saveShip(ship)
        self._updateItemMETA()


    @classmethod
    def deserialize(cls, skinDict: SerializedShipSkinUnion, **kwargs):
        if skinDict.get("builtIn", False):
            return bbData.builtInShipSkins[skinDict["name"]]
        return ShipSkin(**cls._makeDefaults(skinDict, ignores=("ships", "type"), shipRenders=skinDict.get("ships", {})))
