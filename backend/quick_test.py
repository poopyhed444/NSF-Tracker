#!/usr/bin/env python3
"""
Simple test to verify the corrected USASpending integration is working
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(__file__))

from federal_agency_integrator import FederalAgencyIntegrator

async def quick_test():
    """Quick test of the integration"""
    
    print("=== Quick USASpending Integration Test ===")
    print()
    
    integrator = FederalAgencyIntegrator()
    
    # Test NSF funding (should work well now)
    print("Testing NSF funding...")
    nsf_data = await integrator.fetch_usaspending_data(
        agency_codes=['020'],  # NSF
        limit=5
    )
    
    print(f"NSF data retrieved: {len(nsf_data)} awards")
    
    for award in nsf_data:
        recipient = award.get('Recipient Name', 'Unknown')
        amount = award.get('Award Amount', 0)
        print(f"  - {recipient}: ${amount:,}")
    
    print()
    
    # Test funding aggregation
    print("Testing funding aggregation...")
    
    funding_totals = {}
    for award in nsf_data:
        recipient = award.get('Recipient Name', '')
        amount = award.get('Award Amount', 0)
        
        if recipient:
            funding_totals[recipient] = funding_totals.get(recipient, 0) + amount
    
    sorted_funding = sorted(funding_totals.items(), key=lambda x: x[1], reverse=True)
    
    print("Top NSF recipients:")
    for recipient, total in sorted_funding[:3]:
        print(f"  - {recipient}: ${total:,}")
    
    # Check if we have non-zero amounts
    has_funding = any(amount > 0 for amount in funding_totals.values())
    print(f"\n✅ Non-zero funding found: {has_funding}")
    
    if has_funding:
        print("🎉 SUCCESS: USASpending integration is working with correct award types!")
    else:
        print("❌ ISSUE: Still getting zero funding amounts")

if __name__ == "__main__":
    asyncio.run(quick_test())
