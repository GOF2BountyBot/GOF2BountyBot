from typing import Dict, List, Union, cast
from ..lib.emojis import BasedEmoji, UninitializedBasedEmoji

# All emojis used by the bot
defaultEmojis = cast(Dict[str, Union[BasedEmoji, List[BasedEmoji]]], {
    # The emoji that will be used when attempting to display an emoji which the bot cannot access. Make sure this is accessible.
    "unrecognisedEmoji": UninitializedBasedEmoji("⁉"),
    # When a message prompts a process that will take a long time (e.g rendering), this will be added to the message reactions
    # It will be removed when the long process is finished.
    "longProcess": UninitializedBasedEmoji("⏳"),
    # When a user message prompts a DM to be sent, this emoji will be added to the message reactions.
    "dmSent": UninitializedBasedEmoji("📬"),
    "cancel": UninitializedBasedEmoji("❌"),
    "submit": UninitializedBasedEmoji("✅"),
    "spiral": UninitializedBasedEmoji("🌀"),
    "error": UninitializedBasedEmoji("❓"),
    "accept": UninitializedBasedEmoji("👍"),
    "reject": UninitializedBasedEmoji("👎"),
    "next": UninitializedBasedEmoji('⏩'),
    "previous": UninitializedBasedEmoji('⏪'),
    "numbers": [UninitializedBasedEmoji("0️⃣"), UninitializedBasedEmoji("1️⃣"), UninitializedBasedEmoji("2️⃣"),
                UninitializedBasedEmoji("3️⃣"), UninitializedBasedEmoji("4️⃣"), UninitializedBasedEmoji("5️⃣"),
                UninitializedBasedEmoji("6️⃣"), UninitializedBasedEmoji("7️⃣"), UninitializedBasedEmoji("8️⃣"),
                UninitializedBasedEmoji("9️⃣"), UninitializedBasedEmoji("🔟")],

    # The default emojis to list in a reaction menu
    "menuOptions": [UninitializedBasedEmoji("0️⃣"), UninitializedBasedEmoji("1️⃣"), UninitializedBasedEmoji("2️⃣"),
                    UninitializedBasedEmoji("3️⃣"), UninitializedBasedEmoji("4️⃣"), UninitializedBasedEmoji("5️⃣"),
                    UninitializedBasedEmoji("6️⃣"), UninitializedBasedEmoji("7️⃣"), UninitializedBasedEmoji("8️⃣"),
                    UninitializedBasedEmoji("9️⃣"), UninitializedBasedEmoji("🔟")],

    # Default emoji to assign to shipSkinTool items
    "shipSkinTool": UninitializedBasedEmoji("🎨"),

    # Default emoji to assign to bbCrates containing shipSkinTools
    "skinCrate": UninitializedBasedEmoji("🧰"),

    # Default emoji to assign to all other crates
    "defaultCrate": UninitializedBasedEmoji("📦"),
    
    # Emoji sent with new bounty listings
    "newBounty": UninitializedBasedEmoji("⛓"),

    "bountyRespawn": UninitializedBasedEmoji("⛓"),

    "newIssue": UninitializedBasedEmoji("📥"),
    "issueClosed": UninitializedBasedEmoji("✅"),
    "bug": UninitializedBasedEmoji("🕷"),
    "feature": UninitializedBasedEmoji("✨"),
    "gameBalance": UninitializedBasedEmoji("⚖"),
    "optimisation": UninitializedBasedEmoji("🚀"),

    "cropImage": UninitializedBasedEmoji("✂"),
    "stretchImage": UninitializedBasedEmoji("↔")
})

timeouts = {
    "helpMenu": {"minutes": 3},
    "BASED_updateCheckFrequency": {"days": 1},
    # The time to wait inbetween database autosaves.
    "dataSaveFrequency": {"hours": 1},

    # Amount of time before a duel request expires
    "duelRequest": {"days": 1},

    # Amount of time to wait between refreshing stock of all shops
    "shopRefresh": {"days": 0, "hours": 6, "minutes": 0, "seconds": 0},

    # time to put users on cooldown between using !bb check
    "checkCooldown": {"minutes": 3},

    # Default amount of time reaction menus should be active for
    "roleMenuExpiry": {"days": 1},
    "duelChallengeMenuExpiry": {"hours": 2},
    "pollMenuExpiry": {"minutes": 5},

    # The time between decrements to the guild activity temperatures of each tech level
    "guildActivityDecay": {"hours": 1},

    # when using random bounty delay generation, use these min and max points
    # when using random-routeScale generation, use these min and max points for bounties of route length 1
    "newBountyDelayRandomMin": {"minutes": 5},
    "newBountyDelayRandomMax": {"minutes": 7},

    # The amount of time a user must wait before they are allowed to submit a new github issue
    "githubIssueSubmitDelay": {"minutes": 5},

    "selectImageSizeHandling": {"minutes": 1}
}

