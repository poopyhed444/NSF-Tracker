"""
Grant Database Mining Module

This module mines grant databases (NIH RePORTER, NSF) to classify PI departments
based on grant titles, abstracts, funding institutes, and historical patterns.
"""

import asyncio
import httpx
import json
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from dataclasses import dataclass

@dataclass
class GrantInfo:
    """Structured grant information for analysis."""
    pi_name: str
    title: str
    abstract: str
    funding_ic: str  # NIH Institute/Center
    award_amount: int
    start_date: str
    end_date: str
    organization: str
    activity_code: str  # R01, R21, etc.

class GrantDatabaseMiner:
    """Mines grant databases for PI department classification."""
    
    def __init__(self):
        self.nih_api_url = "https://api.reporter.nih.gov/v2/projects/search"
        self.nsf_api_url = "https://www.research.gov/awardapi-service/v1/awards.json"
        
        # NIH Institute/Center to Department mapping
        self.nih_ic_mapping = {
            # Medical/Clinical Institutes
            "NCI": "Oncology",  # National Cancer Institute
            "NHLBI": "Cardiology",  # Heart, Lung, Blood
            "NIDDK": "Endocrinology",  # Diabetes, Digestive, Kidney
            "NINDS": "Neurology",  # Neurological Disorders
            "NIAID": "Immunology",  # Allergy and Infectious Diseases
            "NIGMS": "Medicine",  # General Medical Sciences
            "NICHD": "Pediatrics",  # Child Health and Development
            "NEI": "Ophthalmology",  # Eye Institute
            "NIDCD": "Otolaryngology",  # Deafness and Communication
            "NIMH": "Psychiatry",  # Mental Health
            "NIDA": "Psychiatry",  # Drug Abuse
            "NIAAA": "Psychiatry",  # Alcohol Abuse
            "NIA": "Geriatrics",  # Aging
            "NIAMS": "Rheumatology",  # Arthritis, Musculoskeletal
            "NIDCR": "Dentistry",  # Dental Research
            "NIEHS": "Environmental Health",  # Environmental Health
            "NIOSH": "Occupational Health",  # Occupational Safety
            "NINR": "Nursing",  # Nursing Research
            "NCCIH": "Integrative Medicine",  # Complementary Health
            
            # Research Institutes
            "NHGRI": "Genetics",  # Human Genome Research
            "NIBIB": "Biomedical Engineering",  # Biomedical Imaging
            "NCATS": "Translational Medicine",  # Advancing Translational Sciences
            "NLM": "Medical Informatics",  # Library of Medicine
            "FIC": "Global Health",  # Fogarty International
        }
        
        # Grant title keywords to department mapping
        self.title_keywords = {
            "cancer": "Oncology",
            "tumor": "Oncology",
            "chemotherapy": "Oncology",
            "oncology": "Oncology",
            "malignancy": "Oncology",
            
            "heart": "Cardiology",
            "cardiac": "Cardiology",
            "cardiovascular": "Cardiology",
            "coronary": "Cardiology",
            "hypertension": "Cardiology",
            
            "brain": "Neurology",
            "neurological": "Neurology",
            "alzheimer": "Neurology",
            "parkinson": "Neurology",
            "stroke": "Neurology",
            "epilepsy": "Neurology",
            
            "diabetes": "Endocrinology",
            "insulin": "Endocrinology",
            "glucose": "Endocrinology",
            "metabolic": "Endocrinology",
            
            "immune": "Immunology",
            "immunology": "Immunology",
            "antibody": "Immunology",
            "vaccine": "Immunology",
            "infection": "Immunology",
            
            "pediatric": "Pediatrics",
            "children": "Pediatrics",
            "infant": "Pediatrics",
            "neonatal": "Pediatrics",
            
            "mental": "Psychiatry",
            "depression": "Psychiatry",
            "anxiety": "Psychiatry",
            "psychiatric": "Psychiatry",
            "behavioral": "Psychology",
            
            "gene": "Genetics",
            "genetic": "Genetics",
            "genomic": "Genetics",
            "dna": "Genetics",
            "rna": "Biology",
            
            "protein": "Biochemistry",
            "enzyme": "Biochemistry",
            "molecular": "Biology",
            "cell": "Biology",
            "biology": "Biology",
            
            "chemistry": "Chemistry",
            "chemical": "Chemistry",
            "synthesis": "Chemistry",
            "drug": "Pharmacology",
            
            "imaging": "Radiology",
            "mri": "Radiology",
            "ultrasound": "Radiology",
            "x-ray": "Radiology",
            
            "surgery": "Surgery",
            "surgical": "Surgery",
            "operative": "Surgery",
            
            "engineering": "Engineering",
            "bioengineering": "Bioengineering",
            "technology": "Engineering",
            
            "computational": "Computer Science",
            "algorithm": "Computer Science",
            "machine learning": "Computer Science",
            "artificial intelligence": "Computer Science",
        }

    async def fetch_pi_grants(self, pi_name: str, institution: str, years_back: int = 10) -> List[GrantInfo]:
        """Fetch all grants for a specific PI from multiple databases."""
        grants = []
        
        # Fetch NIH grants
        nih_grants = await self._fetch_nih_grants(pi_name, institution, years_back)
        grants.extend(nih_grants)
        
        # Fetch NSF grants
        nsf_grants = await self._fetch_nsf_grants(pi_name, institution, years_back)
        grants.extend(nsf_grants)
        
        return grants

    async def _fetch_nih_grants(self, pi_name: str, institution: str, years_back: int) -> List[GrantInfo]:
        """Fetch NIH grants for a PI."""
        grants = []
        
        # Simplified search - use existing working format
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365 * years_back)
        
        search_criteria = {
            "criteria": {
                "pi_names": [{"any_name": pi_name}],
                "project_start_date": {
                    "from_date": start_date.strftime("%Y-%m-%d"),
                    "to_date": end_date.strftime("%Y-%m-%d")
                }
            },
            "include_fields": [
                "ProjectTitle",
                "AbstractText", 
                "Organization",
                "ContactPiName",
                "AwardAmount",
                "ProjectStartDate",
                "ProjectEndDate",
                "AgencyIcAdmin",
                "ActivityCode"
            ],
            "offset": 0,
            "limit": 100
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(self.nih_api_url, json=search_criteria)
                response.raise_for_status()
                data = response.json()
                
                for project in data.get("results", []):
                    # Filter by institution if specified
                    if institution != "Unknown":
                        org_name = ""
                        org_info = project.get("organization", {})
                        if isinstance(org_info, list) and len(org_info) > 0:
                            org_name = org_info[0].get("org_name", "")
                        elif isinstance(org_info, dict):
                            org_name = org_info.get("org_name", "")
                        
                        if not self._institution_matches(institution, org_name):
                            continue
                    
                    grant = GrantInfo(
                        pi_name=project.get("contact_pi_name", ""),
                        title=project.get("project_title", ""),
                        abstract=project.get("abstract_text", ""),
                        funding_ic=project.get("agency_ic_admin", {}).get("ic", "") if project.get("agency_ic_admin") else "",
                        award_amount=project.get("award_amount", 0),
                        start_date=project.get("project_start_date", ""),
                        end_date=project.get("project_end_date", ""),
                        organization=org_name,
                        activity_code=project.get("activity_code", "")
                    )
                    grants.append(grant)
                    
            except Exception as e:
                print(f"Error fetching NIH grants for {pi_name}: {e}")
                    
        return grants

    async def _fetch_nsf_grants(self, pi_name: str, institution: str, years_back: int) -> List[GrantInfo]:
        """Fetch NSF grants for a PI."""
        grants = []
        
        # NSF API parameters
        search_terms = self._generate_name_variations(pi_name)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for term in search_terms:
                params = {
                    "printFields": "id,title,piFirstName,piLastName,abstractText,fundsObligatedAmt,startDate,expDate,awardee",
                    "piLastName": term.split()[-1] if " " in term else term,
                    "rpp": "50"  # Results per page
                }
                
                try:
                    response = await client.get(self.nsf_api_url, params=params)
                    response.raise_for_status()
                    data = response.json()
                    
                    for award in data.get("response", {}).get("award", []):
                        # Filter by institution and name match
                        if institution != "Unknown":
                            awardee = award.get("awardee", "")
                            if not self._institution_matches(institution, awardee):
                                continue
                        
                        # Create unified grant object
                        grant = GrantInfo(
                            pi_name=f"{award.get('piFirstName', '')} {award.get('piLastName', '')}".strip(),
                            title=award.get("title", ""),
                            abstract=award.get("abstractText", ""),
                            funding_ic="NSF",
                            award_amount=award.get("fundsObligatedAmt", 0),
                            start_date=award.get("startDate", ""),
                            end_date=award.get("expDate", ""),
                            organization=award.get("awardee", ""),
                            activity_code="NSF"
                        )
                        grants.append(grant)
                        
                except Exception as e:
                    print(f"Error fetching NSF grants for {term}: {e}")
                    
        return grants

    def classify_department_from_grants(self, grants: List[GrantInfo]) -> Tuple[str, str, float]:
        """
        Classify department based on grant portfolio.
        Returns (department, source, confidence_score)
        """
        if not grants:
            return "Unknown", "grant_mining", 0.0
        
        department_scores = defaultdict(float)
        total_weight = 0
        
        for grant in grants:
            weight = 1.0
            
            # 1. NIH Institute/Center classification (high confidence)
            if grant.funding_ic in self.nih_ic_mapping:
                dept = self.nih_ic_mapping[grant.funding_ic]
                department_scores[dept] += 3.0 * weight  # High weight for IC mapping
                total_weight += 3.0 * weight
            
            # 2. Title keyword analysis (medium confidence)
            title_dept = self._classify_by_keywords(grant.title)
            if title_dept != "Unknown":
                department_scores[title_dept] += 2.0 * weight
                total_weight += 2.0 * weight
            
            # 3. Abstract keyword analysis (medium confidence)
            if grant.abstract:
                abstract_dept = self._classify_by_keywords(grant.abstract)
                if abstract_dept != "Unknown":
                    department_scores[abstract_dept] += 1.5 * weight
                    total_weight += 1.5 * weight
            
            # 4. Activity code patterns (low confidence)
            activity_dept = self._classify_by_activity_code(grant.activity_code)
            if activity_dept != "Unknown":
                department_scores[activity_dept] += 1.0 * weight
                total_weight += 1.0 * weight
        
        if not department_scores:
            return "Unknown", "grant_mining", 0.0
        
        # Find best department
        best_dept = max(department_scores, key=department_scores.get)
        confidence = department_scores[best_dept] / total_weight if total_weight > 0 else 0.0
        
        # Normalize confidence to 0-1 scale
        confidence = min(confidence / 2.0, 1.0)  # Divide by 2 since max single score is ~3
        
        return best_dept, "grant_mining", confidence

    def _classify_by_keywords(self, text: str) -> str:
        """Classify department based on text keywords."""
        if not text:
            return "Unknown"
        
        text_lower = text.lower()
        keyword_scores = defaultdict(int)
        
        for keyword, dept in self.title_keywords.items():
            if keyword in text_lower:
                keyword_scores[dept] += 1
        
        if keyword_scores:
            return max(keyword_scores, key=keyword_scores.get)
        
        return "Unknown"

    def _classify_by_activity_code(self, activity_code: str) -> str:
        """Classify department based on NIH activity codes."""
        if not activity_code:
            return "Unknown"
        
        # Some activity codes suggest specific research areas
        activity_mapping = {
            "T32": "Medicine",  # Training grants often medical
            "F30": "Medicine",  # Pre-doctoral fellowships
            "F31": "Biology",   # Graduate fellowships
            "F32": "Biology",   # Post-doctoral fellowships
            "K01": "Medicine",  # Career development
            "K08": "Medicine",  # Clinical scientist career development
            "K23": "Medicine",  # Patient-oriented career development
            "P01": "Medicine",  # Program projects (often clinical)
            "U01": "Medicine",  # Research projects (often clinical trials)
        }
        
        return activity_mapping.get(activity_code, "Unknown")

    def _generate_name_variations(self, name: str) -> List[str]:
        """Generate different name format variations for search."""
        variations = [name]
        
        # Handle comma-separated names
        if "," in name:
            parts = [p.strip() for p in name.split(",")]
            if len(parts) == 2:
                # "Last, First" -> "First Last"
                variations.append(f"{parts[1]} {parts[0]}")
        
        # Handle regular names
        name_parts = name.replace(",", "").split()
        if len(name_parts) >= 2:
            # "First Last" -> "Last, First"
            variations.append(f"{name_parts[-1]}, {' '.join(name_parts[:-1])}")
            # Just last name
            variations.append(name_parts[-1])
        
        return list(set(variations))  # Remove duplicates

    def _institution_matches(self, target: str, candidate: str) -> bool:
        """Check if institution names match (fuzzy matching)."""
        if not target or not candidate:
            return False
        
        target_words = set(target.lower().split())
        candidate_words = set(candidate.lower().split())
        
        # Remove common words
        common_words = {"university", "of", "the", "and", "college", "institute", "center"}
        target_words -= common_words
        candidate_words -= common_words
        
        # Check for significant overlap
        if len(target_words) == 0 or len(candidate_words) == 0:
            return False
        
        overlap = len(target_words & candidate_words)
        return overlap >= min(len(target_words), len(candidate_words)) * 0.5

# Convenience function for integration
async def classify_pi_from_grants(pi_name: str, institution: str) -> Dict[str, str]:
    """
    Classify PI department using grant database mining.
    Returns dict with keys: 'department', 'source', 'confidence'
    """
    miner = GrantDatabaseMiner()
    
    try:
        grants = await miner.fetch_pi_grants(pi_name, institution, years_back=10)
        
        if not grants:
            return {
                'department': 'Unknown',
                'source': 'grant_mining',
                'confidence': 'none'
            }
        
        department, source, confidence_score = miner.classify_department_from_grants(grants)
        
        # Convert confidence to categorical
        if confidence_score >= 0.7:
            confidence = "high"
        elif confidence_score >= 0.4:
            confidence = "medium"
        elif confidence_score > 0:
            confidence = "low"
        else:
            confidence = "none"
        
        return {
            'department': department,
            'source': source,
            'confidence': confidence,
            'grant_count': len(grants),
            'confidence_score': confidence_score
        }
        
    except Exception as e:
        print(f"Error in grant mining for {pi_name}: {e}")
        return {
            'department': 'Unknown',
            'source': 'grant_mining_error',
            'confidence': 'none'
        }

if __name__ == "__main__":
    # Test the module
    async def test():
        result = await classify_pi_from_grants("Jennifer Doudna", "University of California, Berkeley")
        print(f"Test result: {result}")
    
    asyncio.run(test())
