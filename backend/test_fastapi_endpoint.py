#!/usr/bin/env python3
"""
Test the actual FastAPI endpoint to see the 500 error
"""
import requests
import json

def test_fastapi_endpoint():
    print("🔍 Testing FastAPI Endpoint Direct Call")
    print("=" * 50)
    
    # Test the endpoint that's failing
    url = "http://localhost:8000/api/layoff-leaderboard"
    params = {"limit": 25}
    
    print(f"🔄 Calling: {url}")
    print(f"🔄 Params: {params}")
    
    try:
        response = requests.get(url, params=params, timeout=60)
        print(f"✅ Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success! Response keys: {list(data.keys())}")
            if 'institutions' in data:
                print(f"✅ Institutions: {len(data['institutions'])}")
        else:
            print(f"❌ Error Response:")
            print(f"   Status: {response.status_code}")
            print(f"   Headers: {dict(response.headers)}")
            try:
                error_data = response.json()
                print(f"   Error Detail: {error_data}")
            except:
                print(f"   Raw Text: {response.text}")
    
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed - server not running on port 8000")
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
    except Exception as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    test_fastapi_endpoint()
