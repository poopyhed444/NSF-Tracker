#!/usr/bin/env python3
"""
USASpending.gov Cache Loader

This module loads the comprehensive USASpending.gov cache and provides
functions to integrate it with the existing funding system.
"""

import json
import os
from typing import Dict, List, Any, Optional
from collections import defaultdict

class USASpendingCacheLoader:
    def __init__(self):
        # Use absolute path to ensure we find the cache file regardless of CWD
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        self.cache_file = os.path.join(backend_dir, "grant_cache", "usaspending_university_funding.json")
        self._cache_data = None
        
    def load_cache(self) -> Optional[Dict[str, Any]]:
        """Load the USASpending cache data"""
        if self._cache_data is not None:
            return self._cache_data
            
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    self._cache_data = json.load(f)
                    print(f"✅ Loaded USASpending cache: {self._cache_data['metadata']['total_grants']:,} grants")
                    return self._cache_data
            else:
                print(f"❌ USASpending cache not found: {self.cache_file}")
                return None
        except Exception as e:
            print(f"❌ Error loading USASpending cache: {e}")
            return None
    
    def get_institution_funding(self, institution_name: str) -> Dict[str, Any]:
        """Get comprehensive funding data for a specific institution"""
        cache_data = self.load_cache()
        if not cache_data:
            return {
                'total_usaspending_funding': 0,
                'nih_funding': 0,
                'nsf_funding': 0,
                'dod_funding': 0,
                'doe_funding': 0,
                'nasa_funding': 0,
                'other_funding': 0,
                'grants_count': 0,
                'agencies': []
            }
        
        # Normalize institution name for lookup
        normalized_name = self._normalize_institution_name(institution_name)
        
        # Search in institution aggregations
        institution_aggregations = cache_data.get('institution_aggregations', {})
        
        # Try exact match first
        if normalized_name in institution_aggregations:
            funding_data = institution_aggregations[normalized_name]
            return {
                'total_usaspending_funding': funding_data.get('total_funding', 0),
                'nih_funding': funding_data.get('nih_funding', 0),
                'nsf_funding': funding_data.get('nsf_funding', 0),
                'dod_funding': funding_data.get('dod_funding', 0),
                'doe_funding': funding_data.get('doe_funding', 0),
                'nasa_funding': funding_data.get('nasa_funding', 0),
                'other_funding': funding_data.get('other_funding', 0),
                'grants_count': funding_data.get('grants_count', 0),
                'agencies': funding_data.get('agencies', [])
            }
        
        # Try partial matching
        for inst_name, funding_data in institution_aggregations.items():
            if self._institutions_match(normalized_name, inst_name):
                return {
                    'total_usaspending_funding': funding_data.get('total_funding', 0),
                    'nih_funding': funding_data.get('nih_funding', 0),
                    'nsf_funding': funding_data.get('nsf_funding', 0),
                    'dod_funding': funding_data.get('dod_funding', 0),
                    'doe_funding': funding_data.get('doe_funding', 0),
                    'nasa_funding': funding_data.get('nasa_funding', 0),
                    'other_funding': funding_data.get('other_funding', 0),
                    'grants_count': funding_data.get('grants_count', 0),
                    'agencies': funding_data.get('agencies', [])
                }
        
        # No match found
        return {
            'total_usaspending_funding': 0,
            'nih_funding': 0,
            'nsf_funding': 0,
            'dod_funding': 0,
            'doe_funding': 0,
            'nasa_funding': 0,
            'other_funding': 0,
            'grants_count': 0,
            'agencies': []
        }
    
    def _normalize_institution_name(self, name: str) -> str:
        """Normalize institution name for matching"""
        if not name:
            return ""
        
        # Basic normalization
        normalized = name.upper().strip()
        
        # Common replacements
        replacements = {
            'UNIVERSITY OF CALIFORNIA,': 'UNIVERSITY OF CALIFORNIA',
            'THE REGENTS OF THE UNIVERSITY OF CALIFORNIA': 'UNIVERSITY OF CALIFORNIA',
            'REGENTS OF THE UNIVERSITY OF CALIFORNIA': 'UNIVERSITY OF CALIFORNIA',
            'THE TRUSTEES OF': '',
            'TRUSTEES OF': '',
            'THE BOARD OF TRUSTEES OF': '',
            'BOARD OF TRUSTEES OF': '',
            'THE UNIVERSITY OF': 'UNIVERSITY OF',
            ', THE': '',
            ' THE': '',
            '  ': ' '
        }
        
        for old, new in replacements.items():
            normalized = normalized.replace(old, new)
        
        return normalized.strip()
    
    def _institutions_match(self, name1: str, name2: str) -> bool:
        """Check if two institution names likely refer to the same institution"""
        name1 = self._normalize_institution_name(name1)
        name2 = self._normalize_institution_name(name2)
        
        # Exact match
        if name1 == name2:
            return True
        
        # Extract key words (remove common words)
        common_words = {'OF', 'THE', 'AND', 'FOR', 'IN', 'AT', 'ON', 'WITH', 'BY'}
        
        words1 = set(name1.split()) - common_words
        words2 = set(name2.split()) - common_words
        
        # Check if most significant words match
        if len(words1) >= 2 and len(words2) >= 2:
            intersection = words1.intersection(words2)
            if len(intersection) >= min(2, min(len(words1), len(words2))):
                return True
        
        return False
    
    def get_top_institutions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get top institutions by total USASpending funding"""
        cache_data = self.load_cache()
        if not cache_data:
            return []
        
        institution_aggregations = cache_data.get('institution_aggregations', {})
        
        # Sort by total funding
        sorted_institutions = sorted(
            institution_aggregations.items(),
            key=lambda x: x[1].get('total_funding', 0),
            reverse=True
        )
        
        result = []
        for institution, funding_data in sorted_institutions[:limit]:
            result.append({
                'institution': institution,
                'total_usaspending_funding': funding_data.get('total_funding', 0),
                'nih_funding': funding_data.get('nih_funding', 0),
                'nsf_funding': funding_data.get('nsf_funding', 0),
                'dod_funding': funding_data.get('dod_funding', 0),
                'doe_funding': funding_data.get('doe_funding', 0),
                'nasa_funding': funding_data.get('nasa_funding', 0),
                'other_funding': funding_data.get('other_funding', 0),
                'grants_count': funding_data.get('grants_count', 0),
                'agencies': funding_data.get('agencies', [])
            })
        
        return result
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the cached data"""
        cache_data = self.load_cache()
        if not cache_data:
            return {}
        
        metadata = cache_data.get('metadata', {})
        agency_stats = cache_data.get('agency_statistics', {})
        
        return {
            'cache_created': metadata.get('created_at'),
            'total_grants': metadata.get('total_grants', 0),
            'total_institutions': metadata.get('total_institutions', 0),
            'total_funding': metadata.get('total_funding', 0),
            'agency_breakdown': {
                agency: {
                    'grants': stats.get('grants_count', 0),
                    'funding': stats.get('total_funding', 0)
                }
                for agency, stats in agency_stats.items()
            }
        }