paths = {
    # path to JSON files for database saves
    "usersDB": "saveData" + "/" + "users.json",
    "guildsDB": "saveData" + "/" + "guilds.json",
    "reactionMenusDB": "saveData" + "/" + "reactionMenus.json",

    # path to folder to save log txts to
    "logsFolder": "saveData" + "/" + "logs",

    # folders containing game objects to load into the game
    "CriminalMETAFolder": "game objects" + "/" + "criminals",
    "shipSkinMETAFolder": "game objects" + "/" + "ship skins",
    "bbShipUpgradesMETAFolder": "game objects" + "/" + "ship upgrades",
    "SolarSystemMETAFolder": "game objects" + "/" + "solar systems",
    "bbCommodityMETAFolder": "game objects" + "/" + "items" + "/" + "commodities",
    "bbModuleMETAFolder": "game objects" + "/" + "items" + "/" + "modules",
    "bbSecondaryMETAFolder": "game objects" + "/" + "items" + "/" + "secondaries",
    "bbShipMETAFolder": "game objects" + "/" + "items" + "/" + "ships",
    "bbWeaponMETAFolder": "game objects" + "/" + "items" + "/" + "weapons",
    "bbTurretMETAFolder": "game objects" + "/" + "items" + "/" + "turrets",
    "bbToolMETAFolder": "game objects" + "/" + "items" + "/" + "tools",
    "bbMedalsMETAFolder": "game objects" + "/" + "user profile" + "/" + "medals"
}



##### COMMANDS #####

# Message to print alongside cmd_help menus
helpIntro = "Here are my commands!"

# Maximum number of commands each cmd_help menu may contain
maxCommandsPerHelpPage = 5

# List of module names from the commands package to import
# includedCommandModules = ("usr_misc",
#                           "admn_misc",
#                           "dev_misc")

includedCommandModules = (  "usr_misc", "usr_homeguilds", "usr_gof2-info", "usr_bounties", "usr_loadout", "usr_economy",
                            "usr_kaamo", "usr_loma", "usr_github",
                            "admn_channels", "admn_misc",
                            "dev_misc", "dev_channels", "dev_bounties", "dev_items", "dev_skins", "dev_loma", "dev_kaamo",
                                "dev_medals", "dev_github")

# Default prefix for commands
defaultCommandPrefix = "$"



##### REACTION MENUS #####

# Text to edit into expired menu messages
expiredMenuMsg = "😴 This role menu has now expired."
# Length of the bars in poll results bar charts
pollMenuResultsBarLength = 10
# Max number of role menus a guild may own
maxRoleMenusPerGuild = 10
# Amount of time to allow for response to the cmd_use confirmation menu
toolUseConfirmTimeoutSeconds = 60
# Amount of time to allow for response to the cmd_transfer confirmation menu
homeGuildTransferConfirmTimeoutSeconds = 60
# Amount of time to allow for response to the cmd_prestige confirmation menu
prestigeConfirmTimeoutSeconds = 60



##### SCHEDULING #####

# Use "fixed" to check for task expiry every timedTaskLatenessThresholdSeconds (polling-based scheduler)
# Use "dynamic" to check for task expiry exactly at the time of task expiry (interrupts-based scheduler)
timedTaskCheckingType = "dynamic"
# Number of seconds by with the expiry of a timedtask may acceptably be late.
# Regardless of timedTaskCheckingType, this is used for the termination signal checking period.
timedTaskLatenessThresholdSeconds = 10

# Whether or not to check for updates to BASED
BASED_checkForUpdates = True



##### ADMINISTRATION #####

# discord user IDs of developers - will be granted developer command permissions
developers = [188618589102669826, 448491245296418817]

# Names of user access levels to be used in help menus.
# Also determines the number of access levels available, e.g when registering commands
userAccessLevels = ["user", "mod", "admin", "dev"]

