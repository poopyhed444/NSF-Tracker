#!/usr/bin/env python3
"""
Test FastAPI endpoint serialization
"""
import asyncio
import json

async def test_serialization():
    print("🔍 Testing FastAPI Endpoint Serialization")
    print("=" * 50)
    
    try:
        from layoff_estimator import generate_layoff_risk_leaderboard
        
        print("🔄 Getting leaderboard data...")
        result = await generate_layoff_risk_leaderboard(200000, 25)
        
        print(f"✅ Got result with keys: {list(result.keys())}")
        
        # Test JSON serialization
        try:
            json_str = json.dumps(result, default=str)
            print(f"✅ JSON serialization successful! Length: {len(json_str)}")
        except Exception as json_e:
            print(f"❌ JSON serialization failed: {json_e}")
            print(f"❌ Checking each key...")
            for key, value in result.items():
                try:
                    json.dumps(value, default=str)
                    print(f"  ✅ {key}: OK")
                except Exception as key_e:
                    print(f"  ❌ {key}: {key_e}")
                    print(f"      Type: {type(value)}")
        
        # Test conversion to frontend format
        print("\n🔄 Testing frontend format conversion...")
        if 'data' in result:
            frontend_result = {
                "institutions": result['data'],
                "total_institutions": result.get('total_institutions', len(result['data'])),
                "methodology": result.get('methodology', {}),
                "last_updated": result.get('last_updated', "2025-08-11T23:20:00")
            }
            
            try:
                json_str = json.dumps(frontend_result, default=str)
                print(f"✅ Frontend format serialization successful!")
                print(f"✅ Institutions count: {len(frontend_result['institutions'])}")
            except Exception as fe:
                print(f"❌ Frontend format serialization failed: {fe}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_serialization())
