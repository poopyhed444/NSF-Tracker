#!/usr/bin/env python3
"""
Simple test to understand the grant cache structure
"""
from grant_cache import get_combined_cache
import json

def simple_test():
    print("🔍 Debugging Grant Cache Structure")
    print("=" * 50)
    
    # Get grants
    grants = get_combined_cache()
    print(f"Type of grants: {type(grants)}")
    
    if grants is None:
        print("❌ No grants returned (cache empty or invalid)")
        return
    
    print(f"Length: {len(grants)}")
    
    if len(grants) > 0:
        first_grant = grants[0]
        print(f"Type of first grant: {type(first_grant)}")
        print(f"First grant structure:")
        print(json.dumps(first_grant, indent=2)[:1000])
        
        # Test accessing organization
        if isinstance(first_grant, dict):
            org = first_grant.get('organization', {})
            print(f"\nOrganization type: {type(org)}")
            if isinstance(org, dict):
                org_name = org.get('org_name', 'Unknown')
                print(f"Organization name: {org_name}")
            else:
                print(f"Organization value: {org}")
        
        # Try to find any Harvard-related grant
        print(f"\n🔍 Searching for Harvard in {len(grants)} grants...")
        
        harvard_count = 0
        for i, grant in enumerate(grants[:100]):  # Check first 100
            if isinstance(grant, dict) and 'organization' in grant:
                org = grant['organization']
                if isinstance(org, dict) and 'org_name' in org:
                    org_name = org['org_name'].lower()
                    if 'harvard' in org_name:
                        harvard_count += 1
                        if harvard_count <= 3:
                            print(f"  Found: {grant['organization']['org_name']}")
        
        print(f"Total Harvard grants found in first 100: {harvard_count}")

if __name__ == "__main__":
    simple_test()
