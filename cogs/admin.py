"""
Admin commands cog
Server configuration and management
"""
import logging

import discord
from discord import app_commands
from discord.ext import commands

from core.config import Config
from utils.helpers import create_embed_base


class Admin(commands.Cog):
    """Administrative commands for server configuration"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger('FilmBot.Admin')
    
    @app_commands.command(name="setup", description="Set up the bot for this server")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup(self, interaction: discord.Interaction):
        """Initial bot setup for the server"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Create or update guild in database
            guild = await self.bot.db.get_or_create_guild(
                interaction.guild_id,
                interaction.guild.name
            )
            
            embed = create_embed_base(
                title="✅ Setup Complete",
                description=f"**Auto Update Film Bot** has been set up for {interaction.guild.name}!"
            )
            
            embed.add_field(
                name="📋 Next Steps",
                value=(
                    "1. Set notification channel: `/config notification-channel`\n"
                    "2. Subscribe to movies/shows: `/subscribe`\n"
                    "3. Configure auto-updates: `/config auto-update`"
                ),
                inline=False
            )
            
            embed.add_field(
                name="📚 Commands",
                value=(
                    "• `/search` - Search for movies and TV shows\n"
                    "• `/subscribe` - Subscribe to updates\n"
                    "• `/watchlist-add` - Add to personal watchlist\n"
                    "• `/trending` - View trending media\n"
                    "• `/help` - View all commands"
                ),
                inline=False
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            self.logger.info(f"Setup completed for guild {interaction.guild_id}")
            
        except Exception as e:
            self.logger.error(f"Setup error: {e}", exc_info=True)
            embed = create_embed_base(
                title="❌ Setup Error",
                description="An error occurred during setup. Please try again."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="config", description="Configure bot settings")
    @app_commands.describe(
        setting="Setting to configure",
        value="New value for the setting"
    )
    @app_commands.choices(setting=[
        app_commands.Choice(name="Auto-update enabled", value="auto_update"),
        app_commands.Choice(name="Notification channel", value="notification_channel"),
        app_commands.Choice(name="Notification role", value="notification_role"),
        app_commands.Choice(name="Prefix", value="prefix"),
        app_commands.Choice(name="Language", value="language")
    ])
    @app_commands.checks.has_permissions(manage_guild=True)
    async def config(self, interaction: discord.Interaction, setting: str, value: str = None):
        """Configure bot settings"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            guild = await self.bot.db.get_guild(interaction.guild_id)
            
            if not guild:
                embed = create_embed_base(
                    title="⚠️ Not Set Up",
                    description="Please run `/setup` first to initialize the bot for this server."
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Show current settings if no value provided
            if value is None:
                embed = create_embed_base(
                    title="⚙️ Current Settings",
                    description=f"Settings for **{interaction.guild.name}**"
                )
                
                embed.add_field(
                    name="🔄 Auto-update",
                    value="Enabled" if guild.auto_update_enabled else "Disabled",
                    inline=True
                )
                
                notification_channel = interaction.guild.get_channel(guild.notification_channel_id) if guild.notification_channel_id else None
                embed.add_field(
                    name="📢 Notification Channel",
                    value=notification_channel.mention if notification_channel else "Not set",
                    inline=True
                )
                
                notification_role = interaction.guild.get_role(guild.notification_role_id) if guild.notification_role_id else None
                embed.add_field(
                    name="🔔 Notification Role",
                    value=notification_role.mention if notification_role else "Not set",
                    inline=True
                )
                
                embed.add_field(
                    name="⌨️ Prefix",
                    value=guild.prefix,
                    inline=True
                )
                
                embed.add_field(
                    name="🌐 Language",
                    value=guild.language,
                    inline=True
                )
                
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Update settings
            updates = {}
            
            if setting == "auto_update":
                enabled = value.lower() in ['true', 'yes', 'on', '1', 'enable', 'enabled']
                updates['auto_update_enabled'] = enabled
                setting_name = "Auto-update"
                new_value = "Enabled" if enabled else "Disabled"
            
            elif setting == "notification_channel":
                try:
                    channel = await commands.TextChannelConverter().convert(interaction, value)
                    updates['notification_channel_id'] = channel.id
                    setting_name = "Notification channel"
                    new_value = channel.mention
                except:
                    embed = create_embed_base(
                        title="❌ Invalid Channel",
                        description="Please provide a valid text channel mention or ID."
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
            
            elif setting == "notification_role":
                try:
                    role = await commands.RoleConverter().convert(interaction, value)
                    updates['notification_role_id'] = role.id
                    setting_name = "Notification role"
                    new_value = role.mention
                except:
                    embed = create_embed_base(
                        title="❌ Invalid Role",
                        description="Please provide a valid role mention or ID."
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
            
            elif setting == "prefix":
                if len(value) > 10:
                    embed = create_embed_base(
                        title="❌ Invalid Prefix",
                        description="Prefix must be 10 characters or less."
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
                updates['prefix'] = value
                setting_name = "Command prefix"
                new_value = value
            
            elif setting == "language":
                updates['language'] = value
                setting_name = "Language"
                new_value = value
            
            # Apply updates
            await self.bot.db.update_guild(interaction.guild_id, **updates)
            
            embed = create_embed_base(
                title="✅ Setting Updated",
                description=f"**{setting_name}** has been updated to: {new_value}"
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            self.logger.info(f"Guild {interaction.guild_id} updated {setting} to {new_value}")
            
        except Exception as e:
            self.logger.error(f"Config error: {e}", exc_info=True)
            embed = create_embed_base(
                title="❌ Configuration Error",
                description="An error occurred while updating settings."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="stats", description="View bot statistics")
    async def stats(self, interaction: discord.Interaction):
        """Show bot statistics"""
        await interaction.response.defer()
        
        try:
            # Get statistics
            subscriptions = await self.bot.db.get_subscriptions(interaction.guild_id)
            
            async with self.bot.db.async_session() as session:
                from sqlalchemy import select, func
                from core.database import Watchlist
                
                result = await session.execute(
                    select(func.count(Watchlist.id)).where(
                        Watchlist.guild_id == interaction.guild_id
                    )
                )
                total_watchlist_items = result.scalar()
                
                result = await session.execute(
                    select(func.count(Watchlist.user_id.distinct())).where(
                        Watchlist.guild_id == interaction.guild_id
                    )
                )
                active_users = result.scalar()
            
            embed = create_embed_base(
                title="📊 Bot Statistics",
                description=f"Statistics for **{interaction.guild.name}**"
            )
            
            embed.add_field(
                name="📌 Subscriptions",
                value=f"{len(subscriptions)} active",
                inline=True
            )
            
            embed.add_field(
                name="📝 Watchlist Items",
                value=f"{total_watchlist_items} total",
                inline=True
            )
            
            embed.add_field(
                name="👥 Active Users",
                value=f"{active_users} users",
                inline=True
            )
            
            # Bot-wide stats
            embed.add_field(
                name="🌐 Total Servers",
                value=f"{len(self.bot.guilds)}",
                inline=True
            )
            
            embed.add_field(
                name="👤 Total Users",
                value=f"{len(self.bot.users):,}",
                inline=True
            )
            
            embed.add_field(
                name="⏱️ Uptime",
                value="Available in premium",
                inline=True
            )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Stats error: {e}", exc_info=True)
            embed = create_embed_base(
                title="❌ Error",
                description="An error occurred while fetching statistics."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))