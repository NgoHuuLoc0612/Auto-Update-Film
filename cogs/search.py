"""
Search commands cog
Handles movie and TV show search functionality
"""
import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from core.config import Config
from services.tmdb_client import TMDBClient
from utils.helpers import (create_embed_base, format_date, format_list,
                           get_genre_emoji, get_media_type_emoji,
                           get_rating_emoji, truncate_text)
from utils.views import EmbedPaginationView, MediaSelectView


class Search(commands.Cog):
    """Search for movies, TV shows, and people"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger('FilmBot.Search')
        self.tmdb = TMDBClient(Config.TMDB_API_KEY)
    
    async def cog_unload(self):
        """Cleanup when cog is unloaded"""
        await self.tmdb.close()
    
    def create_media_embed(self, media: dict, media_type: str = None) -> discord.Embed:
        """Create detailed embed for media item"""
        media_type = media_type or media.get('media_type', 'unknown')
        
        # Get title
        title = media.get('title') or media.get('name', 'Unknown')
        
        # Get release date
        release_date = media.get('release_date') or media.get('first_air_date', '')
        year = release_date[:4] if release_date else 'N/A'
        
        # Create embed
        embed = create_embed_base(
            title=f"{get_media_type_emoji(media_type)} {title} ({year})",
            description=truncate_text(media.get('overview', 'No description available.'), 400)
        )
        
        # Add rating
        rating = media.get('vote_average', 0)
        if rating:
            embed.add_field(
                name=f"{get_rating_emoji(rating)} Rating",
                value=f"{rating:.1f}/10 ({media.get('vote_count', 0):,} votes)",
                inline=True
            )
        
        # Add release date
        if release_date:
            embed.add_field(
                name="📅 Release Date",
                value=format_date(release_date),
                inline=True
            )
        
        # Add genres
        if 'genre_ids' in media or 'genres' in media:
            genres = media.get('genres', [])
            if genres:
                genre_text = ", ".join([f"{get_genre_emoji(g['name'])} {g['name']}" for g in genres[:3]])
                embed.add_field(
                    name="🎭 Genres",
                    value=genre_text,
                    inline=False
                )
        
        # Add poster
        poster_path = media.get('poster_path')
        if poster_path:
            embed.set_thumbnail(url=Config.get_tmdb_image_url(poster_path, Config.EMBED_THUMBNAIL_SIZE))
        
        # Add backdrop
        backdrop_path = media.get('backdrop_path')
        if backdrop_path:
            embed.set_image(url=Config.get_tmdb_image_url(backdrop_path, Config.EMBED_BACKDROP_SIZE))
        
        # Add TMDB link
        tmdb_id = media.get('id')
        if tmdb_id:
            embed.add_field(
                name="🔗 Links",
                value=f"[View on TMDB](https://www.themoviedb.org/{media_type}/{tmdb_id})",
                inline=False
            )
        
        return embed
    
    @app_commands.command(name="search", description="Search for movies and TV shows")
    @app_commands.describe(
        query="Search query",
        media_type="Type of media to search for"
    )
    @app_commands.choices(media_type=[
        app_commands.Choice(name="All", value="multi"),
        app_commands.Choice(name="Movies", value="movie"),
        app_commands.Choice(name="TV Shows", value="tv")
    ])
    async def search(self, interaction: discord.Interaction, query: str, media_type: str = "multi"):
        """Search for movies and TV shows"""
        await interaction.response.defer()
        
        try:
            # Perform search
            if media_type == "multi":
                results = await self.tmdb.search_multi(query)
            elif media_type == "movie":
                results = await self.tmdb.search_movie(query)
            else:
                results = await self.tmdb.search_tv(query)
            
            items = results.get('results', [])
            
            if not items:
                embed = create_embed_base(
                    title="🔍 No Results",
                    description=f"No results found for: **{query}**"
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Filter out people if multi search
            if media_type == "multi":
                items = [item for item in items if item.get('media_type') in ['movie', 'tv']]
            
            # Limit results
            items = items[:Config.SEARCH_RESULTS_LIMIT]
            
            # Create embeds for each result
            embeds = []
            for item in items:
                embed = self.create_media_embed(item)
                embeds.append(embed)
            
            # Send paginated results
            if len(embeds) == 1:
                await interaction.followup.send(embed=embeds[0])
            else:
                view = EmbedPaginationView(embeds, timeout=Config.PAGINATION_TIMEOUT)
                await interaction.followup.send(embed=embeds[0], view=view)
            
            self.logger.info(f"Search performed by {interaction.user}: '{query}' ({len(items)} results)")
            
        except Exception as e:
            self.logger.error(f"Search error: {e}", exc_info=True)
            embed = create_embed_base(
                title="❌ Error",
                description="An error occurred while searching. Please try again."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="movie", description="Get detailed information about a movie")
    @app_commands.describe(movie_id="TMDB movie ID")
    async def movie_details(self, interaction: discord.Interaction, movie_id: int):
        """Get detailed movie information"""
        await interaction.response.defer()
        
        try:
            movie = await self.tmdb.get_movie_details(movie_id)
            
            title = movie.get('title', 'Unknown')
            year = movie.get('release_date', '')[:4] if movie.get('release_date') else 'N/A'
            
            embed = create_embed_base(
                title=f"🎬 {title} ({year})",
                description=truncate_text(movie.get('overview', 'No description available.'), 600)
            )
            
            # Rating
            rating = movie.get('vote_average', 0)
            if rating:
                embed.add_field(
                    name=f"{get_rating_emoji(rating)} Rating",
                    value=f"{rating:.1f}/10 ({movie.get('vote_count', 0):,} votes)",
                    inline=True
                )
            
            # Runtime
            runtime = movie.get('runtime')
            if runtime:
                from utils.helpers import format_runtime
                embed.add_field(
                    name="⏱️ Runtime",
                    value=format_runtime(runtime),
                    inline=True
                )
            
            # Budget & Revenue
            budget = movie.get('budget', 0)
            revenue = movie.get('revenue', 0)
            if budget or revenue:
                from utils.helpers import format_money
                embed.add_field(
                    name="💰 Budget",
                    value=format_money(budget),
                    inline=True
                )
                embed.add_field(
                    name="💵 Revenue",
                    value=format_money(revenue),
                    inline=True
                )
            
            # Genres
            genres = movie.get('genres', [])
            if genres:
                genre_text = format_list([f"{get_genre_emoji(g['name'])} {g['name']}" for g in genres])
                embed.add_field(
                    name="🎭 Genres",
                    value=genre_text,
                    inline=False
                )
            
            # Cast
            credits = movie.get('credits', {})
            cast = credits.get('cast', [])[:5]
            if cast:
                cast_text = format_list([f"{p['name']} as {p['character']}" for p in cast if p.get('character')])
                embed.add_field(
                    name="👥 Cast",
                    value=cast_text,
                    inline=False
                )
            
            # Directors
            crew = credits.get('crew', [])
            directors = [p['name'] for p in crew if p.get('job') == 'Director']
            if directors:
                embed.add_field(
                    name="🎬 Director(s)",
                    value=format_list(directors),
                    inline=False
                )
            
            # Images
            if movie.get('poster_path'):
                embed.set_thumbnail(url=Config.get_tmdb_image_url(movie['poster_path'], Config.EMBED_THUMBNAIL_SIZE))
            
            if movie.get('backdrop_path'):
                embed.set_image(url=Config.get_tmdb_image_url(movie['backdrop_path'], Config.EMBED_BACKDROP_SIZE))
            
            # Links
            embed.add_field(
                name="🔗 Links",
                value=f"[TMDB](https://www.themoviedb.org/movie/{movie_id})",
                inline=False
            )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Movie details error: {e}", exc_info=True)
            embed = create_embed_base(
                title="❌ Error",
                description="Could not fetch movie details. Please check the ID and try again."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="trending", description="Get trending movies and TV shows")
    @app_commands.describe(
        media_type="Type of media",
        time_window="Time window for trending"
    )
    @app_commands.choices(
        media_type=[
            app_commands.Choice(name="All", value="all"),
            app_commands.Choice(name="Movies", value="movie"),
            app_commands.Choice(name="TV Shows", value="tv")
        ],
        time_window=[
            app_commands.Choice(name="Today", value="day"),
            app_commands.Choice(name="This Week", value="week")
        ]
    )
    async def trending(self, interaction: discord.Interaction, 
                      media_type: str = "all", time_window: str = "week"):
        """Get trending media"""
        await interaction.response.defer()
        
        try:
            results = await self.tmdb.get_trending(media_type, time_window)
            items = results.get('results', [])[:10]
            
            embeds = []
            for item in items:
                embed = self.create_media_embed(item)
                embeds.append(embed)
            
            if embeds:
                view = EmbedPaginationView(embeds, timeout=Config.PAGINATION_TIMEOUT)
                await interaction.followup.send(
                    content=f"📈 **Trending {media_type.title()} - {time_window.title()}**",
                    embed=embeds[0],
                    view=view
                )
            else:
                await interaction.followup.send("No trending items found.")
            
        except Exception as e:
            self.logger.error(f"Trending error: {e}", exc_info=True)
            await interaction.followup.send("❌ Error fetching trending items.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Search(bot))