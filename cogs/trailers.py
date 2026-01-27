"""
Trailer & Media Cog
Watch trailers, clips, and media content
"""
import logging
from typing import Dict, List, Optional

import discord
from discord import app_commands
from discord.ext import commands

from core.config import Config
from services.tmdb_client import TMDBClient
from utils.helpers import create_embed_base, get_media_type_emoji, get_video_url
from utils.views import EmbedPaginationView


class TrailerView(discord.ui.View):
    """View for trailer selection"""
    
    def __init__(self, videos: List[Dict], timeout: int = 180):
        super().__init__(timeout=timeout)
        self.videos = videos
        
        # Create select menu
        options = []
        for i, video in enumerate(videos[:25]):
            video_type = video.get('type', 'Video')
            name = video.get('name', 'Unknown')
            
            emoji_map = {
                'Trailer': '🎬',
                'Teaser': '🎥',
                'Clip': '📹',
                'Featurette': '🎞️',
                'Behind the Scenes': '🎭'
            }
            
            emoji = emoji_map.get(video_type, '📺')
            
            options.append(
                discord.SelectOption(
                    label=name[:100],
                    value=str(i),
                    emoji=emoji,
                    description=f"{video_type} - {video.get('site', 'YouTube')}"[:100]
                )
            )
        
        if options:
            select = discord.ui.Select(
                placeholder="Select a video to watch...",
                options=options,
                min_values=1,
                max_values=1
            )
            select.callback = self.select_callback
            self.add_item(select)
    
    async def select_callback(self, interaction: discord.Interaction):
        """Handle video selection"""
        index = int(interaction.data['values'][0])
        video = self.videos[index]
        
        video_url = get_video_url(video.get('key'), video.get('site', 'YouTube'))
        
        embed = create_embed_base(
            title=f"🎬 {video.get('name')}",
            description=f"**Type:** {video.get('type')}\n**Site:** {video.get('site')}"
        )
        
        embed.add_field(
            name="🔗 Watch Now",
            value=f"[Click here to watch]({video_url})",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


class Trailers(commands.Cog):
    """Trailer and media content features"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger('FilmBot.Trailers')
        self.tmdb = TMDBClient(Config.TMDB_API_KEY)
    
    async def cog_unload(self):
        await self.tmdb.close()
    
    @app_commands.command(name="trailer", description="Watch movie or TV show trailers")
    @app_commands.describe(query="Movie or TV show name")
    async def trailer(self, interaction: discord.Interaction, query: str):
        """Get trailers for a movie or TV show"""
        await interaction.response.defer()
        
        try:
            # Search for media
            results = await self.tmdb.search_multi(query)
            items = [r for r in results.get('results', []) if r.get('media_type') in ['movie', 'tv']]
            
            if not items:
                embed = create_embed_base(
                    title="🔍 No Results",
                    description=f"No results found for: **{query}**"
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            item = items[0]
            media_type = item.get('media_type')
            tmdb_id = item.get('id')
            title = item.get('title') or item.get('name')
            
            # Get videos
            if media_type == 'movie':
                video_data = await self.tmdb.get_movie_videos(tmdb_id)
            else:
                video_data = await self.tmdb.get_tv_videos(tmdb_id)
            
            videos = video_data.get('results', [])
            
            if not videos:
                embed = create_embed_base(
                    title="📹 No Trailers Available",
                    description=f"No trailers found for **{title}**"
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Filter for trailers and teasers first
            trailers = [v for v in videos if v.get('type') in ['Trailer', 'Teaser']]
            if not trailers:
                trailers = videos
            
            # Create main embed
            embed = create_embed_base(
                title=f"🎬 Trailers for {get_media_type_emoji(media_type)} {title}",
                description=f"Found {len(trailers)} video(s)"
            )
            
            # Show first trailer directly
            if trailers:
                first_video = trailers[0]
                video_url = get_video_url(first_video.get('key'), first_video.get('site', 'YouTube'))
                
                embed.add_field(
                    name=f"▶️ {first_video.get('name')}",
                    value=f"**Type:** {first_video.get('type')}\n[Watch Now]({video_url})",
                    inline=False
                )
            
            # Add poster
            if item.get('poster_path'):
                embed.set_thumbnail(url=Config.get_tmdb_image_url(item['poster_path'], 'w342'))
            
            # Create view for additional trailers
            if len(trailers) > 1:
                view = TrailerView(trailers)
                await interaction.followup.send(embed=embed, view=view)
            else:
                await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Trailer error: {e}", exc_info=True)
            await interaction.followup.send("❌ Error fetching trailers.", ephemeral=True)
    
    @app_commands.command(name="videos", description="Get all videos for a movie/show")
    @app_commands.describe(
        query="Movie or TV show name",
        video_type="Type of video"
    )
    @app_commands.choices(video_type=[
        app_commands.Choice(name="All", value="all"),
        app_commands.Choice(name="Trailers", value="Trailer"),
        app_commands.Choice(name="Teasers", value="Teaser"),
        app_commands.Choice(name="Clips", value="Clip"),
        app_commands.Choice(name="Behind the Scenes", value="Behind the Scenes"),
        app_commands.Choice(name="Featurettes", value="Featurette")
    ])
    async def videos(self, interaction: discord.Interaction, query: str, video_type: str = "all"):
        """Get all videos for media"""
        await interaction.response.defer()
        
        try:
            # Search for media
            results = await self.tmdb.search_multi(query)
            items = [r for r in results.get('results', []) if r.get('media_type') in ['movie', 'tv']]
            
            if not items:
                await interaction.followup.send("❌ No results found.", ephemeral=True)
                return
            
            item = items[0]
            media_type = item.get('media_type')
            tmdb_id = item.get('id')
            title = item.get('title') or item.get('name')
            
            # Get videos
            if media_type == 'movie':
                video_data = await self.tmdb.get_movie_videos(tmdb_id)
            else:
                video_data = await self.tmdb.get_tv_videos(tmdb_id)
            
            videos = video_data.get('results', [])
            
            # Filter by type
            if video_type != "all":
                videos = [v for v in videos if v.get('type') == video_type]
            
            if not videos:
                await interaction.followup.send(f"❌ No {video_type} videos found.", ephemeral=True)
                return
            
            # Create embeds for pagination
            embeds = []
            for i in range(0, len(videos), 5):
                chunk = videos[i:i+5]
                
                embed = create_embed_base(
                    title=f"📹 Videos for {title}",
                    description=f"Type: {video_type} | Total: {len(videos)}"
                )
                
                for video in chunk:
                    video_url = get_video_url(video.get('key'), video.get('site', 'YouTube'))
                    embed.add_field(
                        name=f"{video.get('type')} - {video.get('name')}",
                        value=f"[Watch on {video.get('site', 'YouTube')}]({video_url})",
                        inline=False
                    )
                
                if item.get('poster_path'):
                    embed.set_thumbnail(url=Config.get_tmdb_image_url(item['poster_path'], 'w342'))
                
                embeds.append(embed)
            
            # Send with pagination
            if len(embeds) == 1:
                await interaction.followup.send(embed=embeds[0])
            else:
                view = EmbedPaginationView(embeds, timeout=Config.PAGINATION_TIMEOUT)
                await interaction.followup.send(embed=embeds[0], view=view)
            
        except Exception as e:
            self.logger.error(f"Videos error: {e}", exc_info=True)
            await interaction.followup.send("❌ Error fetching videos.", ephemeral=True)
    
    @app_commands.command(name="latest-trailers", description="Get latest movie trailers")
    @app_commands.describe(count="Number of trailers (1-10)")
    async def latest_trailers(self, interaction: discord.Interaction, count: int = 5):
        """Get latest movie trailers"""
        await interaction.response.defer()
        
        if count < 1 or count > 10:
            await interaction.followup.send("❌ Count must be between 1 and 10.", ephemeral=True)
            return
        
        try:
            # Get upcoming movies
            results = await self.tmdb.get_upcoming_movies()
            movies = results.get('results', [])[:count]
            
            embeds = []
            
            for movie in movies:
                movie_id = movie.get('id')
                title = movie.get('title')
                
                # Get videos
                video_data = await self.tmdb.get_movie_videos(movie_id)
                videos = video_data.get('results', [])
                
                trailers = [v for v in videos if v.get('type') in ['Trailer', 'Teaser']]
                
                if trailers:
                    video = trailers[0]
                    video_url = get_video_url(video.get('key'), video.get('site', 'YouTube'))
                    
                    embed = create_embed_base(
                        title=f"🎬 {title}",
                        description=movie.get('overview', 'No description')[:300]
                    )
                    
                    embed.add_field(
                        name="▶️ Trailer",
                        value=f"[Watch {video.get('name')}]({video_url})",
                        inline=False
                    )
                    
                    embed.add_field(
                        name="📅 Release Date",
                        value=movie.get('release_date', 'TBA'),
                        inline=True
                    )
                    
                    rating = movie.get('vote_average', 0)
                    if rating:
                        from utils.helpers import get_rating_emoji
                        embed.add_field(
                            name=f"{get_rating_emoji(rating)} Rating",
                            value=f"{rating:.1f}/10",
                            inline=True
                        )
                    
                    if movie.get('poster_path'):
                        embed.set_image(url=Config.get_tmdb_image_url(movie['poster_path'], 'w500'))
                    
                    embeds.append(embed)
            
            if not embeds:
                await interaction.followup.send("❌ No trailers available.", ephemeral=True)
                return
            
            # Send with pagination
            if len(embeds) == 1:
                await interaction.followup.send(embed=embeds[0])
            else:
                view = EmbedPaginationView(embeds, timeout=Config.PAGINATION_TIMEOUT)
                await interaction.followup.send(
                    content=f"🎬 **Latest {len(embeds)} Movie Trailers**",
                    embed=embeds[0],
                    view=view
                )
            
        except Exception as e:
            self.logger.error(f"Latest trailers error: {e}", exc_info=True)
            await interaction.followup.send("❌ Error fetching trailers.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Trailers(bot))