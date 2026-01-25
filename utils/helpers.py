"""
Utility helper functions
Various helper functions used throughout the bot
"""
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import discord
from discord.ext import commands


logger = logging.getLogger('FilmBot.Helpers')


async def load_extensions(bot: commands.Bot, cogs_dir: Path):
    """Load all extension files from cogs directory"""
    if not cogs_dir.exists():
        logger.warning(f"Cogs directory '{cogs_dir}' does not exist")
        return
    
    for file in cogs_dir.glob('*.py'):
        if file.name.startswith('_'):
            continue
        
        extension = f'{cogs_dir.name}.{file.stem}'
        try:
            await bot.load_extension(extension)
            logger.info(f"Loaded extension: {extension}")
        except Exception as e:
            logger.error(f"Failed to load extension {extension}: {e}", exc_info=True)


def format_runtime(minutes: int) -> str:
    """Format runtime from minutes to hours and minutes"""
    if not minutes:
        return "N/A"
    
    hours = minutes // 60
    mins = minutes % 60
    
    if hours > 0:
        return f"{hours}h {mins}m"
    return f"{mins}m"


def format_date(date_str: str, format: str = "%B %d, %Y") -> str:
    """Format date string to readable format"""
    if not date_str:
        return "N/A"
    
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        return date_obj.strftime(format)
    except ValueError:
        return date_str


def format_money(amount: int) -> str:
    """Format money amount to readable string"""
    if not amount:
        return "N/A"
    
    return f"${amount:,}"


def truncate_text(text: str, max_length: int = 1000, suffix: str = "...") -> str:
    """Truncate text to specified length"""
    if not text:
        return "N/A"
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def get_rating_emoji(rating: float) -> str:
    """Get emoji based on rating value"""
    if rating >= 8.0:
        return "⭐"
    elif rating >= 7.0:
        return "🌟"
    elif rating >= 6.0:
        return "✨"
    elif rating >= 5.0:
        return "💫"
    else:
        return "🌑"


def get_media_type_emoji(media_type: str) -> str:
    """Get emoji for media type"""
    emojis = {
        'movie': '🎬',
        'tv': '📺',
        'person': '👤',
        'collection': '📚'
    }
    return emojis.get(media_type, '🎭')


def get_genre_emoji(genre_name: str) -> str:
    """Get emoji for genre"""
    genre_emojis = {
        'Action': '💥',
        'Adventure': '🗺️',
        'Animation': '🎨',
        'Comedy': '😂',
        'Crime': '🔫',
        'Documentary': '🎥',
        'Drama': '🎭',
        'Family': '👨‍👩‍👧‍👦',
        'Fantasy': '🧙',
        'History': '📜',
        'Horror': '👻',
        'Music': '🎵',
        'Mystery': '🔍',
        'Romance': '💕',
        'Science Fiction': '🚀',
        'TV Movie': '📺',
        'Thriller': '😱',
        'War': '⚔️',
        'Western': '🤠'
    }
    return genre_emojis.get(genre_name, '🎬')


def create_progress_bar(current: int, total: int, length: int = 10) -> str:
    """Create a progress bar string"""
    if total == 0:
        return "░" * length
    
    filled = int((current / total) * length)
    bar = "█" * filled + "░" * (length - filled)
    percentage = int((current / total) * 100)
    
    return f"{bar} {percentage}%"


def get_video_url(video_key: str, site: str = "YouTube") -> str:
    """Get video URL from key and site"""
    if site == "YouTube":
        return f"https://www.youtube.com/watch?v={video_key}"
    return ""


def parse_credits(credits: Dict[str, Any], max_items: int = 5) -> tuple:
    """Parse credits data into cast and crew lists"""
    cast = []
    directors = []
    
    if 'cast' in credits:
        cast = [
            f"{person['name']} as {person['character']}"
            for person in credits['cast'][:max_items]
            if person.get('character')
        ]
    
    if 'crew' in credits:
        directors = [
            person['name']
            for person in credits['crew']
            if person.get('job') == 'Director'
        ]
    
    return cast, directors


def create_pagination_view(items: List[Any], items_per_page: int = 5):
    """Create a pagination view for a list of items"""
    from utils.views import PaginationView
    
    pages = []
    for i in range(0, len(items), items_per_page):
        pages.append(items[i:i + items_per_page])
    
    return PaginationView(pages)


def format_list(items: List[str], separator: str = ", ", max_items: int = None) -> str:
    """Format a list of items into a string"""
    if not items:
        return "N/A"
    
    if max_items and len(items) > max_items:
        items = items[:max_items]
        return separator.join(items) + f" and {len(items) - max_items} more"
    
    return separator.join(items)


def create_embed_base(title: str, description: str = None, color: int = None) -> discord.Embed:
    """Create a base embed with standard formatting"""
    from core.config import Config
    
    embed = discord.Embed(
        title=title,
        description=description,
        color=color or Config.NOTIFICATION_EMBED_COLOR,
        timestamp=datetime.utcnow()
    )
    
    embed.set_footer(text=Config.EMBED_FOOTER_TEXT)
    
    return embed


def get_certification_color(certification: str) -> int:
    """Get color code based on certification/rating"""
    colors = {
        'G': 0x00FF00,
        'PG': 0x90EE90,
        'PG-13': 0xFFFF00,
        'R': 0xFF8C00,
        'NC-17': 0xFF0000,
        'NR': 0x808080,
        'TV-Y': 0x00FF00,
        'TV-Y7': 0x90EE90,
        'TV-G': 0x00FF00,
        'TV-PG': 0xFFFF00,
        'TV-14': 0xFF8C00,
        'TV-MA': 0xFF0000
    }
    return colors.get(certification, 0x00D9FF)


async def send_paginated_message(ctx: commands.Context, pages: List[discord.Embed], timeout: int = 120):
    """Send a paginated message with navigation buttons"""
    if not pages:
        await ctx.send("No results found.")
        return
    
    if len(pages) == 1:
        await ctx.send(embed=pages[0])
        return
    
    from utils.views import EmbedPaginationView
    
    view = EmbedPaginationView(pages, timeout=timeout)
    message = await ctx.send(embed=pages[0], view=view)
    view.message = message


def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """Split a list into chunks of specified size"""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def sanitize_filename(filename: str) -> str:
    """Sanitize filename by removing invalid characters"""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename


def calculate_similarity_score(text1: str, text2: str) -> float:
    """Calculate similarity score between two strings"""
    text1 = text1.lower()
    text2 = text2.lower()
    
    if text1 == text2:
        return 1.0
    
    # Simple word overlap calculation
    words1 = set(text1.split())
    words2 = set(text2.split())
    
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    if not union:
        return 0.0
    
    return len(intersection) / len(union)