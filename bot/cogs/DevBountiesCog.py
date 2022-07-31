import discord
from discord import Member, User, app_commands, Interaction, Colour
from discord.utils import utcnow
from discord.abc import Snowflake
from discord.ext.commands import Range
from typing import Any, Awaitable, Callable, Coroutine, List, Optional, Tuple, Union, cast
from datetime import datetime, timezone, timedelta
from carica import SerializableTimedelta
import json
import random

from bot.lib.stringTyping import isInt
from bot.scheduling import timedTask

from ..interactions import basedCommand, basedApp
from .. import botState, lib, client
from ..lib import gameMaths
from ..cfg import cfg, bbData
from ..cfg.cfg import basicAccessLevels
from ..gameObjects.bounties import bounty, bountyConfig
from ..gameObjects.items import shipItem
from ..users import basedGuild, basedUser
from ..databases.bountyDB import nameForDivision, BountyDB
from ..databases.bountyDivision import BountyDivision
from ..logging import LogCategory
from ..gameObjects.bounties.bountyBoards.bountyBoardChannel import BountyBoardChannel
from .util.CommonAutocomplete import divisionAutoComplete, systemAutoComplete, criminalAutoComplete, factionAutoComplete
from .util.transformers import BoolYesNo
from .util.parameterVerifiers import verifyCriminalName, verifyDivName, verifyFactionName, verifySystemName


class DevBountiesCog(basedApp.BasedCog):
    def __init__(self, bot: client.BasedClient, *args, **kwargs):
        self.bot = bot
        super().__init__(*args, **kwargs)

