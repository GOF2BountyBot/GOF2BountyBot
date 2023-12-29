from typing import Dict, List, cast, Collection

import os
from os.path import join

from discord import Colour, File, TextChannel

from sqlalchemy.orm import Mapped, DeclarativeBase, relationship, mapped_column, attribute_keyed_dict
from sqlalchemy import Table, Column, ForeignKey, String
from sqlalchemy.ext.asyncio import AsyncAttrs

from ....lib.tempFolder import TempFolder
from ....baseClasses.hasRarity import HasRarityMixin
from ....baseClasses.serializable import SerializesToSchema
from ....baseClasses.embedFillable import embedColour, embedField, embedFooterUrl, embedThumbnailUrl, EmbedFillableMixin
from ....cfg import bbData, cfg
from ....shipRenderer import shipRenderer
from ...base.workshopable import Workshopable
from . import shipSpec
from ....database.tables import TableNames
from ....database.constants import ShipSkinRegion, ShipSkinMethod
from ....assetManager import AssetType, Asset
from .shipSkin_json import SerializedShipSkinUnion, SerializedBaseClasses, AnySerializedShipSkin


class Base(DeclarativeBase, AsyncAttrs):
    pass


shipHasCompatibleSkin = Table(
    TableNames.ShipHasCompatibleSkin.value,
    Base.metadata,
    Column(ForeignKey(f"{TableNames.ShipSpec.value}.id")),
    Column(ForeignKey(f"{TableNames.ShipSkin.value}.id")),
)


REGIONS_LIST_SEPARATOR: str = ";"


ShipSkinRenderMessage = Table(
    TableNames.HostedShipSkinRenderOutput.value,
    Base.metadata,
    Column("shipInstanceId", ForeignKey(f"{TableNames.ShipInstance.value}.id"), primary_key=True),
    Column("shipSkinId", ForeignKey(f"{TableNames.ShipSkin.value}.id"), primary_key=True),
    Column("url", String)
)


