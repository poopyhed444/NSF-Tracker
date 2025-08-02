#!/usr/bin/env python3
"""
Debug script to check which grants are assigned to specific institutions
"""

import asyncio
from layoff_estimator import fetch_combined_grants, normalize_institution_name

async def debug_institution_grants():
    grants = await fetch_combined_grants(active_only=True, use_cache=False)
    print(f'Total grants: {len(grants)}')
    
    # Look for UC grants specifically
    uc_grants = []
    for grant in grants:
        org_info = grant.get("organization", [{}])
        if isinstance(org_info, list) and len(org_info) > 0:
            org_name = org_info[0].get("org_name", "Unknown")
        else:
            org_name = "Unknown"
        
        normalized_name = normalize_institution_name(org_name)
        
        if "california" in normalized_name.lower() or "university of chicago" in normalized_name.lower():
            uc_grants.append({
                'original_name': org_name,
                'normalized_name': normalized_name,
                'agency': grant.get('funding_agency'),
                'amount': grant.get('award_amount', 0)
            })
    
    print(f'\nFound {len(uc_grants)} grants for UC/UChicago institutions:')
    for grant in uc_grants:
        print(f"  {grant['agency']} - ${grant['amount']:,.2f} - {grant['original_name']} -> {grant['normalized_name']}")

if __name__ == "__main__":
    asyncio.run(debug_institution_grants())