# titles to give each type of user when reporting error messages etc
accessLevelTitles = ["pilot", "captain", "commander", "officer"]



##### USERS #####

userAlertsIDsDefaults = {   "shop_refresh": False,

                            "duels_challenge_incoming_new": True,
                            "duels_challenge_incoming_cancel": False,

                            "system_updates_major": False,
                            "system_updates_minor": False,
                            "system_misc": False}

homeGuildTransferCooldown = {"weeks": 1}



##### GAME MATHS #####

# Number of decimal places to calculate itemTLSpawnChanceForShopTL values to
itemSpawnRateResDP = 3

# The range of valid tech levels a shop may spawn at
minTechLevel = 1
maxTechLevel = 10

# Names of divisions
bountyDivisionNames = ["bronze", "silver", "gold"]

# Tech-level boundaries, for players and bounties, for each division, in the same order as bountyDivisionNames
bountyDivisionLevels = [(0, 3), (4, 7), (8, 10)]


# Price ranges by which ships should be ranked into tech levels. 0th index = tech level 1
shipMaxPriceTechLevels = [50000, 100000, 200000, 500000, 1000000, 2000000, 5000000, 7000000, 7500000, 999999999]

# Amount of xp a user must have to reach a bounty hunter level. xp required for level 1 = bountyXPLevelBoundaries[1]
# This is a measurement of the old algorithm based approach
#bountyXPLevelBoundaries = [-1, 0, 1500, 3500, 8000, 15000, 28000, 51000, 90000, 165000, 300000]
# This is the new one based on observed criminal values
bountyXPLevelBoundaries = [-1, 0, 1050, 2000, 3500, 10000, 18000, 61000, 71000, 90000, 1000000]



##### USER LEVELING #####


# Apply a multiplier to all rewards gained from a bounty. bounty hunter xp is thus a measure of
# total earnings from bounty hunting.
bountyRewardToXPGainMult = 0.1

# The image to display behind the XP bar during cmd_stats
userProfileBackground = "xp-bar-background.jpg"

# The image to fill the XP bar with during cmd_stats, for users of each division
xpBarFill = {list(bountyDivisions.keys())[0]: "xp-bar-fill.jpg",
            list(bountyDivisions.keys())[1]: "xp-bar-fill.jpg",
            list(bountyDivisions.keys())[2]: "xp-bar-fill.jpg"}

# The colour that appears behind the xp bar, for the unfilled region
xpBarSilhouetteColour = (0, 0, 0, 110)

# The width of the XP bar
xpBarWidth = 350
# The height of the XP bar
xpBarHeight = 20

# Colour of the outline for the xp bar
xpBarOutlineColour = (255, 255, 255, 200)
# Width of the xp bar outline, in pixels
xpBarOutlineWidth = 1

# The width of rendered user profile images (currently only includes bounty hunter XP info)
userProfileImgWidth = 350
# The height of rendered user profile images (currently only includes bounty hunter XP info)
userProfileImgHeight = 35

# Name of the user profile background image to display by default
# defaultUserProfileBackground = "aperture"

userProfileFont = "user-profile-font.ttf"
userProfileFontSize = 16
userProfileLevelColour = (255, 255, 255)
userProfileDivisionColour = (255, 255, 255)
userProfileXPColour = (255, 255, 255)
userProfileNextXPColour = (255, 255, 255)

# Percentage amount of padding to add around the edge of the user profile image
userProfileEdgePaddingX = 0.05
userProfileEdgePaddingY = 0.1



##### DUELS #####

# The amount to vary ship stats (+-) by before executing a duel
duelVariancePercent = 0.05

# Max number of entries that can be printed for a duel log
duelLogMaxLength = 10

# Percentage probability of a user envoking a cloak module in a given timeStep, should they have one equipped
duelCloakChance = 20

# Background images to display behind duel results. Images are selected at random. Give [] to disable
duelResultsBackgrounds = []
# Image to display between the background and content. Give "" to disable
duelResultsUnderlay = ""
# Image to display on top of all other graphics. Give "" to disable
duelResultsOverlay = ""
duelResultsRightWinner = ""
duelResultsLeftWinner = ""
duelResultsDraw = ""
# Dimensions of the duel results image
duelResultsImageDims = (500, 300)

