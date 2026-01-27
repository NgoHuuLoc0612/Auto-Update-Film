"""
Cast & Crew Cog
Detailed information about actors, directors, and crew members
"""
import logging
from typing import Dict, List, Optional

import discord
from discord import app_commands
from discord.ext import commands

from core.config import Config
from services.tmdb_client import TMDBClient
from utils.helpers import create_embed_base, format_date, get_media_type_emoji
from utils.views import EmbedPaginationView


class CastCrew(commands.Cog):
    """Cast and crew information"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger('FilmBot.CastCrew')
        self.tmdb = TMDBClient(Config.TMDB_API_KEY)
    
    async def cog_unload(self):
        await self.tmdb.close()
    
    @app_commands.command(name="cast", description="View cast information for a movie/show")
    @app_commands.describe(query="Movie or TV show name")
    async def cast(self, interaction: discord.Interaction, query: str):
        """Get cast information"""
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
            
            # Get details with credits
            if media_type == 'movie':
                details = await self.tmdb.get_movie_details(tmdb_id)
            else:
                details = await self.tmdb.get_tv_details(tmdb_id)
            
            credits = details.get('credits', {})
            cast = credits.get('cast', [])[:20]  # Top 20 cast members
            
            if not cast:
                await interaction.followup.send("❌ No cast information available.", ephemeral=True)
                return
            
            # Create embeds
            embeds = []
            for i in range(0, len(cast), 10):
                chunk = cast[i:i+10]
                
                embed = create_embed_base(
                    title=f"🎭 Cast - {get_media_type_emoji(media_type)} {title}",
                    description=f"Showing cast members {i+1}-{min(i+10, len(cast))} of {len(cast)}"
                )
                
                for member in chunk:
                    name = member.get('name', 'Unknown')
                    character = member.get('character', 'Unknown Role')
                    
                    embed.add_field(
                        name=f"👤 {name}",
                        value=f"as **{character}**",
                        inline=False
                    )
                
                if details.get('poster_path'):
                    embed.set_thumbnail(url=Config.get_tmdb_image_url(details['poster_path'], 'w185'))
                
                embeds.append(embed)
            
            # Send with pagination
            if len(embeds) == 1:
                await interaction.followup.send(embed=embeds[0])
            else:
                view = EmbedPaginationView(embeds, timeout=Config.PAGINATION_TIMEOUT)
                await interaction.followup.send(embed=embeds[0], view=view)
            
        except Exception as e:
            self.logger.error(f"Cast error: {e}", exc_info=True)
            await interaction.followup.send("❌ Error fetching cast information.", ephemeral=True)
    
    @app_commands.command(name="crew", description="View crew information for a movie/show")
    @app_commands.describe(query="Movie or TV show name")
    async def crew(self, interaction: discord.Interaction, query: str):
        """Get crew information"""
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
            
            # Get details with credits
            if media_type == 'movie':
                details = await self.tmdb.get_movie_details(tmdb_id)
            else:
                details = await self.tmdb.get_tv_details(tmdb_id)
            
            credits = details.get('credits', {})
            crew = credits.get('crew', [])
            
            if not crew:
                await interaction.followup.send("❌ No crew information available.", ephemeral=True)
                return
            
            # Organize by department
            departments = {}
            for member in crew:
                dept = member.get('department', 'Other')
                if dept not in departments:
                    departments[dept] = []
                departments[dept].append(member)
            
            # Create embed
            embed = create_embed_base(
                title=f"🎬 Crew - {get_media_type_emoji(media_type)} {title}",
                description=f"Total crew members: {len(crew)}"
            )
            
            # Key departments
            key_depts = ['Directing', 'Writing', 'Production', 'Camera', 'Editing', 'Sound']
            
            for dept in key_depts:
                if dept in departments:
                    members = departments[dept][:5]
                    crew_list = []
                    for member in members:
                        name = member.get('name')
                        job = member.get('job')
                        crew_list.append(f"• {name} ({job})")
                    
                    if crew_list:
                        embed.add_field(
                            name=f"🎥 {dept}",
                            value="\n".join(crew_list),
                            inline=False
                        )
            
            if details.get('poster_path'):
                embed.set_thumbnail(url=Config.get_tmdb_image_url(details['poster_path'], 'w185'))
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Crew error: {e}", exc_info=True)
            await interaction.followup.send("❌ Error fetching crew information.", ephemeral=True)
    
    @app_commands.command(name="person", description="Get information about an actor, director, or crew member")
    @app_commands.describe(name="Person's name")
    async def person(self, interaction: discord.Interaction, name: str):
        """Get person details"""
        await interaction.response.defer()
        
        try:
            # Search for person
            search_results = await self.tmdb.search_multi(name)
            people = [r for r in search_results.get('results', []) if r.get('media_type') == 'person']
            
            if not people:
                await interaction.followup.send("❌ Person not found.", ephemeral=True)
                return
            
            person_data = people[0]
            person_id = person_data.get('id')
            
            # Get detailed information
            details = await self.tmdb.get_person_details(person_id)
            
            person_name = details.get('name', 'Unknown')
            biography = details.get('biography', 'No biography available.')
            birthday = details.get('birthday')
            birthplace = details.get('place_of_birth')
            known_for = details.get('known_for_department', 'Acting')
            
            embed = create_embed_base(
                title=f"👤 {person_name}",
                description=biography[:500] + "..." if len(biography) > 500 else biography
            )
            
            # Personal info
            if birthday:
                embed.add_field(
                    name="🎂 Birthday",
                    value=format_date(birthday),
                    inline=True
                )
            
            if birthplace:
                embed.add_field(
                    name="📍 Birthplace",
                    value=birthplace,
                    inline=True
                )
            
            embed.add_field(
                name="🎭 Known For",
                value=known_for,
                inline=True
            )
            
            # Filmography
            credits = details.get('combined_credits', {})
            cast_credits = credits.get('cast', [])
            crew_credits = credits.get('crew', [])
            
            if cast_credits:
                # Sort by popularity/release date
                top_credits = sorted(cast_credits, key=lambda x: x.get('popularity', 0), reverse=True)[:10]
                credits_list = []
                
                for credit in top_credits:
                    title = credit.get('title') or credit.get('name')
                    character = credit.get('character', '')
                    if character:
                        credits_list.append(f"• {title} as {character}")
                    else:
                        credits_list.append(f"• {title}")
                
                if credits_list:
                    embed.add_field(
                        name="🎬 Notable Works",
                        value="\n".join(credits_list[:5]),
                        inline=False
                    )
            
            # Statistics
            total_credits = len(cast_credits) + len(crew_credits)
            embed.add_field(
                name="📊 Career Stats",
                value=f"Total Credits: {total_credits}\nActing: {len(cast_credits)}\nCrew: {len(crew_credits)}",
                inline=False
            )
            
            # Profile image
            profile_path = details.get('profile_path')
            if profile_path:
                embed.set_thumbnail(url=Config.get_tmdb_image_url(profile_path, 'w185'))
            
            # IMDB/TMDB links
            imdb_id = details.get('imdb_id')
            links = f"[TMDB](https://www.themoviedb.org/person/{person_id})"
            if imdb_id:
                links += f" • [IMDB](https://www.imdb.com/name/{imdb_id})"
            
            embed.add_field(
                name="🔗 Links",
                value=links,
                inline=False
            )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Person error: {e}", exc_info=True)
            await interaction.followup.send("❌ Error fetching person information.", ephemeral=True)
    
    @app_commands.command(name="filmography", description="View complete filmography of an actor/director")
    @app_commands.describe(name="Person's name")
    async def filmography(self, interaction: discord.Interaction, name: str):
        """Get complete filmography"""
        await interaction.response.defer()
        
        try:
            # Search for person
            search_results = await self.tmdb.search_multi(name)
            people = [r for r in search_results.get('results', []) if r.get('media_type') == 'person']
            
            if not people:
                await interaction.followup.send("❌ Person not found.", ephemeral=True)
                return
            
            person_data = people[0]
            person_id = person_data.get('id')
            person_name = person_data.get('name')
            
            # Get credits
            details = await self.tmdb.get_person_details(person_id)
            credits = details.get('combined_credits', {})
            
            cast_credits = credits.get('cast', [])
            crew_credits = credits.get('crew', [])
            
            # Sort by date
            all_credits = cast_credits + crew_credits
            all_credits.sort(key=lambda x: x.get('release_date') or x.get('first_air_date') or '9999', reverse=True)
            
            if not all_credits:
                await interaction.followup.send("❌ No filmography available.", ephemeral=True)
                return
            
            # Create embeds
            embeds = []
            for i in range(0, len(all_credits), 10):
                chunk = all_credits[i:i+10]
                
                embed = create_embed_base(
                    title=f"🎬 Filmography - {person_name}",
                    description=f"Showing {i+1}-{min(i+10, len(all_credits))} of {len(all_credits)} credits"
                )
                
                for credit in chunk:
                    title = credit.get('title') or credit.get('name', 'Unknown')
                    media_type = credit.get('media_type', 'unknown')
                    date = credit.get('release_date') or credit.get('first_air_date', 'TBA')
                    year = date[:4] if date and date != 'TBA' else 'TBA'
                    
                    role = credit.get('character') or credit.get('job', 'Unknown')
                    
                    embed.add_field(
                        name=f"{get_media_type_emoji(media_type)} {title} ({year})",
                        value=f"as **{role}**",
                        inline=False
                    )
                
                embeds.append(embed)
            
            # Send with pagination
            if len(embeds) == 1:
                await interaction.followup.send(embed=embeds[0])
            else:
                view = EmbedPaginationView(embeds, timeout=Config.PAGINATION_TIMEOUT)
                await interaction.followup.send(embed=embeds[0], view=view)
            
        except Exception as e:
            self.logger.error(f"Filmography error: {e}", exc_info=True)
            await interaction.followup.send("❌ Error fetching filmography.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(CastCrew(bot))