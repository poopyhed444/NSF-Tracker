"""
PI Department Lookup Module

This module provides functionality to determine a principal investigator's 
academic department using ORCID API, grant database mining, and SciBERT classification.
"""

import json
import os
import re
import httpx
import asyncio
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
import requests
from scibert_classifier import predict_department_scibert, predict_from_research_context

# --- Crossref-based department extraction utilities ---
DEPT_VOCAB = [
    "Biology","Chemistry","Physics","Mathematics",
    "Computer Science","Neuroscience","Psychology",
    "Immunology","Oncology","Engineering","Medicine"
]

def fetch_crossref_metadata(doi: str) -> dict:
    """Fetch metadata for a DOI from Crossref."""
    url = f"https://api.crossref.org/works/{doi}"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json().get("message", {})

def find_pi_affiliation(metadata: dict, pi_name: str) -> str:
    """Locate the PI in author list and return their first affiliation string."""
    for author in metadata.get("author", []):
        full = " ".join(filter(None, [author.get("given"), author.get("family")]))
        if full.lower() == pi_name.lower():
            affs = author.get("affiliation", [])
            if affs:
                return affs[0].get("name","")
    return ""

def extract_department(affiliation: str) -> str:
    """Extract department from an affiliation using vocab and regex."""
    text = affiliation or ""
    for dept in DEPT_VOCAB:
        if dept.lower() in text.lower():
            return dept
    m = re.search(r"department\s+of\s+([A-Za-z &\-]+)", text, re.I)
    if m:
        return m.group(1).strip().title()
    return "Unknown"

# Cache file path
CACHE_FILE = os.path.join(os.path.dirname(__file__), "pi_department_cache.json")
CACHE_EXPIRY_DAYS = 30

