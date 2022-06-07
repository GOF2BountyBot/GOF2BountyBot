from carica import ISerializable

class Unlockable(ISerializable):
    """Something which is owned by users, but is not an item. Cannot be spawned or traded,
    more like a user attribute.
    """
    pass
