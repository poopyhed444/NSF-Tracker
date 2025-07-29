"""
Layoff Risk API Endpoints

This module contains FastAPI endpoints for layoff impact estimation and analysis.
Separated from main.py for better organization.
"""

from fastapi import APIRouter, HTTPException
from layoff_estimator import (
    estimate_institution_impact,
    analyze_pi_lab_impact,
    generate_layoff_risk_leaderboard,
    fetch_nsf_grants,
    fetch_combined_grants
)
from department_costs import get_department_cost_summary

# Create router for layoff-related endpoints
layoff_router = APIRouter(prefix="/api", tags=["layoff-analysis"])

@layoff_router.get("/lab-size-estimator")
async def estimate_lab_impact(institution: str, cost_per_researcher: float = 200000):
    """
    Estimate lab sizes and potential layoff impact for an institution.
    Usage: /api/lab-size-estimator?institution=Harvard University&cost_per_researcher=200000
    """
    try:
        result = await estimate_institution_impact(institution, cost_per_researcher)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error estimating lab impact: {str(e)}")

@layoff_router.get("/pi-lab-analysis") 
async def analyze_pi_lab(pi_name: str, institution: str, cost_per_researcher: float = 200000):
    """
    Analyze a specific PI's lab for funding and layoff risk.
    Usage: /api/pi-lab-analysis?pi_name=Jennifer Doudna&institution=University of California, Berkeley
    """
    try:
        result = await analyze_pi_lab_impact(pi_name, institution, cost_per_researcher)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing PI lab: {str(e)}")

@layoff_router.get("/layoff-leaderboard")
async def get_layoff_risk_leaderboard(cost_per_researcher: float = 200000, limit: int = 20):
    """
    Get institutions ranked by layoff risk based on funding cliffs and lab sizes.
    Usage: /api/layoff-leaderboard?cost_per_researcher=200000&limit=20
    """
    try:
        result = await generate_layoff_risk_leaderboard(cost_per_researcher, limit)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating layoff risk leaderboard: {str(e)}")

@layoff_router.get("/layoff-methodology")
async def get_layoff_methodology():
    """
    Get detailed information about the layoff risk calculation methodology.
    """
    return {
        "methodology": {
            "overview": "Layoff risk is calculated using a weighted combination of funding and structural factors",
            "risk_factors": [
                {
                    "factor": "Funding Cliff Percentage",
                    "weight": "40%",
                    "description": "Percentage of total funding that expires within 12 months",
                    "interpretation": ">50% = HIGH risk, 25-50% = MEDIUM risk, <25% = LOW risk"
                },
                {
                    "factor": "Recent Funding Loss Ratio", 
                    "weight": "30%",
                    "description": "Ratio of recently terminated funding to current active funding",
                    "interpretation": "Higher ratios indicate recent instability"
                },
                {
                    "factor": "Lab Size Impact",
                    "weight": "20%", 
                    "description": "Number of estimated researchers affected (capped at 20 points)",
                    "interpretation": "Larger labs have higher absolute impact"
                },
                {
                    "factor": "Grant Concentration Penalty",
                    "weight": "10%",
                    "description": "Penalty for labs with few grants (higher concentration risk)",
                    "interpretation": "1-2 grants = higher risk, 3+ grants = lower risk"
                }
            ],
            "lab_size_estimation": {
                "default_cost_per_researcher": 200000,
                "description": "Annual cost including salary, benefits, and overhead",
                "adjustable": "Can be customized per institution or analysis"
            },
            "data_sources": [
                "NIH RePORTER API for active and terminated grants",
                "NSF Award Search API for research grants",
                "DoD Contract Data from defense.gov announcements", 
                "DoE Research Programs (Solar, Fusion, Battery, Grid, etc.)",
                "Real-time funding status and expiration tracking"
            ],
            "confidence_levels": {
                "HIGH": "Based on substantial funding data (>$500k)",
                "MEDIUM": "Based on moderate funding data ($100k-$500k)", 
                "LOW": "Based on limited funding data (<$100k)"
            }
        },
        "risk_level_definitions": {
            "CRITICAL": "Risk score > 70 - Immediate layoff risk likely",
            "HIGH": "Risk score 50-70 - Significant layoff risk within 6-12 months",
            "MEDIUM": "Risk score 30-50 - Moderate risk, monitoring recommended",
            "LOW": "Risk score < 30 - Minimal immediate risk"
        },
        "limitations": [
            "Based on publicly available grant data only",
            "Does not account for private funding or endowments",
            "Uses department-specific cost models and risk factors",
            "Cannot predict external economic factors or policy changes"
        ]
    }

