"""
Grant Data Caching Module

This module provides caching functionality for grant data from NIH and NSF APIs
to improve performance and reduce API calls.
"""

import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import hashlib

# Cache configuration
CACHE_DIR = "grant_cache"
CACHE_DURATION_HOURS = 6  # Cache expires after 6 hours
NIH_CACHE_FILE = "nih_grants.json"
NSF_CACHE_FILE = "nsf_grants.json"
COMBINED_CACHE_FILE = "combined_grants.json"

def _ensure_cache_dir():
    """Ensure the cache directory exists."""
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)

def _get_cache_path(cache_file: str) -> str:
    """Get the full path to a cache file."""
    return os.path.join(CACHE_DIR, cache_file)

def _is_cache_valid(cache_file: str) -> bool:
    """Check if a cache file exists and is still valid (not expired)."""
    cache_path = _get_cache_path(cache_file)
    
    if not os.path.exists(cache_path):
        return False
    
    # Check file modification time
    mod_time = datetime.fromtimestamp(os.path.getmtime(cache_path))
    expiry_time = mod_time + timedelta(hours=CACHE_DURATION_HOURS)
    
    return datetime.now() < expiry_time

def _save_to_cache(data: List[Dict[str, Any]], cache_file: str, metadata: Dict[str, Any] = None):
    """Save data to cache file with metadata."""
    _ensure_cache_dir()
    cache_path = _get_cache_path(cache_file)
    
    cache_data = {
        "metadata": {
            "cached_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(hours=CACHE_DURATION_HOURS)).isoformat(),
            "record_count": len(data),
            **(metadata or {})
        },
        "data": data
    }
    
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(cache_data, f, indent=2, default=str)
    
    print(f"Cached {len(data)} records to {cache_file}")

def _load_from_cache(cache_file: str) -> Optional[List[Dict[str, Any]]]:
    """Load data from cache file if valid."""
    if not _is_cache_valid(cache_file):
        return None
    
    cache_path = _get_cache_path(cache_file)
    
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        
        data = cache_data.get("data", [])
        metadata = cache_data.get("metadata", {})
        
        print(f"Loaded {len(data)} records from cache {cache_file} (cached at {metadata.get('cached_at', 'unknown')})")
        return data
    
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error loading cache {cache_file}: {e}")
        return None

def get_nih_cache() -> Optional[List[Dict[str, Any]]]:
    """Get NIH grants from cache if available and valid."""
    return _load_from_cache(NIH_CACHE_FILE)

def save_nih_cache(data: List[Dict[str, Any]], metadata: Dict[str, Any] = None):
    """Save NIH grants to cache."""
    _save_to_cache(data, NIH_CACHE_FILE, metadata)

def get_nsf_cache() -> Optional[List[Dict[str, Any]]]:
    """Get NSF grants from cache if available and valid."""
    return _load_from_cache(NSF_CACHE_FILE)

def save_nsf_cache(data: List[Dict[str, Any]], metadata: Dict[str, Any] = None):
    """Save NSF grants to cache."""
    _save_to_cache(data, NSF_CACHE_FILE, metadata)

def get_combined_cache() -> Optional[List[Dict[str, Any]]]:
    """Get combined grants from cache if available and valid."""
    return _load_from_cache(COMBINED_CACHE_FILE)

def save_combined_cache(data: List[Dict[str, Any]], metadata: Dict[str, Any] = None):
    """Save combined grants to cache."""
    _save_to_cache(data, COMBINED_CACHE_FILE, metadata)

def clear_cache():
    """Clear all cache files."""
    _ensure_cache_dir()
    cache_files = [NIH_CACHE_FILE, NSF_CACHE_FILE, COMBINED_CACHE_FILE]
    
    for cache_file in cache_files:
        cache_path = _get_cache_path(cache_file)
        if os.path.exists(cache_path):
            os.remove(cache_path)
            print(f"Cleared cache: {cache_file}")

def get_cache_status() -> Dict[str, Any]:
    """Get status of all cache files."""
    status = {}
    cache_files = {
        "nih": NIH_CACHE_FILE,
        "nsf": NSF_CACHE_FILE,
        "combined": COMBINED_CACHE_FILE
    }
    
    for cache_type, cache_file in cache_files.items():
        cache_path = _get_cache_path(cache_file)
        
        if os.path.exists(cache_path):
            mod_time = datetime.fromtimestamp(os.path.getmtime(cache_path))
            expiry_time = mod_time + timedelta(hours=CACHE_DURATION_HOURS)
            is_valid = datetime.now() < expiry_time
            
            # Try to get record count from metadata
            record_count = 0
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                record_count = len(cache_data.get("data", []))
            except:
                pass
            
            status[cache_type] = {
                "exists": True,
                "valid": is_valid,
                "cached_at": mod_time.isoformat(),
                "expires_at": expiry_time.isoformat(),
                "record_count": record_count
            }
        else:
            status[cache_type] = {
                "exists": False,
                "valid": False,
                "cached_at": None,
                "expires_at": None,
                "record_count": 0
            }
    
    return status
