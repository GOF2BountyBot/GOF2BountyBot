from typing import Any, Dict, Generic, List, Optional, Tuple, Type, TypeVar, Union, cast, get_args, Protocol, overload, runtime_checkable, get_origin

@runtime_checkable
class ParameterlessConstructorProto(Protocol):
    """Any type with a constructor with no required arguments.
    """
    def __init__(self, **kw: Any) -> None: ...


def isOpenGeneric(cls: Type[Any]) -> bool:
    """Decide whether `cls` has any generic type parameters which have not yet been supplied.

    :param cls: The class to check
    :type cls: Type[Any]
    :return: `True` if `cls` is generic in at least one parameter, `False` if `cls` is not generic, or all of its type parameters have been supplied
    :rtype: bool
    """
    if not hasattr(cls, "__orig_bases__"):
        return False
    
    genericBases: Tuple[Type[Any], ...] = getattr(cls, "__orig_bases__")
    for genericBase in genericBases:
        baseGenericParams = get_args(genericBase)
        if any(isinstance(p, TypeVar) for p in baseGenericParams):
            return True
        
    return False


def hasParameterlessConstructor(cls: Type[Any]) -> bool:
    """Decide whether a class has a constructor with no required arguments.

    :param cls: The class to check
    :type cls: Type[Any]
    :return: `True` if `cls` has a constructor overload with no positional parameters, `False` otherwise
    :rtype: bool
    """
    return issubclass(cls, ParameterlessConstructorProto)


def firstBaseWithOrigin(cls: type, origin: Any) -> Optional[Type[Any]]:
    """Get the first `typing.Type` base class on `cls`, of type `origin`.
    This is useful, for example, for getting the generic type parameters of a class.
    Example:

    ```py
    TParam = TypeVar("TParam")

    class Foo(Generic[TParam]):
        ...
    
    bar = firstBaseWithOrigin(Foo, Generic) # Generic[~TParam]
    ```

    :param cls: The class whose base to fetch
    :type cls: type
    :param origin: The `typing.Type` to fetch
    :type origin: Any
    :return: The `typing.Type` of type `origin` which `cls` inherits from
    :rtype: Optional[Type[Any]]
    """
    try:
        return next(b for b in getattr(cls, "__orig_bases__", [])
                    if get_origin(b) == origin)
    except StopIteration:
        return None


def openGenericParameters(cls: Type[Any]) -> List[TypeVar]:
    """Get all generic type parameters for `cls` which have not yet been supplied.

    :param cls: The class to check
    :type cls: Type[Any]
    :return: all generic type parameters for `cls` which have not yet been supplied
    :rtype: bool
    """
    explicitGeneric = firstBaseWithOrigin(cls, Generic)
    if explicitGeneric is not None:
        genericBases = (explicitGeneric,)
    else:
        if not hasattr(cls, "__orig_bases__"):
            return []
        
        genericBases: Tuple[Type[Any], ...] = getattr(cls, "__orig_bases__")

    typeVars: List[TypeVar] = []

    for genericBase in genericBases:
        baseGenericParams = get_args(genericBase)
        for param in (p for p in baseGenericParams if isinstance(p, TypeVar)):
            if param not in typeVars:
                typeVars.append(param)
    
    return typeVars


def _openGenericParamIndex(cls: type, ParamOrType: Union[TypeVar, type]) -> int:
    rootTypeParams = openGenericParameters(cls)
    
    if isinstance(ParamOrType, TypeVar):
        try:
            return rootTypeParams.index(ParamOrType)
        except ValueError as ex:
            raise ValueError(f"Type {cls.__name__} is not generic in TypeVar {ParamOrType.__name__}") from ex

    try:
        if Protocol in cls.__bases__:
            # Note, to allow for value protocols, we check that the generic parameter
            # bound IS rootParamType, not a subclass! https://github.com/python/mypy/issues/3939
            return next(
                i for i, param in enumerate(rootTypeParams)
                if param.__bound__ == ParamOrType)
        else:
            return next(
                i for i, param in enumerate(rootTypeParams)
                if isinstance(param.__bound__, type) and issubclass(param.__bound__, ParamOrType))
    except StopIteration as ex:
        raise RuntimeError(f"Could not find the {ParamOrType.__name__}-bounded generic type parameter for {cls.__name__}") from ex


TRoot = TypeVar("TRoot", bound=Any)
TParam = TypeVar("TParam", bound=Any)

