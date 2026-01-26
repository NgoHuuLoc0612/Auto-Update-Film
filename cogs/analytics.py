"""
Advanced Analytics Cog
Provides data analysis and visualizations
"""
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List

import discord
import numpy as np
from discord import app_commands
from discord.ext import commands
from sqlalchemy import func, select

from core.config import Config
from core.database import Rating, Subscription, Watchlist
from services.tmdb_client import TMDBClient
from services.visualization import VisualizationService
from utils.helpers import create_embed_base


class Analytics(commands.Cog):
    """Advanced analytics and data visualization"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger('FilmBot.Analytics')
        self.tmdb = TMDBClient(Config.TMDB_API_KEY)
        self.viz = VisualizationService()
    
    async def cog_unload(self):
        await self.tmdb.close()
    
    @app_commands.command(name="visualize-ratings", description="Visualize rating distribution")
    @app_commands.describe(media_type="Type of media to analyze")
    @app_commands.choices(media_type=[
        app_commands.Choice(name="Movies", value="movie"),
        app_commands.Choice(name="TV Shows", value="tv"),
        app_commands.Choice(name="All", value="all")
    ])
    async def visualize_ratings(self, interaction: discord.Interaction, media_type: str = "all"):
        """Create rating distribution visualization"""
        await interaction.response.defer()
        
        try:
            async with self.bot.db.async_session() as session:
                query = select(Rating.score)
                
                if media_type != "all":
                    query = query.where(Rating.media_type == media_type)
                
                result = await session.execute(query)
                ratings = [r[0] for r in result.all()]
            
            if not ratings:
                embed = create_embed_base(
                    title="📊 No Data",
                    description="No ratings found to visualize."
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Create visualization
            chart = self.viz.create_rating_distribution(
                ratings,
                f"Rating Distribution - {media_type.title()}"
            )
            
            file = discord.File(chart, filename="rating_distribution.png")
            
            embed = create_embed_base(
                title=f"📊 Rating Distribution - {media_type.title()}",
                description=f"Analysis of {len(ratings)} ratings"
            )
            embed.add_field(name="Mean", value=f"{np.mean(ratings):.2f}", inline=True)
            embed.add_field(name="Median", value=f"{np.median(ratings):.2f}", inline=True)
            embed.add_field(name="Std Dev", value=f"{np.std(ratings):.2f}", inline=True)
            embed.set_image(url="attachment://rating_distribution.png")
            
            await interaction.followup.send(embed=embed, file=file)
            
        except Exception as e:
            self.logger.error(f"Visualization error: {e}", exc_info=True)
            await interaction.followup.send("❌ Error creating visualization.", ephemeral=True)
    
    @app_commands.command(name="genre-analysis", description="Analyze genre popularity with bubble chart")
    async def genre_analysis(self, interaction: discord.Interaction):
        """Create genre bubble chart"""
        await interaction.response.defer()
        
        try:
            # Get popular movies from different genres
            genres_data = {}
            genres = await self.tmdb.get_genres_movie()
            
            for genre in genres['genres'][:10]:
                genre_id = genre['id']
                genre_name = genre['name']
                
                # Discover movies in this genre
                results = await self.tmdb.discover_movies(
                    with_genres=genre_id,
                    sort_by='popularity.desc',
                    page=1
                )
                
                movies = results.get('results', [])[:20]
                
                if movies:
                    avg_rating = np.mean([m.get('vote_average', 0) for m in movies])
                    total_votes = sum([m.get('vote_count', 0) for m in movies])
                    
                    genres_data[genre_name] = {
                        'count': len(movies),
                        'avg_rating': avg_rating,
                        'total_votes': total_votes
                    }
            
            # Create bubble chart
            chart = self.viz.create_genre_bubble_chart(genres_data)
            
            file = discord.File(chart, filename="genre_bubble.png")
            
            embed = create_embed_base(
                title="🎭 Genre Analysis - Bubble Chart",
                description=(
                    "Bubble size = Total votes\n"
                    "X-axis = Number of titles\n"
                    "Y-axis = Average rating"
                )
            )
            embed.set_image(url="attachment://genre_bubble.png")
            
            await interaction.followup.send(embed=embed, file=file)
            
        except Exception as e:
            self.logger.error(f"Genre analysis error: {e}", exc_info=True)
            await interaction.followup.send("❌ Error analyzing genres.", ephemeral=True)
    
    @app_commands.command(name="3d-movie-analysis", description="3D visualization of movie data")
    async def movie_3d_analysis(self, interaction: discord.Interaction):
        """Create 3D scatter plot"""
        await interaction.response.defer()
        
        try:
            # Get popular movies with budget/revenue data
            movies_data = []
            
            for page in range(1, 4):
                results = await self.tmdb.get_popular_movies(page=page)
                
                for movie_data in results.get('results', [])[:10]:
                    movie_id = movie_data.get('id')
                    details = await self.tmdb.get_movie_details(movie_id)
                    
                    budget = details.get('budget', 0)
                    revenue = details.get('revenue', 0)
                    rating = details.get('vote_average', 0)
                    
                    if budget > 0 and revenue > 0:
                        movies_data.append({
                            'rating': rating,
                            'budget': budget,
                            'revenue': revenue,
                            'title': details.get('title')
                        })
            
            if len(movies_data) < 5:
                await interaction.followup.send("❌ Not enough data for 3D visualization.", ephemeral=True)
                return
            
            # Create 3D visualization
            chart = self.viz.create_3d_scatter(movies_data)
            
            file = discord.File(chart, filename="3d_analysis.png")
            
            embed = create_embed_base(
                title="📈 3D Movie Analysis",
                description=f"Analyzing {len(movies_data)} movies"
            )
            embed.add_field(
                name="Axes",
                value="X: Rating\nY: Budget (M$)\nZ: Revenue (M$)",
                inline=False
            )
            embed.set_image(url="attachment://3d_analysis.png")
            
            await interaction.followup.send(embed=embed, file=file)
            
        except Exception as e:
            self.logger.error(f"3D analysis error: {e}", exc_info=True)
            await interaction.followup.send("❌ Error creating 3D visualization.", ephemeral=True)
    
    @app_commands.command(name="watchlist-radar", description="Radar chart of your watchlist preferences")
    async def watchlist_radar(self, interaction: discord.Interaction):
        """Create radar chart of user preferences"""
        await interaction.response.defer()
        
        try:
            async with self.bot.db.async_session() as session:
                result = await session.execute(
                    select(Watchlist).where(
                        Watchlist.guild_id == interaction.guild_id,
                        Watchlist.user_id == interaction.user.id
                    )
                )
                watchlist = list(result.scalars().all())
            
            if not watchlist:
                await interaction.followup.send("❌ Your watchlist is empty.", ephemeral=True)
                return
            
            # Analyze watchlist
            genre_counts = defaultdict(int)
            total_movies = 0
            total_tv = 0
            
            for item in watchlist:
                if item.media_type == 'movie':
                    total_movies += 1
                else:
                    total_tv += 1
                
                # Get details from TMDB
                try:
                    if item.media_type == 'movie':
                        details = await self.tmdb.get_movie_details(item.tmdb_id)
                    else:
                        details = await self.tmdb.get_tv_details(item.tmdb_id)
                    
                    for genre in details.get('genres', [])[:3]:
                        genre_counts[genre['name']] += 1
                except:
                    continue
            
            # Get top 6 genres
            top_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)[:6]
            
            categories = [g[0] for g in top_genres]
            values = [g[1] for g in top_genres]
            
            # Create radar chart
            chart = self.viz.create_radar_chart(
                categories,
                values,
                f"{interaction.user.display_name}'s Preferences"
            )
            
            file = discord.File(chart, filename="radar_chart.png")
            
            embed = create_embed_base(
                title="🎯 Your Watchlist Analysis",
                description=f"Total items: {len(watchlist)}"
            )
            embed.add_field(name="Movies", value=total_movies, inline=True)
            embed.add_field(name="TV Shows", value=total_tv, inline=True)
            embed.set_image(url="attachment://radar_chart.png")
            
            await interaction.followup.send(embed=embed, file=file)
            
        except Exception as e:
            self.logger.error(f"Radar chart error: {e}", exc_info=True)
            await interaction.followup.send("❌ Error creating radar chart.", ephemeral=True)
    
    @app_commands.command(name="server-analytics", description="Comprehensive server analytics dashboard")
    async def server_analytics(self, interaction: discord.Interaction):
        """Create comprehensive analytics dashboard"""
        await interaction.response.defer()
        
        try:
            async with self.bot.db.async_session() as session:
                # Get statistics
                subscriptions_result = await session.execute(
                    select(Subscription).where(Subscription.guild_id == interaction.guild_id)
                )
                subscriptions = list(subscriptions_result.scalars().all())
                
                watchlist_result = await session.execute(
                    select(Watchlist).where(Watchlist.guild_id == interaction.guild_id)
                )
                watchlist = list(watchlist_result.scalars().all())
                
                ratings_result = await session.execute(
                    select(Rating)
                )
                ratings = list(ratings_result.scalars().all())
            
            # Create multiple visualizations
            embeds = []
            
            # Overview embed
            embed = create_embed_base(
                title="📊 Server Analytics Dashboard",
                description=f"Comprehensive analytics for **{interaction.guild.name}**"
            )
            embed.add_field(name="📌 Subscriptions", value=len(subscriptions), inline=True)
            embed.add_field(name="📝 Watchlist Items", value=len(watchlist), inline=True)
            embed.add_field(name="⭐ Ratings", value=len(ratings), inline=True)
            
            # Media type distribution
            movie_subs = len([s for s in subscriptions if s.media_type == 'movie'])
            tv_subs = len([s for s in subscriptions if s.media_type == 'tv'])
            
            embed.add_field(
                name="🎬 Content Distribution",
                value=f"Movies: {movie_subs}\nTV Shows: {tv_subs}",
                inline=False
            )
            
            embeds.append(embed)
            
            # Activity timeline
            if watchlist:
                dates = [w.added_at for w in watchlist if w.added_at]
                if dates:
                    dates.sort()
                    date_counts = defaultdict(int)
                    for date in dates:
                        date_key = date.date()
                        date_counts[date_key] += 1
                    
                    embed2 = create_embed_base(
                        title="📈 Activity Timeline",
                        description="Watchlist activity over time"
                    )
                    embeds.append(embed2)
            
            await interaction.followup.send(embeds=embeds[:10])
            
        except Exception as e:
            self.logger.error(f"Analytics dashboard error: {e}", exc_info=True)
            await interaction.followup.send("❌ Error creating analytics dashboard.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Analytics(bot))