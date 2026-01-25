"""
Discord UI Views and Components
Interactive components for Discord messages
"""
from typing import Any, List, Optional

import discord
from discord import ui


class PaginationView(ui.View):
    """Generic pagination view for any content"""
    
    def __init__(self, pages: List[Any], timeout: int = 180):
        super().__init__(timeout=timeout)
        self.pages = pages
        self.current_page = 0
        self.message: Optional[discord.Message] = None
        
        if len(pages) <= 1:
            self.clear_items()
    
    def get_page_content(self):
        """Get content for current page - override in subclass"""
        return self.pages[self.current_page]
    
    async def update_message(self, interaction: discord.Interaction):
        """Update the message with current page"""
        content = self.get_page_content()
        
        # Update button states
        self.first_page.disabled = self.current_page == 0
        self.previous_page.disabled = self.current_page == 0
        self.next_page.disabled = self.current_page >= len(self.pages) - 1
        self.last_page.disabled = self.current_page >= len(self.pages) - 1
        
        self.page_indicator.label = f"Page {self.current_page + 1}/{len(self.pages)}"
        
        await interaction.response.edit_message(content=content, view=self)
    
    @ui.button(label="⏮️", style=discord.ButtonStyle.secondary)
    async def first_page(self, interaction: discord.Interaction, button: ui.Button):
        self.current_page = 0
        await self.update_message(interaction)
    
    @ui.button(label="◀️", style=discord.ButtonStyle.primary)
    async def previous_page(self, interaction: discord.Interaction, button: ui.Button):
        self.current_page = max(0, self.current_page - 1)
        await self.update_message(interaction)
    
    @ui.button(label="Page 1/1", style=discord.ButtonStyle.secondary, disabled=True)
    async def page_indicator(self, interaction: discord.Interaction, button: ui.Button):
        pass
    
    @ui.button(label="▶️", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: discord.Interaction, button: ui.Button):
        self.current_page = min(len(self.pages) - 1, self.current_page + 1)
        await self.update_message(interaction)
    
    @ui.button(label="⏭️", style=discord.ButtonStyle.secondary)
    async def last_page(self, interaction: discord.Interaction, button: ui.Button):
        self.current_page = len(self.pages) - 1
        await self.update_message(interaction)
    
    @ui.button(label="🗑️", style=discord.ButtonStyle.danger)
    async def delete(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.message.delete()
        self.stop()


class EmbedPaginationView(PaginationView):
    """Pagination view specifically for embeds"""
    
    def __init__(self, embeds: List[discord.Embed], timeout: int = 180):
        super().__init__(embeds, timeout)
    
    def get_page_content(self):
        """Returns current embed"""
        return None
    
    async def update_message(self, interaction: discord.Interaction):
        """Update message with current embed"""
        embed = self.pages[self.current_page]
        
        # Update button states
        self.first_page.disabled = self.current_page == 0
        self.previous_page.disabled = self.current_page == 0
        self.next_page.disabled = self.current_page >= len(self.pages) - 1
        self.last_page.disabled = self.current_page >= len(self.pages) - 1
        
        self.page_indicator.label = f"Page {self.current_page + 1}/{len(self.pages)}"
        
        await interaction.response.edit_message(embed=embed, view=self)


class ConfirmView(ui.View):
    """Confirmation dialog view"""
    
    def __init__(self, timeout: int = 60):
        super().__init__(timeout=timeout)
        self.value: Optional[bool] = None
    
    @ui.button(label="Confirm", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: ui.Button):
        self.value = True
        await interaction.response.defer()
        self.stop()
    
    @ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: ui.Button):
        self.value = False
        await interaction.response.defer()
        self.stop()


class MediaSelectView(ui.View):
    """View for selecting media items from search results"""
    
    def __init__(self, results: List[dict], timeout: int = 120):
        super().__init__(timeout=timeout)
        self.results = results
        self.selected: Optional[dict] = None
        
        # Add select menu
        options = []
        for i, item in enumerate(results[:25]):
            media_type = item.get('media_type', 'unknown')
            title = item.get('title') or item.get('name', 'Unknown')
            year = ''
            
            if 'release_date' in item and item['release_date']:
                year = f" ({item['release_date'][:4]})"
            elif 'first_air_date' in item and item['first_air_date']:
                year = f" ({item['first_air_date'][:4]})"
            
            emoji = '🎬' if media_type == 'movie' else '📺' if media_type == 'tv' else '👤'
            
            options.append(
                discord.SelectOption(
                    label=f"{title}{year}"[:100],
                    value=str(i),
                    emoji=emoji,
                    description=f"{media_type.upper()}"[:100]
                )
            )
        
        select = ui.Select(
            placeholder="Select a movie or TV show...",
            options=options,
            min_values=1,
            max_values=1
        )
        select.callback = self.select_callback
        self.add_item(select)
    
    async def select_callback(self, interaction: discord.Interaction):
        """Handle selection"""
        index = int(interaction.data['values'][0])
        self.selected = self.results[index]
        await interaction.response.defer()
        self.stop()


