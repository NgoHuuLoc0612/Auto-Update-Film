"""
Recommendations cog
AI-powered and collaborative filtering recommendations
"""
import logging
from collections import Counter
from typing import List

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select

from core.config import Config
from core.database import Rating, Watchlist
from services.tmdb_client import TMDBClient
from utils.helpers import create_embed_base, get_media_type_emoji, truncate_text
from utils.views import EmbedPaginationView


class Recommendations(commands.Cog):
    """Get personalized movie and TV show recommendations"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger('FilmBot.Recommendations')
        self.tmdb = TMDBClient(Config.TMDB_API_KEY)
    
    async def cog_unload(self):
        await self.tmdb.close()
    
    async def _get_user_preferences(self, guild_id: int, user_id: int) -> dict:
        """Analyze user's watchlist and ratings to determine preferences"""
        async with self.bot.db.async_session() as session:
            # Get user's watchlist
            result = await session.execute(
                select(Watchlist).where(
                    Watchlist.guild_id == guild_id,
                    Watchlist.user_id == user_id
                )
            )
            watchlist = list(result.scalars().all())
            
            # Get user's ratings
            result = await session.execute(
                select(Rating).where(
                    Rating.user_id == user_id
                )
            )
            ratings = list(result.scalars().all())
        
        preferences = {
            'genres': [],
            'high_rated_ids': [],
            'media_types': [],
            'total_items': len(watchlist)
        }
        
        # Collect highly rated items
        for rating in ratings:
            if rating.score >= 7.0:
                preferences['high_rated_ids'].append((rating.tmdb_id, rating.media_type))
        
        # Collect media types
        for item in watchlist:
            preferences['media_types'].append(item.media_type)
        
        return preferences
    
    @app_commands.command(name="recommend", description="Get personalized recommendations")
    @app_commands.describe(
        based_on="Base recommendations on",
        media_type="Type of media to recommend"
    )
    @app_commands.choices(
        based_on=[
            app_commands.Choice(name="My Watchlist", value="watchlist"),
            app_commands.Choice(name="Trending Now", value="trending"),
            app_commands.Choice(name="Popular", value="popular"),
            app_commands.Choice(name="Top Rated", value="top_rated")
        ],
        media_type=[
            app_commands.Choice(name="Both", value="both"),
            app_commands.Choice(name="Movies", value="movie"),
            app_commands.Choice(name="TV Shows", value="tv")
        ]
    )
    async def recommend(self, interaction: discord.Interaction, 
                       based_on: str = "watchlist",
                       media_type: str = "both"):
        """Get personalized recommendations"""
        await interaction.response.defer()
        
        try:
            recommendations = []
            
            if based_on == "watchlist":
                # Get personalized recommendations based on user's watchlist
                preferences = await self._get_user_preferences(
                    interaction.guild_id,
                    interaction.user.id
                )
                
                if preferences['total_items'] < Config.RECOMMENDATION_MIN_ITEMS:
                    embed = create_embed_base(
                        title="📝 Not Enough Data",
                        description=(
                            f"Add at least {Config.RECOMMENDATION_MIN_ITEMS} items to your watchlist "
                            "to get personalized recommendations.\n\n"
                            f"Current items: {preferences['total_items']}\n"
                            f"Use `/watchlist-add` to add more items!"
                        )
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
                
                # Get recommendations based on highly rated items
                for tmdb_id, item_type in preferences['high_rated_ids'][:5]:
                    try:
                        if item_type == 'movie':
                            similar = await self.tmdb.get_similar_movies(tmdb_id)
                        else:
                            similar = await self.tmdb.get_similar_tv(tmdb_id)
                        
                        recommendations.extend(similar.get('results', [])[:3])
                    except:
                        continue
                
                # Remove duplicates
                seen = set()
                unique_recommendations = []
                for item in recommendations:
                    item_id = item.get('id')
                    if item_id not in seen:
                        seen.add(item_id)
                        unique_recommendations.append(item)
                
                recommendations = unique_recommendations[:10]
            
            elif based_on == "trending":
                result = await self.tmdb.get_trending('all', 'week')
                recommendations = result.get('results', [])[:10]
            
            elif based_on == "popular":
                if media_type == "both" or media_type == "movie":
                    result = await self.tmdb.get_popular_movies()
                    recommendations.extend(result.get('results', [])[:5])
                
                if media_type == "both" or media_type == "tv":
                    result = await self.tmdb.get_popular_tv()
                    recommendations.extend(result.get('results', [])[:5])
            
            elif based_on == "top_rated":
                if media_type == "both" or media_type == "movie":
                    result = await self.tmdb.get_top_rated_movies()
                    recommendations.extend(result.get('results', [])[:5])
                
                if media_type == "both" or media_type == "tv":
                    result = await self.tmdb.get_top_rated_tv()
                    recommendations.extend(result.get('results', [])[:5])
            
            # Filter by media type if specified
            if media_type != "both":
                recommendations = [
                    r for r in recommendations 
                    if r.get('media_type', media_type) == media_type
                ]
            
            if not recommendations:
                embed = create_embed_base(
                    title="🔍 No Recommendations",
                    description="Could not generate recommendations at this time."
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Create embeds
            embeds = []
            for item in recommendations[:10]:
                item_type = item.get('media_type', media_type)
                title = item.get('title') or item.get('name', 'Unknown')
                overview = truncate_text(item.get('overview', 'No description available.'), 400)
                
                embed = create_embed_base(
                    title=f"{get_media_type_emoji(item_type)} {title}",
                    description=overview
                )
                
                # Rating
                rating = item.get('vote_average', 0)
                if rating:
                    from utils.helpers import get_rating_emoji
                    embed.add_field(
                        name=f"{get_rating_emoji(rating)} Rating",
                        value=f"{rating:.1f}/10",
                        inline=True
                    )
                
                # Release date
                release_date = item.get('release_date') or item.get('first_air_date')
                if release_date:
                    from utils.helpers import format_date
                    embed.add_field(
                        name="📅 Release",
                        value=format_date(release_date),
                        inline=True
                    )
                
                # Poster
                poster_path = item.get('poster_path')
                if poster_path:
                    embed.set_thumbnail(
                        url=Config.get_tmdb_image_url(poster_path, 'w342')
                    )
                
                # Backdrop
                backdrop_path = item.get('backdrop_path')
                if backdrop_path:
                    embed.set_image(
                        url=Config.get_tmdb_image_url(backdrop_path, 'w780')
                    )
                
                embeds.append(embed)
            
            # Send recommendations
            if embeds:
                view = EmbedPaginationView(embeds, timeout=Config.PAGINATION_TIMEOUT)
                await interaction.followup.send(
                    content=f"🎬 **Recommendations based on: {based_on.replace('_', ' ').title()}**",
                    embed=embeds[0],
                    view=view
                )
            
            self.logger.info(
                f"Generated {len(embeds)} recommendations for user {interaction.user.id} "
                f"(based on: {based_on}, type: {media_type})"
            )
            
        except Exception as e:
            self.logger.error(f"Recommendation error: {e}", exc_info=True)
            embed = create_embed_base(
                title="❌ Error",
                description="An error occurred while generating recommendations."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="similar", description="Find similar movies or TV shows")
    @app_commands.describe(query="Name of the movie or TV show")
    async def similar(self, interaction: discord.Interaction, query: str):
        """Find similar media"""
        await interaction.response.defer()
        
        try:
            # Search for the media
            results = await self.tmdb.search_multi(query)
            items = [item for item in results.get('results', []) if item.get('media_type') in ['movie', 'tv']]
            
            if not items:
                embed = create_embed_base(
                    title="🔍 No Results",
                    description=f"No results found for: **{query}**"
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Use first result
            item = items[0]
            media_type = item.get('media_type')
            tmdb_id = item.get('id')
            title = item.get('title') or item.get('name')
            
            # Get similar items
            if media_type == 'movie':
                similar_results = await self.tmdb.get_similar_movies(tmdb_id)
            else:
                similar_results = await self.tmdb.get_similar_tv(tmdb_id)
            
            similar_items = similar_results.get('results', [])[:10]
            
            if not similar_items:
                embed = create_embed_base(
                    title="🔍 No Similar Items",
                    description=f"No similar items found for **{title}**."
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Create embeds
            embeds = []
            for similar in similar_items:
                similar_title = similar.get('title') or similar.get('name', 'Unknown')
                overview = truncate_text(similar.get('overview', 'No description available.'), 400)
                
                embed = create_embed_base(
                    title=f"{get_media_type_emoji(media_type)} {similar_title}",
                    description=overview
                )
                
                rating = similar.get('vote_average', 0)
                if rating:
                    from utils.helpers import get_rating_emoji
                    embed.add_field(
                        name=f"{get_rating_emoji(rating)} Rating",
                        value=f"{rating:.1f}/10",
                        inline=True
                    )
                
                poster_path = similar.get('poster_path')
                if poster_path:
                    embed.set_thumbnail(
                        url=Config.get_tmdb_image_url(poster_path, 'w342')
                    )
                
                embeds.append(embed)
            
            # Send results
            view = EmbedPaginationView(embeds, timeout=Config.PAGINATION_TIMEOUT)
            await interaction.followup.send(
                content=f"🎬 **Similar to {title}:**",
                embed=embeds[0],
                view=view
            )
            
        except Exception as e:
            self.logger.error(f"Similar search error: {e}", exc_info=True)
            embed = create_embed_base(
                title="❌ Error",
                description="An error occurred while searching for similar items."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Recommendations(bot))