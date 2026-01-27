"""
Collections Cog
Movie collections, franchises, and series management
"""
import logging
from typing import Dict, List

import discord
from discord import app_commands
from discord.ext import commands

from core.config import Config
from services.tmdb_client import TMDBClient
from utils.helpers import create_embed_base, format_money, get_rating_emoji
from utils.views import EmbedPaginationView


class Collections(commands.Cog):
    """Movie collections and franchises"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger('FilmBot.Collections')
        self.tmdb = TMDBClient(Config.TMDB_API_KEY)
    
    async def cog_unload(self):
        await self.tmdb.close()
    
    @app_commands.command(name="collection", description="View movie collection/franchise")
    @app_commands.describe(query="Movie name or collection")
    async def collection(self, interaction: discord.Interaction, query: str):
        """Get collection information"""
        await interaction.response.defer()
        
        try:
            # Search for movie
            results = await self.tmdb.search_movie(query)
            movies = results.get('results', [])
            
            if not movies:
                await interaction.followup.send("❌ No movies found.", ephemeral=True)
                return
            
            # Get first movie details
            movie = movies[0]
            movie_id = movie.get('id')
            details = await self.tmdb.get_movie_details(movie_id)
            
            # Check if part of collection
            collection_data = details.get('belongs_to_collection')
            
            if not collection_data:
                await interaction.followup.send(
                    f"❌ **{details.get('title')}** is not part of a collection.",
                    ephemeral=True
                )
                return
            
            collection_id = collection_data.get('id')
            
            # Get collection details
            collection = await self.tmdb.get_collection_details(collection_id)
            
            collection_name = collection.get('name', 'Unknown Collection')
            overview = collection.get('overview', 'No description available.')
            parts = collection.get('parts', [])
            
            # Sort by release date
            parts.sort(key=lambda x: x.get('release_date', '9999'))
            
            # Calculate total revenue
            total_revenue = 0
            total_budget = 0
            
            # Create main embed
            embed = create_embed_base(
                title=f"🎬 {collection_name}",
                description=overview[:500]
            )
            
            embed.add_field(
                name="📊 Collection Stats",
                value=f"Total Movies: {len(parts)}",
                inline=False
            )
            
            # List all movies
            movies_list = []
            for i, part in enumerate(parts, 1):
                title = part.get('title', 'Unknown')
                release_date = part.get('release_date', 'TBA')
                year = release_date[:4] if release_date and release_date != 'TBA' else 'TBA'
                rating = part.get('vote_average', 0)
                
                movies_list.append(f"{i}. **{title}** ({year}) {get_rating_emoji(rating)} {rating:.1f}/10")
            
            if movies_list:
                # Split into chunks if too long
                movies_text = "\n".join(movies_list)
                if len(movies_text) > 1000:
                    movies_text = "\n".join(movies_list[:10]) + f"\n... and {len(parts) - 10} more"
                
                embed.add_field(
                    name="🎞️ Movies in Collection",
                    value=movies_text,
                    inline=False
                )
            
            # Poster/Backdrop
            poster_path = collection.get('poster_path')
            if poster_path:
                embed.set_image(url=Config.get_tmdb_image_url(poster_path, 'w780'))
            
            backdrop_path = collection.get('backdrop_path')
            if backdrop_path and not poster_path:
                embed.set_image(url=Config.get_tmdb_image_url(backdrop_path, 'w1280'))
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Collection error: {e}", exc_info=True)
            await interaction.followup.send("❌ Error fetching collection.", ephemeral=True)
    
    @app_commands.command(name="franchise-stats", description="Get detailed statistics for a movie franchise")
    @app_commands.describe(query="Movie or franchise name")
    async def franchise_stats(self, interaction: discord.Interaction, query: str):
        """Get franchise statistics"""
        await interaction.response.defer()
        
        try:
            # Search and get collection
            results = await self.tmdb.search_movie(query)
            if not results.get('results'):
                await interaction.followup.send("❌ No movies found.", ephemeral=True)
                return
            
            movie_id = results['results'][0]['id']
            details = await self.tmdb.get_movie_details(movie_id)
            
            collection_data = details.get('belongs_to_collection')
            if not collection_data:
                await interaction.followup.send("❌ Not part of a collection.", ephemeral=True)
                return
            
            collection_id = collection_data.get('id')
            collection = await self.tmdb.get_collection_details(collection_id)
            
            parts = collection.get('parts', [])
            
            # Calculate statistics
            total_revenue = 0
            total_budget = 0
            ratings = []
            total_votes = 0
            
            for part in parts:
                part_id = part.get('id')
                try:
                    part_details = await self.tmdb.get_movie_details(part_id)
                    
                    revenue = part_details.get('revenue', 0)
                    budget = part_details.get('budget', 0)
                    rating = part_details.get('vote_average', 0)
                    votes = part_details.get('vote_count', 0)
                    
                    if revenue:
                        total_revenue += revenue
                    if budget:
                        total_budget += budget
                    if rating:
                        ratings.append(rating)
                    total_votes += votes
                    
                except:
                    continue
            
            # Create statistics embed
            embed = create_embed_base(
                title=f"📊 Franchise Statistics - {collection.get('name')}",
                description=f"Analysis of {len(parts)} movies"
            )
            
            # Financial stats
            if total_revenue > 0:
                embed.add_field(
                    name="💰 Total Revenue",
                    value=format_money(total_revenue),
                    inline=True
                )
            
            if total_budget > 0:
                embed.add_field(
                    name="💵 Total Budget",
                    value=format_money(total_budget),
                    inline=True
                )
            
            if total_revenue > 0 and total_budget > 0:
                profit = total_revenue - total_budget
                roi = ((total_revenue - total_budget) / total_budget * 100) if total_budget > 0 else 0
                embed.add_field(
                    name="💹 Profit & ROI",
                    value=f"{format_money(profit)}\n{roi:.1f}% ROI",
                    inline=True
                )
            
            # Rating stats
            if ratings:
                avg_rating = sum(ratings) / len(ratings)
                highest_rating = max(ratings)
                lowest_rating = min(ratings)
                
                embed.add_field(
                    name="⭐ Average Rating",
                    value=f"{get_rating_emoji(avg_rating)} {avg_rating:.2f}/10",
                    inline=True
                )
                
                embed.add_field(
                    name="📈 Rating Range",
                    value=f"High: {highest_rating:.1f}\nLow: {lowest_rating:.1f}",
                    inline=True
                )
            
            embed.add_field(
                name="📊 Total Votes",
                value=f"{total_votes:,}",
                inline=True
            )
            
            # Best & Worst
            if parts:
                sorted_by_rating = sorted(parts, key=lambda x: x.get('vote_average', 0), reverse=True)
                
                best = sorted_by_rating[0]
                worst = sorted_by_rating[-1]
                
                embed.add_field(
                    name="🏆 Highest Rated",
                    value=f"{best.get('title')} ({best.get('vote_average', 0):.1f}/10)",
                    inline=False
                )
                
                embed.add_field(
                    name="💔 Lowest Rated",
                    value=f"{worst.get('title')} ({worst.get('vote_average', 0):.1f}/10)",
                    inline=False
                )
            
            poster_path = collection.get('poster_path')
            if poster_path:
                embed.set_thumbnail(url=Config.get_tmdb_image_url(poster_path, 'w342'))
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Franchise stats error: {e}", exc_info=True)
            await interaction.followup.send("❌ Error calculating statistics.", ephemeral=True)
    
    @app_commands.command(name="series", description="View TV series seasons and episodes")
    @app_commands.describe(query="TV show name")
    async def series(self, interaction: discord.Interaction, query: str):
        """Get TV series information"""
        await interaction.response.defer()
        
        try:
            # Search for TV show
            results = await self.tmdb.search_tv(query)
            shows = results.get('results', [])
            
            if not shows:
                await interaction.followup.send("❌ No TV shows found.", ephemeral=True)
                return
            
            show = shows[0]
            show_id = show.get('id')
            
            # Get details
            details = await self.tmdb.get_tv_details(show_id)
            
            show_name = details.get('name', 'Unknown')
            seasons = details.get('seasons', [])
            number_of_seasons = details.get('number_of_seasons', 0)
            number_of_episodes = details.get('number_of_episodes', 0)
            status = details.get('status', 'Unknown')
            
            embed = create_embed_base(
                title=f"📺 {show_name}",
                description=details.get('overview', 'No description')[:500]
            )
            
            embed.add_field(
                name="📊 Series Info",
                value=f"Seasons: {number_of_seasons}\nEpisodes: {number_of_episodes}\nStatus: {status}",
                inline=False
            )
            
            # List seasons
            seasons_list = []
            for season in seasons:
                season_number = season.get('season_number')
                season_name = season.get('name', f'Season {season_number}')
                episode_count = season.get('episode_count', 0)
                air_date = season.get('air_date', 'TBA')
                year = air_date[:4] if air_date and air_date != 'TBA' else 'TBA'
                
                seasons_list.append(f"**{season_name}** ({year}) - {episode_count} episodes")
            
            if seasons_list:
                seasons_text = "\n".join(seasons_list[:15])
                if len(seasons) > 15:
                    seasons_text += f"\n... and {len(seasons) - 15} more"
                
                embed.add_field(
                    name="🎬 Seasons",
                    value=seasons_text,
                    inline=False
                )
            
            # Next episode
            next_episode = details.get('next_episode_to_air')
            if next_episode:
                ep_name = next_episode.get('name', 'Unknown')
                ep_num = f"S{next_episode.get('season_number')}E{next_episode.get('episode_number')}"
                air_date = next_episode.get('air_date', 'TBA')
                
                embed.add_field(
                    name="📅 Next Episode",
                    value=f"{ep_num}: {ep_name}\nAirs: {air_date}",
                    inline=False
                )
            
            # Last episode
            last_episode = details.get('last_episode_to_air')
            if last_episode:
                ep_name = last_episode.get('name', 'Unknown')
                ep_num = f"S{last_episode.get('season_number')}E{last_episode.get('episode_number')}"
                air_date = last_episode.get('air_date', 'TBA')
                
                embed.add_field(
                    name="📺 Last Episode",
                    value=f"{ep_num}: {ep_name}\nAired: {air_date}",
                    inline=False
                )
            
            poster_path = details.get('poster_path')
            if poster_path:
                embed.set_thumbnail(url=Config.get_tmdb_image_url(poster_path, 'w342'))
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Series error: {e}", exc_info=True)
            await interaction.followup.send("❌ Error fetching series information.", ephemeral=True)
    
    @app_commands.command(name="season", description="View specific season details")
    @app_commands.describe(
        show="TV show name",
        season_number="Season number"
    )
    async def season(self, interaction: discord.Interaction, show: str, season_number: int):
        """Get season details"""
        await interaction.response.defer()
        
        try:
            # Search for show
            results = await self.tmdb.search_tv(show)
            if not results.get('results'):
                await interaction.followup.send("❌ TV show not found.", ephemeral=True)
                return
            
            show_id = results['results'][0]['id']
            show_name = results['results'][0]['name']
            
            # Get season details
            season_data = await self.tmdb.get_season_details(show_id, season_number)
            
            season_name = season_data.get('name', f'Season {season_number}')
            overview = season_data.get('overview', 'No description available.')
            episodes = season_data.get('episodes', [])
            
            embed = create_embed_base(
                title=f"📺 {show_name} - {season_name}",
                description=overview[:500]
            )
            
            embed.add_field(
                name="📊 Season Info",
                value=f"Episodes: {len(episodes)}\nAir Date: {season_data.get('air_date', 'TBA')}",
                inline=False
            )
            
            # List episodes
            episodes_list = []
            for ep in episodes[:20]:
                ep_num = ep.get('episode_number')
                ep_name = ep.get('name', 'Unknown')
                rating = ep.get('vote_average', 0)
                
                episodes_list.append(f"E{ep_num}: {ep_name} ({rating:.1f}/10)")
            
            if episodes_list:
                episodes_text = "\n".join(episodes_list)
                if len(episodes) > 20:
                    episodes_text += f"\n... and {len(episodes) - 20} more"
                
                embed.add_field(
                    name="🎬 Episodes",
                    value=episodes_text,
                    inline=False
                )
            
            poster_path = season_data.get('poster_path')
            if poster_path:
                embed.set_thumbnail(url=Config.get_tmdb_image_url(poster_path, 'w342'))
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Season error: {e}", exc_info=True)
            await interaction.followup.send("❌ Error fetching season details.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Collections(bot))