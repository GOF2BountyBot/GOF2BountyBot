from typing import List, Optional, TypedDict, Dict
from typing_extensions import NotRequired


class SerializedBasedUser(TypedDict):
    credits: NotRequired[int]
    lifetimeBountyCreditsWon: NotRequired[int]
    bountyCooldownEnd: NotRequired[float]
    systemsChecked: NotRequired[int]
    bountyWins: NotRequired[int]
    activeShip: shipBase.SerializedShipUnion
    duelWins: NotRequired[int]
    duelLosses: NotRequired[int]
    duelCreditsWins: NotRequired[int]
    bountyHuntingXP: NotRequired[Optional[int]]
    duelCreditsLosses: NotRequired[int]
    homeGuildID: NotRequired[int]
    guildTransferCooldownEnd: NotRequired[float]
    prestiges: NotRequired[int]
    alerts: NotRequired[Dict[str, bool]]
    kaamo: NotRequired[guildShop.SerializedShopBase]
    loma: NotRequired[lomaShop.SerializedLomaShop]
    ownedMenus: NotRequired[Dict[str, List[int]]]
    medals: NotRequired[List[str]]
    classicModeEnabled: NotRequired[bool]
    bountyHuntingXpSurplus: NotRequired[int]
    inactiveShips: NotRequired[List[inventoryListing.SerializedInventoryListing[shipBase.SerializedShipUnion]]]
    inactiveWeapons: NotRequired[List[inventoryListing.SerializedInventoryListing[primaryWeapon.SerializedWeaponUnion]]]
    inactiveModules: NotRequired[List[inventoryListing.SerializedInventoryListing[moduleItem.SerializedModuleItemUnion]]]
    inactiveTurrets: NotRequired[List[inventoryListing.SerializedInventoryListing[turretWeapon.SerializedWeaponUnion]]]
    inactiveTools: NotRequired[List[inventoryListing.SerializedInventoryListing[toolItem.TypedSerializedToolItem]]]