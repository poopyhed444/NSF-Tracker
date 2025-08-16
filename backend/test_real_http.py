#!/usr/bin/env python3
"""
Make a real HTTP request to the server to reproduce the 500 error
"""

import asyncio
import httpx

async def test_real_http_request():
    """Make a real HTTP request to the layoff-leaderboard endpoint"""
    
    try:
        print("🌐 Making real HTTP request to http://127.0.0.1:8000/api/layoff-leaderboard?limit=25")
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get("http://127.0.0.1:8000/api/layoff-leaderboard?limit=25")
            
            print(f"📊 Response status: {response.status_code}")
            print(f"📊 Response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                print("✅ Request successful!")
                data = response.json()
                print(f"Response keys: {list(data.keys())}")
                if 'institutions' in data:
                    print(f"Number of institutions: {len(data['institutions'])}")
            else:
                print(f"❌ Request failed with status {response.status_code}")
                print(f"Response content: {response.text}")
                
    except Exception as e:
        print(f"❌ Error during request: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_real_http_request())
