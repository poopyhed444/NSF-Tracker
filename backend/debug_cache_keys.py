#!/usr/bin/env python3
"""
Debug cache key matching issue
"""

def test_cache_key_matching():
    """Test how cache keys are generated and matched"""
    
    # Test PI names from the non-renewal list
    institution_name = "University of Chicago"
    pi_names = [
        "BENSMAIA, SLIMAN",
        "ARORA, RISHI", 
        "LAZAROV, ORLY",
        "MIRMIRA, RAGHAVENDRA G",
        "WHEELER, HEATHER ELIZABETH"
    ]
    
    institution_key = institution_name.lower().strip()
    
    print(f"Institution key: '{institution_key}'")
    print("\nPI cache keys that would be generated:")
    
    for pi_name in pi_names:
        pi_key = f"{institution_key}|{pi_name.lower().strip()}"
        print(f"  '{pi_name}' -> '{pi_key}'")
    
    print("\nTesting URL encoding/decoding:")
    import urllib.parse
    
    for pi_name in pi_names:
        url_encoded = urllib.parse.quote(pi_name)
        url_decoded = urllib.parse.unquote(url_encoded)
        
        pi_key_original = f"{institution_key}|{pi_name.lower().strip()}"
        pi_key_decoded = f"{institution_key}|{url_decoded.lower().strip()}"
        
        print(f"  Original: '{pi_name}'")
        print(f"  URL encoded: '{url_encoded}'")
        print(f"  URL decoded: '{url_decoded}'")
        print(f"  Original key: '{pi_key_original}'")
        print(f"  Decoded key: '{pi_key_decoded}'")
        print(f"  Keys match: {pi_key_original == pi_key_decoded}")
        print()

if __name__ == "__main__":
    test_cache_key_matching()
