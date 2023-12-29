from discord import Client

from ..discordUserRepository import DiscordUserRepository

class ClientDiscordUserRepositoryFactory:
    def __init__(self, client: Client) -> None:
        self.client = client

    def create(self):
        return DiscordUserRepository(self.client)
    
    
class ShareDiscordUserRepositoryFactory:
    def __init__(self, repository: DiscordUserRepository) -> None:
        self.repository = repository

    def create(self):
        return self.repository
