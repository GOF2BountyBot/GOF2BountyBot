from ..cfg import bbData, cfg
import os
from ..shipRenderer import shipRenderer
from .. import lib
from discord import File
from typing import Dict, List
from ..baseClasses.serializable import Serializable
from ..baseClasses.hasRarity import HasRarityMixin
from .items import shipItem
from os.path import join
from .gameObject import LoadedObject
from ..baseClasses.serializable import JsonType


def _saveShip(ship):
    shipData = bbData.builtInShipData[ship]
    shipTL = shipData["techLevel"]
    shipPath = shipData["path"]
    del shipData["techLevel"]
    del shipData["path"]
    shipData["builtIn"] = False
    lib.jsonHandler.writeJSON(join(shipPath, "META.json"), shipData, prettyPrint=True)
    shipData["builtIn"] = True
    shipData["techLevel"] = shipTL
    shipData["saveDue"] = False
    shipData["path"] = shipPath


class ShipSkin(HasRarityMixin, LoadedObject):
    def __init__(self, name: str, textureRegions: List[int], shipRenders: Dict[str, str],
                    path: str, designer: str, wiki: str = "", disabledRegions: List[int] = [],
                    allShips: bool = False, rarityLevel: int = 0, builtIn: bool = False,
                    designerId: int = -1):

        self.allShips = allShips
        self.name = name
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
        self.wiki = wiki
        self.hasWiki = wiki != ""
        self.disabledRegions = disabledRegions
        for region in disabledRegions:
            if region < 1:
                raise ValueError("Attempted to disable an invalid region number: " + str(region) + ", skin " + name)
        
        super().__init__(rarityLevel, builtIn=builtIn)


    def serialize(self, ignoreBuiltIn: bool = False, **kwargs) -> JsonType:
        """Serialize this ship skin to dictionary.

        :param bool ignoreBuiltIn: When True, the serializer will serialize fully, ignoring
                                    potential field-savings from the builtIn field (Default False)
        :return: A dictionary which can be deserialized into a copy of this ShipSkin object
        :rtype: dict
        """
        if ignoreBuiltIn:
            data = {"name": self.name, "textureRegions": self.textureRegions,
                    "ships": self.shipRenders, "rarityLevel": self.rarityLevel}
            if self.designer:
                data["designer"] = self.designer
            if self.designerId != -1:
                data["designerId"] = self.designerId
        else:
            data = {"name": self.name, "builtIn": self.builtIn}

        if ignoreBuiltIn or not self.builtIn:
            if self.hasWiki:
                data["wiki"] = self.wiki
            if self.disabledRegions:
                data["disabledRegions"] = self.disabledRegions
            if self.allShips:
                data["allShips"] = True

        return data


    def _updateItemMETA(self, **kwargs):
        lib.jsonHandler.writeJSON(join(self.path, "META.json"), self.serialize(ignoreBuiltIn=True, **kwargs),
                                    prettyPrint=True)

    
    def compatibleWithShip(self, ship: "shipItem.Ship") -> bool:
        """Decide whether this skin is compatible with a given ship.

        :param ship: The ship to check for compatibility
        :type ship: shipItem.Ship
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

            await shipRenderer.renderShip(self.name, shipData["path"], shipData["model"], textureFiles, regionsToDisable,
                                            cfg.skinRenderIconResolution[0], cfg.skinRenderIconResolution[1], cfg.skinRenderIconSamples)

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

        if self.name not in shipData["compatibleSkins"]:
            shipData["compatibleSkins"].append(self.name.lower())

        _saveShip(ship)
        self._updateItemMETA()


    async def removeShip(self, ship, rendersChannel):
        if ship not in bbData.builtInShipData:
            raise KeyError("Ship not found: '" + str(ship) + "'")

        shipData = bbData.builtInShipData[ship]

        if ship in self.compatibleShips:
            self.compatibleShips.remove(ship)

        if self.name in shipData["compatibleSkins"]:
            try:
                os.remove(join(shipData["path"], "skins", self.name + ".png"))
            except FileNotFoundError:
                pass
            shipData["compatibleSkins"].remove(self.name.lower())

        if ship in self.shipRenders:
            # renderMsg = await rendersChannel.fetch_message(self.shipRenders[ship][1])
            # await renderMsg.delete()
            del self.shipRenders[ship]

        _saveShip(ship)
        self._updateItemMETA()


    @classmethod
    def deserialize(cls, skinDict: dict, **kwargs):
        if skinDict.get("builtIn", False):
            return bbData.builtInShipSkins[skinDict["name"]]
        return ShipSkin(**cls._makeDefaults(skinDict, ignores=("ships", "type"), shipRenders=skinDict["ships"]))
