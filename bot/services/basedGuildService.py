from ..entities.guilds.basedGuild import BasedGuild
from . import bountyDivisionService

class BasedGuildService():
    def __init__(self, bountyDivisionService: "bountyDivisionService.BountyDivisionService") -> None:
        self.bountyDivisionService = bountyDivisionService


    async def clearAllBounties(self, guildId: int, includeEscaped: bool =True):
        """Clear all bounties in a guild
        If any division was full before, restart its new bounty spawner

        :param bool includeEscaped: Whether to also clear escaped criminals (Default True)
        """
        self.bountyDivisionService.clear
        for div in self.divisions.values():
            await div.clear(includeEscaped=includeEscaped)

    
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
            for div in cast(bountyRepository.BountyRepository, g.bountiesDB).divisions.values():
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
        

    async def spawnAndAnnounceBounty(self, guildId: int, newBountyData, isRespawn: bool = False):
        """Generate a new bounty, either at random or by the given bbBountyConfig, spawn it,
        and announce it if this guild has an appropriate channel selected.
        """
        if self.bountiesDisabled:
            botState.client.logger.log("basedGuild", "spwnAndAnncBty",
                                "Attempted to spawn a bounty into a guild where bounties are disabled: " \
                                    + (self.dcGuild.name if self.dcGuild is not None else "") + "#" + str(self.id),
                                eventType="BTYS_DISABLED")
            return
        # ensure a new bounty can be created
        # Casting here because bountiesDB cannot be None if bountiesDisabled is False
        bountiesDB = cast(BountyRepository, self.bountiesDB)

        if isRespawn or bountiesDB.canMakeBounty():
            newBounty: bounty.Bounty = newBountyData["newBounty"]
            config: bountyConfig.BountyConfig = newBountyData["newConfig"].copy() if "newConfig" in newBountyData else bountyConfig.BountyConfig()

            if newBounty is not None:
                div = newBounty.division
                if config.techLevel == -1:
                    config.techLevel = newBounty.techLevel
            elif config.techLevel != -1:
                div = bountiesDB.divisionForLevel(config.techLevel)
            else:
                div: "bountyDivision.BountyDivision" = random.choice(list(bountiesDB.divisions.values()))
                while div.isFull():
                    div = random.choice(list(bountiesDB.divisions.values()))
                config.techLevel = div.pickNewTL()

            if newBounty is None:
                newBounty = bounty.Bounty(division=div, config=config)
            else:
                # If removed, uncomment this line from bounty._respawn
                if bountiesDB.escapedCriminalExists(newBounty.criminal):
                    bountiesDB.removeEscapedCriminal(newBounty.criminal)

                if config is not None:
                    newConfig = config.copy()
                    if not newConfig.generated:
                        newConfig.generate(div)
                    newBounty.route = newConfig.route
                    newBounty.answer = newConfig.answer
                    newBounty.checked = newConfig.checked
                    newBounty.reward = newConfig.reward
                    newBounty.issueTime = newConfig.issueTime
                    newBounty.endTime = newConfig.endTime

            # activate and announce the bounty
            bountiesDB.addBounty(newBounty, isRespawn=isRespawn)
            await self.announceNewBounty(newBounty, isRespawn=isRespawn)
        
        else:
            raise OverflowError("Attempted to spawnAndAnnounceBounty when no more space is available for bounties " \
                                + "in the bountiesDB")
        
    
    async def makeBountyAlertRoles(self):
        """Create a set of new roles to ping when bounties are created.

        :raise ValueError: If the guild already has new bounty alert roles set, or has bounties disabled
        :raise Forbidden: If the bot does not have role creation permissions
        :raise HTTPException: If creation of any role failed
        :raise RuntimeError: If any roles failed to create for some unexpected reason
        """
        if self.hasBountyAlertRoles:
            raise ValueError("This guild already has bounty alert roles")
        if self.bountiesDisabled:
            raise ValueError("This guild has bounties disabled")
        roleMakers = lib.discordUtil.BasicScheduler()
        divsDone = set()
        async def makeDivRole(div: bountyDivision.BountyDivision):
            divsDone.add(div)
            divName = nameForDivision(div)
            divID = cfg.bountyDivisionNames.index(divName)
            newRole = await self.dcGuild.create_role(name=f"{divName.title()} Bounty Hunter",
                                                    colour=Colour.from_rgb(*cfg.bountyAlertRoleColoursByDivision[divID]),
                                                    reason="Creating new bounty alert roles requested by BB command")
            div.alertRoleID = newRole.id
        
        # Casting here because bountiesDB cannot be None if bountiesDisabled is False
        bountiesDB = cast(BountyRepository, self.bountiesDB)
        for div in bountiesDB.divisions.values():
            roleMakers.add(makeDivRole(div))

        await roleMakers.wait()
        exceptions = roleMakers.getExceptions()
        if exceptions:
            for doneDiv in divsDone:
                doneDiv.alertRoleID = -1
            raise list(exceptions.values())[0]
        # Casting here because bountiesDB cannot be None if bountiesDisabled is False
        for div in bountiesDB.divisions.values():
            if div.alertRoleID == -1:
                # Casting here because bountiesDB cannot be None if bountiesDisabled is False
                for doneDiv in bountiesDB.divisions.values():
                    doneDiv.alertRoleID = -1
                raise RuntimeError("An unknown error occurred when creating roles")
        
        self.hasBountyAlertRoles = True


    async def deleteBountyAlertRoles(self):
        """Delete the bounty alert roles from the server.

        :raise ValueError: If the guild does not have new bounty alert roles set
        :raise Forbidden: If the bot does not have role deletion permissions
        :raise HTTPException: If deletion of any role failed
        """
        if not self.hasBountyAlertRoles:
            raise ValueError("This guild does not have bounty alert roles")
        roleRemovers = lib.discordUtil.BasicScheduler()
        async def removeDivRole(div: bountyDivision.BountyDivision):
            if div.alertRoleID != -1:
                tlRole = self.dcGuild.get_role(div.alertRoleID)
                if tlRole is None:
                    await self.dcGuild.fetch_roles()
                tlRole = self.dcGuild.get_role(div.alertRoleID)
                if tlRole is not None:
                    await tlRole.delete(reason="Removing new bounty alert roles requested by BB command")
                div.alertRoleID = -1
        
        # Casting here because bountiesDB cannot be None if bountiesDisabled is False
        for div in cast(BountyRepository, self.bountiesDB).divisions.values():
            roleRemovers.add(removeDivRole(div))
        await roleRemovers.wait()
        roleRemovers.raiseExceptions()

        self.hasBountyAlertRoles = False


    async def levelUpSwapRoles(self, dcUser: Member, oldRole: Optional[Role], newRole: Optional[Role],
                                    actionOverride="leveled up") -> List[str]:
        """Remove oldRole from dcUser, and grant newRole.
        If errors occur, they will be printed in the context of dcUser leveling up their bounty Hunting level,
        and sent in channel. If oldRole or newRole are given as None, they will be ignored and no exception raised.

        :param Member dcUser: The user to toggle roles for
        :param Role oldRole: The role to remove, corresponding to dcUser's previous tech level
        :param Role newRole: The role to grant, corresponding to dcUser's new tech level
        :param str actionOverride: The reason for the role change, inserted partially into each message.
                                    (Default "leveled up")
        :returns: A list of errors that occurred
        :rtype: List[str]
        """
        errors = []
        if oldRole is not None:
            try:
                await dcUser.remove_roles(oldRole, reason=f"User {actionOverride} into a new division")
            except Forbidden:
                errors.append("I don't have permission to remove your old division role! Please ensure " \
                                    + "it is beneath the BountyBot role.")
            except HTTPException as e:
                errors.append("Something went wrong when removing your old division role!\n" \
                                    + "The error has been logged.")
                botState.client.logger.log("main", "cmd_notify",
                                    f"{type(e).__name__} occurred when attempting to remove new bounty role " \
                                        + f"{oldRole.name}#{oldRole.id}  from user {dcUser.name}#{dcUser.id}" \
                                        + f" in guild {self.dcGuild.name}#{self.id}.",
                                    category=LogCategory.userAlerts, exception=e)
            except client_exceptions.ClientOSError as e:
                errors.append("A connection error occurred when removing your old division role, " \
                                    + "the error has been logged.")
                botState.client.logger.log("main", "cmd_notify",
                                    f"{type(e).__name__} occurred when attempting to remove new bounty role " \
                                        + f"{oldRole.name}#{oldRole.id}  from user {dcUser.name}#{dcUser.id}" \
                                        + f" in guild {self.dcGuild.name}#{self.id}.",
                                    category=LogCategory.userAlerts, exception=e)
        if newRole is not None:
            try:
                await dcUser.add_roles(newRole, reason=f"User {actionOverride} into a new division")
            except Forbidden:
                errors.append("I don't have permission to grant your new division role! Please ensure " \
                                    + "it is beneath the BountyBot role.")
            except HTTPException as e:
                errors.append("Something went wrong when granting your new division role!\n" \
                                    + "The error has been logged.")
                botState.client.logger.log("main", "cmd_notify",
                                    f"{type(e).__name__} occurred when attempting to grant new bounty role " \
                                        + f"{newRole.name}#{newRole.id}  from user {dcUser.name}#{dcUser.id}" \
                                        + f" in guild {self.dcGuild.name}#{self.id}.",
                                    category=LogCategory.userAlerts, exception=e)
            except client_exceptions.ClientOSError as e:
                errors.append("A connection error occurred when granting your new division role, " \
                                    + "the error has been logged.")
                botState.client.logger.log("main", "cmd_notify",
                                    f"{type(e).__name__} occurred when attempting to grant new bounty role " \
                                        + f"{newRole.name}#{newRole.id}  from user {dcUser.name}#{dcUser.id}" \
                                        + f" in guild {self.dcGuild.name}#{self.id}.",
                                    category=LogCategory.userAlerts, exception=e)
        return errors
    

    async def announceNewBounty(self, newBounty: bounty.AnyBounty, isRespawn: bool = False):
        """Announce the creation of a new bounty to this guild's announceChannel, if it has one

        :param bounty newBounty: the bounty to announce
        """
        if newBounty.activeShip is None:
            raise ValueError(f"Bounty does not have a ship: {newBounty.criminal.name}")
        print("Difficulty", newBounty.techLevel, "New bounty with value:", newBounty.activeShip.getValue())
        # Create the announcement embed
        bountyEmbed = lib.discordUtil.makeEmbed(titleTxt=lib.discordUtil.criminalNameOrDiscrim(newBounty.criminal),
                                                col=cfg.factionColourOrDefault(newBounty.faction),
                                                thumb=newBounty.criminal.icon, footerTxt=newBounty.faction.title())
        if isRespawn:
            bountyEmbed.description = f"{cfg.defaultEmojis.bountyRespawn.sendable} __Bounty Respawned__"
            msg = f"A bounty has reappeared onto the **{newBounty.faction.title()}** bounty board:"
        else:
            bountyEmbed.description = f"{cfg.defaultEmojis.newBounty.sendable} __New Bounty Available__"
            msg = f"A new bounty is now available from **{newBounty.faction.title()}** central command:"
            
        bountyEmbed.add_field(name="**Reward Pool:**", value=str(newBounty.reward) + " Credits")
        bountyEmbed.add_field(name="**Difficulty:**", value=str(newBounty.techLevel))
        bountyEmbed.add_field(name="**See the culprit's loadout with:**",
                                value="`" + self.commandPrefix + "loadout criminal " + newBounty.criminal.name + "`")
        bountyEmbed.add_field(name="**Route:**", value=", ".join(newBounty.route), inline=False)
        bountyEmbed.add_field(name="Bounty ends:", value=f"<t:{int(newBounty.endTime)}:R>")

        if self.hasBountyBoardChannels:
            # Casting here because division.bountyBoardChannel is guaranteed for every division, if the guild has hasBountyBoardChannels as True
            bbc = cast(bountyBoardChannel.BountyBoardChannel, newBounty.division.bountyBoardChannel)
            try:
                if self.hasBountyAlertRoles:
                    msg = f"<@&{newBounty.division.alertRoleID}> {msg}"
                # announce to the given channel
                bountyListing = await bbc.channel.send(msg, embed=bountyEmbed)
                await bbc.addBounty(newBounty, bountyListing)
                await bbc.updateBountyMessage(newBounty)
                return bountyListing

            except Forbidden:
                dcGuild = botState.client.get_guild(self.id)
                guildName = "<unknown>" if dcGuild is None else dcGuild.name
                botState.client.logger.log("BasedGuild", "anncBnty",
                                    "Failed to post BBCh listing to guild " + guildName + "#" \
                                    + str(self.id) + " in channel " + bbc.channel.name + "#" \
                                    + str(bbc.channel.id), category=LogCategory.bountyBoards,
                                    eventType="BBC_NW_FRBDN")

        # If the guild has an announceChannel
        elif self.hasAnnounceChannel():
            # ensure the announceChannel is valid
            currentChannel = self.getAnnounceChannel()
            if currentChannel is not None:
                try:
                    if self.hasBountyAlertRoles:
                        # announce to the given channel
                        await currentChannel.send(f"<@&{newBounty.division.alertRoleID}> {msg}",
                                                    embed=bountyEmbed)
                    else:
                        await currentChannel.send(msg, embed=bountyEmbed)
                except Forbidden:
                    dcGuild = botState.client.get_guild(self.id)
                    guildName = "<unknown>" if dcGuild is None else dcGuild.name
                    botState.client.logger.log("BasedGuild", "anncBnty",
                                        "Failed to post announce-channel bounty listing to guild " \
                                        + guildName + "#" + str(self.id) + " in channel " \
                                        + currentChannel.name + "#" + str(currentChannel.id), eventType="ANNCCH_SND_FRBDN")

            # TODO: may wish to add handling for invalid announceChannels - e.g remove them from the BasedGuild object


    async def announceBountyWon(self, bounty: bounty.Bounty, rewards: Dict[int, Dict[str, Union[int, bool]]],
                                winningUser: Union[Member, User], rewardsMeta: Dict[int, bounty.RewardsMeta],
                                leveledUp: Dict["basedUser.BasedUser", List[GameItem]]):
        """Announce the completion of a bounty
        Messages will be sent to the playChannel if one is set

        :param bounty bounty: the bounty to announce
        :param dict rewards: the rewards dictionary as defined by bounty.calculateRewards
        :param discord.Member winningUser: the guild member that won the bounty
        :param rewardsMeta: mapping from user ID to binary flags for special rewards handling (bounty.RewardsMeta)
        :type rewardsMeta: Dict[int, int]
        :param divUpUnlockedUserIDs: IDs for each user that unlocked the next division with this bounty.
        :type divUpUnlockedUserIDs: List[int]
        :param prestigeUnlockedUserIDs: IDs for each user that unlocked prestiging with this bounty.
        :type prestigeUnlockedUserIDs: List[int]
        """
        if self.dcGuild is None:
            dcGuild = botState.client.get_guild(self.id)
            guildName = "<unknown>" if dcGuild is None else dcGuild.name
            botState.client.logger.log("Main", "AnncBtyWn",
                                "None dcGuild received when posting bounty won to guild " \
                                + guildName + "#" + str(self.id) + " in channel ?#" \
                                + str(self.getPlayChannel().id), eventType="DCGUILD_NONE")
            return

        if self.bountiesDB is None or not self.hasPlayChannel(): return
        
        # Create the announcement embed
        rewardsEmbed = lib.discordUtil.makeEmbed(titleTxt="Bounty Complete!",
                                                authorName=lib.discordUtil.criminalNameOrDiscrim(bounty.criminal) \
                                                + " Arrested", icon=bounty.criminal.icon,
                                                col=cfg.factionColourOrDefault(bounty.faction),
                                                desc="`Suspect located in '" + bounty.answer + "'`")

        # Add the winning user to the embed
        rewardsEmbed.add_field(**bountyResultsFieldKwargs(1, winningUser.id, rewards[winningUser.id],
                                                            rewardsMeta[winningUser.id]))

        # The index of the current user in the embed
        place = 2
        # Loop over all non-winning users in the rewards dictionary
        for userID, userRewards in rewards.items():
            if not userRewards["won"]:
                rewardsEmbed.add_field(**bountyResultsFieldKwargs(place, userID, userRewards, rewardsMeta[userID]))
                place += 1

        levelUpsStr = ""
        division: Optional[bountyDivision.BountyDivision] = None
        divUpUnlocked: List["basedUser.BasedUser"] = []

        for user, userRewards in leveledUp.items():
            level = gameMaths.calculateUserBountyHuntingLevel(user.bountyHuntingXP)
            levelUpsStr += "\n:arrow_up: **Level Up!**\n" \
                        + f"<@{user.id}> reached **Bounty Hunter Level {level}!** :partying_face:"

            if len(userRewards) == 1:
                levelUpsStr += f"\nYou got a **{userRewards[0].name}**."
            elif len(userRewards) != 0:
                levelUpsStr += "\nYou got:\n- " + "\n".join(f"- a **{i.name}**" for i in userRewards)
            
            division = division or self.bountiesDB.divisionForLevel(level)
            if level == division.maxLevel:
                divUpUnlocked.append(user)

        if divUpUnlocked:
            if len(divUpUnlocked) > 1:
                levelUpsStr += ", ".join(f"<@{i.id}>" for i in divUpUnlocked[:-1]) + f" and <@{divUpUnlocked[-1].id}>"
            else:
                levelUpsStr += f"<@{divUpUnlocked[0].id}>"
                
            if cast(bountyDivision.BountyDivision, division).maxLevel == cfg.maxTechLevel:
                levelUpsStr += f" unlocked prestiging! use the `{self.commandPrefix}prestige` command to " \
                                + "gain special rewards and start a new run!"
            else:
                levelUpsStr += f" unlocked the next division! use the `/div-up` command to " \
                                + "move up, and take on tougher bounties!\n"

        # Send the announcement to the guild's playChannel
        await self.getPlayChannel().send(":trophy: **You win!**\n**" + winningUser.display_name \
                                            + "** located and EMP'd **" + bounty.criminal.name \
                                            + "**, who has been arrested by local security forces. :chains:\n\n" \
                                            + levelUpsStr,
                                            embed=rewardsEmbed)


    async def announceBountyExpired(self, b: bounty.AnyBounty):
        """Announce the expiry of a bounty. Does not update the bountyboard channel if one exists.

        :param b: The bounty that has expired
        :type b: bounty.Bounty
        """
        if self.dcGuild is not None:
            if self.hasPlayChannel():
                await self.getPlayChannel().send(embed=makeBountyExpiredEmbed(b))
        else:
            dcGuild = botState.client.get_guild(self.id)
            guildName = "<unknown>" if dcGuild is None else dcGuild.name
            botState.client.logger.log("Main", "AnncBtyWn",
                                "None dcGuild received when posting bounty expiry to guild " \
                                + guildName + "#" + str(self.id) + " in channel ?#" \
                                + str(self.getPlayChannel().id), eventType="DCGUILD_NONE")
            
    
    async def enableBounties(self):
        """Enable bounties for this guild.
        Sets up a new bounties DB and bounty spawning TimedTask.

        :raise ValueError: If bounties are already enabled in this guild
        """
        if not self.bountiesDisabled:
            raise ValueError("Bounties are already enabled in this guild")

        self.bountiesDisabled = False


    async def disableBounties(self):
        """Disable bounties for this guild.
        Removes any bountyboard if one is present, and removes the guild's bounties DB and bounty spawning TimedTask.

        :raise ValueError: If bounties are already disabled in this guild
        """
        if self.bountiesDisabled:
            raise ValueError("Bounties are already disabled in this guild")

        if self.hasBountyBoardChannels:
            # Casting here because guild.bountiesDB can be None, but this is checked for in the hasBountyBoardChannels check above
            for div in cast(BountyRepository, self.bountiesDB).divisions.values():
                div.removeBountyBoardChannel()
            self.hasBountyBoardChannels = False
        self.bountiesDisabled = True
        self.bountiesDB = None

        if self.hasBountyAlertRoles:
            await self.deleteBountyAlertRoles()


    async def enableShops(self):
        """Enable shops for this guild.
        Creates a new guildShop object for each division.

        :raise ValueError: If shops are already enabled in this guild
        """
        if not self.shopsDisabled:
            raise ValueError("Shop are already enabled in this guild")

        self.divisionShops = {divName: guildShop.TechLeveledShop(max(cfg.minTechLevel, levels[0]), levels[1], noRefresh=True) \
                                for divName, levels in bountyDivision.divisionNameLevels().items()}
        self.shopsDisabled = False


    async def disableShops(self):
        """Disable shops for this guild.
        Removes the guild's guildShop objects.

        :raise ValueError: If shops are already disabled in this guild
        """
        if self.shopsDisabled:
            raise ValueError("Shop are already disabled in this guild")

        self.divisionShops = None
        self.shopsDisabled = True


    async def announceNewShopStock(self, newLevel: Optional[int] = None):
        """Announce to the guild's play channel that this guild's shop stock has been refreshed.
        If no playChannel has been set, does nothing.
        If newLevel is None, announce that all of the guild's shops have been refreshed.
        Otherwise, just announce that the shop owning that level has refreshed.

        :raise ValueError: If this guild's shop is disabled
        """
        if self.shopsDisabled:
            raise ValueError("Attempted to announceNewShopStock on a guild where shop is disabled")
        if self.hasPlayChannel():
            playCh = self.getPlayChannel()
            msg = "The shop stock has been refreshed!"
            msgEmbed = Embed()
            if newLevel is None:
                for divName, shop in cast(Dict[str, guildShop.TechLeveledShop], self.divisionShops).items():
                    msgEmbed.add_field(name=divName, value=f"Now at level **{shop.currentTechLevel}**")
            else:
                msgEmbed.add_field(name=divisionNameForLevel(newLevel), value=f"Now at level **{newLevel}**")
            try:
                if self.hasUserAlertRoleID("shop_refresh"):
                    # announce to the given channel
                    await playCh.send(":arrows_counterclockwise: <@&" \
                                            + str(self.getUserAlertRoleID("shop_refresh")) + "> " + msg,
                                        embed=msgEmbed)
                else:
                    await playCh.send(":arrows_counterclockwise: " + msg,
                                        embed=msgEmbed)
            except Forbidden:
                botState.client.logger.log("Main", "anncNwShp",
                                    "Failed to post shop stock announcement to " + self.dcGuild.name + "#" + str(self.id) \
                                    + " in channel " + playCh.name + "#" + str(playCh.id), category=LogCategory.shop,
                                    eventType="PLCH_NONE")