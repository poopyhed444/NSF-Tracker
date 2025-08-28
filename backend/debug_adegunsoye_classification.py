#!/usr/bin/env python3
"""
Debug script to test ADEGUNSOYE grant classification
"""

import asyncio
import httpx

async def test_adegunsoye_grants():
    """Test how ADEGUNSOYE's grants are being classified"""
    
    # Search for ADEGUNSOYE grants
    nih_url = 'https://api.reporter.nih.gov/v2/projects/search'
    
    payload = {
        'criteria': {
            'pi_names': [{'any_name': 'ADEGUNSOYE'}]
        },
        'include_fields': [
            'ApplId', 'ProjectNum', 'ContactPiName', 'ProjectTitle', 
            'ProjectStartDate', 'ProjectEndDate', 'AwardAmount', 'IsActive',
            'Organization', 'ActivityCode', 'FiscalYear', 'AwardStatus'
        ],
        'limit': 20
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(nih_url, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            
            print(f'Found {len(results)} grants for ADEGUNSOYE:')
            
            for grant in results:
                org = grant.get('organization', {})
                org_name = org.get('org_name', '') if isinstance(org, dict) else str(org)
                
                if 'CHICAGO' in org_name.upper():
                    print(f'\\nGrant: {grant.get("project_num")}')
                    print(f'  PI: {grant.get("contact_pi_name")}')
                    print(f'  Organization: {org_name}')
                    print(f'  Is Active: {grant.get("is_active")}')
                    print(f'  Award Status: {grant.get("award_status", "Not specified")}')
                    print(f'  Start: {grant.get("project_start_date")}')
                    print(f'  End: {grant.get("project_end_date")}')
                    print(f'  Amount: ${grant.get("award_amount", 0):,}')
                    
                    # Test classification logic
                    status = grant.get('award_status', '').lower() if grant.get('award_status') else ''
                    is_active = grant.get('is_active')
                    
                    is_terminated = (status in ['terminated', 'cancelled', 'expired'] or 
                                   is_active is False)
                    
                    print(f'  Classification: {"TERMINATED" if is_terminated else "ACTIVE"}')
                    print(f'  Reason: status="{status}", is_active={is_active}')

if __name__ == "__main__":
    asyncio.run(test_adegunsoye_grants())
