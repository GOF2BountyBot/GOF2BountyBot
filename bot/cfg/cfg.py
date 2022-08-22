from ..lib.emojis import UninitializedBasedEmoji, BasedEmoji
from ..lib.discordUtil import SerializableDiscordObject
from .schema import BasicAccessLevelNames, EmojisConfig, SerializableTimedelta, TimeoutsConfig, PathsConfig, ConcatenatableSerializablePath
from typing import Dict, List, Tuple, cast

# All emojis used by the bot
defaultEmojis = EmojisConfig(
    # The emoji that will be used when attempting to display an emoji which the bot cannot access. Make sure this is accessible.
    unrecognisedEmoji = cast(BasedEmoji, UninitializedBasedEmoji("⁉")),
    longProcess = cast(BasedEmoji, UninitializedBasedEmoji("⏳")),
    # When a user message prompts a DM to be sent, this emoji will be added to the message reactions.
    dmSent = cast(BasedEmoji, UninitializedBasedEmoji("📬")),
    cancel = cast(BasedEmoji, UninitializedBasedEmoji("🇽")),
    submit = cast(BasedEmoji, UninitializedBasedEmoji("✅")),
    spiral = cast(BasedEmoji, UninitializedBasedEmoji("🌀")),
    error = cast(BasedEmoji, UninitializedBasedEmoji("❓")),
    accept = cast(BasedEmoji, UninitializedBasedEmoji("👍")),
    reject = cast(BasedEmoji, UninitializedBasedEmoji("👎")),
    next = cast(BasedEmoji, UninitializedBasedEmoji('⏩')),
    previous = cast(BasedEmoji, UninitializedBasedEmoji('⏪')),
    numbers = cast(List[BasedEmoji], [UninitializedBasedEmoji("0️⃣"), UninitializedBasedEmoji("1️⃣"), UninitializedBasedEmoji("2️⃣"),
                UninitializedBasedEmoji("3️⃣"), UninitializedBasedEmoji("4️⃣"), UninitializedBasedEmoji("5️⃣"),
                UninitializedBasedEmoji("6️⃣"), UninitializedBasedEmoji("7️⃣"), UninitializedBasedEmoji("8️⃣"),
                UninitializedBasedEmoji("9️⃣"), UninitializedBasedEmoji("🔟")]),

    # The default emojis to list in a reaction menu
    menuOptions = cast(List[BasedEmoji], [UninitializedBasedEmoji("0️⃣"), UninitializedBasedEmoji("1️⃣"), UninitializedBasedEmoji("2️⃣"),
                    UninitializedBasedEmoji("3️⃣"), UninitializedBasedEmoji("4️⃣"), UninitializedBasedEmoji("5️⃣"),
                    UninitializedBasedEmoji("6️⃣"), UninitializedBasedEmoji("7️⃣"), UninitializedBasedEmoji("8️⃣"),
                    UninitializedBasedEmoji("9️⃣"), UninitializedBasedEmoji("🔟")]),

    # Default emoji to assign to shipSkinTool items
    shipSkinTool = cast(BasedEmoji, UninitializedBasedEmoji("🎨")),

    # Default emoji to assign to bbCrates containing shipSkinTools
    skinCrate = cast(BasedEmoji, UninitializedBasedEmoji("🧰")),

    # Default emoji to assign to all other crates
    defaultCrate = cast(BasedEmoji, UninitializedBasedEmoji("📦")),
    
    # Emoji sent with new bounty listings
    newBounty = cast(BasedEmoji, UninitializedBasedEmoji("⛓")),

    bountyRespawn = cast(BasedEmoji, UninitializedBasedEmoji("⛓")),

    newIssue = cast(BasedEmoji, UninitializedBasedEmoji("📥")),
    issueClosed = cast(BasedEmoji, UninitializedBasedEmoji("✅")),
    bug = cast(BasedEmoji, UninitializedBasedEmoji("🕷")),
    feature = cast(BasedEmoji, UninitializedBasedEmoji("✨")),
    gameBalance = cast(BasedEmoji, UninitializedBasedEmoji("⚖")),
    optimisation = cast(BasedEmoji, UninitializedBasedEmoji("🚀")),

    cropImage = cast(BasedEmoji, UninitializedBasedEmoji("✂")),
    stretchImage = cast(BasedEmoji, UninitializedBasedEmoji("↔")),

    classicMode = cast(BasedEmoji, UninitializedBasedEmoji("💽")),

    money = cast(BasedEmoji, UninitializedBasedEmoji("💰")),

    rarity_common = cast(BasedEmoji, UninitializedBasedEmoji("⚫")),
    rarity_uncommon = cast(BasedEmoji, UninitializedBasedEmoji("🟤")),
    rarity_rare = cast(BasedEmoji, UninitializedBasedEmoji("🟠")),
    rarity_epic = cast(BasedEmoji, UninitializedBasedEmoji("🔴")),

    divUpUnlocked = cast(BasedEmoji, UninitializedBasedEmoji("🔼")),
    prestigeUnlocked = cast(BasedEmoji, UninitializedBasedEmoji("⏫"))
)

