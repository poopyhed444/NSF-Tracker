#!/usr/bin/env python3
"""
Test script for the enhanced NSF-Tracker API with optimized caching.
"""

import requests
import json
import time

def test_api_endpoints():
    """Test various API endpoints to ensure they're working correctly."""
    base_url = "http://localhost:8000"
    
    print("🧪 Testing Enhanced NSF-Tracker API...")
    print("=" * 50)
    
    # Test 1: Root endpoint
    try:
        print("1. Testing root endpoint...")
        response = requests.get(f"{base_url}/", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Root endpoint working - Version: {data.get('version', 'Unknown')}")
            print(f"   📝 Message: {data.get('message', 'No message')}")
        else:
            print(f"   ❌ Root endpoint failed with status: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Root endpoint error: {e}")
    
    # Test 2: Cache status
    try:
        print("\n2. Testing cache status endpoint...")
        response = requests.get(f"{base_url}/api/cache/status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Cache status working - Type: {data.get('cache_type', 'Unknown')}")
            print(f"   📊 Performance: {data.get('performance', 'Unknown')}")
        else:
            print(f"   ❌ Cache status failed with status: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Cache status error: {e}")
    
    # Test 3: Cached analysis (should be fast)
    try:
        print("\n3. Testing cached delayed funding analysis...")
        start_time = time.time()
        response = requests.get(f"{base_url}/api/delayed-funding/Stanford%20University", timeout=30)
        elapsed_time = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            institution = data.get('institution', 'Unknown')
            has_cache_optimized = data.get('cache_optimized', False)
            method = data.get('method', 'Unknown')
            
            print(f"   ✅ Delayed funding analysis working")
            print(f"   🏢 Institution: {institution}")
            print(f"   ⚡ Response time: {elapsed_time:.3f}s")
            print(f"   🎯 Cache optimized: {has_cache_optimized}")
            print(f"   📊 Method: {method}")
            
            # Check if it's using cached data (should be very fast)
            if elapsed_time < 1.0:
                print(f"   🚀 FAST RESPONSE - Likely using optimized cache!")
            else:
                print(f"   🐌 Slow response - Performing fresh analysis")
                
        else:
            print(f"   ❌ Delayed funding analysis failed with status: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Delayed funding analysis error: {e}")
    
    # Test 4: Legacy endpoint
    try:
        print("\n4. Testing legacy endpoint...")
        start_time = time.time()
        response = requests.get(f"{base_url}/api/enhanced-delayed-funding/Stanford%20University", timeout=30)
        elapsed_time = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Legacy endpoint working (redirects to optimized)")
            print(f"   ⚡ Response time: {elapsed_time:.3f}s")
        else:
            print(f"   ❌ Legacy endpoint failed with status: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Legacy endpoint error: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 API Test Summary Complete!")

if __name__ == "__main__":
    test_api_endpoints()
