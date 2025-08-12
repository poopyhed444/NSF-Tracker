#!/usr/bin/env python3
"""
Debug the exact type and structure issue
"""
from grant_cache import get_combined_cache

def debug_structure():
    print("🔍 Deep Structure Debug")
    print("=" * 30)
    
    grants = get_combined_cache()
    print(f"grants type: {type(grants)}")
    print(f"grants length: {len(grants) if grants else 'None'}")
    
    if grants and len(grants) > 0:
        first_item = grants[0]
        print(f"first_item type: {type(first_item)}")
        print(f"first_item has .get(): {hasattr(first_item, 'get')}")
        
        if hasattr(first_item, 'get'):
            print(f"first_item keys: {list(first_item.keys()) if hasattr(first_item, 'keys') else 'No keys'}")
        else:
            print(f"first_item value: {first_item}")
            print(f"first_item length: {len(first_item) if hasattr(first_item, '__len__') else 'No length'}")
            
            if isinstance(first_item, (list, tuple)) and len(first_item) > 0:
                print(f"first_item[0] type: {type(first_item[0])}")
                print(f"first_item[0] sample: {first_item[0]}")

if __name__ == "__main__":
    debug_structure()
