#!/usr/bin/env python3

import asyncio
import httpx
from datetime import datetime, timedelta

NIH_API_URL = "https://api.reporter.nih.gov/v2/projects/search"

async def debug_nih_api():
    """Debug why NIH API returns 0 results for general queries"""
    
    print("🔍 Testing NIH API directly...")
    
    # Test 1: Simplified criteria
    simple_criteria = {
        "criteria": {
            "fiscal_years": [2024, 2025]
        },
        "include_fields": [
            "ContactPiName", "ProjectTitle", "Organization", "AwardAmount"
        ],
        "offset": 0,
        "limit": 50
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            print("Testing simple criteria (no filters)...")
            response = await client.post(NIH_API_URL, json=simple_criteria)
            response.raise_for_status()
            data = response.json()
            
            print(f"✅ Simple query returned {len(data.get('results', []))} results")
            if data.get('results'):
                first_grant = data['results'][0]
                print(f"Sample grant: {first_grant.get('project_title', 'No title')}")
                print(f"Organization: {first_grant.get('organization', 'No org')}")
                
        except Exception as e:
            print(f"❌ Simple query failed: {e}")
            
        # Test 2: Complex criteria (what we're currently using)
        complex_criteria = {
            "criteria": {
                "fiscal_years": [2022, 2023, 2024, 2025, 2026],
                "project_types": ["RESEARCH", "TRAINING", "CAREER", "OTHER_RESEARCH"],
                "award_types": ["ALL"]
            },
            "include_fields": [
                "AwardAmount", "ContactPiName", "ProjectTitle", "ProjectStartDate",
                "ProjectEndDate", "Organization", "FiscalYear", "FundingICs"
            ],
            "offset": 0,
            "limit": 50,
            "sort_field": "award_amount",
            "sort_order": "desc"
        }
        
        try:
            print("\nTesting complex criteria (current method)...")
            response = await client.post(NIH_API_URL, json=complex_criteria)
            response.raise_for_status()
            data = response.json()
            
            print(f"✅ Complex query returned {len(data.get('results', []))} results")
            if data.get('results'):
                first_grant = data['results'][0]
                print(f"Sample grant: {first_grant.get('project_title', 'No title')}")
                print(f"Organization: {first_grant.get('organization', 'No org')}")
                
        except Exception as e:
            print(f"❌ Complex query failed: {e}")

        # Test 3: University of California specific query
        uc_criteria = {
            "criteria": {
                "fiscal_years": [2024, 2025],
                "org_names": ["University of California"]
            },
            "include_fields": [
                "ContactPiName", "ProjectTitle", "Organization", "AwardAmount"
            ],
            "offset": 0,
            "limit": 10
        }
        
        try:
            print("\nTesting UC-specific criteria...")
            response = await client.post(NIH_API_URL, json=uc_criteria)
            response.raise_for_status()
            data = response.json()
            
            print(f"✅ UC query returned {len(data.get('results', []))} results")
            if data.get('results'):
                for i, grant in enumerate(data['results'][:3]):
                    print(f"  Grant {i+1}: {grant.get('project_title', 'No title')[:60]}...")
                    print(f"    Org: {grant.get('organization', 'No org')}")
                    
        except Exception as e:
            print(f"❌ UC query failed: {e}")

if __name__ == "__main__":
    asyncio.run(debug_nih_api())
