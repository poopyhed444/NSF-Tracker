#!/usr/bin/env python3
"""
Test the fetch_institution_grants function specifically.
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from layoff_estimator import fetch_institution_grants

async def test_institution_grants():
    """Test the fetch_institution_grants function with various institutions"""
    
    test_institutions = [
        "Stanford University",
        "University of California, Berkeley", 
        "Massachusetts Institute of Technology",
        "Harvard University",
        "University of Michigan"
    ]
    
    print("🧪 Testing fetch_institution_grants function...")
    
    for institution in test_institutions:
        print(f"\n🔍 Testing fetch_institution_grants for: '{institution}'")
        try:
            grants = await fetch_institution_grants(
                organization=institution,
                use_cache=False,
                max_records_per_source=100
            )
            print(f"  ✅ Found {len(grants)} total grants for '{institution}'")
            
            # Count by agency
            nih_count = len([g for g in grants if g.get("funding_agency") == "NIH"])
            nsf_count = len([g for g in grants if g.get("funding_agency") == "NSF"])
            print(f"  📊 Breakdown: {nih_count} NIH + {nsf_count} NSF")
            
            if grants:
                print(f"  📋 Sample grant: {grants[0].get('project_title', 'No title')[:80]}...")
                break  # Stop at first successful result
                
        except Exception as e:
            print(f"  ❌ Error fetching grants for '{institution}': {e}")
    
    # Test with no organization filter (should use cache)
    print(f"\n🔍 Testing fetch_institution_grants with no organization filter...")
    try:
        grants = await fetch_institution_grants(
            use_cache=True,
            max_records_per_source=1000
        )
        print(f"  ✅ Found {len(grants)} total grants (no filter)")
        
        # Count by agency
        nih_count = len([g for g in grants if g.get("funding_agency") == "NIH"])
        nsf_count = len([g for g in grants if g.get("funding_agency") == "NSF"])
        print(f"  📊 Breakdown: {nih_count} NIH + {nsf_count} NSF")
        
    except Exception as e:
        print(f"  ❌ Error fetching grants (no filter): {e}")

if __name__ == "__main__":
    asyncio.run(test_institution_grants())
