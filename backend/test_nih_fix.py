#!/usr/bin/env python3

import asyncio
from layoff_estimator import fetch_active_grants

async def test_fix():
    print('🔧 Testing NIH API fix...')
    grants = await fetch_active_grants(organization=None, pi_name=None, use_cache=False, max_records=50)
    print(f'✅ SUCCESS! Fetched {len(grants)} grants')
    if grants:
        print(f'Sample grant: {grants[0].get("project_title", "No title")[:60]}...')
        org_info = grants[0].get("organization", {})
        if isinstance(org_info, list) and org_info:
            org_name = org_info[0].get("org_name", "No org")
        elif isinstance(org_info, dict):
            org_name = org_info.get("org_name", "No org") 
        else:
            org_name = "No org"
        print(f'Organization: {org_name}')

if __name__ == "__main__":
    asyncio.run(test_fix())
