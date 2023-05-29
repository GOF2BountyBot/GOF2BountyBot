from typing import Dict, Optional, Tuple, Callable, Any, cast, Coroutine, List

from discord import Guild, HTTPException, Interaction, TextChannel
from discord.abc import Snowflake

from ...interactions.basedApp import BasedCog
from ... import client, lib
from ...lib.stringTyping import isInt
from ...users import basedGuild
from ...databases.bountyDB import BountyDB
from ...databases.bountyDivision import BountyDivision
from ...logging import LogCategory
from ...cfg import cfg
from ...gameObjects.guildShop import TechLeveledShop


class GuildsUtilCog(BasedCog):
#region util
#region guild lookups

    async def guildByIdOrAllOrContext(self, interaction: Interaction, guild_id: str, sendError: bool = True, sendErrorEphemeral: bool = True, allowAllGuilds: bool = True) -> Tuple[bool, Optional[basedGuild.BasedGuild]]:
        """Gets a guild if one is specified. If not, then get the current guild. If guild_id is `'all'` then return `None`.
        If the result cannot be found in the guildsDB, respond to the interaction with an error, and return `None`.

        The return value is a tuple of `(bool valid, Optional[BasedGuild] guild)`
        - If `valid` is `False`, then valid options could not be inferred.
        - If `valid` is `True` and `guild` is `None`, then the user selected all guilds (`allowAllGuilds` must be `True`)
        - If `valid` is `True` and `guild` is not `None, then the user selected `guild` (or didn't select a guild, and `guild` is the calling guild)
        """
        if guild_id in ["this", "here"]:
            if interaction.guild is None:
                if sendError:
                    await interaction.response.send_message("Please use this command from within a guild, or specify a guild.", ephemeral=sendErrorEphemeral)
                return False, None
            callingBBGuild: Optional[basedGuild.BasedGuild] = self.bot.guildsDB.getGuild(interaction.guild.id)
        elif guild_id == "all":
            if not allowAllGuilds:
                if sendError:
                    await interaction.response.send_message("This command cannot be applied to all guilds.", ephemeral=sendErrorEphemeral)
                return False, None
            callingBBGuild = None
        elif not lib.stringTyping.isInt(guild_id):
            if sendError:
                await interaction.response.send_message(f":x: Invalid guild id - not a number. Please give an ID, {'`all`, ' if allowAllGuilds else ''}`here` or `this`.", ephemeral=sendErrorEphemeral)
            return False, None
        else:
            guildID = int(guild_id)
            if not self.bot.guildsDB.idExists(guildID):
                if sendError:
                    await interaction.response.send_message(f"Unrecognised guild ID: {guildID}", ephemeral=sendErrorEphemeral)
                return False, None
            callingBBGuild = self.bot.guildsDB.getGuild(guildID)
        
        return True, callingBBGuild


    async def guildWithBountiesByIdOrAllOrContext(self, interaction: Interaction, guild_id: str, sendError: bool = True, sendErrorEphemeral: bool = True, allowAllGuilds: bool = True) -> Tuple[bool, Optional[basedGuild.BasedGuild]]:
        """Gets a guild if one is specified. If not, then get the current guild. If guild_id is `'all'` then return `None`.
        If the result cannot be found in the guildsDB, or the guild has bounties disabled, respond to the interaction with an error, and return `None`.

        The return value is a tuple of `(bool valid, Optional[BasedGuild] guild)`
        - If `valid` is `False`, then valid options could not be inferred.
        - If `valid` is `True` and `guild` is `None`, then the user selected all guilds (`allowAllGuilds` must be `True`)
        - If `valid` is `True` and `guild` is not `None, then the user selected `guild` (or didn't select a guild, and `guild` is the calling guild)
        """
        valid, callingBBGuild = await self.guildByIdOrAllOrContext(interaction, guild_id, sendError=sendError, allowAllGuilds=allowAllGuilds)
        if not valid: return False, None

        if callingBBGuild is not None and callingBBGuild.bountiesDisabled:
            if sendError:
                await interaction.response.send_message(f":x: Bounties are disabled in that guild! ('{'Unknown' if callingBBGuild.dcGuild is None else callingBBGuild.dcGuild.name}')", ephemeral=sendErrorEphemeral)
            return False, None

        return True, callingBBGuild


    async def guildWithShopsByIdOrAllOrContext(self, interaction: Interaction, guild_id: str, sendError: bool = True, sendErrorEphemeral: bool = True, allowAllGuilds: bool = True) -> Tuple[bool, Optional[basedGuild.BasedGuild]]:
        """Gets a guild if one is specified. If not, then get the current guild. If guild_id is `'all'` then return `None`.
        If the result cannot be found in the guildsDB, or the guild has shops disabled, respond to the interaction with an error, and return `None`.

        The return value is a tuple of `(bool valid, Optional[BasedGuild] guild)`
        - If `valid` is `False`, then valid options could not be inferred.
        - If `valid` is `True` and `guild` is `None`, then the user selected all guilds (`allowAllGuilds` must be `True`)
        - If `valid` is `True` and `guild` is not `None, then the user selected `guild` (or didn't select a guild, and `guild` is the calling guild)
        """
        valid, callingBBGuild = await self.guildByIdOrAllOrContext(interaction, guild_id, sendError=sendError, allowAllGuilds=allowAllGuilds)
        if not valid: return False, None

        if callingBBGuild is not None and callingBBGuild.shopsDisabled:
            if sendError:
                await interaction.response.send_message(f":x: Shops are disabled in that guild! ('{'Unknown' if callingBBGuild.dcGuild is None else callingBBGuild.dcGuild.name}')", ephemeral=sendErrorEphemeral)
            return False, None

        return True, callingBBGuild


    @classmethod
    async def textChannelOrThreadByIdOrContext(cls, interaction: Interaction, channel_id: str, guild: Guild, sendError: bool = True, sendErrorEphemeral: bool = True) -> Optional[TextChannel]:
        """Get a text channel for a command.
        If `channel_id` is specified, make sure it's an int, and send an error if it's not.
            Then get the channel from `guild`, and make sure it's a text channel, and send an error if it's not.
        If `channel_id` is not specified, get the channel from which `interaction` was sent, and send an error if it is not a text channel.

        if no errors occurred, return the channel.
        """
        if channel_id == "here":
            if not isinstance(interaction.channel, TextChannel):
                if sendError:
                    await interaction.response.send_message(":x: Invalid channel! Make sure you are calling from, or specifying, a **text channel** in a guild.", ephemeral=sendErrorEphemeral)
                return None
            channel = interaction.channel

        elif not isInt(channel_id):
            await interaction.response.send_message(":x: Invalid `channel_id` - must be a number.", ephemeral=sendErrorEphemeral)
            return None
        else:
            channelId = int(channel_id)
            channel = guild.get_channel_or_thread(channelId)
            if channel is None:
                try:
                    channel = await guild.fetch_channel(channelId)
                except HTTPException as e:
                    await interaction.response.send_message(f":x: I can't find channel '{channelId}': {e}", ephemeral=sendErrorEphemeral)
                    return None
        
        if not isinstance(channel, TextChannel):
            await interaction.response.send_message(f":x: Invalid channel! Make sure you are calling from, or specifying, a **text channel** in a guild.", ephemeral=sendErrorEphemeral)
            return None

        return channel

