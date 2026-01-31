"""
Awards & Film Festivals Cog
Oscar winners, Golden Globes, Cannes, and other prestigious awards
"""
import logging
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional

import discord
from discord import app_commands
from discord.ext import commands

from core.config import Config
from services.tmdb_client import TMDBClient
from utils.helpers import create_embed_base, format_date, get_media_type_emoji, get_rating_emoji
from utils.views import EmbedPaginationView


class Awards(commands.Cog):
    """Awards and film festival information"""
    
    # Award categories mapping
    OSCAR_CATEGORIES = {
        'best_picture': 'Best Picture',
        'best_director': 'Best Director',
        'best_actor': 'Best Actor',
        'best_actress': 'Best Actress',
        'best_supporting_actor': 'Best Supporting Actor',
        'best_supporting_actress': 'Best Supporting Actress',
        'best_original_screenplay': 'Best Original Screenplay',
        'best_adapted_screenplay': 'Best Adapted Screenplay',
        'best_cinematography': 'Best Cinematography',
        'best_visual_effects': 'Best Visual Effects',
        'best_animated_feature': 'Best Animated Feature',
        'best_international_feature': 'Best International Feature'
    }
    
    FESTIVALS = {
        'cannes': '🎬 Cannes Film Festival',
        'venice': '🦁 Venice Film Festival',
        'berlin': '🐻 Berlin International Film Festival',
        'sundance': '⛰️ Sundance Film Festival',
        'toronto': '🍁 Toronto International Film Festival',
        'tribeca': '🗽 Tribeca Film Festival'
    }
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger('FilmBot.Awards')
        self.tmdb = TMDBClient(Config.TMDB_API_KEY)
    
    async def cog_unload(self):
        await self.tmdb.close()
    
    @app_commands.command(name="oscar-winners", description="View Oscar winners by year")
    @app_commands.describe(year="Year of the Academy Awards (e.g., 2024)")
    async def oscar_winners(self, interaction: discord.Interaction, year: int):
        """Get Oscar winners for a specific year"""
        await interaction.response.defer()
        
        try:
            # Search for movies from that year with high ratings
            results = await self.tmdb.discover_movies(
                primary_release_year=year,
                sort_by='vote_average.desc',
                **{'vote_count.gte': 500}
            )
            
            movies = results.get('results', [])[:10]
            
            if not movies:
                await interaction.followup.send(f"❌ No notable films found for {year}.", ephemeral=True)
                return
            
            embed = create_embed_base(
                title=f"🏆 {year} Oscar Season - Notable Films",
                description=f"Top-rated films from {year} (Oscar ceremony typically held in {year + 1})"
            )
            
            for i, movie in enumerate(movies[:5], 1):
                title = movie.get('title', 'Unknown')
                rating = movie.get('vote_average', 0)
                votes = movie.get('vote_count', 0)
                
                # Get full details for additional info
                details = await self.tmdb.get_movie_details(movie['id'])
                budget = details.get('budget', 0)
                revenue = details.get('revenue', 0)
                
                from utils.helpers import format_money
                
                field_value = f"{get_rating_emoji(rating)} {rating:.1f}/10 ({votes:,} votes)"
                if budget > 0:
                    field_value += f"\n💰 Budget: {format_money(budget)}"
                if revenue > 0:
                    field_value += f"\n💵 Revenue: {format_money(revenue)}"
                
                embed.add_field(
                    name=f"{i}. 🎬 {title}",
                    value=field_value,
                    inline=False
                )
            
            embed.add_field(
                name="ℹ️ Note",
                value="This shows top-rated films from the year. For official Oscar winners, visit [oscars.org](https://www.oscars.org)",
                inline=False
            )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Oscar winners error: {e}", exc_info=True)
            await interaction.followup.send("❌ Error fetching Oscar information.", ephemeral=True)
    
    @app_commands.command(name="best-picture-nominees", description="Search for Best Picture nominees")
    @app_commands.describe(
        year="Year to search",
        min_rating="Minimum rating"
    )
    async def best_picture_nominees(self, interaction: discord.Interaction, year: int, min_rating: float = 7.5):
        """Find potential Best Picture nominees"""
        await interaction.response.defer()
        
        try:
            # Discover highly-rated films from the year
            results = await self.tmdb.discover_movies(
                primary_release_year=year,
                sort_by='vote_average.desc',
                **{
                    'vote_count.gte': 1000,
                    'vote_average.gte': min_rating
                }
            )
            
            movies = results.get('results', [])[:15]
            
            # Create embeds
            embeds = []
            for movie in movies:
                title = movie.get('title')
                rating = movie.get('vote_average', 0)
                overview = movie.get('overview', 'No description')[:400]
                
                embed = create_embed_base(
                    title=f"🏆 {title}",
                    description=overview
                )
                
                # Get detailed info
                details = await self.tmdb.get_movie_details(movie['id'])
                
                embed.add_field(
                    name=f"{get_rating_emoji(rating)} Rating",
                    value=f"{rating:.1f}/10 ({movie.get('vote_count', 0):,} votes)",
                    inline=True
                )
                
                # Genres
                genres = details.get('genres', [])
                if genres:
                    genre_text = ", ".join([g['name'] for g in genres[:3]])
                    embed.add_field(
                        name="🎭 Genres",
                        value=genre_text,
                        inline=True
                    )
                
                # Runtime
                runtime = details.get('runtime')
                if runtime:
                    from utils.helpers import format_runtime
                    embed.add_field(
                        name="⏱️ Runtime",
                        value=format_runtime(runtime),
                        inline=True
                    )
                
                # Director
                credits = details.get('credits', {})
                crew = credits.get('crew', [])
                directors = [p['name'] for p in crew if p.get('job') == 'Director']
                if directors:
                    embed.add_field(
                        name="🎬 Director",
                        value=", ".join(directors[:2]),
                        inline=True
                    )
                
                # Budget & Revenue
                budget = details.get('budget', 0)
                revenue = details.get('revenue', 0)
                if budget > 0 or revenue > 0:
                    from utils.helpers import format_money
                    money_info = []
                    if budget > 0:
                        money_info.append(f"Budget: {format_money(budget)}")
                    if revenue > 0:
                        money_info.append(f"Revenue: {format_money(revenue)}")
                    
                    embed.add_field(
                        name="💰 Box Office",
                        value="\n".join(money_info),
                        inline=True
                    )
                
                # Poster
                if movie.get('poster_path'):
                    embed.set_image(url=Config.get_tmdb_image_url(movie['poster_path'], 'w780'))
                
                embeds.append(embed)
            
            if not embeds:
                await interaction.followup.send(f"❌ No highly-rated films found for {year}.", ephemeral=True)
                return
            
            # Send with pagination
            view = EmbedPaginationView(embeds, timeout=Config.PAGINATION_TIMEOUT)
            await interaction.followup.send(
                content=f"🏆 **Potential Best Picture Nominees - {year}**",
                embed=embeds[0],
                view=view
            )
            
        except Exception as e:
            self.logger.error(f"Best Picture nominees error: {e}", exc_info=True)
            await interaction.followup.send("❌ Error searching for nominees.", ephemeral=True)
    
    @app_commands.command(name="award-winning-directors", description="Find films by award-winning directors")
    @app_commands.describe(director="Director name")
    async def award_winning_directors(self, interaction: discord.Interaction, director: str):
        """Search for films by award-winning directors"""
        await interaction.response.defer()
        
        try:
            # Search for the director
            search_results = await self.tmdb.search_multi(director)
            people = [r for r in search_results.get('results', []) if r.get('media_type') == 'person']
            
            if not people:
                await interaction.followup.send("❌ Director not found.", ephemeral=True)
                return
            
            person = people[0]
            person_id = person.get('id')
            person_name = person.get('name')
            
            # Get person details with filmography
            details = await self.tmdb.get_person_details(person_id)
            credits = details.get('combined_credits', {})
            crew_credits = credits.get('crew', [])
            
            # Filter directing credits
            directing = [c for c in crew_credits if c.get('job') == 'Director']
            
            # Sort by rating
            directing.sort(key=lambda x: (x.get('vote_average', 0), x.get('vote_count', 0)), reverse=True)
            
            if not directing:
                await interaction.followup.send(f"❌ No directing credits found for {person_name}.", ephemeral=True)
                return
            
            embed = create_embed_base(
                title=f"🎬 Films Directed by {person_name}",
                description=f"Total films directed: {len(directing)}"
            )
            
            # Show top films
            for i, credit in enumerate(directing[:10], 1):
                title = credit.get('title') or credit.get('name', 'Unknown')
                rating = credit.get('vote_average', 0)
                year = ''
                
                release_date = credit.get('release_date') or credit.get('first_air_date')
                if release_date:
                    year = f" ({release_date[:4]})"
                
                embed.add_field(
                    name=f"{i}. {title}{year}",
                    value=f"{get_rating_emoji(rating)} {rating:.1f}/10",
                    inline=False
                )
            
            # Add profile image
            if details.get('profile_path'):
                embed.set_thumbnail(url=Config.get_tmdb_image_url(details['profile_path'], 'w185'))
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Award-winning directors error: {e}", exc_info=True)
            await interaction.followup.send("❌ Error fetching director information.", ephemeral=True)
    
    @app_commands.command(name="cannes-winners", description="Top-rated films by year (Cannes style)")
    @app_commands.describe(year="Year")
    async def cannes_winners(self, interaction: discord.Interaction, year: int):
        """Get Cannes Film Festival style winners"""
        await interaction.response.defer()
        
        try:
            # Get international films from that year
            results = await self.tmdb.discover_movies(
                primary_release_year=year,
                sort_by='vote_average.desc',
                **{
                    'vote_count.gte': 200,
                    'vote_average.gte': 7.0
                }
            )
            
            movies = results.get('results', [])[:8]
            
            embed = create_embed_base(
                title=f"🎬 {year} - Festival Quality Films",
                description=f"Critically acclaimed films from {year}"
            )
            
            categories = [
                "🏆 Palme d'Or Contender",
                "🥇 Grand Prix Quality",
                "🎭 Best Director Style",
                "🎬 Best Actor Showcase",
                "🌟 Best Actress Showcase",
                "📽️ Camera d'Or Candidate",
                "🎨 Special Jury Prize",
                "✨ Critics' Choice"
            ]
            
            for i, (movie, category) in enumerate(zip(movies, categories)):
                title = movie.get('title')
                rating = movie.get('vote_average', 0)
                
                embed.add_field(
                    name=f"{category}",
                    value=f"**{title}** - {get_rating_emoji(rating)} {rating:.1f}/10",
                    inline=False
                )
            
            embed.add_field(
                name="ℹ️ Note",
                value="Based on critical acclaim. For official Cannes winners, visit [festival-cannes.com](https://www.festival-cannes.com)",
                inline=False
            )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Cannes winners error: {e}", exc_info=True)
            await interaction.followup.send("❌ Error fetching festival information.", ephemeral=True)
    
    @app_commands.command(name="golden-globes", description="Golden Globe style winners")
    @app_commands.describe(year="Year", category="Award category")
    @app_commands.choices(category=[
        app_commands.Choice(name="Drama", value="drama"),
        app_commands.Choice(name="Musical/Comedy", value="comedy"),
        app_commands.Choice(name="All", value="all")
    ])
    async def golden_globes(self, interaction: discord.Interaction, year: int, category: str = "all"):
        """Get Golden Globe style winners"""
        await interaction.response.defer()
        
        try:
            # Get films from the year
            results = await self.tmdb.discover_movies(
                primary_release_year=year,
                sort_by='popularity.desc',
                **{'vote_count.gte': 500}
            )
            
            movies = results.get('results', [])[:20]
            
            # Categorize by genre
            drama_films = []
            comedy_films = []
            
            for movie in movies:
                details = await self.tmdb.get_movie_details(movie['id'])
                genres = [g['name'] for g in details.get('genres', [])]
                
                if 'Comedy' in genres or 'Music' in genres or 'Musical' in genres:
                    comedy_films.append(details)
                else:
                    drama_films.append(details)
            
            embed = create_embed_base(
                title=f"🌟 {year} Golden Globe Style - Top Films",
                description=f"Award-worthy performances from {year}"
            )
            
            if category in ['drama', 'all'] and drama_films:
                drama_list = []
                for film in drama_films[:5]:
                    title = film.get('title')
                    rating = film.get('vote_average', 0)
                    drama_list.append(f"• **{title}** - {get_rating_emoji(rating)} {rating:.1f}/10")
                
                embed.add_field(
                    name="🎭 Best Motion Picture - Drama",
                    value="\n".join(drama_list),
                    inline=False
                )
            
            if category in ['comedy', 'all'] and comedy_films:
                comedy_list = []
                for film in comedy_films[:5]:
                    title = film.get('title')
                    rating = film.get('vote_average', 0)
                    comedy_list.append(f"• **{title}** - {get_rating_emoji(rating)} {rating:.1f}/10")
                
                embed.add_field(
                    name="🎭 Best Motion Picture - Musical or Comedy",
                    value="\n".join(comedy_list),
                    inline=False
                )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Golden Globes error: {e}", exc_info=True)
            await interaction.followup.send("❌ Error fetching award information.", ephemeral=True)
    
    @app_commands.command(name="film-festivals", description="Explore major film festivals")
    @app_commands.describe(festival="Film festival name")
    @app_commands.choices(festival=[
        app_commands.Choice(name="Cannes Film Festival", value="cannes"),
        app_commands.Choice(name="Venice Film Festival", value="venice"),
        app_commands.Choice(name="Berlin Film Festival", value="berlin"),
        app_commands.Choice(name="Sundance Film Festival", value="sundance"),
        app_commands.Choice(name="Toronto Film Festival", value="toronto"),
        app_commands.Choice(name="Tribeca Film Festival", value="tribeca")
    ])
    async def film_festivals(self, interaction: discord.Interaction, festival: str):
        """Get information about major film festivals"""
        await interaction.response.defer()
        
        try:
            festival_info = {
                'cannes': {
                    'full_name': 'Festival de Cannes',
                    'location': 'Cannes, France',
                    'founded': '1946',
                    'when': 'May',
                    'top_award': "Palme d'Or",
                    'description': 'The most prestigious film festival in the world, showcasing the best of international cinema.',
                    'genre_focus': 'Arthouse, International'
                },
                'venice': {
                    'full_name': 'Venice Film Festival',
                    'location': 'Venice, Italy',
                    'founded': '1932',
                    'when': 'August-September',
                    'top_award': 'Golden Lion',
                    'description': "The world's oldest film festival, part of the Venice Biennale.",
                    'genre_focus': 'International, Arthouse'
                },
                'berlin': {
                    'full_name': 'Berlin International Film Festival (Berlinale)',
                    'location': 'Berlin, Germany',
                    'founded': '1951',
                    'when': 'February',
                    'top_award': 'Golden Bear',
                    'description': 'One of Europe\'s "Big Three" film festivals, known for political and artistic films.',
                    'genre_focus': 'Political, International'
                },
                'sundance': {
                    'full_name': 'Sundance Film Festival',
                    'location': 'Park City, Utah, USA',
                    'founded': '1978',
                    'when': 'January',
                    'top_award': 'Grand Jury Prize',
                    'description': 'The largest independent film festival in the United States.',
                    'genre_focus': 'Independent, Documentary'
                },
                'toronto': {
                    'full_name': 'Toronto International Film Festival (TIFF)',
                    'location': 'Toronto, Canada',
                    'founded': '1976',
                    'when': 'September',
                    'top_award': "People's Choice Award",
                    'description': 'Major platform for Oscar contenders and international premieres.',
                    'genre_focus': 'Mainstream, International'
                },
                'tribeca': {
                    'full_name': 'Tribeca Film Festival',
                    'location': 'New York City, USA',
                    'founded': '2002',
                    'when': 'April-May',
                    'top_award': 'Best Narrative Feature',
                    'description': 'Founded by Robert De Niro after 9/11 to revitalize Lower Manhattan.',
                    'genre_focus': 'Independent, Diverse'
                }
            }
            
            info = festival_info[festival]
            
            embed = create_embed_base(
                title=f"{self.FESTIVALS[festival]}",
                description=info['description']
            )
            
            embed.add_field(name="📍 Location", value=info['location'], inline=True)
            embed.add_field(name="📅 When", value=info['when'], inline=True)
            embed.add_field(name="🗓️ Founded", value=info['founded'], inline=True)
            
            embed.add_field(name="🏆 Top Award", value=info['top_award'], inline=True)
            embed.add_field(name="🎬 Focus", value=info['genre_focus'], inline=True)
            
            # Get some highly-rated international films
            current_year = datetime.now().year
            results = await self.tmdb.discover_movies(
                primary_release_year=current_year,
                sort_by='vote_average.desc',
                **{
                    'vote_count.gte': 100,
                    'vote_average.gte': 7.5
                }
            )
            
            movies = results.get('results', [])[:5]
            
            if movies:
                movie_list = []
                for movie in movies:
                    title = movie.get('title')
                    rating = movie.get('vote_average', 0)
                    movie_list.append(f"• {title} ({rating:.1f}/10)")
                
                embed.add_field(
                    name=f"🎬 {current_year} Festival-Worthy Films",
                    value="\n".join(movie_list),
                    inline=False
                )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Film festivals error: {e}", exc_info=True)
            await interaction.followup.send("❌ Error fetching festival information.", ephemeral=True)
    
    @app_commands.command(name="acting-awards", description="Find films with award-worthy performances")
    @app_commands.describe(
        actor="Actor name",
        year="Optional year filter"
    )
    async def acting_awards(self, interaction: discord.Interaction, actor: str, year: Optional[int] = None):
        """Search for award-worthy acting performances"""
        await interaction.response.defer()
        
        try:
            # Search for actor
            search_results = await self.tmdb.search_multi(actor)
            people = [r for r in search_results.get('results', []) if r.get('media_type') == 'person']
            
            if not people:
                await interaction.followup.send("❌ Actor not found.", ephemeral=True)
                return
            
            person = people[0]
            person_id = person.get('id')
            person_name = person.get('name')
            
            # Get filmography
            details = await self.tmdb.get_person_details(person_id)
            credits = details.get('combined_credits', {})
            cast_credits = credits.get('cast', [])
            
            # Filter by year if specified
            if year:
                cast_credits = [c for c in cast_credits if 
                              (c.get('release_date', '')[:4] == str(year)) or
                              (c.get('first_air_date', '')[:4] == str(year))]
            
            # Sort by rating
            cast_credits.sort(key=lambda x: (x.get('vote_average', 0), x.get('vote_count', 0)), reverse=True)
            
            if not cast_credits:
                await interaction.followup.send(f"❌ No performances found for {person_name}.", ephemeral=True)
                return
            
            # Create embeds
            embeds = []
            for credit in cast_credits[:10]:
                title = credit.get('title') or credit.get('name')
                character = credit.get('character', 'Unknown Role')
                rating = credit.get('vote_average', 0)
                media_type = credit.get('media_type', 'movie')
                
                release_date = credit.get('release_date') or credit.get('first_air_date', '')
                year_str = release_date[:4] if release_date else 'N/A'
                
                embed = create_embed_base(
                    title=f"{get_media_type_emoji(media_type)} {title} ({year_str})",
                    description=f"**Role:** {character}\n\n{credit.get('overview', 'No description')[:300]}"
                )
                
                embed.add_field(
                    name=f"{get_rating_emoji(rating)} Rating",
                    value=f"{rating:.1f}/10",
                    inline=True
                )
                
                embed.add_field(
                    name="🎭 Performance",
                    value=f"by **{person_name}**",
                    inline=True
                )
                
                if credit.get('poster_path'):
                    embed.set_image(url=Config.get_tmdb_image_url(credit['poster_path'], 'w780'))
                
                embeds.append(embed)
            
            if not embeds:
                await interaction.followup.send("❌ No performances found.", ephemeral=True)
                return
            
            view = EmbedPaginationView(embeds, timeout=Config.PAGINATION_TIMEOUT)
            year_text = f" in {year}" if year else ""
            await interaction.followup.send(
                content=f"🎭 **Award-Worthy Performances by {person_name}{year_text}**",
                embed=embeds[0],
                view=view
            )
            
        except Exception as e:
            self.logger.error(f"Acting awards error: {e}", exc_info=True)
            await interaction.followup.send("❌ Error fetching performance information.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Awards(bot))