#!/usr/bin/env python3

"""
Quick test script to debug cache issues
"""

from pi_department_lookup import _cache, CACHE_FILE
import os
import json

print(f"Cache file path: {CACHE_FILE}")
print(f"Cache file exists: {os.path.exists(CACHE_FILE)}")

# Test setting a value
print("Setting test value...")
_cache.set("Test Person", "Test University", "Test Department", "test", "high")

print("Checking if test value is in memory cache...")
result = _cache.get("Test Person", "Test University")
print(f"In-memory result: {result}")

print("Checking if test value is in file...")
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, 'r', encoding='utf-8') as f:
        file_cache = json.load(f)
    
    test_key = _cache._normalize_name("Test Person") + "|test university"
    print(f"Test key: {test_key}")
    print(f"In file: {test_key in file_cache}")
    
    if test_key in file_cache:
        print(f"File result: {file_cache[test_key]}")
else:
    print("Cache file does not exist!")