#endregion guild lookups
#region iterators

    async def operateOverBasedGuilds(self, callback: Callable[[basedGuild.BasedGuild], Any], operationCompleteStr: str, interaction: Interaction, callingBBGuild: Optional[basedGuild.BasedGuild], sendSuccess: bool = True, sendSuccessEphemeral: bool = True, defer: bool = True):
        """Perform some synchronous operation over:
        - all guilds if `callingBBGuild` is `None`
        - `callingBBGuild` if it isn't `None`

        On success, send a **followup** to `interaction` containing `operationCompleteStr`, with some other stuff.
        """
        if defer and not interaction.response.is_done():
            await interaction.response.defer(ephemeral=sendSuccessEphemeral)

        if callingBBGuild is None:
            for currentGuild in self.bot.guildsDB.guilds.values():
                callback(currentGuild)
        else:
            callback(callingBBGuild)

        guildResultStr = ((" for '" + callingBBGuild.dcGuild.name + "'.") if callingBBGuild.dcGuild is not None else ".") \
                            if callingBBGuild is not None else " for all guilds."
        if sendSuccess:
            await interaction.followup.send(":ballot_box_with_check: " + operationCompleteStr + guildResultStr, ephemeral=sendSuccessEphemeral)


    async def operateOverBasedGuildsAsync(self, funcName: str, callback: Callable[[basedGuild.BasedGuild], Coroutine], operationCompleteStr: str, interaction: Interaction, callingBBGuild: Optional[basedGuild.BasedGuild], sendSuccess: bool = True, awaitTasks: bool = True, logCategory: Optional[LogCategory] = None, className: Optional[str] = "GuildsUtilCog", sendSuccessEphemeral: bool = True, defer: bool = True):
        """Perform some asynchronous operation, with parallelization over the bounty DB(s) of:
        - all guilds if `callingBBGuild` is `None`
        - `callingBBGuild` if it isn't `None`

        On success, send a followup to `interaction` containing `operationCompleteStr`, with some other stuff.
        """
        dbTasks = lib.discordUtil.BasicScheduler()
        def doTask(guild: basedGuild.BasedGuild):
            dbTasks.add(lib.discordUtil.scheduleCoroWithLogging(callback(guild), logCategory=logCategory, className=className, funcName=funcName))

        await self.operateOverBasedGuilds(doTask, operationCompleteStr=operationCompleteStr, interaction=interaction, callingBBGuild=callingBBGuild, sendSuccess=sendSuccess, sendSuccessEphemeral=sendSuccessEphemeral, defer=defer)

        if awaitTasks and dbTasks:
            await dbTasks.wait()

    
    async def operateOverBountyDBs(self, callback: Callable[[BountyDB], Any], operationCompleteStr: str, interaction: Interaction, callingBBGuild: Optional[basedGuild.BasedGuild], sendErrors: bool = True, sendSuccess: bool = True, sendErrorsEphemeral: bool = True, sendSuccessEphemeral: bool = True, defer: bool = True) -> bool:
        """Perform some synchronous operation over the bounty DB(s) in:
        - all guilds if `callingBBGuild` is `None`
        - `callingBBGuild` if it isn't `None`

        On success, send a **followup** to `interaction` containing `operationCompleteStr`, with some other stuff.

        returns `bool success` = `False` if errors occurred, or `True` otherwise.
        """
        if defer and not interaction.response.is_done():
            await interaction.response.defer(ephemeral=sendErrorsEphemeral or sendSuccessEphemeral)

        if callingBBGuild is None:
            for currentGuild in self.bot.guildsDB.guilds.values():
                if not currentGuild.bountiesDisabled:
                    # casting here because guild.bountiesDB cannot be None if bountiesDisabled is False
                    callback(cast(BountyDB, currentGuild.bountiesDB))
        else:
            if callingBBGuild.bountiesDisabled:
                if sendErrors:
                    await interaction.followup.send((("'" + callingBBGuild.dcGuild.name + "' ") if callingBBGuild.dcGuild is not None \
                                                else "The requested guild ") + " has bounties disabled.", ephemeral=sendErrorsEphemeral)
                return False
            
            # casting here because guild.bountiesDB cannot be None if bountiesDisabled is False
            callback(cast(BountyDB, callingBBGuild.bountiesDB))

        guildResultStr = ((" for '" + callingBBGuild.dcGuild.name + "'.") if callingBBGuild.dcGuild is not None else ".") \
                            if callingBBGuild is not None else " for all guilds."
        if sendSuccess:
            await interaction.followup.send(":ballot_box_with_check: " + operationCompleteStr + guildResultStr, ephemeral=sendSuccessEphemeral)

        return True


    async def operateOverBountyDBsAsync(self, funcName: str, callback: Callable[[BountyDB], Coroutine], operationCompleteStr: str, interaction: Interaction, callingBBGuild: Optional[basedGuild.BasedGuild], sendErrors: bool = True, sendSuccess: bool = True, awaitTasks: bool = True, logCategory: Optional[LogCategory] = None, className: Optional[str] = "GuildsUtilCog", sendErrorsEphemeral: bool = True, sendSuccessEphemeral: bool = True, defer: bool = True) -> bool:
        """Perform some asynchronous operation, with parallelization over the bounty DB(s) of:
        - all guilds if `callingBBGuild` is `None`
        - `callingBBGuild` if it isn't `None`

        On success, send a followup to `interaction` containing `operationCompleteStr`, with some other stuff.
        """
        dbTasks = lib.discordUtil.BasicScheduler()
        def doTask(div: BountyDB):
            dbTasks.add(lib.discordUtil.scheduleCoroWithLogging(callback(div), logCategory=logCategory, className=className, funcName=funcName))

        success = await self.operateOverBountyDBs(doTask, operationCompleteStr=operationCompleteStr, interaction=interaction, callingBBGuild=callingBBGuild, sendErrors=sendErrors, sendSuccess=sendSuccess, sendErrorsEphemeral=sendErrorsEphemeral, sendSuccessEphemeral=sendSuccessEphemeral, defer=defer)

        if awaitTasks and dbTasks:
            await dbTasks.wait()

        return success


    async def operateOverDivisions(self, callback: Callable[[BountyDivision], Any], operationCompleteStr: str, division: str, interaction: Interaction, callingBBGuild: Optional[basedGuild.BasedGuild], allDivs: bool, sendErrors: bool = True, sendSuccess: bool = True, sendErrorsEphemeral: bool = True, sendSuccessEphemeral: bool = True, defer: bool = True) -> bool:
        """Perform some synchronous operation over:
        - the division called `division` if `allDivs` is `False`
        - all divisions if `allDivs` is `True`
        - in all guilds if `callingBBGuild` is `None`
        - in `callingBBGuild` if it isn't `None`

        On success, send a **followup** to `interaction` containing `operationCompleteStr`, with some other stuff.

        returns `bool success` = `False` if errors occurred, or `True` otherwise.
        """
        def doDivs(bountyDB: BountyDB):
            if allDivs:
                for div in bountyDB.divisions.values():
                    callback(div)
            else:
                callback(bountyDB.divisionForName(division))
        
        return await self.operateOverBountyDBs(doDivs, operationCompleteStr=operationCompleteStr, interaction=interaction, callingBBGuild=callingBBGuild, sendErrors=sendErrors, sendSuccess=sendSuccess, sendErrorsEphemeral=sendErrorsEphemeral, sendSuccessEphemeral=sendSuccessEphemeral, defer=defer)


    async def operateOverDivisionsAsync(self, funcName: str, callback: Callable[[BountyDivision], Coroutine], operationCompleteStr: str, division: str, interaction: Interaction, callingBBGuild: Optional[basedGuild.BasedGuild], allDivs: bool, sendErrors: bool = True, sendSuccess: bool = True, awaitTasks: bool = True, logCategory: Optional[LogCategory] = None, className: Optional[str] = "GuildsUtilCog", sendErrorsEphemeral: bool = True, sendSuccessEphemeral: bool = True, defer: bool = True) -> bool:
        """Perform some asynchronous operation, with parallelization over:
        - the division called `division` if `allDivs` is `False`
        - all divisions if `allDivs` is `True`
        - in all guilds if `callingBBGuild` is `None`
        - in `callingBBGuild` if it isn't `None`

        On success, send a followup to `interaction` containing `operationCompleteStr`, with some other stuff.
        """
        # I've chosen to duplicate the operateOverBountyDBsAsync logic here.
        # I could just make a copy of operateOverDivisions, but with an async callback wrapper,
        # But that would result in callbacks being parallelized at the guild level rather than at the division level,
        # And I forsee this method mostly being used to operate over the divisions of a single guild.
        divTasks = lib.discordUtil.BasicScheduler()
        def doTask(div: BountyDivision):
            divTasks.add(lib.discordUtil.scheduleCoroWithLogging(callback(div), logCategory=logCategory, className=className, funcName=funcName))

        success = await self.operateOverDivisions(doTask, operationCompleteStr=operationCompleteStr, division=division, interaction=interaction, callingBBGuild=callingBBGuild, allDivs=allDivs, sendErrors=sendErrors, sendSuccess=sendSuccess, sendErrorsEphemeral=sendErrorsEphemeral, sendSuccessEphemeral=sendSuccessEphemeral, defer=defer)

        if awaitTasks and divTasks:
            await divTasks.wait()

        return success

    
    async def operateOverShops(self, callback: Callable[[basedGuild.BasedGuild, str, TechLeveledShop], Any], operationCompleteStr: str, interaction: Interaction, callingBBGuild: Optional[basedGuild.BasedGuild], division: str, allDivs: bool, sendErrors: bool = True, sendSuccess: bool = True, sendErrorsEphemeral: bool = True, sendSuccessEphemeral: bool = True, defer: bool = True) -> bool:
        """Perform some synchronous operation over the division shop(s) in:
        - the division called `division` if `allDivs` is `False`
        - all divisions if `allDivs` is `True`
        - all guilds if `callingBBGuild` is `None`
        - `callingBBGuild` if it isn't `None`

        On success, send a **followup** to `interaction` containing `operationCompleteStr`, with some other stuff.

        returns `bool success` = `False` if errors occurred, or `True` otherwise.
        """
        if defer and not interaction.response.is_done():
            await interaction.response.defer(ephemeral=sendErrorsEphemeral or sendSuccessEphemeral)

        def _processGuildWithShops(guild: basedGuild.BasedGuild):
            # casting here because guild.divisionShops cannot be None if shopsDisabled is False
            currentShops = cast(Dict[str, TechLeveledShop], guild.divisionShops)
            if allDivs:
                for divisionName, shop in currentShops.items():
                    callback(guild, divisionName, shop)
            elif division in currentShops:
                callback(guild, division, currentShops[division])

        if callingBBGuild is None:
            for currentGuild in self.bot.guildsDB.guilds.values():
                if not currentGuild.shopsDisabled:
                    _processGuildWithShops(currentGuild)
        else:
            if callingBBGuild.shopsDisabled:
                if sendErrors:
                    await interaction.followup.send((("'" + callingBBGuild.dcGuild.name + "' ") if callingBBGuild.dcGuild is not None \
                                                else "The requested guild ") + " has shops disabled.", ephemeral=sendErrorsEphemeral)
                return False
            
            _processGuildWithShops(callingBBGuild)

        guildResultStr = ((" for '" + callingBBGuild.dcGuild.name + "'.") if callingBBGuild.dcGuild is not None else ".") \
                            if callingBBGuild is not None else " for all guilds."
        if sendSuccess:
            await interaction.followup.send(":ballot_box_with_check: " + operationCompleteStr + guildResultStr, ephemeral=sendSuccessEphemeral)

        return True


    async def operateOverShopsAsync(self, funcName: str, callback: Callable[[basedGuild.BasedGuild, str, TechLeveledShop], Coroutine], operationCompleteStr: str, interaction: Interaction, callingBBGuild: Optional[basedGuild.BasedGuild], division: str, allDivs: bool, sendErrors: bool = True, sendSuccess: bool = True, awaitTasks: bool = True, logCategory: Optional[LogCategory] = None, className: Optional[str] = "GuildsUtilCog", sendErrorsEphemeral: bool = True, sendSuccessEphemeral: bool = True, defer: bool = True) -> bool:
        """Perform some asynchronous operation, with parallelization over the division shop(s) of:
        - the division called `division` if `allDivs` is `False`
        - all divisions if `allDivs` is `True`
        - all guilds if `callingBBGuild` is `None`
        - `callingBBGuild` if it isn't `None`

        On success, send a followup to `interaction` containing `operationCompleteStr`, with some other stuff.
        """
        dbTasks = lib.discordUtil.BasicScheduler()
        def doTask(guild: basedGuild.BasedGuild, divisionName: str, shop: TechLeveledShop):
            dbTasks.add(lib.discordUtil.scheduleCoroWithLogging(callback(guild, divisionName, shop), logCategory=logCategory, className=className, funcName=funcName))

        success = await self.operateOverShops(doTask, operationCompleteStr, interaction, callingBBGuild, division, allDivs, sendErrors=sendErrors, sendSuccess=sendSuccess, sendErrorsEphemeral=sendErrorsEphemeral, sendSuccessEphemeral=sendSuccessEphemeral, defer=defer)

        if awaitTasks and dbTasks:
            await dbTasks.wait()

        return success


#endregion iterators
#endregion util


async def setup(bot: client.BasedClient):
    await bot.add_cog(GuildsUtilCog(bot))
