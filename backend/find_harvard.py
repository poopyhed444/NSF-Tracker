#!/usr/bin/env python3
from grant_cache import get_combined_cache

grants = get_combined_cache()
harvard_grants = [g for g in grants if 'harvard' in g.get('organization', {}).get('org_name', '').lower()]
print(f'Found {len(harvard_grants)} Harvard grants')

if harvard_grants:
    for i, g in enumerate(harvard_grants[:3]):
        print(f'  {i+1}. {g["organization"]["org_name"]}')
else:
    print("No Harvard grants found, searching for alternative names...")
    
    # Try other variations
    test_names = ['harvard', 'brigham', 'children', 'dana-farber']
    for name in test_names:
        matches = [g for g in grants if name in g.get('organization', {}).get('org_name', '').lower()]
        if matches:
            print(f'Found {len(matches)} grants for "{name}":')
            for g in matches[:2]:
                print(f'  - {g["organization"]["org_name"]}')
