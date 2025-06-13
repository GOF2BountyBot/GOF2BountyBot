class PersistenceException(Exception):
    """Base exception for persistence layer"""
    pass

class EntityNotFoundException(PersistenceException):
    """Raised when an entity is not found"""
    pass

class EntityAlreadyExistsException(PersistenceException):
    """Raised when trying to create an entity that already exists"""
    pass

class ValidationException(PersistenceException):
    """Raised when entity validation fails"""
    pass

class StorageException(PersistenceException):
    """Raised when storage operations fail"""
    pass

class SessionException(PersistenceException):
    """Raised when session operations fail"""
    pass

class MigrationException(PersistenceException):
    """Raised when migration operations fail"""
    pass
