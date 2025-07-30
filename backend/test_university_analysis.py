#!/usr/bin/env python3
"""
Test University Analysis

Tests the enhanced university-focused recipient analysis with name normalization
"""

import asyncio
import json
from federal_agency_integrator import FederalAgencyIntegrator

async def test_university_analysis():
    """Test university-focused analysis with multiple agencies"""
    integrator = FederalAgencyIntegrator()
    
    print("🎓 University Research Awards Analysis")
    print("=" * 50)
    
    # Test agencies known to fund universities heavily
    agencies_to_test = [
        ('020', 'National Science Foundation'),
        ('075', 'Department of Health and Human Services (NIH)'),
        ('089', 'Department of Energy'),
    ]
    
    for agency_code, agency_name in agencies_to_test:
        print(f"\n📊 Analyzing {agency_name}...")
        print("-" * 40)
        
        try:
            # Fetch awards for this agency
            awards = await integrator.fetch_usaspending_data(
                agency_codes=[agency_code],
                limit=100
            )
            
            if not awards:
                print(f"❌ No awards found for {agency_name}")
                continue
            
            print(f"✅ Retrieved {len(awards)} total awards")
            
            # Analyze with university focus
            analysis = integrator.analyze_award_recipients(awards)
            
            if 'error' in analysis:
                print(f"❌ Analysis error: {analysis['error']}")
                continue
            
            # Display summary
            summary = analysis['summary']
            print(f"📈 Analysis Summary:")
            print(f"   • Total awards analyzed: {summary['total_awards_analyzed']:,}")
            print(f"   • University awards found: {summary['university_awards_found']:,}")
            print(f"   • Universities (original names): {summary['unique_universities_original']:,}")
            print(f"   • Universities (normalized): {summary['unique_universities_normalized']:,}")
            print(f"   • Name consolidation: {summary['consolidation_ratio']}")
            print(f"   • Total funding to universities: ${summary['total_amount']:,.2f}")
            print(f"   • Average award size: ${summary['average_award_amount']:,.2f}")
            
            # Top universities by total funding
            print(f"\n🏆 Top Universities by Total Funding:")
            top_unis = analysis['top_universities']['by_total_amount_normalized'][:10]
            for i, uni in enumerate(top_unis, 1):
                print(f"   {i:2d}. {uni['display_name']}")
                print(f"       Normalized: {uni['normalized_name']}")
                print(f"       Total: ${uni['total_amount']:,.2f} ({uni['award_count']} awards)")
                print(f"       Average: ${uni['average_award']:,.2f}")
                print(f"       Share: {uni['percentage_of_total']:.1f}%")
                print()
            
            # Geographic distribution
            print(f"🗺️  Top States by University Funding:")
            state_summary = analysis['geographic_distribution']['state_summary'][:8]
            for state_data in state_summary:
                print(f"   • {state_data['state']}: ${state_data['total_amount']:,.0f} "
                      f"({state_data['university_count']} universities, "
                      f"{state_data['award_count']} awards)")
            
            # Name normalization examples
            if analysis.get('name_normalization_examples', {}).get('consolidation_examples'):
                print(f"\n🔄 Name Consolidation Examples:")
                for example in analysis['name_normalization_examples']['consolidation_examples'][:3]:
                    print(f"   Consolidated into: '{example['normalized_name']}'")
                    print(f"   Original names ({example['count_consolidated']}):")
                    for orig_name in example['original_names'][:3]:  # Show first 3
                        print(f"     - {orig_name}")
                    if len(example['original_names']) > 3:
                        print(f"     ... and {len(example['original_names']) - 3} more")
                    print()
        
        except Exception as e:
            print(f"❌ Error analyzing {agency_name}: {str(e)}")
            import traceback
            traceback.print_exc()

async def test_name_normalization():
    """Test the name normalization function"""
    integrator = FederalAgencyIntegrator()
    
    print("\n🔤 Name Normalization Testing")
    print("=" * 40)
    
    test_names = [
        "Massachusetts Institute of Technology",
        "The Regents of the University of California, Berkeley",
        "University of California, Los Angeles",
        "Trustees of Columbia University in the City of New York",
        "The Board of Regents of the University of Texas System",
        "Virginia Polytechnic Institute and State University",
        "Texas A&M University",
        "The President and Fellows of Harvard College",
        "Stanford University",
        "University of Michigan",
        "The Curators of the University of Missouri",
        "Carnegie Mellon University",
        "Washington University in St. Louis"
    ]
    
    print("Original Name → Normalized Name")
    print("-" * 60)
    
    for name in test_names:
        normalized = integrator.normalize_institution_name(name)
        is_research = integrator.is_research_institution(name)
        status = "✅" if is_research else "❌"
        print(f"{status} {name}")
        print(f"    → {normalized}")
        print()

if __name__ == "__main__":
    asyncio.run(test_university_analysis())
    asyncio.run(test_name_normalization())
