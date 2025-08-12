"""
Optimized Grant Data Caching Module

This module provides high-performance caching functionality for grant data with:
- Dictionary-based cache structure for O(1) lookups
- Separate cache files by type
- Smart cache invalidation and updates
"""

import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import hashlib

# Cache configuration
CACHE_DIR = "grant_cache"
CACHE_DURATION_HOURS = 6  # Cache expires after 6 hours

# Separate cache files for different types of data
ANALYSIS_CACHE_FILE = "analysis_cache.json"  # For comprehensive analysis results
INSTITUTION_CACHE_FILE = "institution_cache.json"  # For institution-specific data
PI_CACHE_FILE = "pi_cache.json"  # For PI-specific data
GENERAL_CACHE_FILE = "general_cache.json"  # For general/global data

def _ensure_cache_dir():
    """Ensure the cache directory exists."""
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)

def _get_cache_path(cache_file: str) -> str:
    """Get the full path to a cache file."""
    return os.path.join(CACHE_DIR, cache_file)

def _load_cache_dict(cache_file: str) -> Dict[str, Any]:
    """Load cache as a dictionary for fast lookups."""
    cache_path = _get_cache_path(cache_file)
    
    if not os.path.exists(cache_path):
        return {}
    
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
            
        # Check if cache file has expired
        cached_at_str = cache_data.get('metadata', {}).get('cached_at')
        if cached_at_str:
            cached_at = datetime.fromisoformat(cached_at_str)
            expiry_time = cached_at + timedelta(hours=CACHE_DURATION_HOURS)
            
            if datetime.now() > expiry_time:
                print(f"Cache expired: {cache_file}")
                return {}
        
        return cache_data.get('data', {})
        
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        print(f"Error loading cache {cache_file}: {e}")
        return {}

def _save_cache_dict(cache_dict: Dict[str, Any], cache_file: str):
    """Save dictionary cache to file."""
    _ensure_cache_dir()
    cache_path = _get_cache_path(cache_file)
    
    cache_data = {
        "metadata": {
            "cached_at": datetime.now().isoformat(),
            "cache_version": "2.0",
            "total_entries": len(cache_dict)
        },
        "data": cache_dict
    }
    
    try:
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving cache {cache_file}: {e}")

def get_cached_analysis(institution_name: str, method: str = "comprehensive", include_departments: bool = True) -> Optional[Dict[str, Any]]:
    """Get cached comprehensive analysis result with O(1) lookup."""
    cache_key = f"{institution_name}_{method}_{include_departments}"
    cache_dict = _load_cache_dict(ANALYSIS_CACHE_FILE)
    
    cached_result = cache_dict.get(cache_key)
    if cached_result:
        print(f"✅ Cache HIT for analysis: {institution_name}")
        return cached_result
    
    print(f"❌ Cache MISS for analysis: {institution_name}")
    return None

def save_cached_analysis(institution_name: str, analysis_data: Dict[str, Any], method: str = "comprehensive", include_departments: bool = True):
    """Save analysis result to cache with O(1) access."""
    cache_key = f"{institution_name}_{method}_{include_departments}"
    cache_dict = _load_cache_dict(ANALYSIS_CACHE_FILE)
    
    # Add timestamp to the data
    analysis_data['_cached_at'] = datetime.now().isoformat()
    cache_dict[cache_key] = analysis_data
    
    _save_cache_dict(cache_dict, ANALYSIS_CACHE_FILE)
    print(f"💾 Cached analysis: {institution_name}")

def get_cached_institution_data(institution_name: str, data_type: str = "funding") -> Optional[Dict[str, Any]]:
    """Get cached institution-specific data."""
    cache_key = f"{institution_name}_{data_type}"
    cache_dict = _load_cache_dict(INSTITUTION_CACHE_FILE)
    
    cached_result = cache_dict.get(cache_key)
    if cached_result:
        print(f"✅ Cache HIT for institution data: {institution_name}")
        return cached_result
    
    return None

def save_cached_institution_data(institution_name: str, data: Dict[str, Any], data_type: str = "funding"):
    """Save institution-specific data to cache."""
    cache_key = f"{institution_name}_{data_type}"
    cache_dict = _load_cache_dict(INSTITUTION_CACHE_FILE)
    
    data['_cached_at'] = datetime.now().isoformat()
    cache_dict[cache_key] = data
    
    _save_cache_dict(cache_dict, INSTITUTION_CACHE_FILE)
    print(f"💾 Cached institution data: {institution_name}")

