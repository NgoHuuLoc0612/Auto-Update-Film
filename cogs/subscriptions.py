"""
Subscription management cog
Handles auto-update subscriptions for movies and TV shows
"""
import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from core.config import Config
from services.tmdb_client import TMDBClient
from utils.helpers import create_embed_base, get_media_type_emoji
from utils.views import ConfirmView, MediaSelectView


class Subscriptions(commands.Cog):
    """Manage movie and TV show subscriptions"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger('FilmBot.Subscriptions')
        self.tmdb = TMDBClient(Config.TMDB_API_KEY)
    
    async def cog_unload(self):
        """Cleanup when cog is unloaded"""
        await self.tmdb.close()
    
    @app_commands.command(name="subscribe", description="Subscribe to updates for a movie or TV show")
    @app_commands.describe(query="Name of the movie or TV show")
    async def subscribe(self, interaction: discord.Interaction, query: str):
        """Subscribe to a movie or TV show"""
        await interaction.response.defer()
        
        try:
            # Search for media
            results = await self.tmdb.search_multi(query)
            items = [item for item in results.get('results', []) if item.get('media_type') in ['movie', 'tv']]
            
            if not items:
                embed = create_embed_base(
                    title="🔍 No Results",
                    description=f"No results found for: **{query}**"
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Let user select from results
            view = MediaSelectView(items[:10])
            
            embed = create_embed_base(
                title="📌 Select Media to Subscribe",
                description=f"Found {len(items[:10])} results for: **{query}**\nPlease select one from the dropdown below."
            )
            
            message = await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
            # Wait for selection
            await view.wait()
            
            if not view.selected:
                await message.edit(content="⏱️ Selection timed out.", embed=None, view=None)
                return
            
            selected = view.selected
            media_type = selected.get('media_type')
            tmdb_id = selected.get('id')
            title = selected.get('title') or selected.get('name')
            poster_path = selected.get('poster_path')
            
            # Check if already subscribed
            existing = await self.bot.db.get_subscriptions(interaction.guild_id)
            if any(s.tmdb_id == tmdb_id and s.media_type == media_type for s in existing):
                embed = create_embed_base(
                    title="⚠️ Already Subscribed",
                    description=f"This server is already subscribed to **{title}**."
                )
                await message.edit(embed=embed, view=None)
                return
            
            # Add subscription
            await self.bot.db.add_subscription(
                guild_id=interaction.guild_id,
                tmdb_id=tmdb_id,
                media_type=media_type,
                title=title,
                poster_path=poster_path
            )
            
            # Create confirmation embed
            embed = create_embed_base(
                title=f"✅ Subscribed to {get_media_type_emoji(media_type)} {title}",
                description=f"You will receive notifications when this {media_type} is updated or released."
            )
            
            if poster_path:
                embed.set_thumbnail(url=Config.get_tmdb_image_url(poster_path, 'w185'))
            
            await message.edit(embed=embed, view=None)
            
            self.logger.info(f"Guild {interaction.guild_id} subscribed to {media_type} {tmdb_id}: {title}")
            
        except Exception as e:
            self.logger.error(f"Subscribe error: {e}", exc_info=True)
            embed = create_embed_base(
                title="❌ Error",
                description="An error occurred while subscribing. Please try again."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="unsubscribe", description="Unsubscribe from a movie or TV show")
    @app_commands.describe(query="Name of the movie or TV show")
    async def unsubscribe(self, interaction: discord.Interaction, query: str):
        """Unsubscribe from a movie or TV show"""
        await interaction.response.defer()
        
        try:
            # Get current subscriptions
            subscriptions = await self.bot.db.get_subscriptions(interaction.guild_id)
            
            if not subscriptions:
                embed = create_embed_base(
                    title="📭 No Subscriptions",
                    description="This server has no active subscriptions."
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Filter subscriptions by query
            matching = [s for s in subscriptions if query.lower() in s.title.lower()]
            
            if not matching:
                embed = create_embed_base(
                    title="🔍 No Matches",
                    description=f"No subscriptions found matching: **{query}**"
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # If multiple matches, create selection list
            if len(matching) > 1:
                items = [
                    {
                        'id': s.tmdb_id,
                        'media_type': s.media_type,
                        'title': s.title,
                        'name': s.title,
                        'poster_path': s.poster_path
                    }
                    for s in matching
                ]
                
                view = MediaSelectView(items)
                
                embed = create_embed_base(
                    title="📌 Select Subscription to Remove",
                    description=f"Found {len(matching)} matching subscriptions.\nPlease select one from the dropdown below."
                )
                
                message = await interaction.followup.send(embed=embed, view=view, ephemeral=True)
                await view.wait()
                
                if not view.selected:
                    await message.edit(content="⏱️ Selection timed out.", embed=None, view=None)
                    return
                
                selected = view.selected
                tmdb_id = selected['id']
                media_type = selected['media_type']
                title = selected['title']
            else:
                # Only one match
                subscription = matching[0]
                tmdb_id = subscription.tmdb_id
                media_type = subscription.media_type
                title = subscription.title
                message = None
            
            # Confirm unsubscribe
            confirm_view = ConfirmView()
            confirm_embed = create_embed_base(
                title="⚠️ Confirm Unsubscribe",
                description=f"Are you sure you want to unsubscribe from **{title}**?"
            )
            
            if message:
                await message.edit(embed=confirm_embed, view=confirm_view)
            else:
                message = await interaction.followup.send(embed=confirm_embed, view=confirm_view, ephemeral=True)
            
            await confirm_view.wait()
            
            if not confirm_view.value:
                await message.edit(content="❌ Unsubscribe cancelled.", embed=None, view=None)
                return
            
            # Remove subscription
            success = await self.bot.db.remove_subscription(interaction.guild_id, tmdb_id, media_type)
            
            if success:
                embed = create_embed_base(
                    title=f"✅ Unsubscribed from {title}",
                    description="You will no longer receive notifications for this title."
                )
                await message.edit(embed=embed, view=None)
                self.logger.info(f"Guild {interaction.guild_id} unsubscribed from {media_type} {tmdb_id}: {title}")
            else:
                embed = create_embed_base(
                    title="❌ Error",
                    description="Failed to unsubscribe. The subscription may have already been removed."
                )
                await message.edit(embed=embed, view=None)
            
        except Exception as e:
            self.logger.error(f"Unsubscribe error: {e}", exc_info=True)
            embed = create_embed_base(
                title="❌ Error",
                description="An error occurred while unsubscribing. Please try again."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="subscriptions", description="List all active subscriptions")
    async def list_subscriptions(self, interaction: discord.Interaction):
        """List all subscriptions for the server"""
        await interaction.response.defer()
        
        try:
            subscriptions = await self.bot.db.get_subscriptions(interaction.guild_id)
            
            if not subscriptions:
                embed = create_embed_base(
                    title="📭 No Subscriptions",
                    description="This server has no active subscriptions.\nUse `/subscribe` to add one!"
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Group by media type
            movies = [s for s in subscriptions if s.media_type == 'movie']
            tv_shows = [s for s in subscriptions if s.media_type == 'tv']
            
            embed = create_embed_base(
                title=f"📌 Active Subscriptions ({len(subscriptions)})",
                description=f"Subscriptions for **{interaction.guild.name}**"
            )
            
            if movies:
                movie_list = "\n".join([f"🎬 {m.title}" for m in movies[:10]])
                if len(movies) > 10:
                    movie_list += f"\n... and {len(movies) - 10} more"
                embed.add_field(
                    name=f"Movies ({len(movies)})",
                    value=movie_list,
                    inline=False
                )
            
            if tv_shows:
                tv_list = "\n".join([f"📺 {t.title}" for t in tv_shows[:10]])
                if len(tv_shows) > 10:
                    tv_list += f"\n... and {len(tv_shows) - 10} more"
                embed.add_field(
                    name=f"TV Shows ({len(tv_shows)})",
                    value=tv_list,
                    inline=False
                )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"List subscriptions error: {e}", exc_info=True)
            embed = create_embed_base(
                title="❌ Error",
                description="An error occurred while fetching subscriptions."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Subscriptions(bot))