"""
Auto update cog
Background task that checks for updates to subscribed media
"""
import asyncio
import logging
from datetime import datetime, timedelta

import discord
from discord.ext import commands, tasks

from core.config import Config
from services.tmdb_client import TMDBClient
from utils.helpers import create_embed_base, format_date, get_media_type_emoji


class AutoUpdate(commands.Cog):
    """Automatic update checker for subscribed media"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger('FilmBot.AutoUpdate')
        self.tmdb = TMDBClient(Config.TMDB_API_KEY)
        self.update_check.start()
    
    def cog_unload(self):
        """Stop tasks when cog is unloaded"""
        self.update_check.cancel()
        asyncio.create_task(self.tmdb.close())
    
    @tasks.loop(hours=Config.UPDATE_INTERVAL_HOURS)
    async def update_check(self):
        """Check for updates to subscribed media"""
        try:
            self.logger.info("Starting auto-update check...")
            
            # Get all guilds with subscriptions
            async with self.bot.db.async_session() as session:
                from sqlalchemy import select
                from core.database import Guild, Subscription
                
                result = await session.execute(
                    select(Guild).where(Guild.auto_update_enabled == True)
                )
                guilds = list(result.scalars().all())
            
            total_updates = 0
            
            for guild_data in guilds:
                try:
                    guild = self.bot.get_guild(guild_data.id)
                    if not guild:
                        continue
                    
                    subscriptions = await self.bot.db.get_subscriptions(guild_data.id)
                    
                    if not subscriptions:
                        continue
                    
                    self.logger.info(f"Checking {len(subscriptions)} subscriptions for guild {guild.name}")
                    
                    for subscription in subscriptions:
                        try:
                            # Check if we should check this subscription
                            if subscription.last_checked:
                                time_since_check = datetime.utcnow() - subscription.last_checked
                                if time_since_check < timedelta(hours=Config.UPDATE_INTERVAL_HOURS):
                                    continue
                            
                            # Get current details
                            if subscription.media_type == 'movie':
                                details = await self.tmdb.get_movie_details(subscription.tmdb_id)
                            else:
                                details = await self.tmdb.get_tv_details(subscription.tmdb_id)
                            
                            # Check for updates
                            notification = await self._check_for_updates(subscription, details)
                            
                            if notification:
                                await self._send_notification(guild, guild_data, subscription, notification)
                                total_updates += 1
                            
                            # Update last checked time
                            async with self.bot.db.async_session() as session:
                                from sqlalchemy import update
                                await session.execute(
                                    update(Subscription)
                                    .where(Subscription.id == subscription.id)
                                    .values(last_checked=datetime.utcnow())
                                )
                                await session.commit()
                            
                            # Rate limiting
                            await asyncio.sleep(0.5)
                            
                        except Exception as e:
                            self.logger.error(f"Error checking subscription {subscription.id}: {e}")
                            continue
                    
                except Exception as e:
                    self.logger.error(f"Error processing guild {guild_data.id}: {e}")
                    continue
            
            self.logger.info(f"Auto-update check complete. {total_updates} notifications sent.")
            
        except Exception as e:
            self.logger.error(f"Error in auto-update task: {e}", exc_info=True)
    
    @update_check.before_loop
    async def before_update_check(self):
        """Wait until bot is ready before starting task"""
        await self.bot.wait_until_ready()
        self.logger.info("Auto-update task initialized")
    
    async def _check_for_updates(self, subscription, details: dict) -> dict:
        """Check if media has updates that should trigger notification"""
        notification = {}
        
        # Check release status for movies
        if subscription.media_type == 'movie':
            release_date = details.get('release_date')
            status = details.get('status')
            
            if release_date and subscription.notify_on_release:
                release_dt = datetime.strptime(release_date, '%Y-%m-%d')
                
                # Check if recently released (within last update interval)
                if status == 'Released':
                    days_since_release = (datetime.utcnow() - release_dt).days
                    if 0 <= days_since_release <= (Config.UPDATE_INTERVAL_HOURS / 24):
                        notification['type'] = 'release'
                        notification['date'] = release_date
                        notification['title'] = details.get('title')
                
                # Check if releasing soon (within next 7 days)
                elif status in ['Post Production', 'In Production']:
                    days_until_release = (release_dt - datetime.utcnow()).days
                    if 0 <= days_until_release <= 7:
                        notification['type'] = 'upcoming'
                        notification['date'] = release_date
                        notification['title'] = details.get('title')
        
        # Check for new episodes for TV shows
        elif subscription.media_type == 'tv':
            last_air_date = details.get('last_air_date')
            next_air_date = details.get('next_episode_to_air')
            
            if next_air_date and subscription.notify_on_update:
                air_date = next_air_date.get('air_date')
                if air_date:
                    air_dt = datetime.strptime(air_date, '%Y-%m-%d')
                    days_until_air = (air_dt - datetime.utcnow()).days
                    
                    # Notify 1 day before new episode
                    if days_until_air == 1:
                        notification['type'] = 'new_episode'
                        notification['date'] = air_date
                        notification['title'] = details.get('name')
                        notification['episode'] = next_air_date
            
            elif last_air_date and subscription.notify_on_update:
                last_dt = datetime.strptime(last_air_date, '%Y-%m-%d')
                days_since_air = (datetime.utcnow() - last_dt).days
                
                # Notify if episode aired recently
                if 0 <= days_since_air <= (Config.UPDATE_INTERVAL_HOURS / 24):
                    notification['type'] = 'episode_aired'
                    notification['date'] = last_air_date
                    notification['title'] = details.get('name')
        
        return notification if notification else None
    
    async def _send_notification(self, guild: discord.Guild, guild_data, subscription, notification: dict):
        """Send notification to guild"""
        try:
            # Get notification channel
            channel_id = guild_data.notification_channel_id
            if not channel_id:
                # Use system channel as fallback
                channel = guild.system_channel
            else:
                channel = guild.get_channel(channel_id)
            
            if not channel:
                self.logger.warning(f"No notification channel found for guild {guild.id}")
                return
            
            # Create notification embed
            media_type = subscription.media_type
            title = notification['title']
            emoji = get_media_type_emoji(media_type)
            
            if notification['type'] == 'release':
                embed = create_embed_base(
                    title=f"🎉 {emoji} {title} is Now Available!",
                    description=f"**{title}** has been released!\nRelease Date: {format_date(notification['date'])}"
                )
            
            elif notification['type'] == 'upcoming':
                embed = create_embed_base(
                    title=f"🔜 {emoji} {title} Releasing Soon!",
                    description=f"**{title}** will be released in the next few days!\nRelease Date: {format_date(notification['date'])}"
                )
            
            elif notification['type'] == 'new_episode':
                episode_info = notification['episode']
                embed = create_embed_base(
                    title=f"📺 New Episode Tomorrow!",
                    description=f"**{title}**\nS{episode_info.get('season_number')}E{episode_info.get('episode_number')}: {episode_info.get('name')}\nAirs: {format_date(notification['date'])}"
                )
            
            elif notification['type'] == 'episode_aired':
                embed = create_embed_base(
                    title=f"📺 New Episode Available!",
                    description=f"A new episode of **{title}** has aired!\nAir Date: {format_date(notification['date'])}"
                )
            
            else:
                return
            
            # Add poster
            if subscription.poster_path:
                embed.set_thumbnail(url=Config.get_tmdb_image_url(subscription.poster_path, 'w185'))
            
            # Add link
            embed.add_field(
                name="🔗 More Info",
                value=f"[View on TMDB](https://www.themoviedb.org/{media_type}/{subscription.tmdb_id})",
                inline=False
            )
            
            # Mention role if configured
            content = None
            if guild_data.notification_role_id and Config.NOTIFICATION_PING_ROLE:
                role = guild.get_role(guild_data.notification_role_id)
                if role:
                    content = role.mention
            
            await channel.send(content=content, embed=embed)
            self.logger.info(f"Sent notification for {title} to guild {guild.id}")
            
        except Exception as e:
            self.logger.error(f"Error sending notification: {e}", exc_info=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AutoUpdate(bot))