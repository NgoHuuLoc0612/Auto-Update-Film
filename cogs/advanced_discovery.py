"""
Advanced Discovery Cog
Enhanced content discovery with decades, countries, languages, runtime, and more
"""
import logging
from typing import Dict, List, Optional

import discord
from discord import app_commands
from discord.ext import commands

from core.config import Config
from services.tmdb_client import TMDBClient
from utils.helpers import create_embed_base, format_runtime, get_media_type_emoji, get_rating_emoji
from utils.views import EmbedPaginationView


class AdvancedDiscovery(commands.Cog):
    """Advanced content discovery features"""
    
    DECADES = {
        '2020s': (2020, 2029),
        '2010s': (2010, 2019),
        '2000s': (2000, 2009),
        '1990s': (1990, 1999),
        '1980s': (1980, 1989),
        '1970s': (1970, 1979),
        '1960s': (1960, 1969),
        '1950s': (1950, 1959)
    }
    
    COUNTRIES = {
        'ad': 'Andorra',
        'ae': 'United Arab Emirates',
        'af': 'Afghanistan',
        'ag': 'Antigua and Barbuda',
        'ai': 'Anguilla',
        'al': 'Albania',
        'am': 'Armenia',
        'ao': 'Angola',
        'aq': 'Antarctica',
        'ar': 'Argentina',
        'as': 'American Samoa',
        'at': 'Austria',
        'au': 'Australia',
        'aw': 'Aruba',
        'ax': 'Åland Islands',
        'az': 'Azerbaijan',
        'ba': 'Bosnia and Herzegovina',
        'bb': 'Barbados',
        'bd': 'Bangladesh',
        'be': 'Belgium',
        'bf': 'Burkina Faso',
        'bg': 'Bulgaria',
        'bh': 'Bahrain',
        'bi': 'Burundi',
        'bj': 'Benin',
        'bl': 'Saint Barthélemy',
        'bm': 'Bermuda',
        'bn': 'Brunei Darussalam',
        'bo': 'Bolivia',
        'bq': 'Bonaire, Sint Eustatius and Saba',
        'br': 'Brazil',
        'bs': 'Bahamas',
        'bt': 'Bhutan',
        'bv': 'Bouvet Island',
        'bw': 'Botswana',
        'by': 'Belarus',
        'bz': 'Belize',
        'ca': 'Canada',
        'cc': 'Cocos Islands',
        'cd': 'Democratic Republic of the Congo',
        'cf': 'Central African Republic',
        'cg': 'Congo',
        'ch': 'Switzerland',
        'ci': 'Côte d\'Ivoire',
        'ck': 'Cook Islands',
        'cl': 'Chile',
        'cm': 'Cameroon',
        'cn': 'China',
        'co': 'Colombia',
        'cr': 'Costa Rica',
        'cu': 'Cuba',
        'cv': 'Cabo Verde',
        'cw': 'Curaçao',
        'cx': 'Christmas Island',
        'cy': 'Cyprus',
        'cz': 'Czechia',
        'de': 'Germany',
        'dj': 'Djibouti',
        'dk': 'Denmark',
        'dm': 'Dominica',
        'do': 'Dominican Republic',
        'dz': 'Algeria',
        'ec': 'Ecuador',
        'ee': 'Estonia',
        'eg': 'Egypt',
        'eh': 'Western Sahara',
        'er': 'Eritrea',
        'es': 'Spain',
        'et': 'Ethiopia',
        'fi': 'Finland',
        'fj': 'Fiji',
        'fk': 'Falkland Islands',
        'fm': 'Micronesia',
        'fo': 'Faroe Islands',
        'fr': 'France',
        'ga': 'Gabon',
        'gb': 'United Kingdom',
        'gd': 'Grenada',
        'ge': 'Georgia',
        'gf': 'French Guiana',
        'gg': 'Guernsey',
        'gh': 'Ghana',
        'gi': 'Gibraltar',
        'gl': 'Greenland',
        'gm': 'Gambia',
        'gn': 'Guinea',
        'gp': 'Guadeloupe',
        'gq': 'Equatorial Guinea',
        'gr': 'Greece',
        'gs': 'South Georgia and the South Sandwich Islands',
        'gt': 'Guatemala',
        'gu': 'Guam',
        'gw': 'Guinea-Bissau',
        'gy': 'Guyana',
        'hk': 'Hong Kong',
        'hm': 'Heard Island and McDonald Islands',
        'hn': 'Honduras',
        'hr': 'Croatia',
        'ht': 'Haiti',
        'hu': 'Hungary',
        'id': 'Indonesia',
        'ie': 'Ireland',
        'il': 'Israel',
        'im': 'Isle of Man',
        'in': 'India',
        'io': 'British Indian Ocean Territory',
        'iq': 'Iraq',
        'ir': 'Iran',
        'is': 'Iceland',
        'it': 'Italy',
        'je': 'Jersey',
        'jm': 'Jamaica',
        'jo': 'Jordan',
        'jp': 'Japan',
        'ke': 'Kenya',
        'kg': 'Kyrgyzstan',
        'kh': 'Cambodia',
        'ki': 'Kiribati',
        'km': 'Comoros',
        'kn': 'Saint Kitts and Nevis',
        'kp': 'North Korea',
        'kr': 'Korea',
        'kw': 'Kuwait',
        'ky': 'Cayman Islands',
        'kz': 'Kazakhstan',
        'la': 'Laoss',
        'lb': 'Lebanon',
        'lc': 'Saint Lucia',
        'li': 'Liechtenstein',
        'lk': 'Sri Lanka',
        'lr': 'Liberia',
        'ls': 'Lesotho',
        'lt': 'Lithuania',
        'lu': 'Luxembourg',
        'lv': 'Latvia',
        'ly': 'Libya',
        'ma': 'Morocco',
        'mc': 'Monaco',
        'md': 'Moldova',
        'me': 'Montenegro',
        'mf': 'Saint Martin',
        'mg': 'Madagascar',
        'mh': 'Marshall Islands',
        'mk': 'Republic of North Macedonia',
        'ml': 'Mali',
        'mm': 'Myanmar',
        'mn': 'Mongolia',
        'mo': 'Macao',
        'mp': 'Northern Mariana Islands',
        'mq': 'Martinique',
        'mr': 'Mauritania',
        'ms': 'Montserrat',
        'mt': 'Malta',
        'mu': 'Mauritius',
        'mv': 'Maldives',
        'mw': 'Malawi',
        'mx': 'Mexico',
        'my': 'Malaysia',
        'mz': 'Mozambique',
        'na': 'Namibia',
        'nc': 'New Caledonia',
        'ne': 'Niger',
        'nf': 'Norfolk Island',
        'ng': 'Nigeria',
        'ni': 'Nicaragua',
        'nl': 'Netherlands',
        'no': 'Norway',
        'np': 'Nepal',
        'nr': 'Nauru',
        'nu': 'Niue',
        'nz': 'New Zealand',
        'om': 'Oman',
        'pa': 'Panama',
        'pe': 'Peru',
        'pf': 'French Polynesia',
        'pg': 'Papua New Guinea',
        'ph': 'Philippines',
        'pk': 'Pakistan',
        'pl': 'Poland',
        'pm': 'Saint Pierre and Miquelon',
        'pn': 'Pitcairn',
        'pr': 'Puerto Rico',
        'ps': 'Palestine, State of',
        'pt': 'Portugal',
        'pw': 'Palau',
        'py': 'Paraguay',
        'qa': 'Qatar',
        're': 'Réunion',
        'ro': 'Romania',
        'rs': 'Serbia',
        'ru': 'Russian Federation',
        'rw': 'Rwanda',
        'sa': 'Saudi Arabia',
        'sb': 'Solomon Islands',
        'sc': 'Seychelles',
        'sd': 'Sudan',
        'se': 'Sweden',
        'sg': 'Singapore',
        'sh': 'Saint Helena, Ascension and Tristan da Cunha',
        'si': 'Slovenia',
        'sj': 'Svalbard and Jan Mayen',
        'sk': 'Slovakia',
        'sl': 'Sierra Leone',
        'sm': 'San Marino',
        'sn': 'Senegal',
        'so': 'Somalia',
        'sr': 'Suriname',
        'ss': 'South Sudan',
        'st': 'Sao Tome and Principe',
        'sv': 'El Salvador',
        'sx': 'Sint Maarten',
        'sy': 'Syrian Arab Republic',
        'sz': 'Eswatini',
        'tc': 'Turks and Caicos Islands',
        'td': 'Chad',
        'tf': 'French Southern Territories',
        'tg': 'Togo',
        'th': 'Thailand',
        'tj': 'Tajikistan',
        'tk': 'Tokelau',
        'tl': 'Timor-Leste',
        'tm': 'Turkmenistan',
        'tn': 'Tunisia',
        'to': 'Tonga',
        'tr': 'Turkey',
        'tt': 'Trinidad and Tobago',
        'tv': 'Tuvalu',
        'tw': 'Taiwan',
        'tz': 'Tanzania',
        'ua': 'Ukraine',
        'ug': 'Uganda',
        'um': 'United States Minor Outlying Islands',
        'us': 'United States',
        'uy': 'Uruguay',
        'uz': 'Uzbekistan',
        'va': 'Vatican City',
        'vc': 'Saint Vincent and the Grenadines',
        've': 'Venezuela',
        'vg': 'Virgin Islands British',
        'vi': 'Virgin Islands U.S.',
        'vn': 'Viet Nam',
        'vu': 'Vanuatu',
        'wf': 'Wallis and Futuna',
        'ws': 'Samoa',
        'ye': 'Yemen',
        'yt': 'Mayotte',
        'za': 'South Africa',
        'zm': 'Zambia',
        'zw': 'Zimbabwe'

    }
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger('FilmBot.AdvancedDiscovery')
        self.tmdb = TMDBClient(Config.TMDB_API_KEY)
    
    async def cog_unload(self):
        await self.tmdb.close()
    
    @app_commands.command(name="by-decade", description="Discover films from a specific decade")
    @app_commands.describe(
        decade="Which decade",
        min_rating="Minimum rating"
    )
    @app_commands.choices(decade=[
        app_commands.Choice(name="2020s", value="2020s"),
        app_commands.Choice(name="2010s", value="2010s"),
        app_commands.Choice(name="2000s", value="2000s"),
        app_commands.Choice(name="1990s", value="1990s"),
        app_commands.Choice(name="1980s", value="1980s"),
        app_commands.Choice(name="1970s", value="1970s"),
        app_commands.Choice(name="1960s", value="1960s"),
        app_commands.Choice(name="1950s", value="1950s")
    ])
    async def by_decade(self, interaction: discord.Interaction, decade: str, min_rating: float = 7.0):
        """Discover films from a specific decade"""
        await interaction.response.defer()
        
        try:
            start_year, end_year = self.DECADES[decade]
            
            # Get films from the decade
            results = await self.tmdb.discover_movies(
                **{
                    'primary_release_date.gte': f'{start_year}-01-01',
                    'primary_release_date.lte': f'{end_year}-12-31',
                    'vote_average.gte': min_rating,
                    'vote_count.gte': 100,
                    'sort_by': 'vote_average.desc'
                }
            )
            
            movies = results.get('results', [])[:15]
            
            if not movies:
                await interaction.followup.send(f"❌ No films found from the {decade}.", ephemeral=True)
                return
            
            embed = create_embed_base(
                title=f"🎬 Best of the {decade}",
                description=f"Top-rated films from {start_year}-{end_year}"
            )
            
            for i, movie in enumerate(movies[:10], 1):
                title = movie.get('title')
                rating = movie.get('vote_average', 0)
                year = movie.get('release_date', '')[:4]
                
                embed.add_field(
                    name=f"{i}. {title} ({year})",
                    value=f"{get_rating_emoji(rating)} {rating:.1f}/10",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"By decade error: {e}", exc_info=True)
            await interaction.followup.send("❌ Error discovering films.", ephemeral=True)
    
    async def country_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete for country selection"""
        # Filter countries based on current input
        current_lower = current.lower()
        choices = []
        
        for code, name in sorted(self.COUNTRIES.items(), key=lambda item: item[1]):
            if current_lower in name.lower() or current_lower in code.lower():
                choices.append(app_commands.Choice(name=name, value=code))
                if len(choices) >= 25:  # Discord limit
                    break
        
        # If no matches or empty input, return top 25 popular countries
        if not choices:
            popular_countries = ['us', 'gb', 'fr', 'de', 'jp', 'kr', 'cn', 'in', 'ca', 'au',
                                'es', 'it', 'mx', 'br', 'ru', 'ar', 'nl', 'se', 'no', 'dk',
                                'fi', 'be', 'ch', 'at', 'nz']
            choices = [
                app_commands.Choice(name=self.COUNTRIES[code], value=code)
                for code in popular_countries if code in self.COUNTRIES
            ]
        
        return choices
    
    @app_commands.command(name="by-country", description="Discover films from a specific country")
    @app_commands.describe(country="Country of origin (type to search)")
    @app_commands.autocomplete(country=country_autocomplete)
    async def by_country(self, interaction: discord.Interaction, country: str):
        """Discover films from a specific country"""
        await interaction.response.defer()
        
        try:
            country_name = self.COUNTRIES[country]
            
            # Discover films
            results = await self.tmdb.discover_movies(
                **{
                    'with_origin_country': country.upper(),
                    'sort_by': 'vote_average.desc',
                    'vote_count.gte': 50
                }
            )
            
            movies = results.get('results', [])[:15]
            
            if not movies:
                await interaction.followup.send(f"❌ No films found from {country_name}.", ephemeral=True)
                return
            
            # Create embeds
            embeds = []
            for movie in movies:
                title = movie.get('title')
                rating = movie.get('vote_average', 0)
                overview = movie.get('overview', 'No description')[:400]
                year = movie.get('release_date', '')[:4] if movie.get('release_date') else 'N/A'
                
                embed = create_embed_base(
                    title=f"🎬 {title} ({year})",
                    description=overview
                )
                
                embed.add_field(
                    name=f"{get_rating_emoji(rating)} Rating",
                    value=f"{rating:.1f}/10 ({movie.get('vote_count', 0):,} votes)",
                    inline=True
                )
                
                embed.add_field(
                    name="🌍 Origin",
                    value=country_name,
                    inline=True
                )
                
                if movie.get('poster_path'):
                    embed.set_thumbnail(url=Config.get_tmdb_image_url(movie['poster_path'], 'w342'))
                
                embeds.append(embed)
            
            view = EmbedPaginationView(embeds, timeout=Config.PAGINATION_TIMEOUT)
            await interaction.followup.send(
                content=f"🎬 **Films from {country_name}**",
                embed=embeds[0],
                view=view
            )
            
        except Exception as e:
            self.logger.error(f"By country error: {e}", exc_info=True)
            await interaction.followup.send("❌ Error discovering films.", ephemeral=True)
    
    @app_commands.command(name="by-runtime", description="Find films by runtime length")
    @app_commands.describe(
        min_runtime="Minimum runtime (minutes)",
        max_runtime="Maximum runtime (minutes)"
    )
    async def by_runtime(self, interaction: discord.Interaction, min_runtime: int = 0, max_runtime: int = 300):
        """Find films by runtime"""
        await interaction.response.defer()
        
        try:
            results = await self.tmdb.discover_movies(
                **{
                    'with_runtime.gte': min_runtime,
                    'with_runtime.lte': max_runtime,
                    'sort_by': 'vote_average.desc',
                    'vote_count.gte': 500
                }
            )
            
            movies = results.get('results', [])[:15]
            
            if not movies:
                await interaction.followup.send("❌ No films found with that runtime.", ephemeral=True)
                return
            
            embed = create_embed_base(
                title=f"⏱️ Films {format_runtime(min_runtime)} - {format_runtime(max_runtime)}",
                description=f"Top-rated films in this runtime range"
            )
            
            for movie in movies[:10]:
                title = movie.get('title')
                rating = movie.get('vote_average', 0)
                
                # Get full details for runtime
                details = await self.tmdb.get_movie_details(movie['id'])
                runtime = details.get('runtime', 0)
                
                embed.add_field(
                    name=f"🎬 {title}",
                    value=f"{get_rating_emoji(rating)} {rating:.1f}/10 | ⏱️ {format_runtime(runtime)}",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"By runtime error: {e}", exc_info=True)
            await interaction.followup.send("❌ Error discovering films.", ephemeral=True)
    
    @app_commands.command(name="hidden-gems", description="Discover underrated hidden gems")
    @app_commands.describe(
        min_rating="Minimum rating",
        max_votes="Maximum vote count (lower = more hidden)"
    )
    async def hidden_gems(self, interaction: discord.Interaction, min_rating: float = 7.5, max_votes: int = 5000):
        """Find hidden gem films"""
        await interaction.response.defer()
        
        try:
            results = await self.tmdb.discover_movies(
                **{
                    'vote_average.gte': min_rating,
                    'vote_count.gte': 50,
                    'vote_count.lte': max_votes,
                    'sort_by': 'vote_average.desc'
                }
            )
            
            movies = results.get('results', [])[:15]
            
            if not movies:
                await interaction.followup.send("❌ No hidden gems found.", ephemeral=True)
                return
            
            # Create embeds
            embeds = []
            for movie in movies:
                title = movie.get('title')
                rating = movie.get('vote_average', 0)
                votes = movie.get('vote_count', 0)
                overview = movie.get('overview', 'No description')[:400]
                year = movie.get('release_date', '')[:4] if movie.get('release_date') else 'N/A'
                
                embed = create_embed_base(
                    title=f"💎 {title} ({year})",
                    description=overview
                )
                
                embed.add_field(
                    name=f"{get_rating_emoji(rating)} Rating",
                    value=f"{rating:.1f}/10",
                    inline=True
                )
                
                embed.add_field(
                    name="👥 Votes",
                    value=f"{votes:,}",
                    inline=True
                )
                
                embed.add_field(
                    name="💎 Hidden Gem Score",
                    value=f"{(rating * 10) / (votes / 100):.1f}",
                    inline=True
                )
                
                if movie.get('poster_path'):
                    embed.set_image(url=Config.get_tmdb_image_url(movie['poster_path'], 'w780'))
                
                embeds.append(embed)
            
            view = EmbedPaginationView(embeds, timeout=Config.PAGINATION_TIMEOUT)
            await interaction.followup.send(
                content="💎 **Hidden Gems - Underrated Films**",
                embed=embeds[0],
                view=view
            )
            
        except Exception as e:
            self.logger.error(f"Hidden gems error: {e}", exc_info=True)
            await interaction.followup.send("❌ Error finding hidden gems.", ephemeral=True)
    
    @app_commands.command(name="cult-classics", description="Find cult classic films")
    async def cult_classics(self, interaction: discord.Interaction):
        """Find cult classic films"""
        await interaction.response.defer()
        
        try:
            # Look for older films with strong ratings but not massive popularity
            results = await self.tmdb.discover_movies(
                **{
                    'primary_release_date.lte': '2010-12-31',
                    'vote_average.gte': 7.0,
                    'vote_count.gte': 500,
                    'vote_count.lte': 10000,
                    'sort_by': 'vote_average.desc'
                }
            )
            
            movies = results.get('results', [])[:15]
            
            # Create embeds
            embeds = []
            for movie in movies:
                title = movie.get('title')
                rating = movie.get('vote_average', 0)
                overview = movie.get('overview', 'No description')[:400]
                year = movie.get('release_date', '')[:4] if movie.get('release_date') else 'N/A'
                
                embed = create_embed_base(
                    title=f"🎭 {title} ({year})",
                    description=overview
                )
                
                embed.add_field(
                    name=f"{get_rating_emoji(rating)} Rating",
                    value=f"{rating:.1f}/10",
                    inline=True
                )
                
                # Get full details
                details = await self.tmdb.get_movie_details(movie['id'])
                
                genres = details.get('genres', [])
                if genres:
                    genre_text = ", ".join([g['name'] for g in genres[:3]])
                    embed.add_field(
                        name="🎭 Genres",
                        value=genre_text,
                        inline=True
                    )
                
                if movie.get('poster_path'):
                    embed.set_image(url=Config.get_tmdb_image_url(movie['poster_path'], 'w780'))
                
                embeds.append(embed)
            
            view = EmbedPaginationView(embeds, timeout=Config.PAGINATION_TIMEOUT)
            await interaction.followup.send(
                content="🎭 **Cult Classics**",
                embed=embeds[0],
                view=view
            )
            
        except Exception as e:
            self.logger.error(f"Cult classics error: {e}", exc_info=True)
            await interaction.followup.send("❌ Error finding cult classics.", ephemeral=True)
    
    @app_commands.command(name="critically-acclaimed", description="Find critically acclaimed films")
    @app_commands.describe(year="Optional year filter")
    async def critically_acclaimed(self, interaction: discord.Interaction, year: Optional[int] = None):
        """Find critically acclaimed films"""
        await interaction.response.defer()
        
        try:
            filters = {
                'vote_average.gte': 8.0,
                'vote_count.gte': 1000,
                'sort_by': 'vote_average.desc'
            }
            
            if year:
                filters['primary_release_year'] = year
            
            results = await self.tmdb.discover_movies(**filters)
            movies = results.get('results', [])[:15]
            
            if not movies:
                await interaction.followup.send("❌ No critically acclaimed films found.", ephemeral=True)
                return
            
            embed = create_embed_base(
                title=f"⭐ Critically Acclaimed Films{f' ({year})' if year else ''}",
                description="Films with exceptional critical reception"
            )
            
            for i, movie in enumerate(movies[:10], 1):
                title = movie.get('title')
                rating = movie.get('vote_average', 0)
                votes = movie.get('vote_count', 0)
                year_str = movie.get('release_date', '')[:4] if movie.get('release_date') else 'N/A'
                
                embed.add_field(
                    name=f"{i}. {title} ({year_str})",
                    value=f"{get_rating_emoji(rating)} {rating:.1f}/10 ({votes:,} votes)",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Critically acclaimed error: {e}", exc_info=True)
            await interaction.followup.send("❌ Error finding films.", ephemeral=True)
    
    @app_commands.command(name="box-office-hits", description="Find highest-grossing films")
    @app_commands.describe(year="Optional year filter")
    async def box_office_hits(self, interaction: discord.Interaction, year: Optional[int] = None):
        """Find box office hits"""
        await interaction.response.defer()
        
        try:
            filters = {
                'sort_by': 'revenue.desc',
                'vote_count.gte': 1000
            }
            
            if year:
                filters['primary_release_year'] = year
            
            results = await self.tmdb.discover_movies(**filters)
            movies = results.get('results', [])[:10]
            
            # Get full details for revenue
            embeds = []
            for movie in movies:
                details = await self.tmdb.get_movie_details(movie['id'])
                
                title = details.get('title')
                revenue = details.get('revenue', 0)
                budget = details.get('budget', 0)
                rating = details.get('vote_average', 0)
                overview = details.get('overview', 'No description')[:400]
                year_str = details.get('release_date', '')[:4] if details.get('release_date') else 'N/A'
                
                embed = create_embed_base(
                    title=f"💰 {title} ({year_str})",
                    description=overview
                )
                
                from utils.helpers import format_money
                
                if revenue > 0:
                    embed.add_field(
                        name="💵 Box Office",
                        value=format_money(revenue),
                        inline=True
                    )
                
                if budget > 0:
                    embed.add_field(
                        name="💰 Budget",
                        value=format_money(budget),
                        inline=True
                    )
                
                if revenue > 0 and budget > 0:
                    profit = revenue - budget
                    roi = (profit / budget * 100) if budget > 0 else 0
                    embed.add_field(
                        name="💹 Profit & ROI",
                        value=f"{format_money(profit)}\n{roi:.1f}% ROI",
                        inline=True
                    )
                
                embed.add_field(
                    name=f"{get_rating_emoji(rating)} Rating",
                    value=f"{rating:.1f}/10",
                    inline=True
                )
                
                if details.get('poster_path'):
                    embed.set_thumbnail(url=Config.get_tmdb_image_url(details['poster_path'], 'w342'))
                
                embeds.append(embed)
            
            if not embeds:
                await interaction.followup.send("❌ No box office data found.", ephemeral=True)
                return
            
            view = EmbedPaginationView(embeds, timeout=Config.PAGINATION_TIMEOUT)
            await interaction.followup.send(
                content=f"💰 **Box Office Hits{f' ({year})' if year else ''}**",
                embed=embeds[0],
                view=view
            )
            
        except Exception as e:
            self.logger.error(f"Box office hits error: {e}", exc_info=True)
            await interaction.followup.send("❌ Error fetching box office data.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AdvancedDiscovery(bot))