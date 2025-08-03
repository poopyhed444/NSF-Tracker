#!/usr/bin/env python3
"""
Debug script to test USASpending.gov API with proper grant award types
"""

import requests
import json

def test_grant_types():
    base_url = "https://api.usaspending.gov/api/v2"
    endpoint = f"{base_url}/search/spending_by_award"
    
    # The API told us the grant award types are:
    # "02": "Block Grant"
    # "03": "Formula Grant" 
    # "04": "Project Grant"
    # "05": "Cooperative Agreement"
    
    # Test 1: NSF with Project Grants (most common for research)
    print("=== TEST 1: NSF with Project Grants (04) ===")
    payload_nsf_project = {
        "filters": {
            "award_type_codes": ["04"],  # Project Grant
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
        response = requests.post(endpoint, json=payload_nsf_project, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            print(f"NSF Project Grant Results: {len(results)} awards found")
            
            for i, award in enumerate(results[:5]):
                print(f"  Award {i+1}:")
                print(f"    Recipient: {award.get('Recipient Name', 'N/A')}")
                print(f"    Amount: ${award.get('Award Amount', 0):,}")
                print(f"    Agency: {award.get('Awarding Agency', 'N/A')}")
                print(f"    Type: {award.get('Award Type', 'N/A')}")
                description = award.get('Award Description', '')
                if description:
                    print(f"    Description: {description[:150]}...")
                print()
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"NSF Project Grant Test Error: {e}")
    
    print()
    
    # Test 2: NSF with Cooperative Agreements (05)
    print("=== TEST 2: NSF with Cooperative Agreements (05) ===")
    payload_nsf_coop = {
        "filters": {
            "award_type_codes": ["05"],  # Cooperative Agreement
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
                description = award.get('Award Description', '')
                if description:
                    print(f"    Description: {description[:150]}...")
                print()
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"NSF Cooperative Agreement Test Error: {e}")
    
    print()
    
    # Test 3: HHS/NIH with Project Grants (04)
    print("=== TEST 3: HHS/NIH with Project Grants (04) ===")
    payload_hhs_project = {
        "filters": {
            "award_type_codes": ["04"],  # Project Grant
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
        response = requests.post(endpoint, json=payload_hhs_project, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            print(f"HHS Project Grant Results: {len(results)} awards found")
            
            for i, award in enumerate(results[:5]):
                print(f"  Award {i+1}:")
                print(f"    Recipient: {award.get('Recipient Name', 'N/A')}")
                print(f"    Amount: ${award.get('Award Amount', 0):,}")
                print(f"    Agency: {award.get('Awarding Agency', 'N/A')}")
                print(f"    Sub Agency: {award.get('Awarding Sub Agency', 'N/A')}")
                print(f"    Type: {award.get('Award Type', 'N/A')}")
                description = award.get('Award Description', '')
                if description:
                    print(f"    Description: {description[:150]}...")
                print()
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"HHS Project Grant Test Error: {e}")
    
    print()
    
    # Test 4: Check all grant types for NSF
    print("=== TEST 4: NSF with ALL Grant Types (02,03,04,05) ===")
    payload_nsf_all_grants = {
        "filters": {
            "award_type_codes": ["02", "03", "04", "05"],  # All grant types
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
        "limit": 20,
        "sort": "Award Amount",
        "order": "desc"
    }
    
    try:
        response = requests.post(endpoint, json=payload_nsf_all_grants, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            print(f"NSF All Grant Types Results: {len(results)} awards found")
            
            # Count award types
            award_types = {}
            universities = []
            
            for award in results:
                award_type = award.get('Award Type', 'Unknown')
                award_types[award_type] = award_types.get(award_type, 0) + 1
                
                recipient = award.get('Recipient Name', '')
                if any(word in recipient.upper() for word in ['UNIVERSITY', 'COLLEGE', 'INSTITUTE']):
                    universities.append(award)
            
            print(f"Award Types found:")
            for award_type, count in award_types.items():
                print(f"  {award_type}: {count}")
            
            print(f"\nUniversities found: {len(universities)}")
            for i, award in enumerate(universities[:5]):
                print(f"  University {i+1}:")
                print(f"    Recipient: {award.get('Recipient Name', 'N/A')}")
                print(f"    Amount: ${award.get('Award Amount', 0):,}")
                print(f"    Type: {award.get('Award Type', 'N/A')}")
                print()
                
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"NSF All Grant Types Test Error: {e}")

if __name__ == "__main__":
    test_grant_types()
