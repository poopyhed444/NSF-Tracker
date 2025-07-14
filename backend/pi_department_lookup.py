"""
PI Department Lookup Module

This module provides functionality to determine a principal investigator's 
academic department using ORCID API with local caching.
"""

import json
import os
import re
import httpx
import asyncio
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta

# Cache file path
CACHE_FILE = os.path.join(os.path.dirname(__file__), "pi_department_cache.json")
CACHE_EXPIRY_DAYS = 30

class PILookupCache:
    """Handles caching of PI department lookup results."""
    
    def __init__(self):
        self.cache = self._load_cache()
    
    def _load_cache(self) -> Dict:
        """Load cache from JSON file."""
        try:
            if os.path.exists(CACHE_FILE):
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading cache: {e}")
        return {}
    
    def _save_cache(self):
        """Save cache to JSON file."""
        try:
            with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving cache: {e}")
    
    def _is_expired(self, timestamp: str) -> bool:
        """Check if cache entry is expired."""
        try:
            cached_date = datetime.fromisoformat(timestamp)
            expiry_date = cached_date + timedelta(days=CACHE_EXPIRY_DAYS)
            return datetime.now() > expiry_date
        except:
            return True
    
    def get(self, name: str, institution: str) -> Optional[Dict]:
        """Get cached result for PI."""
        key = f"{name.lower()}|{institution.lower()}"
        entry = self.cache.get(key)
        
        if entry and not self._is_expired(entry.get('timestamp', '')):
            return entry
        return None
    
    def set(self, name: str, institution: str, department: str, source: str, confidence: str):
        """Cache PI lookup result."""
        key = f"{name.lower()}|{institution.lower()}"
        self.cache[key] = {
            'department': department,
            'source': source,
            'confidence': confidence,
            'timestamp': datetime.now().isoformat()
        }
        self._save_cache()

