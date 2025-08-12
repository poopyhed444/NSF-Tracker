#!/usr/bin/env python3
"""
Test the layoff leaderboard endpoint directly to find the 500 error
"""

import sys
import os

# Add the backend directory to path
sys.path.append(os.path.join(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from enhanced_main import app

def test_layoff_leaderboard_endpoint():
    """Test the layoff leaderboard endpoint directly"""
    
    print("🧪 Testing /api/layoff-leaderboard endpoint...")
    
    client = TestClient(app)
    
    try:
        # Test the endpoint with a small limit to speed up testing
        response = client.get("/api/layoff-leaderboard?limit=3")
        
        print(f"📊 Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success! Response keys: {list(data.keys())}")
            
            if 'institutions' in data:
                institutions = data['institutions']
                print(f"🏛️ Found {len(institutions)} institutions")
                for i, inst in enumerate(institutions):
                    print(f"  {i+1}. {inst.get('institution', 'Unknown')} - Risk: {inst.get('risk_score', 0)}")
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
        print("\n✅ Layoff leaderboard endpoint working!")
    else:
        print("\n❌ Layoff leaderboard endpoint has issues!")
