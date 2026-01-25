"""
Configuration management for the bot
Handles environment variables and settings
"""
import os
from pathlib import Path
from typing import Set

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Central configuration class"""
    
    # Discord Configuration
    DISCORD_TOKEN: str = os.getenv('DISCORD_TOKEN', '')
    PREFIX: str = os.getenv('PREFIX', '!')
    OWNER_IDS: Set[int] = set(map(int, os.getenv('OWNER_IDS', '').split(','))) if os.getenv('OWNER_IDS') else set()
    SYNC_COMMANDS: bool = os.getenv('SYNC_COMMANDS', 'true').lower() == 'true'
    
    # TMDB API Configuration
    TMDB_API_KEY: str = os.getenv('TMDB_API_KEY', '')
    TMDB_API_VERSION: int = int(os.getenv('TMDB_API_VERSION', '3'))
    TMDB_LANGUAGE: str = os.getenv('TMDB_LANGUAGE', 'en-US')
    TMDB_REGION: str = os.getenv('TMDB_REGION', 'US')
    TMDB_IMAGE_BASE_URL: str = 'https://image.tmdb.org/t/p/'
    TMDB_CACHE_TTL: int = int(os.getenv('TMDB_CACHE_TTL', '3600'))
    
    # Database Configuration
    # Priority: SUPABASE_DB_URL > SUPABASE components > DATABASE_URL > SQLite fallback
    USE_SUPABASE: bool = os.getenv('USE_SUPABASE', 'true').lower() == 'true'
    DATABASE_URL: str = os.getenv('DATABASE_URL', 'sqlite+aiosqlite:///./filmbot.db')
    DATABASE_ECHO: bool = os.getenv('DATABASE_ECHO', 'false').lower() == 'true'
    DATABASE_POOL_SIZE: int = int(os.getenv('DATABASE_POOL_SIZE', '10'))
    DATABASE_MAX_OVERFLOW: int = int(os.getenv('DATABASE_MAX_OVERFLOW', '20'))
    
    # Auto Update Configuration
    AUTO_UPDATE_ENABLED: bool = os.getenv('AUTO_UPDATE_ENABLED', 'true').lower() == 'true'
    UPDATE_INTERVAL_HOURS: int = int(os.getenv('UPDATE_INTERVAL_HOURS', '6'))
    UPDATE_CHECK_UPCOMING: bool = os.getenv('UPDATE_CHECK_UPCOMING', 'true').lower() == 'true'
    UPDATE_CHECK_POPULAR: bool = os.getenv('UPDATE_CHECK_POPULAR', 'true').lower() == 'true'
    UPDATE_CHECK_TRENDING: bool = os.getenv('UPDATE_CHECK_TRENDING', 'true').lower() == 'true'
    
    # Notification Configuration
    NOTIFICATION_ENABLED: bool = os.getenv('NOTIFICATION_ENABLED', 'true').lower() == 'true'
    NOTIFICATION_PING_ROLE: bool = os.getenv('NOTIFICATION_PING_ROLE', 'true').lower() == 'true'
    NOTIFICATION_EMBED_COLOR: int = int(os.getenv('NOTIFICATION_EMBED_COLOR', '0x00D9FF'), 16)
    
    # Watchlist Configuration
    MAX_WATCHLIST_ITEMS: int = int(os.getenv('MAX_WATCHLIST_ITEMS', '100'))
    WATCHLIST_REMINDER_ENABLED: bool = os.getenv('WATCHLIST_REMINDER_ENABLED', 'true').lower() == 'true'
    
    # Search Configuration
    SEARCH_RESULTS_LIMIT: int = int(os.getenv('SEARCH_RESULTS_LIMIT', '10'))
    SEARCH_CACHE_ENABLED: bool = os.getenv('SEARCH_CACHE_ENABLED', 'true').lower() == 'true'
    
    # Rating & Review Configuration
    ALLOW_USER_RATINGS: bool = os.getenv('ALLOW_USER_RATINGS', 'true').lower() == 'true'
    ALLOW_USER_REVIEWS: bool = os.getenv('ALLOW_USER_REVIEWS', 'true').lower() == 'true'
    MAX_REVIEW_LENGTH: int = int(os.getenv('MAX_REVIEW_LENGTH', '2000'))
    
    # Recommendation Configuration
    RECOMMENDATION_ENABLED: bool = os.getenv('RECOMMENDATION_ENABLED', 'true').lower() == 'true'
    RECOMMENDATION_MIN_ITEMS: int = int(os.getenv('RECOMMENDATION_MIN_ITEMS', '5'))
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE: str = os.getenv('LOG_FILE', 'logs/filmbot.log')
    LOG_MAX_BYTES: int = int(os.getenv('LOG_MAX_BYTES', '10485760'))
    LOG_BACKUP_COUNT: int = int(os.getenv('LOG_BACKUP_COUNT', '5'))
    
    # Cache Configuration
    REDIS_ENABLED: bool = os.getenv('REDIS_ENABLED', 'false').lower() == 'true'
    REDIS_URL: str = os.getenv('REDIS_URL', 'redis://localhost:6379')
    CACHE_DEFAULT_TTL: int = int(os.getenv('CACHE_DEFAULT_TTL', '3600'))
    
    # API Rate Limiting
    API_RATE_LIMIT: int = int(os.getenv('API_RATE_LIMIT', '40'))
    API_RATE_PERIOD: int = int(os.getenv('API_RATE_PERIOD', '10'))
    
    # Embed Configuration
    EMBED_FOOTER_TEXT: str = os.getenv('EMBED_FOOTER_TEXT', 'Auto Update Film Bot')
    EMBED_AUTHOR_ICON: str = os.getenv('EMBED_AUTHOR_ICON', '')
    EMBED_THUMBNAIL_SIZE: str = os.getenv('EMBED_THUMBNAIL_SIZE', 'w342')
    EMBED_POSTER_SIZE: str = os.getenv('EMBED_POSTER_SIZE', 'w500')
    EMBED_BACKDROP_SIZE: str = os.getenv('EMBED_BACKDROP_SIZE', 'w1280')
    
    # Feature Flags
    FEATURE_COLLECTIONS: bool = os.getenv('FEATURE_COLLECTIONS', 'true').lower() == 'true'
    FEATURE_POLLS: bool = os.getenv('FEATURE_POLLS', 'true').lower() == 'true'
    FEATURE_TRIVIA: bool = os.getenv('FEATURE_TRIVIA', 'true').lower() == 'true'
    FEATURE_STATS: bool = os.getenv('FEATURE_STATS', 'true').lower() == 'true'
    
    # Pagination
    PAGINATION_TIMEOUT: int = int(os.getenv('PAGINATION_TIMEOUT', '120'))
    ITEMS_PER_PAGE: int = int(os.getenv('ITEMS_PER_PAGE', '5'))
    
    # Paths
    BASE_DIR: Path = Path(__file__).parent.parent
    LOGS_DIR: Path = BASE_DIR / 'logs'
    DATA_DIR: Path = BASE_DIR / 'data'
    CACHE_DIR: Path = BASE_DIR / 'cache'
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration"""
        required_vars = {
            'DISCORD_TOKEN': cls.DISCORD_TOKEN,
            'TMDB_API_KEY': cls.TMDB_API_KEY,
        }
        
        missing = [key for key, value in required_vars.items() if not value]
        
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        
        # Create necessary directories
        cls.LOGS_DIR.mkdir(exist_ok=True)
        cls.DATA_DIR.mkdir(exist_ok=True)
        cls.CACHE_DIR.mkdir(exist_ok=True)
        
        return True
    
    @classmethod
    def get_tmdb_image_url(cls, path: str, size: str = 'original') -> str:
        """Generate full TMDB image URL"""
        if not path:
            return ''
        return f"{cls.TMDB_IMAGE_BASE_URL}{size}{path}"


# Validate configuration on import
Config.validate()