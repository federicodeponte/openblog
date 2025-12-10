#!/usr/bin/env python3
"""
Show Example of Simple Prompt Generation
Demonstrates the clean, simple prompt that gets generated with company context.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pipeline.core.company_context import create_scaile_example
from pipeline.prompts.simple_article_prompt import build_article_prompt

def show_prompt_example():
    """Show example of the simple prompt generation."""
    
    print("📝 SIMPLE PROMPT EXAMPLE")
    print("=" * 60)
    print()
    
    # Create SCAILE context
    scaile_context = create_scaile_example()
    prompt_context = scaile_context.to_prompt_context()
    
    # Generate prompt
    prompt = build_article_prompt(
        primary_keyword="Answer Engine Optimization for B2B startups",
        company_context=prompt_context,
        language="en"
    )
    
    print("Generated prompt:")
    print("-" * 40)
    print(prompt)
    print("-" * 40)
    print()
    print(f"Prompt length: {len(prompt)} characters")
    print()
    
    print("🎯 KEY IMPROVEMENTS:")
    print("✅ No market awareness complexity")
    print("✅ Simple company context only") 
    print("✅ All fields optional except company URL")
    print("✅ Clean, readable prompt structure")
    print("✅ Flexible content guidelines")
    print("✅ No country/market parameters")
    print("✅ No complex fallback logic")

if __name__ == "__main__":
    show_prompt_example()