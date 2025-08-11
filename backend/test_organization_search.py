#!/usr/bin/env python3
"""
Test organization-specific search for debugging.
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from layoff_estimator import fetch_active_grants, fetch_nsf_grants

async def test_organization_search():
    """Test searching for a specific organization"""
    
    # Test with a few well-known universities
    test_organizations = [
        "Stanford University",
        "STANFORD UNIVERSITY", 
        "Stanford",
        "Massachusetts Institute of Technology",
        "MIT",
        "University of California",
        "Harvard University"
    ]
    
    print("🧪 Testing NIH organization search...")
    
    for org in test_organizations:
        print(f"\n🔍 Testing NIH search for: '{org}'")
        try:
            nih_grants = await fetch_active_grants(
                organization=org, 
                use_cache=False, 
                max_records=100
            )
            print(f"  ✅ Found {len(nih_grants)} NIH grants for '{org}'")
            
            if nih_grants:
                print(f"  📊 Sample grant: {nih_grants[0].get('project_title', 'No title')}")
                break  # Stop at first successful result
                
        except Exception as e:
            print(f"  ❌ Error searching NIH for '{org}': {e}")
    
    print("\n🧪 Testing NSF organization search...")
    
    for org in test_organizations:
        print(f"\n🔍 Testing NSF search for: '{org}'")
        try:
            nsf_grants = await fetch_nsf_grants(
                organization=org, 
                use_cache=False, 
                max_records=100
            )
            print(f"  ✅ Found {len(nsf_grants)} NSF grants for '{org}'")
            
            if nsf_grants:
                print(f"  📊 Sample grant: {nsf_grants[0].get('project_title', 'No title')}")
                break  # Stop at first successful result
                
        except Exception as e:
            print(f"  ❌ Error searching NSF for '{org}': {e}")

if __name__ == "__main__":
    asyncio.run(test_organization_search())
