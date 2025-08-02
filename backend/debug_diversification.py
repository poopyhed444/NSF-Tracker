#!/usr/bin/env python3
"""
Debug script to test funding diversification calculation directly
"""

import asyncio
from layoff_estimator import generate_layoff_risk_leaderboard

async def debug_funding_diversification():
    print("Testing funding diversification calculation...")
    
    # Generate leaderboard with detailed funding info
    result = await generate_layoff_risk_leaderboard(limit=3)
    
    print(f"Generated leaderboard with {len(result.get('data', []))} institutions")
    
    for i, institution in enumerate(result.get('data', [])[:3]):
        name = institution.get('institution', 'Unknown')
        diversification = institution.get('funding_diversification', {})
        
        print(f"\n--- Institution {i+1}: {name} ---")
        print(f"Total funding: ${institution.get('total_active_funding', 0):,.2f}")
        print(f"Active grants: {institution.get('active_grants_count', 0)}")
        
        print("Funding breakdown:")
        print(f"  NIH: ${diversification.get('nih_funding', 0):,.2f} ({diversification.get('nih_percentage', 0)}%)")
        print(f"  NSF: ${diversification.get('nsf_funding', 0):,.2f} ({diversification.get('nsf_percentage', 0)}%)")
        print(f"  DOD: ${diversification.get('dod_funding', 0):,.2f} ({diversification.get('dod_percentage', 0)}%)")
        print(f"  DOE: ${diversification.get('doe_funding', 0):,.2f} ({diversification.get('doe_percentage', 0)}%)")
        print(f"Agencies with funding: {diversification.get('agencies_with_funding', 0)}")

if __name__ == "__main__":
    asyncio.run(debug_funding_diversification())
