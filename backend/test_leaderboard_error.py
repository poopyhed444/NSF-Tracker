#!/usr/bin/env python3
"""
Test the layoff leaderboard endpoint directly to see the error
"""
import asyncio
import traceback

async def test_leaderboard_error():
    print("🔍 Testing Layoff Leaderboard for 500 Error")
    print("=" * 50)
    
    try:
        from layoff_estimator import generate_layoff_risk_leaderboard
        
        print("🔄 Calling generate_layoff_risk_leaderboard...")
        result = await generate_layoff_risk_leaderboard(200000, 25)
        
        print(f"✅ Success! Result type: {type(result)}")
        print(f"✅ Result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
        
        if isinstance(result, dict):
            if 'data' in result:
                print(f"✅ Found 'data' key with {len(result['data'])} items")
            if 'leaderboard' in result:
                print(f"✅ Found 'leaderboard' key with {len(result['leaderboard'])} items")
        
    except Exception as e:
        print(f"❌ Error in generate_layoff_risk_leaderboard: {e}")
        print(f"❌ Error type: {type(e)}")
        traceback.print_exc()
        
        # Try to see if it's an import issue
        try:
            from layoff_estimator import generate_layoff_risk_leaderboard
            print("✅ Import successful")
        except Exception as import_e:
            print(f"❌ Import failed: {import_e}")

if __name__ == "__main__":
    asyncio.run(test_leaderboard_error())