class PILookupCache:
    """Handles caching of PI department lookup results."""
    
    def __init__(self):
        self.cache = self._load_cache()
    
    def _normalize_name(self, name: str) -> str:
        """
        Normalize name format to ensure consistent cache keys.
        Handles different formats like:
        - "Kjersti Aagaard" -> "aagaard kjersti"
        - "aagaard, kjersti marie" -> "aagaard kjersti"
        - "Aagaard, K. M." -> "aagaard k"
        
        Strategy: Extract first and last name only, handle comma-separated formats
        """
        if not name:
            return ""
        
        # Handle comma-separated format (Last, First Middle)
        if ',' in name:
            parts = name.split(',', 1)
            last_name = parts[0].strip()
            first_part = parts[1].strip() if len(parts) > 1 else ""
            
            # Extract first name from the first part (ignore middle names)
            first_names = [part.strip() for part in first_part.split() if part.strip() and len(part.strip()) > 1]
            first_name = first_names[0] if first_names else ""
            
            if first_name and last_name:
                return ' '.join(sorted([first_name.lower(), last_name.lower()]))
            elif last_name:
                return last_name.lower()
            else:
                return ""
        
        # Handle regular format (First Middle Last)
        cleaned = name.replace('.', ' ').strip()
        name_parts = [part.strip().lower() for part in cleaned.split() if part.strip() and len(part.strip()) > 1]
        
        if len(name_parts) == 0:
            return ""
        elif len(name_parts) == 1:
            return name_parts[0]
        elif len(name_parts) == 2:
            # Two parts: assume first and last
            return ' '.join(sorted(name_parts))
        else:
            # Multiple parts: use first and last word
            first_part = name_parts[0]
            last_part = name_parts[-1]
            
            return ' '.join(sorted([first_part, last_part]))
    
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
        key = self._normalize_name(name) + "|" + institution.lower().strip()
        entry = self.cache.get(key)
        
        if entry and not self._is_expired(entry.get('timestamp', '')):
            return entry
        return None
    
    def set(self, name: str, institution: str, department: str, source: str, confidence: str):
        """Cache PI lookup result."""
        key = self._normalize_name(name) + "|" + institution.lower().strip()
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
        with open(os.path.join(os.path.dirname(__file__), "debug.log"), "a", encoding="utf-8") as debug_log:
            debug_log.write(f"[DEBUG] Starting ORCID search for '{name}' at '{institution}'\n")
        
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

                # Create search query - be less restrictive with middle names
                search_query = f'given-names:{given} AND family-name:{family}'
                # Don't include middle names in the primary search as they might not match exactly
                # if middle:
                #     search_query += f' AND other-names:{middle}'

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

                # Handle case where ORCID API returns None for result instead of empty list
                results = search_data.get('result', [])
                if results is None:
                    with open(os.path.join(os.path.dirname(__file__), "debug.log"), "a", encoding="utf-8") as debug_log:
                        debug_log.write(f"[DEBUG] ORCID API returned None for results, treating as empty.\n")
                    return None

                for result in results:
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
                        record_data, institution, name)
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
    def _extract_department_from_record(record_data: Dict, target_institution: str, pi_name: str) -> Optional[str]:
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
            works_dept = ORCIDLookup._analyze_works_for_department(activities, pi_name)
            if works_dept:
                with open(os.path.join(os.path.dirname(__file__), "debug.log"), "a", encoding="utf-8") as debug_log:
                    debug_log.write(f"[DEBUG] NLP analysis found department: {works_dept}\n")
                return works_dept

            return None
        except Exception as e:
            print(f"Error extracting department from ORCID record: {e}")
            return None

    @staticmethod 
    def _analyze_works_for_department(activities: Dict, pi_name: str) -> Optional[str]:
        """Enhanced analysis of ORCID works/publications to guess department using research content."""
        try:
            works = activities.get('works', {})
            if works is None:
                with open(os.path.join(os.path.dirname(__file__), "debug.log"), "a", encoding="utf-8") as debug_log:
                    debug_log.write(f"[DEBUG] Works is None for {pi_name}\n")
                return None
            
            work_groups = works.get('group', [])
            if work_groups is None:
                with open(os.path.join(os.path.dirname(__file__), "debug.log"), "a", encoding="utf-8") as debug_log:
                    debug_log.write(f"[DEBUG] Work groups is None for {pi_name}\n")
                return None
                
            with open(os.path.join(os.path.dirname(__file__), "debug.log"), "a", encoding="utf-8") as debug_log:
                debug_log.write(f"[DEBUG] Analyzing {len(work_groups)} work groups for {pi_name}\n")
            
            # Collect comprehensive research content
            titles = []
            abstracts = []
            affiliations = []
            journal_names = []
            keywords = []
            
            # First try Crossref API lookup via DOI for detailed metadata
            for group in work_groups:
                if group is None:
                    continue
                work_summaries = group.get('work-summary', [])
                if work_summaries is None:
                    continue
                    
                for summary in work_summaries:
                    if summary is None:
                        continue
                        
                    # Collect title for analysis
                    try:
                        title_data = summary.get('title')
                        if title_data is not None:
                            title_inner = title_data.get('title')
                            if title_inner is not None:
                                title = title_inner.get('value', '')
                                if title:
                                    titles.append(title.strip())
                                    with open(os.path.join(os.path.dirname(__file__), "debug.log"), "a", encoding="utf-8") as debug_log:
                                        debug_log.write(f"[DEBUG] Found title: {title.strip()}\n")
                    except Exception as e:
                        with open(os.path.join(os.path.dirname(__file__), "debug.log"), "a", encoding="utf-8") as debug_log:
                            debug_log.write(f"[DEBUG] Error extracting title: {e}\n")
                    
                    # Collect journal name for field inference
                    try:
                        journal_data = summary.get('journal-title')
                        if journal_data is not None:
                            journal_title = journal_data.get('value', '')
                            if journal_title:
                                journal_names.append(journal_title.strip())
                                with open(os.path.join(os.path.dirname(__file__), "debug.log"), "a", encoding="utf-8") as debug_log:
                                    debug_log.write(f"[DEBUG] Found journal: {journal_title.strip()}\n")
                    except Exception as e:
                        with open(os.path.join(os.path.dirname(__file__), "debug.log"), "a", encoding="utf-8") as debug_log:
                            debug_log.write(f"[DEBUG] Error extracting journal: {e}\n")
                    
                    # Try DOI lookup for detailed metadata - skip this for now to isolate the issue
                    # We'll process this after we confirm basic extraction works
            
            with open(os.path.join(os.path.dirname(__file__), "debug.log"), "a", encoding="utf-8") as debug_log:
                debug_log.write(f"[DEBUG] Collected {len(titles)} titles, {len(journal_names)} journals\n")
                if journal_names:
                    debug_log.write(f"[DEBUG] Sample journals: {journal_names[:5]}\n")
            
            # Enhanced SciBERT analysis with comprehensive research context
            if titles or abstracts or affiliations or journal_names:
                try:
                    # Create comprehensive research profile
                    
                    # Combine titles (limit to avoid too much noise)
                    title_text = " ".join(titles[:10])  # Use first 10 titles
                    
                    # Combine abstracts 
                    abstract_text = " ".join(abstracts[:5])  # Use first 5 abstracts
                    
                    # Combine affiliations
                    affiliation_text = " ".join(affiliations[:5])
                    
                    # Analyze journal names for field hints
                    journal_hints = []
                    for journal in journal_names[:10]:  # Check first 10 journals
                        journal_lower = journal.lower()
                        
                        # Medical journal patterns
                        if any(word in journal_lower for word in [
                            'obstetrics', 'gynecology', 'maternal', 'fetal', 'pregnancy',
                            'reproductive', 'contraception', 'perinatal'
                        ]):
                            journal_hints.append('obstetrics gynecology reproductive medicine')
                        elif any(word in journal_lower for word in [
                            'pediatr', 'child', 'adolescent', 'neonatal', 'infant'
                        ]):
                            journal_hints.append('pediatrics child health development')
                        elif any(word in journal_lower for word in [
                            'cardio', 'heart', 'cardiac', 'cardiovascular', 'coronary'
                        ]):
                            journal_hints.append('cardiology heart disease cardiovascular')
                        elif any(word in journal_lower for word in [
                            'cancer', 'oncol', 'tumor', 'malignancy', 'chemotherapy'
                        ]):
                            journal_hints.append('oncology cancer treatment')
                        elif any(word in journal_lower for word in [
                            'dermat', 'skin', 'melanoma', 'psoriasis'
                        ]):
                            journal_hints.append('dermatology skin disease')
                        elif any(word in journal_lower for word in [
                            'psych', 'mental health', 'depression', 'anxiety'
                        ]):
                            journal_hints.append('psychiatry mental health')
                        elif any(word in journal_lower for word in [
                            'neurol', 'brain', 'stroke', 'epilepsy', 'alzheimer'
                        ]):
                            journal_hints.append('neurology brain disorders')
                        elif any(word in journal_lower for word in [
                            'anesth', 'pain', 'analgesia'
                        ]):
                            journal_hints.append('anesthesiology pain management')
                        elif any(word in journal_lower for word in [
                            'radiol', 'imaging', 'mri', 'ct scan'
                        ]):
                            journal_hints.append('radiology medical imaging')
                        elif any(word in journal_lower for word in [
                            'pathol', 'histopathology', 'biopsy'
                        ]):
                            journal_hints.append('pathology diagnostic medicine')
                    
                    journal_text = " ".join(journal_hints)
                    
                    # Combine keywords
                    keyword_text = " ".join(keywords[:20]) if keywords else ""
                    
                    with open(os.path.join(os.path.dirname(__file__), "debug.log"), "a", encoding="utf-8") as debug_log:
                        debug_log.write(f"[DEBUG] Journal hints: {journal_hints}\n")
                        debug_log.write(f"[DEBUG] Combined journal text: {journal_text}\n")
                    
                    # Use enhanced SciBERT prediction with multiple text sources
                    scibert_result = predict_from_research_context(
                        title=title_text,
                        abstract=abstract_text,
                        affiliation=affiliation_text + " " + journal_text + " " + keyword_text,
                        keywords=keywords[:10] if keywords else []
                    )
                    
                    with open(os.path.join(os.path.dirname(__file__), "debug.log"), "a", encoding="utf-8") as debug_log:
                        debug_log.write(f"[DEBUG] SciBERT result: {scibert_result}\n")
                        debug_log.write(f"[DEBUG] Checking confidence: {scibert_result['confidence']} > 0.20 = {scibert_result['confidence'] > 0.20}\n")
                        debug_log.write(f"[DEBUG] Department != Unknown: {scibert_result['department'] != 'Unknown'}\n")
                    
                    # Lower confidence threshold for ORCID-based research analysis
                    # since we have rich publication data
                    if (scibert_result['department'] != 'Unknown' and 
                        scibert_result['confidence'] > 0.20):  # Lower threshold for rich ORCID data
                        with open(os.path.join(os.path.dirname(__file__), "debug.log"), "a", encoding="utf-8") as debug_log:
                            debug_log.write(f"[DEBUG] Enhanced ORCID SciBERT found: {scibert_result['department']} (confidence: {scibert_result['confidence']:.3f})\n")
                            debug_log.write(f"[DEBUG] Research context - Titles: {len(titles)}, Abstracts: {len(abstracts)}, Journals: {len(journal_names)}\n")
                        return scibert_result['department']
                    else:
                        with open(os.path.join(os.path.dirname(__file__), "debug.log"), "a", encoding="utf-8") as debug_log:
                            debug_log.write(f"[DEBUG] SciBERT result failed threshold check\n")
                
                except Exception as e:
                    with open(os.path.join(os.path.dirname(__file__), "debug.log"), "a", encoding="utf-8") as debug_log:
                        debug_log.write(f"[DEBUG] Enhanced SciBERT analysis error: {e}\n")
            
            return None
        except Exception as e:
            with open(os.path.join(os.path.dirname(__file__), "debug.log"), "a", encoding="utf-8") as debug_log:
                debug_log.write(f"[DEBUG] Works analysis error: {e}\n")
            return None

