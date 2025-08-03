#!/usr/bin/env python3
"""
Test the leaderboard generation to see if it's working correctly.
"""

import asyncio
from layoff_estimator import generate_layoff_risk_leaderboard

async def test_leaderboard():
    print("=== Testing Layoff Risk Leaderboard ===\n")
    
    try:
        print("Generating leaderboard with limit 5...")
        result = await generate_layoff_risk_leaderboard(limit=5)
        
        if 'error' in result:
            print(f"❌ Error: {result['error']}")
            print(f"   Note: {result.get('note', 'No additional details')}")
        else:
            print("✅ Leaderboard generated successfully!")
            
            # Check the structure
            if 'data' in result:
                institutions = result['data']
                print(f"   Found {len(institutions)} institutions")
                
                for i, inst in enumerate(institutions[:3], 1):
                    print(f"   {i}. {inst.get('institution', 'Unknown')}")
                    print(f"      Total funding: ${inst.get('total_active_funding', 0):,.2f}")
                    print(f"      Lab size: {inst.get('estimated_lab_size', 0)} researchers")
                    print(f"      Risk level: {inst.get('risk_level', 'Unknown')}")
                    print(f"      Risk score: {inst.get('risk_score', 0)}")
                    
                    # Show funding breakdown
                    diversification = inst.get('funding_diversification', {})
                    agencies = []
                    if diversification.get('nih_funding', 0) > 0:
                        agencies.append(f"NIH: ${diversification['nih_funding']:,.0f}")
                    if diversification.get('nsf_funding', 0) > 0:
                        agencies.append(f"NSF: ${diversification['nsf_funding']:,.0f}")
                    if diversification.get('dod_funding', 0) > 0:
                        agencies.append(f"DOD: ${diversification['dod_funding']:,.0f}")
                    if diversification.get('doe_funding', 0) > 0:
                        agencies.append(f"DOE: ${diversification['doe_funding']:,.0f}")
                    
                    if agencies:
                        print(f"      Agencies: {', '.join(agencies)}")
                    print(f"      Agencies with funding: {diversification.get('agencies_with_funding', 0)}")
                    print()
            else:
                print("   Unexpected result structure")
                print(f"   Keys: {list(result.keys())}")
                
    except Exception as e:
        print(f"❌ Exception occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_leaderboard())
