class PersistenceError(Exception):
    """Base class for persistence-related problems."""


class UnknownBackend(PersistenceError):
    """Raised when the chosen backend identifier is not recognised."""