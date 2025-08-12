#!/usr/bin/env python3
"""
Find the problematic element in the list
"""

def find_problem():
    from grant_cache import get_combined_cache
    
    fresh_grants = get_combined_cache()
    print(f"Checking all {len(fresh_grants)} elements for type issues...")
    
    non_dict_count = 0
    for i, g in enumerate(fresh_grants):
        if not isinstance(g, dict):
            non_dict_count += 1
            print(f"❌ Element {i}: type={type(g)}, value={g}")
            if non_dict_count >= 5:  # Only show first 5
                break
    
    if non_dict_count == 0:
        print("✅ All elements are dictionaries")
        
        # Try a safer list comprehension
        print("Testing safer approach...")
        result = []
        error_count = 0
        for i, g in enumerate(fresh_grants):
            try:
                if isinstance(g, dict) and 'organization' in g:
                    org = g.get('organization', {})
                    if isinstance(org, dict) and 'org_name' in org:
                        org_name = org['org_name'].lower()
                        if 'harvard' in org_name:
                            result.append(g)
            except Exception as e:
                error_count += 1
                if error_count <= 3:
                    print(f"❌ Error at element {i}: {e}")
                    print(f"   Element: {g}")
        
        print(f"✅ Safer approach found {len(result)} Harvard grants")
    else:
        print(f"❌ Found {non_dict_count} non-dictionary elements")

if __name__ == "__main__":
    find_problem()
