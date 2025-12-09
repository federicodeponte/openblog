#!/usr/bin/env python3
"""
Test HTML list preservation with our fixed regex patterns
"""
import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pipeline.processors.html_renderer import HTMLRenderer

# Sample content with lists that should be PRESERVED
test_content_with_lists = """
<p>The National Institute of Standards and Technology (NIST) established the gold standard for this approach in Special Publication 800-207. Understanding these tenets is essential when you're designing a zero trust security architecture for your enterprise.</p>

<ul>
<li><strong>Continuous Verification:</strong> Never trust a user or device based on a previous verification; you must re-authenticate and authorize every single access request</li>
<li><strong>Least Privilege Access:</strong> Limit user access strictly to the resources they need for their current task, reducing the potential impact if an account is compromised</li>
<li><strong>Assume Breach:</strong> Operate with the mindset that the network is already compromised, which forces you to implement robust monitoring and encryption by default</li>
<li><strong>Device Context:</strong> Evaluate the security posture of the device (OS version, patch level) before granting access, not just the user's credentials</li>
</ul>

<p>Transitioning to a zero trust security architecture doesn't happen overnight. It requires a phased approach that prioritizes your most critical assets while minimizing disruption to users. Here's how to get started with a practical roadmap that scales with your organization.</p>

<ol>
<li><strong>Identify Critical Assets:</strong> Map out your most sensitive data, applications, and services to understand exactly what you need to protect first</li>
<li><strong>Map Transaction Flows:</strong> Visualize how users and applications interact with these assets so you can define legitimate traffic patterns</li>
<li><strong>Architect the Micro-perimeter:</strong> Design segmentation gateways that isolate protected surfaces, ensuring traffic must pass through a policy enforcement point</li>
<li><strong>Create Zero Trust Policy:</strong> Define granular rules based on the "who, what, when, where, and why" of access requests rather than just IP addresses</li>
<li><strong>Monitor and Maintain:</strong> Continuously inspect all traffic and logs to refine policies and detect anomalies in real-time</li>
</ol>

<p>No single vendor sells "Zero Trust" in a box, but specific tools are essential building blocks.</p>

<p>Here are the core components of a unified system:</p>
<ul>
<li><strong>Identity Providers (IdP):</strong> Tools like Okta or Microsoft Entra ID that manage user identities and facilitate MFA</li>
<li><strong>Policy Engines:</strong> Centralized brains that evaluate access requests against your security policies before granting permission</li>
<li><strong>Segmentation Gateways:</strong> Next-generation firewalls that enforce micro-segmentation to prevent lateral movement</li>
</ul>

<p>When evaluating these tools, look for open APIs and integration capabilities.</p>
"""

print("🧪 TESTING LIST PRESERVATION")
print("=" * 60)
print("ORIGINAL CONTENT:")
print(test_content_with_lists)
print("\n" + "=" * 60)

# Apply our cleanup method to see if lists survive
cleaned_content = HTMLRenderer._cleanup_content(test_content_with_lists)

print("AFTER HTML CLEANUP:")
print(cleaned_content)
print("\n" + "=" * 60)

# Count lists before and after
original_ul_count = test_content_with_lists.count('<ul>')
original_ol_count = test_content_with_lists.count('<ol>')
original_li_count = test_content_with_lists.count('<li>')

cleaned_ul_count = cleaned_content.count('<ul>')
cleaned_ol_count = cleaned_content.count('<ol>')
cleaned_li_count = cleaned_content.count('<li>')

print("LIST PRESERVATION ANALYSIS:")
print(f"UL lists: {original_ul_count} → {cleaned_ul_count} ({'✅ PRESERVED' if cleaned_ul_count == original_ul_count else '❌ LOST'})")
print(f"OL lists: {original_ol_count} → {cleaned_ol_count} ({'✅ PRESERVED' if cleaned_ol_count == original_ol_count else '❌ LOST'})")  
print(f"List items: {original_li_count} → {cleaned_li_count} ({'✅ PRESERVED' if cleaned_li_count == original_li_count else f'❌ LOST {original_li_count - cleaned_li_count}'})")

# Check for specific intro preservation
intro_preserved = "Here are the core components of a unified system:" in cleaned_content
print(f"Meaningful intro preserved: {'✅ YES' if intro_preserved else '❌ NO'}")

success = (cleaned_ul_count == original_ul_count and cleaned_ol_count == original_ol_count and cleaned_li_count >= original_li_count - 1)
print(f"\n🎯 Overall result: {'✅ SUCCESS - Lists preserved!' if success else '❌ FAILURE - Lists damaged'}")