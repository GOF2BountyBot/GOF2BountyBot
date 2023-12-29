from typing import Dict, Optional, Tuple, Union, cast, TYPE_CHECKING, List, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func

from ..entities.bounties.bountyBoardChannel import BountyBoardChannel, SerializedBountyBoardChannel
from ..entities.bounties import bounty, criminal
from ..entities.guilds import basedGuild
from ..cfg import cfg
from ..entities.bounties.bountyDivision import BountyDivision
from ..baseClasses.serializable import SerializesToSchema
from .snowflakeRepository import SnowflakeRepository
from ..baseClasses.aliasable import _ObjectAlias
from ..lib.sql import count, SqlColumnExpression


class BountyRepository(SnowflakeRepository["bounty.Bounty[Any]"]):
    def __init__(self, session: AsyncSession):
        super().__init__(bounty.Bounty[Any], session)


    async def getBountyByCrim(self, guildId: int, crim: Union[int, criminal.Criminal[Any]], level: Optional[int] = None, allowEscaped: bool = False, withOnlyFields: Optional[Tuple[SqlColumnExpression[Any], ...]] = None) -> bounty.AnyBounty:
        """Get the bounty object for a given criminal name object
        
        :param crim: The criminal, or criminal id, whose bounty is to be fetched.
        :type crim: Union[int, Criminal]
        :param str level: The difficulty level of the criminal's bounty, if known (Default None)
        :return: the bounty object tracking crim
        :rtype: Bounty
        :raise KeyError: If the requested criminal does not exist in this DB
        """
        crimId = crim if isinstance(crim, int) else crim.id

        query = select(bounty.Bounty[Any]).join(BountyDivision[Any]).where(and_(
            BountyDivision.guildId == guildId,
            bounty.Bounty.criminalId == crimId
        ))

        if level is not None:
            query = query.where(bounty.Bounty.techLevel == level)

        if not allowEscaped:
            query = query.where(bounty.Bounty.isEscaped == False)
        
        if withOnlyFields:
            query = query.with_only_columns(*withOnlyFields)

        result = await self.session.execute(query)
        row = result.one_or_none()
        if row is None:
            raise KeyError(f"No bounty found for criminal: {crimId}" + ("" if level is None else f" and level: {level}"))
        
        return row.t[0]


    async def getEscapedBountyByCrim(self, guildId: int, crim: Union[int, criminal.Criminal[Any]], level: Optional[int] = None, withOnlyFields: Optional[Tuple[SqlColumnExpression[Any], ...]] = None) -> bounty.Bounty:
        """Get the escaped bounty object for a given criminal object.
        This process is much more efficient when given the difficulty level of the criminal's bounty.

        :param crim: The criminal, or criminal id, whose escaped bounty is to be fetched.
        :type crim: Union[int, Criminal]
        :param int level: The difficulty level of the criminal's bounty, if known (Default None)
        :return: the escaped bounty object tracking crim
        :rtype: Bounty
        :raise KeyError: If the requested criminal does not exist in this DB
        """
        crimId = crim if isinstance(crim, int) else crim.id

        query = select(bounty.Bounty[Any]).join(BountyDivision[Any]).where(and_(
            BountyDivision.guildId == guildId,
            bounty.Bounty.criminalId == crimId,
            bounty.Bounty.isEscaped == True
        ))

        if level is not None:
            query = query.where(bounty.Bounty.techLevel == level)
        
        if withOnlyFields:
            query = query.with_only_columns(*withOnlyFields)

        result = await self.session.execute(query)
        row = result.one_or_none()
        if row is None:
            raise KeyError(f"No escaped bounty found for criminal: {crimId}" + ("" if level is None else f" and level: {level}"))
        
        return row.t[0]


    async def getBountyByAlias(self, guildId: int, name: str, level: Optional[int] = None, withOnlyFields: Optional[Tuple[SqlColumnExpression[Any], ...]] = None) -> bounty.Bounty:
        """Get the bounty object for a given criminal name or alias.
        This method implementation currently joins FOUR tables! If possible, always use the get by criminal ID method instead!
        As of writing, SqlAlchemy will raise MultipleResultsFound if more than one bounty matches this alias.
        
        :param str name: A name or alias for the criminal whose bounty is to be fetched.
        :param int level: The difficulty level of the criminal's bounty, if known (Default None)
        :return: the bounty object tracking the named criminal
        :rtype: Bounty
        :raise KeyError: If the requested criminal name does not exist in this DB
        """
        # This is an unfortunate number of joins...
        query = select(bounty.Bounty[Any]) \
            .join(criminal.Criminal[Any], criminal.Criminal.id == bounty.Bounty.criminalId) \
            .join(BountyDivision[Any], BountyDivision.id == bounty.Bounty.divisionId) \
            .join(_ObjectAlias, _ObjectAlias.objectAliasesId == criminal.Criminal.id).where(and_(
                BountyDivision.guildId == guildId,
                bounty.Bounty.isEscaped == False,
                or_(
                    criminal.Criminal.name.ilike(name),
                    _ObjectAlias.alias.ilike(name),
                )
            ))

        if level is not None:
            query = query.where(bounty.Bounty.techLevel == level)
        
        if withOnlyFields:
            query = query.with_only_columns(*withOnlyFields)

        result = await self.session.execute(query)
        row = result.one_or_none()
        if row is None:
            raise KeyError(f"No bounty found for name: {name}'" + ("'" if level is None else f"' and level: {level}"))
        
        return row.t[0]


    async def getEscapedBountyByAlias(self, guildId: int, name: str, level: Optional[int] = None, withOnlyFields: Optional[Tuple[SqlColumnExpression[Any], ...]] = None) -> bounty.Bounty:
        """Get the escaped bounty object for a given criminal name or alias.
        This method implementation currently joins FOUR tables! If possible, always use the get by criminal ID method instead!
        As of writing, SqlAlchemy will raise MultipleResultsFound if more than one bounty matches this alias.
        
        :param str name: A name or alias for the criminal whose escaped bounty is to be fetched.
        :param int level: The difficulty level of the criminal's bounty, if known (Default None)
        :return: the escaped bounty object tracking the named criminal
        :rtype: Bounty
        :raise KeyError: If the requested criminal name does not exist in this DB
        """
        # This is an unfortunate number of joins...
        query = select(bounty.Bounty[Any]) \
            .join(criminal.Criminal[Any], criminal.Criminal.id == bounty.Bounty.criminalId) \
            .join(BountyDivision[Any], BountyDivision.id == bounty.Bounty.divisionId) \
            .join(_ObjectAlias, _ObjectAlias.objectAliasesId == criminal.Criminal.id).where(and_(
                BountyDivision.guildId == guildId,
                bounty.Bounty.isEscaped == True,
                or_(
                    criminal.Criminal.name.ilike(name),
                    _ObjectAlias.alias.ilike(name),
                )
            ))

        if level is not None:
            query = query.where(bounty.Bounty.techLevel == level)
        
        if withOnlyFields:
            query = query.with_only_columns(*withOnlyFields)

        result = await self.session.execute(query)
        row = result.one_or_none()
        if row is None:
            raise KeyError(f"No escaped bounty found for name: {name}'" + ("'" if level is None else f"' and level: {level}"))
        
        return row.t[0]


    async def totalBounties(self, guildId: int, includeEscaped: bool = True) -> int:
        """Decide the total number of bounties currently stored across all divisions.
        If includeEscaped is given as true, escaped bounties will also be counted.

        :param bool includeEscaped: Whether or not to count escaped bounties as well as active bounties (Default True)
        :return: The number of bounties stored in the DB across all divisions
        :rtype: int
        """
        query = count(bounty.Bounty[Any]).join(BountyDivision[Any]).where(BountyDivision.guildId == guildId)

        if not includeEscaped:
            query = query.where(bounty.Bounty.isEscaped == False)

        return await self.session.scalar(query)


    def canMakeBounty(self, guildId: int) -> bool:
        """Check whether this DB has space for more bounties

        :return: True if at least one division is not at capacity, False if all divisions' bounties are full
        :rtype: bool
        """
        return any((not div.isFull() or not div.hasMinTLBounty()) for div in self.divisions.values())


    def bountyNameExists(self, guildId: int, name: str, level: Optional[int] = None, noEscapedCrim: bool = True) -> bool:
        """Check whether a criminal with the given name or alias exists in the DB
        The process is much more efficient if the level of the criminal is known.

        :param str name: The name or alias to check for criminal existence against
        :param str level: The difficulty level of the named criminal's bounty.
                            Use None if the level is not known. (default None)
        :param bool noEscapedCrim: When False, the escaped criminals database is also checked (default True)

        :return: True if a bounty is found for a criminal with the given name,
                    False if the given name does not correspond to an active bounty in this DB
        :rtype: bool
        """
        # Search for a bounty object under the given name
        try:
            self.getBounty(name, level)
        # Return False if the name was not found, True otherwise
        except KeyError:
            if not noEscapedCrim:
                try:
                    self.getEscapedBounty(name, level)
                except KeyError:
                    return False
            else:
                return False
        return True


    def criminalObjExists(self, guildId: int, crim: criminal.Criminal[Any], noEscapedCrim=True) -> bool:
        """Check whether a given criminal object exists in the DB.
        Existence is checked across all divisions and levels.

        :param Criminal crim: The criminal object to check for existence in the DB
        :param bool noEscapedCriminal: Give `False` to also search escaped criminals (Defaults to True)
        :return: True if the given criminal is found within the DB, False otherwise
        :rtype: bool
        """
        activeExists = any(div.criminalObjExists(crim) for div in self.divisions.values())
        if noEscapedCrim:
            return activeExists
        escapedExists = any(div.escapedCriminalExists(crim) for div in self.divisions.values())
        return activeExists or escapedExists


    def addBounty(self, guildId: int, bounty: bounty.Bounty, dbReload=False, isRespawn=False):
        """Add a given bounty object to the database.
        Bounties cannot be added if the division for its level does not have space for more bounties.
        Bounties cannot be added if a bounty already exists for the same criminal in this DB.

        :param Bounty bounty: the bounty object to add to the database
        :param bool isRespawn: Skips division fullness checks
        :raise OverflowError: if the division for this bounty's level is already at capacity
        :raise ValueError: if the criminal is already wanted in the database
        """
        div = self.divisionForLevel(bounty.techLevel)

        # Ensure the DB has space for the bounty
        if not isRespawn and not dbReload and div.isFull(includeEscaped=True) and \
                ((bounty.techLevel == div.minLevel and div.hasMinTLBounty()) or (bounty.techLevel != div.minLevel)):
            raise OverflowError(f"Division for the bounty ({bounty.criminal.name}, level {bounty.techLevel}) is full")
        
        if self.criminalObjExists(bounty.criminal):
            raise ValueError(f"Attempted to add {bounty} for a criminal who is already wanted: {bounty.criminal} by {bounty}")

        # # ensure the given bounty does not already exist
        # if self.bountyNameExists(bounty.criminal.name, noEscapedCrim=False):
        #     raise ValueError("Attempted to add a bounty whose name already exists: " + bounty.criminal.name)

        # Add the bounty to the database
        div._addBounty(bounty, dbReload=dbReload, isRespawn=isRespawn)


    def escapedCriminalExists(self, guildId: int, crim):
        """Decide whether a criminal is recorded in the escaped criminals database.

        :param criminal crim: The criminal to check for existence
        :return: True if crim is in this database's escaped criminals record, False otherwise
        :rtype: bool
        """
        return any(div.escapedCriminalExists(crim) for div in self.divisions.values())


    def addEscapedBounty(self, guildId: int, bounty: bounty.Bounty, dbReload: bool = False, ignoreFull: bool = False):
        """Add a given bounty object to the escaped bounties database.
        Bounties cannot be added if the object or name already exists in the database.

        :param Bounty bounty: the bounty object to add to the database
        :param bool dbReload: When true, skip checking for duplicate bounties and full divisions (Default False)
        :param bool ignoreFull: When true, skip checking if the division is full (Default False)
        :raise ValueError: if the requested bounty's name already exists in the database
        """
        div = self.divisionForLevel(bounty.techLevel)

        # Ensure the DB has space for the bounty
        # If ignoreFull is set, don't check
        # If the database is being reloaded (i.e we are in 'eventual consistency' style mode), don't check
        # The divison is full if it has both reached capacity, and has min-level bounty (or the new bounty is not min level)
        if not ignoreFull and \
                not dbReload and \
                div.isFull(includeEscaped=True) and \
                ((bounty.techLevel == div.minLevel and div.hasMinTLBounty()) or (bounty.techLevel != div.minLevel)):
            raise OverflowError(f"Division for the escaped bounty ({bounty.criminal.name}, level {bounty.techLevel}) is full")
        
        if self.criminalObjExists(bounty.criminal):
            raise ValueError(f"Attempted to add escaped {bounty} for a criminal who is already wanted: " \
                            + f"{bounty.criminal} by unescaped {bounty}")
        if self.escapedCriminalExists(bounty.criminal):
            raise ValueError(f"Attempted to add escaped {bounty} for a criminal who is already wanted: " \
                            + f"{bounty.criminal} by escaped {bounty}")
        # # ensure the given bounty does not already exist
        # if self.bountyNameExists(bounty.criminal.name, noEscapedCrim=False):
        #     raise ValueError("Attempted to add a bounty whose name already exists: " + bounty.criminal.name)

        # Add the bounty to the database
        div._addEscapedBounty(bounty, dbReload=dbReload, ignoreFull=ignoreFull)


    def removeEscapedBountyObj(self, guildId: int, bounty: bounty.Bounty):
        """Remove a given escaped bounty object from the database.
        the bounty must already be recorded in the escaped criminals database.
        This does not perform respawning of the bounty.

        If the division was full before, restart the new bounty spawner

        :param Bounty bounty: the bounty object to remove from the database
        """
        self.divisionForLevel(bounty.techLevel).removeEscapedBountyObj(bounty)


    def removeEscapedCriminal(self, guildId: int, crim):
        """Remove a criminal from the record of escaped criminals.
        crim must already be recorded in the escaped criminals database.
        This does not perform respawning of the bounty.

        If the division was full before, restart the new bounties timed task

        :param criminal crim: The criminal to remove from the record
        :raise KeyError: If criminal is not registered in the db
        """
        self.removeEscapedBountyObj(self.getEscapedBountyByCrim(crim))
        # print(f"removed escaped criminal {bounty.criminal.name} from div {nameForDivision(self.divisionForLevel(bounty.techLevel))}, level {bounty.techLevel}")


    def removeBountyObj(self, guildId: int, bounty: bounty.Bounty):
        """Remove a given bounty object from the database.
        If the division was full before, restart the new bounty spawner

        :param Bounty bounty: the bounty object to remove from the database
        """
        self.divisionForLevel(bounty.techLevel).removeBountyObj(bounty)


    def removeBountyName(self, guildId: int, name: str, faction: Optional[str] = None):
        """Find the bounty associated with the given criminal name or alias, and remove it from the database.
        This process is much more efficient if the faction under which the bounty is wanted is given.

        :param str name: The name of the criminal to remove
        :param str faction: The faction whose bounties to check for the named criminal.
                            Use None if the faction is not known. (default None)
        """
        self.removeBountyObj(self.getBounty(name))


    def hasBounties(self, guildId: int) -> bool:
        """Check whether any division has bounties stored.

        :return: True if at least one bounty is stored in this DB, False otherwise
        :rtype: bool
        """
        return any(not div.isEmpty() for div in self.divisions.values())
