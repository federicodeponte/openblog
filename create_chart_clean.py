#!/usr/bin/env python3
"""
Clean, Simple Chart - Just Make It Look Good

Using matplotlib with modern, clean styling.
Simple and reliable.
"""

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import subprocess

def create_clean_chart():
    """Create a clean, simple chart that actually looks good."""
    print("📊 Creating clean, simple chart...\n")
    
    # Set modern style
    sns.set_style("white")
    plt.rcParams['font.family'] = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
    plt.rcParams['font.size'] = 12
    plt.rcParams['axes.spines.top'] = False
    plt.rcParams['axes.spines.right'] = False
    
    # Data
    labels = ['<3 months', '9-12+ months']
    values = [35, 13]
    colors = ['#9ACD32', '#90EE90']
    
    # Create figure
    fig, ax = plt.subplots(figsize=(10, 6), dpi=100)
    
    # Create bars
    bars = ax.bar(labels, values, color=colors, width=0.5, edgecolor='white', linewidth=2)
    
    # Add value labels
    for i, (bar, val) in enumerate(zip(bars, values)):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 1,
                f'{val}%',
                ha='center', va='bottom',
                fontsize=14, fontweight=600, color='#09090b')
    
    # Title
    ax.set_title('Your Content Is 3x More Likely to Get Cited\nIf It\'s Less Than 3 Months Old',
                 fontsize=16, fontweight=600, color='#09090b', pad=20)
    
    # Y-axis
    ax.set_ylabel('Citation Rate (%)', fontsize=13, fontweight=500, color='#71717a')
    ax.set_ylim(0, 42)
    ax.yaxis.set_tick_params(colors='#71717a', labelsize=11)
    ax.yaxis.grid(True, color='#e4e4e7', linestyle='--', linewidth=0.5, alpha=0.7)
    ax.set_axisbelow(True)
    
    # X-axis
    ax.xaxis.set_tick_params(colors='#71717a', labelsize=12)
    ax.spines['bottom'].set_color('#e4e4e7')
    ax.spines['left'].set_color('#e4e4e7')
    
    # Source
    fig.text(0.99, 0.02, 'Source: airops Research',
             ha='right', fontsize=10, style='italic', color='#a1a1aa')
    
    # Tight layout
    plt.tight_layout()
    
    # Save as WebP
    output_file = Path('output/real_charts/citation_statistics_clean.webp')
    output_file.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_file, format='webp', dpi=100, bbox_inches='tight', facecolor='white')
    plt.close()
    
    file_size = output_file.stat().st_size // 1024
    print(f"✅ Created: {output_file.name} ({file_size}KB)")
    print(f"   Clean, simple, modern design")
    
    # Open
    subprocess.run(['open', '-a', 'Preview', str(output_file)])
    print(f"\n✅ Opened in Preview!")

if __name__ == "__main__":
    create_clean_chart()

