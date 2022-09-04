from __future__ import annotations
from typing import List, Dict, TypedDict, cast
from discord import Guild, Interaction
from concurrent.futures import ThreadPoolExecutor
import os

from ..users import basedGuild
from . import bountyDB
from .. import botState, lib
from .. import lib
from ..logging import LogCategory
from ..baseClasses.serializable import SerializesToType
from ..logging import LogCategory
from ..gameObjects import guildShop


_minGuildsToParallelize = os.cpu_count()
_minGuildsToParallelize = None if _minGuildsToParallelize is None else \
                            (_minGuildsToParallelize + (_minGuildsToParallelize % 2)) // 2


class GuildDB(SerializesToType[Dict[int, basedGuild.SerializedBasedGuildUnion]]):
    """A database of BasedGuilds.

    :var guilds: Dictionary of guild.id to guild, where guild is a BasedGuild
    :vartype guilds: dict[int, BasedGuild]
    """

    def __init__(self):
        # Store guilds as a dict of guild.id: guild
        self.guilds: Dict[int, basedGuild.BasedGuild] = {}


    def getIDs(self) -> List[int]:
        """Get a list of all guild IDs in the database.

        :return: A list containing all guild IDs (ints) stored in the database.
        :rtype: list
        """
        return list(self.guilds.keys())


    def getGuilds(self) -> List[basedGuild.BasedGuild]:
        """Get a list of all BasedGuilds in the database.

        :return: A list containing all BasedGuild objects stored in the database
        :rtype: list
        """
        return list(self.guilds.values())


    def getGuild(self, id: int) -> basedGuild.BasedGuild:
        """Get the BasedGuild object with the specified ID.

        :param str id: integer discord ID for the requested guild
        :return: BasedGuild having the requested ID
        :rtype: BasedGuild
        """
        return self.guilds[id]


    def fromInteraction(self, interaction: Interaction) -> basedGuild.BasedGuild:
        if interaction.guild_id is None:
            raise lib.exceptions.IncorrectInteractionContext("This interaction is only applicable to guild channels")
        return self.getGuild(interaction.guild_id)


    def idExists(self, id: int) -> bool:
        """Check whether a BasedGuild with a given ID exists in the database.

        :param int id: integer discord ID to check for existence
        :return: True if a BasedGuild is stored in the database with the requested ID, False otherwise
        :rtype: bool
        """
        # Search the DB for the requested ID
        try:
            self.getGuild(id)
        # No BasedGuild found, return False
        except KeyError:
            return False
        # Return True otherwise
        return True


    def guildExists(self, guild: basedGuild.BasedGuild) -> bool:
        """Check whether a BasedGuild object exists in the database.
        Existence checking is currently handled by checking if a guild with the requested ID is stored.

        :param BasedGuild guild: BasedGuild object to check for existence

        :return: True if the exact BasedGuild exists in the DB, False otherwise
        :rtype: bool
        """
        return self.idExists(guild.id)


    def addBasedGuild(self, guild: basedGuild.BasedGuild):
        """Add a given BasedGuild object to the database.

        :param BasedGuild guild: the BasedGuild object to store
        :raise KeyError: If the the guild is already in the database
        """
        # Ensure guild is not yet in the database
        if self.guildExists(guild):
            raise KeyError(f"Attempted to add a guild that already exists: {guild.id}")
        self.guilds[guild.id] = guild


    def addDcGuild(self, dcGuild: Guild) -> basedGuild.BasedGuild:
        """Add a BasedGuild object to the database for the provided discord guild

        :param Guild dcGuild: discord Guild to create and store a BasedGuild for
        :raise KeyError: If a BasedGuild is already stored for the requested guild
        :return: the new BasedGuild object
        :rtype: BasedGuild
        """
        # Ensure the requested guild does not yet exist in the database
        if self.idExists(dcGuild.id):
            raise KeyError(f"Attempted to add a guild that already exists: {dcGuild.id}")
        # Create and return a BasedGuild for the requested ID
        basedGuild.BasedGuild.deserialize({}, guildID=dcGuild.id)
        self.guilds[dcGuild.id] = basedGuild.BasedGuild.deserialize({}, guildID=dcGuild.id)
        return self.guilds[dcGuild.id]


    def removeID(self, id: int):
        """Remove the BasedGuild with the requested ID from the database.

        :param int id: integer discord ID to remove from the database
        """
        self.guilds.pop(id)


    def removeGuild(self, guild: basedGuild.BasedGuild):
        """Remove the given BasedGuild object from the database
        Currently removes any BasedGuild sharing the given guild's ID, even if it is a different object.

        :param BasedGuild guild: the guild object to remove from the database
        """
        self.removeID(guild.id)


    def refreshAllShopStocks(self):
        """Generate new stock for all shops belonging to the stored guilds
        """
        for guild in self.guilds.values():
            if not guild.shopsDisabled:
                # Casting here because any guild that has shopsDisabled set to False must have divisionShops
                for shop in cast(Dict[str, guildShop.TechLeveledShop], guild.divisionShops).values():
                    shop.refreshStock()


    def _decayGuildTemps(self, g: basedGuild.BasedGuild):
        """Decay the activity temperatures of a single guild, if it has bounties enabled.
        Does nothing otherwise.

        :param BasedGuild g: The guild whose temperatures to decay
        """
        if not g.bountiesDisabled:
            # Casting here because any guild that has bountiesDisabled set to False must have a bountyDB
            for div in cast(bountyDB.BountyDB, g.bountiesDB).divisions.values():
                if div.isActive:
                    div.decayTemp()


    def decayAllTemps(self):
        """Decay the activity temperatures of all guilds in the database.
        This should be called daily.
        """
        if _minGuildsToParallelize is not None and len(self.guilds) > _minGuildsToParallelize:
            print("parallelizing temp decay")
            with ThreadPoolExecutor() as executor:
                executor.map(self._decayGuildTemps, self.getGuilds())
        else:
            print("serializing temp decay")
            for g in self.getGuilds():
                print("decaying guild #" + str(g.id))
                self._decayGuildTemps(g)
        botState.client.logger.log("GuildDB", "decayAllTemps", "All guild activity temperatures decayed successfuly.",
                            category=LogCategory.bountiesDB, eventType="TEMPS_DECAY")

    
    async def decayAllTempsAsync(self):
        """Wraps decayAllTemps in a coroutine, so it can be used with taskSchedulers.
        """
        self.decayAllTemps()


    def serialize(self, **kwargs) -> Dict[int, basedGuild.SerializedBasedGuildUnion]:
        """Serialise this GuildDB into dictionary format

        :return: A dictionary containing all data needed to recreate this GuildDB
        :rtype: dict
        """
        data = {}
        # Iterate over all stored guilds
        for guild in self.getGuilds():
            # Serialise and then store each guild
            # JSON stores properties as strings, so ids must be converted to str first.
            data[str(guild.id)] = guild.serialize(**kwargs)
        return data


    def __str__(self) -> str:
        """Fetch summarising information about the database, as a string
        Currently only the number of guilds stored

        :return: A string summarising this db
        :rtype: str
        """
        return "<GuildDB: " + str(len(self.guilds)) + " guilds>"


    @classmethod
    def deserialize(cls, guildDBDict: Dict[int, basedGuild.SerializedBasedGuildUnion], dbReload=False, **kwargs) -> GuildDB:
        """Construct a GuildDB object from dictionary-serialised format; the reverse of GuildDB.serialize()

        :param dict bountyDBDict: The dictionary representation of the GuildDB to create
        :return: The new GuildDB
        :rtype: GuildDB
        """
        # Instance the new GuildDB
        newDB = GuildDB()
        # Iterate over all IDs to add to the DB
        for guildID in guildDBDict.keys():
            # Instance new BasedGuilds for each ID, with the provided data
            # JSON stores properties as strings, so ids must be converted to int first.
            try:
                newDB.addBasedGuild(basedGuild.BasedGuild.deserialize(guildDBDict[guildID], guildID=int(guildID), dbReload=dbReload))
            # Ignore guilds that don't have a corresponding dcGuild
            except lib.exceptions.NoneDCGuildObj:
                botState.client.logger.log("GuildDB", "deserialize",
                                    f"no corresponding discord guild found for ID {guildID}, guild removed from database",
                                    category=LogCategory.guildsDB, eventType="NULL_GLD")
        return newDB
