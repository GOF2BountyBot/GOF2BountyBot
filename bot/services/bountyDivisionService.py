class BountyDivisionService():
    def nameForDivision(self, div: BountyDivision) -> str:
        """Get the name for the given BountyDivision, as specified in cfg.bountyDivisionNames.

        :param BountyDivison div: The division to get the name of
        :return: The name for the given division
        :rtype: str
        :raise KeyError: When no name is found for the given division
        """
        try:
            return next(k for i, k in enumerate(cfg.bountyDivisionNames) if div.minLevel == cfg.bountyDivisionLevels[i][0])
        except KeyError:
            raise KeyError(f"The given division is non-standard, no name found: {div} range: {div.minLevel} - {div.maxLevel}")


    def divisionNameForLevel(self, tl: int) -> str:
        """Get the name of the division which players and bounties of the given techlevel belong to.

        :param int tl: The techlevel whose division name to find
        :return: The name for divisions responsible for bounties of the given level
        :rtype: str
        :raise KeyError: When no division is found for bounties of the given level
        """
        try:
            return next(k for i, k in enumerate(cfg.bountyDivisionNames) \
                        if cfg.bountyDivisionLevels[i][0] <= tl <= cfg.bountyDivisionLevels[i][1])
        except StopIteration:
            raise KeyError(f"No division found for bounties of TL {tl}")