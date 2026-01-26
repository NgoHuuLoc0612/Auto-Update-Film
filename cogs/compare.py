"""
Compare & Battle Cog
Compare movies/shows, create polls, battles
"""
import asyncio
import logging
import random
from typing import Dict, List, Optional

import discord
from discord import app_commands
from discord.ext import commands

from core.config import Config
from services.tmdb_client import TMDBClient
from utils.helpers import create_embed_base, format_money, get_media_type_emoji, get_rating_emoji
from utils.views import ConfirmView


class CompareView(discord.ui.View):
    """View for comparison with voting"""
    
    def __init__(self, item1: Dict, item2: Dict, timeout: int = 300):
        super().__init__(timeout=timeout)
        self.item1 = item1
        self.item2 = item2
        self.votes = {'item1': set(), 'item2': set()}
    
    @discord.ui.button(label="Vote Left", style=discord.ButtonStyle.primary, emoji="👈")
    async def vote_left(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        
        # Remove from other if exists
        self.votes['item2'].discard(user_id)
        self.votes['item1'].add(user_id)
        
        await interaction.response.send_message(
            f"✅ Voted for **{self.item1['title']}**!",
            ephemeral=True
        )
        
        # Update button labels
        self.vote_left.label = f"Vote Left ({len(self.votes['item1'])})"
        self.vote_right.label = f"Vote Right ({len(self.votes['item2'])})"
        await interaction.message.edit(view=self)
    
    @discord.ui.button(label="Vote Right", style=discord.ButtonStyle.primary, emoji="👉")
    async def vote_right(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        
        # Remove from other if exists
        self.votes['item1'].discard(user_id)
        self.votes['item2'].add(user_id)
        
        await interaction.response.send_message(
            f"✅ Voted for **{self.item2['title']}**!",
            ephemeral=True
        )
        
        # Update button labels
        self.vote_left.label = f"Vote Left ({len(self.votes['item1'])})"
        self.vote_right.label = f"Vote Right ({len(self.votes['item2'])})"
        await interaction.message.edit(view=self)
    
    @discord.ui.button(label="End Poll", style=discord.ButtonStyle.danger, emoji="🛑")
    async def end_poll(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Poll ended!", ephemeral=True)
        self.stop()


class Compare(commands.Cog):
    """Compare movies/shows and create battles"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger('FilmBot.Compare')
        self.tmdb = TMDBClient(Config.TMDB_API_KEY)
    
    async def cog_unload(self):
        await self.tmdb.close()
    
    @app_commands.command(name="compare", description="Compare two movies or TV shows")
    @app_commands.describe(
        item1="First movie/show name",
        item2="Second movie/show name"
    )
    async def compare(self, interaction: discord.Interaction, item1: str, item2: str):
        """Compare two media items"""
        await interaction.response.defer()
        
        try:
            # Search for both items
            search1 = await self.tmdb.search_multi(item1)
            search2 = await self.tmdb.search_multi(item2)
            
            results1 = [r for r in search1.get('results', []) if r.get('media_type') in ['movie', 'tv']]
            results2 = [r for r in search2.get('results', []) if r.get('media_type') in ['movie', 'tv']]
            
            if not results1 or not results2:
                await interaction.followup.send("❌ Could not find one or both items.", ephemeral=True)
                return
            
            item1_data = results1[0]
            item2_data = results2[0]
            
            # Get detailed info
            media_type1 = item1_data.get('media_type')
            media_type2 = item2_data.get('media_type')
            
            if media_type1 == 'movie':
                details1 = await self.tmdb.get_movie_details(item1_data['id'])
            else:
                details1 = await self.tmdb.get_tv_details(item1_data['id'])
            
            if media_type2 == 'movie':
                details2 = await self.tmdb.get_movie_details(item2_data['id'])
            else:
                details2 = await self.tmdb.get_tv_details(item2_data['id'])
            
            # Create comparison embed
            embed = create_embed_base(
                title="⚔️ Movie/Show Battle",
                description="Vote for your favorite!"
            )
            
            # Item 1
            title1 = details1.get('title') or details1.get('name')
            rating1 = details1.get('vote_average', 0)
            votes1 = details1.get('vote_count', 0)
            
            embed.add_field(
                name=f"{get_media_type_emoji(media_type1)} {title1}",
                value=(
                    f"{get_rating_emoji(rating1)} Rating: {rating1:.1f}/10\n"
                    f"📊 Votes: {votes1:,}\n"
                    f"📅 Release: {details1.get('release_date') or details1.get('first_air_date', 'N/A')}"
                ),
                inline=True
            )
            
            embed.add_field(name="⚡", value="VS", inline=True)
            
            # Item 2
            title2 = details2.get('title') or details2.get('name')
            rating2 = details2.get('vote_average', 0)
            votes2 = details2.get('vote_count', 0)
            
            embed.add_field(
                name=f"{get_media_type_emoji(media_type2)} {title2}",
                value=(
                    f"{get_rating_emoji(rating2)} Rating: {rating2:.1f}/10\n"
                    f"📊 Votes: {votes2:,}\n"
                    f"📅 Release: {details2.get('release_date') or details2.get('first_air_date', 'N/A')}"
                ),
                inline=True
            )
            
            # Budget/Revenue comparison for movies
            if media_type1 == 'movie' and media_type2 == 'movie':
                budget1 = details1.get('budget', 0)
                budget2 = details2.get('budget', 0)
                revenue1 = details1.get('revenue', 0)
                revenue2 = details2.get('revenue', 0)
                
                if budget1 > 0 or budget2 > 0:
                    embed.add_field(
                        name="💰 Budget Comparison",
                        value=f"{format_money(budget1)} vs {format_money(budget2)}",
                        inline=False
                    )
                
                if revenue1 > 0 or revenue2 > 0:
                    embed.add_field(
                        name="💵 Revenue Comparison",
                        value=f"{format_money(revenue1)} vs {format_money(revenue2)}",
                        inline=False
                    )
            
            # Create voting view
            view = CompareView(
                {'title': title1, 'rating': rating1},
                {'title': title2, 'rating': rating2}
            )
            
            await interaction.followup.send(embed=embed, view=view)
            
        except Exception as e:
            self.logger.error(f"Compare error: {e}", exc_info=True)
            await interaction.followup.send("❌ Error comparing items.", ephemeral=True)
    
    @app_commands.command(name="battle-royale", description="Random movie battle royale")
    @app_commands.describe(count="Number of movies to battle (2-10)")
    async def battle_royale(self, interaction: discord.Interaction, count: int = 5):
        """Create a battle royale with random movies"""
        await interaction.response.defer()
        
        if count < 2 or count > 10:
            await interaction.followup.send("❌ Count must be between 2 and 10.", ephemeral=True)
            return
        
        try:
            # Get random popular movies
            page = random.randint(1, 5)
            results = await self.tmdb.get_popular_movies(page=page)
            movies = results.get('results', [])[:count]
            
            embed = create_embed_base(
                title="🎲 Movie Battle Royale",
                description=f"Vote for the best movie! ({count} contestants)"
            )
            
            for i, movie in enumerate(movies, 1):
                title = movie.get('title')
                rating = movie.get('vote_average', 0)
                
                embed.add_field(
                    name=f"{i}. {title}",
                    value=f"{get_rating_emoji(rating)} {rating:.1f}/10",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Battle royale error: {e}", exc_info=True)
            await interaction.followup.send("❌ Error creating battle.", ephemeral=True)
    
    @app_commands.command(name="versus-stats", description="Detailed statistical comparison")
    @app_commands.describe(
        item1="First movie/show",
        item2="Second movie/show"
    )
    async def versus_stats(self, interaction: discord.Interaction, item1: str, item2: str):
        """Detailed statistical comparison"""
        await interaction.response.defer()
        
        try:
            # Get items
            search1 = await self.tmdb.search_multi(item1)
            search2 = await self.tmdb.search_multi(item2)
            
            results1 = [r for r in search1.get('results', []) if r.get('media_type') in ['movie', 'tv']]
            results2 = [r for r in search2.get('results', []) if r.get('media_type') in ['movie', 'tv']]
            
            if not results1 or not results2:
                await interaction.followup.send("❌ Could not find items.", ephemeral=True)
                return
            
            item1_data = results1[0]
            item2_data = results2[0]
            
            # Get details
            if item1_data.get('media_type') == 'movie':
                details1 = await self.tmdb.get_movie_details(item1_data['id'])
            else:
                details1 = await self.tmdb.get_tv_details(item1_data['id'])
            
            if item2_data.get('media_type') == 'movie':
                details2 = await self.tmdb.get_movie_details(item2_data['id'])
            else:
                details2 = await self.tmdb.get_tv_details(item2_data['id'])
            
            title1 = details1.get('title') or details1.get('name')
            title2 = details2.get('title') or details2.get('name')
            
            embed = create_embed_base(
                title=f"📊 Statistical Comparison",
                description=f"**{title1}** vs **{title2}**"
            )
            
            # Rating
            rating1 = details1.get('vote_average', 0)
            rating2 = details2.get('vote_average', 0)
            winner_rating = "LEFT" if rating1 > rating2 else "RIGHT" if rating2 > rating1 else "TIE"
            
            embed.add_field(
                name="⭐ Rating",
                value=f"{rating1:.1f} vs {rating2:.1f}\n**Winner: {winner_rating}**",
                inline=False
            )
            
            # Popularity
            pop1 = details1.get('popularity', 0)
            pop2 = details2.get('popularity', 0)
            winner_pop = "LEFT" if pop1 > pop2 else "RIGHT" if pop2 > pop1 else "TIE"
            
            embed.add_field(
                name="🔥 Popularity",
                value=f"{pop1:.1f} vs {pop2:.1f}\n**Winner: {winner_pop}**",
                inline=False
            )
            
            # Vote count
            votes1 = details1.get('vote_count', 0)
            votes2 = details2.get('vote_count', 0)
            winner_votes = "LEFT" if votes1 > votes2 else "RIGHT" if votes2 > votes1 else "TIE"
            
            embed.add_field(
                name="📊 Total Votes",
                value=f"{votes1:,} vs {votes2:,}\n**Winner: {winner_votes}**",
                inline=False
            )
            
            # Overall winner
            score1 = (1 if winner_rating == "LEFT" else 0) + \
                    (1 if winner_pop == "LEFT" else 0) + \
                    (1 if winner_votes == "LEFT" else 0)
            score2 = (1 if winner_rating == "RIGHT" else 0) + \
                    (1 if winner_pop == "RIGHT" else 0) + \
                    (1 if winner_votes == "RIGHT" else 0)
            
            if score1 > score2:
                overall_winner = f"🏆 **{title1}** wins!"
            elif score2 > score1:
                overall_winner = f"🏆 **{title2}** wins!"
            else:
                overall_winner = "🤝 It's a tie!"
            
            embed.add_field(
                name="🏆 Overall Winner",
                value=overall_winner,
                inline=False
            )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Versus stats error: {e}", exc_info=True)
            await interaction.followup.send("❌ Error creating comparison.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Compare(bot))