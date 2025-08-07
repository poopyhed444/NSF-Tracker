#!/usr/bin/env python3
"""
Clean FastAPI server for NSF-Tracker with enhanced multi-agency integration.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import asyncio
import json
import os
from layoff_estimator import fetch_institution_grants, fetch_total_funding_grants, normalize_institution_name, fetch_terminated_grants
from grant_cache import clear_cache
from collections import defaultdict
from department_costs import get_department_cost_per_researcher, get_department_risk_multiplier
from usaspending_cache_loader import get_usaspending_funding, get_usaspending_stats
from delayed_funding_tracker import analyze_delayed_funding_for_institution, analyze_delayed_funding_with_departments
import pandas as pd

app = FastAPI(title="NSF-Tracker Enhanced API", version="2.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "NSF-Tracker Enhanced API", 
        "version": "2.0.0",
        "features": [
            "Direct NIH Reporter API integration",
            "Direct NSF Awards API integration", 
            "USASpending.gov DoD/DoE integration",
            "Enhanced funding diversification tracking"
        ]
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

def match_pi_to_department(pi_name: str, institution: str, pi_cache: dict) -> str:
    """Match a PI to their department using the cached data"""
    if not pi_name or not institution:
        return "Unknown Department"
    
    # Normalize PI name and institution for lookup
    pi_key = f"{pi_name.lower().strip()}|{institution.lower().strip()}"
    
    # Direct lookup
    if pi_key in pi_cache:
        return pi_cache[pi_key].get('department', 'Unknown Department')
    
    # Try partial matching on PI name within the same institution
    pi_name_normalized = pi_name.lower().strip()
    institution_normalized = institution.lower().strip()
    
    for key, data in pi_cache.items():
        if '|' in key:
            cached_pi, cached_inst = key.split('|', 1)
            if (cached_inst.strip() == institution_normalized and 
                pi_name_normalized in cached_pi):
                return data.get('department', 'Unknown Department')
    
    return "Unknown Department"

@app.get("/api/university-details/{institution_name}")
async def get_university_details(institution_name: str):
    """Get detailed information about a university including cancelled grants by department"""
    try:
        print(f"Fetching details for: {institution_name}")
        
        # Normalize the institution name
        normalized_institution = normalize_institution_name(institution_name)
        
        # Get USASpending funding data
        usaspending_funding = get_usaspending_funding(normalized_institution)
        
        # Get terminated grants
        terminated_grants = await fetch_terminated_grants()
        nsf_terminated = await fetch_institution_grants(active_only=False, max_records_per_source=1000)
        nsf_terminated = [g for g in nsf_terminated if g.get('award_status', '').lower() in ['terminated', 'cancelled', 'expired']]
        all_terminated_grants = terminated_grants + nsf_terminated
        
        # Load PI department cache
        pi_cache = load_pi_department_cache()
        
        # Filter terminated grants for this institution
        institution_terminated_grants = []
        for grant in all_terminated_grants:
            org_info = grant.get("organization", {})
            if isinstance(org_info, list) and len(org_info) > 0:
                org_name = org_info[0].get("org_name", "")
            elif isinstance(org_info, dict):
                org_name = org_info.get("org_name", "")
            else:
                continue
                
            grant_institution = normalize_institution_name(org_name)
            if grant_institution == normalized_institution:
                institution_terminated_grants.append(grant)
        
        # Group grants by department
        department_grants = defaultdict(list)
        total_terminated_funding_by_dept = defaultdict(float)
        
        for grant in institution_terminated_grants:
            pi_name = grant.get("contact_pi_name", "").strip()
            funding_agency = grant.get("funding_agency", "Unknown")
            award_amount = grant.get("award_amount", 0) or 0
            
            # Match PI to department
            department = match_pi_to_department(pi_name, institution_name, pi_cache)
            
            # Add grant details
            grant_detail = {
                "pi_name": pi_name,
                "project_title": grant.get("project_title", ""),
                "award_amount": award_amount,
                "funding_agency": funding_agency,
                "project_start_date": grant.get("project_start_date", ""),
                "project_end_date": grant.get("project_end_date", ""),
                "fiscal_year": grant.get("fiscal_year", ""),
                "award_id": grant.get("core_project_num", "") or grant.get("award_id", "")
            }
            
            department_grants[department].append(grant_detail)
            total_terminated_funding_by_dept[department] += award_amount
        
        # Calculate department statistics
        department_stats = []
        for dept, grants in department_grants.items():
            total_funding = total_terminated_funding_by_dept[dept]
            positions_at_risk = total_funding / 200000  # Assuming $200k per researcher
            
            # Count unique PIs
            unique_pis = len(set(grant["pi_name"] for grant in grants if grant["pi_name"]))
            
            # Agency breakdown
            agency_counts = defaultdict(int)
            agency_funding = defaultdict(float)
            for grant in grants:
                agency = grant["funding_agency"]
                agency_counts[agency] += 1
                agency_funding[agency] += grant["award_amount"]
            
            department_stats.append({
                "department": dept,
                "total_terminated_funding": round(total_funding, 2),
                "grants_count": len(grants),
                "unique_pis": unique_pis,
                "estimated_positions_at_risk": round(positions_at_risk, 1),
                "agency_breakdown": {
                    "counts": dict(agency_counts),
                    "funding": {k: round(v, 2) for k, v in agency_funding.items()}
                },
                "grants": grants
            })
        
        # Sort departments by funding at risk
        department_stats.sort(key=lambda x: x["total_terminated_funding"], reverse=True)
        
        # Calculate overall university statistics
        total_terminated_funding = sum(total_terminated_funding_by_dept.values())
        total_active_funding = usaspending_funding.get('total_usaspending_funding', 0)
        
        # Get delayed funding analysis (basic summary)
        delayed_funding_summary = None
        try:
            delayed_funding_data = await analyze_delayed_funding_for_institution(normalized_institution)
            if delayed_funding_data and 'summary' in delayed_funding_data:
                delayed_funding_summary = {
                    "cash_flow_risk": delayed_funding_data['summary']['cash_flow_risk'],
                    "undisbursed_amount": delayed_funding_data['summary']['total_undisbursed'],
                    "disbursement_efficiency": delayed_funding_data['summary']['disbursement_efficiency'],
                    "delayed_awards_count": delayed_funding_data['summary']['awards_with_significant_delays']
                }
        except Exception as e:
            print(f"Could not fetch delayed funding data: {e}")
            delayed_funding_summary = {
                "cash_flow_risk": "UNKNOWN",
                "undisbursed_amount": 0,
                "disbursement_efficiency": "N/A",
                "delayed_awards_count": 0,
                "note": "Delayed funding analysis not available"
            }
        
        return {
            "institution": institution_name,
            "normalized_name": normalized_institution,
            "overview": {
                "total_active_funding": round(total_active_funding, 2),
                "total_terminated_funding": round(total_terminated_funding, 2),
                "funding_cliff_percentage": round((total_terminated_funding / max(total_active_funding, 1)) * 100, 1),
                "total_departments_affected": len(department_stats),
                "total_pis_affected": sum(dept["unique_pis"] for dept in department_stats),
                "total_grants_terminated": sum(dept["grants_count"] for dept in department_stats),
                "estimated_total_positions_at_risk": round(total_terminated_funding / 200000, 1)
            },
            "funding_breakdown": {
                "nih_funding": round(usaspending_funding.get('nih_funding', 0), 2),
                "nsf_funding": round(usaspending_funding.get('nsf_funding', 0), 2),
                "dod_funding": round(usaspending_funding.get('dod_funding', 0), 2),
                "doe_funding": round(usaspending_funding.get('doe_funding', 0), 2),
                "nasa_funding": round(usaspending_funding.get('nasa_funding', 0), 2),
                "other_funding": round(usaspending_funding.get('other_funding', 0), 2),
                "agencies_with_funding": len([f for f in [
                    usaspending_funding.get('nih_funding', 0),
                    usaspending_funding.get('nsf_funding', 0),
                    usaspending_funding.get('dod_funding', 0),
                    usaspending_funding.get('doe_funding', 0),
                    usaspending_funding.get('nasa_funding', 0),
                    usaspending_funding.get('other_funding', 0)
                ] if f > 0])
            },
            "delayed_funding": delayed_funding_summary,
            "departments": department_stats,
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"Error getting university details: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting university details: {str(e)}")

@app.get("/api/delayed-funding/{institution_name}")
async def get_comprehensive_delayed_funding_analysis(institution_name: str, include_departments: bool = True, method: str = "comprehensive"):
    """
    Comprehensive delayed funding analysis combining:
    - Enhanced Times-style renewal analysis
    - Disbursement tracking
    - Department-level breakdown
    - Risk assessment and recommendations
    
    Parameters:
    - include_departments: Include department-level analysis
    - method: 'disbursement', 'renewal', or 'comprehensive' (default)
    """
    try:
        print(f"🔍 DEBUG: Comprehensive delayed funding analysis for: {institution_name} (method: {method}, departments: {include_departments})")
        print(f"🔍 DEBUG: Method is: '{method}', checking if in ['comprehensive', 'renewal']")
        
        # Check cache first
        cache_key = f"comprehensive_delayed_funding_{institution_name}_{method}_{include_departments}"
        cached_result = None
        try:
            from grant_cache import get_combined_cache
            cached_data = get_combined_cache()
            if cached_data:
                for item in cached_data:
                    if item.get('cache_key') == cache_key:
                        # Check if cache is still valid (1 hour)
                        cache_time = datetime.fromisoformat(item.get('cached_at', '2000-01-01'))
                        if (datetime.now() - cache_time).total_seconds() < 3600:  # 1 hour cache
                            print(f"Using cached result for {institution_name}")
                            cached_result = item.get('data')
                            break
        except Exception as e:
            print(f"Cache check error: {e}")
        
        if cached_result:
            return cached_result
        
        # Initialize result structure
        result = {
            "institution": institution_name,
            "analysis_date": datetime.now().isoformat(),
            "methodology": "Comprehensive delayed funding analysis",
            "cash_flow_risk": {"level": "UNKNOWN", "score": 0, "risk_factors": [], "severity": "UNKNOWN"},
            "financial_overview": {
                "total_awarded": 0,
                "total_obligated": 0,
                "total_disbursed": 0,
                "undisbursed_amount": 0,
                "disbursement_efficiency": "0.0%",
                "undisbursed_percentage": "0.0%"
            },
            "delayed_awards": {"count": 0, "total_awards_analyzed": 0, "delay_frequency": "0.0%", "awards_details": []},
            "implications": {
                "estimated_cash_flow_impact": "LOW",
                "operational_risk": "Minimal impact expected",
                "recommended_actions": []
            }
        }
        
        # 1. Standard disbursement analysis
        disbursement_analysis = None
        try:
            disbursement_data = await analyze_delayed_funding_for_institution(institution_name)
            if disbursement_data and not disbursement_data.get('error'):
                disbursement_analysis = disbursement_data
                analysis = disbursement_data['disbursement_analysis']
                summary = disbursement_data['summary']
                
                # Update financial overview
                result["financial_overview"] = {
                    "total_awarded": round(analysis.get('total_awarded_amount', 0), 2),
                    "total_obligated": round(analysis.get('total_obligated_amount', 0), 2),
                    "total_disbursed": round(analysis.get('total_outlayed_amount', 0), 2),
                    "undisbursed_amount": round(analysis.get('undisbursed_amount', 0), 2),
                    "disbursement_efficiency": f"{analysis.get('disbursement_efficiency', 0)*100:.1f}%",
                    "undisbursed_percentage": f"{(analysis.get('undisbursed_amount', 0)/max(analysis.get('total_awarded_amount', 1), 1))*100:.1f}%"
                }
                
                # Update delayed awards
                result["delayed_awards"] = {
                    "count": analysis.get('delayed_awards_count', 0),
                    "total_awards_analyzed": analysis.get('total_awards', 0),
                    "delay_frequency": f"{(analysis.get('delayed_awards_count', 0)/max(analysis.get('total_awards', 1), 1))*100:.1f}%",
                    "awards_details": analysis.get('awards_with_delays', [])[:5]
                }
                
                # Calculate risk factors
                risk_factors = []
                risk_score = summary.get('delayed_funding_risk_score', 0)
                if analysis.get('delayed_funding_risk', 0) >= 50:
                    risk_factors.append("High percentage of undisbursed awards")
                if analysis.get('disbursement_efficiency', 1) < 0.6:
                    risk_factors.append("Low disbursement efficiency")
                if analysis.get('delayed_awards_count', 0) > 5:
                    risk_factors.append("Multiple awards with significant delays")
                if analysis.get('undisbursed_amount', 0) > 10000000:
                    risk_factors.append("Large absolute amount of undisbursed funding")
                
                # Update cash flow risk
                result["cash_flow_risk"] = {
                    "level": summary.get('cash_flow_risk', 'UNKNOWN'),
                    "score": risk_score,
                    "risk_factors": risk_factors,
                    "severity": "IMMEDIATE ATTENTION" if risk_score >= 75 else 
                              "MONITOR CLOSELY" if risk_score >= 50 else
                              "STABLE" if risk_score >= 25 else "LOW RISK"
                }
                
                # Update implications
                result["implications"] = {
                    "estimated_cash_flow_impact": "HIGH" if analysis.get('undisbursed_amount', 0) > 20000000 else
                                                "MEDIUM" if analysis.get('undisbursed_amount', 0) > 5000000 else "LOW",
                    "operational_risk": "Research operations may be constrained by delayed disbursements" if risk_score >= 50 else
                                      "Minimal impact on research operations expected",
                    "recommended_actions": [action for action in [
                        "Contact agency program officers to expedite disbursements" if analysis.get('delayed_awards_count', 0) > 3 else None,
                        "Review grant compliance and reporting requirements" if analysis.get('disbursement_efficiency', 1) < 0.5 else None,
                        "Consider bridge funding for critical research activities" if analysis.get('undisbursed_amount', 0) > 10000000 else None,
                        "Monitor cash flow closely for next 6 months" if risk_score >= 50 else None
                    ] if action is not None]
                }
        except Exception as e:
            print(f"Disbursement analysis error: {e}")
        
        # 2. Enhanced Times-style analysis (if method allows)
        enhanced_analysis = None
        if method in ["comprehensive", "renewal"]:
            try:
                print(f"Starting enhanced analysis for {institution_name}...")
                from enhanced_delayed_funding_tracker import EnhancedDelayedFundingTracker
                enhanced_tracker = EnhancedDelayedFundingTracker()
                pi_cache = load_pi_department_cache()
                enhanced_data = await enhanced_tracker.analyze_comprehensive_delays(institution_name, pi_cache)
                print(f"Enhanced analysis completed. Keys: {list(enhanced_data.keys()) if enhanced_data else 'None'}")
                
                if enhanced_data and not enhanced_data.get('error'):
                    enhanced_analysis = enhanced_data
                    
                    # Add enhanced methodology info
                    result["methodology"] = "Enhanced Times-style analysis + disbursement tracking"
                    result["enhanced_analysis"] = {
                        "overall_risk_level": enhanced_data.get('overall_risk_level', 'UNKNOWN'),
                        "combined_risk_score": enhanced_data.get('combined_risk_score', 0),
                        "total_at_risk_funding": enhanced_data.get('total_at_risk', 0),
                        "immediate_concerns": enhanced_data.get('immediate_concerns', []),
                        "renewal_analysis": enhanced_data.get('renewal_analysis', {}),
                        "disbursement_analysis": enhanced_data.get('disbursement_analysis', {})
                    }
                    print(f"Enhanced analysis added to result")
                    
                    # Update risk assessment if enhanced data suggests higher risk
                    enhanced_risk_score = enhanced_data.get('combined_risk_score', 0)
                    if enhanced_risk_score > result["cash_flow_risk"]["score"]:
                        result["cash_flow_risk"]["score"] = enhanced_risk_score
                        result["cash_flow_risk"]["level"] = enhanced_data.get('overall_risk_level', result["cash_flow_risk"]["level"])
                        
                        # Add enhanced concerns to risk factors
                        enhanced_concerns = enhanced_data.get('immediate_concerns', [])
                        if enhanced_concerns:
                            result["cash_flow_risk"]["risk_factors"].extend(enhanced_concerns)
                    
                    # Add enhanced recommendations
                    enhanced_actions = enhanced_data.get('recommended_actions', [])
                    if enhanced_actions:
                        result["implications"]["recommended_actions"].extend(enhanced_actions)
            except Exception as e:
                print(f"Enhanced analysis error: {e}")
        
        # 3. Department-level analysis (if requested)
        if include_departments:
            try:
                pi_cache = load_pi_department_cache()
                dept_analysis = await analyze_delayed_funding_with_departments(institution_name, pi_cache)
                
                if dept_analysis and not dept_analysis.get('error'):
                    result["department_analysis"] = {
                        "departments": dept_analysis.get('departments', []),
                        "highest_risk": dept_analysis.get('highest_risk_departments', [])[:5],
                        "summary_by_risk": {
                            risk: len([d for d in dept_analysis.get('departments', []) if d.get('risk_level') == risk])
                            for risk in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']
                        }
                    }
                    
                    result["overview"] = {
                        "total_undisbursed": round(dept_analysis.get('overall_summary', {}).get('total_undisbursed', 0), 2),
                        "disbursement_efficiency": dept_analysis.get('overall_summary', {}).get('disbursement_efficiency', 'N/A'),
                        "cash_flow_risk": dept_analysis.get('overall_summary', {}).get('cash_flow_risk', 'UNKNOWN'),
                        "risk_score": dept_analysis.get('overall_summary', {}).get('delayed_funding_risk_score', 0),
                        "departments_affected": dept_analysis.get('overall_summary', {}).get('total_departments_affected', 0),
                        "high_risk_departments": dept_analysis.get('overall_summary', {}).get('high_risk_departments', 0)
                    }
                    
                    result["institutional_impact"] = {
                        "total_positions_potentially_affected": sum(d.get('estimated_positions_affected', 0) for d in dept_analysis.get('departments', [])),
                        "most_underfunded_department": dept_analysis.get('departments', [{}])[0].get('department') if dept_analysis.get('departments') else None,
                        "total_delayed_awards": sum(d.get('delayed_awards_count', 0) for d in dept_analysis.get('departments', [])),
                        "departments_needing_immediate_attention": len([d for d in dept_analysis.get('departments', []) if d.get('risk_level') == 'CRITICAL'])
                    }
                    
                    result["recommendations"] = {
                        "priority_departments": [
                            {
                                "department": dept['department'],
                                "undisbursed_amount": dept['total_undisbursed'],
                                "action": "Immediate intervention required" if dept['risk_level'] == 'CRITICAL' else
                                        "Monitor closely" if dept['risk_level'] == 'HIGH' else "Routine monitoring"
                            }
                            for dept in dept_analysis.get('departments', [])[:3]
                        ],
                        "next_steps": [
                            "Focus on departments with CRITICAL risk levels",
                            "Review grant compliance for delayed awards",
                            "Contact program officers for expedited processing",
                            "Consider interim funding for critical research"
                        ] if any(d.get('risk_level') == 'CRITICAL' for d in dept_analysis.get('departments', [])) else [
                            "Continue monitoring disbursement patterns",
                            "Maintain good grant compliance practices"
                        ]
                    }
            except Exception as e:
                print(f"Department analysis error: {e}")
        
        # Add sample delayed awards if available
        if disbursement_analysis:
            result["sample_delayed_awards"] = disbursement_analysis.get('raw_disbursement_data', [])[:3]
        
        result["last_updated"] = datetime.now().isoformat()
        
        # Cache the result
        try:
            from grant_cache import save_combined_cache, get_combined_cache
            cached_data = get_combined_cache() or []
            cached_data.append({
                'cache_key': cache_key,
                'cached_at': datetime.now().isoformat(),
                'data': result
            })
            save_combined_cache(cached_data)
            print(f"Cached comprehensive analysis for {institution_name}")
        except Exception as e:
            print(f"Caching error: {e}")
        
        return result
        
    except Exception as e:
        print(f"Error in comprehensive delayed funding analysis: {e}")
        return {
            "institution": institution_name,
            "error": f"Analysis failed: {str(e)}",
            "note": "Comprehensive delayed funding analysis not available",
            "analysis_date": datetime.now().isoformat()
        }

@app.get("/api/enhanced-delayed-funding/{institution_name}")
async def get_enhanced_delayed_funding_analysis_legacy(institution_name: str, method: str = "comprehensive"):
    """
    Legacy endpoint - redirects to comprehensive analysis
    Maintained for backward compatibility
    """
    return await get_comprehensive_delayed_funding_analysis(institution_name, include_departments=True, method=method)

@app.get("/api/delayed-funding-departments/{institution_name}")
async def get_delayed_funding_by_departments_legacy(institution_name: str):
    """
    Legacy endpoint - redirects to comprehensive analysis with departments
    Maintained for backward compatibility
    """
    return await get_comprehensive_delayed_funding_analysis(institution_name, include_departments=True, method="comprehensive")

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
        
        print(f"Analyzing renewal patterns for {len(institution_list)} institutions")
        
        # Get multi-institutional analysis
        analysis = await analyze_institutional_renewal_patterns(institution_list)
        
        # Format for API response
        return {
            "analysis_date": analysis['analysis_date'],
            "methodology": "Times-style multi-institutional renewal pattern analysis",
            "institutions_analyzed": len(institution_list),
            "summary": {
                "institutions_with_delays": analysis['overall_statistics']['institutions_with_delays'],
                "percentage_with_delays": f"{analysis['summary']['percentage_with_delays']:.1f}%",
                "total_missing_renewals": analysis['overall_statistics']['total_missing_renewals'],
                "total_funding_at_risk": analysis['overall_statistics']['total_at_risk_funding'],
                "average_missing_renewals_per_institution": f"{analysis['summary']['average_missing_renewals']:.1f}"
            },
            "institutional_breakdown": {
                inst: {
                    "missing_renewals": result.get('missing_renewals', 0),
                    "renewal_rate": f"{result.get('renewal_rate', 0):.1f}%",
                    "at_risk_funding": result.get('at_risk_amount', 0),
                    "risk_level": result.get('risk_level', 'Unknown'),
                    "error": result.get('error')
                }
                for inst, result in analysis['institutional_results'].items()
            },
            "insights": {
                "most_affected_institutions": sorted(
                    [(inst, result.get('missing_renewals', 0)) 
                     for inst, result in analysis['institutional_results'].items() 
                     if not result.get('error')],
                    key=lambda x: x[1], reverse=True
                )[:5],
                "methodology_notes": [
                    "Based on NYT methodology for detecting delayed funding",
                    "Focuses on grants eligible for continuation/renewal",
                    "Accounts for typical reporting lag periods",
                    "Uses historical renewal timing patterns"
                ]
            }
        }
        
    except Exception as e:
        print(f"Error in renewal patterns analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Error in renewal patterns analysis: {str(e)}")

async def generate_comprehensive_leaderboard(cost_per_researcher: float = 200000, limit: int = 20) -> dict:
    """
    Generate leaderboard using:
    - CACHED USASpending.gov data for ACTIVE FUNDING (comprehensive $130B+ dataset)
    - NIH/NSF APIs for TERMINATED/CANCELLED grants (research-specific risk analysis)
    
    This provides accurate funding totals with precise research risk assessment.
    """
    try:
        print("Loading comprehensive USASpending.gov funding data from cache...")
        
        # Check cache stats
        try:
            cache_stats = get_usaspending_stats()
            print(f"DEBUG: Cache stats result: {cache_stats}")
        except Exception as e:
            print(f"DEBUG: Error getting cache stats: {e}")
            cache_stats = None
            
        if not cache_stats:
            return {
                "error": "USASpending.gov cache not available",
                "note": "Run usaspending_cache_builder.py to build the cache"
            }
        
        print(f"Cache loaded: {cache_stats['total_grants']:,} grants, ${cache_stats['total_funding']:,.0f}")
        
        print("Fetching terminated grants from NIH/NSF (research-specific risk)...")
        # Use NIH/NSF for terminated grants - research-specific risk analysis
        terminated_grants = await fetch_terminated_grants()  # This gets NIH terminated
        
        # Also get NSF terminated grants
        nsf_terminated = await fetch_institution_grants(active_only=False, max_records_per_source=1000)
        nsf_terminated = [g for g in nsf_terminated if g.get('award_status', '').lower() in ['terminated', 'cancelled', 'expired']]
        
        # Combine terminated research grants
        all_terminated_grants = terminated_grants + nsf_terminated
        
        print(f"Terminated research grants: {len(terminated_grants)} NIH + {len(nsf_terminated)} NSF = {len(all_terminated_grants)} total")
        
        # Get institutions from terminated grants to ensure we have risk data
        institution_data = defaultdict(lambda: {
            "terminated_grants": [],
            "total_terminated_funding": 0,
            "terminated_nih_funding": 0,
            "terminated_nsf_funding": 0
        })
        
        # Process terminated research grants (NIH + NSF for research-specific risk)
        for grant in all_terminated_grants:
            org_info = grant.get("organization", {})
            if isinstance(org_info, list) and len(org_info) > 0:
                org_name = org_info[0].get("org_name", "Unknown")
            elif isinstance(org_info, dict):
                org_name = org_info.get("org_name", "Unknown")
            else:
                continue
                
            normalized_name = normalize_institution_name(org_name)
            
            if normalized_name != "Unknown":
                institution_data[normalized_name]["terminated_grants"].append(grant)
                try:
                    amount = float(grant.get("award_amount", 0))
                    institution_data[normalized_name]["total_terminated_funding"] += amount
                    
                    # Track terminated funding by research agency
                    funding_agency = grant.get("funding_agency", "").upper()
                    if funding_agency == "NIH":
                        institution_data[normalized_name]["terminated_nih_funding"] += amount
                    elif funding_agency == "NSF":
                        institution_data[normalized_name]["terminated_nsf_funding"] += amount
                        
                except (ValueError, TypeError):
                    pass
        
        # Calculate risk scores for each institution
        institution_results = []
        
        for institution, terminated_data in institution_data.items():
            # Get comprehensive USASpending.gov funding data from cache
            usaspending_funding = get_usaspending_funding(institution)
            
            total_active_funding = usaspending_funding.get('total_usaspending_funding', 0)
            
            if total_active_funding > 50000:  # Only include institutions with meaningful funding
                
                # Calculate funding cliff percentage based on research grant terminations vs total funding
                terminated_research_funding = terminated_data["total_terminated_funding"]
                
                # Risk calculation: terminated research funding vs total active funding
                research_funding_at_risk = min(100.0, (terminated_research_funding / max(total_active_funding, 1)) * 100)
                
                # Get agency breakdown from USASpending cache
                nih_funding = usaspending_funding.get('nih_funding', 0)
                nsf_funding = usaspending_funding.get('nsf_funding', 0)
                dod_funding = usaspending_funding.get('dod_funding', 0)
                doe_funding = usaspending_funding.get('doe_funding', 0)
                nasa_funding = usaspending_funding.get('nasa_funding', 0)
                other_funding = usaspending_funding.get('other_funding', 0)
                
                # Calculate diversification metrics (based on USASpending.gov comprehensive data)
                total_agencies = sum([
                    1 if nih_funding > 0 else 0,
                    1 if nsf_funding > 0 else 0,
                    1 if dod_funding > 0 else 0,
                    1 if doe_funding > 0 else 0,
                    1 if nasa_funding > 0 else 0,
                    1 if other_funding > 0 else 0
                ])
                
                # Calculate percentages
                nih_pct = (nih_funding / total_active_funding * 100) if total_active_funding > 0 else 0
                nsf_pct = (nsf_funding / total_active_funding * 100) if total_active_funding > 0 else 0
                dod_pct = (dod_funding / total_active_funding * 100) if total_active_funding > 0 else 0
                doe_pct = (doe_funding / total_active_funding * 100) if total_active_funding > 0 else 0
                nasa_pct = (nasa_funding / total_active_funding * 100) if total_active_funding > 0 else 0
                other_pct = (other_funding / total_active_funding * 100) if total_active_funding > 0 else 0
                
                # Diversification bonus
                diversification_bonus = 0.0
                if total_agencies >= 5:
                    diversification_bonus = 30.0
                elif total_agencies == 4:
                    diversification_bonus = 25.0
                elif total_agencies == 3:
                    diversification_bonus = 15.0
                elif total_agencies == 2:
                    diversification_bonus = 10.0
                
                # Calculate estimated lab size based on total funding
                estimated_lab_size = total_active_funding / cost_per_researcher
                
                # Calculate research positions at risk based on terminated research funding
                research_positions_at_risk = terminated_research_funding / cost_per_researcher
                
                # Calculate risk score (0-100, higher = more risk)
                # Focus on research funding risk since that's what affects academic positions
                research_cliff_factor = research_funding_at_risk * 0.5  # 50% weight - research-specific risk
                recent_loss_factor = min(40.0, (terminated_research_funding / max(total_active_funding, 1)) * 100) * 0.3  # 30% weight
                concentration_risk = (100 - diversification_bonus) * 0.2  # 20% weight - agency concentration
                
                base_risk_score = research_cliff_factor + recent_loss_factor + concentration_risk
                final_risk_score = max(0, base_risk_score - (diversification_bonus * 0.1))
                
                # Determine risk level
                if final_risk_score >= 70:
                    risk_level = "CRITICAL"
                elif final_risk_score >= 50:
                    risk_level = "HIGH"
                elif final_risk_score >= 30:
                    risk_level = "MODERATE"
                else:
                    risk_level = "LOW"
                
                institution_results.append({
                    "institution": institution,
                    "risk_score": round(final_risk_score, 1),
                    "estimated_lab_size": round(estimated_lab_size, 1),
                    "at_risk_positions": round(research_positions_at_risk, 1),  # Based on terminated research grants
                    "recently_lost_positions": round(terminated_research_funding / cost_per_researcher, 1),
                    "funding_cliff_percentage": round(research_funding_at_risk, 1),
                    "total_active_funding": round(total_active_funding, 2),  # USASpending.gov cached total
                    "active_grants_count": usaspending_funding.get('grants_count', 0),
                    "terminated_grants_count": len(terminated_data["terminated_grants"]),
                    "weighted_cost_per_researcher": cost_per_researcher,
                    "department_risk_multiplier": 1.0,
                    "funding_diversification": {
                        "nih_funding": round(nih_funding, 2),
                        "nsf_funding": round(nsf_funding, 2),
                        "dod_funding": round(dod_funding, 2),
                        "doe_funding": round(doe_funding, 2),
                        "nasa_funding": round(nasa_funding, 2),
                        "other_funding": round(other_funding, 2),
                        "nih_percentage": round(nih_pct, 1),
                        "nsf_percentage": round(nsf_pct, 1),
                        "dod_percentage": round(dod_pct, 1),
                        "doe_percentage": round(doe_pct, 1),
                        "nasa_percentage": round(nasa_pct, 1),
                        "other_percentage": round(other_pct, 1),
                        "agencies_with_funding": total_agencies,
                        "diversification_bonus": round(diversification_bonus, 1),
                        "terminated_research_funding": round(terminated_research_funding, 2)
                    },
                    "top_departments": [{"department": "Multiple", "grants": usaspending_funding.get('grants_count', 0), "funding": round(total_active_funding, 2), "percentage": 100.0}],
                    "risk_level": risk_level
                })
        
        # Sort by risk score (highest first)
        institution_results.sort(key=lambda x: x["risk_score"], reverse=True)
        
        # Limit results
        limited_results = institution_results[:limit]
        
        return {
            "institutions": limited_results,
            "total_institutions": len(institution_results),
            "methodology": {
                "risk_factors": [
                    "Research funding cliff (terminated NIH/NSF grants vs total funding) - 50% weight",
                    "Recent research funding loss ratio - 30% weight",
                    "Agency concentration penalty - 20% weight",
                    "Multi-agency diversification bonus (up to 30% risk reduction)"
                ],
                "funding_calculation": "Cached USASpending.gov data ($130B+ comprehensive dataset)",
                "risk_calculation": "Terminated NIH/NSF research grants (research-specific risk)",
                "cache_info": cache_stats,
                "diversification_tiers": [
                    "Single agency: No risk reduction",
                    "2 agencies: 10% risk reduction",
                    "3 agencies: 15% risk reduction", 
                    "4 agencies: 25% risk reduction",
                    "5+ agencies: 30% risk reduction"
                ],
                "data_sources": [
                    f"Active funding: Cached USASpending.gov ({cache_stats['total_grants']:,} grants)",
                    "Risk analysis: NIH RePORTER + NSF Awards (terminated research grants)",
                    "Rationale: Cached USASpending.gov eliminates API rate limits and $0 funding issues"
                ],
                "analysis_window": "12 months ahead"
            },
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"Error in comprehensive leaderboard: {e}")
        return {"error": f"Error generating leaderboard: {str(e)}"}

@app.get("/api/usaspending-stats")
async def get_usaspending_cache_stats():
    """Get statistics about the cached USASpending.gov data."""
    try:
        stats = get_usaspending_stats()
        if not stats:
            return {
                "error": "USASpending.gov cache not available",
                "note": "Run usaspending_cache_builder.py to build the cache"
            }
        
        return {
            "status": "success",
            "cache_info": stats,
            "message": "Comprehensive USASpending.gov funding data available"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting cache stats: {str(e)}")

@app.get("/api/layoff-leaderboard")
async def get_layoff_risk_leaderboard(cost_per_researcher: float = 200000, limit: int = 20):
    """Get institutions ranked by layoff risk using comprehensive multi-agency data."""
    try:
        result = await generate_comprehensive_leaderboard(cost_per_researcher, limit)
        
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
        
        # Count institution grants by agency
        institution_nih = len([g for g in institution_grants if g.get("funding_agency") == "NIH"])
        institution_nsf = len([g for g in institution_grants if g.get("funding_agency") == "NSF"])
        
        # Count funding grants by agency
        funding_agency_counts = {}
        for grant in funding_grants:
            agency = grant.get("funding_agency", "UNKNOWN")
            funding_agency_counts[agency] = funding_agency_counts.get(agency, 0) + 1
        
        # Get sample grants
        institution_samples = {}
        for agency in ["NIH", "NSF"]:
            agency_grants = [g for g in institution_grants if g.get("funding_agency") == agency]
            if agency_grants:
                sample = agency_grants[0]
                # Safely get organization name
                org_info = sample.get('organization', [])
                if isinstance(org_info, list) and len(org_info) > 0:
                    org_name = org_info[0].get('org_name', 'Unknown')
                elif isinstance(org_info, dict):
                    org_name = org_info.get('org_name', 'Unknown')
                else:
                    org_name = 'Unknown'
                
                title = sample.get('project_title', '') or ''
                institution_samples[agency] = {
                    "institution": org_name,
                    "amount": sample.get('award_amount', 0),
                    "title": title[:100] + "..." if len(title) > 100 else title,
                    "source": sample.get('source', 'Unknown')
                }
        
        funding_samples = {}
        for agency in list(funding_agency_counts.keys())[:3]:  # Top 3 agencies
            agency_grants = [g for g in funding_grants if g.get("funding_agency") == agency]
            if agency_grants:
                sample = agency_grants[0]
                # Safely get organization name
                org_info = sample.get('organization', [])
                if isinstance(org_info, list) and len(org_info) > 0:
                    org_name = org_info[0].get('org_name', 'Unknown')
                elif isinstance(org_info, dict):
                    org_name = org_info.get('org_name', 'Unknown')
                else:
                    org_name = 'Unknown'
                
                title = sample.get('project_title', '') or ''
                funding_samples[agency] = {
                    "institution": org_name,
                    "amount": sample.get('award_amount', 0),
                    "title": title[:100] + "..." if len(title) > 100 else title,
                    "source": sample.get('source', 'Unknown')
                }
        
        return {
            "status": "success",
            "message": "Enhanced funding data separation working",
            "institution_analysis": {
                "total_grants": len(institution_grants),
                "nih_grants": institution_nih,
                "nsf_grants": institution_nsf,
                "sample_grants": institution_samples,
                "data_source": "NIH Reporter API + NSF Awards API"
            },
            "total_funding": {
                "total_grants": len(funding_grants),
                "agency_breakdown": funding_agency_counts,
                "sample_grants": funding_samples,
                "data_source": "USASpending.gov API"
            },
            "architecture": "Separated data sources for optimal data quality"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error testing combined grants: {str(e)}")

@app.post("/api/refresh-cache")
async def refresh_grant_cache():
    """Force refresh all grant caches and fetch fresh data from all APIs."""
    try:
        # Clear all caches
        clear_cache()
        
        # Force fresh data fetch for total funding
        from layoff_estimator import fetch_total_funding_grants
        fresh_grants = await fetch_total_funding_grants(use_cache=False)
        
        # Count by agency
        agency_counts = {}
        for grant in fresh_grants:
            agency = grant.get("funding_agency", "UNKNOWN")
            agency_counts[agency] = agency_counts.get(agency, 0) + 1
        return {
            "status": "success",
            "message": "Grant cache refreshed successfully with funding data separation",
            "total_grants": len(fresh_grants),
            "agency_breakdown": agency_counts,
            "refreshed_at": datetime.now().isoformat(),
            "data_source": "USASpending.gov API (comprehensive funding data)"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error refreshing cache: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    print("Starting Enhanced NSF-Tracker API with multi-agency integration...")
    print("Features:")
    print("  ✅ Direct NIH Reporter API integration")
    print("  ✅ Direct NSF Awards API integration") 
    print("  ✅ USASpending.gov DoD/DoE integration")
    print("  ✅ Enhanced funding diversification tracking")
    print()
    uvicorn.run(app, host="localhost", port=8000)
