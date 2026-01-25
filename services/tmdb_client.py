"""
TMDB API Client
Comprehensive client for interacting with The Movie Database API
"""
import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import aiohttp
from aiohttp import ClientSession

from core.config import Config


class TMDBRateLimiter:
    """Rate limiter for TMDB API requests"""
    
    def __init__(self, rate: int, period: int):
        self.rate = rate
        self.period = period
        self.allowance = rate
        self.last_check = datetime.now()
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """Acquire permission to make a request"""
        async with self._lock:
            current = datetime.now()
            time_passed = (current - self.last_check).total_seconds()
            self.last_check = current
            self.allowance += time_passed * (self.rate / self.period)
            
            if self.allowance > self.rate:
                self.allowance = self.rate
            
            if self.allowance < 1.0:
                sleep_time = (1.0 - self.allowance) * (self.period / self.rate)
                await asyncio.sleep(sleep_time)
                self.allowance = 0.0
            else:
                self.allowance -= 1.0


class TMDBClient:
    """Client for TMDB API operations"""
    
    BASE_URL = "https://api.themoviedb.org/3"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session: Optional[ClientSession] = None
        self.rate_limiter = TMDBRateLimiter(
            Config.API_RATE_LIMIT,
            Config.API_RATE_PERIOD
        )
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _request(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make authenticated request to TMDB API"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        await self.rate_limiter.acquire()
        
        params = params or {}
        params['api_key'] = self.api_key
        params.setdefault('language', Config.TMDB_LANGUAGE)
        
        # Convert boolean values to strings for aiohttp compatibility
        for key, value in params.items():
            if isinstance(value, bool):
                params[key] = str(value).lower()
        
        url = f"{self.BASE_URL}/{endpoint}"
        
        async with self.session.get(url, params=params) as response:
            response.raise_for_status()
            return await response.json()
    
    async def search_multi(self, query: str, page: int = 1) -> Dict[str, Any]:
        """Search for movies, TV shows, and people"""
        return await self._request('search/multi', {
            'query': query,
            'page': page,
            'include_adult': False
        })
    
    async def search_movie(self, query: str, page: int = 1, year: int = None) -> Dict[str, Any]:
        """Search for movies"""
        params = {
            'query': query,
            'page': page,
            'include_adult': False
        }
        if year:
            params['year'] = year
        return await self._request('search/movie', params)
    
    async def search_tv(self, query: str, page: int = 1, year: int = None) -> Dict[str, Any]:
        """Search for TV shows"""
        params = {
            'query': query,
            'page': page,
            'include_adult': False
        }
        if year:
            params['first_air_date_year'] = year
        return await self._request('search/tv', params)
    
    async def get_movie_details(self, movie_id: int) -> Dict[str, Any]:
        """Get detailed movie information"""
        return await self._request(f'movie/{movie_id}', {
            'append_to_response': 'credits,videos,recommendations,similar,release_dates,keywords'
        })
    
    async def get_tv_details(self, tv_id: int) -> Dict[str, Any]:
        """Get detailed TV show information"""
        return await self._request(f'tv/{tv_id}', {
            'append_to_response': 'credits,videos,recommendations,similar,content_ratings,keywords'
        })
    
    async def get_season_details(self, tv_id: int, season_number: int) -> Dict[str, Any]:
        """Get TV season details"""
        return await self._request(f'tv/{tv_id}/season/{season_number}')
    
    async def get_episode_details(self, tv_id: int, season_number: int, episode_number: int) -> Dict[str, Any]:
        """Get TV episode details"""
        return await self._request(f'tv/{tv_id}/season/{season_number}/episode/{episode_number}')
    
    async def get_trending(self, media_type: str = 'all', time_window: str = 'week') -> Dict[str, Any]:
        """Get trending movies/TV shows"""
        return await self._request(f'trending/{media_type}/{time_window}')
    
    async def get_popular_movies(self, page: int = 1) -> Dict[str, Any]:
        """Get popular movies"""
        return await self._request('movie/popular', {'page': page})
    
    async def get_popular_tv(self, page: int = 1) -> Dict[str, Any]:
        """Get popular TV shows"""
        return await self._request('tv/popular', {'page': page})
    
    async def get_upcoming_movies(self, page: int = 1) -> Dict[str, Any]:
        """Get upcoming movies"""
        return await self._request('movie/upcoming', {
            'page': page,
            'region': Config.TMDB_REGION
        })
    
    async def get_now_playing_movies(self, page: int = 1) -> Dict[str, Any]:
        """Get now playing movies"""
        return await self._request('movie/now_playing', {
            'page': page,
            'region': Config.TMDB_REGION
        })
    
    async def get_top_rated_movies(self, page: int = 1) -> Dict[str, Any]:
        """Get top rated movies"""
        return await self._request('movie/top_rated', {'page': page})
    
    async def get_top_rated_tv(self, page: int = 1) -> Dict[str, Any]:
        """Get top rated TV shows"""
        return await self._request('tv/top_rated', {'page': page})
    
    async def get_airing_today_tv(self, page: int = 1) -> Dict[str, Any]:
        """Get TV shows airing today"""
        return await self._request('tv/airing_today', {'page': page})
    
    async def get_on_the_air_tv(self, page: int = 1) -> Dict[str, Any]:
        """Get TV shows currently on the air"""
        return await self._request('tv/on_the_air', {'page': page})
    
    async def get_person_details(self, person_id: int) -> Dict[str, Any]:
        """Get person details"""
        return await self._request(f'person/{person_id}', {
            'append_to_response': 'combined_credits,images'
        })
    
    async def get_movie_recommendations(self, movie_id: int, page: int = 1) -> Dict[str, Any]:
        """Get movie recommendations"""
        return await self._request(f'movie/{movie_id}/recommendations', {'page': page})
    
    async def get_tv_recommendations(self, tv_id: int, page: int = 1) -> Dict[str, Any]:
        """Get TV show recommendations"""
        return await self._request(f'tv/{tv_id}/recommendations', {'page': page})
    
    async def get_similar_movies(self, movie_id: int, page: int = 1) -> Dict[str, Any]:
        """Get similar movies"""
        return await self._request(f'movie/{movie_id}/similar', {'page': page})
    
    async def get_similar_tv(self, tv_id: int, page: int = 1) -> Dict[str, Any]:
        """Get similar TV shows"""
        return await self._request(f'tv/{tv_id}/similar', {'page': page})
    
    async def discover_movies(self, **filters) -> Dict[str, Any]:
        """Discover movies with filters"""
        return await self._request('discover/movie', filters)
    
    async def discover_tv(self, **filters) -> Dict[str, Any]:
        """Discover TV shows with filters"""
        return await self._request('discover/tv', filters)
    
    async def get_genres_movie(self) -> Dict[str, Any]:
        """Get movie genres"""
        return await self._request('genre/movie/list')
    
    async def get_genres_tv(self) -> Dict[str, Any]:
        """Get TV genres"""
        return await self._request('genre/tv/list')
    
    async def get_movie_videos(self, movie_id: int) -> Dict[str, Any]:
        """Get movie videos (trailers, teasers, etc.)"""
        return await self._request(f'movie/{movie_id}/videos')
    
    async def get_tv_videos(self, tv_id: int) -> Dict[str, Any]:
        """Get TV show videos"""
        return await self._request(f'tv/{tv_id}/videos')
    
    async def get_movie_reviews(self, movie_id: int, page: int = 1) -> Dict[str, Any]:
        """Get movie reviews"""
        return await self._request(f'movie/{movie_id}/reviews', {'page': page})
    
    async def get_tv_reviews(self, tv_id: int, page: int = 1) -> Dict[str, Any]:
        """Get TV show reviews"""
        return await self._request(f'tv/{tv_id}/reviews', {'page': page})
    
    async def get_collection_details(self, collection_id: int) -> Dict[str, Any]:
        """Get collection details"""
        return await self._request(f'collection/{collection_id}')
    
    async def get_watch_providers_movie(self, movie_id: int) -> Dict[str, Any]:
        """Get movie watch providers"""
        return await self._request(f'movie/{movie_id}/watch/providers')
    
    async def get_watch_providers_tv(self, tv_id: int) -> Dict[str, Any]:
        """Get TV show watch providers"""
        return await self._request(f'tv/{tv_id}/watch/providers')
    
    def get_image_url(self, path: str, size: str = 'original') -> str:
        """Get full image URL"""
        return Config.get_tmdb_image_url(path, size) if path else ''
    
    async def close(self):
        """Close the session"""
        if self.session:
            await self.session.close()
            self.session = None