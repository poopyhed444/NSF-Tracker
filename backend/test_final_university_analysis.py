#!/usr/bin/env python3
"""
University-Focused Federal Awards Analysis

Comprehensive test of the enhanced university-only analysis with improved name normalization
"""

import asyncio
from federal_agency_integrator import FederalAgencyIntegrator

async def main():
    integrator = FederalAgencyIntegrator()
    
    print("🎓 University-Focused Federal Awards Analysis")
    print("=" * 60)
    print("This analysis focuses exclusively on research institutions (universities)")
    print("and includes advanced name normalization for better consolidation.")
    print()
    
    # Test with multiple agencies that fund universities
    agencies_to_test = [
        ('020', 'National Science Foundation'),
        ('089', 'Department of Energy'),
        ('080', 'National Aeronautics and Space Administration'),
    ]
    
    all_university_awards = []
    
    for agency_code, agency_name in agencies_to_test:
        print(f"📊 {agency_name}")
        print("-" * 50)
        
        try:
            # Fetch awards
            awards = await integrator.fetch_usaspending_data(
                agency_codes=[agency_code],
                limit=100
            )
            
            if not awards:
                print(f"❌ No awards found")
                continue
            
            # Filter to universities only
            university_awards = integrator.filter_university_awards(awards)
            all_university_awards.extend(university_awards)
            
            print(f"✅ Total awards: {len(awards)}")
            print(f"🏛️  University awards: {len(university_awards)}")
            print(f"📈 University percentage: {len(university_awards)/len(awards)*100:.1f}%")
            
            if university_awards:
                total_amount = sum(award.get('Award Amount', 0) or 0 for award in university_awards)
                print(f"💰 Total university funding: ${total_amount:,.2f}")
                
                # Show top 3 universities for this agency
                analysis = integrator.analyze_award_recipients(university_awards)
                if 'error' not in analysis:
                    top_unis = analysis['top_universities']['by_total_amount_normalized'][:3]
                    print(f"🏆 Top universities:")
                    for i, uni in enumerate(top_unis, 1):
                        print(f"   {i}. {uni['display_name']} - ${uni['total_amount']:,.0f}")
            
            print()
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            print()
    
    # Overall analysis
    if all_university_awards:
        print("🌟 COMPREHENSIVE UNIVERSITY ANALYSIS")
        print("=" * 60)
        
        analysis = integrator.analyze_award_recipients(all_university_awards)
        
        if 'error' not in analysis:
            summary = analysis['summary']
            print(f"📊 Overall Summary:")
            print(f"   • Total university awards analyzed: {summary['university_awards_found']:,}")
            print(f"   • Unique universities (original names): {summary['unique_universities_original']:,}")
            print(f"   • Unique universities (after normalization): {summary['unique_universities_normalized']:,}")
            print(f"   • Name consolidation efficiency: {summary['consolidation_ratio']}")
            print(f"   • Total funding to universities: ${summary['total_amount']:,.2f}")
            print(f"   • Average award size: ${summary['average_award_amount']:,.2f}")
            print()
            
            print(f"🏆 Top 10 Universities (Multi-Agency):")
            top_unis = analysis['top_universities']['by_total_amount_normalized'][:10]
            for i, uni in enumerate(top_unis, 1):
                print(f"   {i:2d}. {uni['display_name']}")
                print(f"       Normalized: '{uni['normalized_name']}'")
                print(f"       Awards: {uni['award_count']}, Total: ${uni['total_amount']:,.2f}")
                print(f"       Average: ${uni['average_award']:,.2f}, Share: {uni['percentage_of_total']:.1f}%")
                print()
            
            # Geographic analysis
            state_summary = analysis['geographic_distribution']['state_summary'][:8]
            if state_summary:
                print(f"🗺️  Geographic Distribution (Top States):")
                for state_data in state_summary:
                    print(f"   • {state_data['state']}: {state_data['university_count']} universities, "
                          f"${state_data['total_amount']:,.0f} total")
                print()
            
            # Show name consolidation examples
            consolidation_examples = analysis.get('name_normalization_examples', {}).get('consolidation_examples', [])
            if consolidation_examples:
                print(f"🔄 Name Consolidation Examples:")
                for example in consolidation_examples[:3]:
                    print(f"   '{example['normalized_name']}' consolidates {example['count_consolidated']} variants:")
                    for orig_name in example['original_names'][:2]:  # Show first 2
                        print(f"     - {orig_name}")
                    if len(example['original_names']) > 2:
                        print(f"     - ... and {len(example['original_names']) - 2} more")
                    print()
        
        print("✅ Analysis complete! The system now:")
        print("   • Filters awards to universities only")
        print("   • Normalizes institution names for better consolidation")
        print("   • Provides detailed breakdowns by funding amount and award count")
        print("   • Shows geographic distribution of university funding")
        print("   • Demonstrates significant improvements in data quality through name normalization")

if __name__ == "__main__":
    asyncio.run(main())
