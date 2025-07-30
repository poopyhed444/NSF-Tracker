#!/usr/bin/env python3
"""
Test UC System Consolidation

Test how the UC system awards get consolidated under the improved normalization
"""

from federal_agency_integrator import FederalAgencyIntegrator

def test_uc_consolidation():
    integrator = FederalAgencyIntegrator()
    
    # Simulate UC system awards
    test_awards = [
        {
            'Recipient Name': 'THE REGENTS OF THE UNIVERSITY OF CALIFORNIA',
            'Award Amount': 36925788552.84,
            'Recipient City Name': 'Oakland',
            'Recipient State Code': 'CA'
        },
        {
            'Recipient Name': 'REGENTS OF THE UNIVERSITY OF CALIFORNIA, THE', 
            'Award Amount': 35295413219.18,
            'Recipient City Name': 'Oakland',
            'Recipient State Code': 'CA'
        },
        {
            'Recipient Name': 'University of California, Berkeley',
            'Award Amount': 5000000.00,
            'Recipient City Name': 'Berkeley', 
            'Recipient State Code': 'CA'
        },
        {
            'Recipient Name': 'University of California, Los Angeles',
            'Award Amount': 3000000.00,
            'Recipient City Name': 'Los Angeles',
            'Recipient State Code': 'CA'
        },
        {
            'Recipient Name': 'STANFORD UNIVERSITY',
            'Award Amount': 14153481956.51,
            'Recipient City Name': 'Stanford',
            'Recipient State Code': 'CA'
        }
    ]
    
    print("🔬 Testing UC System Consolidation")
    print("=" * 50)
    
    # Test normalization for each name
    print("Name Normalization:")
    for award in test_awards:
        original = award['Recipient Name']
        normalized = integrator.normalize_institution_name(original)
        print(f"  {original}")
        print(f"  → {normalized}")
        print()
    
    # Run full analysis
    print("Full Analysis Results:")
    analysis = integrator.analyze_award_recipients(test_awards)
    
    if 'error' not in analysis:
        summary = analysis['summary']
        print(f"📊 Summary:")
        print(f"   • Total awards: {summary['total_awards_analyzed']}")
        print(f"   • University awards: {summary['university_awards_found']}")
        print(f"   • Original names: {summary['unique_universities_original']}")
        print(f"   • Normalized names: {summary['unique_universities_normalized']}")
        print(f"   • Consolidation: {summary['consolidation_ratio']}")
        
        print(f"\n🏆 Top Universities (Normalized):")
        top_unis = analysis['top_universities']['by_total_amount_normalized']
        for i, uni in enumerate(top_unis, 1):
            print(f"   {i}. {uni['display_name']}")
            print(f"      Normalized: '{uni['normalized_name']}'")
            print(f"      Total: ${uni['total_amount']:,.2f} ({uni['award_count']} awards)")
            print()
        
        # Show consolidation examples
        if analysis.get('name_normalization_examples', {}).get('consolidation_examples'):
            print(f"🔄 Consolidation Examples:")
            for example in analysis['name_normalization_examples']['consolidation_examples']:
                print(f"   Consolidated '{example['normalized_name']}' from {example['count_consolidated']} names:")
                for orig in example['original_names']:
                    print(f"     - {orig}")
                print()

if __name__ == "__main__":
    test_uc_consolidation()
