#!/usr/bin/env python3
"""
Test the funding separation for a specific institution to demonstrate the functionality.
"""

import asyncio
from layoff_estimator import (
    fetch_institution_grants, 
    fetch_total_funding_grants,
    get_institution_total_funding,
    estimate_institution_impact
)

async def test_university_of_chicago():
    """Test funding separation with University of Chicago as example."""
    
    print("=== University of Chicago Funding Analysis ===\n")
    
    # Test 1: Institution grants (NIH + NSF for detailed analysis)
    print("1. Institution Analysis (NIH + NSF for detailed grant information):")
    institution_grants = await fetch_institution_grants(
        organization="University of Chicago", 
        active_only=True,
        max_records_per_source=25
    )
    
    print(f"   Total grants: {len(institution_grants)}")
    
    # Count and analyze
    agencies = {}
    total_funding = 0
    sample_grants = []
    
    for grant in institution_grants:
        agency = grant.get("funding_agency", "UNKNOWN")
        amount = float(grant.get("award_amount", 0))
        
        agencies[agency] = agencies.get(agency, 0) + 1
        total_funding += amount
        
        if len(sample_grants) < 3:
            sample_grants.append({
                "agency": agency,
                "pi": grant.get("contact_pi_name", "Unknown"),
                "title": grant.get("project_title", "Unknown")[:80] + "...",
                "amount": amount,
                "source": grant.get("source", "Unknown")
            })
    
    print(f"   Agency breakdown: {agencies}")
    print(f"   Total funding: ${total_funding:,.2f}")
    print(f"   Data sources: High-quality NIH Reporter API + NSF Awards API")
    print(f"   Sample grants:")
    for grant in sample_grants:
        print(f"     - {grant['agency']}: {grant['pi']} - ${grant['amount']:,.0f}")
        print(f"       {grant['title']}")
    print()
    
    # Test 2: Total funding (all agencies via USASpending.gov)
    print("2. Total Funding Analysis (All agencies via USASpending.gov):")
    total_funding_summary = await get_institution_total_funding("University of Chicago")
    
    if 'error' not in total_funding_summary:
        print(f"   Institution: {total_funding_summary['institution']}")
        print(f"   Total funding: ${total_funding_summary['total_funding']:,.2f}")
        print(f"   Total grants: {total_funding_summary['total_grants']}")
        print(f"   Data source: {total_funding_summary['data_source']}")
        
        print(f"   Agency breakdown:")
        for agency, data in total_funding_summary.get('agency_breakdown', {}).items():
            print(f"     {agency}: ${data['total_amount']:,.2f} ({data['percentage']}%) - {data['grant_count']} grants")
    else:
        print(f"   Error: {total_funding_summary['error']}")
    print()
    
    # Test 3: Full institution impact analysis
    print("3. Full Institution Impact Analysis:")
    try:
        impact_analysis = await estimate_institution_impact("University of Chicago")
        
        if 'error' not in impact_analysis:
            print(f"   Institution: {impact_analysis['institution']}")
            
            # Show detailed vs total funding
            detailed = impact_analysis['funding_breakdown']['detailed_analysis']
            total_funding_data = impact_analysis['funding_breakdown']['total_funding']
            
            print(f"   Detailed Analysis (for institution analysis):")
            print(f"     NIH + NSF funding: ${detailed['nih_nsf_funding']:,.2f}")
            print(f"     NIH grants: {detailed['nih_grant_count']}, NSF grants: {detailed['nsf_grant_count']}")
            print(f"     Data source: {detailed['data_source']}")
            
            print(f"   Total Funding (for funding resources):")
            print(f"     All agencies: ${total_funding_data.get('total_funding', 0):,.2f}")
            print(f"     Total grants: {total_funding_data.get('total_grants', 0)}")
            print(f"     Data source: {total_funding_data.get('data_source', 'N/A')}")
            
            # Show methodology
            methodology = impact_analysis['methodology']
            print(f"   Methodology:")
            sources = methodology['data_sources']
            print(f"     Institution analysis: {sources['institution_analysis']}")
            print(f"     Total funding: {sources['total_funding']}")
            
        else:
            print(f"   Error: {impact_analysis['error']}")
            
    except Exception as e:
        print(f"   Error in analysis: {e}")
    
    print("\n=== Analysis Complete ===")
    print("\nSUMMARY:")
    print("✅ Institution analysis uses NIH + NSF APIs for detailed grant information")
    print("✅ Total funding calculations use USASpending.gov for comprehensive accuracy")
    print("✅ Different data sources optimized for different use cases")

if __name__ == "__main__":
    asyncio.run(test_university_of_chicago())
