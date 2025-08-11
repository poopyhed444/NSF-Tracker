#!/usr/bin/env python3

import asyncio
from layoff_estimator import fetch_active_grants

async def test_incremental_nih_cache():
    print('🚀 Testing incremental NIH cache saves...')
    
    # Force fresh API call with cache disabled, then enabled for saving
    print('Fetching fresh NIH data to test incremental cache saves...')
    
    grants = await fetch_active_grants(
        organization=None,  # Get all grants
        pi_name=None,
        use_cache=True,  # Enable incremental caching
        max_records=2000  # Enough to trigger multiple batches and incremental saves
    )
    
    print(f'✅ Test completed! Total NIH grants: {len(grants)}')
    print('🔍 Look for "💾 Incremental NIH cache save" messages above')

if __name__ == "__main__":
    asyncio.run(test_incremental_nih_cache())
