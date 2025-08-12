#!/usr/bin/env python3
"""
Test the exact same code that's failing
"""

def test_exact_issue():
    from grant_cache import get_combined_cache
    
    fresh_grants = get_combined_cache()
    print(f"Fresh grants type: {type(fresh_grants)}")
    print(f"Fresh grants length: {len(fresh_grants)}")
    
    # Test accessing the first item
    if fresh_grants:
        item = fresh_grants[0]
        print(f"First item type: {type(item)}")
        print(f"First item keys: {list(item.keys()) if hasattr(item, 'keys') else 'No keys'}")
        
        # Try the exact failing line
        try:
            test_result = [g for g in fresh_grants if 'harvard' in g.get('organization', {}).get('org_name', '').lower()]
            print(f"✅ List comprehension worked! Found {len(test_result)} items")
        except Exception as e:
            print(f"❌ List comprehension failed: {e}")
            
            # Debug each element
            print("Checking first 3 elements:")
            for i, g in enumerate(fresh_grants[:3]):
                print(f"  Element {i}: type={type(g)}, has_get={hasattr(g, 'get')}")
                if not hasattr(g, 'get'):
                    print(f"    Value: {g}")

if __name__ == "__main__":
    test_exact_issue()
