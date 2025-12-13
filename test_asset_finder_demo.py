#!/usr/bin/env python3
"""
Demo: Show Example Assets Found by Asset Finder Agent

This script shows example output without needing an API key.
It demonstrates what assets would be found for different article topics.
"""

import json
from typing import List
from pipeline.agents.asset_finder import FoundAsset


def show_example_assets():
    """Show example assets that would be found."""
    
    print("\n" + "="*80)
    print("EXAMPLE ASSETS FOUND BY ASSET FINDER AGENT")
    print("="*80)
    print("\nThese are example assets that the agent would find using")
    print("Gemini AI + Google Search for different article topics.\n")
    
    # Example 1: AI Cybersecurity
    print("\n" + "="*80)
    print("EXAMPLE 1: AI Cybersecurity Automation Article")
    print("="*80)
    print("\nSearch Query: AI cybersecurity automation free stock images Technology")
    print("\nFound Assets:\n")
    
    assets_cyber = [
        FoundAsset(
            url="https://images.unsplash.com/photo-1563013544-824ae1b704d3?w=1920",
            title="Cybersecurity Operations Center",
            description="Modern security operations center with multiple monitors showing network security dashboards, threat detection visualizations, and real-time analytics. Professional tech environment.",
            source="Unsplash",
            image_type="photo",
            license_info="Free to use (Unsplash License)",
            width=1920,
            height=1080
        ),
        FoundAsset(
            url="https://images.pexels.com/photos/590016/pexels-photo-590016.jpeg?auto=compress&cs=tinysrgb&w=1920",
            title="AI Security Dashboard",
            description="Digital security dashboard displaying AI-powered threat detection, network monitoring, and automated response systems. Clean, modern interface design.",
            source="Pexels",
            image_type="illustration",
            license_info="Free to use (Pexels License)",
            width=1920,
            height=1080
        ),
        FoundAsset(
            url="https://cdn.pixabay.com/photo/2020/05/24/09/15/ethereum-5213525_1280.jpg",
            title="Blockchain Security Concept",
            description="Abstract visualization of blockchain security, encryption, and data protection. Digital shield protecting network connections.",
            source="Pixabay",
            image_type="infographic",
            license_info="Free to use (Pixabay License)",
            width=1920,
            height=1080
        ),
        FoundAsset(
            url="https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=1920",
            title="Network Security Visualization",
            description="3D network diagram showing secure connections, firewall protection, and encrypted data flows. Professional cybersecurity visualization.",
            source="Unsplash",
            image_type="diagram",
            license_info="Free to use (Unsplash License)",
            width=1920,
            height=1080
        ),
        FoundAsset(
            url="https://images.pexels.com/photos/1181244/pexels-photo-1181244.jpeg?auto=compress&cs=tinysrgb&w=1920",
            title="Data Protection Shield",
            description="Conceptual image of digital data protection, encryption keys, and security protocols. Modern cybersecurity theme.",
            source="Pexels",
            image_type="photo",
            license_info="Free to use (Pexels License)",
            width=1920,
            height=1080
        )
    ]
    
    for i, asset in enumerate(assets_cyber, 1):
        print(f"Asset {i}:")
        print(f"  📸 Title: {asset.title}")
        print(f"  🔗 URL: {asset.url}")
        print(f"  📦 Source: {asset.source}")
        print(f"  🎨 Type: {asset.image_type}")
        print(f"  📝 Description: {asset.description}")
        print(f"  📄 License: {asset.license_info}")
        print(f"  📐 Dimensions: {asset.width}x{asset.height}")
        print()
    
    # Example 2: Cloud Security
    print("\n" + "="*80)
    print("EXAMPLE 2: Cloud Security Best Practices Article")
    print("="*80)
    print("\nSearch Query: cloud security best practices free stock images Technology")
    print("\nFound Assets:\n")
    
    assets_cloud = [
        FoundAsset(
            url="https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1920",
            title="Cloud Infrastructure",
            description="Aerial view of cloud data centers and server infrastructure. Modern cloud computing environment with data storage facilities.",
            source="Unsplash",
            image_type="photo",
            license_info="Free to use (Unsplash License)",
            width=1920,
            height=1080
        ),
        FoundAsset(
            url="https://images.pexels.com/photos/1181298/pexels-photo-1181298.jpeg?auto=compress&cs=tinysrgb&w=1920",
            title="Cloud Security Architecture",
            description="Diagram showing cloud security layers, encryption, access controls, and multi-factor authentication. Professional cloud security visualization.",
            source="Pexels",
            image_type="diagram",
            license_info="Free to use (Pexels License)",
            width=1920,
            height=1080
        ),
        FoundAsset(
            url="https://cdn.pixabay.com/photo/2018/05/18/15/30/web-design-3411373_1280.jpg",
            title="Cloud Computing Concept",
            description="Abstract cloud computing visualization with connected nodes, data flows, and security elements. Modern tech illustration.",
            source="Pixabay",
            image_type="illustration",
            license_info="Free to use (Pixabay License)",
            width=1920,
            height=1080
        )
    ]
    
    for i, asset in enumerate(assets_cloud, 1):
        print(f"Asset {i}:")
        print(f"  📸 Title: {asset.title}")
        print(f"  🔗 URL: {asset.url}")
        print(f"  📦 Source: {asset.source}")
        print(f"  🎨 Type: {asset.image_type}")
        print(f"  📝 Description: {asset.description}")
        print(f"  📄 License: {asset.license_info}")
        print()
    
    # Example 3: Data Analytics
    print("\n" + "="*80)
    print("EXAMPLE 3: Data Analytics Dashboard Article")
    print("="*80)
    print("\nSearch Query: data analytics dashboard diagram infographic free stock images")
    print("\nFound Assets:\n")
    
    assets_data = [
        FoundAsset(
            url="https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=1920",
            title="Data Analytics Dashboard",
            description="Professional data analytics dashboard with charts, graphs, and KPIs. Business intelligence visualization on multiple screens.",
            source="Unsplash",
            image_type="infographic",
            license_info="Free to use (Unsplash License)",
            width=1920,
            height=1080
        ),
        FoundAsset(
            url="https://images.pexels.com/photos/590020/pexels-photo-590020.jpeg?auto=compress&cs=tinysrgb&w=1920",
            title="Business Intelligence Visualization",
            description="Modern BI dashboard showing data trends, analytics, and insights. Clean, professional design with colorful charts.",
            source="Pexels",
            image_type="illustration",
            license_info="Free to use (Pexels License)",
            width=1920,
            height=1080
        )
    ]
    
    for i, asset in enumerate(assets_data, 1):
        print(f"Asset {i}:")
        print(f"  📸 Title: {asset.title}")
        print(f"  🔗 URL: {asset.url}")
        print(f"  📦 Source: {asset.source}")
        print(f"  🎨 Type: {asset.image_type}")
        print(f"  📝 Description: {asset.description}")
        print(f"  📄 License: {asset.license_info}")
        print()
    
    # Show JSON format
    print("\n" + "="*80)
    print("JSON FORMAT (What the Agent Returns)")
    print("="*80)
    print("\nThe agent returns assets in this JSON format:\n")
    
    example_json = [
        {
            "url": "https://images.unsplash.com/photo-1563013544-824ae1b704d3",
            "title": "Cybersecurity Operations Center",
            "description": "Modern security operations center with multiple monitors",
            "source": "Unsplash",
            "image_type": "photo",
            "license_info": "Free to use (Unsplash License)",
            "width": 1920,
            "height": 1080
        },
        {
            "url": "https://images.pexels.com/photos/590016/pexels-photo-590016.jpeg",
            "title": "AI Security Dashboard",
            "description": "Digital security dashboard with AI analytics",
            "source": "Pexels",
            "image_type": "illustration",
            "license_info": "Free to use (Pexels License)",
            "width": 1920,
            "height": 1080
        }
    ]
    
    print(json.dumps(example_json, indent=2))
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"\n✅ Total example assets shown: {len(assets_cyber) + len(assets_cloud) + len(assets_data)}")
    print(f"   - AI Cybersecurity: {len(assets_cyber)} assets")
    print(f"   - Cloud Security: {len(assets_cloud)} assets")
    print(f"   - Data Analytics: {len(assets_data)} assets")
    print("\n📦 Sources: Unsplash, Pexels, Pixabay (all free stock photo sites)")
    print("🎨 Types: Photos, illustrations, infographics, diagrams")
    print("✅ All assets are free to use with proper attribution")
    print("\n💡 Note: These are example assets. With a real API key, the agent")
    print("   would search the internet and find actual relevant images!")


if __name__ == "__main__":
    show_example_assets()

