#!/usr/bin/env python3
"""
Test script to verify that all restored endpoints are present and accessible.
"""

import requests
import time

def test_restored_endpoints():
    """Test that all restored endpoints respond correctly."""
    base_url = "http://localhost:8000"
    
    endpoints_to_test = [
        "/api/layoff-leaderboard?limit=5",
        "/api/renewal-patterns-analysis",
        "/api/usaspending-stats", 
        "/api/test-combined-grants",
        "/api/cache/status",
        "/api/institution-grants/Stanford%20University?limit=5"
    ]
    
    print("🧪 Testing Restored API Endpoints...")
    print("=" * 50)
    
    for endpoint in endpoints_to_test:
        try:
            print(f"Testing: {endpoint}")
            start_time = time.time()
            
            response = requests.get(f"{base_url}{endpoint}", timeout=30)
            elapsed_time = time.time() - start_time
            
            if response.status_code == 200:
                print(f"   ✅ Status: {response.status_code} - Response time: {elapsed_time:.3f}s")
                
                # Try to parse JSON
                try:
                    data = response.json()
                    if isinstance(data, dict):
                        keys = list(data.keys())[:5]  # First 5 keys
                        print(f"   📊 Data keys: {keys}")
                    else:
                        print(f"   📊 Data type: {type(data)}")
                except:
                    print(f"   📊 Response length: {len(response.text)} chars")
                    
            else:
                print(f"   ❌ Status: {response.status_code}")
                if response.status_code == 404:
                    print(f"   🔍 Endpoint not found - may still be missing")
                    
        except requests.exceptions.ConnectionError:
            print(f"   ❌ Connection error - server may not be running")
            break
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()
    
    print("=" * 50)
    print("✅ Endpoint restoration test completed!")

if __name__ == "__main__":
    test_restored_endpoints()
