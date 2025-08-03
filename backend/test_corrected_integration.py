#!/usr/bin/env python3
"""
Test the corrected USASpending.gov integration
"""

import asyncio
import sys
sys.path.append('.')

from federal_agency_integrator import FederalAgencyIntegrator

async def test_corrected_integration():
    """Test the corrected award type codes"""
    
    integrator = FederalAgencyIntegrator()
    
    print("=== Testing Corrected USASpending Integration ===")
    print()
    
    # Test NSF with correct award types
    print("1. Testing NSF with corrected award types (04, 05)...")
    nsf_data = await integrator.fetch_usaspending_data(
        agency_codes=['020'],  # NSF
        award_types=['04', '05'],  # Project Grant, Cooperative Agreement
        limit=10
    )
    
    print(f"NSF Results: {len(nsf_data)} awards found")
    universities_nsf = []
    for award in nsf_data:
        recipient = award.get('Recipient Name', '')
        if any(word in recipient.upper() for word in ['UNIVERSITY', 'COLLEGE', 'INSTITUTE']):
            universities_nsf.append(award)
    
    print(f"Universities in NSF data: {len(universities_nsf)}")
    for i, award in enumerate(universities_nsf[:3]):
        print(f"  {i+1}. {award.get('Recipient Name', 'N/A')}: ${award.get('Award Amount', 0):,}")
    
    print()
    
    # Test HHS/NIH with correct award types
    print("2. Testing HHS/NIH with corrected award types (04, 05)...")
    hhs_data = await integrator.fetch_usaspending_data(
        agency_codes=['075'],  # HHS
        award_types=['04', '05'],  # Project Grant, Cooperative Agreement
        limit=10
    )
    
    print(f"HHS Results: {len(hhs_data)} awards found")
    universities_hhs = []
    for award in hhs_data:
        recipient = award.get('Recipient Name', '')
        if any(word in recipient.upper() for word in ['UNIVERSITY', 'COLLEGE', 'INSTITUTE']):
            universities_hhs.append(award)
    
    print(f"Universities in HHS data: {len(universities_hhs)}")
    for i, award in enumerate(universities_hhs[:3]):
        print(f"  {i+1}. {award.get('Recipient Name', 'N/A')}: ${award.get('Award Amount', 0):,}")
        sub_agency = award.get('Awarding Sub Agency', '')
        if 'NIH' in sub_agency or 'National Institute' in sub_agency:
            print(f"      → NIH Grant!")
    
    print()
    
    # Test aggregation by recipient
    print("3. Testing funding aggregation...")
    all_awards = nsf_data + hhs_data
    
    funding_by_institution = {}
    for award in all_awards:
        recipient = award.get('Recipient Name', '')
        amount = award.get('Award Amount', 0)
        
        if recipient:
            if recipient not in funding_by_institution:
                funding_by_institution[recipient] = {
                    'total_usaspending': 0,
                    'awards_count': 0,
                    'agencies': set()
                }
            
            funding_by_institution[recipient]['total_usaspending'] += amount
            funding_by_institution[recipient]['awards_count'] += 1
            funding_by_institution[recipient]['agencies'].add(award.get('Awarding Agency', ''))
    
    # Sort by funding amount
    sorted_institutions = sorted(
        funding_by_institution.items(),
        key=lambda x: x[1]['total_usaspending'],
        reverse=True
    )
    
    print("Top institutions by USASpending funding:")
    for i, (institution, data) in enumerate(sorted_institutions[:5]):
        agencies_str = ', '.join(data['agencies'])
        print(f"  {i+1}. {institution}")
        print(f"      Total: ${data['total_usaspending']:,}")
        print(f"      Awards: {data['awards_count']}")
        print(f"      Agencies: {agencies_str}")
        print()

if __name__ == "__main__":
    asyncio.run(test_corrected_integration())
