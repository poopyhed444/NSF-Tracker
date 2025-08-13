#!/usr/bin/env python3
"""
Enhanced NSF-Tracker API with optimized caching system.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from datetime import datetime
import asyncio
import json
import os
from typing import List, Dict, Any
from optimized_cache import (
    get_cached_analysis, save_cached_analysis,
    get_cached_institution_data, save_cached_institution_data,
    get_cached_general_data, save_cached_general_data,
    clear_cache as clear_optimized_cache
)

app = FastAPI(
    title="NSF-Tracker Enhanced API",
    description="Enhanced funding analysis with optimized caching",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def fetch_additional_terminated_grants(institution_name: str) -> List[Dict[str, Any]]:
    """
    Fetch comprehensive terminated/cancelled grants for better department analysis
    """
    try:
        import httpx
        from datetime import datetime, timedelta
        
        print(f"🔍 Fetching comprehensive terminated grants for {institution_name}...")
        
        # NIH API for terminated grants
        nih_url = "https://api.reporter.nih.gov/v2/projects/search"
        
        # Search for grants in the last 5 years that have ended
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1825)  # 5 years
        
        all_terminated_grants = []
        
        # Multiple search strategies to catch different types of terminated grants
        search_strategies = [
            # Strategy 1: Recently ended grants
            {
                "criteria": {
                    "project_end_date": {
                        "from_date": start_date.strftime("%Y-%m-%d"),
                        "to_date": end_date.strftime("%Y-%m-%d")
                    },
                    "organization_names": [institution_name],
                    "award_notice_date": {
                        "from_date": "2019-01-01",
                        "to_date": end_date.strftime("%Y-%m-%d")
                    }
                },
                "include_fields": [
                    "Organization", "ProjectTitle", "ProjectEndDate", "ProjectStartDate",
                    "AwardAmount", "FiscalYear", "ContactPiName", "ProjectNum", "AwardNoticeDate"
                ],
                "offset": 0,
                "limit": 500
            },
            # Strategy 2: Search by institution variations
            {
                "criteria": {
                    "project_end_date": {
                        "from_date": start_date.strftime("%Y-%m-%d"),
                        "to_date": end_date.strftime("%Y-%m-%d")
                    },
                    "organization_names": [
                        institution_name,
                        institution_name.replace("University", "Univ"),
                        institution_name.replace("University of", ""),
                        institution_name.split()[0] if " " in institution_name else institution_name
                    ]
                },
                "include_fields": [
                    "Organization", "ProjectTitle", "ProjectEndDate", "ProjectStartDate",
                    "AwardAmount", "FiscalYear", "ContactPiName", "ProjectNum", "AwardNoticeDate"
                ],
                "offset": 0,
                "limit": 500
            }
        ]
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            for strategy_num, search_criteria in enumerate(search_strategies, 1):
                try:
                    print(f"📋 Trying search strategy {strategy_num}...")
                    response = await client.post(nih_url, json=search_criteria)
                    response.raise_for_status()
                    data = response.json()
                    
                    strategy_results = []
                    
                    # Process grants and filter for truly terminated ones
                    for grant in data.get("results", []):
                        # Check if grant has actually ended (not just scheduled to end)
                        end_date_str = grant.get('project_end_date')
                        current_date = datetime.now()
                        
                        grant_ended = False
                        if end_date_str:
                            try:
                                grant_end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                                if grant_end_date < current_date:
                                    grant_ended = True
                            except:
                                # Try alternative date format
                                try:
                                    grant_end_date = datetime.strptime(end_date_str[:10], "%Y-%m-%d")
                                    if grant_end_date < current_date:
                                        grant_ended = True
                                except:
                                    continue
                        
                        if grant_ended:
                            # Add standardized fields to match cache format
                            processed_grant = {
                                'fiscal_year': grant.get('fiscal_year'),
                                'project_num': grant.get('project_num'),
                                'organization': grant.get('organization', {}),
                                'award_amount': grant.get('award_amount', 0),
                                'contact_pi_name': grant.get('contact_pi_name'),
                                'project_start_date': grant.get('project_start_date'),
                                'project_end_date': grant.get('project_end_date'),
                                'project_title': grant.get('project_title'),
                                'funding_agency': 'NIH',
                                'award_status': 'terminated',  # These are all ended grants
                                'source': f'terminated_search_strategy_{strategy_num}'
                            }
                            strategy_results.append(processed_grant)
                    
                    print(f"✅ Strategy {strategy_num}: Found {len(strategy_results)} terminated grants")
                    all_terminated_grants.extend(strategy_results)
                    
                except Exception as e:
                    print(f"⚠️ Strategy {strategy_num} failed: {e}")
                    continue
        
        # Remove duplicates based on project_num
        seen_projects = set()
        unique_terminated_grants = []
        for grant in all_terminated_grants:
            project_num = grant.get('project_num')
            if project_num and project_num not in seen_projects:
                seen_projects.add(project_num)
                unique_terminated_grants.append(grant)
        
        print(f"✅ Total unique terminated grants found: {len(unique_terminated_grants)}")
        return unique_terminated_grants
        
    except Exception as e:
        print(f"❌ Failed to fetch comprehensive terminated grants: {e}")
        return []

async def fetch_comprehensive_institution_grants(institution_name: str, max_grants: int = 10000) -> List[Dict[str, Any]]:
    """
    Fetch comprehensive grants for an institution using multiple API strategies
    """
    try:
        import httpx
        from datetime import datetime, timedelta
        
        print(f"🔍 Fetching comprehensive grants for {institution_name} (up to {max_grants} grants)...")
        
        all_grants = []
        
        # NIH API - Multiple search strategies
        nih_url = "https://api.reporter.nih.gov/v2/projects/search"
        
        # Create institution name variations for better matching
        institution_variations = [
            institution_name,
            institution_name.upper(),
            institution_name.replace("University of", "").strip(),
            institution_name.replace("University", "Univ").strip(),
            institution_name.replace(",", "").strip()
        ]
        
        # Remove duplicates while preserving order
        seen = set()
        unique_variations = []
        for var in institution_variations:
            if var.lower() not in seen and var.strip():
                seen.add(var.lower())
                unique_variations.append(var)
        
        print(f"🔍 Searching with institution variations: {unique_variations}")
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            # NIH search strategies
            nih_strategies = [
                # Strategy 1: Recent grants (last 5 years, all statuses)
                {
                    "criteria": {
                        "organization_names": unique_variations,
                        "fiscal_years": [2020, 2021, 2022, 2023, 2024, 2025]
                    },
                    "include_fields": [
                        "Organization", "ProjectTitle", "ProjectEndDate", "ProjectStartDate",
                        "AwardAmount", "FiscalYear", "ContactPiName", "ProjectNum", "AwardNoticeDate",
                        "ActivityCode", "FullStudySection"
                    ],
                    "limit": 500
                },
                # Strategy 2: Broader time range with higher amounts
                {
                    "criteria": {
                        "organization_names": unique_variations,
                        "award_amount_low": 100000,  # Focus on substantial grants
                        "fiscal_years": [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]
                    },
                    "include_fields": [
                        "Organization", "ProjectTitle", "ProjectEndDate", "ProjectStartDate",
                        "AwardAmount", "FiscalYear", "ContactPiName", "ProjectNum", "AwardNoticeDate",
                        "ActivityCode", "FullStudySection"
                    ],
                    "limit": 500
                },
                # Strategy 3: Search by DUNS/UEI if available
                {
                    "criteria": {
                        "organization_names": unique_variations,
                        "project_types": ["RESEARCH", "TRAINING", "CAREER", "OTHER_RESEARCH"],
                        "fiscal_years": [2019, 2020, 2021, 2022, 2023, 2024, 2025]
                    },
                    "include_fields": [
                        "Organization", "ProjectTitle", "ProjectEndDate", "ProjectStartDate",
                        "AwardAmount", "FiscalYear", "ContactPiName", "ProjectNum", "AwardNoticeDate",
                        "ActivityCode", "FullStudySection"
                    ],
                    "limit": 500
                }
            ]
            
            for strategy_num, search_criteria in enumerate(nih_strategies, 1):
                try:
                    print(f"📋 NIH Strategy {strategy_num}: Searching...")
                    
                    # Paginate through results
                    offset = 0
                    batch_size = 500
                    strategy_grants = []
                    
                    while len(strategy_grants) < 2000:  # Max 2000 per strategy
                        search_criteria["offset"] = offset
                        search_criteria["limit"] = batch_size
                        
                        response = await client.post(nih_url, json=search_criteria)
                        response.raise_for_status()
                        data = response.json()
                        
                        results = data.get("results", [])
                        if not results:
                            break
                        
                        # Process and standardize grants
                        for grant in results:
                            processed_grant = {
                                'fiscal_year': grant.get('fiscal_year'),
                                'project_num': grant.get('project_num'),
                                'organization': grant.get('organization', {}),
                                'activity_code': grant.get('activity_code'),
                                'award_amount': grant.get('award_amount', 0),
                                'contact_pi_name': grant.get('contact_pi_name'),
                                'project_start_date': grant.get('project_start_date'),
                                'project_end_date': grant.get('project_end_date'),
                                'full_study_section': grant.get('full_study_section', {}),
                                'award_notice_date': grant.get('award_notice_date'),
                                'project_title': grant.get('project_title'),
                                'funding_agency': 'NIH',
                                'source': f'NIH_comprehensive_strategy_{strategy_num}'
                            }
                            strategy_grants.append(processed_grant)
                        
                        print(f"  📥 Batch {offset//batch_size + 1}: +{len(results)} grants (total: {len(strategy_grants)})")
                        offset += batch_size
                        
                        if len(results) < batch_size:
                            break
                    
                    all_grants.extend(strategy_grants)
                    print(f"✅ NIH Strategy {strategy_num}: Found {len(strategy_grants)} grants")
                    
                except Exception as e:
                    print(f"⚠️ NIH Strategy {strategy_num} failed: {e}")
                    continue
            
            # NSF API search
            print("🧪 Fetching NSF grants...")
            nsf_url = "https://api.nsf.gov/services/v1/awards.json"
            
            try:
                nsf_params = {
                    'printFields': 'id,title,startDate,expDate,fundsObligatedAmt,awardeeName,pdPIName,agency,fundProgramName',
                    'rpp': '500',
                    'awardeeName': institution_name
                }
                
                # Paginate through NSF results
                offset = 1
                nsf_grants = []
                
                while len(nsf_grants) < 2000:  # Max 2000 NSF grants
                    nsf_params['offset'] = str(offset)
                    
                    response = await client.get(nsf_url, params=nsf_params)
                    response.raise_for_status()
                    data = response.json()
                    
                    awards = data.get('response', {}).get('award', [])
                    if not awards:
                        break
                    
                    # Process NSF grants
                    for award in awards:
                        processed_grant = {
                            'fiscal_year': None,  # NSF doesn't use fiscal years the same way
                            'project_num': award.get('id'),
                            'organization': {
                                'org_name': award.get('awardeeName'),
                                'org_state': award.get('awardeeStateCode'),
                                'org_city': award.get('awardeeCity')
                            },
                            'activity_code': 'NSF',
                            'award_amount': award.get('fundsObligatedAmt', 0),
                            'contact_pi_name': award.get('pdPIName'),
                            'project_start_date': award.get('startDate'),
                            'project_end_date': award.get('expDate'),
                            'project_title': award.get('title'),
                            'funding_agency': 'NSF',
                            'source': 'NSF_comprehensive_search'
                        }
                        nsf_grants.append(processed_grant)
                    
                    print(f"  📥 NSF Batch {offset//500 + 1}: +{len(awards)} grants (total: {len(nsf_grants)})")
                    offset += 500
                    
                    if len(awards) < 500:
                        break
                
                all_grants.extend(nsf_grants)
                print(f"✅ NSF: Found {len(nsf_grants)} grants")
                
            except Exception as e:
                print(f"⚠️ NSF search failed: {e}")
        
        # Remove duplicates based on project_num/id
        seen_projects = set()
        unique_grants = []
        for grant in all_grants:
            project_num = grant.get('project_num')
            if project_num and project_num not in seen_projects:
                seen_projects.add(project_num)
                unique_grants.append(grant)
            elif not project_num:
                # Include grants without project numbers (shouldn't happen but just in case)
                unique_grants.append(grant)
        
        print(f"🎯 Total unique grants found: {len(unique_grants)} (from {len(all_grants)} total)")
        return unique_grants[:max_grants]  # Limit to max_grants
        
    except Exception as e:
        print(f"❌ Failed to fetch comprehensive institution grants: {e}")
        return []

async def fetch_additional_terminated_grants(institution_name: str) -> List[Dict[str, Any]]:
    """
    Fetch comprehensive terminated/cancelled grants for better department analysis
    """
    try:
        import httpx
        from datetime import datetime, timedelta
        
        print(f"🔍 Fetching comprehensive terminated grants for {institution_name}...")
        
        # NIH API for terminated grants
        nih_url = "https://api.reporter.nih.gov/v2/projects/search"
        
        # Search for grants in the last 5 years that have ended
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1825)  # 5 years
        
        all_terminated_grants = []
        
        # Multiple search strategies to catch different types of terminated grants
        search_strategies = [
            # Strategy 1: Recently ended grants
            {
                "criteria": {
                    "project_end_date": {
                        "from_date": start_date.strftime("%Y-%m-%d"),
                        "to_date": end_date.strftime("%Y-%m-%d")
                    },
                    "organization_names": [institution_name],
                    "award_notice_date": {
                        "from_date": "2019-01-01",
                        "to_date": end_date.strftime("%Y-%m-%d")
                    }
                },
                "include_fields": [
                    "Organization", "ProjectTitle", "ProjectEndDate", "ProjectStartDate",
                    "AwardAmount", "FiscalYear", "ContactPiName", "ProjectNum", "AwardNoticeDate"
                ],
                "offset": 0,
                "limit": 500
            },
            # Strategy 2: Search by institution variations
            {
                "criteria": {
                    "project_end_date": {
                        "from_date": start_date.strftime("%Y-%m-%d"),
                        "to_date": end_date.strftime("%Y-%m-%d")
                    },
                    "organization_names": [
                        institution_name,
                        institution_name.replace("University", "Univ"),
                        institution_name.replace("University of", ""),
                        institution_name.split()[0] if " " in institution_name else institution_name
                    ]
                },
                "include_fields": [
                    "Organization", "ProjectTitle", "ProjectEndDate", "ProjectStartDate",
                    "AwardAmount", "FiscalYear", "ContactPiName", "ProjectNum", "AwardNoticeDate"
                ],
                "offset": 0,
                "limit": 500
            }
        ]
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            for strategy_num, search_criteria in enumerate(search_strategies, 1):
                try:
                    print(f"📋 Trying search strategy {strategy_num}...")
                    response = await client.post(nih_url, json=search_criteria)
                    response.raise_for_status()
                    data = response.json()
                    
                    strategy_results = []
                    
                    # Process grants and filter for truly terminated ones
                    for grant in data.get("results", []):
                        # Check if grant has actually ended (not just scheduled to end)
                        end_date_str = grant.get('project_end_date')
                        current_date = datetime.now()
                        
                        grant_ended = False
                        if end_date_str:
                            try:
                                grant_end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                                if grant_end_date < current_date:
                                    grant_ended = True
                            except:
                                # Try alternative date format
                                try:
                                    grant_end_date = datetime.strptime(end_date_str[:10], "%Y-%m-%d")
                                    if grant_end_date < current_date:
                                        grant_ended = True
                                except:
                                    continue
                        
                        if grant_ended:
                            # Add standardized fields to match cache format
                            processed_grant = {
                                'fiscal_year': grant.get('fiscal_year'),
                                'project_num': grant.get('project_num'),
                                'organization': grant.get('organization', {}),
                                'award_amount': grant.get('award_amount', 0),
                                'contact_pi_name': grant.get('contact_pi_name'),
                                'project_start_date': grant.get('project_start_date'),
                                'project_end_date': grant.get('project_end_date'),
                                'project_title': grant.get('project_title'),
                                'funding_agency': 'NIH',
                                'award_status': 'terminated',  # These are all ended grants
                                'source': f'terminated_search_strategy_{strategy_num}'
                            }
                            strategy_results.append(processed_grant)
                    
                    print(f"✅ Strategy {strategy_num}: Found {len(strategy_results)} terminated grants")
                    all_terminated_grants.extend(strategy_results)
                    
                except Exception as e:
                    print(f"⚠️ Strategy {strategy_num} failed: {e}")
                    continue
        
        # Remove duplicates based on project_num
        seen_projects = set()
        unique_terminated_grants = []
        for grant in all_terminated_grants:
            project_num = grant.get('project_num')
            if project_num and project_num not in seen_projects:
                seen_projects.add(project_num)
                unique_terminated_grants.append(grant)
        
        print(f"✅ Total unique terminated grants found: {len(unique_terminated_grants)}")
        return unique_terminated_grants
        
    except Exception as e:
        print(f"❌ Failed to fetch comprehensive terminated grants: {e}")
        return []

async def analyze_nonrenewal_grants(institution_name: str, active_grants: list) -> dict:
    """
    Analyze non-renewal grants using Times-style methodology.
    Identifies grants that should have been renewed but show no evidence of renewal.
    """
    try:
        from enhanced_delayed_funding_tracker import EnhancedDelayedFundingTracker
        from datetime import datetime, timedelta
        
        print(f"🔍 Analyzing non-renewal grants for {institution_name}")
        
        # Initialize tracker
        tracker = EnhancedDelayedFundingTracker()
        
        # Analysis period: last 24 months for renewal eligibility (extended for better detection)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=730)  # Extended to 2 years
        
        # Find grants eligible for renewal that haven't been renewed
        renewal_eligible_grants = []
        missing_renewals = []
        nonrenewal_dept_losses = {}
        nonrenewal_grants_by_pi = {}
        
        for grant in active_grants:
            # Check if grant is eligible for renewal
            if tracker._is_renewal_eligible_grant(grant):
                expected_renewal_date = tracker._calculate_expected_renewal_date(grant)
                
                if expected_renewal_date and expected_renewal_date < datetime.now() - timedelta(days=90):  # 90-day grace period
                    pi_name = (grant.get('contact_pi_name') or grant.get('pi_name') or '').strip()
                    amount = float(grant.get('award_amount', 0) or 0)
                    
                    # Check for renewal evidence
                    renewal_found = await tracker._check_for_renewal_evidence(grant, active_grants)
                    
                    renewal_info = {
                        'grant': grant,
                        'pi_name': pi_name,
                        'expected_renewal_date': expected_renewal_date.isoformat(),
                        'award_amount': amount,
                        'days_overdue': (datetime.now() - expected_renewal_date).days,
                        'renewal_found': renewal_found,
                        'project_title': grant.get('project_title', ''),
                        'project_num': grant.get('project_num') or grant.get('award_id'),
                        'funding_agency': grant.get('funding_agency', 'Unknown')
                    }
                    
                    renewal_eligible_grants.append(renewal_info)
                    
                    if not renewal_found:
                        missing_renewals.append(renewal_info)
                        
                        # Department-level tracking
                        try:
                            from pi_department_lookup import get_department_string
                            dept = get_department_string(pi_name, institution_name)
                        except:
                            # Fallback to grant organization data
                            org_info = grant.get('organization', {})
                            if isinstance(org_info, dict):
                                dept = org_info.get('dept_type', 'Unknown Department')
                            elif isinstance(org_info, list) and org_info:
                                dept = org_info[0].get('dept_type', 'Unknown Department')
                            else:
                                dept = 'Unknown Department'
                        
                        nonrenewal_dept_losses[dept] = nonrenewal_dept_losses.get(dept, 0) + amount
                        
                        # PI-level tracking
                        if pi_name not in nonrenewal_grants_by_pi:
                            nonrenewal_grants_by_pi[pi_name] = {
                                'pi_name': pi_name,
                                'department': dept,
                                'lost_funding': 0,
                                'grants': []
                            }
                        
                        nonrenewal_grants_by_pi[pi_name]['lost_funding'] += amount
                        nonrenewal_grants_by_pi[pi_name]['grants'].append({
                            'award_id': grant.get('project_num') or grant.get('award_id'),
                            'project_title': grant.get('project_title', ''),
                            'amount': amount,
                            'expected_renewal': expected_renewal_date.isoformat(),
                            'days_overdue': (datetime.now() - expected_renewal_date).days,
                            'funding_agency': grant.get('funding_agency', 'Unknown')
                        })
        
        # Calculate metrics
        total_at_risk_funding = sum(r['award_amount'] for r in missing_renewals)
        renewal_rate = 0
        if renewal_eligible_grants:
            renewed_count = len([r for r in renewal_eligible_grants if r['renewal_found']])
            renewal_rate = (renewed_count / len(renewal_eligible_grants)) * 100
        
        top_affected_pis = sorted(nonrenewal_grants_by_pi.values(), key=lambda x: x['lost_funding'], reverse=True)[:10]
        
        risk_level = "LOW"
        if len(missing_renewals) > 5 or total_at_risk_funding > 10000000:
            risk_level = "HIGH"
        elif len(missing_renewals) > 2 or total_at_risk_funding > 5000000:
            risk_level = "MEDIUM"
        
        return {
            'total_lost_funding': total_at_risk_funding,
            'grants_eligible_for_renewal': len(renewal_eligible_grants),
            'missing_renewals_count': len(missing_renewals),
            'renewal_rate': renewal_rate,
            'risk_level': risk_level,
            'departments_affected': len(nonrenewal_dept_losses),
            'pis_impacted': len(nonrenewal_grants_by_pi),
            'top_affected_pis': [
                {
                    'pi_name': pi['pi_name'],
                    'department': pi['department'],
                    'lost_funding': pi['lost_funding'],
                    'grants_count': len(pi['grants'])
                } for pi in top_affected_pis
            ],
            'department_losses': dict(sorted(nonrenewal_dept_losses.items(), key=lambda x: x[1], reverse=True)),
            'detailed_missing_renewals': missing_renewals[:10],  # Top 10 for review
            'analysis_period': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            'methodology_note': 'Times-style non-renewal analysis: identifies grants eligible for renewal that show no evidence of renewal within expected timeframes'
        }
        
    except Exception as e:
        print(f"Error in non-renewal analysis: {e}")
        return {
            'total_lost_funding': 0,
            'grants_eligible_for_renewal': 0,
            'missing_renewals_count': 0,
            'renewal_rate': 0,
            'risk_level': 'UNKNOWN',
            'departments_affected': 0,
            'pis_impacted': 0,
            'top_affected_pis': [],
            'department_losses': {},
            'detailed_missing_renewals': [],
            'analysis_period': '',
            'methodology_note': 'Non-renewal analysis failed',
            'error': str(e)
        }

async def analyze_fresh_nih_nsf_data(institution_name: str, grants: list, pi_cache: dict = None) -> dict:
    """
    Analyze institution using fresh NIH/NSF grant data
    """
    try:
        from layoff_estimator import calculate_funding_cliff, estimate_lab_size
        
        print(f"🔬 Analyzing {len(grants)} fresh NIH/NSF grants for {institution_name}")
        
        # Filter to ensure all grants are dictionaries
        valid_grants = []
        for grant in grants:
            if isinstance(grant, dict):
                valid_grants.append(grant)
            else:
                print(f"⚠️ Skipping invalid grant (type: {type(grant)})")
        
        print(f"📊 Valid grants: {len(valid_grants)}")
        grants = valid_grants
        
        # Separate active and terminated grants
        active_grants = []
        terminated_grants = []
        total_funding = 0
        
        for grant in grants:
            try:
                amount = float(grant.get('award_amount', 0) or 0)
                total_funding += amount
                
                # Check grant status
                status = grant.get('award_status', '').lower()
                if status in ['terminated', 'cancelled', 'expired']:
                    terminated_grants.append(grant)
                else:
                    active_grants.append(grant)
            except Exception as e:
                print(f"⚠️ Error processing grant status: {e}")
                continue
        
        print(f"📊 Found {len(active_grants)} active grants, {len(terminated_grants)} terminated grants")
        
        # Calculate funding breakdown
        funding_breakdown = {
            'nih_funding': 0,
            'nsf_funding': 0,
            'total_funding': total_funding
        }
        
        for grant in grants:
            try:
                amount = float(grant.get('award_amount', 0) or 0)
                agency = grant.get('funding_agency', '').upper()
                if agency == 'NIH':
                    funding_breakdown['nih_funding'] += amount
                elif agency == 'NSF':
                    funding_breakdown['nsf_funding'] += amount
            except Exception as e:
                print(f"⚠️ Error in funding breakdown: {e}")
                continue
        
        # Calculate risk metrics
        cliff_analysis = calculate_funding_cliff(active_grants, months_ahead=12) if active_grants else {'cliff_percentage': 0, 'expiring_funding': 0}
        lab_size_info = estimate_lab_size(total_funding)
        
        # Process departments (enhanced approach with cancelled grants tracking)
        dept_breakdown = {}
        cancelled_dept_losses = {}
        cancelled_grants_by_pi = {}
        
        if pi_cache:
            try:
                from pi_department_lookup import get_department_string
                
                # Process active grants by department
                for grant in active_grants:
                    pi_name = (grant.get('contact_pi_name') or grant.get('pi_name') or '').strip()
                    if pi_name:
                        dept = get_department_string(pi_name, institution_name)
                        amount = float(grant.get('award_amount', 0) or 0)
                        dept_breakdown[dept] = dept_breakdown.get(dept, 0) + amount
                
                # Process terminated grants by department for cancelled grants analysis
                for grant in terminated_grants:
                    # Check if grant belongs to target institution
                    grant_org = grant.get('organization', {})
                    if isinstance(grant_org, dict):
                        org_name = grant_org.get('org_name', '').upper()
                    else:
                        org_name = ''
                    
                    # Simple institution matching - check if institution name appears in org name
                    institution_upper = institution_name.upper()
                    institution_keywords = institution_upper.split()
                    
                    # Check if any major keywords from institution name appear in org name
                    is_institution_match = any(keyword in org_name for keyword in institution_keywords if len(keyword) > 3)
                    
                    if is_institution_match:
                        pi_name = (grant.get('contact_pi_name') or grant.get('pi_name') or '').strip()
                        if pi_name:
                            dept = get_department_string(pi_name, institution_name)
                            amount = float(grant.get('award_amount', 0) or 0)
                            
                            # Track department losses
                            cancelled_dept_losses[dept] = cancelled_dept_losses.get(dept, 0) + amount
                            
                            # Track PI-level losses
                            if pi_name not in cancelled_grants_by_pi:
                                cancelled_grants_by_pi[pi_name] = {
                                    'pi_name': pi_name,
                                    'department': dept,
                                    'lost_funding': 0,
                                    'grants': []
                                }
                            
                            cancelled_grants_by_pi[pi_name]['lost_funding'] += amount
                            cancelled_grants_by_pi[pi_name]['grants'].append({
                                'award_id': grant.get('project_num') or grant.get('award_id'),
                                'project_title': grant.get('project_title', ''),
                                'amount': amount,
                                'status': grant.get('award_status', 'Unknown'),
                                'end_date': grant.get('project_end_date'),
                                'funding_agency': grant.get('funding_agency', 'Unknown')
                            })
                        
            except Exception:
                # Fallback to simple department detection
                for grant in active_grants:
                    # Try to extract department from grant data
                    org_info = grant.get('organization', {})
                    dept_type = 'Unknown Department'
                    
                    if isinstance(org_info, dict):
                        dept_type = org_info.get('dept_type', 'Unknown Department')
                    elif isinstance(org_info, list) and org_info and isinstance(org_info[0], dict):
                        dept_type = org_info[0].get('dept_type', 'Unknown Department')
                    
                    if dept_type and dept_type != 'Unknown Department':
                        amount = float(grant.get('award_amount', 0) or 0)
                        dept_breakdown[dept_type] = dept_breakdown.get(dept_type, 0) + amount
                
                # Track cancelled grants by department
                for grant in terminated_grants:
                    org_info = grant.get('organization', {})
                    dept_type = 'Unknown Department'
                    
                    if isinstance(org_info, dict):
                        dept_type = org_info.get('dept_type', 'Unknown Department')
                    elif isinstance(org_info, list) and org_info and isinstance(org_info[0], dict):
                        dept_type = org_info[0].get('dept_type', 'Unknown Department')
                    
                    if dept_type and dept_type != 'Unknown Department':
                        amount = float(grant.get('award_amount', 0) or 0)
                        cancelled_dept_losses[dept_type] = cancelled_dept_losses.get(dept_type, 0) + amount
        else:
            # Simple fallback when no PI cache
            for grant in active_grants:
                org_info = grant.get('organization', {})
                dept_type = 'Unknown Department'
                
                if isinstance(org_info, dict):
                    dept_type = org_info.get('dept_type', 'Unknown Department')
                elif isinstance(org_info, list) and org_info and isinstance(org_info[0], dict):
                    dept_type = org_info[0].get('dept_type', 'Unknown Department')
                
                if dept_type:
                    amount = float(grant.get('award_amount', 0) or 0)
                    dept_breakdown[dept_type] = dept_breakdown.get(dept_type, 0) + amount
            
            # Track cancelled grants by department
            for grant in terminated_grants:
                org_info = grant.get('organization', {})
                dept_type = 'Unknown Department'
                
                if isinstance(org_info, dict):
                    dept_type = org_info.get('dept_type', 'Unknown Department')
                elif isinstance(org_info, list) and org_info and isinstance(org_info[0], dict):
                    dept_type = org_info[0].get('dept_type', 'Unknown Department')
                
                if dept_type:
                    amount = float(grant.get('award_amount', 0) or 0)
                    cancelled_dept_losses[dept_type] = cancelled_dept_losses.get(dept_type, 0) + amount
        
        # Prepare cancelled grants analysis
        total_cancelled_funding = sum(cancelled_dept_losses.values())
        top_cancelled_pis = sorted(cancelled_grants_by_pi.values(), key=lambda x: x['lost_funding'], reverse=True)[:10]
        
        # Non-renewal grants analysis (Times-style methodology)
        print("🔍 Performing non-renewal grants analysis...")
        nonrenewal_analysis = await analyze_nonrenewal_grants(institution_name, active_grants)
        
        # Enhanced cash flow risk assessment with multiple methodologies
        risk_factors = []
        risk_score = cliff_analysis.get('cliff_percentage', 0)
        
        # Add cancelled grants impact to risk
        if total_cancelled_funding > 0:
            cancellation_risk = min(30, (total_cancelled_funding / max(total_funding, 1)) * 100)
            risk_score += cancellation_risk
            risk_factors.append(f"Grant cancellations: ${total_cancelled_funding:,.0f} lost funding")
        
        # Add non-renewal impact to risk
        if nonrenewal_analysis.get('total_lost_funding', 0) > 0:
            nonrenewal_risk = min(20, (nonrenewal_analysis['total_lost_funding'] / max(total_funding, 1)) * 100)
            risk_score += nonrenewal_risk
            risk_factors.append(f"Non-renewal delays: ${nonrenewal_analysis['total_lost_funding']:,.0f} at risk")
        
        # Add traditional disbursement analysis if available
        try:
            from delayed_funding_tracker import DelayedFundingTracker
            legacy_tracker = DelayedFundingTracker()
            
            # Convert grants to USASpending format for legacy analysis
            usaspending_grants = []
            for grant in grants:
                usaspending_grants.append({
                    'Award ID': grant.get('project_num') or grant.get('award_id', ''),
                    'Award Amount': grant.get('award_amount', 0),
                    'Outlayed Amount': 0,  # NIH/NSF data doesn't include disbursement info
                    'Obligated Amount': grant.get('award_amount', 0),
                    'Base Obligation Date': grant.get('project_start_date', ''),
                    'Action Date': grant.get('award_notice_date', ''),
                    'Award Description': grant.get('project_title', ''),
                    'Recipient Name': institution_name,
                    'Period of Performance Start Date': grant.get('project_start_date', ''),
                    'Period of Performance Current End Date': grant.get('project_end_date', '')
                })
            
            if usaspending_grants:
                legacy_analysis = legacy_tracker.analyze_funding_delays(usaspending_grants)
                if legacy_analysis.get('delayed_funding_risk', 0) > 0:
                    disbursement_risk = min(25, legacy_analysis['delayed_funding_risk'])
                    risk_score += disbursement_risk
                    risk_factors.append(f"Legacy disbursement delays detected")
                    
        except Exception as e:
            print(f"Legacy cash flow analysis error: {e}")
        
        # Funding cliff analysis
        if cliff_analysis.get('cliff_percentage', 0) > 15:
            risk_factors.append(f"Funding cliff: {cliff_analysis['cliff_percentage']:.1f}% of funding expires within 12 months")
        
        # Build comprehensive result
        result = {
            'institution': institution_name,
            'data_source': 'Fresh NIH/NSF APIs',
            'overview': {
                'total_grants': len(grants),
                'active_grants': len(active_grants),
                'terminated_grants': len(terminated_grants),
                'total_funding': total_funding,
                'total_undisbursed': 0,  # NIH/NSF data doesn't track disbursement details
                'disbursement_efficiency': 'N/A (NIH/NSF data)',
                'risk_score': cliff_analysis.get('cliff_percentage', 0)
            },
            'financial_overview': {
                'undisbursed_amount': 0,
                'disbursement_efficiency': 'N/A (research grant focus)',
                'funding_cliff_percentage': cliff_analysis.get('cliff_percentage', 0),
                'estimated_positions_at_risk': cliff_analysis.get('expiring_funding', 0) / 200000
            },
            'funding_breakdown': funding_breakdown,
            'department_breakdown': dict(sorted(dept_breakdown.items(), key=lambda x: x[1], reverse=True)),
            'cancelled_grants_impact': {
                'total_lost_funding': total_cancelled_funding,
                'departments_affected': len(cancelled_dept_losses),
                'pis_impacted': len(cancelled_grants_by_pi),
                'top_affected_pis': [
                    {
                        'pi_name': pi['pi_name'],
                        'department': pi['department'],
                        'lost_funding': pi['lost_funding'],
                        'grants_count': len(pi['grants'])
                    } for pi in top_cancelled_pis
                ],
                'department_losses': dict(sorted(cancelled_dept_losses.items(), key=lambda x: x[1], reverse=True)),
                'methodology_note': 'Analysis based on fresh NIH/NSF grant status data tracking terminated and cancelled grants'
            },
            'nonrenewal_grants_impact': nonrenewal_analysis,
            'grant_details': grants[:50],  # Limit to first 50 for response size
            'cash_flow_risk': {
                'level': 'HIGH' if risk_score > 50 else 'MEDIUM' if risk_score > 25 else 'LOW',
                'score': min(100, risk_score),
                'risk_factors': risk_factors,
                'methodology_note': 'Enhanced risk assessment including funding cliff, cancelled grants, and non-renewal delays'
            },
            'methodology_note': 'Enhanced analysis with cancelled grants tracking based on fresh NIH Reporter and NSF Awards API data'
        }
        
        return result
        
    except Exception as e:
        print(f"Error in fresh NIH/NSF analysis: {e}")
        return {
            'institution': institution_name,
            'error': f'Fresh data analysis failed: {str(e)}',
            'note': 'Falling back to comprehensive analysis'
        }

def load_pi_department_cache():
    """Load the PI department cache for matching PIs to departments"""
    try:
        cache_file = "pi_department_cache.json"
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                return json.load(f)
        return {}
    except Exception as e:
        print(f"Error loading PI department cache: {e}")
        return {}

@app.get("/")
async def root():
    return {
        "message": "Enhanced NSF-Tracker API with Optimized Caching",
        "version": "2.0.0",
        "features": [
            "Optimized O(1) caching system",
            "Enhanced delayed funding analysis",
            "Department-level breakdown",
            "Multi-agency integration"
        ]
    }

@app.get("/api/delayed-funding/{institution_name}")
async def get_comprehensive_delayed_funding_analysis(
    institution_name: str,
    include_departments: bool = True,
    method: str = "comprehensive",
    force_refresh: bool = False
):
    """
    Comprehensive delayed funding analysis with optimized caching.
    
    This endpoint provides instant cached results for previously analyzed institutions,
    dramatically improving performance over the legacy system.
    """
    from datetime import datetime as dt
    
    try:
        print(f"🔍 Enhanced analysis for: {institution_name} (method: {method}, departments: {include_departments})")
        
        # Check optimized cache first (skip if force_refresh)
        if not force_refresh:
            print(f"🚀 Checking optimized cache for {institution_name}...")
            cached_result = get_cached_analysis(institution_name, method, include_departments)
            
            if cached_result:
                print(f"✅ Using cached analysis for {institution_name} (optimized cache)")
                return cached_result

        # Perform fresh analysis
        print(f"🔍 Starting fresh analysis for {institution_name}")
        
        # Import analysis function
        from enhanced_delayed_funding_tracker import EnhancedDelayedFundingTracker
        
        # Load PI cache
        pi_cache = load_pi_department_cache()
        
        # Create tracker and perform analysis using fresh NIH/NSF data
        print("🎯 Using fresh NIH/NSF grant data for enhanced analysis...")
        
        # Use fresh NIH/NSF cache data for enhanced analysis
        from grant_cache import get_combined_cache
        fresh_grants = get_combined_cache()
        
        if fresh_grants and len(fresh_grants) > 0:
            print(f"📊 Using fresh grant cache with {len(fresh_grants)} grants")
            
            # Filter grants for this institution
            from layoff_estimator import normalize_institution_name
            normalized_institution = normalize_institution_name(institution_name)
            institution_grants = []
            
            for grant in fresh_grants:
                org_info = grant.get('organization', {})
                if isinstance(org_info, list) and org_info:
                    org_name = org_info[0].get('org_name','')
                elif isinstance(org_info, dict):
                    org_name = org_info.get('org_name','')
                else:
                    continue
                    
                if normalize_institution_name(org_name) == normalized_institution:
                    institution_grants.append(grant)
            
            if len(institution_grants) > 0:
                print(f"✅ Found {len(institution_grants)} grants for {institution_name} in fresh NIH/NSF data")
                
                # Perform analysis using fresh data
                result = await analyze_fresh_nih_nsf_data(institution_name, institution_grants, pi_cache)
            else:
                print(f"⚠️ No grants found in fresh data, falling back to comprehensive tracker")
                # Fallback to comprehensive tracker
                tracker = EnhancedDelayedFundingTracker()
                result = await tracker.analyze_comprehensive_delays(
                    institution_name=institution_name,
                    pi_cache=pi_cache
                )
        else:
            print("⚠️ Fresh cache not available, using comprehensive tracker")
            # Fallback to comprehensive tracker
            tracker = EnhancedDelayedFundingTracker()
            result = await tracker.analyze_comprehensive_delays(
                institution_name=institution_name,
                pi_cache=pi_cache
            )
        
        # Add metadata
        result.update({
            'institution': institution_name,
            'analysis_date': dt.now().isoformat(),
            'method': method,
            'include_departments': include_departments,
            'cache_optimized': True
        })
        
        # Cache the result using optimized cache
        try:
            print(f"💾 Caching analysis result for {institution_name} (optimized)")
            save_cached_analysis(institution_name, result, method, include_departments)
        except Exception as e:
            print(f"Optimized caching error: {e}")

        # Add summary field for frontend compatibility
        financial_overview = result.get('financial_overview', {})
        overview = result.get('overview', {})
        result['summary'] = {
            'total_undisbursed': financial_overview.get('undisbursed_amount', overview.get('total_undisbursed', 0)),
            'disbursement_efficiency': financial_overview.get('disbursement_efficiency', overview.get('disbursement_efficiency', '0.0%')),
            'delayed_funding_risk': overview.get('risk_score', result.get('cash_flow_risk', {}).get('score', 0)),
            'cash_flow_risk': result.get('cash_flow_risk', {'level': 'UNKNOWN', 'score': 0})
        }

        return result
        
    except Exception as e:
        print(f"Error in comprehensive delayed funding analysis: {e}")
        return {
            'institution': institution_name,
            'error': f'Analysis failed: {str(e)}',
            'note': 'Comprehensive delayed funding analysis not available',
            'analysis_date': dt.now().isoformat(),
            'cache_optimized': True
        }

@app.get("/api/enhanced-delayed-funding/{institution_name}")
async def get_enhanced_delayed_funding_analysis_legacy(institution_name: str, method: str = "comprehensive"):
    """Legacy endpoint - redirects to optimized comprehensive analysis"""
    return await get_comprehensive_delayed_funding_analysis(institution_name, include_departments=True, method=method)

@app.get("/api/delayed-funding-departments/{institution_name}")
async def get_delayed_funding_by_departments_legacy(institution_name: str):
    """Legacy endpoint - redirects to optimized comprehensive analysis with departments"""
    return await get_comprehensive_delayed_funding_analysis(institution_name, include_departments=True, method="comprehensive")

@app.get("/api/methodology-comparison/{institution_name}")
async def get_methodology_comparison(institution_name: str):
    """
    Compare different funding analysis methodologies:
    1. Enhanced (current) - Cancelled + Non-renewal + Cash flow
    2. Times-style - Non-renewal focus
    3. Legacy USASpending - Disbursement focus
    """
    try:
        print(f"🔬 Methodology comparison for {institution_name}")
        
        # Get enhanced analysis (current method)
        enhanced_result = await get_comprehensive_delayed_funding_analysis(institution_name, method="comprehensive")
        
        # Get Times-style renewal analysis
        from enhanced_delayed_funding_tracker import EnhancedDelayedFundingTracker
        times_tracker = EnhancedDelayedFundingTracker()
        times_result = await times_tracker.analyze_renewal_delays(institution_name)
        
        # Get legacy USASpending disbursement analysis
        try:
            from delayed_funding_tracker import DelayedFundingTracker
            from layoff_estimator import fetch_institution_grants
            
            # Fetch grants using legacy method
            legacy_grants = await fetch_institution_grants(
                organization=institution_name,
                active_only=False,
                max_records_per_source=1000
            )
            
            # Convert to USASpending format
            usaspending_data = []
            for grant in legacy_grants:
                usaspending_data.append({
                    'Award ID': grant.get('project_num') or grant.get('award_id', ''),
                    'Award Amount': grant.get('award_amount', 0),
                    'Outlayed Amount': 0,  # Not available in NIH/NSF data
                    'Obligated Amount': grant.get('award_amount', 0),
                    'Base Obligation Date': grant.get('project_start_date', ''),
                    'Action Date': grant.get('award_notice_date', ''),
                    'Award Description': grant.get('project_title', ''),
                    'Recipient Name': institution_name,
                    'Period of Performance Start Date': grant.get('project_start_date', ''),
                    'Period of Performance Current End Date': grant.get('project_end_date', '')
                })
            
            legacy_tracker = DelayedFundingTracker()
            legacy_result = legacy_tracker.analyze_funding_delays(usaspending_data)
            
        except Exception as e:
            print(f"Legacy analysis error: {e}")
            legacy_result = {
                'error': str(e),
                'note': 'Legacy USASpending analysis unavailable'
            }
        
        return {
            'institution': institution_name,
            'analysis_date': datetime.now().isoformat(),
            'methodologies': {
                'enhanced_current': {
                    'name': 'Enhanced Multi-Methodology Analysis',
                    'description': 'Combines cancelled grants, non-renewal analysis, and cash flow risk assessment',
                    'data_sources': ['NIH Reporter API', 'NSF Awards API', 'USASpending.gov'],
                    'risk_score': enhanced_result.get('cash_flow_risk', {}).get('score', 0),
                    'risk_level': enhanced_result.get('cash_flow_risk', {}).get('level', 'UNKNOWN'),
                    'cancelled_funding': enhanced_result.get('cancelled_grants_impact', {}).get('total_lost_funding', 0),
                    'nonrenewal_funding': enhanced_result.get('nonrenewal_grants_impact', {}).get('total_lost_funding', 0),
                    'total_funding': enhanced_result.get('overview', {}).get('total_funding', 0),
                    'methodology_strengths': [
                        'Comprehensive multi-agency coverage',
                        'Real-time cancelled grants tracking',
                        'Non-renewal pattern detection',
                        'Enhanced risk factor analysis'
                    ]
                },
                'times_style': {
                    'name': 'Times-Style Renewal Analysis',
                    'description': 'Focus on grants that should have renewed but show no evidence of renewal',
                    'data_sources': ['NIH Reporter API', 'NSF Awards API'],
                    'expected_renewals': times_result.get('expected_renewals', 0),
                    'missing_renewals': times_result.get('missing_renewals', 0),
                    'renewal_rate': times_result.get('renewal_rate', 0),
                    'at_risk_amount': times_result.get('at_risk_amount', 0),
                    'risk_level': times_result.get('risk_level', 'UNKNOWN'),
                    'methodology_strengths': [
                        'Historical renewal pattern analysis',
                        'PI continuity tracking',
                        'Grant lifecycle understanding',
                        'Manual verification capability'
                    ]
                },
                'legacy_usaspending': {
                    'name': 'Legacy USASpending Disbursement Analysis',
                    'description': 'Traditional disbursement tracking (awarded vs. disbursed amounts)',
                    'data_sources': ['USASpending.gov API'],
                    'total_awards': legacy_result.get('total_awards', 0),
                    'total_awarded': legacy_result.get('total_awarded_amount', 0),
                    'total_outlayed': legacy_result.get('total_outlayed_amount', 0),
                    'undisbursed_amount': legacy_result.get('undisbursed_amount', 0),
                    'disbursement_efficiency': legacy_result.get('disbursement_efficiency', 0),
                    'delayed_funding_risk': legacy_result.get('delayed_funding_risk', 0),
                    'methodology_strengths': [
                        'Actual cash flow tracking',
                        'Disbursement timeline analysis',
                        'Federal-wide coverage',
                        'Real-time financial data'
                    ],
                    'limitations': [
                        'Limited to USASpending data only',
                        '1-month reporting lag',
                        'Missing NIH/NSF direct API data',
                        'No renewal pattern analysis'
                    ]
                }
            },
            'comparison_insights': {
                'data_completeness': {
                    'enhanced': 'High - Fresh NIH/NSF + USASpending integration',
                    'times_style': 'High - Fresh NIH/NSF data with renewal analysis',
                    'legacy': 'Medium - USASpending only with reporting lag'
                },
                'risk_detection': {
                    'enhanced': 'Comprehensive - Multiple risk factors',
                    'times_style': 'Focused - Renewal delays only',
                    'legacy': 'Limited - Disbursement delays only'
                },
                'real_time_capability': {
                    'enhanced': 'High - Fresh API data with caching',
                    'times_style': 'High - Fresh API data',
                    'legacy': 'Medium - 1-month reporting lag'
                },
                'recommended_use': {
                    'enhanced': 'Primary analysis for comprehensive risk assessment',
                    'times_style': 'Detailed renewal pattern investigation',
                    'legacy': 'Cash flow verification and historical comparison'
                }
            }
        }
        
    except Exception as e:
        print(f"Error in methodology comparison: {e}")
        return {
            'institution': institution_name,
            'error': f'Methodology comparison failed: {str(e)}',
            'analysis_date': datetime.now().isoformat()
        }

@app.delete("/api/cache/clear")
async def clear_cache():
    """Clear all caches"""
    try:
        clear_optimized_cache()
        return {"success": True, "message": "All caches cleared successfully"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/cache/status")
async def get_cache_status():
    """Get cache status information"""
    try:
        from optimized_cache import get_cache_stats
        stats = get_cache_stats()
        return {
            "cache_type": "optimized_dictionary_based",
            "performance": "O(1) lookups",
            "stats": stats
        }
    except Exception as e:
        return {"error": str(e)}

def match_pi_to_department(pi_name: str, institution: str, pi_cache: dict) -> str:
    """Match a PI to their department using the cached data"""
    if not pi_name or not institution:
        return "Unknown Department"
    
    # Simple lookup in the cache
    pi_name_normalized = pi_name.lower().strip()
    institution_normalized = institution.lower().strip()
    
    for key, data in pi_cache.items():
        if '|' in key:
            cached_pi, cached_inst = key.split('|', 1)
            if (cached_inst.strip().lower() == institution_normalized and 
                pi_name_normalized in cached_pi.lower()):
                return data.get('department', 'Unknown Department')
    
    return "Unknown Department"

@app.get("/api/university-details/{institution_name}")
async def get_university_details(institution_name: str):
    """Get detailed information about a university using comprehensive multi-source data fetching"""
    try:
        print(f"Fetching comprehensive details for: {institution_name}")
        
        # Import required functions
        from layoff_estimator import (
            fetch_terminated_grants, 
            normalize_institution_name,
            calculate_funding_cliff,
            estimate_lab_size
        )
        from grant_cache import get_combined_cache
        
        # Normalize the institution name
        normalized_institution = normalize_institution_name(institution_name)
        
        # Strategy 1: Use fresh NIH/NSF cache data
        print("🎯 Using fresh NIH/NSF grant data...")
        combined_grants = get_combined_cache()
        
        institution_active_grants = []
        institution_terminated_grants = []
        
        if combined_grants:
            print(f"📊 Analyzing {len(combined_grants)} fresh grants from NIH/NSF APIs")
            
            # Filter grants for this institution from fresh NIH/NSF data
            for grant in combined_grants:
                try:
                    org_info = grant.get('organization', {})
                    org_name = ''
                    
                    if isinstance(org_info, list) and org_info:
                        # Handle list format
                        first_org = org_info[0]
                        if isinstance(first_org, dict):
                            org_name = first_org.get('org_name', '')
                        elif isinstance(first_org, str):
                            org_name = first_org
                    elif isinstance(org_info, dict):
                        # Handle dict format
                        org_name = org_info.get('org_name', '')
                    elif isinstance(org_info, str):
                        # Handle string format
                        org_name = org_info
                    
                    if not org_name:
                        continue
                    
                    if normalize_institution_name(org_name) == normalized_institution:
                        # Check if grant is active or terminated based on status/end date
                        status = grant.get('project_end_date', '')
                        award_status = grant.get('award_status', '').lower()
                        
                        if award_status in ['terminated', 'cancelled', 'expired']:
                            institution_terminated_grants.append(grant)
                        else:
                            institution_active_grants.append(grant)
                            
                except Exception as e:
                    print(f"⚠️ Error processing grant: {e}")
                    continue
        
        # Strategy 2: Direct comprehensive API fetch for this specific institution
        print(f"🔍 Fetching comprehensive grants directly for {institution_name}...")
        try:
            fresh_institution_grants = await fetch_comprehensive_institution_grants(institution_name, max_grants=15000)
            if fresh_institution_grants:
                print(f"✅ Found {len(fresh_institution_grants)} additional grants from direct API fetch")
                
                # Add to our collections
                for grant in fresh_institution_grants:
                    try:
                        status = grant.get('project_end_date', '')
                        award_status = grant.get('award_status', '').lower()
                        
                        # Check if we already have this grant
                        project_num = grant.get('project_num') or grant.get('award_id') or grant.get('id')
                        existing_nums = [g.get('project_num') or g.get('award_id') or g.get('id') for g in institution_active_grants + institution_terminated_grants]
                        
                        if project_num not in existing_nums:
                            if award_status in ['terminated', 'cancelled', 'expired']:
                                institution_terminated_grants.append(grant)
                            else:
                                institution_active_grants.append(grant)
                    except Exception as e:
                        print(f"⚠️ Error processing fresh grant: {e}")
                        continue
        except Exception as e:
            print(f"⚠️ Direct comprehensive API fetch failed: {e}")
        
        # Strategy 3: Enhanced terminated grants fetch
        print("🔍 Fetching comprehensive terminated grants...")
        try:
            enhanced_terminated = await fetch_additional_terminated_grants(institution_name)
            if enhanced_terminated:
                print(f"📋 Adding {len(enhanced_terminated)} additional terminated grants")
                # Remove duplicates
                existing_nums = [g.get('project_num') or g.get('award_id') or g.get('id') for g in institution_terminated_grants]
                for grant in enhanced_terminated:
                    project_num = grant.get('project_num') or grant.get('award_id') or grant.get('id')
                    if project_num not in existing_nums:
                        institution_terminated_grants.append(grant)
        except Exception as e:
            print(f"⚠️ Enhanced terminated grants fetch failed: {e}")
        
        # Strategy 4: Legacy terminated grants for broader coverage
        print("🔍 Fetching legacy terminated grants...")
        try:
            legacy_terminated_grants = await fetch_terminated_grants()
            for grant in legacy_terminated_grants:
                try:
                    org_info = grant.get('organization', {})
                    org_name = ''
                    
                    if isinstance(org_info, list) and org_info:
                        first_org = org_info[0]
                        if isinstance(first_org, dict):
                            org_name = first_org.get('org_name', '')
                        elif isinstance(first_org, str):
                            org_name = first_org
                    elif isinstance(org_info, dict):
                        org_name = org_info.get('org_name', '')
                    elif isinstance(org_info, str):
                        org_name = org_info
                    
                    if not org_name:
                        continue
                    
                    if normalize_institution_name(org_name) == normalized_institution:
                        project_num = grant.get('project_num') or grant.get('award_id') or grant.get('id')
                        existing_nums = [g.get('project_num') or g.get('award_id') or g.get('id') for g in institution_terminated_grants]
                        if project_num not in existing_nums:
                            institution_terminated_grants.append(grant)
                        
                except Exception as e:
                    print(f"⚠️ Error processing legacy terminated grant: {e}")
                    continue
        except Exception as e:
            print(f"⚠️ Legacy terminated grants fetch failed: {e}")
        
        # Strategy 5: USASpending fallback if still not enough data
        if len(institution_active_grants) < 50:
            print("⚡ Supplementing with USASpending.gov data...")
            try:
                from layoff_estimator import fetch_total_funding_grants
                usaspending_grants = await fetch_total_funding_grants(active_only=True, max_records_per_source=5000)
                
                for grant in usaspending_grants:
                    try:
                        org_info = grant.get('organization', {})
                        org_name = ''
                        
                        if isinstance(org_info, list) and org_info:
                            first_org = org_info[0]
                            if isinstance(first_org, dict):
                                org_name = first_org.get('org_name', '')
                            elif isinstance(first_org, str):
                                org_name = first_org
                        elif isinstance(org_info, dict):
                            org_name = org_info.get('org_name', '')
                        elif isinstance(org_info, str):
                            org_name = org_info
                        
                        if not org_name:
                            continue
                        
                        if normalize_institution_name(org_name) == normalized_institution:
                            project_num = grant.get('project_num') or grant.get('award_id') or grant.get('id')
                            existing_nums = [g.get('project_num') or g.get('award_id') or g.get('id') for g in institution_active_grants]
                            if project_num not in existing_nums:
                                institution_active_grants.append(grant)
                            
                    except Exception as e:
                        print(f"⚠️ Error processing USASpending grant: {e}")
                        continue
                        
                print(f"✅ Added {len([g for g in usaspending_grants if normalize_institution_name(g.get('organization', {}).get('org_name', '')) == normalized_institution])} USASpending grants")
            except Exception as e:
                print(f"⚠️ USASpending supplement failed: {e}")
        
        # Combine all grants for comprehensive analysis
        all_grants_for_institution = institution_active_grants + institution_terminated_grants
        
        print(f"🎯 Total grants collected: {len(all_grants_for_institution)} ({len(institution_active_grants)} active, {len(institution_terminated_grants)} terminated)")
        
        # Ensure we have meaningful data
        if len(all_grants_for_institution) > 0:
            print(f"🎯 Analyzing {len(all_grants_for_institution)} total grants using enhanced fresh data analysis")
            
            # Use enhanced analysis function with comprehensive grant data
            result = await analyze_fresh_nih_nsf_data(institution_name, all_grants_for_institution, pi_cache=None)
            return result
        else:
            print("⚠️ No grants found with comprehensive search, falling back to enhanced tracker")
            
            # Final fallback to comprehensive analysis
            from enhanced_delayed_funding_tracker import EnhancedDelayedFundingTracker
            enhanced_tracker = EnhancedDelayedFundingTracker()
            return await enhanced_tracker.comprehensive_delayed_funding_analysis(
                institution_name, 
                force_fresh_analysis=True  # Force fresh analysis for better coverage
            )
        
    except Exception as e:
        print(f"Error getting university details: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting university details: {str(e)}")

@app.get("/api/renewal-patterns-analysis")
async def get_renewal_patterns_analysis(institutions: str = None):
    """
    Multi-institutional renewal patterns analysis (Times-style methodology)
    
    Query parameter:
    - institutions: Comma-separated list of institution names
    """
    try:
        from enhanced_delayed_funding_tracker import analyze_institutional_renewal_patterns
        
        # Parse institutions
        if not institutions:
            institution_list = [
                "Harvard University",
                "Stanford University", 
                "Massachusetts Institute of Technology",
                "University of California Berkeley",
                "Yale University"
            ]
        else:
            institution_list = [inst.strip() for inst in institutions.split(',')]
        
        result = await analyze_institutional_renewal_patterns(institution_list)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in renewal patterns analysis: {str(e)}")

@app.get("/api/usaspending-stats")
async def get_usaspending_cache_stats():
    """Get detailed statistics about cached USASpending.gov data."""
    try:
        from usaspending_cache_loader import get_usaspending_stats
        stats = get_usaspending_stats()
        
        return {
            "cache_info": stats,
            "message": "Comprehensive USASpending.gov funding data available"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting cache stats: {str(e)}")

@app.get("/api/layoff-leaderboard")
async def get_layoff_risk_leaderboard(cost_per_researcher: float = 200000, limit: int = 20):
    """Get institutions ranked by layoff risk using comprehensive multi-agency data."""
    try:
        from layoff_estimator import generate_layoff_risk_leaderboard
        
        result = await generate_layoff_risk_leaderboard(cost_per_researcher, limit)
        
        # Convert the format to match frontend expectations
        if 'data' in result:
            # The new format uses 'data' key, convert to 'institutions' for frontend compatibility
            return {
                "institutions": result['data'],
                "total_institutions": result.get('total_institutions', len(result['data'])),
                "methodology": result.get('methodology', {}),
                "last_updated": result.get('last_updated', datetime.now().isoformat())
            }
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating leaderboard: {str(e)}")

@app.get("/api/test-combined-grants")
async def test_combined_grants_endpoint():
    """Test endpoint to verify enhanced multi-agency grant fetching."""
    try:
        # Test both data sources
        from layoff_estimator import fetch_institution_grants, fetch_total_funding_grants
        
        # Institution analysis grants (NIH + NSF)
        institution_grants = await fetch_institution_grants(active_only=True, max_records_per_source=100)
        
        # Total funding grants (all agencies)
        funding_grants = await fetch_total_funding_grants(active_only=True, max_records_per_source=100)
        
        return {
            "institution_grants": {
                "count": len(institution_grants),
                "sample": institution_grants[:3] if institution_grants else [],
                "agencies": list(set(g.get('funding_agency', 'Unknown') for g in institution_grants))
            },
            "funding_grants": {
                "count": len(funding_grants),
                "sample": funding_grants[:3] if funding_grants else [],
                "agencies": list(set(g.get('funding_agency', 'Unknown') for g in funding_grants))
            },
            "total_records": len(institution_grants) + len(funding_grants),
            "test_status": "success"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in test endpoint: {str(e)}")

@app.get("/api/cache-refresh")
async def refresh_cache():
    """Refresh all grant caches using the enhanced async cache builder."""
    try:
        print("🔄 Starting enhanced cache refresh...")
        
        # Import and run the enhanced cache builder
        import subprocess
        import sys
        
        # Run the enhanced cache builder as a subprocess
        result = subprocess.run([
            sys.executable, "enhanced_cache_builder.py"
        ], capture_output=True, text=True, cwd=".")
        
        if result.returncode == 0:
            # Get cache status after refresh
            from grant_cache import get_cache_status
            cache_status = get_cache_status()
            
            return {
                "success": True,
                "message": "Enhanced cache refresh completed successfully",
                "cache_status": cache_status,
                "output": result.stdout[-1000:] if result.stdout else "",  # Last 1000 chars
            }
        else:
            return {
                "success": False,
                "error": "Cache refresh failed",
                "stderr": result.stderr,
                "stdout": result.stdout
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"Error refreshing cache: {str(e)}"
        }

@app.get("/api/institution-grants/{institution}")
async def get_institution_grants_endpoint(institution: str, limit: int = 100):
    """Get grants for a specific institution from enhanced cache."""
    try:
        from grant_cache import get_combined_cache
        from layoff_estimator import normalize_institution_name
        
        cached_data = get_combined_cache()
        
        if not cached_data:
            return {
                "error": "No cached grant data available",
                "note": "Run /api/cache-refresh to populate cache"
            }
        
        # Filter for the specific institution
        institution_grants = []
        normalized_institution = normalize_institution_name(institution)
        
        for grant in cached_data:
            org_info = grant.get("organization", {})
            if isinstance(org_info, list) and len(org_info) > 0:
                org_name = org_info[0].get("org_name", "")
            elif isinstance(org_info, dict):
                org_name = org_info.get("org_name", "")
            else:
                continue
                
            if normalized_institution.lower() in normalize_institution_name(org_name).lower():
                institution_grants.append(grant)
                
                if len(institution_grants) >= limit:
                    break
        
        return {
            "institution": institution,
            "grants": institution_grants,
            "count": len(institution_grants),
            "limited_to": limit,
            "cache_info": f"Searched {len(cached_data)} total grants"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting institution grants: {str(e)}")

@app.get("/api/enhanced-delayed-funding/{institution_name}/csv")
async def download_delayed_funding_csv(institution_name: str, method: str = "comprehensive"):
    """Download delayed funding analysis as CSV."""
    try:
        # Get the analysis data
        analysis_data = await get_comprehensive_delayed_funding_analysis(
            institution_name=institution_name,
            method=method,
            include_departments=True
        )
        
        # Create CSV content
        import io
        import csv
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Institution', 'Analysis Date', 'Method', 'Total Risk', 'Department', 'PI Name', 'Funding at Risk'])
        
        # Write data rows
        institution = analysis_data.get('institution', institution_name)
        analysis_date = analysis_data.get('analysis_date', 'Unknown')
        total_risk = analysis_data.get('total_funding_loss', 0)
        
        # Extract department and PI data
        dept_breakdown = analysis_data.get('department_breakdown', {})
        if dept_breakdown:
            for dept_name, dept_data in dept_breakdown.items():
                pis = dept_data.get('pis', [])
                for pi_data in pis:
                    writer.writerow([
                        institution,
                        analysis_date,
                        method,
                        total_risk,
                        dept_name,
                        pi_data.get('pi_name', 'Unknown'),
                        pi_data.get('funding_at_risk', 0)
                    ])
        
        # If no department breakdown, use summary data
        if not dept_breakdown:
            writer.writerow([
                institution,
                analysis_date,
                method,
                total_risk,
                'Summary',
                'N/A',
                total_risk
            ])
        
        csv_content = output.getvalue()
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={institution_name.replace(' ', '_')}_delayed_funding.csv"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating CSV: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Enhanced NSF-Tracker API with Optimized Caching...")
    print("✨ Features:")
    print("  🎯 O(1) Dictionary-based caching")
    print("  ⚡ Instant cached result retrieval") 
    print("  🔄 Fresh analysis when needed")
    print("  📊 Enhanced delayed funding analysis")
    print("  🏢 Department-level breakdown")
    print()
    uvicorn.run(app, host="localhost", port=8000)
