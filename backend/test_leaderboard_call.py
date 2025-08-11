#!/usr/bin/env python3
"""
Test the exact leaderboard call to debug the 0 results issue.
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_main import get_institution_funding_with_fallback

async def test_leaderboard_call():
    """Test the exact call that the leaderboard makes"""
    
    print("🧪 Testing exact leaderboard call...")
    print("This mimics: get_institution_funding_with_fallback(active_only=False, max_records_per_source=1000)")
    
    try:
        # This is the exact call from the leaderboard function
        grants = await get_institution_funding_with_fallback(
            active_only=False, 
            max_records_per_source=1000
        )
        
        print(f"✅ Leaderboard call returned: {len(grants)} grants")
        
        if grants:
            # Count by agency
            nih_count = len([g for g in grants if g.get("funding_agency") == "NIH"])
            nsf_count = len([g for g in grants if g.get("funding_agency") == "NSF"])
            print(f"📊 Breakdown: {nih_count} NIH + {nsf_count} NSF")
            
            # Check if using cache fallback
            cache_count = len([g for g in grants if g.get("_cache_fallback")])
            print(f"📦 Cache fallback items: {cache_count}")
            
            # Show sample grant
            print(f"📋 Sample grant: {grants[0].get('project_title', 'No title')[:80]}...")
        else:
            print("❌ No grants returned - this is the issue!")
            
        # Test with active_only=True for comparison
        print(f"\n🔄 Testing with active_only=True for comparison...")
        grants_active = await get_institution_funding_with_fallback(
            active_only=True, 
            max_records_per_source=1000
        )
        
        print(f"✅ Active grants call returned: {len(grants_active)} grants")
        
        if grants_active:
            nih_count = len([g for g in grants_active if g.get("funding_agency") == "NIH"])
            nsf_count = len([g for g in grants_active if g.get("funding_agency") == "NSF"])
            print(f"📊 Active breakdown: {nih_count} NIH + {nsf_count} NSF")
        
    except Exception as e:
        print(f"❌ Error testing leaderboard call: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_leaderboard_call())