class DepartmentNormalizer:
    """Normalizes department names to standard forms."""
    
    DEPARTMENT_MAPPINGS = {
        # Medical specialties
        'obstetrics and gynecology': 'Obstetrics and Gynecology',
        'obstetrics': 'Obstetrics and Gynecology',
        'gynecology': 'Obstetrics and Gynecology',
        'maternal fetal medicine': 'Obstetrics and Gynecology',
        'reproductive medicine': 'Obstetrics and Gynecology',
        'pediatrics': 'Pediatrics',
        'pediatric': 'Pediatrics',
        'child health': 'Pediatrics',
        'neonatology': 'Pediatrics',
        'cardiology': 'Cardiology',
        'cardiac': 'Cardiology',
        'cardiovascular': 'Cardiology',
        'heart': 'Cardiology',
        'oncology': 'Oncology',
        'cancer': 'Oncology',
        'tumor': 'Oncology',
        'hematology': 'Oncology',
        'dermatology': 'Dermatology',
        'skin': 'Dermatology',
        'psychiatry': 'Psychiatry',
        'mental health': 'Psychiatry',
        'psychology': 'Psychology',
        'orthopedics': 'Orthopedics',
        'orthopaedics': 'Orthopedics',
        'bone': 'Orthopedics',
        'joint': 'Orthopedics',
        'neurology': 'Neurology',
        'neurological': 'Neurology',
        'brain': 'Neurology',
        'anesthesiology': 'Anesthesiology',
        'anesthesia': 'Anesthesiology',
        'pain medicine': 'Anesthesiology',
        'radiology': 'Radiology',
        'imaging': 'Radiology',
        'diagnostic radiology': 'Radiology',
        'pathology': 'Pathology',
        'pathological': 'Pathology',
        'histopathology': 'Pathology',
        
        # Biology variations
        'biology': 'Biology',
        'biological sciences': 'Biology',
        'life sciences': 'Biology',
        'molecular biology': 'Biology',
        'cell biology': 'Biology',
        'developmental biology': 'Biology',
        
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

# --- Main Department Lookup Orchestration ---

async def get_pi_department(name: str, institution: str, force_refresh: bool = False) -> Dict[str, str]:
    """
    Get PI department using a multi-step lookup process with caching.
    
    Args:
        name: Full name of the PI
        institution: Institution name
        force_refresh: If True, bypass cache and perform a fresh lookup.
    
    Returns:
        Dict with keys: 'department', 'source', 'confidence'
    """
    if not name or not institution:
        return {
            'department': 'Unknown',
            'source': 'none',
            'confidence': 'none'
        }
    
    # Check cache first, unless a refresh is forced
    if not force_refresh:
        cached_result = _cache.get(name, institution)
        if cached_result:
            return {
                'department': cached_result['department'],
                'source': cached_result['source'],
                'confidence': cached_result['confidence']
            }
    
    # --- Start of the full lookup process ---
    
    # 1. Try ORCID lookup
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
    
    # 2. Enhanced SciBERT fallback with research context
    try:
        # Try to get additional research context if available
        research_context = []
        
        # Add PI name for potential field inference
        if name:
            research_context.append(name)
        
        # Add institution for field specialization hints
        if institution != "Unknown":
            research_context.append(institution)
            
            # Add institutional context hints for better classification
            institution_lower = institution.lower()
            if 'medical' in institution_lower or 'hospital' in institution_lower:
                research_context.append('medical research clinical')
            elif 'cancer' in institution_lower:
                research_context.append('oncology cancer research')
            elif 'children' in institution_lower or 'pediatric' in institution_lower:
                research_context.append('pediatrics child health')
            elif 'heart' in institution_lower or 'cardiac' in institution_lower:
                research_context.append('cardiology cardiovascular')
        
        # Use enhanced research context classification
        text_for_classification = " ".join(research_context)
        
        if len(text_for_classification.strip()) > 10:  # Ensure we have meaningful text
            scibert_result = predict_from_research_context(
                title="",
                abstract="",
                affiliation=text_for_classification,
                keywords=[]
            )
            
            # Lower threshold for fallback since we have limited context
            if (scibert_result['department'] != 'Unknown' and 
                scibert_result['confidence'] > 0.22):  # Lower threshold for fallback
                
                normalized_dept = DepartmentNormalizer.normalize(scibert_result['department'])
                
                # Cache result
                _cache.set(name, institution, normalized_dept, 'scibert', 'medium')
                
                return {
                    'department': normalized_dept,
                    'source': 'scibert',
                    'confidence': 'medium'
                }
    except Exception as e:
        print(f"Error in enhanced SciBERT lookup for {name}: {e}")
    
    # 3. Grant database mining (NEW)
    try:
        from grant_mining import classify_pi_from_grants
        
        grant_result = await classify_pi_from_grants(name, institution)
        if (grant_result['department'] != 'Unknown' and 
            grant_result.get('confidence_score', 0) > 0.20):  # Lowered threshold for more coverage
            
            normalized_dept = DepartmentNormalizer.normalize(grant_result['department'])
            
            # Cache result with grant source info
            confidence = grant_result['confidence']
            source = f"grant_mining_{grant_result.get('grant_count', 0)}_grants"
            
            _cache.set(name, institution, normalized_dept, source, confidence)
            
            return {
                'department': normalized_dept,
                'source': source,
                'confidence': confidence
            }
    except Exception as e:
        print(f"Error in grant mining lookup for {name}: {e}")
    
    # 4. Final fallback: Try institution-based heuristics
    try:
        if institution != "Unknown":
            institution_lower = institution.lower()
            
            # Institution type heuristics
            institution_hints = {
                'medical center': 'Medicine',
                'cancer center': 'Oncology', 
                'hospital': 'Medicine',
                'medical college': 'Medicine',
                'school of medicine': 'Medicine',
                'health sciences': 'Medicine',
                'tech': 'Engineering',
                'institute of technology': 'Engineering',
                'massachusetts institute of technology': 'Engineering',
                'california institute of technology': 'Engineering',
                'agricultural': 'Biology',
                'marine': 'Biology',
                'astronomical': 'Physics',
                'observatory': 'Physics',
                'biomedical': 'Medicine',
                'veterinary': 'Veterinary Medicine',
                'dental': 'Dentistry',
                'pharmacy': 'Pharmacy',
                'nursing': 'Nursing',
                'psychiatry': 'Psychiatry',
                'neurology': 'Neurology',
                'cardiology': 'Cardiology',
                'children': 'Pediatrics',
                'pediatric': 'Pediatrics',
            }
            
            for hint, dept in institution_hints.items():
                if hint in institution_lower:
                    normalized_dept = DepartmentNormalizer.normalize(dept)
                    _cache.set(name, institution, normalized_dept, 'institution_heuristic', 'low')
                    
                    return {
                        'department': normalized_dept,
                        'source': 'institution_heuristic', 
                        'confidence': 'low'
                    }
    except Exception as e:
        print(f"Error in institution heuristics for {name}: {e}")
    
    # If all lookups fail, cache the 'Unknown' result to avoid repeated failed lookups
    result = {
        'department': 'Unknown',
        'source': 'none',
        'confidence': 'none'
    }
    
    # Cache the unknown result to avoid repeated lookups for PIs that are truly not found
    _cache.set(name, institution, 'Unknown', 'none', 'none')
    
    return result

def get_pi_department_sync(name: str, institution: str, force_refresh: bool = False) -> Dict[str, str]:
    """
    Synchronous implementation for PI department lookup.
    
    Args:
        name: Full name of the PI
        institution: Institution name
        force_refresh: If True, bypass cache and perform a fresh lookup.
    
    Returns:
        Dict with keys: 'department', 'source', 'confidence'
    """
    try:
        # Check cache first (unless force_refresh is True)
        if not force_refresh:
            cached_result = _cache.get(name, institution)
            if cached_result:
                return cached_result
        
        # For synchronous calls, we'll use a simplified approach that relies on cached data
        # and basic heuristics rather than making async web requests
        
        # Try basic pattern matching for common department keywords
        name_lower = name.lower()
        dept = 'Other'
        source = 'heuristic'
        confidence = 'low'
        
        # Simple department heuristics based on name patterns
        if any(keyword in name_lower for keyword in ['bio', 'life', 'molecular', 'cell', 'genetics', 'micro']):
            dept = 'Biology/Life Sciences'
            confidence = 'medium'
        elif any(keyword in name_lower for keyword in ['chem', 'biochem']):
            dept = 'Chemistry'
            confidence = 'medium'
        elif any(keyword in name_lower for keyword in ['phys', 'astro', 'quantum']):
            dept = 'Physics'
            confidence = 'medium'
        elif any(keyword in name_lower for keyword in ['comp', 'cs', 'software', 'data']):
            dept = 'Computer Science'
            confidence = 'medium'
        elif any(keyword in name_lower for keyword in ['eng', 'mech', 'civil', 'electric']):
            dept = 'Engineering'
            confidence = 'medium'
        elif any(keyword in name_lower for keyword in ['med', 'clinic', 'hospital', 'health']):
            dept = 'Medicine'
            confidence = 'medium'
        elif any(keyword in name_lower for keyword in ['math', 'stat', 'applied']):
            dept = 'Mathematics/Statistics'
            confidence = 'medium'
        
        result = {
            'department': dept,
            'source': source,
            'confidence': confidence
        }
        
        # Cache the result
        _cache.set(name, institution, result)
        
        return result
        
    except Exception as e:
        print(f"Error in sync PI lookup: {e}")
        return {
            'department': 'Other',
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
