#!/usr/bin/env python3

import asyncio
import httpx

NIH_API_URL = "https://api.reporter.nih.gov/v2/projects/search"

async def test_project_types():
    """Test different project types to find what works"""
    
    print("🔍 Testing different project type combinations...")
    
    project_type_tests = [
        # Test 1: No project_types filter
        {
            "name": "No project_types filter",
            "criteria": {
                "fiscal_years": [2024, 2025]
            }
        },
        # Test 2: Try standard types
        {
            "name": "Standard types",
            "criteria": {
                "fiscal_years": [2024, 2025],
                "project_types": ["RESEARCH"]
            }
        },
        # Test 3: Try removing project_types but keep others
        {
            "name": "No project_types, with award_types",
            "criteria": {
                "fiscal_years": [2024, 2025],
                "award_types": ["ALL"]
            }
        },
        # Test 4: Just fiscal years and sort
        {
            "name": "Just fiscal years + sort",
            "criteria": {
                "fiscal_years": [2024, 2025]
            },
            "sort_field": "award_amount",
            "sort_order": "desc"
        }
    ]
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        for test in project_type_tests:
            try:
                search_criteria = {
                    "criteria": test["criteria"],
                    "include_fields": ["ContactPiName", "ProjectTitle", "Organization"],
                    "offset": 0,
                    "limit": 10
                }
                
                # Add sort if specified
                if "sort_field" in test:
                    search_criteria["sort_field"] = test["sort_field"]
                    search_criteria["sort_order"] = test["sort_order"]
                
                print(f"\nTesting: {test['name']}")
                response = await client.post(NIH_API_URL, json=search_criteria)
                response.raise_for_status()
                data = response.json()
                
                results_count = len(data.get('results', []))
                print(f"✅ Results: {results_count}")
                
                if results_count > 0:
                    print(f"  Sample: {data['results'][0].get('project_title', 'No title')[:60]}...")
                
            except Exception as e:
                print(f"❌ {test['name']} failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_project_types())
