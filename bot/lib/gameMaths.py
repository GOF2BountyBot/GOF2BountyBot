from ..cfg import cfg
import math
import random
from typing import List, Union


def makeMatrix(xDim : int, yDim : int) -> List[List[int]]:
    """Create an (xDim, yDim) matrix of zeros.

    :param int xDim: The number of columns to create
    :param int yDim: The number of rows to create
    :return: An (xDim, yDim) matrix of zeros.
    :rtype: List[List[int]]
    """
    return [[0] * xDim for _ in range(yDim)]


itemSpawnRateResDigits = math.pow(10, cfg.itemSpawnRateResDP)

numTechLevels = cfg.maxTechLevel - cfg.minTechLevel + 1
techLevelRange = range(cfg.minTechLevel, cfg.maxTechLevel + 1)

# The probability of a shop spawning with a given tech level. Tech level = index + 1
cumulativeShopTLChance = [0] * numTechLevels

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


def truncItemSpawnResolution(num : float) -> float:
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


def makeCumulative(nums : List[Union[int, float]]) -> List[Union[int, float]]:
    """Add the items in the array in series, from left to right, to create a cumulative scale.
    0-valued elements are ignored in rescaling.
    This operation is performed in place.

    :param nums: Array of numbers to accumulate.
    :type nums: List[Union[int, float]
    :return: nums, with each element added to the next iteratively.
    :rtype: List[Union[int, float]
    """
    if len(nums) > 1:
        return [nums[0]] + [truncItemSpawnResolution(nums[i] + nums[i - 1]) for i in range(1, len(nums))]
    return nums


def pickRandomShopTL() -> int:
    """Pick a random shop techlevel, with probabilities calculated previously in gameMaths.

    :return: An integer between 1 and 10 representing a shop tech level
    :rtype: int
    """
    tlChance = random.randint(1, itemSpawnRateResDigits) / itemSpawnRateResDigits
    for shopTL in range(numTechLevels):
        if cumulativeShopTLChance[shopTL] >= tlChance:
            return shopTL + 1
    return cfg.maxTechLevel


def tl_u(x : int, t : int) -> float:
    """mathematical function used when calculating item spawn probabilities.

    :param int x: int representing the item's tech level
    :param int t: int representing the owning shop's tech level
    :return: A partial probability for use in probability generation
    :rtype: float
    """
    return max(0, truncItemSpawnResolution(1 - math.pow((x - t) / 1.4, 2)))


def pickRandomItemTL(shopTL : int) -> int:
    """Pick a random item techlevel, with probabilities calculated previously in gameMaths.

    :param int shopTL: int representing the tech level of the shop owning the item
    :return: An integer between 1 and 10 representing a item tech level
    :rtype: int
    """
    tlChance = random.randint(1, itemSpawnRateResDigits) / itemSpawnRateResDigits
    for itemTL in range(len(cumulativeItemTLSpawnChanceForShopTL[shopTL - 1])):
        if cumulativeItemTLSpawnChanceForShopTL[shopTL - 1][itemTL] >= tlChance:
            return itemTL + 1
    return cfg.maxTechLevel


def shipSkinValueForTL(averageTL : int) -> int:
    """Calculate how skins are valued with respect to their average compatible ship techlevel.

    :param int averageTL: The average techLevel of the ships that this skin is compatible with
    :return: The value to assign to the ship skin
    :rtype: int
    """
    return averageTL * 10000


# Calculate spawn chance for each shop TL
for shopTL in techLevelRange:
    cumulativeShopTLChance[shopTL - 1] = truncItemSpawnResolution(1 - math.exp((shopTL - 10.5) / 5))

cumulativeShopTLChance = normalizeArray(cumulativeShopTLChance)
# Sum probabilities to give cumulative scale
cumulativeShopTLChance = makeCumulative(cumulativeShopTLChance)

# Loop through shop TLs
for shopTL in techLevelRange:
    # Calculate spawn chance for each item TL in this shop TL
    tlSpawnRates = normalizeArray([tl_u(itemTL, shopTL) for itemTL in techLevelRange])

    # Save non-cumulative probabilities
    itemTLSpawnChanceForShopTL[shopTL - 1] = [i for i in tlSpawnRates]

    # Sum probabilities to give cumulative scale
    cumulativeItemTLSpawnChanceForShopTL[shopTL - 1] = makeCumulative(tlSpawnRates)

print("[gameMaths] Item rarities generated:")
for shopTL in range(len(itemTLSpawnChanceForShopTL)):
    print("\t• shop TL" + str(shopTL + 1) + ": itemTL", end="")
    for itemTL in range(len((itemTLSpawnChanceForShopTL[shopTL]))):
        if itemTLSpawnChanceForShopTL[shopTL][itemTL] != 0:
            print(" " + str(itemTL + 1) + "=" \
                        + str(truncItemSpawnResolution(itemTLSpawnChanceForShopTL[shopTL][itemTL] * 100)),
                    end="% ")
    print()