# Global cache loader instance
_cache_loader = USASpendingCacheLoader()

def get_usaspending_funding(institution_name: str) -> Dict[str, Any]:
    """
    Get USASpending.gov funding data for an institution
    
    This function integrates with the cached USASpending.gov data to provide
    real funding amounts instead of $0 values.
    """
    return _cache_loader.get_institution_funding(institution_name)

def get_usaspending_stats() -> Dict[str, Any]:
    """Get USASpending.gov cache statistics"""
    return _cache_loader.get_cache_stats()

def get_top_funded_institutions(limit: int = 20) -> List[Dict[str, Any]]:
    """Get top institutions by USASpending.gov funding"""
    return _cache_loader.get_top_institutions(limit)

# Test function
def test_cache_integration():
    """Test the cache integration"""
    print("=== Testing USASpending Cache Integration ===")
    
    # Test stats
    stats = get_usaspending_stats()
    if stats:
        print(f"Cache loaded: {stats['total_grants']:,} grants, ${stats['total_funding']:,.0f}")
    
    # Test specific institutions
    test_institutions = [
        "University of California, Los Angeles",
        "Duke University",
        "Johns Hopkins University",
        "Stanford University",
        "Massachusetts Institute of Technology"
    ]
    
    print("\nTesting institution lookups:")
    for institution in test_institutions:
        funding = get_usaspending_funding(institution)
        if funding['total_usaspending_funding'] > 0:
            print(f"✅ {institution}: ${funding['total_usaspending_funding']:,.0f}")
            print(f"   NIH: ${funding['nih_funding']:,.0f}, NSF: ${funding['nsf_funding']:,.0f}")
        else:
            print(f"❌ {institution}: No funding found")
    
    # Test top institutions
    print(f"\nTop 5 funded institutions:")
    top_institutions = get_top_funded_institutions(5)
    for i, inst in enumerate(top_institutions):
        print(f"{i+1}. {inst['institution']}: ${inst['total_usaspending_funding']:,.0f}")

if __name__ == "__main__":
    test_cache_integration()
