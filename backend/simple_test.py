#!/usr/bin/env python3
"""
Simple test to verify funding separation works.
"""

import asyncio
from layoff_estimator import fetch_institution_grants, fetch_total_funding_grants

async def simple_test():
    print("=== Simple Funding Separation Test ===\n")
    
    # Test institution grants (should be NIH + NSF only)
    print("1. Testing institution grants (NIH + NSF):")
    institution_grants = await fetch_institution_grants(max_records_per_source=10)
    
    agencies = set()
    for grant in institution_grants:
        agencies.add(grant.get("funding_agency", "UNKNOWN"))
    
    print(f"   Total grants: {len(institution_grants)}")
    print(f"   Agencies found: {sorted(agencies)}")
    print(f"   Expected: Only NIH and NSF")
    
    # Test total funding grants (should include all agencies)
    print("\n2. Testing total funding grants (all agencies):")
    total_grants = await fetch_total_funding_grants(max_records_per_source=20)
    
    agencies = set()
    for grant in total_grants:
        agencies.add(grant.get("funding_agency", "UNKNOWN"))
    
    print(f"   Total grants: {len(total_grants)}")
    print(f"   Agencies found: {sorted(agencies)}")
    print(f"   Expected: Multiple agencies (DOD, DOE, NIH, NSF, NASA, etc.)")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    asyncio.run(simple_test())
