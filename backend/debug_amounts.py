#!/usr/bin/env python3
"""
Debug script to check award amounts in grants
"""

import asyncio
from layoff_estimator import fetch_combined_grants

async def debug_award_amounts():
    grants = await fetch_combined_grants(active_only=True, use_cache=False)
    print(f'Total grants: {len(grants)}')
    
    if grants:
        # Check award amounts
        amounts = [float(g.get("award_amount", 0)) for g in grants]
        non_zero_amounts = [a for a in amounts if a > 0]
        
        print(f'Grants with zero amounts: {len(amounts) - len(non_zero_amounts)}')
        print(f'Grants with non-zero amounts: {len(non_zero_amounts)}')
        
        if non_zero_amounts:
            print(f'Min amount: ${min(non_zero_amounts):,.2f}')
            print(f'Max amount: ${max(non_zero_amounts):,.2f}')
            print(f'Average amount: ${sum(non_zero_amounts)/len(non_zero_amounts):,.2f}')
        
        # Show some sample grants with amounts
        print('\nSample grants with award amounts:')
        for i, grant in enumerate(grants[:10]):
            amount = grant.get("award_amount", 0)
            agency = grant.get("funding_agency", "Unknown")
            org = grant.get("organization", [{}])[0].get("org_name", "Unknown")
            print(f'Grant {i+1}: {agency} - ${amount:,.2f} - {org}')

if __name__ == "__main__":
    asyncio.run(debug_award_amounts())
