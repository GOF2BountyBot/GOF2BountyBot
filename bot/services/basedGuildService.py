class BasedGuildService():
    async def clearAllBounties(self, guildId: int, includeEscaped=True):
        """Clear all bounties in a guild
        If any division was full before, restart its new bounty spawner

        :param bool includeEscaped: Whether to also clear escaped criminals (Default True)
        """
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