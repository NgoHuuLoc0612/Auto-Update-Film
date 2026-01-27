"""
Reviews & Keywords Cog
User reviews and content keywords/tags
"""
import logging
from typing import Dict, List

import discord
from discord import app_commands
from discord.ext import commands

from core.config import Config
from services.tmdb_client import TMDBClient
from utils.helpers import create_embed_base, truncate_text
from utils.views import EmbedPaginationView


class ReviewsKeywords(commands.Cog):
    """Reviews and keywords features"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger('FilmBot.ReviewsKeywords')
        self.tmdb = TMDBClient(Config.TMDB_API_KEY)
    
    async def cog_unload(self):
        await self.tmdb.close()
    
    @app_commands.command(name="reviews", description="Read user reviews for a movie/show")
    @app_commands.describe(query="Movie or TV show name")
    async def reviews(self, interaction: discord.Interaction, query: str):
        """Get user reviews"""
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
            
            # Get reviews
            if media_type == 'movie':
                reviews_data = await self.tmdb.get_movie_reviews(tmdb_id)
            else:
                reviews_data = await self.tmdb.get_tv_reviews(tmdb_id)
            
            reviews = reviews_data.get('results', [])
            
            if not reviews:
                await interaction.followup.send(
                    f"❌ No reviews found for **{title}**.",
                    ephemeral=True
                )
                return
            
            # Create embeds
            embeds = []
            for i, review in enumerate(reviews[:10]):
                author = review.get('author', 'Anonymous')
                content = review.get('content', 'No content')
                rating = review.get('author_details', {}).get('rating')
                
                embed = create_embed_base(
                    title=f"📝 Review {i+1}/{min(10, len(reviews))} - {title}",
                    description=truncate_text(content, 1500)
                )
                
                embed.add_field(
                    name="✍️ Author",
                    value=author,
                    inline=True
                )
                
                if rating:
                    from utils.helpers import get_rating_emoji
                    embed.add_field(
                        name=f"{get_rating_emoji(rating)} Rating",
                        value=f"{rating}/10",
                        inline=True
                    )
                
                embeds.append(embed)
            
            # Send with pagination
            if len(embeds) == 1:
                await interaction.followup.send(embed=embeds[0])
            else:
                view = EmbedPaginationView(embeds, timeout=Config.PAGINATION_TIMEOUT)
                await interaction.followup.send(
                    content=f"📝 **{len(embeds)} Reviews for {title}**",
                    embed=embeds[0],
                    view=view
                )
            
        except Exception as e:
            self.logger.error(f"Reviews error: {e}", exc_info=True)
            await interaction.followup.send("❌ Error fetching reviews.", ephemeral=True)
    
    @app_commands.command(name="keywords", description="View keywords/tags for a movie/show")
    @app_commands.describe(query="Movie or TV show name")
    async def keywords(self, interaction: discord.Interaction, query: str):
        """Get content keywords"""
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
            
            # Get details with keywords
            if media_type == 'movie':
                details = await self.tmdb.get_movie_details(tmdb_id)
            else:
                details = await self.tmdb.get_tv_details(tmdb_id)
            
            keywords_data = details.get('keywords', {})
            keywords = keywords_data.get('keywords') or keywords_data.get('results', [])
            
            if not keywords:
                await interaction.followup.send(
                    f"❌ No keywords found for **{title}**.",
                    ephemeral=True
                )
                return
            
            # Create embed
            embed = create_embed_base(
                title=f"🏷️ Keywords - {title}",
                description=f"Tags and keywords associated with this {media_type}"
            )
            
            # Group keywords
            keyword_names = [k.get('name', 'Unknown') for k in keywords]
            
            # Split into chunks
            from utils.helpers import chunk_list
            chunks = chunk_list(keyword_names, 10)
            
            for i, chunk in enumerate(chunks[:5]):
                embed.add_field(
                    name=f"Keywords {i*10+1}-{i*10+len(chunk)}",
                    value=", ".join(chunk),
                    inline=False
                )
            
            if len(keywords) > 50:
                embed.add_field(
                    name="ℹ️ Note",
                    value=f"Showing 50 of {len(keywords)} keywords",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Keywords error: {e}", exc_info=True)
            await interaction.followup.send("❌ Error fetching keywords.", ephemeral=True)
    
    @app_commands.command(name="watch-providers", description="Find where to watch a movie/show")
    @app_commands.describe(query="Movie or TV show name")
    async def watch_providers(self, interaction: discord.Interaction, query: str):
        """Get streaming availability"""
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
            
            # Get watch providers
            if media_type == 'movie':
                providers_data = await self.tmdb.get_watch_providers_movie(tmdb_id)
            else:
                providers_data = await self.tmdb.get_watch_providers_tv(tmdb_id)
            
            results_dict = providers_data.get('results', {})
            
            # Check for user's region (from config) and US as fallback
            regions = [Config.TMDB_REGION, 'US']
            region_data = None
            region_code = None
            
            for region in regions:
                if region in results_dict:
                    region_data = results_dict[region]
                    region_code = region
                    break
            
            if not region_data:
                await interaction.followup.send(
                    f"❌ No streaming information available for **{title}**.",
                    ephemeral=True
                )
                return
            
            embed = create_embed_base(
                title=f"📺 Where to Watch - {title}",
                description=f"Streaming availability in {region_code}"
            )
            
            # Streaming services
            stream = region_data.get('flatrate', [])
            if stream:
                providers = ", ".join([p.get('provider_name', 'Unknown') for p in stream[:10]])
                embed.add_field(
                    name="🎬 Stream",
                    value=providers,
                    inline=False
                )
            
            # Buy options
            buy = region_data.get('buy', [])
            if buy:
                providers = ", ".join([p.get('provider_name', 'Unknown') for p in buy[:10]])
                embed.add_field(
                    name="💰 Buy",
                    value=providers,
                    inline=False
                )
            
            # Rent options
            rent = region_data.get('rent', [])
            if rent:
                providers = ", ".join([p.get('provider_name', 'Unknown') for p in rent[:10]])
                embed.add_field(
                    name="🎥 Rent",
                    value=providers,
                    inline=False
                )
            
            # Link
            link = region_data.get('link')
            if link:
                embed.add_field(
                    name="🔗 More Info",
                    value=f"[View on JustWatch]({link})",
                    inline=False
                )
            
            if not (stream or buy or rent):
                embed.description = "No streaming information available for this region."
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Watch providers error: {e}", exc_info=True)
            await interaction.followup.send("❌ Error fetching streaming information.", ephemeral=True)
    
    @app_commands.command(name="certifications", description="View content ratings and certifications")
    @app_commands.describe(query="Movie or TV show name")
    async def certifications(self, interaction: discord.Interaction, query: str):
        """Get content certifications"""
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
            
            # Get details
            if media_type == 'movie':
                details = await self.tmdb.get_movie_details(tmdb_id)
                certifications_data = details.get('release_dates', {}).get('results', [])
            else:
                details = await self.tmdb.get_tv_details(tmdb_id)
                certifications_data = details.get('content_ratings', {}).get('results', [])
            
            if not certifications_data:
                await interaction.followup.send(
                    f"❌ No certification information available for **{title}**.",
                    ephemeral=True
                )
                return
            
            embed = create_embed_base(
                title=f"🔞 Certifications - {title}",
                description=f"Content ratings by country/region"
            )
            
            # Extract certifications
            certs = []
            for cert_data in certifications_data[:15]:
                country = cert_data.get('iso_3166_1', 'Unknown')
                
                if media_type == 'movie':
                    releases = cert_data.get('release_dates', [])
                    if releases:
                        certification = releases[0].get('certification', 'NR')
                else:
                    certification = cert_data.get('rating', 'NR')
                
                if certification:
                    certs.append(f"**{country}**: {certification}")
            
            if certs:
                # Split into chunks
                from utils.helpers import chunk_list
                chunks = chunk_list(certs, 10)
                
                for i, chunk in enumerate(chunks[:3]):
                    embed.add_field(
                        name=f"Ratings {i+1}",
                        value="\n".join(chunk),
                        inline=True
                    )
            
            embed.add_field(
                name="ℹ️ Common Ratings",
                value=(
                    "**G**: General Audiences\n"
                    "**PG**: Parental Guidance\n"
                    "**PG-13**: Parents Strongly Cautioned\n"
                    "**R**: Restricted\n"
                    "**NC-17/18**: Adults Only"
                ),
                inline=False
            )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Certifications error: {e}", exc_info=True)
            await interaction.followup.send("❌ Error fetching certifications.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ReviewsKeywords(bot))