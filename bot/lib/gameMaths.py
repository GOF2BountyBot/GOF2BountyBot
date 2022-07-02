from ..cfg import cfg
import math
import random
from typing import List, Union


def makeMatrix(xDim: int, yDim: int) -> List[List[float]]:
    """Create an (xDim, yDim) matrix of zeros.

    :param int xDim: The number of columns to create
    :param int yDim: The number of rows to create
    :return: An (xDim, yDim) matrix of zeros.
    :rtype: List[List[int]]
    """
    return [[0] * xDim for _ in range(yDim)]


# cfg.itemSpawnRateResDP in terms of decimal digits, used 
itemSpawnRateResDigits = int(math.pow(10, cfg.itemSpawnRateResDP))

# Valid ranges of item tech levels
numTechLevels = cfg.maxTechLevel - cfg.minTechLevel + 1
techLevelRange = range(cfg.minTechLevel, cfg.maxTechLevel + 1)

# The probability of a shop spawning with a given tech level. Tech level = index + 1
cumulativeShopTLChance: List[float] = [0] * numTechLevels

# CUMULATIVE probabilities of items of a given tech level spawning in a shop of a given tech level
# Outer dimension is shop tech level
# Inner dimension is item tech level
itemTLSpawnChanceForShopTL = makeMatrix(numTechLevels, numTechLevels)
cumulativeItemTLSpawnChanceForShopTL = makeMatrix(numTechLevels, numTechLevels)

# Parameters for itemTLSpawnChanceForShopTL values, using quadratic function: https://www.desmos.com/calculator/n2xfxf8taj
# Original u function by Novahkiin22: https://www.desmos.com/calculator/tnldodey5u
# Original function by Novahkiin22: https://www.desmos.com/calculator/nrshikfmxc
tl_s = 7
tl_o = 2.3


def truncItemSpawnResolution(num: float) -> float:
    """Truncate the passed float to cfg.itemSpawnRateResDP decimal places.

    :param float num: Float number to truncate
    :return: num, truncated to cfg.itemSpawnRateResDP decimal places
    :rtype: float
    """
    return math.trunc(num * itemSpawnRateResDigits) / itemSpawnRateResDigits


def normalizeArray(nums: List[Union[int, float]]) -> List[Union[int, float]]:
    """Rescale the array elements to the range [0, 1], in place.

    :param nums: Array of numbers to normalize
    :type nums: List[Union[int, float]
    :return: nums, with all elements rescaled into the range [0, 1]
    :rtype: List[Union[int, float]
    """
    numSum = sum(nums)
    return [truncItemSpawnResolution(i / numSum) for i in nums]


def makeCumulative(nums: List[Union[int, float]]) -> List[Union[int, float]]:
    """Add the items in the array in series, from left to right, to create a cumulative scale.
    0-valued elements are ignored in rescaling.
    This operation is performed in place.

    :param nums: Array of numbers to accumulate.
    :type nums: List[Union[int, float]
    :return: nums, with each element added to the next iteratively.
    :rtype: List[Union[int, float]
    """
    for i in range(1,len(nums)):
        nums[i] = truncItemSpawnResolution(nums[i] + nums[i-1])
    return nums


def pickRandomShopTL() -> int:
    """Pick a random shop techlevel, with probabilities calculated previously in gameMaths.

    :return: An integer between 1 and 10 representing a shop tech level
    :rtype: int
    """
    tlChance = random.randint(1, itemSpawnRateResDigits) / itemSpawnRateResDigits
    try:
        return next(i + 1 for i, v in enumerate(cumulativeShopTLChance) if v >= tlChance)
    except StopIteration:
        return cfg.maxTechLevel


def tl_u(x: int, t: int) -> float:
    """mathematical function used when calculating item spawn probabilities.

    :param int x: int representing the item's tech level
    :param int t: int representing the owning shop's tech level
    :return: A partial probability for use in probability generation
    :rtype: float
    """
    return max(0, truncItemSpawnResolution(1 - math.pow((x - t) / 1.4, 2)))


def pickRandomItemTL(shopTL: int) -> int:
    """Pick a random item techlevel, with probabilities calculated previously in gameMaths.

    :param int shopTL: int representing the tech level of the shop owning the item
    :return: An integer between 1 and 10 representing a item tech level
    :rtype: int
    """
    tlChance = random.randint(1, itemSpawnRateResDigits) / itemSpawnRateResDigits
    try:
        return next(i + 1 for i, v in enumerate(cumulativeItemTLSpawnChanceForShopTL[shopTL - 1]) if v >= tlChance)
    except StopIteration:
        return cfg.maxTechLevel


def possibleItemTLs(shopTL: int) -> List[int]:
    """Get a list of all item tech levels that can spawn for a given shop tech level
    
    :param int shopTL: The level of the shop whose possible item levels to look up
    :return: A list of item tech levels with non-zero spawn chances for shops of level shopTL
    :rtype: List[int]
    """
    return [i for i in techLevelRange if itemTLSpawnChanceForShopTL[shopTL - 1][i - 1] != 0]


def shipSkinValueForTL(averageTL: int) -> int:
    """Calculate how skins are valued with respect to their average compatible ship techlevel.

    :param int averageTL: The average techLevel of the ships that this skin is compatible with
    :return: The value to assign to the ship skin
    :rtype: int
    """
    # return averageTL * 10000
    return 0


# Calculate spawn chance for each shop TL
for shopTL in techLevelRange:
    cumulativeShopTLChance[shopTL - 1] = truncItemSpawnResolution(1 - math.exp((shopTL - 10.5) / 5))

cumulativeShopTLChance = normalizeArray(cumulativeShopTLChance)
# Sum probabilities to give cumulative scale
makeCumulative(cumulativeShopTLChance)