#region util
    
    async def _makeBounty(self, interaction: Interaction,
            guild_id: str = "here", difficulty: Optional[Range[int, cfg.minTechLevel, cfg.maxTechLevel]] = None, 
            division: Optional[str] = None, name: Optional[str] = None, faction: Optional[str] = None,
            route: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None, 
            answer: Optional[str] = None, reward: Optional[int] = None, endTime: Optional[str] = None,
            icon: Optional[str] = None, player_id: Optional[str] = None, ship_dict: Optional[str] = None):
        
        if player_id is not None and name is not None:
            raise ValueError("parameters name and player_id are mutually exclusive")

        valid, callingBBGuild = await self.GuildsUtilCog.getGuildWithBounties(interaction, guild_id, allowAllGuilds=False)
        if not valid: return

        callingBBGuild = cast(basedGuild.BasedGuild, callingBBGuild)
        config = bountyConfig.BountyConfig()
        # The following parameters are not passed into the config:
        # guild_id, division
        errors: List[str] = []

        if player_id is not None:
            if not lib.stringTyping.isInt(player_id):
                errors.append("Your `player_id` is not a valid user id")
            else:
                playerIdInt = int(player_id)
                if requestedUser := (self.bot.get_user(playerIdInt) or await self.bot.fetch_user(playerIdInt)):
                    if self.bot.usersDB.idExists(requestedUser.id):
                        requestedBUser = self.bot.usersDB.getUser(requestedUser.id)
                        config.activeShip = requestedBUser.activeShip
                        if requestedBUser.classicModeEnabled:
                            if difficulty is None:
                                errors.append("That user has classic mode enabled, so I can't infer their difficulty. Please give `difficulty` explicitly")
                        else:
                            config.techLevel = gameMaths.calculateUserBountyHuntingLevel(requestedBUser.bountyHuntingXP)
                    else:
                        config.activeShip = shipItem.Ship.deserialize(basedUser.defaultShipLoadoutDict)
                        config.techLevel = cfg.minTechLevel

                    config.name = f"<@{player_id}>"
                    config.isPlayer = True
                    config.icon = requestedUser.display_avatar.with_size(64).url
                    config.aliases = [str(requestedUser)]
                else:
                    errors.append("Unknown user")

        if difficulty is not None:
            config.techLevel = difficulty
        if division is not None and await verifyDivName(interaction, division, allowAllDivisions=False) is None:
            return
        if name is not None:
            if not await verifyCriminalName(interaction, name): return
            config.name = name
        if ship_dict is not None:
            try:
                serializedShip = json.loads(ship_dict)
            except json.decoder.JSONDecodeError as e:
                errors.append(f"Your `ship_dict` is not valid json: {e}")
            else:
                config.activeShip = shipItem.Ship.deserialize(serializedShip)
        if faction is not None:
            if not await verifyFactionName(interaction, faction): return
            config.faction = faction
        if route is not None:
            routeSplit = route.split(",")
            config.route = []
            for system in routeSplit:
                system = system.strip()
                if not await verifySystemName(interaction, system): return
                config.route.append(system)
        if start is not None:
            if not await verifySystemName(interaction, start): return
            if config.route is not None and start not in config.route:
                errors.append("Your `start` is not in your `route")
            else:
                config.start = start
        if end is not None:
            if not await verifySystemName(interaction, end): return
            if config.route is not None and end not in config.route:
                errors.append("Your `end` is not in your `route")
            else:
                config.end = end
        if answer is not None:
            if not await verifySystemName(interaction, answer): return
            if config.route is not None and answer not in config.route:
                errors.append("Your `answer` is not in your `route")
            else:
                config.answer = answer
        if reward is not None:
            if reward < 0:
                errors.append("`reward` cannot be negative")
            else:
                config.reward = reward
        if endTime is not None:
            if lib.stringTyping.isFloat(endTime):
                errors.append("Your `endTime` is not a valid unix timestamp")
            else:
                endTimeFloat = float(endTime)
                if endTimeFloat < 0:
                    errors.append("`endTime` cannot be negative")
                else:
                    endDT = datetime.fromtimestamp(endTimeFloat, tz=timezone.utc)
                    if endDT - utcnow() < timedelta(minutes=1):
                        errors.append("`end` must be at least one minute in the future")
                    else:
                        config.endTime = int(endDT.timestamp())
        if icon is not None:
            config.icon = icon

        # Casting here because getGuildWithBounties ensures that `calling BBGuild` has bounties enabled
        bountiesDB = cast(BountyDB, callingBBGuild.bountiesDB)
        if division is not None:
            div = bountiesDB.divisionForName(division)
        else:
            if config.techLevel == -1:
                possibleDivisions = list(bountiesDB.divisions.values())
                div = random.choice(possibleDivisions)
                tries = 10
                while div.canMakeBounty():
                    if tries == 0:
                        errors.append("Unable to find a division that is not full")
                        break
                    div = random.choice(possibleDivisions)
                    tries -= 1
            else:
                div = bountiesDB.divisionForLevel(config.techLevel)
                if div.canMakeBounty():
                    errors.append("The division for the bounty's difficulty level is full")

        if errors:
            await interaction.response.send_message(":x: Unable to create the bounty due to the following error(s):\n" + "\n".join(f"- {error}" for error in errors), ephemeral=True)
        else:
            newBounty = bounty.Bounty(division=div, config=config.generate(div))
            bountiesDB.addBounty(newBounty)
            await interaction.response.send_message(":white_check_mark: Bounty created!", ephemeral=True)
            await callingBBGuild.announceNewBounty(newBounty)


    async def _setBountyXP(self, interaction: Interaction, xp: int, user_id: str):
        callingUser = await self.UsersUtilCog.getUserOrAuthor(interaction, user_id)
        if callingUser is None:
            return

        requestedBBUser = self.bot.usersDB.getOrAddID(callingUser.id)
        if requestedBBUser.classicModeEnabled:
            await interaction.response.send_message(":x: That user has classic mode enabled!", ephemeral=True)
            return

        newLevel = gameMaths.calculateUserBountyHuntingLevel(xp)

        errors = []
        # Handle bounty alert roles updates
        if requestedBBUser.hasHomeGuild and self.bot.guildsDB.idExists(requestedBBUser.homeGuildID):
            homeBGuild: basedGuild.BasedGuild = self.bot.guildsDB.getGuild(requestedBBUser.homeGuildID)
            if not homeBGuild.bountiesDisabled and homeBGuild.hasBountyAlertRoles:
                # Casing here because bountiesDisabled being False guarantees bountiesDB
                bountiesDB = cast(BountyDB, homeBGuild.bountiesDB)
                tl = gameMaths.calculateUserBountyHuntingLevel(requestedBBUser.bountyHuntingXP)
                oldDiv = bountiesDB.divisionForLevel(tl)
                oldRole = homeBGuild.dcGuild.get_role(oldDiv.alertRoleID)
                requestedMember = homeBGuild.dcGuild.get_member(callingUser.id)
                if requestedMember is not None:
                    if oldRole is None:
                        errors.append(f"I can't find the {nameForDivision(oldDiv).title()}" \
                                    + " division bounty alerts role, did it get deleted?")
                    elif oldRole in requestedMember.roles:
                        newDiv = bountiesDB.divisionForLevel(newLevel)
                        newRole = homeBGuild.dcGuild.get_role(newDiv.alertRoleID)
                        if newRole is None:
                            errors.append("I can't find the " \
                                        + f"{nameForDivision(newDiv).title()} division's bounty alerts " \
                                        + "role, did it get deleted?")
                        
                        elif oldRole is not None or newRole is not None:
                            errors = await homeBGuild.levelUpSwapRoles(requestedMember, oldRole, newRole)

        # update the balance
        oldXP = requestedBBUser.bountyHuntingXP
        requestedBBUser.bountyHuntingXP = xp
        await interaction.response.send_message(f"XP updated from {oldXP} to {xp}." + ("" if not errors else \
                                                "\nThe following error(s) occurred when updating the user's bounty alert role:" \
                                                + "\n".join(f"- {error}" for error in errors)), ephemeral=True)

