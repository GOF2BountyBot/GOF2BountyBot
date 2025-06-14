"""
Updated bot class integrating the repository pattern.
Shows how to modify your existing Discord bot to use the new architecture.
"""
import discord
from discord.ext import commands
import json
import os
from typing import Dict, Any, Optional

from repository_factory import BotRepositoryManager
from hybrid_repository import UserRepository, GuildRepository, BountyRepository, GameDataRepository

class GOF2BountyBot(commands.Bot):
    """
    Enhanced GOF2BountyBot with repository pattern integration.

    This replaces your existing bot class and provides repository access
    throughout your command implementations.
    """

    def __init__(self, config: Dict[str, Any]):
        # Initialize Discord bot with config
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True

        super().__init__(
            command_prefix=self.get_prefix,
            description=config.get("description", "GOF2 Bounty Bot"),
            intents=intents
        )

        self.config = config
        self.repository_manager: Optional[BotRepositoryManager] = None

        # Repository shortcuts for easy access
        self.user_repo: Optional[UserRepository] = None
        self.guild_repo: Optional[GuildRepository] = None
        self.bounty_repo: Optional[BountyRepository] = None
        self.game_data_repo: Optional[GameDataRepository] = None

    async def setup_hook(self):
        """
        Setup hook called when bot is starting up.
        Initialize repositories and load cogs.
        """
        print("Initializing GOF2BountyBot...")

        # Initialize repository manager
        self.repository_manager = BotRepositoryManager(self.config)
        success = await self.repository_manager.initialize()

        if not success:
            print("WARNING: Repository initialization failed - some features may not work")

        # Set up repository shortcuts
        self.user_repo = self.repository_manager.get_user_repository()
        self.guild_repo = self.repository_manager.get_guild_repository()
        self.bounty_repo = self.repository_manager.get_bounty_repository()
        self.game_data_repo = self.repository_manager.get_game_data_repository()

        # Load cogs/extensions
        await self.load_extensions()

        print("Bot setup complete!")

    async def close(self):
        """Cleanup when bot is shutting down."""
        if self.repository_manager:
            await self.repository_manager.shutdown()
        await super().close()

    async def get_prefix(self, message):
        """
        Dynamic prefix based on guild settings.
        Falls back to default if guild not configured.
        """
        if not message.guild:
            return self.config.get("default_prefix", "!")

        if self.guild_repo:
            prefix = await self.guild_repo.get_guild_prefix(str(message.guild.id))
            return prefix

        return self.config.get("default_prefix", "!")

    async def load_extensions(self):
        """Load bot extensions/cogs."""
        extensions = [
            "cogs.user_commands",
            "cogs.bounty_commands", 
            "cogs.admin_commands",
            "cogs.game_commands"
        ]

        for extension in extensions:
            try:
                await self.load_extension(extension)
                print(f"Loaded extension: {extension}")
            except Exception as e:
                print(f"Failed to load extension {extension}: {e}")

    async def on_ready(self):
        """Called when bot is ready and connected."""
        print(f"{self.user} has connected to Discord!")
        print(f"Bot is in {len(self.guilds)} guilds")

        # Display repository status
        if self.repository_manager:
            status = await self.repository_manager.get_status()
            print(f"Database available: {self.repository_manager.is_database_available()}")

            # Show migration status
            migration_status = status.get("migration", {})
            for repo_name, repo_status in migration_status.get("repositories", {}).items():
                total = repo_status.get("total_entities", 0)
                migrated = repo_status.get("migrated_entities", 0)
                print(f"{repo_name}: {migrated}/{total} entities migrated to database")

    async def on_guild_join(self, guild):
        """Called when bot joins a new guild."""
        print(f"Joined new guild: {guild.name} ({guild.id})")

        # Initialize guild settings
        if self.guild_repo:
            guild_data = {
                "id": str(guild.id),
                "name": guild.name,
                "settings": {},
                "prefix": "!",
                "enabled_modules": ["bounties", "users", "game_data"],
                "admin_roles": []
            }

            result = await self.guild_repo.save(str(guild.id), guild_data)
            if result.success:
                print(f"Initialized settings for guild {guild.name}")

    async def on_command_error(self, ctx, error):
        """Handle command errors."""
        if isinstance(error, commands.CommandNotFound):
            return  # Ignore unknown commands

        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Missing required argument: {error.param.name}")
            return

        if isinstance(error, commands.BadArgument):
            await ctx.send(f"Invalid argument provided: {error}")
            return

        # Log unexpected errors
        print(f"Command error in {ctx.command}: {error}")
        await ctx.send("An unexpected error occurred. Please try again later.")


