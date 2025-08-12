#!/usr/bin/env python3
"""
Quick test to verify the layoff-leaderboard function works
"""

import asyncio
import sys
import os

# Add the backend directory to path
sys.path.append(os.path.join(os.path.dirname(__file__)))

async def test_leaderboard():
    """Test the layoff leaderboard function directly"""
    try:
        from layoff_estimator import generate_layoff_risk_leaderboard
        
        print("🧪 Testing generate_layoff_risk_leaderboard function...")
        result = await generate_layoff_risk_leaderboard(cost_per_researcher=200000, limit=3)
        
        print(f"✅ Function executed successfully!")
        print(f"📊 Result keys: {list(result.keys())}")
        
        if 'data' in result:
            print(f"🏛️ Found {len(result['data'])} institutions")
            for i, inst in enumerate(result['data'][:2]):  # Show first 2
                print(f"  {i+1}. {inst['institution']} - Risk Score: {inst['risk_score']}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = asyncio.run(test_leaderboard())
    
    if result:
        print("\n✅ Leaderboard function works correctly!")
    else:
        print("\n❌ Leaderboard function failed!")
