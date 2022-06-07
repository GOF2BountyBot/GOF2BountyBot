class SimpleHashMixin:
    """A class mixin that adds a minimal hash implementation.
    """
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)


    def __hash__(self) -> int:
        """Calculate a hash of this object based on its type name and location in memory.

        :return: A unique hash for this object
        :rtype: int
        """
        return hash(repr(self))


def simpleHash(cls: type) -> type:
    """Assign the SimpleHashMixin hash implementation to a class using a decorator instead of inheritence.
    """
    cls.__hash__ = SimpleHashMixin.__hash__
