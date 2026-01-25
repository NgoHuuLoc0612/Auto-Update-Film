"""
Watchlist management cog
Personal watchlists for users
"""
import logging
from datetime import datetime
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select

from core.config import Config
from core.database import Rating, Watchlist
from services.tmdb_client import TMDBClient
from utils.helpers import create_embed_base, format_date, get_media_type_emoji
from utils.views import MediaSelectView, RatingModal, WatchlistActionView


class WatchlistCog(commands.Cog):
    """Personal watchlist management"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger('FilmBot.Watchlist')
        self.tmdb = TMDBClient(Config.TMDB_API_KEY)
    
    async def cog_unload(self):
        await self.tmdb.close()
    
    @app_commands.command(name="watchlist-add", description="Add a movie or TV show to your watchlist")
    @app_commands.describe(query="Name of the movie or TV show")
    async def watchlist_add(self, interaction: discord.Interaction, query: str):
        """Add item to watchlist"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Search for media
            results = await self.tmdb.search_multi(query)
            items = [item for item in results.get('results', []) if item.get('media_type') in ['movie', 'tv']]
            
            if not items:
                embed = create_embed_base(
                    title="🔍 No Results",
                    description=f"No results found for: **{query}**"
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Let user select
            view = MediaSelectView(items[:10])
            embed = create_embed_base(
                title="📝 Select Media to Add",
                description=f"Found {len(items[:10])} results. Select one to add to your watchlist."
            )
            
            message = await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            await view.wait()
            
            if not view.selected:
                await message.edit(content="⏱️ Selection timed out.", embed=None, view=None)
                return
            
            selected = view.selected
            media_type = selected.get('media_type')
            tmdb_id = selected.get('id')
            title = selected.get('title') or selected.get('name')
            poster_path = selected.get('poster_path')
            
            # Check if already in watchlist
            async with self.bot.db.async_session() as session:
                result = await session.execute(
                    select(Watchlist).where(
                        Watchlist.guild_id == interaction.guild_id,
                        Watchlist.user_id == interaction.user.id,
                        Watchlist.tmdb_id == tmdb_id,
                        Watchlist.media_type == media_type
                    )
                )
                existing = result.scalar_one_or_none()
                
                if existing:
                    embed = create_embed_base(
                        title="⚠️ Already in Watchlist",
                        description=f"**{title}** is already in your watchlist."
                    )
                    await message.edit(embed=embed, view=None)
                    return
                
                # Check watchlist limit
                result = await session.execute(
                    select(Watchlist).where(
                        Watchlist.guild_id == interaction.guild_id,
                        Watchlist.user_id == interaction.user.id
                    )
                )
                count = len(list(result.scalars().all()))
                
                if count >= Config.MAX_WATCHLIST_ITEMS:
                    embed = create_embed_base(
                        title="⚠️ Watchlist Full",
                        description=f"Your watchlist is full ({Config.MAX_WATCHLIST_ITEMS} items max).\nRemove some items to add new ones."
                    )
                    await message.edit(embed=embed, view=None)
                    return
                
                # Add to watchlist
                watchlist_item = Watchlist(
                    guild_id=interaction.guild_id,
                    user_id=interaction.user.id,
                    tmdb_id=tmdb_id,
                    media_type=media_type,
                    title=title,
                    poster_path=poster_path
                )
                session.add(watchlist_item)
                await session.commit()
            
            embed = create_embed_base(
                title=f"✅ Added to Watchlist",
                description=f"{get_media_type_emoji(media_type)} **{title}** has been added to your watchlist!"
            )
            
            if poster_path:
                embed.set_thumbnail(url=Config.get_tmdb_image_url(poster_path, 'w185'))
            
            await message.edit(embed=embed, view=None)
            self.logger.info(f"User {interaction.user.id} added {title} to watchlist")
            
        except Exception as e:
            self.logger.error(f"Watchlist add error: {e}", exc_info=True)
            embed = create_embed_base(
                title="❌ Error",
                description="An error occurred while adding to watchlist."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="watchlist", description="View your watchlist")
    @app_commands.describe(show_watched="Include watched items")
    async def view_watchlist(self, interaction: discord.Interaction, show_watched: bool = False):
        """View user's watchlist"""
        await interaction.response.defer()
        
        try:
            async with self.bot.db.async_session() as session:
                query = select(Watchlist).where(
                    Watchlist.guild_id == interaction.guild_id,
                    Watchlist.user_id == interaction.user.id
                )
                
                if not show_watched:
                    query = query.where(Watchlist.watched == False)
                
                result = await session.execute(query.order_by(Watchlist.added_at.desc()))
                items = list(result.scalars().all())
            
            if not items:
                embed = create_embed_base(
                    title="📝 Your Watchlist",
                    description="Your watchlist is empty.\nUse `/watchlist-add` to add movies or TV shows!"
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Create embed
            embed = create_embed_base(
                title=f"📝 {interaction.user.display_name}'s Watchlist",
                description=f"Total items: {len(items)}"
            )
            
            # Group by watched status
            unwatched = [i for i in items if not i.watched]
            watched = [i for i in items if i.watched]
            
            if unwatched:
                unwatched_list = "\n".join([
                    f"{get_media_type_emoji(i.media_type)} {i.title}"
                    for i in unwatched[:15]
                ])
                if len(unwatched) > 15:
                    unwatched_list += f"\n... and {len(unwatched) - 15} more"
                
                embed.add_field(
                    name=f"📌 To Watch ({len(unwatched)})",
                    value=unwatched_list,
                    inline=False
                )
            
            if watched and show_watched:
                watched_list = "\n".join([
                    f"✅ {get_media_type_emoji(i.media_type)} {i.title}"
                    for i in watched[:10]
                ])
                if len(watched) > 10:
                    watched_list += f"\n... and {len(watched) - 10} more"
                
                embed.add_field(
                    name=f"✅ Watched ({len(watched)})",
                    value=watched_list,
                    inline=False
                )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"View watchlist error: {e}", exc_info=True)
            embed = create_embed_base(
                title="❌ Error",
                description="An error occurred while fetching your watchlist."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="watchlist-remove", description="Remove an item from your watchlist")
    @app_commands.describe(query="Name of the movie or TV show to remove")
    async def watchlist_remove(self, interaction: discord.Interaction, query: str):
        """Remove item from watchlist"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            async with self.bot.db.async_session() as session:
                result = await session.execute(
                    select(Watchlist).where(
                        Watchlist.guild_id == interaction.guild_id,
                        Watchlist.user_id == interaction.user.id
                    )
                )
                items = list(result.scalars().all())
                
                matching = [i for i in items if query.lower() in i.title.lower()]
                
                if not matching:
                    embed = create_embed_base(
                        title="🔍 No Matches",
                        description=f"No items found in your watchlist matching: **{query}**"
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
                
                # If multiple matches, let user select
                if len(matching) > 1:
                    items_dict = [
                        {
                            'id': i.tmdb_id,
                            'media_type': i.media_type,
                            'title': i.title,
                            'name': i.title,
                            'poster_path': i.poster_path
                        }
                        for i in matching
                    ]
                    
                    view = MediaSelectView(items_dict)
                    embed = create_embed_base(
                        title="📌 Select Item to Remove",
                        description=f"Found {len(matching)} matching items."
                    )
                    
                    message = await interaction.followup.send(embed=embed, view=view, ephemeral=True)
                    await view.wait()
                    
                    if not view.selected:
                        await message.edit(content="⏱️ Selection timed out.", embed=None, view=None)
                        return
                    
                    selected_id = view.selected['id']
                    selected_type = view.selected['media_type']
                    item_to_remove = next(i for i in matching if i.tmdb_id == selected_id and i.media_type == selected_type)
                else:
                    item_to_remove = matching[0]
                    message = None
                
                # Remove item
                await session.delete(item_to_remove)
                await session.commit()
                
                embed = create_embed_base(
                    title="✅ Removed from Watchlist",
                    description=f"**{item_to_remove.title}** has been removed from your watchlist."
                )
                
                if message:
                    await message.edit(embed=embed, view=None)
                else:
                    await interaction.followup.send(embed=embed, ephemeral=True)
                
                self.logger.info(f"User {interaction.user.id} removed {item_to_remove.title} from watchlist")
                
        except Exception as e:
            self.logger.error(f"Watchlist remove error: {e}", exc_info=True)
            embed = create_embed_base(
                title="❌ Error",
                description="An error occurred while removing from watchlist."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="watchlist-mark-watched", description="Mark an item as watched")
    @app_commands.describe(query="Name of the movie or TV show")
    async def mark_watched(self, interaction: discord.Interaction, query: str):
        """Mark watchlist item as watched"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            async with self.bot.db.async_session() as session:
                result = await session.execute(
                    select(Watchlist).where(
                        Watchlist.guild_id == interaction.guild_id,
                        Watchlist.user_id == interaction.user.id,
                        Watchlist.watched == False
                    )
                )
                items = list(result.scalars().all())
                
                matching = [i for i in items if query.lower() in i.title.lower()]
                
                if not matching:
                    embed = create_embed_base(
                        title="🔍 No Matches",
                        description=f"No unwatched items found matching: **{query}**"
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
                
                item = matching[0]
                item.watched = True
                item.watched_at = datetime.utcnow()
                await session.commit()
                
                embed = create_embed_base(
                    title="✅ Marked as Watched",
                    description=f"**{item.title}** has been marked as watched!\n\nWould you like to rate it?"
                )
                
                await interaction.followup.send(embed=embed, ephemeral=True)
                self.logger.info(f"User {interaction.user.id} marked {item.title} as watched")
                
        except Exception as e:
            self.logger.error(f"Mark watched error: {e}", exc_info=True)
            await interaction.followup.send("❌ Error marking as watched.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(WatchlistCog(bot))