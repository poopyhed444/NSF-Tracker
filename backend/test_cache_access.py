#!/usr/bin/env python3
"""
Test USASpending cache access from the server directory
"""

import os
import sys

print("Current working directory:", os.getcwd())
print("Python path:", sys.path)

# Check if cache file exists
cache_file = os.path.join("grant_cache", "usaspending_university_funding.json")
print(f"Cache file path: {cache_file}")
print(f"Cache file exists: {os.path.exists(cache_file)}")

# Try absolute path
abs_cache_file = os.path.join(os.getcwd(), "grant_cache", "usaspending_university_funding.json")
print(f"Absolute cache file path: {abs_cache_file}")
print(f"Absolute cache file exists: {os.path.exists(abs_cache_file)}")

# List directory contents
if os.path.exists("grant_cache"):
    print("grant_cache directory contents:")
    for file in os.listdir("grant_cache"):
        print(f"  {file}")
else:
    print("grant_cache directory does not exist")

# Test the cache loader
try:
    from usaspending_cache_loader import get_usaspending_stats
    stats = get_usaspending_stats()
    if stats:
        print(f"✅ Cache loaded successfully: {stats['total_grants']:,} grants")
    else:
        print("❌ Cache loader returned None")
except Exception as e:
    print(f"❌ Error loading cache: {e}")
