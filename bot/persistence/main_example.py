"""
Main entry point for GOF2BountyBot.
Handles configuration loading and bot startup.
"""
import asyncio
import json
import os
import sys
import logging
from pathlib import Path

from bot_integration import GOF2BountyBot

def load_config(config_path: str = "config.json") -> dict:
    """Load configuration from JSON file."""
    if not os.path.exists(config_path):
        print(f"Configuration file {config_path} not found!")
        print("Please copy config.example.json to config.json and update with your settings.")
        sys.exit(1)

    try:
        with open(config_path, 'r') as f:
            config = json.load(f)

        # Validate required settings
        if not config.get("discord", {}).get("token"):
            print("Discord bot token not configured!")
            print("Please set discord.token in your config.json file.")
            sys.exit(1)

        return config

    except json.JSONDecodeError as e:
        print(f"Invalid JSON in configuration file: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading configuration: {e}")
        sys.exit(1)

def setup_logging(config: dict):
    """Setup logging configuration."""
    log_config = config.get("logging", {})
    log_level = getattr(logging, log_config.get("level", "INFO"))

    # Create logs directory if needed
    log_file = log_config.get("file")
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

    # Setup logging format
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file) if log_file else logging.NullHandler()
        ]
    )

def setup_data_directory(config: dict):
    """Ensure data directory exists."""
    data_dir = config.get("data_dir", "data")
    Path(data_dir).mkdir(parents=True, exist_ok=True)
    print(f"Data directory: {data_dir}")

async def main():
    """Main async entry point."""
    print("Starting GOF2BountyBot with Repository Pattern...")

    # Load configuration
    config = load_config()

    # Setup logging
    setup_logging(config)

    # Setup data directory  
    setup_data_directory(config)

    # Create and run bot
    bot = GOF2BountyBot(config)

    try:
        # Get Discord token
        token = config["discord"]["token"]

        print("Connecting to Discord...")
        await bot.start(token)

    except KeyboardInterrupt:
        print("\nShutting down bot...")
        await bot.close()

    except Exception as e:
        print(f"Bot error: {e}")
        await bot.close()
        sys.exit(1)

if __name__ == "__main__":
    # Check Python version
    if sys.version_info < (3, 8):
        print("Python 3.8 or higher is required!")
        sys.exit(1)

    # Run the bot
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped by user.")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)
