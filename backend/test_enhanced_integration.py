#!/usr/bin/env python3
"""
Test script for enhanced funding integration.
Tests the improved fetch_combined_grants function with NIH/NSF direct API integration.
"""

import asyncio
import json
from layoff_estimator import fetch_combined_grants, generate_layoff_risk_leaderboard

async def test_enhanced_integration():
    """Test the enhanced funding integration."""
    print("Testing Enhanced Federal Funding Integration")
    print("=" * 50)
    
    # Test 1: Fetch combined grants with fresh data
    print("\n1. Testing combined grant fetching (fresh data)...")
    try:
        grants = await fetch_combined_grants(use_cache=False, max_records_per_source=1000)
        
        # Count by agency
        nih_count = len([g for g in grants if g.get("funding_agency") == "NIH"])
        nsf_count = len([g for g in grants if g.get("funding_agency") == "NSF"])
        dod_count = len([g for g in grants if g.get("funding_agency") == "DOD"])
        doe_count = len([g for g in grants if g.get("funding_agency") == "DOE"])
        
        print(f"Total grants fetched: {len(grants)}")
        print(f"  - NIH: {nih_count}")
        print(f"  - NSF: {nsf_count}")
        print(f"  - DOD: {dod_count}")
        print(f"  - DOE: {doe_count}")
        
        # Show sample grants from each agency
        for agency in ["NIH", "NSF", "DOD", "DOE"]:
            agency_grants = [g for g in grants if g.get("funding_agency") == agency]
            if agency_grants:
                sample = agency_grants[0]
                print(f"\nSample {agency} grant:")
                print(f"  Institution: {sample.get('organization', [{}])[0].get('org_name', 'Unknown')}")
                print(f"  Amount: ${sample.get('award_amount', 0):,.2f}")
                print(f"  Source: {sample.get('source', 'Unknown')}")
        
    except Exception as e:
        print(f"Error in combined grant fetching: {e}")
    
    # Test 2: Generate leaderboard with enhanced data
    print("\n\n2. Testing layoff risk leaderboard with enhanced data...")
    try:
        leaderboard = await generate_layoff_risk_leaderboard(limit=5)
        
        if 'institutions' in leaderboard:
            print(f"Generated leaderboard with {len(leaderboard['institutions'])} institutions")
            
            for i, inst in enumerate(leaderboard['institutions'][:3], 1):
                print(f"\n#{i}. {inst['institution']}")
                print(f"  Risk Score: {inst['risk_score']}")
                print(f"  Total Active Funding: ${inst['total_active_funding']:,.2f}")
                
                # Check funding diversification
                if 'funding_diversification' in inst:
                    div = inst['funding_diversification']
                    print(f"  Funding Sources:")
                    if div.get('nih_percentage', 0) > 0:
                        print(f"    NIH: ${div.get('nih_funding', 0):,.0f} ({div.get('nih_percentage', 0)}%)")
                    if div.get('nsf_percentage', 0) > 0:
                        print(f"    NSF: ${div.get('nsf_funding', 0):,.0f} ({div.get('nsf_percentage', 0)}%)")
                    if div.get('dod_percentage', 0) > 0:
                        print(f"    DOD: ${div.get('dod_funding', 0):,.0f} ({div.get('dod_percentage', 0)}%)")
                    if div.get('doe_percentage', 0) > 0:
                        print(f"    DOE: ${div.get('doe_funding', 0):,.0f} ({div.get('doe_percentage', 0)}%)")
                    print(f"  Agencies with funding: {div.get('agencies_with_funding', 0)}")
        else:
            print("No institutions in leaderboard - possible error:")
            print(json.dumps(leaderboard, indent=2))
            
    except Exception as e:
        print(f"Error generating leaderboard: {e}")
    
    print("\n" + "=" * 50)
    print("Enhanced integration test completed!")

if __name__ == "__main__":
    asyncio.run(test_enhanced_integration())
