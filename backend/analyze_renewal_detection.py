#!/usr/bin/env python3
"""
Detailed analysis of ARORA vs ADEGUNSOYE grant renewal detection
"""

import asyncio
import httpx
from datetime import datetime, timedelta
from enhanced_delayed_funding_tracker import EnhancedDelayedFundingTracker

async def get_arora_grant():
    """Get ARORA, RISHI's grant"""
    nih_url = 'https://api.reporter.nih.gov/v2/projects/search'
    
    payload = {
        'criteria': {
            'project_nums': ['7R35HL161249-04', '7R35HL161249']
        },
        'include_fields': [
            'ApplId', 'ProjectNum', 'ContactPiName', 'ProjectTitle', 
            'ProjectStartDate', 'ProjectEndDate', 'AwardAmount', 'IsActive',
            'Organization', 'ActivityCode', 'FiscalYear'
        ],
        'limit': 10
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(nih_url, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            if results:
                grant = results[0]
                return {
                    'project_num': grant.get('project_num'),
                    'award_id': grant.get('project_num'),
                    'contact_pi_name': grant.get('contact_pi_name'),
                    'pi_name': grant.get('contact_pi_name'),
                    'project_title': grant.get('project_title'),
                    'project_start_date': grant.get('project_start_date'),
                    'project_end_date': grant.get('project_end_date'),
                    'award_amount': grant.get('award_amount', 0),
                    'activity_code': grant.get('activity_code'),
                    'fiscal_year': grant.get('fiscal_year'),
                    'is_active': grant.get('is_active'),
                    'funding_agency': 'NIH',
                    'organization': grant.get('organization')
                }
    return None

async def get_adegunsoye_grants():
    """Get ADEGUNSOYE, AYODEJI's grants"""
    nih_url = 'https://api.reporter.nih.gov/v2/projects/search'
    
    payload = {
        'criteria': {
            'pi_names': [{'any_name': 'ADEGUNSOYE'}]
        },
        'include_fields': [
            'ApplId', 'ProjectNum', 'ContactPiName', 'ProjectTitle', 
            'ProjectStartDate', 'ProjectEndDate', 'AwardAmount', 'IsActive',
            'Organization', 'ActivityCode', 'FiscalYear'
        ],
        'limit': 20
    }
    
    grants = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(nih_url, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            
            for grant in results:
                org = grant.get('organization', {})
                org_name = org.get('org_name', '') if isinstance(org, dict) else str(org)
                
                if 'CHICAGO' in org_name.upper():
                    grants.append({
                        'project_num': grant.get('project_num'),
                        'award_id': grant.get('project_num'),
                        'contact_pi_name': grant.get('contact_pi_name'),
                        'pi_name': grant.get('contact_pi_name'),
                        'project_title': grant.get('project_title'),
                        'project_start_date': grant.get('project_start_date'),
                        'project_end_date': grant.get('project_end_date'),
                        'award_amount': grant.get('award_amount', 0),
                        'activity_code': grant.get('activity_code'),
                        'fiscal_year': grant.get('fiscal_year'),
                        'is_active': grant.get('is_active'),
                        'funding_agency': 'NIH',
                        'organization': grant.get('organization')
                    })
    
    return grants

async def analyze_renewal_logic():
    """Analyze why ARORA is detected as non-renewal but ADEGUNSOYE isn't"""
    
    tracker = EnhancedDelayedFundingTracker()
    
    # Get grants for both PIs
    arora_grant = await get_arora_grant()
    adegunsoye_grants = await get_adegunsoye_grants()
    
    all_grants = []
    if arora_grant:
        all_grants.append(arora_grant)
    all_grants.extend(adegunsoye_grants)
    
    print("=== DETAILED RENEWAL ANALYSIS ===\n")
    
    if arora_grant:
        print(f"ARORA, RISHI - Grant: {arora_grant['project_num']}")
        print(f"  Title: {arora_grant['project_title']}")
        print(f"  Start: {arora_grant['project_start_date']}")
        print(f"  End: {arora_grant['project_end_date']}")
        print(f"  Active: {arora_grant['is_active']}")
        print(f"  Activity Code: {arora_grant['activity_code']}")
        print(f"  Amount: ${arora_grant['award_amount']:,}")
        
        # Check renewal eligibility
        eligible = tracker._is_renewal_eligible_grant(arora_grant)
        print(f"  Renewal eligible: {eligible}")
        
        if eligible:
            expected_renewal = tracker._calculate_expected_renewal_date(arora_grant)
            print(f"  Expected renewal date: {expected_renewal}")
            
            if expected_renewal:
                days_overdue = (datetime.now() - expected_renewal).days
                grace_period_check = expected_renewal < datetime.now() - timedelta(days=90)
                print(f"  Days overdue: {days_overdue}")
                print(f"  Past grace period (90 days): {grace_period_check}")
                
                renewal_found = tracker._check_for_renewal_evidence_sync(arora_grant, all_grants)
                print(f"  Renewal evidence found: {renewal_found}")
                
                should_be_flagged = grace_period_check and not renewal_found
                print(f"  Should be flagged as non-renewal: {should_be_flagged}")
        print()
    
    print(f"ADEGUNSOYE, AYODEJI - {len(adegunsoye_grants)} grants:")
    for i, grant in enumerate(adegunsoye_grants):
        print(f"  Grant {i+1}: {grant['project_num']}")
        print(f"    Title: {grant['project_title']}")
        print(f"    Start: {grant['project_start_date']}")
        print(f"    End: {grant['project_end_date']}")
        print(f"    Active: {grant['is_active']}")
        print(f"    Activity Code: {grant['activity_code']}")
        print(f"    Amount: ${grant['award_amount']:,}")
        
        # Check renewal eligibility
        eligible = tracker._is_renewal_eligible_grant(grant)
        print(f"    Renewal eligible: {eligible}")
        
        if eligible:
            expected_renewal = tracker._calculate_expected_renewal_date(grant)
            print(f"    Expected renewal date: {expected_renewal}")
            
            if expected_renewal:
                days_overdue = (datetime.now() - expected_renewal).days
                grace_period_check = expected_renewal < datetime.now() - timedelta(days=90)
                print(f"    Days overdue: {days_overdue}")
                print(f"    Past grace period (90 days): {grace_period_check}")
                
                renewal_found = tracker._check_for_renewal_evidence_sync(grant, all_grants)
                print(f"    Renewal evidence found: {renewal_found}")
                
                should_be_flagged = grace_period_check and not renewal_found
                print(f"    Should be flagged as non-renewal: {should_be_flagged}")
        print()
    
    # Check what the renewal eligibility logic is looking for
    print("=== RENEWAL ELIGIBILITY CRITERIA ===")
    print("Renewable activity codes: R01, R21, R03, R15, R16, R25, T32, T34, F31, P01, P30, P50, U01, U19, U54")
    
    if arora_grant:
        print(f"\nARORA's grant activity code: {arora_grant['activity_code']}")
        code = arora_grant['activity_code'].upper() if arora_grant['activity_code'] else ''
        renewable_types = ['R01', 'R21', 'R03', 'R15', 'R16', 'R25', 'T32', 'T34', 'F31', 'P01', 'P30', 'P50', 'U01', 'U19', 'U54']
        print(f"Is in renewable types: {code in renewable_types}")
    
    if adegunsoye_grants:
        for grant in adegunsoye_grants:
            print(f"\nADEGUNSOYE's grant {grant['project_num']} activity code: {grant['activity_code']}")
            code = grant['activity_code'].upper() if grant['activity_code'] else ''
            renewable_types = ['R01', 'R21', 'R03', 'R15', 'R16', 'R25', 'T32', 'T34', 'F31', 'P01', 'P30', 'P50', 'U01', 'U19', 'U54']
            print(f"Is in renewable types: {code in renewable_types}")

if __name__ == "__main__":
    asyncio.run(analyze_renewal_logic())
