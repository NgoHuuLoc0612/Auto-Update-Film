"""
Advanced Visualization Service
Creates charts, graphs, and 3D visualizations for movie/TV data
"""
import io
import logging
from datetime import datetime
from typing import Dict, List, Optional

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import cm
from mpl_toolkits.mplot3d import Axes3D
import seaborn as sns

logger = logging.getLogger('FilmBot.Visualization')


class VisualizationService:
    """Service for creating advanced visualizations"""
    
    def __init__(self):
        self.setup_style()
    
    def setup_style(self):
        """Setup matplotlib style"""
        plt.style.use('dark_background')
        sns.set_palette("husl")
    
    def create_rating_distribution(self, ratings: List[float], title: str = "Rating Distribution") -> io.BytesIO:
        """Create histogram of rating distribution"""
        fig, ax = plt.subplots(figsize=(12, 6))
        
        ax.hist(ratings, bins=20, color='#00D9FF', alpha=0.7, edgecolor='white')
        ax.set_xlabel('Rating', fontsize=12)
        ax.set_ylabel('Frequency', fontsize=12)
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        # Add statistics
        mean_rating = np.mean(ratings)
        median_rating = np.median(ratings)
        ax.axvline(mean_rating, color='red', linestyle='--', label=f'Mean: {mean_rating:.2f}')
        ax.axvline(median_rating, color='yellow', linestyle='--', label=f'Median: {median_rating:.2f}')
        ax.legend()
        
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close()
        
        return buf
    
    def create_genre_bubble_chart(self, genre_data: Dict[str, Dict]) -> io.BytesIO:
        """Create bubble chart for genre popularity"""
        fig, ax = plt.subplots(figsize=(14, 10))
        
        genres = list(genre_data.keys())
        x = [genre_data[g]['count'] for g in genres]
        y = [genre_data[g]['avg_rating'] for g in genres]
        sizes = [genre_data[g]['total_votes'] / 1000 for g in genres]
        colors = plt.cm.viridis(np.linspace(0, 1, len(genres)))
        
        scatter = ax.scatter(x, y, s=sizes, c=colors, alpha=0.6, edgecolors='white', linewidth=2)
        
        # Add labels
        for i, genre in enumerate(genres):
            ax.annotate(genre, (x[i], y[i]), fontsize=9, ha='center')
        
        ax.set_xlabel('Number of Titles', fontsize=12)
        ax.set_ylabel('Average Rating', fontsize=12)
        ax.set_title('Genre Popularity Bubble Chart', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close()
        
        return buf
    
    def create_3d_scatter(self, data: List[Dict]) -> io.BytesIO:
        """Create 3D scatter plot (Rating vs Budget vs Revenue)"""
        fig = plt.figure(figsize=(14, 10))
        ax = fig.add_subplot(111, projection='3d')
        
        ratings = [d['rating'] for d in data]
        budgets = [d['budget'] / 1_000_000 for d in data]  # In millions
        revenues = [d['revenue'] / 1_000_000 for d in data]  # In millions
        
        scatter = ax.scatter(ratings, budgets, revenues, 
                           c=ratings, cmap='plasma', 
                           s=100, alpha=0.6, edgecolors='white')
        
        ax.set_xlabel('Rating', fontsize=12)
        ax.set_ylabel('Budget (Millions $)', fontsize=12)
        ax.set_zlabel('Revenue (Millions $)', fontsize=12)
        ax.set_title('3D Movie Analysis: Rating vs Budget vs Revenue', 
                     fontsize=14, fontweight='bold')
        
        plt.colorbar(scatter, ax=ax, label='Rating')
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close()
        
        return buf
    
    def create_radar_chart(self, categories: List[str], values: List[float], 
                          title: str = "Content Analysis") -> io.BytesIO:
        """Create radar chart for multi-dimensional analysis"""
        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))
        
        # Normalize values to 0-10 scale
        max_val = max(values) if max(values) > 0 else 1
        normalized = [(v / max_val) * 10 for v in values]
        
        angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
        normalized += normalized[:1]
        angles += angles[:1]
        
        ax.plot(angles, normalized, 'o-', linewidth=2, color='#00D9FF')
        ax.fill(angles, normalized, alpha=0.25, color='#00D9FF')
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, fontsize=10)
        ax.set_ylim(0, 10)
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        ax.grid(True)
        
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close()
        
        return buf
    
    def create_polar_area_chart(self, labels: List[str], values: List[float],
                                title: str = "Distribution") -> io.BytesIO:
        """Create polar area chart"""
        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))
        
        theta = np.linspace(0, 2 * np.pi, len(labels), endpoint=False)
        width = 2 * np.pi / len(labels)
        colors = plt.cm.viridis(np.linspace(0, 1, len(labels)))
        
        bars = ax.bar(theta, values, width=width, bottom=0.0, color=colors, alpha=0.8)
        
        ax.set_xticks(theta)
        ax.set_xticklabels(labels, fontsize=10)
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close()
        
        return buf
    
    def create_heatmap(self, data: np.ndarray, xlabels: List[str], ylabels: List[str],
                      title: str = "Correlation Heatmap") -> io.BytesIO:
        """Create correlation heatmap"""
        fig, ax = plt.subplots(figsize=(12, 10))
        
        sns.heatmap(data, annot=True, fmt='.2f', cmap='coolwarm',
                   xticklabels=xlabels, yticklabels=ylabels,
                   ax=ax, cbar_kws={'label': 'Correlation'})
        
        ax.set_title(title, fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close()
        
        return buf
    
    def create_timeline_chart(self, dates: List[datetime], values: List[float],
                            title: str = "Timeline") -> io.BytesIO:
        """Create timeline chart with trend"""
        fig, ax = plt.subplots(figsize=(14, 6))
        
        ax.plot(dates, values, marker='o', linewidth=2, color='#00D9FF', label='Data')
        
        # Add trend line
        x_numeric = [(d - dates[0]).days for d in dates]
        z = np.polyfit(x_numeric, values, 1)
        p = np.poly1d(z)
        ax.plot(dates, p(x_numeric), "--", color='red', alpha=0.8, label='Trend')
        
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Value', fontsize=12)
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close()
        
        return buf
    
    def create_box_plot(self, data_dict: Dict[str, List[float]], 
                       title: str = "Box Plot Comparison") -> io.BytesIO:
        """Create box plot for comparison"""
        fig, ax = plt.subplots(figsize=(12, 8))
        
        data = [data_dict[key] for key in data_dict.keys()]
        labels = list(data_dict.keys())
        
        bp = ax.boxplot(data, labels=labels, patch_artist=True,
                        boxprops=dict(facecolor='#00D9FF', alpha=0.7),
                        medianprops=dict(color='red', linewidth=2))
        
        ax.set_ylabel('Rating', fontsize=12)
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close()
        
        return buf
    
    def create_3d_surface(self, x: np.ndarray, y: np.ndarray, z: np.ndarray,
                         title: str = "3D Surface") -> io.BytesIO:
        """Create 3D surface plot"""
        fig = plt.figure(figsize=(14, 10))
        ax = fig.add_subplot(111, projection='3d')
        
        surf = ax.plot_surface(x, y, z, cmap='plasma', alpha=0.8,
                              linewidth=0, antialiased=True)
        
        ax.set_xlabel('X Axis', fontsize=12)
        ax.set_ylabel('Y Axis', fontsize=12)
        ax.set_zlabel('Z Axis', fontsize=12)
        ax.set_title(title, fontsize=14, fontweight='bold')
        
        fig.colorbar(surf, ax=ax, shrink=0.5, aspect=5)
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close()
        
        return buf
    
    def create_violin_plot(self, data_dict: Dict[str, List[float]],
                          title: str = "Violin Plot") -> io.BytesIO:
        """Create violin plot"""
        fig, ax = plt.subplots(figsize=(12, 8))
        
        data = [data_dict[key] for key in data_dict.keys()]
        labels = list(data_dict.keys())
        
        parts = ax.violinplot(data, showmeans=True, showmedians=True)
        
        for pc in parts['bodies']:
            pc.set_facecolor('#00D9FF')
            pc.set_alpha(0.7)
        
        ax.set_xticks(range(1, len(labels) + 1))
        ax.set_xticklabels(labels, rotation=45)
        ax.set_ylabel('Rating', fontsize=12)
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close()
        
        return buf
    
    def create_sankey_diagram(self, source: List[int], target: List[int], 
                             value: List[float], labels: List[str]) -> io.BytesIO:
        """Create Sankey diagram for flow visualization"""
        # Note: Requires plotly, but we'll create a simplified version with matplotlib
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # Create flow chart representation
        unique_sources = list(set(source))
        unique_targets = list(set(target))
        
        for i, (s, t, v) in enumerate(zip(source, target, value)):
            color = plt.cm.viridis(i / len(source))
            ax.barh(s, v, left=0, height=0.8, color=color, alpha=0.6)
            ax.barh(t + len(unique_sources), v, left=5, height=0.8, color=color, alpha=0.6)
            
            # Draw connecting lines
            ax.plot([v, 5], [s, t + len(unique_sources)], 
                   color=color, alpha=0.3, linewidth=v*2)
        
        ax.set_yticks(range(len(labels)))
        ax.set_yticklabels(labels)
        ax.set_title('Flow Diagram', fontsize=14, fontweight='bold')
        ax.set_xlim(-1, 10)
        
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close()
        
        return buf