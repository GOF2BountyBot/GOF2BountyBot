from sqlalchemy.orm.decl_api import DeclarativeAttributeIntercept
from abc import ABCMeta

from ..baseClasses.embedFillable import _EmbedFillableMeta

class AbcSqlTableMeta(ABCMeta, DeclarativeAttributeIntercept):
    """Metaclass intersecting the sqlalchemy declarative base and abstract base class metaclasses.
    """

class EmbedFillableSqlTableMeta(_EmbedFillableMeta, DeclarativeAttributeIntercept):
    """Metaclass intersecting the sqlalchemy declarative base and EmbedFillable metaclasses.
    """