timeouts = TimeoutsConfig(
    menuInteractionDefault = SerializableTimedelta(minutes=2),
    
    helpMenu = SerializableTimedelta(minutes=3),
    BASED_updateCheckFrequency = SerializableTimedelta(days=1),
    # The time to wait inbetween database autosaves.
    dataSaveFrequency = SerializableTimedelta(hours=1),

    # Amount of time before a duel request expires
    duelRequest = SerializableTimedelta(days=1),

    # Amount of time to wait between refreshing stock of all shops
    shopRefresh = SerializableTimedelta(hours=6),

    # time to put users on cooldown between using !bb check
    checkCooldown = SerializableTimedelta(minutes=3),

    # Default amount of time reaction menus should be active for
    roleMenuExpiry = SerializableTimedelta(days=1),
    duelChallengeMenuExpiry = SerializableTimedelta(hours=2),
    pollMenuExpiry = SerializableTimedelta(minutes=5),

    # The time between decrements to the guild activity temperatures of each tech level
    guildActivityDecay = SerializableTimedelta(hours=1),

    # when using random bounty delay generation, use these min and max points
    # when using random-routeScale generation, use these min and max points for bounties of route length 1
    newBountyDelayRandomMin = SerializableTimedelta(minutes=5),
    newBountyDelayRandomMax = SerializableTimedelta(minutes=7),

    # The amount of time a user must wait before they are allowed to submit a new github issue
    githubIssueSubmitDelay = SerializableTimedelta(minutes=5),

    # Time allowed to select 'crop' or 'stretch' for incorrectly shaped autoskin input images
    selectImageSizeHandling = SerializableTimedelta(minutes=1),

    toggleClassicMode = SerializableTimedelta(minutes=2),

    # The termination signal checking period.
    shutdownCheckPeriod = SerializableTimedelta(seconds=10),

    # The cooldown between uses of the transfer command.
    homeGuildTransferCooldown = SerializableTimedelta(weeks=1),

    # time to wait inbetween spawning bounties, when newBountyDelayType starts with 'fixed'
    # when using fixed-routeScale generation, use this for bounties of route length 1
    newBountyFixedDelta = SerializableTimedelta(minutes=1)
)

paths = PathsConfig(
    # path to JSON files for database saves
    usersDB = ConcatenatableSerializablePath("saveData", "users.json"),
    guildsDB = ConcatenatableSerializablePath("saveData", "guilds.json"),
    reactionMenusDB = ConcatenatableSerializablePath("saveData", "reactionMenus.json"),

    # path to folder to save log txts to
    logsFolder = ConcatenatableSerializablePath("saveData", "logs"),

    # folders containing game objects to load into the game
    CriminalMETAFolder = ConcatenatableSerializablePath("game objects", "criminals"),
    shipSkinMETAFolder = ConcatenatableSerializablePath("game objects", "ship skins"),
    bbShipUpgradesMETAFolder = ConcatenatableSerializablePath("game objects", "ship upgrades"),
    SolarSystemMETAFolder = ConcatenatableSerializablePath("game objects", "solar systems"),
    bbCommodityMETAFolder = ConcatenatableSerializablePath("game objects", "items", "commodities"),
    bbModuleMETAFolder = ConcatenatableSerializablePath("game objects", "items", "modules"),
    bbSecondaryMETAFolder = ConcatenatableSerializablePath("game objects", "items", "secondaries"),
    bbShipMETAFolder = ConcatenatableSerializablePath("game objects", "items", "ships"),
    bbWeaponMETAFolder = ConcatenatableSerializablePath("game objects", "items", "weapons"),
    bbTurretMETAFolder = ConcatenatableSerializablePath("game objects", "items", "turrets"),
    bbToolMETAFolder = ConcatenatableSerializablePath("game objects", "items", "tools"),
    bbMedalsMETAFolder = ConcatenatableSerializablePath("game objects", "user profile", "medals"),
    
    # Temporary folder for autoskin renders
    tempRenders = ConcatenatableSerializablePath("rendering-temp"),

    # snowball images to use in ThrowSnowballTool
    snowballImages = ConcatenatableSerializablePath("snowballs"),

    # map image used in bounty route renders
    mapImage = ConcatenatableSerializablePath("starmap.png"),

    # The image to display behind the XP bar during cmd_stats
    userProfileBackground = ConcatenatableSerializablePath("xp-bar-background.jpg"),

    # Font to use for user profiles in the stats command.
    userProfileFont = ConcatenatableSerializablePath("user-profile-font.ttf"),

    # Background images to display behind duel results. Images are selected at random. Give [] to disable
    duelResultsBackgrounds = [],
    # Image to display between the background and content. Give "" to disable
    duelResultsUnderlay = ConcatenatableSerializablePath(),
    # Image to display on top of all other graphics. Give "" to disable
    duelResultsOverlay = ConcatenatableSerializablePath(),
    duelResultsRightWinner = ConcatenatableSerializablePath(),
    duelResultsLeftWinner = ConcatenatableSerializablePath(),
    duelResultsDraw = ConcatenatableSerializablePath(),

    # Font to use for duel statistics, e.g time to kill
    duelResultsFont = ConcatenatableSerializablePath("duel-results-font.ttf")
)


