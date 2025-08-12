#!/usr/bin/env python3
from grant_cache import get_combined_cache
import json

grants = get_combined_cache()
print(f'Type: {type(grants)}')
print(f'Length: {len(grants)}')

if grants:
    print(f'First grant type: {type(grants[0])}')
    print(f'First grant keys: {list(grants[0].keys())}')
    print(f'First grant sample:')
    print(json.dumps(grants[0], indent=2)[:500])