@overload
def genericParamValue(root: Type[TRoot], rootParamType: Type[TParam], cls: Type[TRoot], /) -> Optional[Type[TParam]]:
    """Given a parent class `root` which is generic in a type parameter with bound `rootParamType`,
    and a class `cls` which inherits from `root`, determine the concrete type for the type parameter.
    
    This operation respects transitive and inherited type parameter values, classes which don't
    inherit directly from `typing.Generic`, and also Protocols.

    If `root` has several type parameters with the given bound, the first applicable type var on `root` used.
    
    Example:
    ```py
    class VarBase:
        ...

    class VarChild(VarBase):
        ...

    MyVar = TypeVar(MyVar, bound=VarBase)

    class Parent(List[MyVar]):
        ...
    
    class Child(Parent[VarChild]):
        ...
    
    foo = genericParamValue(Parent, VarBase, Child) # foo = VarChild

    MyVar2 = TypeVar(MyVar2, bound=VarChild)
    
    class GenericChild(Parent[MyVar2]):
        ...

    bar = genericParamValue(Parent, VarBase, GenericChild) # foo = None
    ```

    :param root: The base class containing the desired type var
    :type root: Type[TRoot]
    :param rootParamType: The bound of the type var whose value to find
    :type rootParamType: Type[TParam]
    :param cls: The child class containing the concrete type parameter value
    :type cls: Type[TRoot]
    :return: The value of the first type var with bound `rootParamType` on `cls`
    :rtype: Optional[Type[TParam]]
    """

@overload
def genericParamValue(root: Type[TRoot], rootTypeVar: TypeVar, cls: Type[TRoot], /) -> Optional[Type[Any]]:
    """Given a parent class `root` which is generic in a type parameter `rootTypeVar`,
    and a class `cls` which inherits from `root`, determine the concrete type for `rootTypeVar`.
    
    This operation respects transitive and inherited type parameter values, classes which don't
    inherit directly from `typing.Generic`, and also Protocols.
    
    Example:
    ```py
    class Parent(List[MyVar]):
        ...
    
    class Child(Parent[int]):
        ...
    
    foo = genericParamValue(Parent, MyVar, Child) # foo = int

    class GenericChild(Parent[MyVar2]):
        ...

    bar = genericParamValue(Parent, MyVar, GenericChild) # foo = None
    ```

    :param root: The base class containing the desired type var
    :type root: Type[TRoot]
    :param rootTypeVar: The type var whose value to find
    :type rootTypeVar: Type[TParam]
    :param cls: The child class containing the concrete type parameter value
    :type cls: Type[TRoot]
    :return: The value of `rootTypeVar` on `cls`
    :rtype: Optional[Type[TParam]]
    """

def genericParamValue(root: Type[TRoot], rootParamOrType: Union[TypeVar, TParam], cls: Type[TRoot], /) -> Optional[Type[TParam]]:
    # Find the index of the type param on root
    rootParamIndex = _openGenericParamIndex(root, rootParamOrType)
    
    # For each base, record the position of the type parameter which decides rootParamOrType
    recordTypeParameterIndices: Dict[Type[TRoot], int] = {root: rootParamIndex}

    # only take base classes higher than root
    # Not sure why pyright is reporting that I need to give a 'self' argument to cls.mro
    mro = cast(List[type], cls.mro()) # type: ignore[reportCallIssue]
    bases: List[Type[TRoot]] = list(b for b in reversed(mro) if issubclass(b, root))
    rootBaseIndex = bases.index(root)

    # Walk up the mro to find the first rootParamOrType-deciding type parameter which has been
    # given as a type rather than a TypeVar
    for base in bases[rootBaseIndex+1:]:
        currentRootBase: Optional[Type[TRoot]] = None
        currentRootHint: Optional[Type[TRoot]] = None

        # Find the first base class of the current base which inherits from root. We're walking the
        # mro, which always(tm) a linear list of all bases, so just taking the first here is fine
        for upperHint in getattr(base, "__orig_bases__", []):
            upperBase = get_origin(upperHint)
            if isinstance(upperBase, type) and issubclass(upperBase, root):
                currentRootBase = upperBase
                currentRootHint = upperHint
                break
        
        if currentRootBase is None: # Should never happen, but just in case
            continue

        # Since we're walking the mro, we're walking the bases in upwards-inheritence order.
        # That means we must already have visited this class's bases, and therefore already
        # know the index of the type parameter we're looking for
        argIndex = recordTypeParameterIndices[currentRootBase]
        recordTypeArg: Union[Type[Any], TypeVar] = get_args(currentRootHint)[argIndex]
        if isinstance(recordTypeArg, type):
            # if isOpenGeneric(base):
            #     continue
            # The current base class sets the value of the type var we're looking for to a concrete type
            return recordTypeArg
        
        params = openGenericParameters(base)
        rootParamIndex = params.index(recordTypeArg)
        recordTypeParameterIndices[base] = rootParamIndex

    return None