# Example command cog showing repository usage
class UserCommands(commands.Cog):
    """Example cog showing how to use repositories in commands."""

    def __init__(self, bot: GOF2BountyBot):
        self.bot = bot

    @commands.command(name="credits")
    async def show_credits(self, ctx, user: discord.User = None):
        """Show user credits."""
        target_user = user or ctx.author
        user_id = str(target_user.id)

        # Get credits using repository
        credits = await self.bot.user_repo.get_user_credits(user_id)

        embed = discord.Embed(
            title="Credits",
            description=f"{target_user.mention} has **{credits:,}** credits",
            color=discord.Color.green()
        )

        await ctx.send(embed=embed)

    @commands.command(name="give_credits")
    @commands.has_permissions(administrator=True)
    async def give_credits(self, ctx, user: discord.User, amount: int):
        """Give credits to a user (admin only)."""
        if amount <= 0:
            await ctx.send("Amount must be positive!")
            return

        user_id = str(user.id)

        # Update credits using repository
        result = await self.bot.user_repo.update_user_credits(user_id, amount)

        if result.success:
            new_credits = await self.bot.user_repo.get_user_credits(user_id)
            embed = discord.Embed(
                title="Credits Given",
                description=f"Gave {amount:,} credits to {user.mention}\n"
                           f"New balance: {new_credits:,} credits",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"Failed to give credits: {result.error}")

    @commands.command(name="profile")
    async def show_profile(self, ctx, user: discord.User = None):
        """Show user profile."""
        target_user = user or ctx.author
        user_id = str(target_user.id)

        # Get full user data using repository
        result = await self.bot.user_repo.get(user_id)

        if result.success and result.data:
            user_data = result.data
            embed = discord.Embed(
                title=f"{target_user.display_name}'s Profile",
                color=discord.Color.blue()
            )
            embed.add_field(name="Credits", value=f"{user_data.get('credits', 0):,}", inline=True)
            embed.add_field(name="Reputation", value=user_data.get('reputation', 0), inline=True)
            embed.add_field(name="Data Source", value=result.source.value.title(), inline=True)

            # Show inventory if exists
            inventory = user_data.get('inventory', {})
            if inventory:
                inv_text = "\n".join([f"{item}: {count}" for item, count in inventory.items()])
                embed.add_field(name="Inventory", value=inv_text[:1024], inline=False)

            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="Profile Not Found",
                description=f"{target_user.mention} hasn't used the bot yet!",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)


# Example bounty command showing repository usage
class BountyCommands(commands.Cog):
    """Example bounty commands using repositories."""

    def __init__(self, bot: GOF2BountyBot):
        self.bot = bot

    @commands.command(name="bounties")
    async def list_bounties(self, ctx):
        """List all open bounties for this server."""
        guild_id = str(ctx.guild.id)

        # Get open bounties using repository
        result = await self.bot.bounty_repo.get_open_bounties(guild_id)

        if not result.success:
            await ctx.send(f"Error retrieving bounties: {result.error}")
            return

        bounties = result.data

        if not bounties:
            embed = discord.Embed(
                title="No Open Bounties",
                description="There are no open bounties in this server.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(
            title=f"Open Bounties ({len(bounties)})",
            color=discord.Color.gold()
        )

        for bounty in bounties[:10]:  # Show first 10
            embed.add_field(
                name=f"{bounty['title']} - {bounty['reward']:,} credits",
                value=f"Criminal: {bounty['criminal_name']}\n"
                      f"System: {bounty['system_name']}\n"
                      f"Created by: <@{bounty['creator_id']}>",
                inline=False
            )

        if len(bounties) > 10:
            embed.set_footer(text=f"Showing 10 of {len(bounties)} bounties")

        await ctx.send(embed=embed)


# Admin command showing migration status
class AdminCommands(commands.Cog):
    """Admin commands for bot management."""

    def __init__(self, bot: GOF2BountyBot):
        self.bot = bot

    @commands.command(name="migration_status")
    @commands.has_permissions(administrator=True)
    async def migration_status(self, ctx):
        """Show migration status (admin only)."""
        if not self.bot.repository_manager:
            await ctx.send("Repository manager not initialized!")
            return

        status = await self.bot.repository_manager.get_status()

        embed = discord.Embed(
            title="Migration Status",
            color=discord.Color.blue()
        )

        # Database status
        db_health = status.get("health", {}).get("database", {})
        db_status = db_health.get("status", "unknown")
        embed.add_field(name="Database", value=db_status.title(), inline=True)

        # Repository migration status
        migration = status.get("migration", {})
        repos = migration.get("repositories", {})

        for repo_name, repo_status in repos.items():
            total = repo_status.get("total_entities", 0)
            migrated = repo_status.get("migrated_entities", 0)
            json_only = repo_status.get("json_only_entities", 0)

            if total > 0:
                percentage = (migrated / total) * 100
                embed.add_field(
                    name=f"{repo_name.title()} Repository",
                    value=f"{migrated}/{total} migrated ({percentage:.1f}%)\n"
                          f"{json_only} JSON-only entities",
                    inline=True
                )

        await ctx.send(embed=embed)


# Setup function for loading cogs
async def setup(bot):
    """Setup function to load cogs."""
    await bot.add_cog(UserCommands(bot))
    await bot.add_cog(BountyCommands(bot))
    await bot.add_cog(AdminCommands(bot))
