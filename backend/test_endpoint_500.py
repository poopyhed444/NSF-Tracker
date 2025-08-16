#!/usr/bin/env python3
"""
Test the FastAPI layoff-leaderboard endpoint directly to identify the HTTP error
"""

import sys
import traceback

def test_endpoint():
    """Test the layoff-leaderboard endpoint using FastAPI TestClient"""
    
    try:
        print("🧪 Testing /api/layoff-leaderboard endpoint with TestClient...")
        
        # Import FastAPI and create test client
        from fastapi.testclient import TestClient
        from enhanced_main import app
        
        print("✅ Successfully imported app and TestClient")
        
        # Create test client
        client = TestClient(app)
        print("✅ TestClient created")
        
        # Make the same request as the frontend
        print("📡 Making GET request to /api/layoff-leaderboard?limit=25...")
        response = client.get("/api/layoff-leaderboard?limit=25")
        
        print(f"📊 Response status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Request successful!")
            data = response.json()
            print(f"Response keys: {list(data.keys())}")
            if 'institutions' in data:
                print(f"Number of institutions: {len(data['institutions'])}")
        else:
            print(f"❌ Request failed with status {response.status_code}")
            print(f"Response content: {response.text}")
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        traceback.print_exc()
    except Exception as e:
        print(f"❌ Error during request: {e}")
        print("Full traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    test_endpoint()
