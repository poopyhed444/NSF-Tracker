#!/usr/bin/env python3
"""
Test script to debug institution name normalization
"""

import sys
import os
sys.path.append('c:/Users/xinpe/Downloads/NSF-Tracker/backend')

from layoff_estimator import normalize_institution_name

def test_normalization():
    """Test various institution name formats"""
    
    test_cases = [
        # NIH format (all caps)
        "MASSACHUSETTS INSTITUTE OF TECHNOLOGY",
        "STANFORD UNIVERSITY", 
        "UNIVERSITY OF CALIFORNIA, SAN DIEGO",
        "UNIVERSITY OF MICHIGAN",
        "CARNEGIE MELLON UNIVERSITY",
        
        # DoD/DoE format (title case)  
        "Massachusetts Institute of Technology",
        "Stanford University",
        "University of California, San Diego", 
        "University of Michigan",
        "Carnegie Mellon University",
        
        # Mixed case
        "Massachusetts Institute Of Technology",
        "stanford university",
        "STANFORD UNIVERSITY",
        
        # Variations
        "MIT",
        "Stanford",
        "UC San Diego",
        "UCSD",
        "Carnegie Mellon",
        "CMU"
    ]
    
    print("=== INSTITUTION NAME NORMALIZATION TEST ===\n")
    
    normalized_groups = {}
    
    for name in test_cases:
        normalized = normalize_institution_name(name)
        print(f"'{name}' -> '{normalized}'")
        
        if normalized not in normalized_groups:
            normalized_groups[normalized] = []
        normalized_groups[normalized].append(name)
    
    print("\n=== GROUPING RESULTS ===\n")
    
    for normalized_name, original_names in normalized_groups.items():
        if len(original_names) > 1:
            print(f"✓ MATCHED GROUP: '{normalized_name}'")
            for orig in original_names:
                print(f"  - '{orig}'")
            print()
        else:
            print(f"✗ SINGLE: '{normalized_name}' <- '{original_names[0]}'")
    
    print("=== EXPECTED MATCHES ===")
    print("MIT variations should all normalize to the same name")
    print("Stanford variations should all normalize to the same name") 
    print("UC San Diego variations should all normalize to the same name")

if __name__ == "__main__":
    test_normalization()
