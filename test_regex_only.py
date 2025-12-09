#!/usr/bin/env python3
"""
Test only the HTML renderer regex fixes with sample problematic content
"""
import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pipeline.processors.html_renderer import HTMLRenderer

# Sample content with the issues you identified
test_content = """
<p>This means you must authenticate and authorize every single connection attempt, whether it originates from a coffee shop or the corporate data center. </p><ul><li>First, verify explicitly by using all available data points, including user identity, location, [1]</li></ul><p>You can break this down into three main pillars. </p><p><strong>zero trust security architecture</strong></p><p>Microsoft's internal implementation demonstrates the power of this identity-first approach.</p>
"""

print("🧪 TESTING REGEX FIXES")
print("=" * 50)
print("ORIGINAL CONTENT:")
print(test_content)
print("\n" + "=" * 50)

# Test the _cleanup_content method
cleaned_content = HTMLRenderer._cleanup_content(test_content)

print("AFTER CLEANUP:")
print(cleaned_content)
print("\n" + "=" * 50)

# Test specific issues:
print("ISSUE ANALYSIS:")
print(f"1. Contains <strong> tags: {'<strong>' in cleaned_content}")
print(f"2. Has broken sentence fragments: {'</p><p>' in cleaned_content}")
print(f"3. Empty list items: {'<li></li>' in cleaned_content or '<li>[' in cleaned_content}")

# Test with more specific content that mimics the user's issue
test_content_2 = """
<p>In a </p><p>You can </p><p><strong>zero trust security architecture</strong></p><p> Microsoft's internal implementation demonstrates the power of this identity-first approach. By enforcing explicit verification and phasing out legacy authentication protocols, they reduced password spray attacks by 98% across their enterprise environment. </p><p> - database unless explicitly authorized. This containment strategy is a critical component of </p><p><strong>zero trust security architecture</strong></p><p> What is Continuous Monitoring and Device Trust?</p><p>That's why trust is e</p>
"""

print("\nTEST 2 - USER'S EXACT ISSUE:")
print("ORIGINAL:")
print(test_content_2)
print("\nCLEANED:")
cleaned_content_2 = HTMLRenderer._cleanup_content(test_content_2)
print(cleaned_content_2)