##### COMMANDS #####

basicAccessLevels = BasicAccessLevelNames(
    user = "user",
    serverAdmin = "admin",
    developer = "developer"
)

# Names of user access levels to be used in help menus.
# Also determines the number of access levels available, e.g when registering commands
userAccessLevels = [basicAccessLevels.user, "mod", basicAccessLevels.serverAdmin, basicAccessLevels.developer]

# Message to print alongside cmd_help menus
helpIntro = "Give a command name in `/help` for more detail."

# Name of the help section for un-categorized commands
defaultHelpSection = "Miscellaneous"

# Maximum number of commands each cmd_help menu may contain
maxCommandsPerHelpPage = 5

# List of module names from the commands package to import
includedCommandModules: List[str] = []

def cogPath(cogName: str, basePackage: str = "bot.cogs") -> str:
    return ".".join((basePackage, cogName))

includedCogs = (
    cogPath("CommonStaticComponentsCog", basePackage="bot.cogs.util"),
    cogPath("EmbedEditorCog", basePackage="bot.cogs.util"),
    cogPath("GithubUtilCog", basePackage="bot.cogs.util"),
    cogPath("GuildsUtilCog", basePackage="bot.cogs.util"),
    cogPath("UsersUtilCog", basePackage="bot.cogs.util"),

    cogPath("BASEDVersionCog"),
    cogPath("HelpCog"),
    
    cogPath("DevBountiesCog"),
    cogPath("DevChannelsCog"),
    cogPath("DevEconomyCog"),
    cogPath("DevEventsCog"),
    cogPath("DevGithubCog"),
    cogPath("DevHomeGuildsCog"),
    cogPath("DevItemsCog"),
    cogPath("DevKaamoCog"),
    cogPath("DevLomaCog"),
    cogPath("DevMedalsCog"),
    cogPath("DevMiscCog"),

    cogPath("AdminChannelsCog"),
    cogPath("AdminMiscCog"),
    
    cogPath("UserMiscCog")
)

# Default prefix for commands
defaultCommandPrefix = "$"

# Text to edit into expired menu messages
expiredMenuMsg = "😴 This menu has now expired."
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

# Whether or not to check for updates to BASED
BASED_checkForUpdates = True



##### ADMINISTRATION #####

# discord user IDs of developers - will be granted developer command permissions
developers = [188618589102669826, 448491245296418817]


# titles to give each type of user when reporting error messages etc
accessLevelTitles = ["pilot", "captain", "commander", "officer"]



##### USERS #####

userAlertsIDsDefaults = {   "shop_refresh": False,

                            "duels_challenge_incoming_new": True,
                            "duels_challenge_incoming_cancel": False,

                            "system_updates_major": False,
                            "system_updates_minor": False,
                            "system_misc": False}



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

# The image to fill the XP bar with during cmd_stats, for users of each division, in the same order as bountyDivisionNames
xpBarFillsByDivision = ["xp-bar-fill.jpg", "xp-bar-fill.jpg", "xp-bar-fill.jpg"]

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

# Dimensions of the duel results image
duelResultsImageDims = (500, 300)

# Width (and height) of player profile images
duelResultsPlayerWidth = 144
# Coordinates of the top-left corner of the player 1 profile image
duelResultsP1Pos = (54, 54)
# Coordinates of the top-left corner of the player 2 profile image
duelResultsP2Pos = (304, 54)

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

### routeScale config
newBountyDelayRouteScaleCoefficient = 1
fallbackRouteScale = 5

# Whether or not to log th calculation of delays between new bounty generation
logNewBountyDelays = True

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
bountyAlertRoleColoursByDivision = [(89, 39, 12), (157, 94, 11), (255, 174, 8)]

