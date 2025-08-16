#!/usr/bin/env python3
"""
Debug script to check actual field names in NIH terminated grants response
"""

import asyncio
import httpx
from datetime import datetime, timedelta

async def debug_nih_fields():
    """Debug the actual field names returned by NIH API"""
    
    nih_url = "https://api.reporter.nih.gov/v2/projects/search"
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    payload = {
        "criteria": {
            "project_end_date": {
                "from_date": start_date.strftime("%Y-%m-%d"),
                "to_date": end_date.strftime("%Y-%m-%d")
            }
        },
        "include_fields": [
            "ProjectNum", "Organization", "ContactPiName", "AwardAmount", 
            "ProjectStartDate", "ProjectEndDate", "ProjectTitle", "FiscalYear"
        ],
        "offset": 0,
        "limit": 1  # Just one grant to see field names
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(nih_url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            results = data.get("results", [])
            if results:
                grant = results[0]
                print("NIH Grant Fields:")
                for key, value in grant.items():
                    print(f"  {key}: {value}")
            else:
                print("No grants found")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(debug_nih_fields())
