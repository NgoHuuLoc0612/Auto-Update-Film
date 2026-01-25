"""
Supabase configuration and client
Handles Supabase connection and authentication
"""
import os
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


class SupabaseConfig:
    """Supabase configuration"""
    
    # Supabase Connection
    SUPABASE_URL: str = os.getenv('SUPABASE_URL', '')
    SUPABASE_KEY: str = os.getenv('SUPABASE_ANON_KEY', '')
    SUPABASE_SERVICE_KEY: str = os.getenv('SUPABASE_SERVICE_KEY', '')
    
    # Database Connection String for SQLAlchemy
    SUPABASE_DB_URL: str = os.getenv('SUPABASE_DB_URL', '')
    
    # Alternative: Build connection string from components
    SUPABASE_DB_HOST: str = os.getenv('SUPABASE_DB_HOST', '')
    SUPABASE_DB_PORT: int = int(os.getenv('SUPABASE_DB_PORT', '5432'))
    SUPABASE_DB_NAME: str = os.getenv('SUPABASE_DB_NAME', 'postgres')
    SUPABASE_DB_USER: str = os.getenv('SUPABASE_DB_USER', 'postgres')
    SUPABASE_DB_PASSWORD: str = os.getenv('SUPABASE_DB_PASSWORD', '')
    
    @classmethod
    def get_database_url(cls) -> str:
        """Get PostgreSQL connection URL for SQLAlchemy"""
        if cls.SUPABASE_DB_URL:
            # Use provided URL
            return cls.SUPABASE_DB_URL
        
        # Build URL from components
        if cls.SUPABASE_DB_HOST and cls.SUPABASE_DB_PASSWORD:
            return (
                f"postgresql+asyncpg://{cls.SUPABASE_DB_USER}:{cls.SUPABASE_DB_PASSWORD}"
                f"@{cls.SUPABASE_DB_HOST}:{cls.SUPABASE_DB_PORT}/{cls.SUPABASE_DB_NAME}"
            )
        
        # Fallback to SQLite
        return "sqlite+aiosqlite:///./filmbot.db"
    
    @classmethod
    def validate(cls) -> bool:
        """Validate Supabase configuration"""
        if cls.SUPABASE_DB_URL or (cls.SUPABASE_DB_HOST and cls.SUPABASE_DB_PASSWORD):
            return True
        
        print("⚠️  Supabase configuration not found. Using SQLite as fallback.")
        return False
    
    @classmethod
    def is_using_supabase(cls) -> bool:
        """Check if using Supabase"""
        return bool(cls.SUPABASE_DB_URL or cls.SUPABASE_DB_HOST)