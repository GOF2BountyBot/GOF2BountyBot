from ..baseClasses.basedEnum import BasedEnum

class StoreableItemType(BasedEnum):
    ship = 0
    primaryWeapon = 1
    turret = 2
    module = 3
    tool = 4


class ShipInstanceEquippedItemType(BasedEnum):
    primaryWeapon = 1
    turret = 2
    module = 3
    shipUpgrade = 5


class GuildRoleUserAlertType(BasedEnum):
    shopRefresh = 0
    botUpdatesMajor = 1
    botUpdatesMinor = 2
    botAnnouncements = 3


class StateUserAlertFlag(BasedEnum):
   duelsIncomingNew = 0x01
   duelsIncomingCancelled = 0x10


class ShipSkinRegion(BasedEnum):
    primary = 0
    secondary = 1
    tertiary = 2
    cockpit = 3
    glyphs = 4


class ShipSkinMethod(BasedEnum):
    direct = 0
    autoskin = 1
