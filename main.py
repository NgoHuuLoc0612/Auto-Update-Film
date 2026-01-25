"""
Auto Update Film Discord Bot
Main entry point for the application
"""
import asyncio
import logging
import signal
import sys
from pathlib import Path

import discord
from discord.ext import commands

from core.config import Config
from core.database import Database
from core.logger import setup_logging
from core.supabase_config import SupabaseConfig
from utils.helpers import load_extensions


class FilmBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        
        super().__init__(
            command_prefix=commands.when_mentioned_or(Config.PREFIX),
            intents=intents,
            help_command=None,
            case_insensitive=True,
            owner_ids=Config.OWNER_IDS
        )
        
        self.config = Config
        self.db = None
        self.logger = logging.getLogger('FilmBot')
        
    async def setup_hook(self):
        """Initialize bot components before connecting"""
        self.logger.info("Initializing bot components...")
        
        # Determine database URL
        if Config.USE_SUPABASE:
            database_url = SupabaseConfig.get_database_url()
            if SupabaseConfig.is_using_supabase():
                self.logger.info("Using Supabase PostgreSQL database")
            else:
                self.logger.warning("Supabase not configured, falling back to SQLite")
                database_url = Config.DATABASE_URL
        else:
            database_url = Config.DATABASE_URL
            self.logger.info("Using configured database")
        
        # Initialize database
        self.db = Database(
            database_url,
            Config.DATABASE_ECHO,
            Config.DATABASE_POOL_SIZE,
            Config.DATABASE_MAX_OVERFLOW
        )
        await self.db.initialize()
        self.logger.info("Database initialized")
        
        # Load all extensions
        extensions_dir = Path('cogs')
        await load_extensions(self, extensions_dir)
        self.logger.info(f"Loaded {len(self.extensions)} extensions")
        
        # Sync slash commands
        if Config.SYNC_COMMANDS:
            self.logger.info("Syncing slash commands...")
            await self.tree.sync()
            self.logger.info("Commands synced")
    
    async def on_ready(self):
        """Called when bot is ready"""
        self.logger.info(f"Logged in as {self.user.name} ({self.user.id})")
        self.logger.info(f"Connected to {len(self.guilds)} guilds")
        
        # Set bot presence
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{Config.PREFIX}help | Movies & TV Shows"
        )
        await self.change_presence(activity=activity, status=discord.Status.online)
    
    async def on_command_error(self, ctx, error):
        """Global error handler"""
        if isinstance(error, commands.CommandNotFound):
            return
        
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to use this command.")
            return
        
        if isinstance(error, commands.BotMissingPermissions):
            await ctx.send("❌ I don't have the required permissions.")
            return
        
        self.logger.error(f"Command error in {ctx.command}: {error}", exc_info=error)
        await ctx.send(f"❌ An error occurred: {str(error)}")
    
    async def close(self):
        """Cleanup before shutdown"""
        self.logger.info("Shutting down bot...")
        
        if self.db:
            await self.db.close()
            self.logger.info("Database connection closed")
        
        await super().close()


async def main():
    """Main function to run the bot"""
    setup_logging()
    logger = logging.getLogger('FilmBot')
    
    bot = FilmBot()
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        asyncio.create_task(bot.close())
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await bot.start(Config.DISCORD_TOKEN)
    except KeyboardInterrupt:
        logger.info("Bot interrupted by user")
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())