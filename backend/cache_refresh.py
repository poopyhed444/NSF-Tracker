#!/usr/bin/env python3
"""
Cache management utility for PI department classifications.
This script provides utilities to clear and manage the PI department cache.
"""

import json
import logging
from pathlib import Path
from typing import Dict

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CacheManager:
    def __init__(self, cache_file: Path = Path('pi_department_cache.json')):
        self.cache_file = cache_file
        
    def clear_cache(self) -> bool:
        """Clear the entire cache file."""
        try:
            if self.cache_file.exists():
                self.cache_file.unlink()
                logger.info(f"Cache file {self.cache_file} deleted successfully")
                return True
            else:
                logger.info(f"Cache file {self.cache_file} does not exist")
                return False
        except Exception as e:
            logger.error(f"Error deleting cache file: {e}")
            return False
    
    def get_cache_stats(self) -> Dict:
        """Get statistics about the current cache state."""
        try:
            if not self.cache_file.exists():
                return {"error": "Cache file not found", "total_entries": 0}
            
            with open(self.cache_file, 'r') as f:
                cache = json.load(f)
            
            from collections import Counter
            
            # Calculate statistics
            total_entries = len(cache)
            departments = [entry.get('department', 'Unknown') for entry in cache.values()]
            sources = [entry.get('source', 'unknown') for entry in cache.values()]
            confidences = [entry.get('confidence', 'unknown') for entry in cache.values()]
            
            dept_counts = Counter(departments)
            source_counts = Counter(sources)
            confidence_counts = Counter(confidences)
            
            unknown_count = dept_counts.get('Unknown', 0)
            
            return {
                "total_entries": total_entries,
                "unknown_entries": unknown_count,
                "success_rate": round((total_entries - unknown_count) / total_entries * 100, 1) if total_entries > 0 else 0,
                "department_distribution": dict(dept_counts.most_common(10)),
                "source_distribution": dict(source_counts),
                "confidence_distribution": dict(confidence_counts)
            }
            
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"error": str(e)}

def main():
    """Main function for cache management."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Manage PI department cache')
    parser.add_argument('--clear', action='store_true',
                        help='Clear the entire cache file')
    parser.add_argument('--stats', action='store_true',
                        help='Show cache statistics')
    
    args = parser.parse_args()
    
    manager = CacheManager()
    
    if args.clear:
        success = manager.clear_cache()
        if success:
            print("Cache cleared successfully. New lookups will use the improved classification system.")
        else:
            print("Failed to clear cache or cache was already empty.")
    
    if args.stats:
        stats = manager.get_cache_stats()
        if "error" in stats:
            print(f"Error: {stats['error']}")
        else:
            print(f"\nCache Statistics:")
            print(f"Total entries: {stats['total_entries']}")
            print(f"Unknown entries: {stats['unknown_entries']}")
            print(f"Success rate: {stats['success_rate']}%")
            print(f"\nTop departments:")
            for dept, count in list(stats['department_distribution'].items())[:5]:
                print(f"  {dept}: {count}")
    
    if not args.clear and not args.stats:
        parser.print_help()

if __name__ == '__main__':
    main()
