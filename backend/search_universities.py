#!/usr/bin/env python3
"""
Search for major universities in the grant cache
"""
from grant_cache import get_combined_cache

def search_universities():
    grants = get_combined_cache()
    if not grants:
        print("No grants found")
        return
    
    # Search for major universities
    universities_to_find = [
        'harvard', 'mit', 'stanford', 'ucla', 'university of california',
        'johns hopkins', 'duke', 'yale', 'princeton', 'columbia'
    ]
    
    found_universities = {}
    
    for grant in grants:
        if isinstance(grant, dict) and 'organization' in grant:
            org = grant['organization']
            if isinstance(org, dict) and 'org_name' in org:
                org_name = org['org_name'].lower()
                
                for search_term in universities_to_find:
                    if search_term in org_name:
                        if search_term not in found_universities:
                            found_universities[search_term] = []
                        if len(found_universities[search_term]) < 3:  # Keep only first 3 examples
                            found_universities[search_term].append(org['org_name'])
    
    print(f"🏛️ Universities found in {len(grants)} grants:")
    for term, examples in found_universities.items():
        print(f"\n'{term}': {len(examples)} examples found")
        for example in examples:
            print(f"  - {example}")
    
    if not found_universities:
        print("❌ No major universities found. Showing first 10 organization names:")
        for i, grant in enumerate(grants[:10]):
            if isinstance(grant, dict) and 'organization' in grant:
                org = grant['organization']
                if isinstance(org, dict) and 'org_name' in org:
                    print(f"  {i+1}. {org['org_name']}")

if __name__ == "__main__":
    search_universities()