class WatchlistActionView(ui.View):
    """View for watchlist item actions"""
    
    def __init__(self, item_id: int, timeout: int = 300):
        super().__init__(timeout=timeout)
        self.item_id = item_id
        self.action: Optional[str] = None
    
    @ui.button(label="Mark Watched", style=discord.ButtonStyle.success, emoji="✅")
    async def mark_watched(self, interaction: discord.Interaction, button: ui.Button):
        self.action = 'watched'
        await interaction.response.defer()
        self.stop()
    
    @ui.button(label="Add Rating", style=discord.ButtonStyle.primary, emoji="⭐")
    async def add_rating(self, interaction: discord.Interaction, button: ui.Button):
        self.action = 'rating'
        await interaction.response.defer()
        self.stop()
    
    @ui.button(label="Remove", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def remove_item(self, interaction: discord.Interaction, button: ui.Button):
        self.action = 'remove'
        await interaction.response.defer()
        self.stop()


class RatingModal(ui.Modal, title="Rate This Title"):
    """Modal for submitting ratings"""
    
    rating = ui.TextInput(
        label="Rating (1-10)",
        placeholder="Enter a rating from 1 to 10",
        required=True,
        max_length=4
    )
    
    review = ui.TextInput(
        label="Review (Optional)",
        placeholder="Write your review here...",
        required=False,
        style=discord.TextStyle.paragraph,
        max_length=2000
    )
    
    def __init__(self, media_title: str):
        super().__init__()
        self.media_title = media_title
        self.rating_value: Optional[float] = None
        self.review_text: Optional[str] = None
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            self.rating_value = float(self.rating.value)
            if not 1 <= self.rating_value <= 10:
                await interaction.response.send_message(
                    "❌ Rating must be between 1 and 10!",
                    ephemeral=True
                )
                return
            
            self.review_text = self.review.value if self.review.value else None
            await interaction.response.send_message(
                f"✅ Rating submitted for {self.media_title}!",
                ephemeral=True
            )
        except ValueError:
            await interaction.response.send_message(
                "❌ Please enter a valid number!",
                ephemeral=True
            )


class NotificationSettingsView(ui.View):
    """View for notification settings"""
    
    def __init__(self, current_settings: dict, timeout: int = 300):
        super().__init__(timeout=timeout)
        self.settings = current_settings
        self.updated = False
        
        # Update button labels based on current settings
        self.toggle_release.label = f"Release Notifications: {'ON' if current_settings.get('notify_on_release', True) else 'OFF'}"
        self.toggle_update.label = f"Update Notifications: {'ON' if current_settings.get('notify_on_update', True) else 'OFF'}"
    
    @ui.button(label="Release Notifications: ON", style=discord.ButtonStyle.primary)
    async def toggle_release(self, interaction: discord.Interaction, button: ui.Button):
        self.settings['notify_on_release'] = not self.settings.get('notify_on_release', True)
        button.label = f"Release Notifications: {'ON' if self.settings['notify_on_release'] else 'OFF'}"
        button.style = discord.ButtonStyle.primary if self.settings['notify_on_release'] else discord.ButtonStyle.secondary
        self.updated = True
        await interaction.response.edit_message(view=self)
    
    @ui.button(label="Update Notifications: ON", style=discord.ButtonStyle.primary)
    async def toggle_update(self, interaction: discord.Interaction, button: ui.Button):
        self.settings['notify_on_update'] = not self.settings.get('notify_on_update', True)
        button.label = f"Update Notifications: {'ON' if self.settings['notify_on_update'] else 'OFF'}"
        button.style = discord.ButtonStyle.primary if self.settings['notify_on_update'] else discord.ButtonStyle.secondary
        self.updated = True
        await interaction.response.edit_message(view=self)
    
    @ui.button(label="Save Settings", style=discord.ButtonStyle.success)
    async def save_settings(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("✅ Settings saved!", ephemeral=True)
        self.stop()
    
    @ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: ui.Button):
        self.updated = False
        await interaction.response.defer()
        self.stop()