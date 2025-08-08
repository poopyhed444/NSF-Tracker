#!/usr/bin/env python3
"""
Enhanced Async Cache Builder for NSF-Tracker

This script builds comprehensive grant caches by scraping data from:
- NIH Reporter API (comprehensive research grants)
- NSF Awards API (comprehensive NSF grants)
- USASpending.gov API (federal agency grants)

Features:
- Async/concurrent data fetching for performance
- Comprehensive university filtering
- Large-scale data collection (50K+ grants)
- Institution-specific caching
- Duplicate detection and deduplication
- Progress tracking and error handling
"""

import asyncio
import httpx
import json
import os
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Set
from collections import defaultdict
import re

# Import existing cache functions
from grant_cache import save_nih_cache, save_nsf_cache, save_combined_cache, CACHE_DIR
from layoff_estimator import _map_nsf_to_nih_format, _extract_fiscal_year, _format_nsf_date

class EnhancedCacheBuilder:
    """Enhanced async cache builder for comprehensive grant data."""
    
    def __init__(self):
        self.nih_api_url = "https://api.reporter.nih.gov/v2/projects/search"
        self.nsf_api_url = "https://www.research.gov/awardapi-service/v1/awards.json"
        
        # University keywords for filtering
        self.university_keywords = [
            "University", "College", "Institute", "School", "Academy",
            "Hospital", "Medical Center", "Health System", "Foundation",
            "Research", "Center", "Laboratory", "Clinic"
        ]
        
        # Track progress
        self.total_grants = 0
        self.nih_grants = 0
        self.nsf_grants = 0
        self.institutions = set()
        
    def is_university(self, org_name: str) -> bool:
        """Check if organization name indicates a university/research institution."""
        if not org_name:
            return False
            
        org_name = org_name.upper()
        
        # Direct university indicators
        university_indicators = [
            "UNIVERSITY", "COLLEGE", "INSTITUTE", "SCHOOL",
            "HOSPITAL", "MEDICAL CENTER", "HEALTH SYSTEM",
            "RESEARCH", "LABORATORY", "CLINIC"
        ]
        
        # Exclude non-research entities
        exclusions = [
            "CORPORATION", "LLC", "INC", "COMPANY", "CONSULTING",
            "SERVICES", "GOVERNMENT", "FEDERAL", "DEPARTMENT",
            "ADMINISTRATION", "AGENCY", "BUREAU", "OFFICE"
        ]
        
        # Check for university indicators
        has_university_indicator = any(indicator in org_name for indicator in university_indicators)
        
        # Check for exclusions
        has_exclusion = any(exclusion in org_name for exclusion in exclusions)
        
        return has_university_indicator and not has_exclusion
    
    async def fetch_nih_grants_comprehensive(self, max_records: int = 25000) -> List[Dict[str, Any]]:
        """Fetch comprehensive NIH grants with university filtering."""
        print(f"🔬 Fetching comprehensive NIH grants (target: {max_records:,})...")
        
        all_grants = []
        batch_size = 500
        offset = 0
        
        # Search criteria for comprehensive data
        search_criteria = {
            "criteria": {
                "advanced_text_search": {
                    "operator": "advanced",
                    "search_field": "all",
                    "search_text": ""
                },
                "fiscal_years": [2020, 2021, 2022, 2023, 2024, 2025],
                "project_types": ["RESEARCH", "TRAINING", "CAREER", "OTHER_RESEARCH"]
            },
            "include_fields": [
                "AwardAmount", "ContactPiName", "ProjectTitle", "ProjectStartDate",
                "ProjectEndDate", "Organization", "FiscalYear", "FundingICs",
                "ActivityCode", "AwardNoticeDate", "ProjectNum", "FullStudySection"
            ],
            "offset": offset,
            "limit": batch_size,
            "sort_field": "award_amount",
            "sort_order": "desc"
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            while len(all_grants) < max_records:
                current_batch_size = min(batch_size, max_records - len(all_grants))
                search_criteria["limit"] = current_batch_size
                search_criteria["offset"] = offset
                
                try:
                    print(f"  📥 Fetching NIH batch {offset//batch_size + 1} (offset {offset})...")
                    response = await client.post(self.nih_api_url, json=search_criteria)
                    response.raise_for_status()
                    data = response.json()
                    
                    batch_results = data.get("results", [])
                    if not batch_results:
                        print(f"  ✅ No more NIH results at offset {offset}")
                        break
                    
                    # Filter for universities only
                    university_grants = []
                    for grant in batch_results:
                        org_info = grant.get("organization", {})
                        if isinstance(org_info, list) and len(org_info) > 0:
                            org_name = org_info[0].get("org_name", "")
                        elif isinstance(org_info, dict):
                            org_name = org_info.get("org_name", "")
                        else:
                            continue
                            
                        if self.is_university(org_name):
                            grant["funding_agency"] = "NIH"
                            grant["source"] = "NIH Reporter API"
                            university_grants.append(grant)
                            self.institutions.add(org_name)
                    
                    all_grants.extend(university_grants)
                    print(f"  ✅ Added {len(university_grants)} university grants (total: {len(all_grants):,})")
                    
                    # If we got fewer results than requested, we've reached the end
                    if len(batch_results) < current_batch_size:
                        break
                    
                    offset += batch_size
                    
                    # Small delay to be respectful to the API
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    print(f"  ❌ Error fetching NIH grants at offset {offset}: {e}")
                    break
        
        self.nih_grants = len(all_grants)
        print(f"🎯 NIH grants collected: {len(all_grants):,} from {len(self.institutions)} institutions")
        return all_grants
    
    async def fetch_nsf_grants_comprehensive(self, max_records: int = 25000) -> List[Dict[str, Any]]:
        """Fetch comprehensive NSF grants with university filtering."""
        print(f"🧪 Fetching comprehensive NSF grants (target: {max_records:,})...")
        
        all_grants = []
        batch_size = 500
        offset = 1  # NSF uses 1-based indexing
        
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            while len(all_grants) < max_records:
                current_batch_size = min(batch_size, max_records - len(all_grants))
                
                # Build comprehensive query parameters
                params = {
                    "printFields": "id,title,startDate,expDate,fundsObligatedAmt,awardeeName,pdPIName,agency,fundProgramName,abstractText,publicationResearch,awardee",
                    "offset": str(offset),
                    "rpp": str(current_batch_size),
                    # Include recent grants (last 5 years)
                    "startDateStart": "01/01/2020",
                    "expDateStart": datetime.now().strftime("%m/%d/%Y")  # Not yet expired
                }
                
                try:
                    print(f"  📥 Fetching NSF batch {(offset-1)//batch_size + 1} (offset {offset})...")
                    response = await client.get(self.nsf_api_url, params=params)
                    response.raise_for_status()
                    data = response.json()
                    
                    nsf_awards = data.get("response", {}).get("award", [])
                    if not nsf_awards:
                        print(f"  ✅ No more NSF results at offset {offset}")
                        break
                    
                    # Filter for universities and map to NIH format
                    university_grants = []
                    for award in nsf_awards:
                        awardee = award.get("awardeeName", "") or award.get("awardee", "")
                        
                        if self.is_university(awardee):
                            mapped_grant = _map_nsf_to_nih_format(award)
                            if mapped_grant:
                                mapped_grant["funding_agency"] = "NSF"
                                mapped_grant["source"] = "NSF Awards API"
                                university_grants.append(mapped_grant)
                                self.institutions.add(awardee)
                    
                    all_grants.extend(university_grants)
                    print(f"  ✅ Added {len(university_grants)} university grants (total: {len(all_grants):,})")
                    
                    # If we got fewer results than requested, we've reached the end
                    if len(nsf_awards) < current_batch_size:
                        break
                    
                    offset += batch_size
                    
                    # Small delay to be respectful to the API
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    print(f"  ❌ Error fetching NSF grants at offset {offset}: {e}")
                    break
        
        self.nsf_grants = len(all_grants)
        print(f"🎯 NSF grants collected: {len(all_grants):,} from {len(self.institutions)} institutions")
        return all_grants
    
    def deduplicate_grants(self, grants: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate grants based on award ID and organization."""
        print("🔍 Deduplicating grants...")
        
        unique_grants = {}
        duplicates_removed = 0
        
        for grant in grants:
            # Create unique key from award info
            award_id = ""
            if "project_num" in grant:
                award_id = grant["project_num"]
            elif "Award ID" in grant:
                award_id = grant["Award ID"]
            elif "id" in grant:
                award_id = str(grant["id"])
            
            org_name = ""
            org_info = grant.get("organization", {})
            if isinstance(org_info, list) and len(org_info) > 0:
                org_name = org_info[0].get("org_name", "")
            elif isinstance(org_info, dict):
                org_name = org_info.get("org_name", "")
            
            key = f"{award_id}_{org_name}_{grant.get('funding_agency', '')}"
            
            if key not in unique_grants:
                unique_grants[key] = grant
            else:
                duplicates_removed += 1
                # Keep the one with higher award amount
                current_amount = float(grant.get("award_amount", 0) or 0)
                existing_amount = float(unique_grants[key].get("award_amount", 0) or 0)
                if current_amount > existing_amount:
                    unique_grants[key] = grant
        
        final_grants = list(unique_grants.values())
        print(f"🎯 Deduplication complete: {duplicates_removed:,} duplicates removed, {len(final_grants):,} unique grants")
        return final_grants
    
    def generate_institution_stats(self, grants: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate comprehensive institution statistics."""
        print("📊 Generating institution statistics...")
        
        institution_data = defaultdict(lambda: {
            "total_grants": 0,
            "total_funding": 0,
            "nih_grants": 0,
            "nih_funding": 0,
            "nsf_grants": 0,
            "nsf_funding": 0,
            "agencies": set(),
            "departments": set(),
            "pis": set()
        })
        
        for grant in grants:
            # Extract organization name
            org_name = ""
            org_info = grant.get("organization", {})
            if isinstance(org_info, list) and len(org_info) > 0:
                org_name = org_info[0].get("org_name", "")
                dept = org_info[0].get("org_dept", "")
            elif isinstance(org_info, dict):
                org_name = org_info.get("org_name", "")
                dept = org_info.get("org_dept", "")
            else:
                continue
            
            if not org_name:
                continue
            
            # Extract other data
            amount = float(grant.get("award_amount", 0) or 0)
            agency = grant.get("funding_agency", "")
            pi_name = grant.get("contact_pi_name", "")
            
            # Update institution data
            data = institution_data[org_name]
            data["total_grants"] += 1
            data["total_funding"] += amount
            data["agencies"].add(agency)
            
            if dept:
                data["departments"].add(dept)
            if pi_name:
                data["pis"].add(pi_name)
            
            if agency == "NIH":
                data["nih_grants"] += 1
                data["nih_funding"] += amount
            elif agency == "NSF":
                data["nsf_grants"] += 1
                data["nsf_funding"] += amount
        
        # Convert sets to lists and counts
        stats = {}
        for org_name, data in institution_data.items():
            stats[org_name] = {
                "total_grants": data["total_grants"],
                "total_funding": data["total_funding"],
                "nih_grants": data["nih_grants"],
                "nih_funding": data["nih_funding"],
                "nsf_grants": data["nsf_grants"],
                "nsf_funding": data["nsf_funding"],
                "agencies_count": len(data["agencies"]),
                "departments_count": len(data["departments"]),
                "pis_count": len(data["pis"]),
                "avg_grant_size": data["total_funding"] / data["total_grants"] if data["total_grants"] > 0 else 0
            }
        
        return stats
    
    async def build_comprehensive_cache(self, nih_max: int = 25000, nsf_max: int = 25000) -> Dict[str, Any]:
        """Build comprehensive grant cache with async data fetching."""
        start_time = time.time()
        
        print("🚀 Starting Enhanced Cache Builder...")
        print(f"📋 Targets: NIH={nih_max:,}, NSF={nsf_max:,}")
        print("=" * 60)
        
        # Fetch data concurrently
        print("⚡ Starting concurrent API fetching...")
        nih_task = asyncio.create_task(self.fetch_nih_grants_comprehensive(nih_max))
        nsf_task = asyncio.create_task(self.fetch_nsf_grants_comprehensive(nsf_max))
        
        # Wait for both to complete
        nih_grants, nsf_grants = await asyncio.gather(nih_task, nsf_task)
        
        # Combine and deduplicate
        print("\n🔄 Processing combined data...")
        all_grants = nih_grants + nsf_grants
        unique_grants = self.deduplicate_grants(all_grants)
        
        # Generate statistics
        institution_stats = self.generate_institution_stats(unique_grants)
        
        # Save to cache files
        print("\n💾 Saving to cache files...")
        
        # Save individual caches
        nih_only = [g for g in unique_grants if g.get("funding_agency") == "NIH"]
        nsf_only = [g for g in unique_grants if g.get("funding_agency") == "NSF"]
        
        save_nih_cache(nih_only, {
            "total_fetched": len(nih_only),
            "institutions": len([org for org, stats in institution_stats.items() if stats["nih_grants"] > 0]),
            "total_funding": sum(stats["nih_funding"] for stats in institution_stats.values())
        })
        
        save_nsf_cache(nsf_only, {
            "total_fetched": len(nsf_only),
            "institutions": len([org for org, stats in institution_stats.items() if stats["nsf_grants"] > 0]),
            "total_funding": sum(stats["nsf_funding"] for stats in institution_stats.values())
        })
        
        save_combined_cache(unique_grants, {
            "nih_count": len(nih_only),
            "nsf_count": len(nsf_only),
            "total_count": len(unique_grants),
            "institutions": len(institution_stats),
            "total_funding": sum(stats["total_funding"] for stats in institution_stats.values()),
            "sources": ["NIH Reporter API", "NSF Awards API"]
        })
        
        # Save institution statistics
        stats_path = os.path.join(CACHE_DIR, "institution_stats.json")
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump({
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "institutions_count": len(institution_stats),
                    "total_grants": len(unique_grants),
                    "total_funding": sum(stats["total_funding"] for stats in institution_stats.values())
                },
                "institutions": institution_stats
            }, f, indent=2, default=str)
        
        duration = time.time() - start_time
        
        # Final summary
        total_funding = sum(stats["total_funding"] for stats in institution_stats.values())
        print("\n" + "=" * 60)
        print("🎉 ENHANCED CACHE BUILD COMPLETE!")
        print(f"⏱️  Duration: {duration:.1f} seconds")
        print(f"🏫 Institutions: {len(institution_stats):,}")
        print(f"📊 Total Grants: {len(unique_grants):,}")
        print(f"   • NIH: {len(nih_only):,}")
        print(f"   • NSF: {len(nsf_only):,}")
        print(f"💰 Total Funding: ${total_funding:,.0f}")
        print(f"💾 Cache files updated successfully")
        print("=" * 60)
        
        return {
            "success": True,
            "duration_seconds": duration,
            "institutions": len(institution_stats),
            "total_grants": len(unique_grants),
            "nih_grants": len(nih_only),
            "nsf_grants": len(nsf_only),
            "total_funding": total_funding,
            "top_institutions": sorted(
                institution_stats.items(),
                key=lambda x: x[1]["total_funding"],
                reverse=True
            )[:10]
        }

async def main():
    """Main function to run the enhanced cache builder."""
    builder = EnhancedCacheBuilder()
    
    try:
        result = await builder.build_comprehensive_cache(
            nih_max=30000,  # Increased for better coverage
            nsf_max=20000   # Increased for better coverage  
        )
        
        print("\n🔍 Top 10 Institutions by Funding:")
        for i, (institution, stats) in enumerate(result["top_institutions"], 1):
            print(f"{i:2d}. {institution}")
            print(f"     💰 ${stats['total_funding']:,.0f} ({stats['total_grants']} grants)")
            print(f"     📊 NIH: {stats['nih_grants']}, NSF: {stats['nsf_grants']}")
        
    except Exception as e:
        print(f"❌ Error building cache: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
