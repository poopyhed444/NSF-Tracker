"""
Federal Agency Grant Integration Module

This module provides access to grants and funding data from multiple federal agencies:
- USAspending.gov API for comprehensive federal spending data
- Grants.gov XML extract for opportunities data
- Agency-specific APIs (DoD, DOE, etc.)

Author: NSF-Tracker Enhancement
Date: July 2025
"""

import requests
import asyncio
import json
import xml.etree.ElementTree as ET
import zipfile
import io
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import pandas as pd
from collections import defaultdict, Counter
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FederalAgencyIntegrator:
    """Integrates with multiple federal agency APIs and data sources"""
    
    def __init__(self):
        self.usaspending_base_url = "https://api.usaspending.gov/api/v2"
        self.grants_gov_xml_url = "https://www.grants.gov/xml-extract"
        
        # Agency mapping for classification
        self.agency_mapping = {
            'Department of Health and Human Services': 'HHS',
            'National Science Foundation': 'NSF', 
            'National Institutes of Health': 'NIH',
            'Department of Defense': 'DOD',
            'Department of Energy': 'DOE',
            'Department of Agriculture': 'USDA',
            'Department of Education': 'ED',
            'Environmental Protection Agency': 'EPA',
            'Department of Veterans Affairs': 'VA',
            'National Aeronautics and Space Administration': 'NASA',
            'Department of Commerce': 'DOC',
            'Department of Homeland Security': 'DHS',
            'Department of Transportation': 'DOT',
            'Department of Justice': 'DOJ',
            'Small Business Administration': 'SBA'
        }
        
        # Common research-related CFDA codes
        self.research_cfda_codes = [
            '12.300',  # DOD Basic and Applied Scientific Research
            '12.431',  # DOD Basic Scientific Research
            '12.630',  # DOD Basic, Applied, and Advanced Research
            '47.041',  # NSF Engineering
            '47.049',  # NSF Mathematical and Physical Sciences
            '47.050',  # NSF Geosciences
            '47.070',  # NSF Computer and Information Science and Engineering
            '47.074',  # NSF Biological Sciences
            '47.075',  # NSF Social Behavioral and Economic Sciences
            '47.076',  # NSF Education and Human Resources
            '47.078',  # NSF Polar Programs
            '47.079',  # NSF International Science and Engineering
            '47.083',  # NSF Integrative Activities
            '93.121',  # NIH Oral Diseases and Disorders Research
            '93.172',  # NIH Human Heredity and Health Research
            '93.173',  # NIH Research Related to Deafness and Communication Disorders
            '93.233',  # NIH National Center for Advancing Translational Sciences
            '93.242',  # NIH Mental Health Research Grants
            '93.273',  # NIH Alcohol Research Programs
            '93.279',  # NIH Drug Abuse and Addiction Research Programs
            '93.286',  # NIH Discovery and Applied Research for Technological Innovations
            '93.393',  # NIH Cancer Cause and Prevention Research
            '93.394',  # NIH Cancer Detection and Diagnosis Research
            '93.395',  # NIH Cancer Treatment Research
            '93.396',  # NIH Cancer Biology Research
            '93.837',  # NIH Heart and Vascular Diseases Research
            '93.838',  # NIH Lung Diseases Research
            '93.839',  # NIH Blood Diseases and Resources Research
            '93.846',  # NIH Arthritis, Musculoskeletal and Skin Diseases Research
            '93.847',  # NIH Diabetes, Endocrinology and Metabolic Diseases Research
            '93.848',  # NIH Digestive Diseases and Nutrition Research
            '93.849',  # NIH Kidney Diseases, Urology and Hematology Research
            '93.853',  # NIH Extramural Research Programs in the Neurosciences
            '93.855',  # NIH Allergy and Infectious Diseases Research
            '93.859',  # NIH Pharmacology, Physiology, and Biological Chemistry Research
            '93.865',  # NIH Child Health and Human Development Extramural Research
            '93.866',  # NIH Aging Research
            '93.867',  # NIH Vision Research
            '93.879',  # NIH Medical Library Assistance
            '81.049',  # DOE Office of Science Financial Assistance Program
            '81.087',  # DOE Renewable Energy Research and Development
            '81.089',  # DOE Fossil Energy Research and Development
            '81.112',  # DOE Stewardship Science Grant Program
            '10.001',  # USDA Agricultural Research Basic and Applied Research
            '10.200',  # USDA Grants for Agricultural Research, Special Research Grants
            '10.206',  # USDA Grants for Agricultural Research Competitive Research Grants
            '10.310',  # USDA Agriculture and Food Research Initiative
        ]

    async def fetch_usaspending_data(self, 
                                   agency_codes: List[str] = None,
                                   award_types: List[str] = None,
                                   fiscal_years: List[int] = None,
                                   limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Fetch award data from USAspending.gov API
        
        Args:
            agency_codes: List of agency codes (e.g., ['020', '049'] for NSF, NIH)
            award_types: List of award types ('grant', 'contract', etc.)
            fiscal_years: List of fiscal years to include
            limit: Maximum number of records to return
        """
        try:
            # Default to research-focused agencies if none specified
            if not agency_codes:
                agency_codes = [
                    '020',  # National Science Foundation
                    '075',  # Department of Health and Human Services (includes NIH)
                    '097',  # Department of Defense
                    '089',  # Department of Energy
                ]
            
            if not award_types:
                # Use correct USASpending award type codes
                award_types = ['B', 'C', 'D']  # B=Cooperative Agreement, C=Block Grant, D=Project Grant
                
            if not fiscal_years:
                current_year = datetime.now().year
                fiscal_years = [current_year - 1, current_year, current_year + 1]

            # Construct the API request
            endpoint = f"{self.usaspending_base_url}/search/spending_by_award"
            
            # Map agency codes to agency names for USASpending API
            agency_name_mapping = {
                '020': 'National Science Foundation',
                '075': 'Department of Health and Human Services',  
                '097': 'Department of Defense',
                '089': 'Department of Energy',
                '080': 'National Aeronautics and Space Administration',
            }
            
            # Convert agency codes to names
            agency_filters = []
            for code in agency_codes:
                if code in agency_name_mapping:
                    agency_filters.append({
                        "type": "awarding",
                        "tier": "toptier", 
                        "name": agency_name_mapping[code]
                    })
            
            payload = {
                "filters": {
                    "award_type_codes": award_types,
                    "agencies": agency_filters
                },
                "fields": [
                    "Award ID", "Recipient Name", "Start Date", "End Date", 
                    "Award Amount", "Awarding Agency", "Awarding Sub Agency",
                    "Award Description", "Recipient State Code", "Recipient City Name",
                    "Recipient Country Name", "Primary Place of Performance City",
                    "Primary Place of Performance State", "NAICS Code", "NAICS Description",
                    "PSC Code", "PSC Description", "Award Type", "Recipient UEI"
                ],
                "page": 1,
                "limit": min(limit, 100),  # USASpending API max limit is 100
                "sort": "Award Amount",
                "order": "desc"
            }
            
            logger.info(f"Fetching USAspending data for agencies: {agency_codes}")
            logger.debug(f"Request payload: {json.dumps(payload, indent=2)}")
            
            response = requests.post(endpoint, json=payload, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"USASpending API error {response.status_code}: {response.text}")
            
            response.raise_for_status()
            
            data = response.json()
            awards = data.get('results', [])
            
            logger.info(f"Retrieved {len(awards)} awards from USAspending.gov")
            return awards
            
        except Exception as e:
            logger.error(f"Error fetching USAspending data: {str(e)}")
            return []

    async def fetch_grants_gov_xml(self, date: str = None) -> List[Dict[str, Any]]:
        """
        Fetch and parse Grants.gov XML extract
        
        Args:
            date: Date string in YYYYMMDD format, defaults to latest available
        """
        try:
            if not date:
                # Use today's date if available, fallback to yesterday
                today = datetime.now()
                date = today.strftime('%Y%m%d')
            
            xml_filename = f"GrantsDBExtract{date}v2.zip"
            xml_url = f"{self.grants_gov_xml_url}/{xml_filename}"
            
            logger.info(f"Downloading Grants.gov XML extract: {xml_filename}")
            
            response = requests.get(xml_url, timeout=60)
            response.raise_for_status()
            
            # Extract and parse the XML file
            with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
                xml_files = [f for f in zip_file.namelist() if f.endswith('.xml')]
                
                if not xml_files:
                    logger.error("No XML files found in the zip archive")
                    return []
                
                xml_content = zip_file.read(xml_files[0])
                
            # Parse XML content
            root = ET.fromstring(xml_content)
            grants = []
            
            for opportunity in root.findall('.//OpportunityDetail'):
                try:
                    grant_data = {
                        'opportunity_id': self._get_xml_text(opportunity, 'OpportunityID'),
                        'opportunity_number': self._get_xml_text(opportunity, 'OpportunityNumber'),
                        'opportunity_title': self._get_xml_text(opportunity, 'OpportunityTitle'),
                        'agency_code': self._get_xml_text(opportunity, 'AgencyCode'),
                        'agency_name': self._get_xml_text(opportunity, 'AgencyName'),
                        'sub_agency': self._get_xml_text(opportunity, 'SubAgency'),
                        'opportunity_category': self._get_xml_text(opportunity, 'OpportunityCategory'),
                        'funding_instrument': self._get_xml_text(opportunity, 'FundingInstrumentType'),
                        'category_explanation': self._get_xml_text(opportunity, 'CategoryExplanation'),
                        'cfda_numbers': self._get_xml_text(opportunity, 'CFDANumbers'),
                        'eligible_applicants': self._get_xml_text(opportunity, 'EligibleApplicants'),
                        'post_date': self._get_xml_text(opportunity, 'PostDate'),
                        'close_date': self._get_xml_text(opportunity, 'CloseDate'),
                        'last_updated': self._get_xml_text(opportunity, 'LastUpdatedDate'),
                        'award_ceiling': self._get_xml_text(opportunity, 'AwardCeiling'),
                        'award_floor': self._get_xml_text(opportunity, 'AwardFloor'),
                        'estimated_funding': self._get_xml_text(opportunity, 'EstimatedTotalProgramFunding'),
                        'expected_awards': self._get_xml_text(opportunity, 'ExpectedNumberOfAwards'),
                        'description': self._get_xml_text(opportunity, 'Description'),
                        'version': self._get_xml_text(opportunity, 'Version'),
                        'cost_sharing': self._get_xml_text(opportunity, 'CostSharingOrMatchingRequirement'),
                        'funding_activity': self._get_xml_text(opportunity, 'FundingActivity')
                    }
                    
                    # Only include research-related opportunities
                    if self._is_research_related(grant_data):
                        grants.append(grant_data)
                        
                except Exception as e:
                    logger.warning(f"Error parsing opportunity: {str(e)}")
                    continue
            
            logger.info(f"Parsed {len(grants)} research-related opportunities from Grants.gov XML")
            return grants
            
        except Exception as e:
            logger.error(f"Error fetching Grants.gov XML: {str(e)}")
            return []

    def _get_xml_text(self, element, tag_name: str) -> str:
        """Safely extract text from XML element"""
        child = element.find(tag_name)
        return child.text if child is not None and child.text else ""

    def _is_research_related(self, grant_data: Dict[str, Any]) -> bool:
        """Determine if a grant opportunity is research-related"""
        # Check CFDA numbers
        cfda_numbers = grant_data.get('cfda_numbers', '').split(',')
        for cfda in cfda_numbers:
            if cfda.strip() in self.research_cfda_codes:
                return True
        
        # Check title and description for research keywords
        research_keywords = [
            'research', 'science', 'innovation', 'discovery', 'investigation',
            'study', 'analysis', 'experiment', 'development', 'technology',
            'scientific', 'academic', 'university', 'college', 'faculty',
            'laboratory', 'lab', 'R&D', 'STEM', 'biomedical', 'clinical'
        ]
        
        text_to_check = (
            grant_data.get('opportunity_title', '') + ' ' +
            grant_data.get('description', '') + ' ' +
            grant_data.get('category_explanation', '')
        ).lower()
        
        return any(keyword in text_to_check for keyword in research_keywords)

    async def fetch_agency_specific_data(self, agency: str) -> List[Dict[str, Any]]:
        """
        Fetch data from agency-specific APIs where available
        
        Args:
            agency: Agency identifier (DOD, DOE, etc.)
        """
        try:
            if agency.upper() == 'DOD':
                return await self._fetch_dod_data()
            elif agency.upper() == 'DOE':
                return await self._fetch_doe_data()
            elif agency.upper() == 'NASA':
                return await self._fetch_nasa_data()
            else:
                logger.info(f"No specific API integration available for {agency}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching {agency} data: {str(e)}")
            return []

    async def _fetch_dod_data(self) -> List[Dict[str, Any]]:
        """Fetch DoD-specific grant data"""
        # Note: DoD doesn't have a public API, but we can get data from USAspending
        # filtered for DoD research programs
        
        try:
            dod_data = await self.fetch_usaspending_data(
                agency_codes=['097'],  # Department of Defense
                award_types=['B', 'C', 'D'],  # Cooperative Agreement, Block Grant, Project Grant
                limit=100
            )
            
            # Filter for research-related awards
            research_awards = []
            for award in dod_data:
                cfda_number = award.get('CFDA Number', '')
                award_description = award.get('Award Description', '') or ''  # Handle None values
                award_description_lower = award_description.lower()
                
                if (cfda_number in self.research_cfda_codes or
                    any(keyword in award_description_lower for keyword in 
                        ['research', 'science', 'development', 'innovation', 'technology'])):
                    
                    # Standardize the format
                    standardized_award = {
                        'award_id': award.get('Award ID', ''),
                        'recipient_name': award.get('Recipient Name', ''),
                        'award_amount': award.get('Award Amount', 0),
                        'start_date': award.get('Start Date', ''),
                        'end_date': award.get('End Date', ''),
                        'awarding_agency': 'Department of Defense',
                        'sub_agency': award.get('Awarding Sub Agency', ''),
                        'description': award.get('Award Description', ''),
                        'location': f"{award.get('Primary Place of Performance City', '')}, {award.get('Primary Place of Performance State', '')}",
                        'cfda_number': cfda_number,
                        'cfda_title': award.get('CFDA Title', ''),
                        'award_type': award.get('Award Type', ''),
                        'source': 'USAspending.gov (DoD)'
                    }
                    research_awards.append(standardized_award)
            
            logger.info(f"Retrieved {len(research_awards)} DoD research awards")
            return research_awards
            
        except Exception as e:
            logger.error(f"Error fetching DoD data: {str(e)}")
            return []

    async def _fetch_doe_data(self) -> List[Dict[str, Any]]:
        """Fetch DoE-specific grant data"""
        try:
            doe_data = await self.fetch_usaspending_data(
                agency_codes=['089'],  # Department of Energy
                award_types=['B', 'C', 'D'],  # Cooperative Agreement, Block Grant, Project Grant
                limit=100
            )
            
            # Filter and standardize DoE awards
            research_awards = []
            for award in doe_data:
                # DoE is primarily research-focused, so include most awards
                standardized_award = {
                    'award_id': award.get('Award ID', ''),
                    'recipient_name': award.get('Recipient Name', ''),
                    'award_amount': award.get('Award Amount', 0),
                    'start_date': award.get('Start Date', ''),
                    'end_date': award.get('End Date', ''),
                    'awarding_agency': 'Department of Energy',
                    'sub_agency': award.get('Awarding Sub Agency', ''),
                    'description': award.get('Award Description', ''),
                    'location': f"{award.get('Primary Place of Performance City', '')}, {award.get('Primary Place of Performance State', '')}",
                    'cfda_number': award.get('CFDA Number', ''),
                    'cfda_title': award.get('CFDA Title', ''),
                    'award_type': award.get('Award Type', ''),
                    'source': 'USAspending.gov (DoE)'
                }
                research_awards.append(standardized_award)
            
            logger.info(f"Retrieved {len(research_awards)} DoE awards")
            return research_awards
            
        except Exception as e:
            logger.error(f"Error fetching DoE data: {str(e)}")
            return []

    async def _fetch_nasa_data(self) -> List[Dict[str, Any]]:
        """Fetch NASA-specific grant data"""
        try:
            nasa_data = await self.fetch_usaspending_data(
                agency_codes=['080'],  # NASA
                award_types=['B', 'C', 'D'],  # Cooperative Agreement, Block Grant, Project Grant
                limit=100
            )
            
            # Standardize NASA awards
            research_awards = []
            for award in nasa_data:
                standardized_award = {
                    'award_id': award.get('Award ID', ''),
                    'recipient_name': award.get('Recipient Name', ''),
                    'award_amount': award.get('Award Amount', 0),
                    'start_date': award.get('Start Date', ''),
                    'end_date': award.get('End Date', ''),
                    'awarding_agency': 'National Aeronautics and Space Administration',
                    'sub_agency': award.get('Awarding Sub Agency', ''),
                    'description': award.get('Award Description', ''),
                    'location': f"{award.get('Primary Place of Performance City', '')}, {award.get('Primary Place of Performance State', '')}",
                    'cfda_number': award.get('CFDA Number', ''),
                    'cfda_title': award.get('CFDA Title', ''),
                    'award_type': award.get('Award Type', ''),
                    'source': 'USAspending.gov (NASA)'
                }
                research_awards.append(standardized_award)
            
            logger.info(f"Retrieved {len(research_awards)} NASA awards")
            return research_awards
            
        except Exception as e:
            logger.error(f"Error fetching NASA data: {str(e)}")
            return []

    async def get_comprehensive_federal_data(self, 
                                           agencies: List[str] = None,
                                           include_opportunities: bool = True,
                                           include_awards: bool = True) -> Dict[str, Any]:
        """
        Get comprehensive federal funding data from multiple sources
        
        Args:
            agencies: List of agencies to include (defaults to major research agencies)
            include_opportunities: Whether to include grant opportunities from Grants.gov
            include_awards: Whether to include award data from USAspending.gov
        """
        
        if not agencies:
            agencies = ['NSF', 'NIH', 'DOD', 'DOE', 'NASA']
        
        results = {
            'awards': [],
            'opportunities': [],
            'summary': {
                'total_agencies': len(agencies),
                'total_awards': 0,
                'total_opportunities': 0,
                'total_award_amount': 0,
                'data_sources': [],
                'generated_at': datetime.now().isoformat()
            }
        }
        
        try:
            # Fetch award data if requested
            if include_awards:
                logger.info("Fetching comprehensive award data...")
                
                # Get USAspending data for all requested agencies
                all_agency_codes = []
                for agency in agencies:
                    if agency.upper() == 'NSF':
                        all_agency_codes.append('020')
                    elif agency.upper() in ['NIH', 'HHS']:
                        all_agency_codes.append('075')
                    elif agency.upper() == 'DOD':
                        all_agency_codes.append('097')
                    elif agency.upper() == 'DOE':
                        all_agency_codes.append('089')
                    elif agency.upper() == 'NASA':
                        all_agency_codes.append('080')
                
                if all_agency_codes:
                    usaspending_awards = await self.fetch_usaspending_data(
                        agency_codes=all_agency_codes,
                        limit=5000
                    )
                    results['awards'].extend(usaspending_awards)
                    results['summary']['data_sources'].append('USAspending.gov')
                
                # Get agency-specific data
                for agency in agencies:
                    if agency.upper() in ['DOD', 'DOE', 'NASA']:
                        agency_awards = await self.fetch_agency_specific_data(agency)
                        results['awards'].extend(agency_awards)
            
            # Fetch opportunities data if requested
            if include_opportunities:
                logger.info("Fetching grant opportunities...")
                opportunities = await self.fetch_grants_gov_xml()
                results['opportunities'] = opportunities
                results['summary']['data_sources'].append('Grants.gov XML Extract')
            
            # Calculate summary statistics
            results['summary']['total_awards'] = len(results['awards'])
            results['summary']['total_opportunities'] = len(results['opportunities'])
            
            # Calculate total award amount
            total_amount = 0
            for award in results['awards']:
                amount = award.get('Award Amount', 0) or award.get('award_amount', 0)
                if isinstance(amount, (int, float)):
                    total_amount += amount
                elif isinstance(amount, str):
                    try:
                        total_amount += float(amount.replace(',', '').replace('$', ''))
                    except:
                        pass
            
            results['summary']['total_award_amount'] = total_amount
            
            # Add recipient analysis
            if results['awards']:
                logger.info("Analyzing award recipients...")
                recipient_analysis = self.analyze_award_recipients(results['awards'])
                results['recipient_analysis'] = recipient_analysis
            
            logger.info(f"Comprehensive federal data retrieval complete:")
            logger.info(f"  - {results['summary']['total_awards']} awards")
            logger.info(f"  - {results['summary']['total_opportunities']} opportunities")
            logger.info(f"  - ${results['summary']['total_award_amount']:,.2f} total award amount")
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting comprehensive federal data: {str(e)}")
            results['error'] = str(e)
            return results

    def normalize_institution_name(self, institution_name: str) -> str:
        """Normalize institution names for consistent matching"""
        if not institution_name:
            return ""
        
        # Convert to lowercase and remove extra whitespace
        normalized = institution_name.lower().strip()
        
        # Remove common organizational suffixes and prefixes first
        prefixes_to_remove = [
            'the ', 'regents of the ', 'trustees of ', 'board of regents ',
            'president and fellows of ', 'curators of the '
        ]
        
        suffixes_to_remove = [
            ', inc', ', incorporated', ' inc', ' incorporated',
            ', llc', ' llc', ', ltd', ' ltd', ', the'
        ]
        
        for prefix in prefixes_to_remove:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):]
        
        for suffix in suffixes_to_remove:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)]
        
        # Clean up extra spaces after prefix/suffix removal
        normalized = ' '.join(normalized.split())
        
        # Handle UC system consolidation first (before other substitutions)
        uc_patterns = [
            'regents of the university of california',
            'regents of university of california', 
            'the regents of the university of california',
            'university of california system',
            'regents of the univ of california',
            'regents university of california'
        ]
        
        for pattern in uc_patterns:
            if pattern in normalized:
                normalized = normalized.replace(pattern, 'uc system')
        
        # Common substitutions for consistency
        substitutions = {
            # Full university names to standard forms (most specific first)
            'massachusetts institute of technology': 'mit',
            'california institute of technology': 'caltech',
            'georgia institute of technology': 'georgia tech',
            'virginia polytechnic institute and state university': 'virginia tech',
            'texas a&m university': 'texas a&m',
            'pennsylvania state university': 'penn state',
            'ohio state university': 'ohio state',
            'arizona state university': 'arizona state',
            'michigan state university': 'michigan state',
            'florida state university': 'florida state',
            'north carolina state university': 'nc state',
            'washington university in st. louis': 'washington univ st louis',
            
            # University of California system normalization (specific campuses)
            'university of california, berkeley': 'uc berkeley',
            'university of california, los angeles': 'ucla',
            'university of california, san diego': 'uc san diego',
            'university of california, santa barbara': 'uc santa barbara',
            'university of california, irvine': 'uc irvine',
            'university of california, davis': 'uc davis',
            'university of california, santa cruz': 'uc santa cruz',
            'university of california, riverside': 'uc riverside',
            'university of california, merced': 'uc merced',
            'university of california, san francisco': 'ucsf',
            
            # State university systems
            'university of texas at austin': 'ut austin',
            'university of texas at dallas': 'ut dallas',
            'university of texas at arlington': 'ut arlington',
            'board of regents of the university of texas system': 'ut system',
            'university of michigan': 'univ michigan',
            'university of wisconsin': 'univ wisconsin',
            'university of illinois': 'univ illinois',
            'university of florida': 'univ florida',
            'university of georgia': 'univ georgia',
            'university of north carolina': 'unc',
            'university of virginia': 'univ virginia',
            'university of washington': 'univ washington',
            'university of pennsylvania': 'upenn',
            'university of southern california': 'usc',
            
            # Trustee and governance patterns
            'president and fellows of harvard college': 'harvard',
            'trustees of columbia university in the city of new york': 'columbia',
            'trustees of princeton university': 'princeton',
            'trustees of the university of pennsylvania': 'upenn',
            'leland stanford junior university': 'stanford',
            
            # Common abbreviations
            'university': 'univ',
            'college': 'college',
            'institute of technology': 'tech',
            'institute': 'inst',
            'school of medicine': 'medical school',
            'medical college': 'medical college',
            'health sciences center': 'health sciences',
            
            # Remove common words for better matching
            ' and ': ' ',
            ' & ': ' ',
            ' at ': ' ',
            ' in ': ' ',
            ' of ': ' ',
            ' for ': ' ',
            ' the ': ' ',
        }
        
        # Apply substitutions in order of specificity (most specific first)
        for full_form, abbrev in substitutions.items():
            normalized = normalized.replace(full_form, abbrev)
        
        # Clean up extra spaces
        normalized = ' '.join(normalized.split())
        
        return normalized

    def is_research_institution(self, recipient_name: str) -> bool:
        """Determine if a recipient is a research institution (university/college)"""
        if not recipient_name:
            return False
        
        recipient_lower = recipient_name.lower()
        
        # University keywords that indicate research institutions - check these FIRST
        university_keywords = [
            'university', 'college', 'institute of technology', 'school of medicine',
            'regents of', 'trustees of', 'board of regents', 'curators of',
            'president and fellows', 'medical school', 'law school',
            'dental school', 'veterinary school', 'graduate school', 
            'business school', 'engineering school', 'medical college',
            'community college', 'state college', 'technical college'
        ]
        
        # Check for university keywords first
        is_likely_university = False
        for keyword in university_keywords:
            if keyword in recipient_lower:
                is_likely_university = True
                break
        
        # If no university keywords found, check specific institutions
        if not is_likely_university:
            prestigious_patterns = [
                'mit', 'caltech', 'stanford', 'harvard', 'yale', 'princeton',
                'columbia', 'cornell', 'dartmouth', 'brown', 'upenn',
                'carnegie mellon', 'duke', 'northwestern', 'vanderbilt',
                'emory', 'rice', 'johns hopkins', 'washington university',
                'georgia tech', 'virginia tech', 'texas a&m'
            ]
            
            for institution in prestigious_patterns:
                if institution in recipient_lower:
                    is_likely_university = True
                    break
        
        # If still not identified as university, check patterns
        if not is_likely_university:
            university_patterns = [
                'univ of', 'univ at', 'state univ', 'univ system',
                'college of', 'institute for', 'school for'
            ]
            
            for pattern in university_patterns:
                if pattern in recipient_lower:
                    is_likely_university = True
                    break
        
        # If we haven't identified it as a university by now, it's probably not one
        if not is_likely_university:
            return False
        
        # Now check exclusions - but only for edge cases where university keywords might be misleading
        # These are more specific exclusions for entities that might have "university" in name but aren't actually universities
        specific_exclusions = [
            'pricewaterhousecoopers', 'deloitte', 'kpmg', 'ernst', 'young',
            'glaxosmithkline', 'pfizer', 'merck', 'johnson', 'roche',
            'lockheed martin', 'boeing', 'raytheon', 'northrop grumman',
            'general dynamics', 'honeywell', 'ibm', 'microsoft', 'google',
            'apple', 'amazon', 'facebook', 'meta', 'oracle', 'cisco',
            'national laboratory', 'national lab', 'brookhaven', 'argonne', 
            'oak ridge', 'lawrence', 'sandia', 'los alamos', 'battelle'
        ]
        
        # Check if it's a known non-university entity
        for exclusion in specific_exclusions:
            if exclusion in recipient_lower:
                return False
        
        # Check for corporate endings that might indicate it's not a university
        # Only exclude if it has these AND doesn't have clear university indicators
        corporate_endings = [' inc.', ' inc ', ' llc', ' ltd', ' corp.', ' corp ']
        has_corporate_ending = any(ending in recipient_lower for ending in corporate_endings)
        
        if has_corporate_ending:
            # Allow university corporations and research corporations
            university_corp_patterns = [
                'university corporation', 'research corporation', 'educational corporation',
                'college corporation', 'institute corporation', 'academic corporation'
            ]
            
            is_university_corp = any(pattern in recipient_lower for pattern in university_corp_patterns)
            if not is_university_corp:
                # If it has a corporate ending but no clear university corporation pattern,
                # and if it doesn't have strong university indicators, exclude it
                strong_university_indicators = [
                    'trustees of', 'regents of', 'board of regents', 'curators of',
                    'president and fellows', 'university of', 'college of'
                ]
                has_strong_indicator = any(indicator in recipient_lower for indicator in strong_university_indicators)
                if not has_strong_indicator:
                    return False
        
        return True

    def filter_university_awards(self, awards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter awards to only include those going to universities and research institutions"""
        university_awards = []
        
        for award in awards:
            recipient = award.get('Recipient Name', '') or award.get('recipient_name', '')
            
            if self.is_research_institution(recipient):
                # Add normalized name to the award data
                award_copy = award.copy()
                award_copy['normalized_recipient_name'] = self.normalize_institution_name(recipient)
                university_awards.append(award_copy)
        
        return university_awards

    def analyze_award_recipients(self, awards: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze recipient patterns in award data, focusing only on universities"""
        from collections import Counter, defaultdict
        
        if not awards:
            return {"error": "No awards to analyze"}
        
        # Filter to only university awards
        university_awards = self.filter_university_awards(awards)
        
        if not university_awards:
            return {
                "error": "No university awards found",
                "total_awards_checked": len(awards),
                "university_awards_found": 0
            }
        
        # Initialize counters for universities only
        recipients = Counter()
        normalized_recipients = Counter()
        recipient_amounts = defaultdict(float)
        normalized_amounts = defaultdict(float)
        locations = Counter()
        naics_codes = Counter()
        award_types_counter = Counter()
        
        # Track university details
        universities = []
        university_name_mapping = {}  # Maps normalized names to original names
        
        for award in university_awards:
            recipient = award.get('Recipient Name', '') or award.get('recipient_name', 'Unknown')
            normalized_name = award.get('normalized_recipient_name', '') or self.normalize_institution_name(recipient)
            amount = award.get('Award Amount', 0) or award.get('award_amount', 0)
            
            # Handle different amount formats
            if isinstance(amount, str):
                try:
                    amount = float(amount.replace(',', '').replace('$', ''))
                except:
                    amount = 0
            
            location = f"{award.get('Recipient City Name', '') or award.get('Primary Place of Performance City', '')}, {award.get('Recipient State Code', '') or award.get('Primary Place of Performance State', '')}"
            naics = award.get('NAICS Description', 'Unknown')
            award_type = award.get('Award Type', 'Unknown')
            
            # Count by original and normalized names
            recipients[recipient] += 1
            normalized_recipients[normalized_name] += 1
            recipient_amounts[recipient] += amount
            normalized_amounts[normalized_name] += amount
            
            locations[location] += 1
            naics_codes[naics] += 1
            award_types_counter[award_type] += 1
            
            # Track name mapping (use the most recent/complete name)
            if normalized_name not in university_name_mapping or len(recipient) > len(university_name_mapping[normalized_name]):
                university_name_mapping[normalized_name] = recipient
            
            # Add to universities list
            universities.append({
                'name': recipient,
                'normalized_name': normalized_name,
                'amount': amount,
                'location': location,
                'naics': naics,
                'award_type': award_type,
                'award_id': award.get('Award ID', '') or award.get('award_id', ''),
                'start_date': award.get('Start Date', '') or award.get('start_date', ''),
                'end_date': award.get('End Date', '') or award.get('end_date', ''),
                'description': award.get('Award Description', '') or award.get('description', '')
            })
        
        # Sort universities by amount
        universities.sort(key=lambda x: x['amount'], reverse=True)
        
        # Calculate totals
        total_amount = sum(recipient_amounts.values())
        total_normalized_amount = sum(normalized_amounts.values())
        
        # Create consolidated university rankings
        consolidated_universities = []
        for norm_name, total_amount_norm in sorted(normalized_amounts.items(), key=lambda x: x[1], reverse=True):
            original_name = university_name_mapping[norm_name]
            award_count = normalized_recipients[norm_name]
            
            # Find representative award details
            representative_award = next((u for u in universities if u['normalized_name'] == norm_name), {})
            
            consolidated_universities.append({
                'normalized_name': norm_name,
                'display_name': original_name,
                'total_amount': total_amount_norm,
                'award_count': award_count,
                'average_award': total_amount_norm / award_count if award_count > 0 else 0,
                'location': representative_award.get('location', ''),
                'percentage_of_total': (total_amount_norm / total_normalized_amount * 100) if total_normalized_amount > 0 else 0
            })
        
        analysis = {
            'summary': {
                'total_awards_analyzed': len(awards),
                'university_awards_found': len(university_awards),
                'unique_universities_original': len(recipients),
                'unique_universities_normalized': len(normalized_recipients),
                'total_amount': total_amount,
                'average_award_amount': total_amount / len(university_awards) if university_awards else 0,
                'consolidation_ratio': f"{len(recipients)} → {len(normalized_recipients)} ({((len(recipients) - len(normalized_recipients)) / len(recipients) * 100):.1f}% reduction)" if recipients else "N/A"
            },
            'top_universities': {
                'by_total_amount_normalized': consolidated_universities[:15],
                'by_award_count_normalized': sorted(
                    consolidated_universities, 
                    key=lambda x: x['award_count'], 
                    reverse=True
                )[:15],
                'by_average_award_size': sorted(
                    [u for u in consolidated_universities if u['award_count'] >= 2],  # At least 2 awards for meaningful average
                    key=lambda x: x['average_award'], 
                    reverse=True
                )[:15]
            },
            'geographic_distribution': {
                'top_locations': locations.most_common(15),
                'state_summary': self._summarize_by_state(universities)
            },
            'research_areas': naics_codes.most_common(10),
            'award_types': dict(award_types_counter),
            'name_normalization_examples': {
                'before_after': [(university_name_mapping[norm], norm) for norm in list(normalized_recipients.keys())[:10]],
                'consolidation_examples': self._find_consolidation_examples(recipients, normalized_recipients, university_name_mapping)
            }
        }
        
        return analysis

    def _summarize_by_state(self, universities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Summarize university awards by state"""
        from collections import defaultdict
        
        state_data = defaultdict(lambda: {'count': 0, 'total_amount': 0, 'universities': set()})
        
        for univ in universities:
            location = univ.get('location', '')
            if ', ' in location:
                state = location.split(', ')[-1].strip()
                if state and len(state) <= 3:  # Valid state code
                    state_data[state]['count'] += 1
                    state_data[state]['total_amount'] += univ.get('amount', 0)
                    state_data[state]['universities'].add(univ.get('normalized_name', ''))
        
        # Convert to regular dict and sort
        state_summary = []
        for state, data in state_data.items():
            state_summary.append({
                'state': state,
                'award_count': data['count'],
                'total_amount': data['total_amount'],
                'university_count': len(data['universities']),
                'avg_award': data['total_amount'] / data['count'] if data['count'] > 0 else 0
            })
        
        return sorted(state_summary, key=lambda x: x['total_amount'], reverse=True)

    def _find_consolidation_examples(self, original_recipients: Counter, normalized_recipients: Counter, name_mapping: Dict[str, str]) -> List[Dict[str, Any]]:
        """Find examples where multiple original names were consolidated into one normalized name"""
        consolidation_examples = []
        
        # Find normalized names that represent multiple original names
        normalized_to_originals = defaultdict(list)
        for norm_name in normalized_recipients.keys():
            for orig_name in original_recipients.keys():
                if self.normalize_institution_name(orig_name) == norm_name:
                    normalized_to_originals[norm_name].append(orig_name)
        
        # Find cases where multiple originals map to one normalized
        for norm_name, orig_names in normalized_to_originals.items():
            if len(orig_names) > 1:
                consolidation_examples.append({
                    'normalized_name': norm_name,
                    'original_names': orig_names,
                    'count_consolidated': len(orig_names),
                    'total_amount': sum(original_recipients[name] for name in orig_names)
                })
        
        return sorted(consolidation_examples, key=lambda x: x['count_consolidated'], reverse=True)[:5]

# Example usage and testing
async def main():
    """Example usage of the Federal Agency Integrator"""
    integrator = FederalAgencyIntegrator()
    
    # Get comprehensive data from major research agencies
    print("Fetching comprehensive federal funding data...")
    data = await integrator.get_comprehensive_federal_data(
        agencies=['NSF', 'NIH', 'DOD', 'DOE', 'NASA'],
        include_opportunities=True,
        include_awards=True
    )
    
    print(f"Retrieved data summary:")
    print(f"  Awards: {data['summary']['total_awards']}")
    print(f"  Opportunities: {data['summary']['total_opportunities']}")
    print(f"  Total Award Amount: ${data['summary']['total_award_amount']:,.2f}")
    print(f"  Data Sources: {', '.join(data['summary']['data_sources'])}")

if __name__ == "__main__":
    asyncio.run(main())
