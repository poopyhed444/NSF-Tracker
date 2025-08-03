#!/usr/bin/env python3
"""
Test the API endpoints directly via HTTP.
"""

import asyncio
import httpx

async def test_api_endpoints():
    print("=== Testing API Endpoints ===\n")
    
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        # Test 1: Root endpoint
        try:
            print("1. Testing root endpoint...")
            response = await client.get(f"{base_url}/")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Message: {data.get('message', 'N/A')}")
                print(f"   Features: {len(data.get('features', []))} features listed")
            print()
        except Exception as e:
            print(f"   ❌ Error: {e}")
            print()
        
        # Test 2: Leaderboard endpoint
        try:
            print("2. Testing leaderboard endpoint...")
            response = await client.get(f"{base_url}/api/layoff-leaderboard?limit=3")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                institutions = data.get('institutions', [])
                print(f"   Found {len(institutions)} institutions")
                
                if institutions:
                    top_inst = institutions[0]
                    print(f"   Top institution: {top_inst.get('institution', 'Unknown')}")
                    print(f"   Total funding: ${top_inst.get('total_active_funding', 0):,.2f}")
                    print(f"   Lab size: {top_inst.get('estimated_lab_size', 0)} researchers")
            else:
                print(f"   ❌ Error response: {response.text}")
            print()
        except Exception as e:
            print(f"   ❌ Error: {e}")
            print()
        
        # Test 3: Test grants endpoint
        try:
            print("3. Testing grants endpoint...")
            response = await client.get(f"{base_url}/api/test-combined-grants")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Status: {data.get('status', 'Unknown')}")
                
                inst_analysis = data.get('institution_analysis', {})
                total_funding = data.get('total_funding', {})
                
                print(f"   Institution analysis: {inst_analysis.get('total_grants', 0)} grants")
                print(f"   Total funding: {total_funding.get('total_grants', 0)} grants")
                print(f"   Architecture: {data.get('architecture', 'N/A')}")
            else:
                print(f"   ❌ Error response: {response.text}")
            print()
        except Exception as e:
            print(f"   ❌ Error: {e}")
            print()

if __name__ == "__main__":
    asyncio.run(test_api_endpoints())