# Loop through shop TLs
for shopTL in techLevelRange:
    # Calculate spawn chance for each item TL in this shop TL
    tlSpawnRates = normalizeArray([tl_u(itemTL, shopTL) for itemTL in techLevelRange])

    # Save non-cumulative probabilities
    itemTLSpawnChanceForShopTL[shopTL - 1] = [i for i in tlSpawnRates]

    # Sum probabilities to give cumulative scale
    cumulativeItemTLSpawnChanceForShopTL[shopTL - 1] = makeCumulative(tlSpawnRates)

for shopTL in techLevelRange:
    print(f"\t• shop TL {shopTL}: itemTL", end="")
    for itemTL in possibleItemTLs(shopTL):
        print(f" {itemTL}={truncItemSpawnResolution(itemTLSpawnChanceForShopTL[shopTL - 1][itemTL - 1] * 100)}", end="% ")
    print()



##### USER LEVELING #####

BHLa = 4
BHLb = 2300000
BHLc = 1675
BHLd = 13.55


"NEW MANUAL BOUNDARIES BASED METHOD"
def bountyHuntingXPForLevel(level):
    return cfg.bountyXPLevelBoundaries[level]
    
def calculateUserBountyHuntingLevel(xp):
    try:
        return next(i-1 for i, v in enumerate(cfg.bountyXPLevelBoundaries) if v > xp)
    except StopIteration:
        return cfg.maxTechLevel


""" OLD ALGORITHM BASED METHOD

# Inverse of calculateUserBountyHuntingLevel
def bountyHuntingXPForLevel(level):
    return max(0, int(BHLb * math.pow(10, (level - BHLd) / BHLa) - BHLc))


# https://www.desmos.com/calculator/ljkio5xyfz
def calculateUserBountyHuntingLevel(xp):
    if xp <= 0:
        return 1
    return min(cfg.maxTechLevel, max(1, int(BHLa * math.log10((xp + BHLc)/BHLb) + BHLd)))
"""

# def bountyHuntingXPForLevel(level):
#     return int(1000 * math.exp((level - 1)/3.74) - 1000)


# def calculateUserBountyHuntingLevel(xp):
#     return int(1 + 3.74 * math.log((xp/1000)+1))



# def bountyHuntingXPForLevel(level):
#     return int((level + 30001)/4)


# def calculateUserBountyHuntingLevel(xp):
#     return 4 * xp - 30001


def rewardPerSysCheck(techLevel: int, loadoutValue: int) -> int:
    """The number of credits to award for each system check of a bounty
    This implmentation is guaranteed to be at least cfg.classic_creditsPerCheck

    :param int techLevel: The level of the bounty
    :param int loadoutValue: The total value of the criminal's loadout
    :return: The number of credits to award participating players for each system they check in the bounty's route
    :rtype: int
    """
    return max(cfg.classic_creditsPerCheck,
                int((loadoutValue * (1.3 if techLevel == 1 else 1)) / (2*(techLevel+(1 if techLevel == 1 else 2)) * 10)))


def crateValueForTL(TL: int) -> int:
    """Calculate how crate are valued with respect to their techlevel.

    :param int averageTL: The techLevel of the crate
    :return: The value to assign to the crate
    :rtype: int
    """
    # TL * 5000
    return 0


# The probability of a criminal spawning with a given tech level. Tech level = index
cumulativeCriminalTLChance: List[float] = [0] * (numTechLevels + 1)

# Calculate spawn chance for each criminal TL
for criminalTL in range(cfg.minTechLevel - 1, cfg.maxTechLevel + 1):
    cumulativeCriminalTLChance[criminalTL] = truncItemSpawnResolution(1 - math.exp((criminalTL - 10.5) / 5))

cumulativeCriminalTLChance = normalizeArray(cumulativeCriminalTLChance)
makeCumulative(cumulativeCriminalTLChance)

print("[gameMaths] Criminal difficulty spawn rates generated:")
for criminalTL in range(cfg.minTechLevel - 1, cfg.maxTechLevel + 1):
    print("\t• level " + str(criminalTL + 1) + ": " \
                + str(truncItemSpawnResolution(cumulativeCriminalTLChance[criminalTL] * 100)),
            end="%\n")


def pickRandomCriminalTL() -> int:
    """Pick a random criminal difficulty level based on the spawn rates defined in cumulativeCriminalTLChance

    :return: An integer representing a difficulty level to spawn a criminal with
    :rtype: int
    """
    tlChance = random.randint(1, itemSpawnRateResDigits) / itemSpawnRateResDigits
    for criminalTL in range(len(cumulativeCriminalTLChance)):
        if cumulativeCriminalTLChance[criminalTL] >= tlChance:
            return criminalTL
    return cfg.maxTechLevel


itemRaritiesDistributionReverseCumulative = makeCumulative(list(cfg.itemRaritiesDistribution[::-1]))


def pickRandomItemRarityLevel() -> int:
    """Pick a random item rarity level, according to the weightings in cfg.itemRaritiesDistribution.

    :return: An item rarity level. I.e, an index of cfg.itemRarities
    :rtype: int
    """
    distributionScale = sum(cfg.itemRaritiesDistribution)
    rarityChance = random.randint(1, distributionScale)
    minRarity = len(cfg.itemRarities) - 1
    try:
        # Subtracting from minRarity because I'm iterating over the reverse of the rarities distribution,
        # so indices will be reversed as well.
        return next(minRarity - level \
                    for level, weight in enumerate(itemRaritiesDistributionReverseCumulative) \
                    if weight >= rarityChance)
    except StopIteration:
        return 0