class ORCIDLookup:
    """Handles ORCID API lookups."""
    
    ORCID_SEARCH_URL = "https://pub.orcid.org/v3.0/search"
    ORCID_RECORD_URL = "https://pub.orcid.org/v3.0"
    
    @staticmethod
    async def search_orcid(name: str, institution: str) -> Optional[Tuple[str, str]]:
        """
        Search for PI in ORCID and extract department.
        Returns (department, confidence) tuple or None.
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                # Search for the person
                search_query = f'given-names:{name.split()[0]} AND family-name:{name.split()[-1]}'
                if len(name.split()) > 2:
                    # Handle middle names
                    middle_names = ' '.join(name.split()[1:-1])
                    search_query += f' AND other-names:{middle_names}'
                
                headers = {
                    'Accept': 'application/json',
                    'User-Agent': 'NIH-NSF-Tracker/1.0'
                }
                
                params = {
                    'q': search_query,
                    'rows': 20
                }
                
                response = await client.get(ORCIDLookup.ORCID_SEARCH_URL, 
                                          headers=headers, params=params)
                response.raise_for_status()
                search_data = response.json()
                
                for result in search_data.get('result', []):
                    orcid_id = result.get('orcid-identifier', {}).get('path')
                    if not orcid_id:
                        continue
                    
                    # Get detailed record
                    record_url = f"{ORCIDLookup.ORCID_RECORD_URL}/{orcid_id}/record"
                    record_response = await client.get(record_url, headers=headers)
                    record_response.raise_for_status()
                    record_data = record_response.json()
                    
                    # Check if institution matches
                    department = ORCIDLookup._extract_department_from_record(
                        record_data, institution)
                    if department:
                        return department, "high"
                
                return None
                
            except Exception as e:
                print(f"ORCID lookup error: {e}")
                return None
    
    @staticmethod
    def _extract_department_from_record(record_data: Dict, target_institution: str) -> Optional[str]:
        """Extract department from ORCID record if institution matches."""
        try:
            activities = record_data.get('activities-summary', {})
            employments = activities.get('employments', {}).get('employment-summary', [])
            
            target_institution_lower = target_institution.lower()
            
            for employment in employments:
                org_name = employment.get('organization', {}).get('name', '').lower()
                dept_name = employment.get('department-name')
                
                # Check if organization matches (fuzzy match)
                if any(word in org_name for word in target_institution_lower.split() if len(word) > 3):
                    if dept_name:
                        return dept_name
                    
                    # Try to extract from role title
                    role_title = employment.get('role-title', '')
                    if role_title:
                        # Look for department keywords in role title
                        dept_keywords = [
                            'department', 'dept', 'school of', 'division of',
                            'center for', 'institute'
                        ]
                        role_lower = role_title.lower()
                        for keyword in dept_keywords:
                            if keyword in role_lower:
                                # Extract text after keyword
                                parts = role_lower.split(keyword)
                                if len(parts) > 1:
                                    potential_dept = parts[1].strip().split(',')[0].strip()
                                    if potential_dept:
                                        return potential_dept.title()
            
            return None
            
        except Exception as e:
            print(f"Error extracting department from ORCID record: {e}")
            return None

class DepartmentNormalizer:
    """Normalizes department names to standard forms."""
    
    DEPARTMENT_MAPPINGS = {
        # Biology variations
        'biology': 'Biology',
        'biological sciences': 'Biology',
        'life sciences': 'Biology',
        'molecular biology': 'Molecular Biology',
        'cell biology': 'Cell Biology',
        'developmental biology': 'Developmental Biology',
        
        # Chemistry variations
        'chemistry': 'Chemistry',
        'biochemistry': 'Biochemistry',
        'chemical biology': 'Chemical Biology',
        
        # Engineering variations
        'engineering': 'Engineering',
        'bioengineering': 'Bioengineering',
        'biomedical engineering': 'Biomedical Engineering',
        'electrical engineering': 'Electrical Engineering',
        'mechanical engineering': 'Mechanical Engineering',
        
        # Medicine variations
        'medicine': 'Medicine',
        'medical school': 'Medicine',
        'school of medicine': 'Medicine',
        'internal medicine': 'Internal Medicine',
        'pediatrics': 'Pediatrics',
        'surgery': 'Surgery',
        
        # Neuroscience variations
        'neuroscience': 'Neuroscience',
        'neurology': 'Neurology',
        'neurobiology': 'Neurobiology',
        
        # Physics variations
        'physics': 'Physics',
        'biophysics': 'Biophysics',
        
        # Computer Science variations
        'computer science': 'Computer Science',
        'computational biology': 'Computational Biology',
        
        # Psychology variations
        'psychology': 'Psychology',
        'cognitive science': 'Cognitive Science',
        
        # Mathematics variations
        'mathematics': 'Mathematics',
        'statistics': 'Statistics',
        'biostatistics': 'Biostatistics',
    }
    
    @staticmethod
    def normalize(department: str) -> str:
        """Normalize department name to standard form."""
        if not department:
            return "Unknown"
        
        dept_lower = department.lower().strip()
        
        # Direct mapping
        if dept_lower in DepartmentNormalizer.DEPARTMENT_MAPPINGS:
            return DepartmentNormalizer.DEPARTMENT_MAPPINGS[dept_lower]
        
        # Partial matching
        for key, value in DepartmentNormalizer.DEPARTMENT_MAPPINGS.items():
            if key in dept_lower or dept_lower in key:
                return value
        
        # Clean up and title case if no mapping found
        return department.strip().title()

# Initialize cache
_cache = PILookupCache()

async def get_pi_department(name: str, institution: str) -> Dict[str, str]:
    """
    Get PI department using ORCID lookup with caching.
    
    Args:
        name: Full name of the PI
        institution: Institution name
    
    Returns:
        Dict with keys: 'department', 'source', 'confidence'
    """
    if not name or not institution:
        return {
            'department': 'Unknown',
            'source': 'none',
            'confidence': 'none'
        }
    
    # Check cache first
    cached_result = _cache.get(name, institution)
    if cached_result:
        return {
            'department': cached_result['department'],
            'source': cached_result['source'],
            'confidence': cached_result['confidence']
        }
    
    # Try ORCID lookup
    try:
        orcid_result = await ORCIDLookup.search_orcid(name, institution)
        if orcid_result:
            department, confidence = orcid_result
            normalized_dept = DepartmentNormalizer.normalize(department)
            
            # Cache result
            _cache.set(name, institution, normalized_dept, 'orcid', confidence)
            
            return {
                'department': normalized_dept,
                'source': 'orcid',
                'confidence': confidence
            }
    except Exception as e:
        print(f"Error in ORCID lookup for {name}: {e}")
    
    # If all lookups fail
    result = {
        'department': 'Unknown',
        'source': 'none',
        'confidence': 'none'
    }
    
    # Cache the unknown result to avoid repeated lookups
    _cache.set(name, institution, 'Unknown', 'none', 'none')
    
    return result

def get_pi_department_sync(name: str, institution: str) -> Dict[str, str]:
    """
    Synchronous wrapper for get_pi_department.
    
    Args:
        name: Full name of the PI
        institution: Institution name
    
    Returns:
        Dict with keys: 'department', 'source', 'confidence'
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're already in an async context, we can't use run()
            # Return cached result or Unknown
            cached_result = _cache.get(name, institution)
            if cached_result:
                return {
                    'department': cached_result['department'],
                    'source': cached_result['source'],
                    'confidence': cached_result['confidence']
                }
            else:
                return {
                    'department': 'Unknown',
                    'source': 'cache_only',
                    'confidence': 'none'
                }
        else:
            return asyncio.run(get_pi_department(name, institution))
    except Exception as e:
        print(f"Error in sync PI lookup: {e}")
        return {
            'department': 'Unknown',
            'source': 'error',
            'confidence': 'none'
        }

# Convenience function that returns just the department string
def get_department_string(name: str, institution: str) -> str:
    """
    Get just the department string (for backward compatibility).
    
    Args:
        name: Full name of the PI
        institution: Institution name
    
    Returns:
        Department string
    """
    result = get_pi_department_sync(name, institution)
    return result['department']

if __name__ == "__main__":
    # Test the module
    async def test():
        result1 = await get_pi_department("Jennifer Doudna", "UC Berkeley")
        print(f"Test 1: {result1}")
        
        result2 = await get_pi_department("Anthony Fauci", "NIH")
        print(f"Test 2: {result2}")
    
    asyncio.run(test())