# Width (and height) of player profile images
duelResultsPlayerWidth = 144
# Coordinates of the top-left corner of the player 1 profile image
duelResultsP1Pos = (54, 54)
# Coordinates of the top-left corner of the player 2 profile image
duelResultsP2Pos = (304, 54)

# Font to use for duel statistics, e.g time to kill
duelResultsFont = "duel-results-font.ttf"
duelResultsNameFontSize = 16
duelResultsStatsFontSize = 12
duelResultsNameFontColour = "white"
duelResultsStatsFontColour = "white"
duelResultsMaxNameWidth = 10
duelResultsMaxStatsWidth = 10
duelResultsTextLinePadding = 5
# Where to place player 1's duel statistics
duelResultsP1StatsPos = (82, 211)
# Where to place player 2's duel statistics
duelResultsP2StatsPos = (332, 211)
# Where to place player 1's ship
duelResultsP1ShipPos = (19, 211)
# Where to place player 2's ship
duelResultsP2ShipPos = (269, 211)
duelResultsShipDims = (53, 53)
duelResultsShadowOffset = (-4, 3)
duelResultsShadowOpacity = 0.7
duelResultsBlurIterations = 1



##### SHOPS #####

# The number of ranks to use when randomly picking shop stock
numShipRanks = 10
numWeaponRanks = 10
numModuleRanks = 7
numTurretRanks = 3

# The default number of items shops should generate every timeouts.shopRefresh
shopDefaultShipsNum = 5
shopDefaultWeaponsNum = 5
shopDefaultModulesNum = 5
shopDefaultTurretsNum = 2
shopDefaultToolsNum = 0

# bbTurret is the only item that has a probability not to be spawned.
# This metric indicates the percentage chance of turrets being stocked on a given refresh
turretSpawnProbability = 45

# The number of items users may store in their Kaamo Club.
kaamoMaxCapacity = 70



##### BOUNTIES #####

# Maximum number of bounties that may simultaneously be available per division
maxBountiesPerDivision = 5

# can be "fixed" or "random"
newBountyDelayType = "random-routeScale"

### Fixed delay config
# only spawn bounties at this time of day.
newBountyFixedDailyTime = {"hours": 18, "minutes": 40, "seconds": 0}

# time to wait inbetween spawning bounties
# when using fixed-routeScale generation, use this for bounties of route length 1
newBountyFixedDelta = {"days": 0, "hours": 0, "minutes": 1, "seconds": 0}

### random delay config

### routeScale config
newBountyDelayRouteScaleCoefficient = 1
fallbackRouteScale = 5

# Whether or not to log th calculation of delays between new bounty generation
logNewBountyDelays = True

# The number of credits to award for each bPoint (each system in a criminal route)
bPointsToCreditsRatio = 1000

# number of bounties ahead of a checked system in a route to report a recent criminal spotting (+1)
closeBountyThreshold = 4

# The percentage of a criminal's ship value to award to the winner
shipValueRewardPercentage = 0.01

# The probability of a criminal equipping a turret or primary weapon that deals zero damage (e.g plasma collectors)
criminalEquipDamagelessWeaponChance = 20

# The maximum number of levels a criminal's gear may be above their difficulty rating
criminalMaxGearUpgrade = 1

level0CrimLoadout = {"name": "Betty", "builtIn":True,
                    "weapons":[{"name": "Nirai Impulse EX 1", "builtIn": True}],
                    "modules":[{"name": "Telta Quickscan", "builtIn": True}, {"name": "ZMI Optistore", "builtIn": True},
                                {"name": "IMT Extract 2.7", "builtIn": True}]}

# The multiplier applied each timeouts.guildActivityDecay to each guild's player activity for each division
guildActivityDecayRate = 2/3

# The lowest rating a guild can achieve for player activitivity at a certain division
minGuildActivity = 1

# Amount to raise the guild's activity temperature by for each player contributing to a bounty
activityTempPerPlayer = 1

# The RGB colours to make by default for each bounty alert role
defaultBountyAlertRoleColours = {list(bountyDivisions.keys())[0]: (89, 39, 12),
                                list(bountyDivisions.keys())[1]: (157, 94, 11),
                                list(bountyDivisions.keys())[2]: (255, 174, 8)}



##### SKINS #####

