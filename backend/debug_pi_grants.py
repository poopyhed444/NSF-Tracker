#!/usr/bin/env python3
"""
Debug script to analyze why ADEGUNSOYE, AYODEJI doesn't show non-renewal grants
while ARORA, RISHI does.
"""

import asyncio
import json
from datetime import datetime, timedelta
from enhanced_delayed_funding_tracker import EnhancedDelayedFundingTracker

async def fetch_comprehensive_institution_grants(institution_name: str):
    """Fetch grants using the same method as main.py"""
    import httpx
    
    grants = []
    
    # Fetch from NIH Reporter API (same logic as main.py)
    nih_url = f"https://api.reporter.nih.gov/v2/projects/search"
    
    for fiscal_year in range(2020, 2026):  # 2020-2025
        payload = {
            "criteria": {
                "fiscal_years": [fiscal_year],
                "include_active_projects": True
            },
            "include_fields": [
                "ApplId", "SubprojectId", "FiscalYear", "Organization", "ProjectNum", 
                "OrgCountry", "ProjectNumSplit", "ContactPiName", "AllText", "FullStudySection",
                "ProjectStartDate", "ProjectEndDate", "PhrText", "SpendingCategories",
                "ProjectTitle", "AbstractText", "Terms", "PiNames", "OtherPiNames", 
                "ProgramOfficers", "AgencyCode", "ActivityCode", "AwardAmount", "IsActive",
                "Pis", "PrincipalInvestigators", "AwardNoticeDate"
            ],
            "offset": 0,
            "limit": 500
        }
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(nih_url, json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    year_grants = data.get('results', [])
                    
                    # Filter for University of Chicago grants
                    for grant in year_grants:
                        org_info = grant.get('organization', {})
                        if isinstance(org_info, dict):
                            org_name = org_info.get('org_name', '').upper()
                        else:
                            org_name = ''
                            
                        if 'CHICAGO' in org_name and 'UNIVERSITY' in org_name:
                            # Convert NIH format to our standard format
                            standardized_grant = {
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
                            grants.append(standardized_grant)
                            
                    print(f"Fiscal year {fiscal_year}: Found {len([g for g in year_grants if 'CHICAGO' in str(g.get('organization', {})).upper()])} UChicago grants")
                
        except Exception as e:
            print(f"Error fetching fiscal year {fiscal_year}: {e}")
    
    print(f"Total University of Chicago grants found: {len(grants)}")
    return grants

async def debug_pi_analysis():
    """Debug the PI analysis for both ARORA, RISHI and ADEGUNSOYE, AYODEJI"""
    
    # Get all UChicago grants
    all_grants = await fetch_comprehensive_institution_grants("University of Chicago")
    
    # Print all PIs found to see what names we have
    all_pis = set()
    for grant in all_grants:
        pi_name = grant.get('contact_pi_name', '')
        if pi_name:
            all_pis.add(pi_name)
    
    print(f"\n=== ALL PIs FOUND ===")
    sorted_pis = sorted(all_pis)
    for pi in sorted_pis:
        print(f"  {pi}")
    
    # Filter grants for each PI
    arora_grants = []
    adegunsoye_grants = []
    
    for grant in all_grants:
        pi_name = grant.get('contact_pi_name', '').upper()
        if 'ARORA' in pi_name and 'RISHI' in pi_name:
            arora_grants.append(grant)
        elif 'ADEGUNSOYE' in pi_name and 'AYODEJI' in pi_name:
            adegunsoye_grants.append(grant)
    
    # Also search for partial name matches
    print(f"\n=== SEARCHING FOR PARTIAL MATCHES ===")
    arora_partial = []
    adegunsoye_partial = []
    
    for grant in all_grants:
        pi_name = grant.get('contact_pi_name', '').upper()
        if 'ARORA' in pi_name:
            arora_partial.append(grant)
            print(f"Found ARORA: {grant.get('contact_pi_name')}")
        if 'ADEGUNSOYE' in pi_name:
            adegunsoye_partial.append(grant)
            print(f"Found ADEGUNSOYE: {grant.get('contact_pi_name')}")
    
    # Use partial matches if exact matches not found
    if not arora_grants and arora_partial:
        arora_grants = arora_partial
        print(f"Using partial matches for ARORA: {len(arora_grants)} grants")
    
    if not adegunsoye_grants and adegunsoye_partial:
        adegunsoye_grants = adegunsoye_partial
        print(f"Using partial matches for ADEGUNSOYE: {len(adegunsoye_grants)} grants")
    
    print(f"\n=== ARORA, RISHI GRANTS ===")
    print(f"Found {len(arora_grants)} grants:")
    for grant in arora_grants:
        print(f"  {grant['project_num']}: {grant['project_title'][:60]}...")
        print(f"    Start: {grant['project_start_date']}, End: {grant['project_end_date']}")
        print(f"    Active: {grant.get('is_active')}, Amount: ${grant.get('award_amount', 0):,}")
        print(f"    Activity Code: {grant.get('activity_code')}")
        print()
    
    print(f"\n=== ADEGUNSOYE, AYODEJI GRANTS ===")
    print(f"Found {len(adegunsoye_grants)} grants:")
    for grant in adegunsoye_grants:
        print(f"  {grant['project_num']}: {grant['project_title'][:60]}...")
        print(f"    Start: {grant['project_start_date']}, End: {grant['project_end_date']}")
        print(f"    Active: {grant.get('is_active')}, Amount: ${grant.get('award_amount', 0):,}")
        print(f"    Activity Code: {grant.get('activity_code')}")
        print()
    
    # Now analyze renewal eligibility
    tracker = EnhancedDelayedFundingTracker()
    
    print(f"\n=== RENEWAL ELIGIBILITY ANALYSIS ===")
    
    print(f"\nARORA, RISHI grant analysis:")
    for grant in arora_grants:
        eligible = tracker._is_renewal_eligible_grant(grant)
        expected_renewal = tracker._calculate_expected_renewal_date(grant)
        renewal_found = tracker._check_for_renewal_evidence_sync(grant, all_grants)
        
        print(f"  {grant['project_num']}:")
        print(f"    Renewal eligible: {eligible}")
        print(f"    Expected renewal date: {expected_renewal}")
        print(f"    Renewal evidence found: {renewal_found}")
        
        if eligible and expected_renewal:
            days_overdue = (datetime.now() - expected_renewal).days
            print(f"    Days overdue: {days_overdue}")
            print(f"    Grace period check (90 days): {days_overdue > 90}")
        print()
    
    print(f"\nADEGUNSOYE, AYODEJI grant analysis:")
    for grant in adegunsoye_grants:
        eligible = tracker._is_renewal_eligible_grant(grant)
        expected_renewal = tracker._calculate_expected_renewal_date(grant)
        renewal_found = tracker._check_for_renewal_evidence_sync(grant, all_grants)
        
        print(f"  {grant['project_num']}:")
        print(f"    Renewal eligible: {eligible}")
        print(f"    Expected renewal date: {expected_renewal}")
        print(f"    Renewal evidence found: {renewal_found}")
        
        if eligible and expected_renewal:
            days_overdue = (datetime.now() - expected_renewal).days
            print(f"    Days overdue: {days_overdue}")
            print(f"    Grace period check (90 days): {days_overdue > 90}")
        print()

if __name__ == "__main__":
    asyncio.run(debug_pi_analysis())
