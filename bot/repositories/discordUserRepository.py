from typing import Optional
from discord import Client, User

class DiscordUserRepository:
    def __init__(self, client: Client) -> None:
        self.client = client


    async def get(self, id: int) -> Optional[User]:
        return self.client.get_user(id) or await self.client.fetch_user(id)