from .aliasable import Aliasable
from typing import Any, List, Dict


class AliasableDict(dict):
    """A dictionary where keys are guaranteed to be Aliasable subclasses.
    """

    def getKeyNamed(self, name: str) -> Aliasable:
        """Search the dictionary for a key with the given name or alias.

        :param str name: The name or alias to look up
        :return: A key registered in the dictionary with name as either its name or one of its aliases
        :rtype: Aliasable
        :raise KeyError: If no key in the dictionary is called name
        :raise TypeError: If name is not a str
        """
        if type(name) != str:
            raise TypeError("Expecting type str for parameter name, received '" + type(name).__name__ + "'")
        for k in self:
            if k.isCalled(name):
                return k
        raise KeyError("Could not find a key with the given name: " + name)


    def getValueForKeyNamed(self, name: str) -> Any:
        """Search the dictionary for a key with the given name or alias, and get the value paired with it.

        :param str name: The name or alias to look up
        :return: A value which is paired with a registered key where name is either its name or one of its aliases
        :rtype: Any
        :raise KeyError: If no key in the dictionary is called name
        :raise TypeError: If name is not a str
        """
        return self[self.getKeyNamed(name)]


    def getManyKeysNamed(self, names: List[str]) -> Dict[str, Aliasable]:
        """Search the dictionary for a list of keys with the given names or aliases.
        All names must match a key, no partial results are returned.

        In the worst case, this is as efficient as executing one getKeyNamed search per name.
        In the general case however, this is much more efficient as the search is performed over a single iteration.

        :param List[str] name: A list of names or aliases to look up
        :return: A mapping from provided search terms to keys registered in the dictionary, named/aliased as such
        :rtype: Dict[str, Aliasable]
        :raise KeyError: If no key in the dictionary could be found for at least one search term
        :raise TypeError: If name is not a list of strings
        """
        for name in names:
            if type(name) != str:
                raise TypeError(f"Names must be str, but got type '{type(name).__name__}' for name '{name!s}'")
        toFind = set(names)
        results = {}
        for k in self:
            for name in toFind:
                if k.isCalled(name):
                    results[name] = k
                    toFind.remove(name)
        if toFind:
            raise KeyError(f"Could not find keys with the following names: {', '.join(toFind)}")
        return results


    def getValuesForManyKeysNamed(self, name: List[str]) -> Dict[str, Any]:
        """Search the dictionary for keys with the given names or aliases, and get the values paired with them.
        All names must match a key, no partial results are returned.

        In the worst case, this is as efficient as executing one getManyKeysNamed search per name.
        In the general case however, this is much more efficient as the search is performed over a single iteration.

        :param str name: The list of names or aliases to look up
        :return: A mapping from search terms to values paired with registered keys that are named/aliased as such
        :rtype: Dict[str, Any]
        :raise KeyError: If no key in the dictionary could be found for at least one search term
        :raise TypeError: If name is not a list of strings
        """
        return {n: self[k] for n, k in self.getManyKeysNamed(name).items()}


    def __setitem__(self, k: Aliasable, v: Any) -> None:
        """Register a key value pair, or change the value of an existing pair. k must be an Aliasable.

        :param Aliasable k: The key to register, or change the value of
        :param Any v: The value to register to key k
        :raise TypeError: If k is not an Aliasable
        """
        if not isinstance(k, Aliasable):
            raise TypeError("Keys must be Aliasable, given " + type(k).__name__)
        super().__setitem__(k, v)


    def add(self, k: Aliasable) -> None:
        """Register a key value pair, or change the value of an existing pair. k must be an Aliasable.
        The key to register is inferred as k.name

        :param Aliasable k: The key to register, or change the value of
        """
        self[k.name] = k
