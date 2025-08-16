#!/usr/bin/env python3
"""
Test the cached layoff leaderboard endpoint
"""

import sys
import traceback

def test_cached_endpoint():
    """Test the layoff-leaderboard endpoint with caching"""
    
    try:
        print("🧪 Testing cached /api/layoff-leaderboard endpoint...")
        
        # Import FastAPI and create test client
        from fastapi.testclient import TestClient
        from enhanced_main import app
        
        # Create test client
        client = TestClient(app)
        print("✅ TestClient created")
        
        # First request - should generate fresh data
        print("📡 Making first request (should generate fresh data)...")
        response1 = client.get("/api/layoff-leaderboard?limit=5")
        
        print(f"📊 First response status: {response1.status_code}")
        
        if response1.status_code == 200:
            data1 = response1.json()
            cache_info1 = data1.get('cache_info', {})
            print(f"✅ First request successful! Cached: {cache_info1.get('cached', 'unknown')}")
            print(f"   Institutions: {len(data1.get('institutions', []))}")
            
            # Second request - should use cached data
            print("\n📡 Making second request (should use cache)...")
            response2 = client.get("/api/layoff-leaderboard?limit=5")
            
            if response2.status_code == 200:
                data2 = response2.json()
                cache_info2 = data2.get('cache_info', {})
                print(f"✅ Second request successful! Cached: {cache_info2.get('cached', 'unknown')}")
                print(f"   Institutions: {len(data2.get('institutions', []))}")
                
                # Test cache clearing
                print("\n🗑️ Testing cache clearing...")
                clear_response = client.post("/api/clear-leaderboard-cache")
                if clear_response.status_code == 200:
                    clear_data = clear_response.json()
                    print(f"✅ Cache cleared! Entries cleared: {clear_data.get('cleared_entries', 0)}")
                    
                    # Third request - should generate fresh data again
                    print("\n📡 Making third request (should generate fresh data after clear)...")
                    response3 = client.get("/api/layoff-leaderboard?limit=5")
                    
                    if response3.status_code == 200:
                        data3 = response3.json()
                        cache_info3 = data3.get('cache_info', {})
                        print(f"✅ Third request successful! Cached: {cache_info3.get('cached', 'unknown')}")
                        print(f"   Institutions: {len(data3.get('institutions', []))}")
                    else:
                        print(f"❌ Third request failed: {response3.status_code}")
                else:
                    print(f"❌ Cache clear failed: {clear_response.status_code}")
            else:
                print(f"❌ Second request failed: {response2.status_code}")
        else:
            print(f"❌ First request failed: {response1.status_code}")
            print(f"Response: {response1.text}")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    test_cached_endpoint()
