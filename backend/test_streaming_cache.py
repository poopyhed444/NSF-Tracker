#!/usr/bin/env python3

import asyncio
from layoff_estimator import fetch_institution_grants

async def test_streaming_cache():
    print('🚀 Testing streaming cache functionality...')
    
    # Clear any existing cache first to see the full process
    print('Fetching fresh data to test streaming cache saves...')
    
    # This should trigger incremental saves every 1000 grants
    grants = await fetch_institution_grants(
        organization=None,  # Get all grants to trigger incremental saves
        pi_name=None,
        active_only=True,
        use_cache=True,  # Enable caching
        max_records_per_source=2000  # Enough to trigger incremental saves
    )
    
    print(f'✅ Test completed! Total grants: {len(grants)}')
    
    # Check if specific types were cached
    nih_count = len([g for g in grants if g.get("funding_agency") == "NIH"])
    nsf_count = len([g for g in grants if g.get("funding_agency") == "NSF"])
    
    print(f'📊 Grant breakdown: {nih_count} NIH, {nsf_count} NSF')
    print('🔍 Check the logs above for incremental cache save messages (💾)')

if __name__ == "__main__":
    asyncio.run(test_streaming_cache())
