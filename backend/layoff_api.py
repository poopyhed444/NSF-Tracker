"""
Layoff Risk API Endpoints

This module contains FastAPI endpoints for layoff impact estimation and analysis.
Separated from main.py for better organization.
"""

from fastapi import APIRouter, HTTPException
from layoff_estimator import (
    estimate_institution_impact,
    analyze_pi_lab_impact,
    generate_layoff_risk_leaderboard
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
                "NIH RePORTER API for grant data",
                "Real-time funding status",
                "Historical termination patterns"
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