class ShipSkin(Base, HasRarityMixin, Workshopable, EmbedFillableMixin, SerializesToSchema[SerializedShipSkinUnion]):
    id: Mapped[int]
    allShips: Mapped[bool]
    _compatibleShips: Mapped[List["shipSpec.ShipSpec"]] = relationship(secondary=shipHasCompatibleSkin, back_populates="_compatibleSkins")
    method: Mapped[ShipSkinMethod]
    _diffuseSkinnedRegions: Mapped[str] = mapped_column("diffuseSkinnedRegions")
    _diffuseDisabledRegions: Mapped[str] = mapped_column("diffuseDisabledRegions")

    _hostedRenders: Mapped[Dict[int, str]] = relationship(
        secondary=ShipSkinRenderMessage,
        collection_class=attribute_keyed_dict("shipInstanceId"))
    
    @property
    async def hostedRenders(self) -> Dict[int, str]:
        return await self.awaitable_attrs._hostedRenders


    @property
    def diffuseSkinnedRegions(self) -> Collection[ShipSkinRegion]:
        """The list of ship texture regions modified by this skin. This only applies if the skin method is autoskin.

        This is currently represented in the database by serializing to a string, and so it is not usable in queries.
        The moment this needs to be available in queries, we will need to put it in another table, and update all refernces
        to instead use AsyncAttrs.
        """
        return [ShipSkinRegion(int(i)) for i in self._diffuseSkinnedRegions.split(REGIONS_LIST_SEPARATOR)]


    @diffuseSkinnedRegions.setter
    def set_diffuseSkinnedRegions(self, value: Collection[ShipSkinRegion]):
        self._diffuseSkinnedRegions = REGIONS_LIST_SEPARATOR.join(str(i) for i in value)


    @property
    def diffuseDisabledRegions(self) -> Collection[ShipSkinRegion]:
        """The list of ship texture regions disabled by this skin. This only applies if the skin method is autoskin.

        This is currently represented in the database by serializing to a string, and so it is not usable in queries.
        The moment this needs to be available in queries, we will need to put it in another table, and update all refernces
        to instead use AsyncAttrs.
        """
        return [ShipSkinRegion(int(i)) for i in self._diffuseDisabledRegions.split(REGIONS_LIST_SEPARATOR)]


    @diffuseDisabledRegions.setter
    def set_diffuseDisabledRegions(self, value: Collection[ShipSkinRegion]):
        self._diffuseDisabledRegions = REGIONS_LIST_SEPARATOR.join(str(i) for i in value)


    @property
    async def compatibleShips(self) -> List["shipSpec.ShipSpec"]:
        return await self.awaitable_attrs._compatibleShips
    

    @compatibleShips.setter
    def setCompatibleShips(self, value: List["shipSpec.ShipSpec"]):
        self._compatibleShips = value

    
    @embedField("Compatible Ships")
    async def compatibleShipsEmojisOrNames(self):
        if self.allShips:
            return "All skinnable ships"

        compatibleShipStrs = []
        ships: List["shipSpec.ShipSpec"] = await self.compatibleShips
        for ship in ships:
            if ship.emoji is not None and ship.emoji.verifyCustom():
                currentStr = ship.emoji.sendable
            else:
                currentStr = ship.name

            compatibleShipStrs.append(currentStr)
        
        return " • ".join(compatibleShipStrs) if compatibleShipStrs != [] else "None"

    
    @embedField("Modified Texture Regions", hideWhenNone=True)
    @property
    def modifiedRegionsStr(self):
        if not self.diffuseSkinnedRegions:
            return None
        return ", ".join(i.name for i in self.diffuseSkinnedRegions)

    
    @embedField("Disabled Texture Regions", hideWhenNone=True)
    @property
    def disabledRegionsStr(self):
        if not self.diffuseDisabledRegions:
            return None
        return ", ".join(i.name for i in self.diffuseDisabledRegions)

    
    @embedThumbnailUrl
    @property
    def embedThumbnail(self): return cfg.defaultShipSkinToolIcon

    
    @embedFooterUrl
    @property
    def embedFooter(self): return ("Preview this skin with the /showme command.", None)

    
    @embedColour
    def embedColour(self): return Colour(cfg.itemRarityColours[self.rarityLevel])


    @property
    def renderFileName(self):
        return f"{self.id}.png"


    async def serialize(self, **kwargs) -> SerializedShipSkinUnion:
        """Serialize this ship skin to dictionary.

        :return: A dictionary which can be deserialized into a copy of this ShipSkin object
        :rtype: dict
        """
        baseData = cast(SerializedBaseClasses, await super().serialize(**kwargs))

        data: AnySerializedShipSkin = {
            **baseData,
            "allShips": self.allShips,
            "diffuse": {"skinnedRegions": [i.name for i in self.diffuseSkinnedRegions]},
            "method": self.method.name
        }

        if not self.allShips:
            compatibleShips = await self.compatibleShips
            data["compatibleShips"] = [s.id for s in compatibleShips]

        if self.method is ShipSkinMethod.autoskin:
            data["diffuse"]["disabledRegions"] =  [i.name for i in self.diffuseDisabledRegions]

        return cast(SerializedShipSkinUnion, data)

    
    async def compatibleWithShip(self, ship: "shipSpec.ShipSpec") -> bool:
        """Decide whether this skin is compatible with a given ship.

        :param ship: The ship to check for compatibility
        :type ship: baseShip.BaseShip
        :return: True if ship is skinnable and compatible with this skin, False otherwise
        :rtype: bool
        """
        if not ship.skinnable:
            return False
        
        compatibleShips = await self.compatibleShips
        return self.allShips or any(i.id == ship.id for i in compatibleShips)


    async def addShip(self, ship: "shipSpec.ShipSpec", rendersChannel: TextChannel):
        if not ship.skinnable:
            raise ValueError(f"Attempted to render a skin onto an non-skinnable ship: '{ship.name}' ({ship.id})")
        
        if self.compatibleWithShip(ship):
            raise ValueError(f"Ship '{ship.name}' ({ship.id}) is already compatible with this skin '{self.name}' ({self.id})")
        
        textureOutput = f"{ship.id}-{self.id}.jpg"
        newRenderAsset = Asset(AssetType.shipSkinRender, self.renderFileName, ship.id)
        
        skinTextures: Dict[ShipSkinRegion, Asset] = {}
        regionsToDisable: List[ShipSkinRegion] = []
        
        if ship.skinnableTextureRegions:
            for textureRegion in self.diffuseSkinnedRegions:
                if textureRegion in ship.skinnableTextureRegions:
                    skinTextures[textureRegion] = Asset(AssetType.shipskinAutoskinTexture, f"{textureRegion.value}.jpg", self.id)

            for textureRegion in self.diffuseDisabledRegions:
                if textureRegion in ship.skinnableTextureRegions:
                    regionsToDisable.append(textureRegion)

        # I'm allowing up to 30 seconds to write to this file, just in case a render takes a long time.
        # We might even need to increase this later.
        async with newRenderAsset.enterTransientReadWrite(lifetimeMs=30000):
            with TempFolder.Random() as temp:
                await shipRenderer.renderShip(
                    ShipSkinMethod.autoskin, ship.id,
                    cfg.skinRenderIconResolution[0], cfg.skinRenderIconResolution[1], cfg.skinRenderIconSamples,
                    str(newRenderAsset.path), textureOutputPath=join(temp.path, textureOutput),
                    diffusePaths={r: str(a.path) for r, a in skinTextures.items()},
                    diffuseDisabled=regionsToDisable)

        # I'm not reusing the existing RW lease, just in case something else is waiting to read this as well
        async with newRenderAsset.enterTransientRead():
            with open(newRenderAsset.path, "rb") as f:
                renderMsg = await rendersChannel.send(ship.name + " +" + self.name, file=File(f))
                # If saving emoji renders of skins, also save the emoji in here: str(newEmoji)
                self._hostedRenders[ship.id] = renderMsg.attachments[0].url

        self._compatibleShips.append(ship)


    async def removeShip(self, ship: "shipSpec.ShipSpec", rendersChannel: TextChannel):
        if not ship in await self.compatibleShips:
            raise KeyError(f"Ship {ship.name} ({ship.id}) is not compatible with skin {self.name} ({self.id})")
        
        renderAsset = Asset(AssetType.shipSkinRender, self.renderFileName, ship.id)
        async with renderAsset.enterTransientReadWrite(lifetimeMs=1000):
            os.remove(renderAsset.path)

        self._compatibleShips.remove(ship)
        self._hostedRenders.pop(ship.id)
        # renderMsg = await rendersChannel.fetch_message((await self.hostedRenders)[ship.id])[0]
        # await renderMsg.delete()


    @classmethod
    def deserialize(cls, skinDict: SerializedShipSkinUnion, **kwargs):
        return ShipSkin(**cls._makeDefaults(skinDict, ignores=("ships", "type"), shipRenders=skinDict.get("ships", {})))
