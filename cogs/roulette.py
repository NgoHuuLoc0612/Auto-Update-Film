"""
Roulette Cog
Random content selector with spinning animation
"""
import asyncio
import logging
import random
from typing import List

import discord
from discord import app_commands
from discord.ext import commands

from core.config import Config
from services.tmdb_client import TMDBClient
from utils.helpers import create_embed_base, format_date, get_media_type_emoji, get_rating_emoji


class Roulette(commands.Cog):
    """Movie and TV show roulette"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger('FilmBot.Roulette')
        self.tmdb = TMDBClient(Config.TMDB_API_KEY)
    
    async def cog_unload(self):
        await self.tmdb.close()
    
    @app_commands.command(name="movie-roulette", description="Spin the wheel for a random movie recommendation")
    @app_commands.describe(
        genre="Optional genre filter",
        min_rating="Minimum rating (0-10)"
    )
    async def movie_roulette(self, interaction: discord.Interaction,
                            genre: str = None,
                            min_rating: float = 6.0):
        """Random movie roulette"""
        await interaction.response.defer()
        
        try:
            # Get movies
            filters = {
                'sort_by': 'popularity.desc',
                'vote_average.gte': min_rating,
                'vote_count.gte': 100
            }
            
            if genre:
                genres_data = await self.tmdb.get_genres_movie()
                genres = genres_data.get('genres', [])
                
                for g in genres:
                    if genre.lower() in g['name'].lower():
                        filters['with_genres'] = g['id']
                        break
            
            # Get multiple pages for variety
            all_movies = []
            for page in range(1, 4):
                results = await self.tmdb.discover_movies(**filters, page=page)
                all_movies.extend(results.get('results', []))
            
            if not all_movies:
                await interaction.followup.send("❌ No movies found with those filters.", ephemeral=True)
                return
            
            # Spinning animation
            spin_embed = create_embed_base(
                title="🎰 Movie Roulette Spinning...",
                description="🎬 🎬 🎬 🎬 🎬"
            )
            
            message = await interaction.followup.send(embed=spin_embed)
            
            # Animate spinning
            spin_frames = [
                "🎬 ⚪ ⚪ ⚪ ⚪",
                "⚪ 🎬 ⚪ ⚪ ⚪",
                "⚪ ⚪ 🎬 ⚪ ⚪",
                "⚪ ⚪ ⚪ 🎬 ⚪",
                "⚪ ⚪ ⚪ ⚪ 🎬",
                "⚪ ⚪ ⚪ 🎬 ⚪",
                "⚪ ⚪ 🎬 ⚪ ⚪",
                "⚪ 🎬 ⚪ ⚪ ⚪",
            ]
            
            for _ in range(3):
                for frame in spin_frames:
                    spin_embed.description = frame
                    await message.edit(embed=spin_embed)
                    await asyncio.sleep(0.3)
            
            # Select random movie
            selected_movie = random.choice(all_movies)
            
            # Get full details
            movie_id = selected_movie['id']
            details = await self.tmdb.get_movie_details(movie_id)
            
            # Create result embed
            title = details.get('title', 'Unknown')
            year = details.get('release_date', '')[:4] if details.get('release_date') else 'TBA'
            rating = details.get('vote_average', 0)
            overview = details.get('overview', 'No description available.')
            
            result_embed = create_embed_base(
                title=f"🎰 Roulette Winner: {title} ({year})",
                description=overview[:500]
            )
            
            result_embed.add_field(
                name=f"{get_rating_emoji(rating)} Rating",
                value=f"{rating:.1f}/10 ({details.get('vote_count', 0):,} votes)",
                inline=True
            )
            
            if details.get('runtime'):
                from utils.helpers import format_runtime
                result_embed.add_field(
                    name="⏱️ Runtime",
                    value=format_runtime(details['runtime']),
                    inline=True
                )
            
            # Genres
            genres = details.get('genres', [])
            if genres:
                from utils.helpers import get_genre_emoji
                genre_text = ", ".join([f"{get_genre_emoji(g['name'])} {g['name']}" for g in genres[:3]])
                result_embed.add_field(
                    name="🎭 Genres",
                    value=genre_text,
                    inline=False
                )
            
            # Poster
            if details.get('poster_path'):
                result_embed.set_image(url=Config.get_tmdb_image_url(details['poster_path'], 'w780'))
            
            # TMDB link
            result_embed.add_field(
                name="🔗 More Info",
                value=f"[View on TMDB](https://www.themoviedb.org/movie/{movie_id})",
                inline=False
            )
            
            await message.edit(embed=result_embed)
            
        except Exception as e:
            self.logger.error(f"Movie roulette error: {e}", exc_info=True)
            await interaction.followup.send("❌ Error running roulette.", ephemeral=True)
    
    @app_commands.command(name="tv-roulette", description="Spin the wheel for a random TV show recommendation")
    @app_commands.describe(
        genre="Optional genre filter",
        min_rating="Minimum rating (0-10)"
    )
    async def tv_roulette(self, interaction: discord.Interaction,
                         genre: str = None,
                         min_rating: float = 6.0):
        """Random TV show roulette"""
        await interaction.response.defer()
        
        try:
            filters = {
                'sort_by': 'popularity.desc',
                'vote_average.gte': min_rating,
                'vote_count.gte': 100
            }
            
            if genre:
                genres_data = await self.tmdb.get_genres_tv()
                genres = genres_data.get('genres', [])
                
                for g in genres:
                    if genre.lower() in g['name'].lower():
                        filters['with_genres'] = g['id']
                        break
            
            # Get multiple pages
            all_shows = []
            for page in range(1, 4):
                results = await self.tmdb.discover_tv(**filters, page=page)
                all_shows.extend(results.get('results', []))
            
            if not all_shows:
                await interaction.followup.send("❌ No TV shows found with those filters.", ephemeral=True)
                return
            
            # Spinning animation
            spin_embed = create_embed_base(
                title="🎰 TV Roulette Spinning...",
                description="📺 📺 📺 📺 📺"
            )
            
            message = await interaction.followup.send(embed=spin_embed)
            
            # Animate
            spin_frames = [
                "📺 ⚪ ⚪ ⚪ ⚪",
                "⚪ 📺 ⚪ ⚪ ⚪",
                "⚪ ⚪ 📺 ⚪ ⚪",
                "⚪ ⚪ ⚪ 📺 ⚪",
                "⚪ ⚪ ⚪ ⚪ 📺",
            ]
            
            for _ in range(4):
                for frame in spin_frames:
                    spin_embed.description = frame
                    await message.edit(embed=spin_embed)
                    await asyncio.sleep(0.25)
            
            # Select random show
            selected_show = random.choice(all_shows)
            
            # Get details
            show_id = selected_show['id']
            details = await self.tmdb.get_tv_details(show_id)
            
            title = details.get('name', 'Unknown')
            year = details.get('first_air_date', '')[:4] if details.get('first_air_date') else 'TBA'
            rating = details.get('vote_average', 0)
            overview = details.get('overview', 'No description available.')
            
            result_embed = create_embed_base(
                title=f"🎰 Roulette Winner: {title} ({year})",
                description=overview[:500]
            )
            
            result_embed.add_field(
                name=f"{get_rating_emoji(rating)} Rating",
                value=f"{rating:.1f}/10",
                inline=True
            )
            
            result_embed.add_field(
                name="📊 Seasons",
                value=f"{details.get('number_of_seasons', 0)} seasons\n{details.get('number_of_episodes', 0)} episodes",
                inline=True
            )
            
            result_embed.add_field(
                name="📡 Status",
                value=details.get('status', 'Unknown'),
                inline=True
            )
            
            if details.get('poster_path'):
                result_embed.set_image(url=Config.get_tmdb_image_url(details['poster_path'], 'w780'))
            
            result_embed.add_field(
                name="🔗 More Info",
                value=f"[View on TMDB](https://www.themoviedb.org/tv/{show_id})",
                inline=False
            )
            
            await message.edit(embed=result_embed)
            
        except Exception as e:
            self.logger.error(f"TV roulette error: {e}", exc_info=True)
            await interaction.followup.send("❌ Error running roulette.", ephemeral=True)
    
    @app_commands.command(name="watchlist-roulette", description="Pick a random item from your watchlist")
    async def watchlist_roulette(self, interaction: discord.Interaction):
        """Random watchlist item selector"""
        await interaction.response.defer()
        
        try:
            from sqlalchemy import select
            from core.database import Watchlist
            
            async with self.bot.db.async_session() as session:
                result = await session.execute(
                    select(Watchlist).where(
                        Watchlist.guild_id == interaction.guild_id,
                        Watchlist.user_id == interaction.user.id,
                        Watchlist.watched == False
                    )
                )
                watchlist = list(result.scalars().all())
            
            if not watchlist:
                await interaction.followup.send(
                    "❌ Your watchlist is empty or everything is watched!",
                    ephemeral=True
                )
                return
            
            # Spinning animation
            spin_embed = create_embed_base(
                title="🎰 Watchlist Roulette Spinning...",
                description="🎬 📺 🎬 📺 🎬"
            )
            
            message = await interaction.followup.send(embed=spin_embed)
            
            # Show random items while spinning
            for _ in range(10):
                random_item = random.choice(watchlist)
                spin_embed.description = f"🎲 {random_item.title}..."
                await message.edit(embed=spin_embed)
                await asyncio.sleep(0.3)
            
            # Final selection
            selected = random.choice(watchlist)
            
            # Get details from TMDB
            if selected.media_type == 'movie':
                details = await self.tmdb.get_movie_details(selected.tmdb_id)
                title = details.get('title')
                year = details.get('release_date', '')[:4]
                url_type = 'movie'
            else:
                details = await self.tmdb.get_tv_details(selected.tmdb_id)
                title = details.get('name')
                year = details.get('first_air_date', '')[:4]
                url_type = 'tv'
            
            rating = details.get('vote_average', 0)
            overview = details.get('overview', 'No description available.')
            
            result_embed = create_embed_base(
                title=f"🎰 You Should Watch: {title} ({year})",
                description=overview[:500]
            )
            
            result_embed.add_field(
                name=f"{get_rating_emoji(rating)} Rating",
                value=f"{rating:.1f}/10",
                inline=True
            )
            
            result_embed.add_field(
                name="📝 From Your Watchlist",
                value=f"Added {format_date(selected.added_at.strftime('%Y-%m-%d'))}",
                inline=True
            )
            
            if selected.poster_path:
                result_embed.set_image(url=Config.get_tmdb_image_url(selected.poster_path, 'w780'))
            
            result_embed.add_field(
                name="🔗 More Info",
                value=f"[View on TMDB](https://www.themoviedb.org/{url_type}/{selected.tmdb_id})",
                inline=False
            )
            
            await message.edit(embed=result_embed)
            
        except Exception as e:
            self.logger.error(f"Watchlist roulette error: {e}", exc_info=True)
            await interaction.followup.send("❌ Error running watchlist roulette.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Roulette(bot))