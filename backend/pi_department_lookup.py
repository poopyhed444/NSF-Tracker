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
                # Parse name for ORCID search
                clean_name = name.replace(":", "").strip()
                if "," in clean_name:
                    # Format: LASTNAME, FIRSTNAME MIDDLENAME
                    family, given_and_middle = [part.strip() for part in clean_name.split(",", 1)]
                    given_parts = given_and_middle.split()
                    given = given_parts[0] if given_parts else ""
                    middle = ' '.join(given_parts[1:]) if len(given_parts) > 1 else ""
                else:
                    # Format: FIRSTNAME MIDDLENAME LASTNAME
                    name_parts = clean_name.split()
                    given = name_parts[0] if len(name_parts) > 0 else ""
                    family = name_parts[-1] if len(name_parts) > 1 else ""
                    middle = ' '.join(name_parts[1:-1]) if len(name_parts) > 2 else ""

                search_query = f'given-names:{given} AND family-name:{family}'
                if middle:
                    search_query += f' AND other-names:{middle}'

                headers = {
                    'Accept': 'application/json',
                    'User-Agent': 'NIH-NSF-Tracker/1.0'
                }

                params = {
                    'q': search_query,
                    'rows': 20
                }

                with open(os.path.join(os.path.dirname(__file__), "debug.log"), "a", encoding="utf-8") as debug_log:
                    debug_log.write(f"[DEBUG] ORCID search_query: {search_query}\n")
                response = await client.get(ORCIDLookup.ORCID_SEARCH_URL, 
                                          headers=headers, params=params)
                response.raise_for_status()
                search_data = response.json()
                with open(os.path.join(os.path.dirname(__file__), "debug.log"), "a", encoding="utf-8") as debug_log:
                    debug_log.write(f"[DEBUG] ORCID search_data: {search_data}\n")

                for result in search_data.get('result', []):
                    orcid_id = result.get('orcid-identifier', {}).get('path')
                    if not orcid_id:
                        continue

                    # Get detailed record
                    record_url = f"{ORCIDLookup.ORCID_RECORD_URL}/{orcid_id}/record"
                    record_response = await client.get(record_url, headers=headers)
                    record_response.raise_for_status()
                    record_data = record_response.json()
                    with open(os.path.join(os.path.dirname(__file__), "debug.log"), "a", encoding="utf-8") as debug_log:
                        debug_log.write(f"[DEBUG] ORCID record_data for {orcid_id}: {record_data}\n")

                    # Check if institution matches
                    department = ORCIDLookup._extract_department_from_record(
                        record_data, institution)
                    with open(os.path.join(os.path.dirname(__file__), "debug.log"), "a", encoding="utf-8") as debug_log:
                        debug_log.write(f"[DEBUG] Extracted department: {department} (type: {type(department)})\n")
                    if department:
                        with open(os.path.join(os.path.dirname(__file__), "debug.log"), "a", encoding="utf-8") as debug_log:
                            debug_log.write(f"[DEBUG] Returning department: {department}, confidence: 'high'\n")
                        return department, "high"

                with open(os.path.join(os.path.dirname(__file__), "debug.log"), "a", encoding="utf-8") as debug_log:
                    debug_log.write("[DEBUG] No matching department found in ORCID results.\n")
                return None

            except Exception as e:
                with open(os.path.join(os.path.dirname(__file__), "debug.log"), "a", encoding="utf-8") as debug_log:
                    debug_log.write(f"ORCID lookup error: {e}\n")
                    import traceback
                    import io
                    buf = io.StringIO()
                    traceback.print_exc(file=buf)
                    debug_log.write(buf.getvalue())
                return None
    
    @staticmethod
    def _extract_department_from_record(record_data: Dict, target_institution: str) -> Optional[str]:
        """Extract department from ORCID record if institution matches. Handles nested ORCID structure."""
        try:
            activities = record_data.get('activities-summary', {})
            target_institution_lower = target_institution.lower()

            # Helper to check org match
            def org_matches(org_name):
                return any(word in org_name for word in target_institution_lower.split() if len(word) > 3)

            # Check employments (nested structure)
            employments = activities.get('employments', {}).get('affiliation-group', [])
            for group in employments:
                for summary in group.get('summaries', []):
                    employment = summary.get('employment-summary', {})
                    org_name = employment.get('organization', {}).get('name', '').lower()
                    dept_name = employment.get('department-name')
                    if org_matches(org_name):
                        if dept_name:
                            return dept_name
                        # Try to extract from role title
                        role_title = employment.get('role-title', '')
                        if role_title:
                            dept_keywords = [
                                'department', 'dept', 'school of', 'division of',
                                'center for', 'institute'
                            ]
                            role_lower = role_title.lower()
                            for keyword in dept_keywords:
                                if keyword in role_lower:
                                    parts = role_lower.split(keyword)
                                    if len(parts) > 1:
                                        potential_dept = parts[1].strip().split(',')[0].strip()
                                        if potential_dept:
                                            return potential_dept.title()

            # Check educations (nested structure)
            educations = activities.get('educations', {}).get('affiliation-group', [])
            for group in educations:
                for summary in group.get('summaries', []):
                    education = summary.get('education-summary', {})
                    org_name = education.get('organization', {}).get('name', '').lower()
                    dept_name = education.get('department-name')
                    if org_matches(org_name):
                        if dept_name:
                            return dept_name

            # If no department found from employments/educations, analyze works using NLP
            works_dept = ORCIDLookup._analyze_works_for_department(activities)
            if works_dept:
                with open(os.path.join(os.path.dirname(__file__), "debug.log"), "a", encoding="utf-8") as debug_log:
                    debug_log.write(f"[DEBUG] NLP analysis found department: {works_dept}\n")
                return works_dept

            return None
        except Exception as e:
            print(f"Error extracting department from ORCID record: {e}")
            return None

    @staticmethod
    def _analyze_works_for_department(activities: Dict) -> Optional[str]:
        """Analyze ORCID works/publications to guess department using NLP."""
        try:
            works = activities.get('works', {}).get('group', [])
            if not works:
                return None

            # Collect titles and journal names from works
            text_content = []
            journal_titles = []
            for work_group in works:
                for work_summary in work_group.get('work-summary', []):
                    title = work_summary.get('title', {})
                    if title and title.get('title', {}).get('value'):
                        text_content.append(title['title']['value'])
                    
                    journal = work_summary.get('journal-title', {})
                    if journal and journal.get('value'):
                        journal_title = journal['value']
                        text_content.append(journal_title)
                        journal_titles.append(journal_title)

            if not text_content:
                return None

            # Combine all text
            combined_text = ' '.join(text_content).lower()

            # Department keywords and scoring
            dept_keywords = {
                'biology': ['biology', 'biological', 'molecular biology', 'cell biology', 'genetics', 'genomics', 'biotechnology', 'life sciences'],
                'chemistry': ['chemistry', 'chemical', 'biochemistry', 'organic chemistry', 'inorganic chemistry', 'analytical chemistry'],
                'physics': ['physics', 'physical', 'quantum', 'optics', 'mechanics', 'thermodynamics', 'electromagnetic'],
                'engineering': ['engineering', 'mechanical', 'electrical', 'civil', 'bioengineering', 'biomedical engineering', 'computer engineering'],
                'medicine': [
                    'medicine', 'medical', 'clinical', 'therapeutic', 'pharmacology', 'pathology', 'oncology', 'cardiology',
                    'internal medicine', 'infectious disease', 'endocrinology', 'rheumatology', 'hematology', 'gastroenterology',
                    'pulmonology', 'nephrology', 'geriatrics', 'hospital medicine', 'primary care', 'family medicine', 'general practice',
                    'obstetrics', 'gynecology', 'ob/gyn', 'obstetrics and gynecology', 'maternal-fetal medicine', 'perinatology',
                    'reproductive medicine', 'women\'s health', 'pediatrics', 'neonatology', 'adolescent medicine', 'emergency medicine',
                    'critical care', 'anesthesiology', 'dermatology', 'urology', 'orthopedics', 'orthopaedics', 'plastic surgery',
                    'otolaryngology', 'ophthalmology', 'radiology', 'nuclear medicine', 'sports medicine', 'pain medicine', 'allergy', 'immunology',
                    'psychiatry', 'psychosomatic', 'forensic medicine', 'toxicology', 'occupational medicine', 'preventive medicine', 'public health',
                    'obstetric', 'gynecologic', 'obstetrician', 'gynecologist', 'obstetricians', 'gynecologists', 'ob gyn', 'obgyn', 'ob-gyn',
                    'obstetrician-gynecologist', 'obstetrician gynecologist', 'obstetrics & gynecology', 'obstetrics & gynaecology', 'gynaecology',
                    'maternal health', 'perinatal', 'perinatal medicine', 'reproductive endocrinology', 'reproductive endocrinologist',
                    'reproductive endocrinology and infertility', 'infertility', 'fertility', 'fetal medicine', 'placenta', 'placental', 'pregnancy',
                    'prenatal', 'peripartum', 'postpartum', 'labor and delivery', 'labor & delivery', 'labor/delivery', 'obstetric care', 'gynecologic oncology',
                    'urogynecology', 'urogynecologic', 'urogynecology', 'minimally invasive gynecology', 'minimally invasive surgery', 'reproductive biology',
                    'reproductive science', 'reproductive health', 'women\'s reproductive health', 'women\'s medicine', 'women\'s hospital', 'women\'s clinic',
                    'obstetric medicine', 'gynecologic medicine', 'obstetric surgery', 'gynecologic surgery', 'obstetrician/gynecologist', 'obstetrician gynecologist',
                    'obstetrician-gynecologist', 'obstetrician gynecologist', 'obstetrician', 'gynecologist', 'obstetricians', 'gynecologists', 'ob gyn', 'obgyn', 'ob-gyn',
                ],
                'obstetrics and gynecology': [
                    'obstetrics', 'gynecology', 'ob/gyn', 'obstetrics and gynecology', 'maternal-fetal medicine', 'perinatology',
                    'reproductive medicine', 'women\'s health', 'obstetric', 'gynecologic', 'obstetrician', 'gynecologist', 'obstetricians', 'gynecologists',
                    'ob gyn', 'obgyn', 'ob-gyn', 'obstetrician-gynecologist', 'obstetrician gynecologist', 'obstetrics & gynecology', 'obstetrics & gynaecology',
                    'gynaecology', 'maternal health', 'perinatal', 'perinatal medicine', 'reproductive endocrinology', 'reproductive endocrinologist',
                    'reproductive endocrinology and infertility', 'infertility', 'fertility', 'fetal medicine', 'placenta', 'placental', 'pregnancy',
                    'prenatal', 'peripartum', 'postpartum', 'labor and delivery', 'labor & delivery', 'labor/delivery', 'obstetric care', 'gynecologic oncology',
                    'urogynecology', 'urogynecologic', 'urogynecology', 'minimally invasive gynecology', 'minimally invasive surgery', 'reproductive biology',
                    'reproductive science', 'reproductive health', 'women\'s reproductive health', 'women\'s medicine', 'women\'s hospital', 'women\'s clinic',
                    'obstetric medicine', 'gynecologic medicine', 'obstetric surgery', 'gynecologic surgery', 'obstetrician/gynecologist', 'obstetrician gynecologist',
                    'obstetrician-gynecologist', 'obstetrician gynecologist',
                ],
                'neuroscience': ['neuroscience', 'neurological', 'brain', 'neural', 'cognitive', 'behavioral neuroscience'],
                'computer science': ['computer', 'computational', 'algorithm', 'machine learning', 'artificial intelligence', 'software'],
                'psychology': ['psychology', 'psychological', 'behavioral', 'cognitive psychology', 'social psychology'],
                'mathematics': ['mathematics', 'mathematical', 'statistics', 'statistical', 'probability', 'algebra', 'calculus'],
                'environmental science': ['environmental', 'ecology', 'climate', 'sustainability', 'ecosystem', 'conservation'],
                'materials science': ['materials', 'nanomaterials', 'polymer', 'ceramic', 'metallurgy', 'composite'],
                'geology': ['geology', 'geological', 'earth science', 'geophysics', 'mineralogy', 'petrology'],
                'astronomy': ['astronomy', 'astrophysics', 'cosmology', 'planetary', 'stellar', 'galactic'],
                'anthropology': ['anthropology', 'anthropological', 'archaeological', 'cultural', 'ethnographic'],
                'sociology': ['sociology', 'sociological', 'social science', 'demography', 'criminology'],
                'economics': ['economics', 'economic', 'econometrics', 'finance', 'business', 'market'],
                'education': ['education', 'educational', 'pedagogy', 'curriculum', 'learning', 'teaching']
            }
            # If no department found, try external NLP API (placeholder)
            if all(score == 0 for score in dept_scores.values()):
                # Example: call_external_nlp_api(combined_text) and map result to department
                pass  # You can implement this with OpenAI, HuggingFace, etc.

            # Score each department
            dept_scores = {}
            for dept, keywords in dept_keywords.items():
                score = 0
                for keyword in keywords:
                    if keyword in combined_text:
                        # Weight longer phrases higher
                        score += len(keyword.split()) * combined_text.count(keyword)
                dept_scores[dept] = score

            # Try to extract department from journal titles like 'Journal of ...'
            import re
            journal_dept_map = {
                'biology': 'Biology',
                'chemistry': 'Chemistry',
                'physics': 'Physics',
                'engineering': 'Engineering',
                'medicine': 'Medicine',
                'neuroscience': 'Neuroscience',
                'computer science': 'Computer Science',
                'psychology': 'Psychology',
                'mathematics': 'Mathematics',
                'environmental science': 'Environmental Science',
                'materials science': 'Materials Science',
                'geology': 'Geology',
                'astronomy': 'Astronomy',
                'anthropology': 'Anthropology',
                'sociology': 'Sociology',
                'economics': 'Economics',
                'education': 'Education',
                'immunology': 'Immunology',
                'oncology': 'Oncology',
                'cardiology': 'Cardiology',
                'pharmacy': 'Pharmacy',
                'biochemistry': 'Biochemistry',
                'statistics': 'Statistics',
                'biostatistics': 'Biostatistics',
                'neurology': 'Neurology',
                'internal medicine': 'Internal Medicine',
                'pediatrics': 'Pediatrics',
                'surgery': 'Surgery',
                'cognitive science': 'Cognitive Science',
                'computational biology': 'Computational Biology',
            }
            for jt in journal_titles:
                m = re.search(r'journal of ([a-zA-Z &]+)', jt, re.IGNORECASE)
                if m:
                    possible = m.group(1).strip().lower()
                    # Try direct match
                    if possible in journal_dept_map:
                        return journal_dept_map[possible]
                    # Try partial match
                    for key in journal_dept_map:
                        if key in possible:
                            return journal_dept_map[key]

            # Find department with highest score
            if dept_scores:
                best_dept = max(dept_scores, key=dept_scores.get)
                if dept_scores[best_dept] > 0:
                    return best_dept.title()

            return None

        except Exception as e:
            with open(os.path.join(os.path.dirname(__file__), "debug.log"), "a", encoding="utf-8") as debug_log:
                debug_log.write(f"Error analyzing works for department: {e}\n")
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
