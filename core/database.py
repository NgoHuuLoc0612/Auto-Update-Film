"""
Database models and manager
Handles all database operations using SQLAlchemy
"""
from datetime import datetime
from typing import List, Optional

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()


class Guild(Base):
    __tablename__ = 'guilds'
    
    id = Column(BigInteger, primary_key=True)
    name = Column(String(100), nullable=False)
    prefix = Column(String(10), default='!')
    notification_channel_id = Column(BigInteger, nullable=True)
    notification_role_id = Column(BigInteger, nullable=True)
    auto_update_enabled = Column(Boolean, default=True)
    language = Column(String(10), default='en-US')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    subscriptions = relationship('Subscription', back_populates='guild', cascade='all, delete-orphan')
    watchlists = relationship('Watchlist', back_populates='guild', cascade='all, delete-orphan')


class Subscription(Base):
    __tablename__ = 'subscriptions'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(BigInteger, ForeignKey('guilds.id', ondelete='CASCADE'), nullable=False)
    tmdb_id = Column(Integer, nullable=False)
    media_type = Column(String(20), nullable=False)
    title = Column(String(255), nullable=False)
    poster_path = Column(String(255), nullable=True)
    subscribed_at = Column(DateTime, default=datetime.utcnow)
    last_checked = Column(DateTime, nullable=True)
    notify_on_release = Column(Boolean, default=True)
    notify_on_update = Column(Boolean, default=True)
    
    guild = relationship('Guild', back_populates='subscriptions')


class Watchlist(Base):
    __tablename__ = 'watchlists'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(BigInteger, ForeignKey('guilds.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(BigInteger, nullable=False)
    tmdb_id = Column(Integer, nullable=False)
    media_type = Column(String(20), nullable=False)
    title = Column(String(255), nullable=False)
    poster_path = Column(String(255), nullable=True)
    priority = Column(Integer, default=0)
    watched = Column(Boolean, default=False)
    added_at = Column(DateTime, default=datetime.utcnow)
    watched_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    
    guild = relationship('Guild', back_populates='watchlists')
    rating = relationship('Rating', back_populates='watchlist', uselist=False)


class Rating(Base):
    __tablename__ = 'ratings'
    
    id = Column(Integer, primary_key=True)
    watchlist_id = Column(Integer, ForeignKey('watchlists.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(BigInteger, nullable=False)
    tmdb_id = Column(Integer, nullable=False)
    media_type = Column(String(20), nullable=False)
    score = Column(Float, nullable=False)
    review = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    watchlist = relationship('Watchlist', back_populates='rating')


class Cache(Base):
    __tablename__ = 'cache'
    
    id = Column(Integer, primary_key=True)
    key = Column(String(255), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Notification(Base):
    __tablename__ = 'notifications'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(BigInteger, nullable=False)
    tmdb_id = Column(Integer, nullable=False)
    media_type = Column(String(20), nullable=False)
    notification_type = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    sent = Column(Boolean, default=False)
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class UserPreference(Base):
    __tablename__ = 'user_preferences'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, unique=True, nullable=False)
    favorite_genres = Column(Text, nullable=True)
    notification_dm = Column(Boolean, default=False)
    language = Column(String(10), default='en-US')
    region = Column(String(10), default='US')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Collection(Base):
    __tablename__ = 'collections'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(BigInteger, nullable=False)
    user_id = Column(BigInteger, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    items = relationship('CollectionItem', back_populates='collection', cascade='all, delete-orphan')


class CollectionItem(Base):
    __tablename__ = 'collection_items'
    
    id = Column(Integer, primary_key=True)
    collection_id = Column(Integer, ForeignKey('collections.id', ondelete='CASCADE'), nullable=False)
    tmdb_id = Column(Integer, nullable=False)
    media_type = Column(String(20), nullable=False)
    title = Column(String(255), nullable=False)
    poster_path = Column(String(255), nullable=True)
    added_at = Column(DateTime, default=datetime.utcnow)
    
    collection = relationship('Collection', back_populates='items')


class Database:
    """Database manager with async support"""
    
    def __init__(self, url: str, echo: bool = False, pool_size: int = 10, max_overflow: int = 20):
        # Configure engine based on database type
        if url.startswith('postgresql'):
            # PostgreSQL/Supabase configuration
            self.engine = create_async_engine(
                url,
                echo=echo,
                future=True,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_pre_ping=True,
                pool_recycle=3600,
                connect_args={
                    'server_settings': {
                        'application_name': 'FilmBot'
                    }
                }
            )
        else:
            # SQLite configuration
            self.engine = create_async_engine(
                url,
                echo=echo,
                future=True
            )
        
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
    
    async def initialize(self):
        """Create all tables"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    async def close(self):
        """Close database connection"""
        await self.engine.dispose()
    
    async def get_session(self) -> AsyncSession:
        """Get a new database session"""
        return self.async_session()
    
    async def get_guild(self, guild_id: int) -> Optional[Guild]:
        """Get guild by ID"""
        async with self.async_session() as session:
            result = await session.execute(
                select(Guild).where(Guild.id == guild_id)
            )
            return result.scalar_one_or_none()
    
    async def create_guild(self, guild_id: int, name: str) -> Guild:
        """Create new guild"""
        async with self.async_session() as session:
            guild = Guild(id=guild_id, name=name)
            session.add(guild)
            await session.commit()
            await session.refresh(guild)
            return guild
    
    async def get_or_create_guild(self, guild_id: int, name: str) -> Guild:
        """Get or create guild"""
        guild = await self.get_guild(guild_id)
        if not guild:
            guild = await self.create_guild(guild_id, name)
        return guild
    
    async def update_guild(self, guild_id: int, **kwargs) -> Optional[Guild]:
        """Update guild settings"""
        async with self.async_session() as session:
            result = await session.execute(
                select(Guild).where(Guild.id == guild_id)
            )
            guild = result.scalar_one_or_none()
            
            if guild:
                for key, value in kwargs.items():
                    if hasattr(guild, key):
                        setattr(guild, key, value)
                guild.updated_at = datetime.utcnow()
                await session.commit()
                await session.refresh(guild)
            
            return guild
    
    async def get_subscriptions(self, guild_id: int) -> List[Subscription]:
        """Get all subscriptions for a guild"""
        async with self.async_session() as session:
            result = await session.execute(
                select(Subscription).where(Subscription.guild_id == guild_id)
            )
            return list(result.scalars().all())
    
    async def add_subscription(self, guild_id: int, tmdb_id: int, media_type: str, 
                              title: str, poster_path: str = None) -> Subscription:
        """Add new subscription"""
        async with self.async_session() as session:
            subscription = Subscription(
                guild_id=guild_id,
                tmdb_id=tmdb_id,
                media_type=media_type,
                title=title,
                poster_path=poster_path
            )
            session.add(subscription)
            await session.commit()
            await session.refresh(subscription)
            return subscription
    
    async def remove_subscription(self, guild_id: int, tmdb_id: int, media_type: str) -> bool:
        """Remove subscription"""
        async with self.async_session() as session:
            result = await session.execute(
                select(Subscription).where(
                    Subscription.guild_id == guild_id,
                    Subscription.tmdb_id == tmdb_id,
                    Subscription.media_type == media_type
                )
            )
            subscription = result.scalar_one_or_none()
            
            if subscription:
                await session.delete(subscription)
                await session.commit()
                return True
            return False