@layoff_router.get("/department-cost-models")
async def get_department_cost_models():
    """
    Get information about department-specific cost models and risk factors.
    Usage: /api/department-cost-models
    """
    try:
        return get_department_cost_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving department cost models: {str(e)}")

@layoff_router.get("/department-analysis/{institution}")
async def get_institution_department_breakdown(institution: str):
    """
    Get department-specific analysis for an institution showing cost breakdowns and risk factors.
    Usage: /api/department-analysis/Harvard University
    """
    try:
        from layoff_estimator import fetch_active_grants
        from collections import defaultdict
        from department_costs import get_department_cost_per_researcher, get_department_risk_multiplier
        
        # Fetch active grants for the institution
        active_grants = await fetch_active_grants(organization=institution)
        
        if not active_grants:
            return {
                "error": f"No active grants found for {institution}",
                "institution": institution
            }
        
        # Analyze by department
        department_data = defaultdict(lambda: {
            "grants": [],
            "total_funding": 0,
            "grant_count": 0
        })
        
        from layoff_estimator import _estimate_grant_department
        
        for grant in active_grants:
            dept = _estimate_grant_department(grant)
            department_data[dept]["grants"].append(grant)
            department_data[dept]["grant_count"] += 1
            
            try:
                amount = float(grant.get("award_amount", 0))
                department_data[dept]["total_funding"] += amount
            except (ValueError, TypeError):
                pass
        
        # Calculate department-specific metrics
        department_analysis = []
        total_institutional_funding = sum(data["total_funding"] for data in department_data.values())
        
        for dept, data in department_data.items():
            if data["total_funding"] > 0:
                dept_cost = get_department_cost_per_researcher(dept)
                dept_risk = get_department_risk_multiplier(dept)
                estimated_researchers = data["total_funding"] / dept_cost
                
                department_analysis.append({
                    "department": dept,
                    "total_funding": data["total_funding"],
                    "grant_count": data["grant_count"],
                    "percentage_of_institution": round(data["total_funding"] / total_institutional_funding * 100, 1),
                    "cost_per_researcher": dept_cost,
                    "risk_multiplier": dept_risk,
                    "estimated_researchers": round(estimated_researchers, 1),
                    "adjusted_risk_score": round(estimated_researchers * dept_risk, 1)
                })
        
        # Sort by funding amount
        department_analysis.sort(key=lambda x: x["total_funding"], reverse=True)
        
        return {
            "institution": institution,
            "total_funding": total_institutional_funding,
            "total_grants": sum(data["grant_count"] for data in department_data.values()),
            "department_breakdown": department_analysis,
            "risk_summary": {
                "highest_risk_department": max(department_analysis, key=lambda x: x["adjusted_risk_score"])["department"] if department_analysis else "Unknown",
                "most_funded_department": department_analysis[0]["department"] if department_analysis else "Unknown",
                "department_count": len(department_analysis)
            },
            "last_updated": "2025-07-22T00:00:00"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing institution departments: {str(e)}")

@layoff_router.get("/test-nsf-grants")
async def test_nsf_integration(organization: str = None, pi_name: str = None, limit: int = 10):
    """
    Test endpoint for NSF grant integration.
    Usage: /api/test-nsf-grants?organization=MIT&limit=5
    """
    try:
        nsf_grants = await fetch_nsf_grants(organization=organization, pi_name=pi_name, active_only=True)
        
        return {
            "nsf_grants_found": len(nsf_grants),
            "organization_filter": organization,
            "pi_name_filter": pi_name,
            "sample_grants": nsf_grants[:limit],
            "data_sources": ["NSF Award Search API"],
            "note": "This shows NSF grants in NIH-compatible format"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error testing NSF integration: {str(e)}")

@layoff_router.get("/combined-funding-analysis/{institution}")
async def get_combined_funding_analysis(institution: str):
    """
    Get comprehensive funding analysis combining NIH and NSF data.
    Usage: /api/combined-funding-analysis/Harvard University
    """
    try:
        # Get combined grants
        combined_grants = await fetch_combined_grants(organization=institution, active_only=True)
        
        if not combined_grants:
            return {
                "error": f"No grants found for {institution}",
                "institution": institution
            }
        
        # Separate by agency
        nih_grants = [g for g in combined_grants if g.get("funding_agency") == "NIH"]
        nsf_grants = [g for g in combined_grants if g.get("funding_agency") == "NSF"]
        
        # Calculate funding totals
        total_funding = 0
        nih_funding = 0
        nsf_funding = 0
        
        for grant in combined_grants:
            try:
                amount = float(grant.get("award_amount", 0)) if grant.get("award_amount") else 0
                total_funding += amount
            except (ValueError, TypeError):
                pass
        
        for grant in nih_grants:
            try:
                amount = float(grant.get("award_amount", 0)) if grant.get("award_amount") else 0
                nih_funding += amount
            except (ValueError, TypeError):
                pass
        
        for grant in nsf_grants:
            try:
                amount = float(grant.get("award_amount", 0)) if grant.get("award_amount") else 0
                nsf_funding += amount
            except (ValueError, TypeError):
                pass
        
        # Analyze by department for each agency
        from collections import defaultdict
        from layoff_estimator import _estimate_grant_department
        
        nih_dept_breakdown = defaultdict(lambda: {"grants": 0, "funding": 0})
        nsf_dept_breakdown = defaultdict(lambda: {"grants": 0, "funding": 0})
        
        for grant in nih_grants:
            dept = _estimate_grant_department(grant)
            nih_dept_breakdown[dept]["grants"] += 1
            try:
                amount = float(grant.get("award_amount", 0)) if grant.get("award_amount") else 0
                nih_dept_breakdown[dept]["funding"] += amount
            except (ValueError, TypeError):
                pass
        
        for grant in nsf_grants:
            dept = _estimate_grant_department(grant)
            nsf_dept_breakdown[dept]["grants"] += 1
            try:
                amount = float(grant.get("award_amount", 0)) if grant.get("award_amount") else 0
                nsf_dept_breakdown[dept]["funding"] += amount
            except (ValueError, TypeError):
                pass
        
        return {
            "institution": institution,
            "total_funding": total_funding,
            "funding_breakdown": {
                "nih_funding": nih_funding,
                "nsf_funding": nsf_funding,
                "nih_percentage": round(nih_funding / total_funding * 100, 1) if total_funding > 0 else 0,
                "nsf_percentage": round(nsf_funding / total_funding * 100, 1) if total_funding > 0 else 0
            },
            "grant_counts": {
                "total_grants": len(combined_grants),
                "nih_grants": len(nih_grants),
                "nsf_grants": len(nsf_grants)
            },
            "nih_department_breakdown": [
                {
                    "department": dept,
                    "grants": info["grants"],
                    "funding": info["funding"],
                    "percentage": round(info["funding"] / nih_funding * 100, 1) if nih_funding > 0 else 0
                }
                for dept, info in sorted(nih_dept_breakdown.items(), key=lambda x: x[1]["funding"], reverse=True)
            ][:10],
            "nsf_department_breakdown": [
                {
                    "department": dept,
                    "grants": info["grants"],
                    "funding": info["funding"],
                    "percentage": round(info["funding"] / nsf_funding * 100, 1) if nsf_funding > 0 else 0
                }
                for dept, info in sorted(nsf_dept_breakdown.items(), key=lambda x: x[1]["funding"], reverse=True)
            ][:10],
            "diversification_analysis": {
                "has_both_agencies": len(nih_grants) > 0 and len(nsf_grants) > 0,
                "funding_concentration": "HIGH" if len(combined_grants) <= 3 else "MEDIUM" if len(combined_grants) <= 6 else "LOW",
                "agency_balance": "BALANCED" if abs(nih_funding - nsf_funding) / total_funding < 0.3 else "NIH_HEAVY" if nih_funding > nsf_funding else "NSF_HEAVY"
            },
            "last_updated": "2025-07-23T00:00:00"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing combined funding: {str(e)}")

@layoff_router.get("/funding-agency-comparison")
async def get_funding_agency_comparison(limit: int = 20):
    """
    Compare institutions by their NIH vs NSF funding profiles.
    Usage: /api/funding-agency-comparison?limit=20
    """
    try:
        # Get combined grants for all institutions
        combined_grants = await fetch_combined_grants(active_only=True)
        
        if not combined_grants:
            return {"error": "No grant data available"}
        
        # Group by institution and agency
        from collections import defaultdict
        institution_data = defaultdict(lambda: {"nih": 0, "nsf": 0, "total": 0})
        
        for grant in combined_grants:
            org_info = grant.get("organization", {})
            if isinstance(org_info, list) and len(org_info) > 0:
                org_name = org_info[0].get("org_name", "Unknown")
            elif isinstance(org_info, dict):
                org_name = org_info.get("org_name", "Unknown")
            else:
                continue
                
            if org_name != "Unknown":
                try:
                    amount = float(grant.get("award_amount", 0))
                    institution_data[org_name]["total"] += amount
                    
                    if grant.get("funding_agency") == "NIH":
                        institution_data[org_name]["nih"] += amount
                    elif grant.get("funding_agency") == "NSF":
                        institution_data[org_name]["nsf"] += amount
                except (ValueError, TypeError):
                    pass
        
        # Calculate metrics for each institution
        comparison_data = []
        for institution, funding in institution_data.items():
            if funding["total"] > 100000:  # Only include substantial funding
                nih_pct = (funding["nih"] / funding["total"] * 100) if funding["total"] > 0 else 0
                nsf_pct = (funding["nsf"] / funding["total"] * 100) if funding["total"] > 0 else 0
                
                # Categorize funding profile
                if nih_pct > 80:
                    profile = "NIH-Dominant"
                elif nsf_pct > 80:
                    profile = "NSF-Dominant"
                elif abs(nih_pct - nsf_pct) < 20:
                    profile = "Balanced"
                elif nih_pct > nsf_pct:
                    profile = "NIH-Heavy"
                else:
                    profile = "NSF-Heavy"
                
                comparison_data.append({
                    "institution": institution,
                    "total_funding": funding["total"],
                    "nih_funding": funding["nih"],
                    "nsf_funding": funding["nsf"],
                    "nih_percentage": round(nih_pct, 1),
                    "nsf_percentage": round(nsf_pct, 1),
                    "funding_profile": profile,
                    "diversification_score": min(nih_pct, nsf_pct)  # Lower of the two percentages
                })
        
        # Sort by total funding
        comparison_data.sort(key=lambda x: x["total_funding"], reverse=True)
        
        return {
            "data": comparison_data[:limit],
            "total_institutions": len(comparison_data),
            "summary": {
                "nih_dominant": len([x for x in comparison_data if x["funding_profile"] == "NIH-Dominant"]),
                "nsf_dominant": len([x for x in comparison_data if x["funding_profile"] == "NSF-Dominant"]),
                "balanced": len([x for x in comparison_data if x["funding_profile"] == "Balanced"]),
                "total_funding_analyzed": sum(x["total_funding"] for x in comparison_data)
            },
            "last_updated": "2025-07-23T00:00:00"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating agency comparison: {str(e)}")
