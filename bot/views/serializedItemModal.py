from typing import List, Optional, Union, cast
from discord.ui import TextInput, Modal
from discord import Interaction, TextStyle
from discord.utils import MISSING
import json

from ..baseClasses.serializable import JsonType
from ..gameObjects.items.gameItem import TypedSerializedGameItemUnion

class SerializedItemModal(Modal):
    """A modal for gathering a JSON-serialized item.
    `builtIn` bool, `name` str, `type` str and `extras` str
    
    This modal could definitely be dynamic if I wanted.
    E.g the commands using the modal could take the `type` field as an autocomplete and, given the concrete type, a view could be created dynamically with all of the correct fields.
    Obviously this would need some special consideration like paging, and choosing when to finish (because most fields are optional)
    """
    _typeName = TextInput(label="Item Type Name", style=TextStyle.short, required=True)
    _name = TextInput(label="Name", style=TextStyle.short, required=True)
    _extras = TextInput(label="Extras", style=TextStyle.paragraph, required=False, placeholder="{}", default="{\n    \n}")
    _builtIn = TextInput(label="Built In Item?", style=TextStyle.short, placeholder="y/n", default="y", required=False, max_length=1)
    
    def __init__(self, *, title: Optional[str] = "SerializedItem", timeout: Optional[float] = 120, custom_id: Optional[str] = None) -> None:
        super().__init__(title=title or MISSING, timeout=timeout, custom_id=custom_id or MISSING)
        self._interaction: Optional[Interaction] = None
        self._timedOut: Optional[bool] = None
        self.errors: List[str] = []
        self._json: TypedSerializedGameItemUnion = {"name": "", "builtIn": False, "type": ""}
        
        
    def _activeCheck(self):
        if not self.done:
            raise RuntimeError("This modal is still active")
        if self.timedOut:
            raise ValueError("This modal has timed out")

    
    @property
    def done(self):
        """Whether or not the modal has completed.
        This is `True` if the modal has been reponded to or has timed out, and is `False` otherwise.
        """
        return self._timedOut is not None
    
    
    @property
    def isValid(self):
        """Whether or not valid `extras` json was supplied.
        """
        self._activeCheck()
        return not self.errors


    @property
    def interaction(self):
        """The interaction that responded to this modal.
        Raises `ValueError` if the modal timed out.
        """
        self._activeCheck()
        return cast(Interaction, self._interaction)


    @property
    def timedOut(self):
        """Whether or not the modal timed out.
        """
        if not self.done:
            raise RuntimeError("This modal is still active")
        return cast(bool, self._timedOut)
    
    
    def itemJson(self):
        """The JSON result of the modal, entered by the user.
        """
        self._activeCheck()
        if self.errors:
            raise ValueError("Validation failed for this modal. Please consume the .errors instead.")
        return self._json
    
    
    async def on_timeout(self) -> None:
        """Sets the modal's `timedOut` tracker. Do not override.
        """
        self._timedOut = True
    
    
    async def on_submit(self, interaction: Interaction, /) -> None:
        """Sets the modal's `_json` and `errors` trackers. Do not override.
        """
        self._timedOut = False
        self._interaction = interaction
        
        try:
            extras: JsonType = json.loads(self._extras.value)
        except json.JSONDecodeError as e:
            extras = {}
            self.errors.append(f"{json.JSONDecodeError.__name__}: {e}")
            
        if not isinstance(extras, dict):
            self.errors.append(f"Extras must be a json dictionary. Received {type(extras).__name__}: {extras}")
            extras = {}
        
        builtIn = self._builtIn.value.lower()
        if builtIn not in ("y", "n"):
            self.errors.append(f"builtIn can only be 'y' or 'n'. Received '{builtIn}'")
            
        for f in ("builtIn", "name", "type"):
            if f in extras:
                self.errors.append(f"Extras cannot contain field '{f}'")
            
        self._json["builtIn"] = builtIn == "y"
        self._json["name"] = self._name.value
        self._json["type"] = self._typeName.value
        
        # Untyped JSON is not allowed to be applied to a TypedDict.
        # My guess is that it could alter the contents of the dict, for example extras could contain name: None,
        # which bypasses the constraints of the TypedDict.
        # I've checked for the required fields above, which is as much as I can do for now.
        self._json.update(extras) # type: ignore[reportGeneralTypeIssues]
