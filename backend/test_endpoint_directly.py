#!/usr/bin/env python3
"""
Test the fixed layoff-leaderboard endpoint using the FastAPI test client
"""

import sys
import os

# Add the backend directory to path
sys.path.append(os.path.join(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from enhanced_main import app

def test_layoff_leaderboard_endpoint():
    """Test the layoff-leaderboard endpoint using FastAPI test client"""
    
    print("🧪 Testing /api/layoff-leaderboard endpoint with TestClient...")
    
    client = TestClient(app)
    
    try:
        # Test the endpoint
        response = client.get("/api/layoff-leaderboard?limit=3")
        
        print(f"📊 Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success! Response keys: {list(data.keys())}")
            
            if 'institutions' in data:
                institutions = data['institutions']
                print(f"🏛️ Found {len(institutions)} institutions in leaderboard")
                
                for i, inst in enumerate(institutions[:2]):  # Show first 2
                    print(f"  {i+1}. {inst['institution']} - Risk Score: {inst['risk_score']}")
                    
            elif 'data' in data:
                institutions = data['data']
                print(f"🏛️ Found {len(institutions)} institutions in leaderboard")
                
                for i, inst in enumerate(institutions[:2]):  # Show first 2
                    print(f"  {i+1}. {inst['institution']} - Risk Score: {inst['risk_score']}")
                    
            return True
            
        else:
            print(f"❌ Error: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error details: {error_data}")
            except:
                print(f"Response text: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_layoff_leaderboard_endpoint()
    
    if success:
        print("\n✅ /api/layoff-leaderboard endpoint is working correctly!")
    else:
        print("\n❌ /api/layoff-leaderboard endpoint has issues!")