# In bountyboard channels, show criminal loadouts as emojis
bbcShowLoadoutEmojis = True

# In bountyboard channels, show criminal total health points and dps
bbcShowHpDps = True

# In bountyboard channels, render the bounty route onto the starmap image
bbcShowRouteImage = True

# In bountyboard channels, if bbcShowRouteImage is True, this is the colour used for path lines. (R, G, B, A) tuple
bbcRouteImageLineColour = (255, 89, 89, 255)

# In bountyboard channels, if bbcShowRouteImage is True, this is the line width used for path lines
bbcRouteImageLineWidth = 3

# In bountyboard channels, if bbcShowRouteImage is True, this is radius of each dot on systems in path lines
bbcRouteImageNodeRadius = 4

# In bountyboard channels, if bbcShowRouteImage is True, this is colour of each dot on systems in path lines
bbcRouteImageNodeColour = (255, 150, 150, 255)

# In bountyboard channels, if bbcShowRouteImage is True, this radius is used to circle single-system routes
bbcRouteImageSingleSystemRadius = 20

# In bountyboard channels, if bbcShowRouteImage is True, this channel will be used to store route images
# This is needed, because Message.edit cannot introduce new attachments.
# The channel must be in `cfg.mediaServer`.
bbcRouteImageChannel = 934909288495861931



##### CLASSIC MODE #####

# The number of credits to award for each system check (corresponds to the old bPointsToCreditsRatio variable)
classic_creditsPerCheck = 1000

# Name of the division to limit classic mode users to bounties of
classic_divisionName = "bronze"



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

# The minimum number of a given item type that shops will spawn per refresh, if items are available of the correct level
# These MUST be spawnableItems - classes marked with the spawnableItem decorator.
# This feature is not currently available for ships.
minModuleTypeShopSpawns = { "ArmourModule": 1,
                            "ShieldModule": 1
                            }
minWeaponTypeShopSpawns: Dict[str, int] = {}
minTurretTypeShopSpawns: Dict[str, int] = {}

# valid types of crateItem that are in the game. Each will be associated with a zero-indexed (crateNum) list of crate objects
crateTypes = ("levelUp", "special", "christmas")

# Names of item rarities. Item rarity levels are integers that correspond to indices in this tuple.
# Must be in ascending order of rarity.
itemRarities = ("common", "uncommon", "rare", "epic")

# Probability distribution of an event occurring involving an item of a given rarity. E.g crate drop rates. Must be integers.
itemRaritiesDistribution = (45, 28, 15, 7)



##### USER PROFILE #####

# Server in which to save medal emojis
emojisServer = 699744305274945650
# Channel in which to send medal icon images
medalIconsChannel = 859747151746826310



##### MISC #####

# IDs of 'development' servers, where commands will be synced to immediately, and dev commands will be enabled.
developmentGuilds = [SerializableDiscordObject(1)]

# Exactly one of botToken or botToken_envVarName must be given.
# botToken contains a string of your bot token
# botToken_envVarName contains the name of an environment variable to get your bot token from
botToken = ""
botToken_envVarName = ""

# The number of times to retry API calls when HTTP exceptions are thrown
httpErrRetries = 3

# The number of seconds to wait between API call retries upon HTTP exception catching
httpErrRetryDelaySeconds = 1

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

moneyIcon = "https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/twitter/282/money-bag_1f4b0.png"

# The number of snowball icons that can be picked from for ThrowSnowballTool
numSnowballs = 6

leaderboardNames: Tuple[Tuple[str, ...], ...] = (
    ('balance', 'bal', 'credits', 'b'),
    ('checks', 'c'),
    ('wins', 'w'),
    ('xp',)
)

leaderboardTypeSettings: Tuple[Tuple[str, str, str, str, str], ...] = (
    ("credits", "Current Balance", "Credit", "Credits", "*Current player credits balance"),
    ("systemsChecked", "Systems Checked", "System", "Systems", f"*Total number of systems checked"),
    ("bountyWins", "Bounties Won", "Bounty", "Bounties", "*Total number of bounties won"),
    ("lifetimeBountyHuntingXP", "Lifetime Bounty Hunter XP", "xp", "xp",
        "*Total amount of bounty hunting xp earned")
)

leaderboardHelpDescriptions: Tuple[str, ...] = (
    "current credits balance",
    "systems checked",
    "bounties won",
    "lifetime bounty hunter XP"
)

def validateConfig():
    for _, basicAccessLevel in basicAccessLevels._fieldItems():
        if basicAccessLevel not in userAccessLevels:
            raise ValueError(f"basic access level '{basicAccessLevel}' is missing from userAccessLevels")
