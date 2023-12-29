from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..entities.users import basedUser
from .snowflakeRepository import SnowflakeRepository


class UserRepository(SnowflakeRepository["basedUser.BasedUser[Any]"]):
    def __init__(self, session: AsyncSession):
        super().__init__(basedUser.BasedUser[Any], session)

    def addID(self, userID: int) -> "basedUser.BasedUser":
        """
        Create a new BasedUser object with the specified ID and add it to the database

        :param int userID: integer discord ID for the user to add
        :raise KeyError: If a BasedUser already exists in the database with the specified ID
        :return: the newly created BasedUser
        :rtype: BasedUser
        """
        user = await self.create(userID)

        userID = self.validateID(userID)
        # Ensure no user exists with the specified ID in the database
        if self.idExists(userID):
            raise KeyError("Attempted to add a user that is already in this UserDB")
        # Create and return a new user
        newUser = basedUser.BasedUser.deserialize(basedUser.defaultUserDict, id=userID)
        self.users[userID] = newUser
        return newUser
