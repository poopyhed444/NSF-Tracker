#!/usr/bin/env python3
"""
Test the updated university-details endpoint
"""

import asyncio
import sys
import os

# Add the backend directory to path
sys.path.append(os.path.join(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from enhanced_main import app

def test_university_details_endpoint():
    """Test the university-details endpoint with TestClient"""
    
    print("🧪 Testing /api/university-details endpoint with TestClient...")
    
    client = TestClient(app)
    
    try:
        # Test with a common university
        test_institution = "Stanford University"
        response = client.get(f"/api/university-details/{test_institution}")
        
        print(f"📊 Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success! Response keys: {list(data.keys())}")
            
            # Check for overview structure
            if 'overview' in data:
                overview = data['overview']
                print(f"📈 Overview keys: {list(overview.keys())}")
                print(f"💰 Active funding: ${overview.get('total_active_funding', 0):,.2f}")
                print(f"❌ Terminated funding: ${overview.get('total_terminated_funding', 0):,.2f}")
                print(f"⛰️ Funding cliff: {overview.get('funding_cliff_percentage', 0)}%")
                
            # Check for funding breakdown
            if 'funding_breakdown' in data:
                breakdown = data['funding_breakdown']
                print(f"🏛️ Funding breakdown keys: {list(breakdown.keys())}")
                
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
    success = test_university_details_endpoint()
    
    if success:
        print("\n✅ /api/university-details endpoint is working correctly!")
    else:
        print("\n❌ /api/university-details endpoint has issues!")
