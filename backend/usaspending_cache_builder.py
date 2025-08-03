#!/usr/bin/env python3
"""
USASpending.gov Data Cache Builder

This script comprehensively scrapes USASpending.gov for university research funding
and saves it to a cache file to eliminate $0 funding issues.
"""

import requests
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any
import time

class USASpendingCacheBuilder:
    def __init__(self):
        self.base_url = "https://api.usaspending.gov/api/v2"
        self.cache_dir = "grant_cache"
        self.cache_file = os.path.join(self.cache_dir, "usaspending_university_funding.json")
        
        # Ensure cache directory exists
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Research-focused agencies with correct names for USASpending API
        self.research_agencies = [
            "National Science Foundation",
            "Department of Health and Human Services", 
            "Department of Defense",
            "Department of Energy",
            "National Aeronautics and Space Administration",
            "Department of Agriculture",
            "Department of Education",
            "Environmental Protection Agency"
        ]
        
        # Correct award type codes for university research grants
        self.grant_award_types = ["04", "05"]  # Project Grant, Cooperative Agreement
        
        # University keywords for filtering
        self.university_keywords = [
            'UNIVERSITY', 'COLLEGE', 'INSTITUTE', 'SCHOOL', 'MEDICAL CENTER',
            'RESEARCH FOUNDATION', 'ACADEMIC', 'EDUCATION', 'CAMPUS'
        ]

    def fetch_agency_grants(self, agency_name: str, page: int = 1) -> List[Dict]:
        """Fetch grants for a specific agency"""
        endpoint = f"{self.base_url}/search/spending_by_award"
        
        payload = {
            "filters": {
                "award_type_codes": self.grant_award_types,
                "agencies": [{
                    "type": "awarding",
                    "tier": "toptier", 
                    "name": agency_name
                }],
                "time_period": [{
                    "start_date": "2020-01-01",
                    "end_date": "2024-12-31"
                }]
            },
            "fields": [
                "Award ID", "Recipient Name", "Award Amount", "Start Date", "End Date",
                "Awarding Agency", "Awarding Sub Agency", "Award Description", 
                "Recipient State Code", "Recipient City Name", "Award Type",
                "NAICS Code", "NAICS Description", "Primary Place of Performance State"
            ],
            "page": page,
            "limit": 100,  # Max limit
            "sort": "Award Amount",
            "order": "desc"
        }
        
        try:
            response = requests.post(endpoint, json=payload, timeout=30)
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                
                # Filter for universities only
                university_grants = []
                for grant in results:
                    recipient = grant.get('Recipient Name', '').upper()
                    if any(keyword in recipient for keyword in self.university_keywords):
                        # Add metadata
                        grant['data_source'] = 'USASpending.gov'
                        grant['agency_normalized'] = agency_name
                        grant['fetched_at'] = datetime.now().isoformat()
                        university_grants.append(grant)
                
                print(f"  {agency_name} page {page}: {len(results)} total, {len(university_grants)} universities")
                return university_grants
            else:
                print(f"  Error fetching {agency_name} page {page}: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"  Exception fetching {agency_name} page {page}: {e}")
            return []

    def fetch_all_agency_pages(self, agency_name: str, max_pages: int = 10) -> List[Dict]:
        """Fetch multiple pages for an agency"""
        all_grants = []
        
        print(f"Fetching {agency_name} grants...")
        
        for page in range(1, max_pages + 1):
            grants = self.fetch_agency_grants(agency_name, page)
            
            if not grants:  # No more data
                break
                
            all_grants.extend(grants)
            
            # Rate limiting
            time.sleep(0.5)
            
        print(f"  Total {agency_name} university grants: {len(all_grants)}")
        return all_grants

    def scrape_all_agencies(self, max_pages_per_agency: int = 20) -> Dict[str, Any]:
        """Scrape all research agencies for university funding"""
        
        print("=== USASpending.gov University Funding Scraper ===")
        print(f"Target agencies: {len(self.research_agencies)}")
        print(f"Award types: {self.grant_award_types} (Project Grant, Cooperative Agreement)")
        print(f"Max pages per agency: {max_pages_per_agency}")
        print()
        
        all_university_grants = []
        agency_stats = {}
        
        for agency in self.research_agencies:
            start_time = time.time()
            
            agency_grants = self.fetch_all_agency_pages(
                agency, max_pages_per_agency
            )
            
            all_university_grants.extend(agency_grants)
            
            # Calculate agency statistics
            total_funding = sum(grant.get('Award Amount', 0) or 0 for grant in agency_grants)
            agency_stats[agency] = {
                'grants_count': len(agency_grants),
                'total_funding': total_funding,
                'avg_grant_size': total_funding / len(agency_grants) if agency_grants else 0,
                'fetch_time_seconds': round(time.time() - start_time, 2)
            }
            
            print(f"  {agency}: {len(agency_grants)} grants, ${total_funding:,.0f} total")
            print()
        
        # Process and deduplicate grants
        unique_grants = {}
        for grant in all_university_grants:
            award_id = grant.get('Award ID', '')
            recipient = grant.get('Recipient Name', '')
            key = f"{award_id}_{recipient}"
            
            if key not in unique_grants:
                unique_grants[key] = grant
            else:
                # Keep the one with higher amount
                if (grant.get('Award Amount', 0) or 0) > (unique_grants[key].get('Award Amount', 0) or 0):
                    unique_grants[key] = grant
        
        final_grants = list(unique_grants.values())
        
        # Calculate institution aggregations
        institution_funding = {}
        for grant in final_grants:
            recipient = grant.get('Recipient Name', '')
            amount = grant.get('Award Amount', 0) or 0
            agency = grant.get('agency_normalized', 'Unknown')
            
            if recipient not in institution_funding:
                institution_funding[recipient] = {
                    'total_funding': 0,
                    'grants_count': 0,
                    'agencies': set(),
                    'nih_funding': 0,
                    'nsf_funding': 0,
                    'dod_funding': 0,
                    'doe_funding': 0,
                    'nasa_funding': 0,
                    'other_funding': 0
                }
            
            institution_funding[recipient]['total_funding'] += amount
            institution_funding[recipient]['grants_count'] += 1
            institution_funding[recipient]['agencies'].add(agency)
            
            # Categorize by agency
            if 'Health' in agency:
                institution_funding[recipient]['nih_funding'] += amount
            elif 'Science Foundation' in agency:
                institution_funding[recipient]['nsf_funding'] += amount
            elif 'Defense' in agency:
                institution_funding[recipient]['dod_funding'] += amount
            elif 'Energy' in agency:
                institution_funding[recipient]['doe_funding'] += amount
            elif 'NASA' in agency:
                institution_funding[recipient]['nasa_funding'] += amount
            else:
                institution_funding[recipient]['other_funding'] += amount
        
        # Convert sets to lists for JSON serialization
        for inst_data in institution_funding.values():
            inst_data['agencies'] = list(inst_data['agencies'])
        
        # Create comprehensive cache data
        cache_data = {
            'metadata': {
                'created_at': datetime.now().isoformat(),
                'total_grants': len(final_grants),
                'total_institutions': len(institution_funding),
                'agencies_scraped': self.research_agencies,
                'award_types': self.grant_award_types,
                'time_period': '2020-2024',
                'total_funding': sum(grant.get('Award Amount', 0) or 0 for grant in final_grants)
            },
            'agency_statistics': agency_stats,
            'grants': final_grants,
            'institution_aggregations': institution_funding
        }
        
        return cache_data

    def save_cache(self, cache_data: Dict[str, Any]):
        """Save cache data to file"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2, default=str)
            
            print(f"✅ Cache saved to: {self.cache_file}")
            print(f"   Total grants: {cache_data['metadata']['total_grants']:,}")
            print(f"   Total institutions: {cache_data['metadata']['total_institutions']:,}")
            print(f"   Total funding: ${cache_data['metadata']['total_funding']:,.0f}")
            
        except Exception as e:
            print(f"❌ Error saving cache: {e}")

    def load_cache(self) -> Dict[str, Any]:
        """Load cache data from file"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            return None
        except Exception as e:
            print(f"Error loading cache: {e}")
            return None

    def get_institution_funding(self, institution_name: str) -> Dict[str, Any]:
        """Get funding data for a specific institution"""
        cache_data = self.load_cache()
        if not cache_data:
            return None
        
        # Normalize institution name for lookup
        normalized_name = institution_name.upper()
        
        # Search in institution aggregations
        for inst_name, funding_data in cache_data.get('institution_aggregations', {}).items():
            if normalized_name in inst_name.upper():
                return {
                    'institution': inst_name,
                    'funding_data': funding_data,
                    'raw_grants': [
                        grant for grant in cache_data.get('grants', [])
                        if normalized_name in grant.get('Recipient Name', '').upper()
                    ]
                }
        
        return None

    def build_comprehensive_cache(self):
        """Main method to build comprehensive cache"""
        print("Building comprehensive USASpending.gov cache...")
        
        cache_data = self.scrape_all_agencies(max_pages_per_agency=25)
        self.save_cache(cache_data)
        
        # Print summary statistics
        print("\n=== CACHE SUMMARY ===")
        print(f"Total university grants cached: {cache_data['metadata']['total_grants']:,}")
        print(f"Total funding amount: ${cache_data['metadata']['total_funding']:,.0f}")
        print(f"Universities with funding: {cache_data['metadata']['total_institutions']:,}")
        
        print("\nTop 10 institutions by funding:")
        sorted_institutions = sorted(
            cache_data['institution_aggregations'].items(),
            key=lambda x: x[1]['total_funding'],
            reverse=True
        )
        
        for i, (institution, data) in enumerate(sorted_institutions[:10]):
            print(f"{i+1:2d}. {institution[:60]:<60} ${data['total_funding']:>15,.0f}")
        
        print("\nAgency breakdown:")
        for agency, stats in cache_data['agency_statistics'].items():
            print(f"  {agency}: {stats['grants_count']} grants, ${stats['total_funding']:,.0f}")

def main():
    """Main execution function"""
    builder = USASpendingCacheBuilder()
    builder.build_comprehensive_cache()

if __name__ == "__main__":
    main()
