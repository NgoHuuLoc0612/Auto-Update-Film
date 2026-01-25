"""
Help command cog
Displays help information and command list
"""
import logging

import discord
from discord import app_commands
from discord.ext import commands

from core.config import Config
from utils.helpers import create_embed_base


class Help(commands.Cog):
    """Help and information commands"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger('FilmBot.Help')
    
    @app_commands.command(name="help", description="Display help information and command list")
    @app_commands.describe(category="Specific category to view")
    @app_commands.choices(category=[
        app_commands.Choice(name="All Commands", value="all"),
        app_commands.Choice(name="Search & Discovery", value="search"),
        app_commands.Choice(name="Subscriptions", value="subscriptions"),
        app_commands.Choice(name="Watchlist", value="watchlist"),
        app_commands.Choice(name="Recommendations", value="recommendations"),
        app_commands.Choice(name="Admin & Config", value="admin")
    ])
    async def help_command(self, interaction: discord.Interaction, category: str = "all"):
        """Show help information"""
        await interaction.response.defer()
        
        try:
            if category == "all":
                embed = self._create_general_help()
            elif category == "search":
                embed = self._create_search_help()
            elif category == "subscriptions":
                embed = self._create_subscriptions_help()
            elif category == "watchlist":
                embed = self._create_watchlist_help()
            elif category == "recommendations":
                embed = self._create_recommendations_help()
            elif category == "admin":
                embed = self._create_admin_help()
            else:
                embed = self._create_general_help()
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Help command error: {e}", exc_info=True)
            embed = create_embed_base(
                title="❌ Error",
                description="An error occurred while displaying help."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    def _create_general_help(self) -> discord.Embed:
        """Create general help embed"""
        embed = create_embed_base(
            title="🎬 Auto Update Film Bot - Help",
            description=(
                "Your comprehensive movie and TV show tracking assistant!\n\n"
                "**Key Features:**\n"
                "• 🔍 Search movies, TV shows, and people\n"
                "• 📌 Subscribe to get updates on new releases\n"
                "• 📝 Personal watchlist management\n"
                "• 🎯 Personalized recommendations\n"
                "• 🔔 Automatic notifications\n"
                "• ⭐ Rate and review content\n"
            )
        )
        
        embed.add_field(
            name="🔍 Search & Discovery",
            value=(
                "`/search` - Search for movies and TV shows\n"
                "`/movie` - Get detailed movie information\n"
                "`/trending` - View trending content\n"
                "`/similar` - Find similar content"
            ),
            inline=False
        )
        
        embed.add_field(
            name="📌 Subscriptions",
            value=(
                "`/subscribe` - Subscribe to a movie/show\n"
                "`/unsubscribe` - Remove subscription\n"
                "`/subscriptions` - List all subscriptions"
            ),
            inline=False
        )
        
        embed.add_field(
            name="📝 Watchlist",
            value=(
                "`/watchlist-add` - Add to watchlist\n"
                "`/watchlist` - View your watchlist\n"
                "`/watchlist-remove` - Remove from watchlist\n"
                "`/watchlist-mark-watched` - Mark as watched"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🎯 Recommendations",
            value=(
                "`/recommend` - Get personalized recommendations\n"
                "`/similar` - Find similar content"
            ),
            inline=False
        )
        
        embed.add_field(
            name="⚙️ Admin & Config",
            value=(
                "`/setup` - Initial bot setup\n"
                "`/config` - Configure bot settings\n"
                "`/stats` - View bot statistics"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🔗 Links",
            value=(
                "[Support Server](https://discord.gg/example) • "
                "[Documentation](https://docs.example.com) • "
                "[Invite Bot](https://discord.com/api/oauth2/authorize?client_id=YOUR_ID&permissions=8&scope=bot%20applications.commands)"
            ),
            inline=False
        )
        
        return embed
    
    def _create_search_help(self) -> discord.Embed:
        """Create search help embed"""
        embed = create_embed_base(
            title="🔍 Search & Discovery Commands",
            description="Find movies, TV shows, and discover new content"
        )
        
        embed.add_field(
            name="`/search <query> [media_type]`",
            value=(
                "Search for movies and TV shows\n"
                "**Example:** `/search Inception movie`\n"
                "**Options:** All, Movies, TV Shows"
            ),
            inline=False
        )
        
        embed.add_field(
            name="`/movie <movie_id>`",
            value=(
                "Get detailed information about a specific movie\n"
                "**Example:** `/movie 27205`\n"
                "Shows: cast, crew, budget, revenue, ratings, and more"
            ),
            inline=False
        )
        
        embed.add_field(
            name="`/trending [media_type] [time_window]`",
            value=(
                "View trending movies and TV shows\n"
                "**Example:** `/trending movie week`\n"
                "**Options:** All/Movies/TV Shows, Today/This Week"
            ),
            inline=False
        )
        
        embed.add_field(
            name="`/similar <query>`",
            value=(
                "Find similar movies or TV shows\n"
                "**Example:** `/similar Breaking Bad`\n"
                "Returns content similar to your search"
            ),
            inline=False
        )
        
        return embed
    
    def _create_subscriptions_help(self) -> discord.Embed:
        """Create subscriptions help embed"""
        embed = create_embed_base(
            title="📌 Subscription Commands",
            description="Get automatic updates for your favorite movies and TV shows"
        )
        
        embed.add_field(
            name="`/subscribe <query>`",
            value=(
                "Subscribe to get updates on a movie or TV show\n"
                "**Example:** `/subscribe Dune Part 3`\n"
                "Receive notifications when:\n"
                "• New episodes air (TV shows)\n"
                "• Release dates are announced\n"
                "• Content becomes available"
            ),
            inline=False
        )
        
        embed.add_field(
            name="`/unsubscribe <query>`",
            value=(
                "Remove a subscription\n"
                "**Example:** `/unsubscribe Stranger Things`\n"
                "Stop receiving notifications for this content"
            ),
            inline=False
        )
        
        embed.add_field(
            name="`/subscriptions`",
            value=(
                "List all active subscriptions for this server\n"
                "Shows all movies and TV shows being tracked"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🔔 Notification Settings",
            value=(
                "Configure notifications with `/config`\n"
                "• Set notification channel\n"
                "• Set notification role\n"
                "• Enable/disable auto-updates"
            ),
            inline=False
        )
        
        return embed
    
    def _create_watchlist_help(self) -> discord.Embed:
        """Create watchlist help embed"""
        embed = create_embed_base(
            title="📝 Watchlist Commands",
            description="Manage your personal watchlist"
        )
        
        embed.add_field(
            name="`/watchlist-add <query>`",
            value=(
                "Add a movie or TV show to your watchlist\n"
                "**Example:** `/watchlist-add The Matrix`\n"
                f"**Limit:** {Config.MAX_WATCHLIST_ITEMS} items per user"
            ),
            inline=False
        )
        
        embed.add_field(
            name="`/watchlist [show_watched]`",
            value=(
                "View your watchlist\n"
                "**Example:** `/watchlist true`\n"
                "**Options:** Include watched items (true/false)"
            ),
            inline=False
        )
        
        embed.add_field(
            name="`/watchlist-remove <query>`",
            value=(
                "Remove an item from your watchlist\n"
                "**Example:** `/watchlist-remove Inception`"
            ),
            inline=False
        )
        
        embed.add_field(
            name="`/watchlist-mark-watched <query>`",
            value=(
                "Mark an item as watched\n"
                "**Example:** `/watchlist-mark-watched Avatar`\n"
                "Tracks your viewing history"
            ),
            inline=False
        )
        
        embed.add_field(
            name="⭐ Rating & Reviews",
            value=(
                "After marking items as watched, you can:\n"
                "• Rate them on a scale of 1-10\n"
                "• Write reviews\n"
                "• Get personalized recommendations"
            ),
            inline=False
        )
        
        return embed
    
    def _create_recommendations_help(self) -> discord.Embed:
        """Create recommendations help embed"""
        embed = create_embed_base(
            title="🎯 Recommendation Commands",
            description="Discover new content based on your preferences"
        )
        
        embed.add_field(
            name="`/recommend [based_on] [media_type]`",
            value=(
                "Get personalized recommendations\n"
                "**Example:** `/recommend watchlist movie`\n\n"
                "**Based On:**\n"
                "• My Watchlist - Personalized for you\n"
                "• Trending Now - What's hot\n"
                "• Popular - Most watched\n"
                "• Top Rated - Highest rated\n\n"
                "**Media Type:**\n"
                "• Both - Movies and TV shows\n"
                "• Movies - Only movies\n"
                "• TV Shows - Only TV shows"
            ),
            inline=False
        )
        
        embed.add_field(
            name="📊 How It Works",
            value=(
                f"Add at least {Config.RECOMMENDATION_MIN_ITEMS} items to your watchlist\n"
                "Rate content you've watched\n"
                "The bot learns your preferences and suggests similar content"
            ),
            inline=False
        )
        
        return embed
    
    def _create_admin_help(self) -> discord.Embed:
        """Create admin help embed"""
        embed = create_embed_base(
            title="⚙️ Admin & Configuration Commands",
            description="Configure and manage the bot (Requires permissions)"
        )
        
        embed.add_field(
            name="`/setup`",
            value=(
                "Initial bot setup for your server\n"
                "**Required Permission:** Administrator\n"
                "Sets up the database and default settings"
            ),
            inline=False
        )
        
        embed.add_field(
            name="`/config <setting> [value]`",
            value=(
                "Configure bot settings\n"
                "**Required Permission:** Manage Server\n\n"
                "**Settings:**\n"
                "• `auto_update` - Enable/disable auto-updates\n"
                "• `notification_channel` - Set notification channel\n"
                "• `notification_role` - Set role to ping\n"
                "• `prefix` - Change command prefix\n"
                "• `language` - Set language (en-US, etc.)\n\n"
                "**Example:** `/config notification_channel #movies`"
            ),
            inline=False
        )
        
        embed.add_field(
            name="`/stats`",
            value=(
                "View bot statistics\n"
                "Shows subscription count, active users, and more"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🔄 Auto-Update System",
            value=(
                f"Checks for updates every {Config.UPDATE_INTERVAL_HOURS} hours\n"
                "Sends notifications for:\n"
                "• New episode releases (TV shows)\n"
                "• Movie releases\n"
                "• Upcoming releases (7 days notice)\n"
                "• Status changes"
            ),
            inline=False
        )
        
        return embed
    
    @app_commands.command(name="about", description="Information about the bot")
    async def about(self, interaction: discord.Interaction):
        """Show bot information"""
        embed = create_embed_base(
            title="🎬 About Auto Update Film Bot",
            description=(
                "A comprehensive Discord bot for tracking movies and TV shows "
                "with automatic updates from The Movie Database (TMDB)."
            )
        )
        
        embed.add_field(
            name="✨ Features",
            value=(
                "• Real-time movie and TV show search\n"
                "• Automatic release notifications\n"
                "• Personal watchlist management\n"
                "• AI-powered recommendations\n"
                "• Detailed cast and crew information\n"
                "• Rating and review system"
            ),
            inline=False
        )
        
        embed.add_field(
            name="📊 Statistics",
            value=(
                f"• Servers: {len(self.bot.guilds)}\n"
                f"• Users: {len(self.bot.users):,}\n"
                f"• Commands: {len(self.bot.tree.get_commands())}"
            ),
            inline=True
        )
        
        embed.add_field(
            name="🔧 Technology",
            value=(
                "• Discord.py 2.0+\n"
                "• TMDB API v3\n"
                "• SQLAlchemy (Async)\n"
                "• Python 3.10+"
            ),
            inline=True
        )
        
        embed.add_field(
            name="🔗 Links",
            value=(
                "[Support Server](https://discord.gg/example)\n"
                "[GitHub](https://github.com/example)\n"
                "[TMDB](https://www.themoviedb.org/)"
            ),
            inline=False
        )
        
        embed.set_footer(text=f"Bot Version 1.0.0 • Powered by TMDB")
        
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Help(bot))