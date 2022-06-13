from carica import ISerializable # type: ignore[import]
from .defaultable import DefaultableMixin
from .simpleHash import SimpleHashMixin


class Serializable(ISerializable, DefaultableMixin, SimpleHashMixin):
    """BountyBot DefaultableMixin for shorthanding deserializer implementations in most serializable classes,
    and SimpleHashMixin for using game objects as dict keys,
    so just include both by default.
    """
    pass
