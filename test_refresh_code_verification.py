#!/usr/bin/env python3
"""
Code Verification: Refresh vs Stage 2b Implementation

Verifies that refresh uses the same structured JSON output approach as stage 2b
without requiring API calls.
"""

import ast
import re
from pathlib import Path


def check_structured_output_usage(file_path: str) -> dict:
    """Check if a file uses structured JSON output like stage 2b"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    checks = {
        "uses_response_schema": False,
        "uses_response_mime_type": False,
        "parses_json_directly": False,
        "no_regex_cleanup": True,  # Should NOT use regex to extract JSON
        "has_error_handling": False
    }
    
    # Check for response_schema parameter
    if 'response_schema' in content:
        checks["uses_response_schema"] = True
    
    # Check for response_mime_type
    if 'response_mime_type' in content or 'application/json' in content:
        checks["uses_response_mime_type"] = True
    
    # Check for direct JSON parsing (json.loads)
    if 'json.loads' in content:
        checks["parses_json_directly"] = True
    
    # Check for regex cleanup (should NOT be present)
    regex_patterns = [
        r're\.sub.*json',
        r're\.findall.*json',
        r're\.search.*json',
        r'extract.*json.*regex',
        r'parse.*json.*regex'
    ]
    for pattern in regex_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            checks["no_regex_cleanup"] = False
    
    # Check for error handling
    if 'try:' in content and 'except' in content:
        checks["has_error_handling"] = True
    
    return checks


def compare_refresh_to_stage2b():
    """Compare refresh implementation to stage 2b"""
    print("="*60)
    print("REFRESH vs STAGE 2B - CODE VERIFICATION")
    print("="*60)
    
    refresh_file = Path("service/content_refresher.py")
    stage2b_file = Path("pipeline/blog_generation/stage_02b_quality_refinement.py")
    
    if not refresh_file.exists():
        print(f"❌ Refresh file not found: {refresh_file}")
        return False
    
    if not stage2b_file.exists():
        print(f"❌ Stage 2b file not found: {stage2b_file}")
        return False
    
    print(f"\n📄 Checking Refresh Implementation:")
    print(f"   File: {refresh_file}")
    refresh_checks = check_structured_output_usage(str(refresh_file))
    
    for check, passed in refresh_checks.items():
        status = "✅" if passed else "❌"
        print(f"   {status} {check.replace('_', ' ').title()}")
    
    print(f"\n📄 Checking Stage 2b Implementation:")
    print(f"   File: {stage2b_file}")
    stage2b_checks = check_structured_output_usage(str(stage2b_file))
    
    for check, passed in stage2b_checks.items():
        status = "✅" if passed else "❌"
        print(f"   {status} {check.replace('_', ' ').title()}")
    
    # Compare
    print(f"\n🔍 Comparison:")
    all_match = True
    for check in refresh_checks.keys():
        refresh_val = refresh_checks[check]
        stage2b_val = stage2b_checks[check]
        
        if refresh_val == stage2b_val:
            status = "✅"
        else:
            status = "⚠️"
            all_match = False
        
        print(f"   {status} {check.replace('_', ' ').title()}: Refresh={refresh_val}, Stage2b={stage2b_val}")
    
    # Check specific implementation details
    print(f"\n📋 Implementation Details:")
    
    with open(refresh_file, 'r') as f:
        refresh_content = f.read()
    
    with open(stage2b_file, 'r') as f:
        stage2b_content = f.read()
    
    details = {
        "Refresh uses response_schema": "response_schema=" in refresh_content,
        "Refresh uses response_mime_type": "response_mime_type" in refresh_content or "application/json" in refresh_content,
        "Refresh parses JSON directly": "json.loads" in refresh_content,
        "Stage 2b uses response_schema": "response_schema=" in stage2b_content,
        "Stage 2b uses model_json_schema": "model_json_schema" in stage2b_content,
    }
    
    for detail, passed in details.items():
        status = "✅" if passed else "❌"
        print(f"   {status} {detail}")
    
    print(f"\n📊 Summary:")
    refresh_score = sum(refresh_checks.values())
    stage2b_score = sum(stage2b_checks.values())
    
    print(f"   Refresh score: {refresh_score}/{len(refresh_checks)}")
    print(f"   Stage 2b score: {stage2b_score}/{len(stage2b_checks)}")
    
    if refresh_score >= 4 and all_match:
        print(f"\n✅ Refresh implementation matches Stage 2b approach!")
        print(f"   Both use structured JSON output to prevent hallucinations.")
        return True
    else:
        print(f"\n⚠️  Some differences found between implementations.")
        return False


if __name__ == "__main__":
    success = compare_refresh_to_stage2b()
    exit(0 if success else 1)

