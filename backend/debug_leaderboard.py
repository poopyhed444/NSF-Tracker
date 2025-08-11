#!/usr/bin/env python3

import asyncio
import sys
sys.path.append('.')

async def debug_leaderboard():
    try:
        print("🔍 Importing modules...")
        from enhanced_main import generate_comprehensive_leaderboard
        
        print("🔍 Testing leaderboard function...")
        result = await generate_comprehensive_leaderboard(cost_per_researcher=200000, limit=3)
        
        print("✅ Leaderboard function completed successfully!")
        print(f"Found {len(result.get('institutions', []))} institutions")
        
        if 'error' in result:
            print(f"❌ Error in result: {result['error']}")
        else:
            print("✅ No errors in result")
            
        # Check for cache fallback indicators
        methodology = result.get('methodology', {})
        if '_data_source_reliability' in methodology:
            print(f"📊 Data reliability: {methodology['_data_source_reliability']}")
        else:
            print("⚠️ No data reliability indicator found")
            
    except Exception as e:
        print(f"❌ Exception occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_leaderboard())