def get_cached_pi_data(pi_name: str) -> Optional[Dict[str, Any]]:
    """Get cached PI-specific data."""
    cache_key = pi_name.replace(' ', '_').replace(',', '').replace('.', '')
    cache_dict = _load_cache_dict(PI_CACHE_FILE)
    
    cached_result = cache_dict.get(cache_key)
    if cached_result:
        print(f"✅ Cache HIT for PI data: {pi_name}")
        return cached_result
    
    return None

def save_cached_pi_data(pi_name: str, data: Dict[str, Any]):
    """Save PI-specific data to cache."""
    cache_key = pi_name.replace(' ', '_').replace(',', '').replace('.', '')
    cache_dict = _load_cache_dict(PI_CACHE_FILE)
    
    data['_cached_at'] = datetime.now().isoformat()
    cache_dict[cache_key] = data
    
    _save_cache_dict(cache_dict, PI_CACHE_FILE)
    print(f"💾 Cached PI data: {pi_name}")

def get_cached_general_data(data_key: str) -> Optional[Dict[str, Any]]:
    """Get cached general/global data."""
    cache_dict = _load_cache_dict(GENERAL_CACHE_FILE)
    
    cached_result = cache_dict.get(data_key)
    if cached_result:
        print(f"✅ Cache HIT for general data: {data_key}")
        return cached_result
    
    return None

def save_cached_general_data(data_key: str, data: Dict[str, Any]):
    """Save general/global data to cache."""
    cache_dict = _load_cache_dict(GENERAL_CACHE_FILE)
    
    data['_cached_at'] = datetime.now().isoformat()
    cache_dict[data_key] = data
    
    _save_cache_dict(cache_dict, GENERAL_CACHE_FILE)
    print(f"💾 Cached general data: {data_key}")

def clear_cache(cache_type: str = "all"):
    """Clear specific cache files or all caches."""
    _ensure_cache_dir()
    
    cache_files = []
    if cache_type == "all":
        cache_files = [ANALYSIS_CACHE_FILE, INSTITUTION_CACHE_FILE, PI_CACHE_FILE, GENERAL_CACHE_FILE]
    elif cache_type == "analysis":
        cache_files = [ANALYSIS_CACHE_FILE]
    elif cache_type == "institution":
        cache_files = [INSTITUTION_CACHE_FILE]
    elif cache_type == "pi":
        cache_files = [PI_CACHE_FILE]
    elif cache_type == "general":
        cache_files = [GENERAL_CACHE_FILE]
    
    for cache_file in cache_files:
        cache_path = _get_cache_path(cache_file)
        if os.path.exists(cache_path):
            os.remove(cache_path)
            print(f"🗑️ Cleared cache: {cache_file}")

def get_cache_stats() -> Dict[str, Any]:
    """Get detailed statistics about all cache files."""
    cache_files = {
        "analysis": ANALYSIS_CACHE_FILE,
        "institution": INSTITUTION_CACHE_FILE,
        "pi": PI_CACHE_FILE,
        "general": GENERAL_CACHE_FILE
    }
    
    stats = {}
    total_entries = 0
    
    for cache_type, cache_file in cache_files.items():
        cache_path = _get_cache_path(cache_file)
        
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                
                metadata = cache_data.get('metadata', {})
                data = cache_data.get('data', {})
                
                cached_at_str = metadata.get('cached_at')
                cached_at = datetime.fromisoformat(cached_at_str) if cached_at_str else None
                expiry_time = cached_at + timedelta(hours=CACHE_DURATION_HOURS) if cached_at else None
                is_valid = datetime.now() < expiry_time if expiry_time else False
                
                entry_count = len(data)
                total_entries += entry_count
                
                stats[cache_type] = {
                    "exists": True,
                    "valid": is_valid,
                    "entries": entry_count,
                    "cached_at": cached_at.isoformat() if cached_at else None,
                    "expires_at": expiry_time.isoformat() if expiry_time else None,
                    "file_size_kb": round(os.path.getsize(cache_path) / 1024, 2)
                }
                
            except Exception as e:
                stats[cache_type] = {
                    "exists": True,
                    "valid": False,
                    "entries": 0,
                    "error": str(e)
                }
        else:
            stats[cache_type] = {
                "exists": False,
                "valid": False,
                "entries": 0
            }
    
    stats['summary'] = {
        "total_entries": total_entries,
        "cache_version": "2.0"
    }
    
    return stats

# Backward compatibility functions for existing code
def get_combined_cache() -> Optional[List[Dict[str, Any]]]:
    """Legacy function for backward compatibility - returns empty list to force refresh."""
    print("⚠️ Legacy cache function called - consider upgrading to optimized cache")
    return []

def save_combined_cache(data: List[Dict[str, Any]], metadata: Dict[str, Any] = None):
    """Legacy function for backward compatibility - does nothing."""
    print("⚠️ Legacy cache save called - consider upgrading to optimized cache")
    pass
