#!/usr/bin/env python3
"""
Debug script to check funding agency values
"""

import asyncio
from layoff_estimator import fetch_combined_grants

async def debug_grants():
    grants = await fetch_combined_grants(active_only=True)
    print(f'Total grants: {len(grants)}')
    
    if grants:
        print('\nSample grants:')
        for i, grant in enumerate(grants[:5]):
            print(f'Grant {i+1}:')
            print(f'  funding_agency: "{grant.get("funding_agency")}"')
            print(f'  award_amount: {grant.get("award_amount")}')
            print(f'  source: {grant.get("source")}')
            org = grant.get('organization', {})
            if isinstance(org, list) and org:
                print(f'  org_name: {org[0].get("org_name")}')
            elif isinstance(org, dict):
                print(f'  org_name: {org.get("org_name")}')
            print()

        # Check unique funding agencies
        agencies = set()
        for grant in grants:
            agency = grant.get("funding_agency")
            if agency:
                agencies.add(agency)
        
        print(f'Unique funding agencies found: {sorted(agencies)}')

if __name__ == "__main__":
    asyncio.run(debug_grants())
