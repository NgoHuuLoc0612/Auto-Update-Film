"""
Discover Cog
Advanced content discovery with filters
"""
import logging
from typing import Dict, List, Optional

import discord
from discord import app_commands
from discord.ext import commands

from core.config import Config
from services.tmdb_client import TMDBClient
from utils.helpers import create_embed_base, get_rating_emoji
from utils.views import EmbedPaginationView


class Discover(commands.Cog):
    """Advanced content discovery"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger('FilmBot.Discover')
        self.tmdb = TMDBClient(Config.TMDB_API_KEY)
    
    async def cog_unload(self):
        await self.tmdb.close()
    
    @app_commands.command(name="discover-movies", description="Discover movies with advanced filters")
    @app_commands.describe(
        year="Release year",
        min_rating="Minimum rating (0-10)",
        genre="Genre name"
    )
    async def discover_movies(self, interaction: discord.Interaction,
                             year: Optional[int] = None,
                             min_rating: Optional[float] = None,
                             genre: Optional[str] = None):
        """Discover movies with filters"""
        await interaction.response.defer()
        
        try:
            filters = {}
            
            if year:
                filters['primary_release_year'] = year
            
            if min_rating:
                filters['vote_average.gte'] = min_rating
                filters['vote_count.gte'] = 100  # Ensure enough votes
            
            if genre:
                # Get genre list
                genres_data = await self.tmdb.get_genres_movie()
                genres = genres_data.get('genres', [])
                
                # Find matching genre
                genre_id = None
                for g in genres:
                    if genre.lower() in g['name'].lower():
                        genre_id = g['id']
                        break
                
                if genre_id:
                    filters['with_genres'] = genre_id
            
            filters['sort_by'] = 'popularity.desc'
            
            # Discover
            results = await self.tmdb.discover_movies(**filters)
            movies = results.get('results', [])[:20]
            
            if not movies:
                await interaction.followup.send("❌ No movies found with those filters.", ephemeral=True)
                return
            
            # Create embeds
            embeds = []
            for i in range(0, len(movies), 5):
                chunk = movies[i:i+5]
                
                embed = create_embed_base(
                    title="🔍 Discovered Movies",
                    description=f"Showing {i+1}-{min(i+5, len(movies))} of {len(movies)}"
                )
                
                # Add filter info
                filter_text = []
                if year:
                    filter_text.append(f"Year: {year}")
                if min_rating:
                    filter_text.append(f"Min Rating: {min_rating}")
                if genre:
                    filter_text.append(f"Genre: {genre}")
                
                if filter_text:
                    embed.add_field(
                        name="🔎 Filters Applied",
                        value=" • ".join(filter_text),
                        inline=False
                    )
                
                for movie in chunk:
                    title = movie.get('title', 'Unknown')
                    release_date = movie.get('release_date', 'TBA')
                    year_str = release_date[:4] if release_date else 'TBA'
                    rating = movie.get('vote_average', 0)
                    overview = movie.get('overview', 'No description')[:150]
                    
                    embed.add_field(
                        name=f"🎬 {title} ({year_str})",
                        value=f"{get_rating_emoji(rating)} {rating:.1f}/10\n{overview}...",
                        inline=False
                    )
                
                embeds.append(embed)
            
            if len(embeds) == 1:
                await interaction.followup.send(embed=embeds[0])
            else:
                view = EmbedPaginationView(embeds, timeout=Config.PAGINATION_TIMEOUT)
                await interaction.followup.send(embed=embeds[0], view=view)
            
        except Exception as e:
            self.logger.error(f"Discover movies error: {e}", exc_info=True)
            await interaction.followup.send("❌ Error discovering movies.", ephemeral=True)
    
    @app_commands.command(name="discover-tv", description="Discover TV shows with advanced filters")
    @app_commands.describe(
        year="First air year",
        min_rating="Minimum rating (0-10)",
        genre="Genre name"
    )
    async def discover_tv(self, interaction: discord.Interaction,
                         year: Optional[int] = None,
                         min_rating: Optional[float] = None,
                         genre: Optional[str] = None):
        """Discover TV shows with filters"""
        await interaction.response.defer()
        
        try:
            filters = {}
            
            if year:
                filters['first_air_date_year'] = year
            
            if min_rating:
                filters['vote_average.gte'] = min_rating
                filters['vote_count.gte'] = 100
            
            if genre:
                genres_data = await self.tmdb.get_genres_tv()
                genres = genres_data.get('genres', [])
                
                genre_id = None
                for g in genres:
                    if genre.lower() in g['name'].lower():
                        genre_id = g['id']
                        break
                
                if genre_id:
                    filters['with_genres'] = genre_id
            
            filters['sort_by'] = 'popularity.desc'
            
            results = await self.tmdb.discover_tv(**filters)
            shows = results.get('results', [])[:20]
            
            if not shows:
                await interaction.followup.send("❌ No TV shows found with those filters.", ephemeral=True)
                return
            
            # Create embeds
            embeds = []
            for i in range(0, len(shows), 5):
                chunk = shows[i:i+5]
                
                embed = create_embed_base(
                    title="🔍 Discovered TV Shows",
                    description=f"Showing {i+1}-{min(i+5, len(shows))} of {len(shows)}"
                )
                
                for show in chunk:
                    name = show.get('name', 'Unknown')
                    first_air_date = show.get('first_air_date', 'TBA')
                    year_str = first_air_date[:4] if first_air_date else 'TBA'
                    rating = show.get('vote_average', 0)
                    overview = show.get('overview', 'No description')[:150]
                    
                    embed.add_field(
                        name=f"📺 {name} ({year_str})",
                        value=f"{get_rating_emoji(rating)} {rating:.1f}/10\n{overview}...",
                        inline=False
                    )
                
                embeds.append(embed)
            
            if len(embeds) == 1:
                await interaction.followup.send(embed=embeds[0])
            else:
                view = EmbedPaginationView(embeds, timeout=Config.PAGINATION_TIMEOUT)
                await interaction.followup.send(embed=embeds[0], view=view)
            
        except Exception as e:
            self.logger.error(f"Discover TV error: {e}", exc_info=True)
            await interaction.followup.send("❌ Error discovering TV shows.", ephemeral=True)
    
    @app_commands.command(name="by-genre", description="Browse content by genre")
    @app_commands.describe(
        genre="Genre name",
        media_type="Type of content"
    )
    @app_commands.choices(media_type=[
        app_commands.Choice(name="Movies", value="movie"),
        app_commands.Choice(name="TV Shows", value="tv")
    ])
    async def by_genre(self, interaction: discord.Interaction, genre: str, media_type: str = "movie"):
        """Browse by genre"""
        await interaction.response.defer()
        
        try:
            # Get genres
            if media_type == "movie":
                genres_data = await self.tmdb.get_genres_movie()
            else:
                genres_data = await self.tmdb.get_genres_tv()
            
            genres = genres_data.get('genres', [])
            
            # Find matching genre
            genre_id = None
            genre_name = None
            for g in genres:
                if genre.lower() in g['name'].lower():
                    genre_id = g['id']
                    genre_name = g['name']
                    break
            
            if not genre_id:
                # Show available genres
                genre_list = ", ".join([g['name'] for g in genres[:20]])
                await interaction.followup.send(
                    f"❌ Genre not found. Available genres: {genre_list}",
                    ephemeral=True
                )
                return
            
            # Discover with genre
            if media_type == "movie":
                results = await self.tmdb.discover_movies(
                    with_genres=genre_id,
                    sort_by='popularity.desc'
                )
            else:
                results = await self.tmdb.discover_tv(
                    with_genres=genre_id,
                    sort_by='popularity.desc'
                )
            
            items = results.get('results', [])[:15]
            
            # Create embed
            embed = create_embed_base(
                title=f"🎭 {genre_name} {media_type.title()}s",
                description=f"Popular {genre_name.lower()} content"
            )
            
            for item in items:
                title = item.get('title') or item.get('name', 'Unknown')
                rating = item.get('vote_average', 0)
                
                embed.add_field(
                    name=f"{'🎬' if media_type == 'movie' else '📺'} {title}",
                    value=f"{get_rating_emoji(rating)} {rating:.1f}/10",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"By genre error: {e}", exc_info=True)
            await interaction.followup.send("❌ Error browsing by genre.", ephemeral=True)
    
    @app_commands.command(name="by-year", description="Browse movies/shows by year")
    @app_commands.describe(
        year="Release year",
        media_type="Type of content"
    )
    @app_commands.choices(media_type=[
        app_commands.Choice(name="Movies", value="movie"),
        app_commands.Choice(name="TV Shows", value="tv")
    ])
    async def by_year(self, interaction: discord.Interaction, year: int, media_type: str = "movie"):
        """Browse by year"""
        await interaction.response.defer()
        
        try:
            if media_type == "movie":
                results = await self.tmdb.discover_movies(
                    primary_release_year=year,
                    sort_by='vote_average.desc',
                    **{'vote_count.gte': 100}
                )
            else:
                results = await self.tmdb.discover_tv(
                    first_air_date_year=year,
                    sort_by='vote_average.desc',
                    **{'vote_count.gte': 100}
                )
            
            items = results.get('results', [])[:15]
            
            if not items:
                await interaction.followup.send(f"❌ No {media_type}s found for {year}.", ephemeral=True)
                return
            
            embed = create_embed_base(
                title=f"📅 {year} {media_type.title()}s",
                description=f"Top-rated {media_type}s from {year}"
            )
            
            for item in items:
                title = item.get('title') or item.get('name', 'Unknown')
                rating = item.get('vote_average', 0)
                votes = item.get('vote_count', 0)
                
                embed.add_field(
                    name=f"{'🎬' if media_type == 'movie' else '📺'} {title}",
                    value=f"{get_rating_emoji(rating)} {rating:.1f}/10 ({votes:,} votes)",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"By year error: {e}", exc_info=True)
            await interaction.followup.send("❌ Error browsing by year.", ephemeral=True)
    
    @app_commands.command(name="genres-list", description="List all available genres")
    @app_commands.describe(media_type="Type of content")
    @app_commands.choices(media_type=[
        app_commands.Choice(name="Movies", value="movie"),
        app_commands.Choice(name="TV Shows", value="tv")
    ])
    async def genres_list(self, interaction: discord.Interaction, media_type: str = "movie"):
        """List all genres"""
        await interaction.response.defer()
        
        try:
            if media_type == "movie":
                genres_data = await self.tmdb.get_genres_movie()
            else:
                genres_data = await self.tmdb.get_genres_tv()
            
            genres = genres_data.get('genres', [])
            
            embed = create_embed_base(
                title=f"🎭 {media_type.title()} Genres",
                description=f"All available genres for {media_type}s"
            )
            
            # Group genres
            from utils.helpers import get_genre_emoji
            
            genre_list = []
            for genre in genres:
                emoji = get_genre_emoji(genre['name'])
                genre_list.append(f"{emoji} {genre['name']}")
            
            # Split into columns
            half = len(genre_list) // 2
            
            embed.add_field(
                name="Genres A-M",
                value="\n".join(genre_list[:half]),
                inline=True
            )
            
            embed.add_field(
                name="Genres N-Z",
                value="\n".join(genre_list[half:]),
                inline=True
            )
            
            embed.add_field(
                name="💡 Usage",
                value=f"Use `/by-genre <genre>` or `/discover-{media_type}s genre:<genre>` to browse",
                inline=False
            )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Genres list error: {e}", exc_info=True)
            await interaction.followup.send("❌ Error fetching genres.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Discover(bot))