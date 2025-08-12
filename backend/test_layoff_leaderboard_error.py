#!/usr/bin/env python3
"""
Test the layoff leaderboard function to identify issues
"""

import asyncio
import sys
import os

# Add the backend directory to path
sys.path.append(os.path.join(os.path.dirname(__file__)))

async def test_leaderboard():
    try:
        from layoff_estimator import generate_layoff_risk_leaderboard
        
        print('🧪 Testing layoff leaderboard function...')
        result = await generate_layoff_risk_leaderboard(cost_per_researcher=200000, limit=3)
        print('✅ Success!')
        print(f'📊 Result keys: {list(result.keys())}')
        
        if 'data' in result:
            print(f'🏛️ Found {len(result["data"])} institutions')
            for i, inst in enumerate(result["data"]):
                print(f'  {i+1}. {inst.get("institution", "Unknown")} - Risk: {inst.get("risk_score", 0)}')
        else:
            print('⚠️ No data key found in result')
            print(f'Full result: {result}')
            
    except Exception as e:
        print(f'❌ Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_leaderboard())
