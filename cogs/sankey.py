"""
Sankey Diagram Cog
Flow visualizations for content analysis
"""
import logging
from collections import defaultdict
from typing import Dict, List

import discord
import numpy as np
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select

from core.config import Config
from core.database import Rating, Subscription, Watchlist
from services.tmdb_client import TMDBClient
from services.visualization import VisualizationService
from utils.helpers import create_embed_base


class SankeyDiagrams(commands.Cog):
    """Sankey diagram visualizations"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger('FilmBot.Sankey')
        self.tmdb = TMDBClient(Config.TMDB_API_KEY)
        self.viz = VisualizationService()
    
    async def cog_unload(self):
        await self.tmdb.close()
    
    @app_commands.command(name="sankey-genres", description="Genre flow visualization")
    async def sankey_genres(self, interaction: discord.Interaction):
        """Visualize genre distribution flow"""
        await interaction.response.defer()
        
        try:
            async with self.bot.db.async_session() as session:
                # Get watchlist items
                result = await session.execute(
                    select(Watchlist).where(Watchlist.guild_id == interaction.guild_id)
                )
                watchlist_items = list(result.scalars().all())
            
            if not watchlist_items:
                await interaction.followup.send("❌ No data available.", ephemeral=True)
                return
            
            # Analyze genre flows
            genre_to_media = defaultdict(lambda: {'movie': 0, 'tv': 0})
            media_counts = {'movie': 0, 'tv': 0}
            
            for item in watchlist_items[:50]:  # Limit to 50 for performance
                try:
                    if item.media_type == 'movie':
                        details = await self.tmdb.get_movie_details(item.tmdb_id)
                        media_counts['movie'] += 1
                    else:
                        details = await self.tmdb.get_tv_details(item.tmdb_id)
                        media_counts['tv'] += 1
                    
                    genres = details.get('genres', [])
                    for genre in genres[:2]:  # Top 2 genres per item
                        genre_name = genre['name']
                        genre_to_media[genre_name][item.media_type] += 1
                
                except Exception as e:
                    continue
            
            if not genre_to_media:
                await interaction.followup.send("❌ Could not analyze genres.", ephemeral=True)
                return
            
            # Prepare Sankey data
            # Source: Genres (0-9), Target: Media Types (10-11)
            source = []
            target = []
            value = []
            labels = []
            
            # Add genre labels
            genre_list = list(genre_to_media.keys())[:10]
            labels.extend(genre_list)
            
            # Add media type labels
            labels.extend(['Movies', 'TV Shows'])
            
            movie_idx = len(genre_list)
            tv_idx = len(genre_list) + 1
            
            # Create flows
            for i, genre in enumerate(genre_list):
                if genre_to_media[genre]['movie'] > 0:
                    source.append(i)
                    target.append(movie_idx)
                    value.append(float(genre_to_media[genre]['movie']))
                
                if genre_to_media[genre]['tv'] > 0:
                    source.append(i)
                    target.append(tv_idx)
                    value.append(float(genre_to_media[genre]['tv']))
            
            # Create Sankey diagram
            chart = self.viz.create_sankey_diagram(source, target, value, labels)
            
            file = discord.File(chart, filename="sankey_genres.png")
            
            embed = create_embed_base(
                title="📊 Genre Distribution Flow",
                description=(
                    f"Analyzing {len(watchlist_items)} items\n"
                    f"🎬 Movies: {media_counts['movie']}\n"
                    f"📺 TV Shows: {media_counts['tv']}"
                )
            )
            
            embed.add_field(
                name="Top Genres",
                value="\n".join([f"• {g}" for g in genre_list[:5]]),
                inline=False
            )
            
            embed.set_image(url="attachment://sankey_genres.png")
            
            await interaction.followup.send(embed=embed, file=file)
            
        except Exception as e:
            self.logger.error(f"Sankey genres error: {e}", exc_info=True)
            await interaction.followup.send("❌ Error creating visualization.", ephemeral=True)
    
    @app_commands.command(name="sankey-ratings", description="Rating flow visualization")
    async def sankey_ratings(self, interaction: discord.Interaction):
        """Visualize rating distribution flow"""
        await interaction.response.defer()
        
        try:
            async with self.bot.db.async_session() as session:
                # Get ratings
                result = await session.execute(
                    select(Rating)
                )
                ratings = list(result.scalars().all())
            
            if not ratings:
                await interaction.followup.send("❌ No ratings available.", ephemeral=True)
                return
            
            # Categorize ratings
            rating_categories = {
                'Excellent (9-10)': 0,
                'Great (7-8.9)': 0,
                'Good (5-6.9)': 0,
                'Poor (0-4.9)': 0
            }
            
            media_type_counts = {'movie': 0, 'tv': 0}
            
            # Source: Rating categories (0-3), Target: Media types (4-5)
            source = []
            target = []
            value = []
            
            for rating in ratings:
                score = rating.score
                media_type = rating.media_type
                
                # Categorize rating
                if score >= 9:
                    cat_idx = 0
                    rating_categories['Excellent (9-10)'] += 1
                elif score >= 7:
                    cat_idx = 1
                    rating_categories['Great (7-8.9)'] += 1
                elif score >= 5:
                    cat_idx = 2
                    rating_categories['Good (5-6.9)'] += 1
                else:
                    cat_idx = 3
                    rating_categories['Poor (0-4.9)'] += 1
                
                # Media type
                media_idx = 4 if media_type == 'movie' else 5
                media_type_counts[media_type] += 1
                
                # Add flow
                source.append(cat_idx)
                target.append(media_idx)
                value.append(1.0)
            
            # Aggregate flows
            flow_map = defaultdict(float)
            for s, t, v in zip(source, target, value):
                flow_map[(s, t)] += v
            
            source = [k[0] for k in flow_map.keys()]
            target = [k[1] for k in flow_map.keys()]
            value = [v for v in flow_map.values()]
            
            labels = [
                'Excellent (9-10)',
                'Great (7-8.9)',
                'Good (5-6.9)',
                'Poor (0-4.9)',
                'Movies',
                'TV Shows'
            ]
            
            # Create Sankey
            chart = self.viz.create_sankey_diagram(source, target, value, labels)
            
            file = discord.File(chart, filename="sankey_ratings.png")
            
            embed = create_embed_base(
                title="⭐ Rating Distribution Flow",
                description=f"Analyzing {len(ratings)} ratings"
            )
            
            embed.add_field(
                name="Distribution",
                value=(
                    f"🌟 Excellent: {rating_categories['Excellent (9-10)']}\n"
                    f"⭐ Great: {rating_categories['Great (7-8.9)']}\n"
                    f"✨ Good: {rating_categories['Good (5-6.9)']}\n"
                    f"💫 Poor: {rating_categories['Poor (0-4.9)']}"
                ),
                inline=True
            )
            
            embed.add_field(
                name="Media Types",
                value=(
                    f"🎬 Movies: {media_type_counts['movie']}\n"
                    f"📺 TV: {media_type_counts['tv']}"
                ),
                inline=True
            )
            
            embed.set_image(url="attachment://sankey_ratings.png")
            
            await interaction.followup.send(embed=embed, file=file)
            
        except Exception as e:
            self.logger.error(f"Sankey ratings error: {e}", exc_info=True)
            await interaction.followup.send("❌ Error creating visualization.", ephemeral=True)
    
    @app_commands.command(name="sankey-watchlist-flow", description="Watchlist status flow")
    async def sankey_watchlist(self, interaction: discord.Interaction):
        """Visualize watchlist item status flow"""
        await interaction.response.defer()
        
        try:
            async with self.bot.db.async_session() as session:
                result = await session.execute(
                    select(Watchlist).where(Watchlist.guild_id == interaction.guild_id)
                )
                watchlist = list(result.scalars().all())
            
            if not watchlist:
                await interaction.followup.send("❌ No watchlist data.", ephemeral=True)
                return
            
            # Analyze flows
            # Source: Media Type (0-1), Target: Status (2-3)
            media_to_status = {
                ('movie', 'unwatched'): 0,
                ('movie', 'watched'): 0,
                ('tv', 'unwatched'): 0,
                ('tv', 'watched'): 0
            }
            
            for item in watchlist:
                status = 'watched' if item.watched else 'unwatched'
                key = (item.media_type, status)
                if key in media_to_status:
                    media_to_status[key] += 1
            
            # Prepare data
            source = []
            target = []
            value = []
            
            # Movies -> Unwatched
            if media_to_status[('movie', 'unwatched')] > 0:
                source.append(0)
                target.append(2)
                value.append(float(media_to_status[('movie', 'unwatched')]))
            
            # Movies -> Watched
            if media_to_status[('movie', 'watched')] > 0:
                source.append(0)
                target.append(3)
                value.append(float(media_to_status[('movie', 'watched')]))
            
            # TV -> Unwatched
            if media_to_status[('tv', 'unwatched')] > 0:
                source.append(1)
                target.append(2)
                value.append(float(media_to_status[('tv', 'unwatched')]))
            
            # TV -> Watched
            if media_to_status[('tv', 'watched')] > 0:
                source.append(1)
                target.append(3)
                value.append(float(media_to_status[('tv', 'watched')]))
            
            labels = ['Movies', 'TV Shows', 'Unwatched', 'Watched']
            
            # Create Sankey
            chart = self.viz.create_sankey_diagram(source, target, value, labels)
            
            file = discord.File(chart, filename="sankey_watchlist.png")
            
            total_unwatched = media_to_status[('movie', 'unwatched')] + media_to_status[('tv', 'unwatched')]
            total_watched = media_to_status[('movie', 'watched')] + media_to_status[('tv', 'watched')]
            
            embed = create_embed_base(
                title="📝 Watchlist Status Flow",
                description=f"Total items: {len(watchlist)}"
            )
            
            embed.add_field(
                name="Status",
                value=(
                    f"📌 Unwatched: {total_unwatched}\n"
                    f"✅ Watched: {total_watched}"
                ),
                inline=True
            )
            
            completion_rate = (total_watched / len(watchlist) * 100) if watchlist else 0
            embed.add_field(
                name="Completion Rate",
                value=f"{completion_rate:.1f}%",
                inline=True
            )
            
            embed.set_image(url="attachment://sankey_watchlist.png")
            
            await interaction.followup.send(embed=embed, file=file)
            
        except Exception as e:
            self.logger.error(f"Sankey watchlist error: {e}", exc_info=True)
            await interaction.followup.send("❌ Error creating visualization.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(SankeyDiagrams(bot))