#endregion util

    @divisionAutoComplete()
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer, helpSection="bounties")
    @app_commands.command(name="clear-bounties",
                            description="Developer command clearing all active bounties. See the help page for more info.")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_clear_bounties(self, interaction: Interaction, guild_id: str = "here", division: str = "all"):
        """developer command clearing all active bounties. If a guild ID is given, clear bounties in that guild.
        If 'all' is given, clear bounties in all guilds. If nothing is given, clear bounties in the calling guild.
        """
        valid, callingBBGuild = await self.GuildsUtilCog.getGuildWithBounties(interaction, guild_id)
        if not valid:
            return

        allDivs = await verifyDivName(interaction, division)
        if allDivs is None:
            return
                
        await interaction.response.defer(ephemeral=True)
        async def clearDiv(div: BountyDivision):
            await div.clear()

        await self.GuildsUtilCog.operateOverDivisionsAsync("dev_cmd_clear_bounties", clearDiv, "Active bounties cleared", division, interaction, callingBBGuild, allDivs, logCategory=LogCategory.bountiesDB)
        

    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer, helpSection="bounties")
    @app_commands.command(name="get-cool",
                            description="Developer command Getting a user's $check cooldown. Gets your cooldown if not user_id not provided.")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_get_cooldown(self, interaction: Interaction, user_id: str = ""):
        """developer command printing the calling user's checking cooldown
        """
        callingUser = await self.UsersUtilCog.getUserOrAuthor(interaction, user_id)
        if callingUser is None:
            return

        diff = datetime.utcfromtimestamp(callingUser.bountyCooldownEnd) - datetime.utcnow()
        minutes = int(diff.total_seconds() / 60)
        seconds = int(diff.total_seconds() % 60)
        await interaction.response.send_message("\n".join((
            str(callingUser.bountyCooldownEnd) + " = " + str(minutes) + "m, " + str(seconds) + "s.",
            datetime.utcfromtimestamp(callingUser.bountyCooldownEnd).strftime("%Hh%Mm%Ss"),
            datetime.utcnow().strftime("%Hh%Mm%Ss")
            )), ephemeral=True)

    
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer, helpSection="bounties")
    @app_commands.command(name="reset-cool",
                            description="reset the checking cooldown of the calling user, or the specified user if one is given")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_reset_cooldown(self, interaction: Interaction, user_id: str = ""):
        """developer command resetting the checking cooldown of the calling user, or the specified user if one is given
        """
        user = await self.UsersUtilCog.getUserOrAuthor(interaction, user_id)
        if user is None:
            return
        
        user.bountyCooldownEnd = datetime.utcnow().timestamp()
        await interaction.response.send_message("Done!", ephemeral=True)


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer, helpSection="bounties")
    @app_commands.command(name="set-check-cooldown",
                            description="set the cooldown of the /check command.")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_setcheckcooldown(self, interaction: Interaction, seconds: int = 0, minutes: int = 0, hours: int = 0):
        """developer command setting the checking cooldown applied to users
        this does not update cfg and will be reverted on bot restart
        """
        # update the checking cooldown amount
        # Can't do this directly as the properties are write only, so just make a new timedelta
        newTdDict = cfg.timeouts.checkCooldown.serialize().update({"seconds": seconds, "minutes": minutes, "hours": hours})
        cfg.timeouts.checkCooldown = SerializableTimedelta.deserialize(newTdDict)
        await interaction.response.send_message("Checking cooldown updated. **This will be reverted on bot restart unless the bot config is updated.**")


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer, helpSection="bounties")
    @app_commands.command(name="set-bounty-period",
                            description="set the new bounty generation period")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_setbountyperiodm(self, interaction: Interaction, seconds: int = 0, minutes: int = 0, hours: int = 0):
        """developer command setting the number of minutes in the new bounty generation period
        this does not update cfg and will be reverted on bot restart
        """
        # update the new bounty generation cooldown
        # Can't do this directly as the properties are write only, so just make a new timedelta
        newTdDict = cfg.timeouts.newBountyFixedDelta.serialize().update({"seconds": seconds, "minutes": minutes, "hours": hours})
        cfg.timeouts.newBountyFixedDelta = SerializableTimedelta.deserialize(newTdDict)
        botState.newBountyFixedDeltaChanged = True
        await interaction.response.send_message("New bounty period updated. **This will be reverted on bot restart unless the bot config is updated.**")


    @divisionAutoComplete()
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer, helpSection="bounties")
    @app_commands.command(name="reset-new-bounty-cool",
                            description="reset the current bounty generation period, triggering a bounty spawn.")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_resetnewbountycool(self, interaction: Interaction, guild_id: str = "here", division: str = "all"):
        """developer command resetting the current bounty generation period,
        instantly generating a new bounty
        """
        valid, callingBBGuild = await self.GuildsUtilCog.getGuildWithBounties(interaction, guild_id)
        if not valid:
            return

        allDivs = await verifyDivName(interaction, division)
        if allDivs is None:
            return
                
        await interaction.response.defer(ephemeral=True)
        def resetNewBountyCool(div: BountyDivision):
            if div.canMakeBounty():
                div.resetNewBountyCool()

        await self.GuildsUtilCog.operateOverDivisions(resetNewBountyCool, "New bounty cooldowns reset", division, interaction, callingBBGuild, allDivs)


    @divisionAutoComplete()
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer, helpSection="bounties")
    @app_commands.command(name="set-temp",
                            description="set the activity level for a given division in a given guild")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_set_temp(self, interaction: Interaction, division: str, temperature: Range[float, cfg.minTechLevel, cfg.maxTechLevel], guild_id: str = "here"):
        """developer command setting the activity level for the calling guild at the given tech level
        """
        valid, callingBBGuild = await self.GuildsUtilCog.getGuildWithBounties(interaction, guild_id)
        if not valid:
            return

        allDivs = await verifyDivName(interaction, division)
        if allDivs is None:
            return
                
        await interaction.response.defer(ephemeral=True)
        def callback(div: BountyDivision):
            div.setTemp(temperature)

        await self.GuildsUtilCog.operateOverDivisions(callback, f"Temperature set to {temperature}", division, interaction, callingBBGuild, allDivs)


    @divisionAutoComplete()
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer, helpSection="bounties")
    @app_commands.command(name="can-make-bounties",
                            description="Decide whether the given division(s) have space for more bounties.")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_canmakebounty(self, interaction: Interaction, guild_id: str = "here", division: str = "all"):
        """developer command printing whether or not the given division can accept new bounties
        """
        valid, callingBBGuild = await self.GuildsUtilCog.getGuildWithBounties(interaction, guild_id, allowAllGuilds=False)
        if not valid:
            return

        callingBBGuild = cast(basedGuild.BasedGuild, callingBBGuild)

        allDivs = await verifyDivName(interaction, division)
        if allDivs is None:
            return
                
        msgEmbed = lib.discordUtil.makeEmbed(callingBBGuild.dcGuild.name if callingBBGuild.dcGuild is not None else '')
        def callback(div: BountyDivision):
            msgEmbed.add_field(name=nameForDivision(div), value=str(not div.isFull() or not div.hasMinTLBounty()))

        await self.GuildsUtilCog.operateOverDivisions(callback, "", division, interaction, callingBBGuild, allDivs, sendSuccess=False)
        await interaction.followup.send(embed=msgEmbed)


    @systemAutoComplete("start")
    @systemAutoComplete("end")
    @systemAutoComplete("answer")
    @divisionAutoComplete(allowAllDivisions=False)
    @criminalAutoComplete()
    @factionAutoComplete(bountyFactionsOnly=True)
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer, helpSection="bounties")
    @app_commands.describe(
        guild_id="The id of the guild to create the bounty in, or 'here'. Defaults to here.",
        difficulty="The tech level of the bounty. Defaults to random.",
        division="The division of the bounty. Defaults to random.",
        name="The name of the criminal. Defaults to random.",
        faction="The faction of the criminal. Defaults to random.",
        route="A comma-separated list of systems. Defaults to random.",
        start="The start system. Defaults to random.",
        end="the end system. Defaults to random.",
        answer="The answer system. Defaults to random.",
        reward="The credits pool to share amongst contributors. Defaults to auto-generated based on loadout.",
        endTime="The end of the bounty as a unix timestamp. Defaults to auto-generated based on the route length. ",
        icon="The icon of the bounty. Defaults to the criminal's icon.",
        ship_dict="The loadout of the bounty as json. Defaults to random based on difficulty."
    )
    @app_commands.command(name="make-bounty",
                            description="spawn a new bounty in one guild")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_make_bounty(self, interaction: Interaction,
            guild_id: str = "here", difficulty: Optional[Range[int, cfg.minTechLevel, cfg.maxTechLevel]] = None, 
            division: Optional[str] = None, name: Optional[str] = None, faction: Optional[str] = None,
            route: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None, 
            answer: Optional[str] = None, reward: Optional[int] = None, endTime: Optional[str] = None,
            icon: Optional[str] = None, ship_dict: Optional[str] = None):
        """developer command making a new bounty
        """
        await self._makeBounty(interaction, guild_id=guild_id, difficulty=difficulty, division=division,
                                name=name, faction=faction, route=route, start=start, end=end, answer=answer,
                                reward=reward, endTime=endTime, icon=icon, ship_dict=ship_dict)


    @systemAutoComplete("start")
    @systemAutoComplete("end")
    @systemAutoComplete("answer")
    @divisionAutoComplete(allowAllDivisions=False)
    @factionAutoComplete(bountyFactionsOnly=True)
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer, helpSection="bounties")
    @app_commands.describe(
        player_id="The ID of the user.",
        guild_id="The id of the guild to create the bounty in, or 'here'. Defaults to here.",
        difficulty="The tech level of the bounty. Defaults to random.",
        division="The division of the bounty. Defaults to random.",
        faction="The faction of the criminal. Defaults to random.",
        route="A comma-separated list of systems. Defaults to random.",
        start="The start system. Defaults to random.",
        end="the end system. Defaults to random.",
        answer="The answer system. Defaults to random.",
        reward="The credits pool to share amongst contributors. Defaults to auto-generated based on loadout.",
        endTime="The end of the bounty as a unix timestamp. Defaults to auto-generated based on the route length. ",
        icon="The icon of the bounty. Defaults to the criminal's icon.",
        ship_dict="The loadout of the bounty as json. Defaults to random based on difficulty."
    )
    @app_commands.command(name="make-player-bounty",
                            description="spawn a new bounty for the given user in one guild")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_make_player_bounty(self, interaction: Interaction, player_id: str,
            guild_id: str = "here", difficulty: Optional[Range[int, cfg.minTechLevel, cfg.maxTechLevel]] = None, 
            division: Optional[str] = None, faction: Optional[str] = None,
            route: Optional[str] = None, start: Optional[str] = None, end: Optional[str] = None, 
            answer: Optional[str] = None, reward: Optional[int] = None, endTime: Optional[str] = None,
            icon: Optional[str] = None, ship_dict: Optional[str] = None):
        """developer command making a new bounty for a user
        """
        await self._makeBounty(interaction, guild_id=guild_id, difficulty=difficulty, division=division,
                                player_id=player_id, faction=faction, route=route, start=start, end=end, answer=answer,
                                reward=reward, endTime=endTime, icon=icon, ship_dict=ship_dict)


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer, helpSection="bounties")
    @app_commands.command(name="set-bounty-hunter-xp",
                            description="Set the requested user's bounty hunting xp")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_set_bounty_xp(self, interaction: Interaction, xp: int, user_id: str = ""):
        """developer command setting the requested user's bounty hunting xp.
        """
        await self._setBountyXP(interaction, xp, user_id)


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer, helpSection="bounties")
    @app_commands.command(name="set-bounty-hunter-level",
                            description="Set the requested user's bounty hunting xp, by level")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_set_bounty_level(self, interaction: Interaction, level: Range[int, cfg.minTechLevel, cfg.maxTechLevel], user_id: str = ""):
        """developer command setting the requested user's bounty hunting LEVEL.
        """
        await self._setBountyXP(interaction, gameMaths.bountyHuntingXPForLevel(level), user_id)


    @divisionAutoComplete()
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer, helpSection="bounties")
    @app_commands.command(name="measure-temps",
                            description="fetch the current activity temperatures of a guild's bounty division(s)")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_measure_temps(self, interaction: Interaction, guild_id: str = "here", division: str = "all"):
        """developer command fetching the current activity temperatures in the calling guild.
        """
        valid, callingBBGuild = await self.GuildsUtilCog.getGuildWithBounties(interaction, guild_id, allowAllGuilds=False)
        if not valid:
            return

        callingBBGuild = cast(basedGuild.BasedGuild, callingBBGuild)

        allDivs = await verifyDivName(interaction, division)
        if allDivs is None:
            return

        msgEmbed = lib.discordUtil.makeEmbed("Activity Temperatures", col=discord.Colour.random())
        if callingBBGuild.dcGuild is not None:
            msgEmbed.description = callingBBGuild.dcGuild.name
            if callingBBGuild.dcGuild.icon is not None:
                msgEmbed.set_thumbnail(url=callingBBGuild.dcGuild.icon.with_size(64).url)

        def callback(div: BountyDivision):
            msgEmbed.add_field(name=f"{nameForDivision(div).title()} Division", value=div.temperature)

        await self.GuildsUtilCog.operateOverDivisions(callback, "", division, interaction, callingBBGuild, allDivs, sendSuccess=False)
        await interaction.followup.send(embed=msgEmbed)


    @divisionAutoComplete()
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer, helpSection="bounties")
    @app_commands.command(name="decay-temps",
                            description="Trigger bounty activity temperature decay for one or all divisions, in one or all guilds")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_decay_temps(self, interaction: Interaction, guild_id: str = "here", division: str = "all"):
        """developer command decaying the activity temperatures of the calling guild
        """
        valid, callingBBGuild = await self.GuildsUtilCog.getGuildWithBounties(interaction, guild_id)
        if not valid:
            return

        allDivs = await verifyDivName(interaction, division)
        if allDivs is None:
            return
                
        await interaction.response.defer(ephemeral=True)
        def callback(div: BountyDivision):
            div.decayTemp()

        await self.GuildsUtilCog.operateOverDivisions(callback, f"Activity temperatures decayed", division, interaction, callingBBGuild, allDivs)


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer, helpSection="bounties")
    @app_commands.command(name="reset-temps",
                            description="Reset bounty activity temperatures to the minimum in one or all divisions, in one or all guilds")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_reset_temps(self, interaction: Interaction, guild_id: str = "here", division: str = "all"):
        """developer command resetting the activity temperatures of the calling guild
        """
        valid, callingBBGuild = await self.GuildsUtilCog.getGuildWithBounties(interaction, guild_id)
        if not valid:
            return

        allDivs = await verifyDivName(interaction, division)
        if allDivs is None:
            return
                
        await interaction.response.defer(ephemeral=True)
        def callback(div: BountyDivision):
            div.setTemp(cfg.minGuildActivity)

        await self.GuildsUtilCog.operateOverDivisions(callback, f"Activity temperatures reset", division, interaction, callingBBGuild, allDivs)


    @divisionAutoComplete()
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer, helpSection="bounties")
    @app_commands.command(name="next-bounty-time",
                            description="fetch the current activity temperatures of a guild's bounty division(s)")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_next_bounty_time(self, interaction: Interaction, guild_id: str = "here", division: str = "all"):
        """developer command DMing the calling user with the current delays on new bounty TTs for the calling guild
        """
        valid, callingBBGuild = await self.GuildsUtilCog.getGuildWithBounties(interaction, guild_id, allowAllGuilds=False)
        if not valid:
            return

        callingBBGuild = cast(basedGuild.BasedGuild, callingBBGuild)

        allDivs = await verifyDivName(interaction, division)
        if allDivs is None:
            return

        msgEmbed = lib.discordUtil.makeEmbed("Activity Temperatures", col=discord.Colour.random())
        if callingBBGuild.dcGuild is not None:
            msgEmbed.description = callingBBGuild.dcGuild.name
            if callingBBGuild.dcGuild.icon is not None:
                msgEmbed.set_thumbnail(url=callingBBGuild.dcGuild.icon.with_size(64).url)

        def callback(div: BountyDivision):
            if not div.canMakeBounty():
                msgEmbed.add_field(name=nameForDivision(div),
                                    value="<DIVISION FULL>")
            else:
                msgEmbed.add_field(name=nameForDivision(div),
                                    # Casting here because division.newBountyTT is guaranteed if the division is not full
                                    value=lib.timeUtil.td_format_noYM(cast(timedTask.TimedTask, div.newBountyTT).expiryDelta)
                                            + "\nExpiring " + cast(timedTask.TimedTask, div.newBountyTT).expiryTime.strftime("%B %d %H %M %S"))

        await self.GuildsUtilCog.operateOverDivisions(callback, "", division, interaction, callingBBGuild, allDivs, sendSuccess=False)
        await interaction.followup.send(embed=msgEmbed)


    @divisionAutoComplete()
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer, helpSection="bounties")
    @app_commands.command(name="max-bounties",
                            description="fetch the current max bounties of a guild's bounty division(s)")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_current_max_bounties(self, interaction: Interaction, guild_id: str = "here", division: str = "all"):
        """developer command DMing the calling user with the current max bounties for the given guild(s)/division(s)
        """
        valid, callingBBGuild = await self.GuildsUtilCog.getGuildWithBounties(interaction, guild_id, allowAllGuilds=False)
        if not valid:
            return

        callingBBGuild = cast(basedGuild.BasedGuild, callingBBGuild)

        allDivs = await verifyDivName(interaction, division)
        if allDivs is None:
            return

        msgEmbed = lib.discordUtil.makeEmbed("Activity Temperatures", col=discord.Colour.random())
        if callingBBGuild.dcGuild is not None:
            msgEmbed.description = callingBBGuild.dcGuild.name
            if callingBBGuild.dcGuild.icon is not None:
                msgEmbed.set_thumbnail(url=callingBBGuild.dcGuild.icon.with_size(64).url)

        def callback(div: BountyDivision):
            msgEmbed.add_field(name=nameForDivision(div),
                                    value=str(div.maxBounties()))

        await self.GuildsUtilCog.operateOverDivisions(callback, "", division, interaction, callingBBGuild, allDivs, sendSuccess=False)
        await interaction.followup.send(embed=msgEmbed)
        

    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer, helpSection="bounties")
    @app_commands.command(name="xp-for-level",
                            description="Get the amount of bounty hunter xp required to reach a given level")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_xp_for_level(self, interaction: Interaction, level: Range[int, cfg.minTechLevel, cfg.maxTechLevel]):
        """Print the amount of bounty hunter xp required to reach a given level.
        TODO: Possibly make this available to users? I think it'd just be bulk, no one would ever use it. Possibly an optional command that admins can enable?
        """
        await interaction.response.send_message(f"💎 **{gameMaths.bountyHuntingXPForLevel(level)}** total bounty hunter xp is required to reach level {level}.")

    
    @criminalAutoComplete("criminal")
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer, helpSection="bounties")
    @app_commands.command(name="force-expire-bounty",
                            description="Force the named bounty to expire immediately")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_force_expire_bounty(self, interaction: Interaction, criminal: str, guild_id: str = "here", include_escaped: BoolYesNo = BoolYesNo.Yes):
        """Force the named bounty to expire immediately.
        """
        valid, callingBBGuild = await self.GuildsUtilCog.getGuildWithBounties(interaction, guild_id)
        if not valid:
            return

        async def callback(db: BountyDB):
            try:
                bounty = db.getBounty(criminal)
            except KeyError:
                if include_escaped:
                    try:
                        bounty = db.getEscapedBounty(criminal)
                    except KeyError:
                        pass
                    else:
                        await bounty.expire()
            else:
                await bounty.expire()

        await self.GuildsUtilCog.operateOverBountyDBsAsync("dev_cmd_force_expire_bounty", callback, "Bounty expired", interaction, callingBBGuild)

    
    @criminalAutoComplete("criminal")
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer, helpSection="bounties")
    @app_commands.command(name="force-escape-bounty",
                            description="Force the named bounty to escape immediately")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_force_escape_bounty(self, interaction: Interaction, criminal: str, guild_id: str = "here"):
        """Force the named bounty to escape immediately.
        """
        valid, callingBBGuild = await self.GuildsUtilCog.getGuildWithBounties(interaction, guild_id)
        if not valid:
            return

        async def callback(db: BountyDB):
            try:
                bounty = db.getBounty(criminal)
            except KeyError:
                pass
            else:
                if not bounty.isEscaped():
                    bounty.escape()
                    if bounty.division.bountyBoardChannel is not None:
                        await db.owningBasedGuild.updateBountyBoardChannel(bounty, bountyComplete=True)
                        await bounty.division.bountyBoardChannel.updateEscapedBountiesMessage()

        await self.GuildsUtilCog.operateOverBountyDBsAsync("dev_cmd_force_escape_bounty", callback, "Bounty escaped", interaction, callingBBGuild, logCategory=LogCategory.escapedBounties)

    
    @criminalAutoComplete("criminal")
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer, helpSection="bounties")
    @app_commands.command(name="force-respawn-bounty",
                            description="Force the named bounty to respawn immediately")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_force_respawn_bounty(self, interaction: Interaction, criminal: str, guild_id: str = "here"):
        """Force the named bounty to respawn immediately.
        """
        valid, callingBBGuild = await self.GuildsUtilCog.getGuildWithBounties(interaction, guild_id)
        if not valid:
            return

        def callback(db: BountyDB):
            try:
                bounty = db.getEscapedBounty(criminal)
            except KeyError:
                pass
            else:
                bounty.forceRespawn()

        await self.GuildsUtilCog.operateOverBountyDBs(callback, "Bounty respawned", interaction, callingBBGuild)


    @divisionAutoComplete()
    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer, helpSection="bounties")
    @app_commands.command(name="restart-bounty-task",
                            description="Restart the bounty spawner task for one or all divisions in one or all guilds")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_restart_new_bounty_task(self, interaction: Interaction, guild_id: str = "here", division: str = "all"):
        """developer command that restarts a 'new bounties' timedtask for one or all divisions in one or all guilds
        """
        valid, callingBBGuild = await self.GuildsUtilCog.getGuildWithBounties(interaction, guild_id)
        if not valid:
            return

        allDivs = await verifyDivName(interaction, division)
        if allDivs is None:
            return
                
        def callback(div: BountyDivision):
            if div.newBountyTT is not None:
                div.stopBountySpawner()
            if not div.isFull() or not div.hasMinTLBounty():
                div.tryStartBountySpawner()

        await self.GuildsUtilCog.operateOverDivisions(callback, f"Bounty spawner restarted", division, interaction, callingBBGuild, allDivs)


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer, helpSection="bounties")
    @app_commands.command(name="can-div-up",
                            description="Decide whether a user can div-up (or prestige if they are max level)")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_user_can_divup_or_prestige(self, interaction: Interaction, user_id: str = ""):
        """Decide whether a user can div-up/prestige
        """
        u = await self.UsersUtilCog.getUserOrAuthor(interaction, user_id)
        if u is not None:
            await interaction.response.send_message(f"{u.canDivUp()} ({u.bountyHuntingXpSurplus}xp surplus)")


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer, helpSection="bounties",
                                formattedDesc="Set the amount of xp a user will be awarded AFTER using div-up.\n" \
                                            + "Set to at least 0 to enable div-up. Set to -1 to disable div-up.\n" \
                                            + "-> Also enables prestiging, but no xp is awarded after.")
    @app_commands.command(name="set-xp-surplus",
                            description="Enable a user's ability to div-up or prestige by setting their xp surplus")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_set_user_divup_surplus(self, interaction: Interaction, xp_surplus: int, user_id: str = ""):
        """Change a user's ability to div-up or prestige by setting their xp surplus
        """
        u = await self.UsersUtilCog.getUserOrAuthor(interaction, user_id)
        if u is not None:
            oldSurplus = u.bountyHuntingXpSurplus
            canDivup = u.canDivUp()

            u.bountyHuntingXpSurplus = xp_surplus
            if xp_surplus == -1:
                await interaction.response.send_message("✅ set successfully!" + (f"User can no longer div-up ({oldSurplus} -> {xp_surplus})" if canDivup else "No change."))
            else:
                await interaction.response.send_message("✅ set successfully!" + (f"User can now div-up ({oldSurplus} -> {xp_surplus})" if not canDivup else f"User was already able to div-up. ({oldSurplus} -> {xp_surplus})"))


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer, helpSection="bounties")
    @app_commands.command(name="disable-div-up",
                            description="Disable a user's ability to div-up/prestige, clearing their xp surplus")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_disable_user_can_divup_or_prestige(self, interaction: Interaction, user_id: str = ""):
        """Disable a user's ability to div-up/prestige, setting their xp surplus to -1.
        """
        u = await self.UsersUtilCog.getUserOrAuthor(interaction, user_id)
        if u is not None:
            oldSurplus = u.bountyHuntingXpSurplus
            canDivup = u.canDivUp()

            u.bountyHuntingXpSurplus = -1
            await interaction.response.send_message("✅ set successfully!" + (f"User can no longer div-up ({oldSurplus} -> -1)" if canDivup else "No change."))


    @basedCommand.basedCommand(accessLevel=basicAccessLevels.developer, helpSection="bounties")
    @app_commands.command(name="enable-div-up",
                            description="Enable a user's ability to div-up/prestige, with no xp surplus")
    @app_commands.guilds(*cfg.developmentGuilds)
    async def dev_cmd_enable_user_can_divup_or_prestige(self, interaction: Interaction, user_id: str = ""):
        """Enable a user's ability to div-up/prestige, setting their xp surplus to 0.
        """
        u = await self.UsersUtilCog.getUserOrAuthor(interaction, user_id)
        if u is not None:
            canDivup = u.canDivUp()
            if canDivup:
                await interaction.response.send_message("✅ User was already able to div-up. No change to xp surplus.")
            else:
                u.bountyHuntingXpSurplus = -0
                await interaction.response.send_message(f"✅ set successfully! User can now div-up (-1 -> 0)")


#endregion commands


async def setup(bot: client.BasedClient):
    # Casting here because for some reason pyright doesn't think SerializableDiscordObject is a Snowflake,
    # even though it extends discord.Object
    await bot.add_cog(DevBountiesCog(bot), guilds=cast(List[Snowflake], cfg.developmentGuilds))