# Discord server containing the skinRendersChannel
mediaServer = 699744305274945650
# Channel to send ship skin renders to and link from
skinRendersChannel = 770036783026667540
# Channel to send showme-prompted ship skin renders to and link from
showmeSkinRendersChannel = 771368555019108352
# Resolution of skin render icons
skinRenderIconResolution = [600, 600]
skinRenderIconSamples = 8
# Resolution of skin render emojis (currently unused)
skinRenderEmojiResolution = [400, 400]
skinRenderEmojiSamples = 8
# Resolution of skin renders from cmd_showme_ship calls
skinRenderShowmeResolution = [352, 240]
skinRenderShowmeSamples = 4
# Resolution of skin renders from admin_cmd_showmeHD calls
skinRenderShowmeHDResolution = [1920, 1080]
skinRenderShowmeHDSamples = 4

# Default graphics to use for ship skin application tool items
defaultShipSkinToolIcon = "https://cdn.discordapp.com/attachments/700683544103747594/723472334362771536/documents.png"

# The maximum number of rendering threads that may be dispatched simultaneously
maxConcurrentRenders = 1

defaultCrateIcon = "https://cdn.discordapp.com/attachments/700683544103747594/723472359113359410/secure_container.png" 

# Percentage tolerance to give when deciding whether an image is of the correct aspect ratio
aspectRatioTolerance = 0.1



##### ITEMS #####

# max number of characters accepted by nameShip
maxShipNickLength = 30

# max number of characters accepted by nameShip, when called by a developer
maxDevShipNickLength = 100

# The maximum number of items that will be displayed per page of a user's hangar, when all item types are requested
maxItemsPerHangarPageAll = 3
# The maximum number of items that will be displayed per page of a user's hangar, when a single item type is requested
maxItemsPerHangarPageIndividual = 10

# Names to be used when checking input to cmd_hangar and BasedUser.numInventoryPages
validItemNames = ["ship", "weapon", "module", "turret", "all", "tool"]

# the max number of each module type that can be equipped on a ship.
maxModuleTypeEquips = {     "ArmourModule": 1,
                            "BoosterModule": 1,
                            "CabinModule": -1,
                            "CloakModule": 1,
                            "CompressorModule": -1,
                            "EmergencySystemModule": 1,
                            "GammaShieldModule": 1,
                            "JumpDriveModule": 0,
                            "MiningDrillModule": 1,
                            "PrimaryWeaponModModule": 1,
                            "RepairBeamModule": 1,
                            "RepairBotModule": 1,
                            "ScannerModule": 1,
                            "ShieldInjectorModule": 1,
                            "ShieldModule": 1,
                            "SignatureModule": 1,
                            "SpectralFilterModule": 1,
                            "ThrusterModule": 1,
                            "TimeExtenderModule": 1,
                            "TractorBeamModule": 1,
                            "TransfusionBeamModule": 1}

# valid types of crateItem that are in the game. Each will be associated with a zero-indexed (crateNum) list of crate objects
crateTypes = ("levelUp", "special")



##### USER PROFILE #####

# Server in which to save medal emojis
emojisServer = 699744305274945650
# Channel in which to send medal icon images
medalIconsChannel = 859747151746826310



##### MISC #####

# Exactly one of botToken or botToken_envVarName must be given.
# botToken contains a string of your bot token
# botToken_envVarName contains the name of an environment variable to get your bot token from
botToken = ""
botToken_envVarName = ""

# The number of times to retry API calls when HTTP exceptions are thrown
httpErrRetries = 3

# The number of seconds to wait between API call retries upon HTTP exception catching
httpErrRetryDelaySeconds = 1

# The categories to sort and save logs into
loggingCategories = [   "usersDB", "guildsDB", "bountiesDB", "shop", "escapedBounties", "bountyConfig", "duels", "hangar",
                        "bountyBoards", "newBounties", "reactionMenus", "userAlerts"]

# The maximum recursion depth of directory-walking when loading gameObjects from their JSON representation
gameObjectCfgMaxRecursion = 6

# github account access token to be used for submitting issues
githubAccessToken = ""

# github repo to submit issues into
githubIssuesRepo = ""

# a translation from github label names to user-facing label names
githubLabelNames = {"enhancement": "feature",
                    "i showed u my issue pls respond": "new issue"}

githubIssueTemplates = ["bug_report", "feature_request", "new-item-alias"]

# Top n results will be showed in github search
githubIssueSearchNumResults = 9
