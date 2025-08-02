#!/usr/bin/env python3
"""
Test script to verify the separation of funding data sources.
Tests the new fetch_institution_grants() and fetch_total_funding_grants() functions.
"""

import asyncio
from layoff_estimator import (
    fetch_institution_grants, 
    fetch_total_funding_grants,
    get_institution_total_funding,
    estimate_institution_impact
)

async def test_funding_separation():
    """Test the new funding data separation."""
    
    print("=== Testing Funding Data Separation ===\n")
    
    # Test 1: Institution grants (NIH + NSF only)
    print("1. Testing fetch_institution_grants() - NIH + NSF only:")
    institution_grants = await fetch_institution_grants(
        organization="University of Chicago", 
        max_records_per_source=50
    )
    
    print(f"   Total institution grants: {len(institution_grants)}")
    nih_count = len([g for g in institution_grants if g.get("funding_agency") == "NIH"])
    nsf_count = len([g for g in institution_grants if g.get("funding_agency") == "NSF"])
    other_count = len([g for g in institution_grants if g.get("funding_agency") not in ["NIH", "NSF"]])
    
    print(f"   NIH grants: {nih_count}")
    print(f"   NSF grants: {nsf_count}")
    print(f"   Other agencies: {other_count} (should be 0)")
    
    if institution_grants:
        sample = institution_grants[0]
        print(f"   Sample grant agency: {sample.get('funding_agency')}")
        print(f"   Sample grant source: {sample.get('source')}")
        print(f"   Sample PI: {sample.get('contact_pi_name', 'N/A')}")
    print()
    
    # Test 2: Total funding grants (all agencies via USASpending.gov)
    print("2. Testing fetch_total_funding_grants() - All agencies via USASpending.gov:")
    total_funding_grants = await fetch_total_funding_grants(
        organization="University of Chicago",
        max_records_per_source=100
    )
    
    print(f"   Total funding grants: {len(total_funding_grants)}")
    
    agency_counts = {}
    for grant in total_funding_grants:
        agency = grant.get("funding_agency", "UNKNOWN")
        agency_counts[agency] = agency_counts.get(agency, 0) + 1
    
    for agency, count in sorted(agency_counts.items()):
        print(f"   {agency}: {count} grants")
    
    if total_funding_grants:
        sample = total_funding_grants[0]
        print(f"   Sample grant source: {sample.get('source')}")
        print(f"   Sample funding amount: ${sample.get('award_amount', 0):,.2f}")
    print()
    
    # Test 3: Institution total funding summary
    print("3. Testing get_institution_total_funding() - Summary data:")
    funding_summary = await get_institution_total_funding("University of Chicago")
    
    print(f"   Institution: {funding_summary.get('institution')}")
    print(f"   Total funding: ${funding_summary.get('total_funding', 0):,.2f}")
    print(f"   Total grants: {funding_summary.get('total_grants', 0)}")
    print(f"   Data source: {funding_summary.get('data_source')}")
    
    agency_breakdown = funding_summary.get('agency_breakdown', {})
    print("   Agency breakdown:")
    for agency, data in agency_breakdown.items():
        print(f"     {agency}: ${data['total_amount']:,.2f} ({data['percentage']}%) - {data['grant_count']} grants")
    print()
    
    # Test 4: Full institution impact analysis
    print("4. Testing estimate_institution_impact() - Full analysis:")
    impact_analysis = await estimate_institution_impact("University of Chicago")
    
    if 'error' not in impact_analysis:
        print(f"   Institution: {impact_analysis['institution']}")
        
        # Detailed analysis (NIH + NSF)
        detailed = impact_analysis['funding_breakdown']['detailed_analysis']
        print(f"   Detailed Analysis (NIH + NSF):")
        print(f"     NIH + NSF funding: ${detailed['nih_nsf_funding']:,.2f}")
        print(f"     NIH grants: {detailed['nih_grant_count']}")
        print(f"     NSF grants: {detailed['nsf_grant_count']}")
        print(f"     Data source: {detailed['data_source']}")
        
        # Total funding (USASpending.gov)
        total_funding = impact_analysis['funding_breakdown']['total_funding']
        print(f"   Total Funding (All Agencies):")
        print(f"     Total funding: ${total_funding.get('total_funding', 0):,.2f}")
        print(f"     Total grants: {total_funding.get('total_grants', 0)}")
        print(f"     Data source: {total_funding.get('data_source')}")
        
        # Methodology
        methodology = impact_analysis['methodology']
        print(f"   Data Sources:")
        sources = methodology['data_sources']
        print(f"     Institution analysis: {sources['institution_analysis']}")
        print(f"     Total funding: {sources['total_funding']}")
        print(f"     Note: {sources['note']}")
        
    else:
        print(f"   Error: {impact_analysis['error']}")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    asyncio.run(test_funding_separation())
