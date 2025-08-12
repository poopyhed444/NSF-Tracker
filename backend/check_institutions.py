#!/usr/bin/env python3
from grant_cache import get_combined_cache

grants = get_combined_cache()
print(f"Total grants: {len(grants)}")
print("\nInstitution field names in first 5 grants:")
for i, grant in enumerate(grants[:5]):
    print(f"Grant {i+1}:")
    for key in grant.keys():
        if 'institution' in key.lower() or 'organization' in key.lower() or 'recipient' in key.lower():
            print(f"  {key}: {grant[key]}")
    print()
