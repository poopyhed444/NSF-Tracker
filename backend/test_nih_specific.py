#!/usr/bin/env python3
"""
Test NIH-specific funding from USASpending.gov
"""

import requests
import asyncio

async def test_nih_specific():
    """Test NIH-specific grant funding"""
    
    base_url = "https://api.usaspending.gov/api/v2"
    endpoint = f"{base_url}/search/spending_by_award"
    
    print("=== Testing NIH-Specific University Funding ===")
    print()
    
    # Test with NIH sub-agency filter
    payload_nih = {
        "filters": {
            "award_type_codes": ["04", "05"],  # Project Grant, Cooperative Agreement
            "agencies": [{
                "type": "awarding",
                "tier": "toptier", 
                "name": "Department of Health and Human Services"
            }],
            "sub_agencies": [{
                "type": "awarding",
                "tier": "subtier",
                "name": "National Institutes of Health"
            }]
        },
        "fields": [
            "Award ID", "Recipient Name", "Award Amount", "Awarding Agency", 
            "Awarding Sub Agency", "Award Description", "Start Date", "End Date", "Award Type"
        ],
        "page": 1,
        "limit": 20,
        "sort": "Award Amount",
        "order": "desc"
    }
    
    try:
        response = requests.post(endpoint, json=payload_nih, timeout=30)
        print(f"NIH Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            print(f"NIH Results: {len(results)} awards found")
            
            universities = []
            for award in results:
                recipient = award.get('Recipient Name', '')
                if any(word in recipient.upper() for word in ['UNIVERSITY', 'COLLEGE', 'INSTITUTE', 'MEDICAL CENTER']):
                    universities.append(award)
            
            print(f"Universities found: {len(universities)}")
            for i, award in enumerate(universities[:5]):
                print(f"  {i+1}. {award.get('Recipient Name', 'N/A')}")
                print(f"      Amount: ${award.get('Award Amount', 0):,}")
                print(f"      Sub Agency: {award.get('Awarding Sub Agency', 'N/A')}")
                description = award.get('Award Description', '')
                if description:
                    print(f"      Description: {description[:100]}...")
                print()
                
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"NIH Test Error: {e}")
    
    print()
    
    # Also test with just checking for NIH in sub-agency field
    print("=== Testing HHS awards that mention NIH ===")
    payload_hhs_nih = {
        "filters": {
            "award_type_codes": ["04", "05"],  # Project Grant, Cooperative Agreement
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
        "limit": 50,
        "sort": "Award Amount",
        "order": "desc"
    }
    
    try:
        response = requests.post(endpoint, json=payload_hhs_nih, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            
            nih_awards = []
            for award in results:
                sub_agency = award.get('Awarding Sub Agency', '')
                if 'NIH' in sub_agency or 'National Institute' in sub_agency:
                    nih_awards.append(award)
            
            print(f"Awards from NIH sub-agencies: {len(nih_awards)}")
            
            universities_nih = []
            for award in nih_awards:
                recipient = award.get('Recipient Name', '')
                if any(word in recipient.upper() for word in ['UNIVERSITY', 'COLLEGE', 'INSTITUTE', 'MEDICAL']):
                    universities_nih.append(award)
            
            print(f"Universities with NIH funding: {len(universities_nih)}")
            for i, award in enumerate(universities_nih[:5]):
                print(f"  {i+1}. {award.get('Recipient Name', 'N/A')}")
                print(f"      Amount: ${award.get('Award Amount', 0):,}")
                print(f"      Sub Agency: {award.get('Awarding Sub Agency', 'N/A')}")
                print()
                
    except Exception as e:
        print(f"HHS NIH Test Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_nih_specific())
