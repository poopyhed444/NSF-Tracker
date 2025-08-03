#!/usr/bin/env python3
"""
Clean FastAPI server for NSF-Tracker with enhanced multi-agency integration.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import asyncio
from layoff_estimator import fetch_institution_grants, fetch_total_funding_grants, normalize_institution_name, fetch_terminated_grants
from grant_cache import clear_cache
from collections import defaultdict
from department_costs import get_department_cost_per_researcher, get_department_risk_multiplier
from usaspending_cache_loader import get_usaspending_funding, get_usaspending_stats
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
        cache_stats = get_usaspending_stats()
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
