#!/usr/bin/env python3

import requests
import json

def test_usaspending_api():
    """Test USASpending API with a very simple request"""
    
    print("Testing USASpending API with minimal request...")
    
    # Simple request - just get any awards from DoE
    url = "https://api.usaspending.gov/api/v2/search/spending_by_award"
    
    # Very basic payload with required award_type_codes
    payload = {
        "filters": {
            "award_type_codes": ["B", "C", "D"]  # B=Cooperative Agreement, C=Block Grant, D=Project Grant
        },
        "fields": ["Award ID", "Recipient Name", "Award Amount", "Awarding Agency"],
        "page": 1,
        "limit": 5
    }
    
    print(f"Request URL: {url}")
    print(f"Request payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            print(f"✅ SUCCESS! Got {len(results)} results")
            
            if results:
                print("\nFirst result:")
                print(json.dumps(results[0], indent=2))
        else:
            print(f"❌ ERROR: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")

def test_with_agency_filter():
    """Test with a simple agency filter"""
    
    print("\n" + "="*50)
    print("Testing with agency filter...")
    
    url = "https://api.usaspending.gov/api/v2/search/spending_by_award"
    
    # Try with a simple agency filter + required award types
    payload = {
        "filters": {
            "award_type_codes": ["B", "C", "D"],  # Required field
            "agencies": [{
                "type": "awarding",
                "tier": "toptier",
                "name": "Department of Energy"
            }]
        },
        "fields": ["Award ID", "Recipient Name", "Award Amount", "Awarding Agency"],
        "page": 1,
        "limit": 3
    }
    
    print(f"Request payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            print(f"✅ SUCCESS! Got {len(results)} DoE results")
            
            if results:
                print("\nFirst DoE result:")
                print(json.dumps(results[0], indent=2))
        else:
            print(f"❌ ERROR: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")

if __name__ == "__main__":
    test_usaspending_api()
    test_with_agency_filter()
