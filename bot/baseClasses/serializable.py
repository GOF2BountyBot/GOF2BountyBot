from __future__ import annotations
from abc import ABC, abstractmethod, abstractclassmethod
import inspect
from typing import Dict, Any, Tuple, List, Union
from types import FunctionType

def get_default_args(func: FunctionType) -> Dict[str, Any]:
    """Get a dictionary of the default kwarg values for a given function.
    https://stackoverflow.com/a/12627202

    :param FunctionType func: The function for which to read argument defaults
    :return: A dictionary with all of func's kwarg names as keys, and default values as defaults
    :rtype: Dict[str, Any]
    """
    signature = inspect.signature(func)
    return {
        k: v.default
        for k, v in signature.parameters.items()
        if v.default is not inspect.Parameter.empty
    }


class Serializable(ABC):
    _defaults: Union[None, Dict[str, Any]] = None

    @abstractmethod
    def toDict(self, **kwargs) -> dict:
        """Serialize this object into dictionary format, to be recreated completely.

        :return: A dictionary containing all information needed to recreate this object
        :rtype: dict
        """
        return {}


    @abstractclassmethod
    def fromDict(cls, data: dict, **kwargs) -> Serializable:
        """Recreate a dictionary-serialized Serializable object

        :param dict data: A dictionary containing all information needed to recreate the serialized object
        :return: A new object as specified by the attributes in data
        :rtype: Serializable
        """
        pass


    def __hash__(self) -> int:
        """Calculate a hash of this object based on its type name and location in memory.

        :return: A unique hash for this object
        :rtype: int
        """
        return hash(repr(self))
    
    @classmethod
    def _makeDefaults(cls, args : Dict[str, Any] = {}, ignores : Tuple[str] = (), **overrides) -> Dict[str, Any]:
        """Creates a dictionary addressing each KEYWORD argument of this class's constructor.
        Does not address positional arguments.

        If a kwarg value is given in args, then it replaces the default value.
        Overrides acts as a secondary mask to args, replacing those values again.
        All keys listed in ignores are removed from the args dictionary prior to copying into the new dict.

        :param args: A dict of argument values to replace the default values with
        :type args: Dict[str, Any] 
        :param ignores: A list of keys to remove from the working copy of args prior to use
        :type ignores: Tuple[str]
        :param **overrides: values for any kwarg can be given to override the args values again.
        :return: A dictionary containing the default KWARG values for the class constructor, with values replaced by those
                in args (as long as they are not in ignores), but replace again by any overrides.
        :rtype: Dict[str, Any]
        """
        if cls._defaults is None:
            cls._defaults = get_default_args(cls.__init__)
        newArgs = cls._defaults.copy()
        if ignores:
            workingArgs = args.copy()
            for argName in ignores:
                if argName in workingArgs:
                    del workingArgs[argName]
            newArgs.update(workingArgs)
        else:
            newArgs.update(args)
        newArgs.update(overrides)
        return newArgs

    
    @classmethod
    def _allArgs(cls) -> List[str]:
        """Get a list of all argument names accepted by the class constructor, including positional and keyword.

        :return: All argument names for the subclass constructor
        :rtype: List[str]
        """
        return [str(i) for i in inspect.signature(cls).parameters]
