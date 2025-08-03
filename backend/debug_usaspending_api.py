#!/usr/bin/env python3
"""
Debug script to test USASpending.gov API calls and see what's being returned for NIH/NSF
"""

import requests
import json
from datetime import datetime

def test_usaspending_api():
    """Test the USASpending.gov API with different configurations"""
    
    base_url = "https://api.usaspending.gov/api/v2"
    endpoint = f"{base_url}/search/spending_by_award"
    
    # Test 1: NSF only with different award types
    print("=== TEST 1: NSF with Research Grants ===")
    payload_nsf = {
        "filters": {
            "award_type_codes": ["04", "05", "06", "07", "08", "09", "10", "11"],  # Different grant codes
            "agencies": [{
                "type": "awarding",
                "tier": "toptier", 
                "name": "National Science Foundation"
            }]
        },
        "fields": [
            "Award ID", "Recipient Name", "Award Amount", "Awarding Agency", 
            "Award Description", "Start Date", "End Date", "Award Type"
        ],
        "page": 1,
        "limit": 10,
        "sort": "Award Amount",
        "order": "desc"
    }
    
    try:
        response = requests.post(endpoint, json=payload_nsf, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            print(f"NSF Results: {len(results)} awards found")
            
            for i, award in enumerate(results[:3]):
                print(f"  Award {i+1}:")
                print(f"    Recipient: {award.get('Recipient Name', 'N/A')}")
                print(f"    Amount: ${award.get('Award Amount', 0):,}")
                print(f"    Agency: {award.get('Awarding Agency', 'N/A')}")
                print(f"    Type: {award.get('Award Type', 'N/A')}")
                description = award.get('Award Description', '')
                if description:
                    print(f"    Description: {description[:100]}...")
                print()
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"NSF Test Error: {e}")
    
    print()
    
    # Test 2: Try the cooperative agreement and grant codes that should work
    print("=== TEST 2: NSF with Cooperative Agreements (B) ===")
    payload_nsf_coop = {
        "filters": {
            "award_type_codes": ["B"],  # Just cooperative agreements
            "agencies": [{
                "type": "awarding",
                "tier": "toptier", 
                "name": "National Science Foundation"
            }]
        },
        "fields": [
            "Award ID", "Recipient Name", "Award Amount", "Awarding Agency", 
            "Award Description", "Start Date", "End Date", "Award Type"
        ],
        "page": 1,
        "limit": 10,
        "sort": "Award Amount",
        "order": "desc"
    }
    
    try:
        response = requests.post(endpoint, json=payload_nsf_coop, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            print(f"NSF Cooperative Agreement Results: {len(results)} awards found")
            
            for i, award in enumerate(results[:5]):
                print(f"  Award {i+1}:")
                print(f"    Recipient: {award.get('Recipient Name', 'N/A')}")
                print(f"    Amount: ${award.get('Award Amount', 0):,}")
                print(f"    Agency: {award.get('Awarding Agency', 'N/A')}")
                print(f"    Type: {award.get('Award Type', 'N/A')}")
                print()
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"NSF Cooperative Agreement Test Error: {e}")

    print()
    
    # Test 3: HHS/NIH with different award types
    print("=== TEST 3: HHS/NIH with Research Grants ===")
    payload_hhs = {
        "filters": {
            "award_type_codes": ["04", "05", "06", "07", "08", "09", "10", "11"],  # Grant codes
            "agencies": [{
                "type": "awarding",
                "tier": "toptier", 
                "name": "Department of Health and Human Services"
            }]
        },
        "fields": [
            "Award ID", "Recipient Name", "Award Amount", "Awarding Agency", 
            "Awarding Sub Agency", "Award Description", "Start Date", "End Date", "Award Type"
        ],
        "page": 1,
        "limit": 10,
        "sort": "Award Amount",
        "order": "desc"
    }
    
    try:
        response = requests.post(endpoint, json=payload_hhs, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            print(f"HHS Research Grant Results: {len(results)} awards found")
            
            for i, award in enumerate(results[:3]):
                print(f"  Award {i+1}:")
                print(f"    Recipient: {award.get('Recipient Name', 'N/A')}")
                print(f"    Amount: ${award.get('Award Amount', 0):,}")
                print(f"    Agency: {award.get('Awarding Agency', 'N/A')}")
                print(f"    Sub Agency: {award.get('Awarding Sub Agency', 'N/A')}")
                print(f"    Type: {award.get('Award Type', 'N/A')}")
                description = award.get('Award Description', '')
                if description:
                    print(f"    Description: {description[:100]}...")
                print()
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"HHS Test Error: {e}")
    
    print()
    
    # Test 4: Get award type reference to see what codes are available
    print("=== TEST 4: Available Award Types ===")
    award_type_endpoint = f"{base_url}/references/award_types"
    
    try:
        response = requests.get(award_type_endpoint, timeout=30)
        if response.status_code == 200:
            data = response.json()
            award_types = data.get('results', [])
            
            print("Available award types:")
            for award_type in award_types:
                code = award_type.get('award_type_code', 'N/A')
                name = award_type.get('award_type', 'N/A')
                if any(keyword in name.lower() for keyword in ['grant', 'cooperative', 'research', 'agreement']):
                    print(f"  {code}: {name}")
                    
    except Exception as e:
        print(f"Award type search error: {e}")

    # Test 4: Simple agency search to see what's available
    print("=== TEST 4: Available Agencies ===")
    agency_endpoint = f"{base_url}/references/toptier_agencies"
    
    try:
        response = requests.get(agency_endpoint, timeout=30)
        if response.status_code == 200:
            data = response.json()
            agencies = data.get('results', [])
            
            print("Research-related agencies found:")
            for agency in agencies:
                name = agency.get('agency_name', '')
                if any(keyword in name.lower() for keyword in ['science', 'health', 'research', 'energy', 'defense']):
                    print(f"  {agency.get('agency_id', 'N/A')}: {name}")
                    
    except Exception as e:
        print(f"Agency search error: {e}")

if __name__ == "__main__":
    test_usaspending_api()
