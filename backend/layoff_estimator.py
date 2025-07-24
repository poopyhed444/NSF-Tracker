"""
Layoff Impact Estimation Module

This module provides functionality to estimate lab sizes and potential layoff impact
based on grant funding analysis, funding cliffs, and historical data.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any
import httpx
from collections import defaultdict
from department_costs import (
    get_department_cost_per_researcher, 
    get_department_risk_multiplier,
    calculate_department_adjusted_lab_size
)

# API endpoints
NIH_API_URL = "https://api.reporter.nih.gov/v2/projects/search"
NSF_API_URL = "https://www.research.gov/awardapi-service/v1/awards.json"

async def fetch_active_grants(organization: str = None, pi_name: str = None) -> List[Dict[str, Any]]:
    """Fetch currently active grants for analysis."""
    end_date = datetime.now() + timedelta(days=365)  # Look ahead 1 year
    start_date = datetime.now() - timedelta(days=30)   # Started recently or ongoing
    
    search_criteria = {
        "criteria": {
            "project_start_date": {
                "from_date": start_date.strftime("%Y-%m-%d"),
                "to_date": end_date.strftime("%Y-%m-%d")
            }
        },
        "include_fields": [
            "Organization",
            "ProjectTitle", 
            "ProjectEndDate",
            "ProjectStartDate",
            "AwardAmount",
            "FiscalYear",
            "ContactPiName"
        ],
        "offset": 0,
        "limit": 500
    }
    
    # Add filters if specified
    if organization:
        search_criteria["criteria"]["organization"] = organization
    if pi_name:
        search_criteria["criteria"]["pi_names"] = [pi_name]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(NIH_API_URL, json=search_criteria)
            response.raise_for_status()
            data = response.json()
            print(f"Fetched {len(data.get('results', []))} active grants from NIH API")
            return data.get("results", [])
        except Exception as e:
            print(f"Error fetching active grants: {e}")
            return []

async def fetch_nsf_grants(organization: str = None, pi_name: str = None, active_only: bool = True) -> List[Dict[str, Any]]:
    """
    Fetch NSF awards using the NSF Award Search API.
    Maps NSF data structure to align with NIH grant format for consistency.
    """
    # Build query parameters
    params = {
        "printFields": "id,title,startDate,expDate,fundsObligatedAmt,awardeeName,pdPIName,agency,fundProgramName",
        "offset": "1",
        "rpp": "500"  # Results per page
    }
    
    # Add filters
    if organization:
        params["awardeeState"] = organization  # NSF uses state-based org filtering
    if pi_name:
        params["pdPIName"] = pi_name
    
    # Filter for active grants if requested
    if active_only:
        current_year = datetime.now().year
        params["startDateStart"] = f"01/01/{current_year-2}"  # Last 2 years
        params["expDateStart"] = datetime.now().strftime("%m/%d/%Y")  # Not yet expired
    
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        try:
            response = await client.get(NSF_API_URL, params=params)
            response.raise_for_status()
            data = response.json()
            
            nsf_awards = data.get("response", {}).get("award", [])
            print(f"Fetched {len(nsf_awards)} NSF awards")
            
            # Map NSF data structure to NIH-compatible format
            mapped_grants = []
            for award in nsf_awards:
                mapped_grant = _map_nsf_to_nih_format(award)
                if mapped_grant:
                    mapped_grants.append(mapped_grant)
            
            return mapped_grants
            
        except Exception as e:
            print(f"Error fetching NSF grants: {e}")
            return []

def _map_nsf_to_nih_format(nsf_award: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map NSF award data to NIH grant format for consistency.
    
    NSF Fields -> NIH Fields:
    - fundsObligatedAmt -> award_amount
    - awardeeName -> organization.org_name
    - pdPIName -> contact_pi_name
    - title -> project_title
    - startDate -> project_start_date
    - expDate -> project_end_date
    """
    try:
        # Extract and format funding amount
        funding_str = nsf_award.get("fundsObligatedAmt", "0")
        if isinstance(funding_str, str):
            # Remove $ and commas, convert to float
            funding_amount = float(funding_str.replace("$", "").replace(",", ""))
        else:
            funding_amount = float(funding_str) if funding_str else 0
        
        # Extract PI name
        pi_name = nsf_award.get("pdPIName", "")
        if isinstance(pi_name, list):
            pi_name = pi_name[0] if pi_name else ""
        
        # Format dates
        start_date = _format_nsf_date(nsf_award.get("startDate", ""))
        end_date = _format_nsf_date(nsf_award.get("expDate", ""))
        
        # Map to NIH-compatible structure
        mapped_grant = {
            "award_amount": funding_amount,
            "contact_pi_name": pi_name,
            "project_title": nsf_award.get("title", ""),
            "project_start_date": start_date,
            "project_end_date": end_date,
            "organization": [{
                "org_name": nsf_award.get("awardeeName", "Unknown"),
                "org_dept": None  # NSF doesn't provide department info
            }],
            "fiscal_year": _extract_fiscal_year(start_date),
            "funding_agency": "NSF",  # Add source identifier
            "program": nsf_award.get("fundProgramName", ""),
            "award_id": nsf_award.get("id", "")
        }
        
        return mapped_grant
        
    except Exception as e:
        print(f"Error mapping NSF award: {e}")
        return None

def _format_nsf_date(date_str: str) -> str:
    """
    Format NSF date string to YYYY-MM-DD format.
    NSF typically uses MM/DD/YYYY format.
    """
    if not date_str:
        return ""
    
    try:
        # Handle MM/DD/YYYY format
        if "/" in date_str:
            month, day, year = date_str.split("/")
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        return date_str
    except Exception:
        return date_str

def _extract_fiscal_year(date_str: str) -> int:
    """Extract fiscal year from date string."""
    if not date_str:
        return datetime.now().year
    
    try:
        return int(date_str[:4])
    except (ValueError, IndexError):
        return datetime.now().year

async def fetch_combined_grants(organization: str = None, pi_name: str = None, active_only: bool = True) -> List[Dict[str, Any]]:
    """
    Fetch and combine grants from both NIH and NSF sources.
    Returns a unified list of grants in consistent format.
    """
    print("Fetching grants from NIH and NSF...")
    
    # Fetch from both sources concurrently
    if active_only:
        nih_grants = await fetch_active_grants(organization=organization, pi_name=pi_name)
    else:
        # For terminated grants, we'll need a different NIH function
        nih_grants = await fetch_active_grants(organization=organization, pi_name=pi_name)
    
    nsf_grants = await fetch_nsf_grants(organization=organization, pi_name=pi_name, active_only=active_only)
    
    # Combine and tag sources
    all_grants = []
    
    # Add NIH grants with source tag
    for grant in nih_grants:
        grant["funding_agency"] = "NIH"
        all_grants.append(grant)
    
    # Add NSF grants (already tagged in mapping function)
    all_grants.extend(nsf_grants)
    
    print(f"Combined total: {len(all_grants)} grants ({len(nih_grants)} NIH + {len(nsf_grants)} NSF)")
    
    return all_grants

def estimate_lab_size(total_annual_funding: float, cost_per_researcher: float = 200000, department: str = None) -> Dict[str, Any]:
    """
    Estimate lab size based on total funding and cost per researcher.
    If department is provided, uses department-specific cost models.
    Default: $200k/year per researcher (salary + benefits + overhead)
    """
    if department:
        # Use department-specific calculation
        return calculate_department_adjusted_lab_size(total_annual_funding, department)
    
    # Fallback to generic calculation
    if total_annual_funding <= 0:
        return {
            "estimated_researchers": 0,
            "funding_per_researcher": cost_per_researcher,
            "total_funding": total_annual_funding
        }
    
    estimated_count = total_annual_funding / cost_per_researcher
    
    return {
        "estimated_researchers": round(estimated_count, 1),
        "funding_per_researcher": cost_per_researcher,
        "total_funding": total_annual_funding,
        "confidence": "medium" if total_annual_funding > 500000 else "low"
    }

def estimate_lab_size_with_department(total_annual_funding: float, department: str) -> Dict[str, Any]:
    """
    Estimate lab size using department-specific cost models.
    This is a convenience wrapper around calculate_department_adjusted_lab_size.
    """
    return calculate_department_adjusted_lab_size(total_annual_funding, department)

def calculate_funding_cliff(grants: List[Dict[str, Any]], months_ahead: int = 12) -> Dict[str, Any]:
    """
    Calculate what percentage of funding is set to expire in the next N months.
    """
    cutoff_date = datetime.now() + timedelta(days=months_ahead * 30)
    
    total_funding = 0
    expiring_funding = 0
    expiring_grants = []
    
    for grant in grants:
        # Parse award amount
        award_amount = 0
        if grant.get("award_amount"):
            try:
                award_amount = float(grant["award_amount"])
            except (ValueError, TypeError):
                continue
        
        total_funding += award_amount
        
        # Check if grant expires soon
        end_date_str = grant.get("project_end_date")
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str[:10], "%Y-%m-%d")
                if end_date <= cutoff_date:
                    expiring_funding += award_amount
                    expiring_grants.append({
                        "title": grant.get("project_title", "Unknown"),
                        "pi": grant.get("contact_pi_name", "Unknown"),
                        "amount": award_amount,
                        "end_date": end_date_str
                    })
            except ValueError:
                continue
    
    cliff_percentage = (expiring_funding / total_funding * 100) if total_funding > 0 else 0
    
    return {
        "total_funding": total_funding,
        "expiring_funding": expiring_funding,
        "cliff_percentage": round(cliff_percentage, 1),
        "expiring_grants": expiring_grants,
        "months_ahead": months_ahead
    }

async def estimate_institution_impact(institution: str, cost_per_researcher: float = 200000) -> Dict[str, Any]:
    """
    Estimate lab sizes and potential layoff impact for an institution.
    Now includes both NIH and NSF funding data.
    """
    from main import fetch_terminated_grants  # Import to avoid circular imports
    
    # Fetch combined active grants from both NIH and NSF
    active_grants = await fetch_combined_grants(organization=institution, active_only=True)
    terminated_grants = await fetch_terminated_grants()  # NIH only for now
    
    if not active_grants and not terminated_grants:
        return {
            "error": "No grant data found for this institution",
            "institution": institution
        }
    
    # Calculate current lab size based on active funding
    total_active_funding = sum(
        float(grant.get("award_amount", 0)) 
        for grant in active_grants 
        if grant.get("award_amount")
    )
    
    # Separate funding by agency for detailed analysis
    nih_funding = sum(
        float(grant.get("award_amount", 0))
        for grant in active_grants
        if grant.get("funding_agency") == "NIH" and grant.get("award_amount")
    )
    
    nsf_funding = sum(
        float(grant.get("award_amount", 0))
        for grant in active_grants
        if grant.get("funding_agency") == "NSF" and grant.get("award_amount")
    )
    
    lab_size = estimate_lab_size(total_active_funding, cost_per_researcher)
    
    # Calculate funding cliff (grants expiring in next 12 months)
    cliff_analysis = calculate_funding_cliff(active_grants, months_ahead=12)
    
    # Calculate recent funding loss from terminated grants
    terminated_funding = sum(
        float(grant.get("award_amount", 0))
        for grant in terminated_grants
        if grant.get("award_amount") and grant.get("organization", [{}])[0].get("org_name") == institution
    )
    
    # Estimate at-risk positions
    at_risk_positions = cliff_analysis["expiring_funding"] / cost_per_researcher
    recent_lost_positions = terminated_funding / cost_per_researcher
    
    return {
        "institution": institution,
        "current_lab_size": lab_size,
        "funding_breakdown": {
            "total_active_funding": total_active_funding,
            "nih_funding": nih_funding,
            "nsf_funding": nsf_funding,
            "nih_percentage": round(nih_funding / total_active_funding * 100, 1) if total_active_funding > 0 else 0,
            "nsf_percentage": round(nsf_funding / total_active_funding * 100, 1) if total_active_funding > 0 else 0,
            "grant_count": len(active_grants),
            "nih_grant_count": len([g for g in active_grants if g.get("funding_agency") == "NIH"]),
            "nsf_grant_count": len([g for g in active_grants if g.get("funding_agency") == "NSF"])
        },
        "funding_cliff": cliff_analysis,
        "layoff_risk": {
            "at_risk_positions": round(at_risk_positions, 1),
            "recently_lost_positions": round(recent_lost_positions, 1),
            "risk_level": "HIGH" if cliff_analysis["cliff_percentage"] > 50 else "MEDIUM" if cliff_analysis["cliff_percentage"] > 25 else "LOW",
            "diversification_score": "HIGH" if nsf_funding > 0 and nih_funding > 0 else "MEDIUM" if total_active_funding > 1000000 else "LOW"
        },
        "methodology": {
            "cost_per_researcher": cost_per_researcher,
            "analysis_window": "12 months ahead",
            "confidence": lab_size.get("confidence", "medium"),
            "data_sources": ["NIH RePORTER", "NSF Award Search API"]
        },
        "last_updated": datetime.now().isoformat()
    }

async def analyze_pi_lab_impact(pi_name: str, institution: str, cost_per_researcher: float = 200000) -> Dict[str, Any]:
    """
    Analyze a specific PI's lab for funding and layoff risk.
    Now includes both NIH and NSF grants.
    """
    from pi_department_lookup import get_pi_department  # Import to avoid circular imports
    
    # Fetch combined grants for this specific PI from both NIH and NSF
    active_grants = await fetch_combined_grants(pi_name=pi_name, active_only=True)
    
    # Filter by institution if needed
    if institution:
        active_grants = [
            grant for grant in active_grants
            if any(institution.lower() in org.get("org_name", "").lower() 
                  for org in (grant.get("organization", []) if isinstance(grant.get("organization"), list) 
                            else [grant.get("organization", {})]))
        ]
    
    if not active_grants:
        return {
            "error": f"No active grants found for {pi_name} at {institution}",
            "pi_name": pi_name,
            "institution": institution
        }
    
    # Calculate PI's lab funding and size
    total_funding = sum(
        float(grant.get("award_amount", 0))
        for grant in active_grants
        if grant.get("award_amount")
    )
    
    # Separate funding by agency
    nih_grants = [g for g in active_grants if g.get("funding_agency") == "NIH"]
    nsf_grants = [g for g in active_grants if g.get("funding_agency") == "NSF"]
    
    nih_funding = sum(float(g.get("award_amount", 0)) for g in nih_grants if g.get("award_amount"))
    nsf_funding = sum(float(g.get("award_amount", 0)) for g in nsf_grants if g.get("award_amount"))
    
    lab_size = estimate_lab_size(total_funding, cost_per_researcher)
    cliff_analysis = calculate_funding_cliff(active_grants, months_ahead=12)
    
    # Get department classification
    dept_result = await get_pi_department(pi_name, institution)
    
    # Calculate funding diversification including agency diversity
    agency_diversity = "HIGH" if len(nih_grants) > 0 and len(nsf_grants) > 0 else "MEDIUM"
    grant_diversity = "HIGH" if len(active_grants) >= 3 else "MEDIUM" if len(active_grants) == 2 else "LOW"
    
    return {
        "pi_name": pi_name,
        "institution": institution,
        "department": dept_result.get("department", "Unknown"),
        "lab_analysis": {
            "estimated_lab_size": lab_size,
            "funding_cliff": cliff_analysis,
            "grant_count": len(active_grants),
            "funding_diversification": grant_diversity,
            "agency_diversification": agency_diversity
        },
        "funding_breakdown": {
            "total_funding": total_funding,
            "nih_funding": nih_funding,
            "nsf_funding": nsf_funding,
            "nih_percentage": round(nih_funding / total_funding * 100, 1) if total_funding > 0 else 0,
            "nsf_percentage": round(nsf_funding / total_funding * 100, 1) if total_funding > 0 else 0,
            "nih_grant_count": len(nih_grants),
            "nsf_grant_count": len(nsf_grants)
        },
        "layoff_risk": {
            "at_risk_positions": round(cliff_analysis["expiring_funding"] / cost_per_researcher, 1),
            "risk_level": "HIGH" if cliff_analysis["cliff_percentage"] > 60 else "MEDIUM" if cliff_analysis["cliff_percentage"] > 30 else "LOW",
            "primary_risk_factor": _assess_primary_risk_factor(active_grants, cliff_analysis, nih_grants, nsf_grants)
        },
        "grants": [
            {
                "title": grant.get("project_title", "Unknown")[:100] + "...",
                "amount": grant.get("award_amount"),
                "end_date": grant.get("project_end_date"),
                "fiscal_year": grant.get("fiscal_year"),
                "agency": grant.get("funding_agency", "Unknown"),
                "program": grant.get("program", "")
            }
            for grant in active_grants[:5]  # Show top 5 grants
        ],
        "last_updated": datetime.now().isoformat()
    }

def _assess_primary_risk_factor(active_grants: List[Dict], cliff_analysis: Dict, nih_grants: List[Dict], nsf_grants: List[Dict]) -> str:
    """Assess the primary risk factor for a PI's lab."""
    total_grants = len(active_grants)
    cliff_percentage = cliff_analysis.get("cliff_percentage", 0)
    
    # Check for single agency dependency
    if len(nih_grants) == 0 or len(nsf_grants) == 0:
        if total_grants <= 2:
            return "Single agency + funding concentration"
        else:
            return "Single agency dependency"
    
    # Check for funding concentration
    if total_grants <= 2:
        return "Funding concentration"
    
    # Check for funding cliff
    if cliff_percentage > 40:
        return "Funding cliff"
    
    return "Normal"

async def generate_layoff_risk_leaderboard(cost_per_researcher: float = 200000, limit: int = 20) -> Dict[str, Any]:
    """
    Get institutions ranked by layoff risk based on funding cliffs and lab sizes.
    Now includes both NIH and NSF funding data.
    """
    from main import fetch_terminated_grants  # Import to avoid circular imports
    
    # Fetch both active and terminated grants (NIH + NSF for active, NIH only for terminated)
    active_grants = await fetch_combined_grants(active_only=True)
    terminated_grants = await fetch_terminated_grants()
    
    if not active_grants:
        return {
            "error": "No active grant data available",
            "note": "Cannot calculate layoff risk without current funding data"
        }
    
    # Group by institution
    institution_data = defaultdict(lambda: {
        "active_grants": [],
        "terminated_grants": [],
        "total_active_funding": 0,
        "total_terminated_funding": 0,
        "nih_funding": 0,
        "nsf_funding": 0
    })
    
    # Process active grants (NIH + NSF)
    for grant in active_grants:
        org_info = grant.get("organization", {})
        if isinstance(org_info, list) and len(org_info) > 0:
            org_name = org_info[0].get("org_name", "Unknown")
        elif isinstance(org_info, dict):
            org_name = org_info.get("org_name", "Unknown")
        else:
            continue
            
        if org_name != "Unknown":
            institution_data[org_name]["active_grants"].append(grant)
            try:
                amount = float(grant.get("award_amount", 0))
                institution_data[org_name]["total_active_funding"] += amount
                
                # Track funding by agency
                if grant.get("funding_agency") == "NIH":
                    institution_data[org_name]["nih_funding"] += amount
                elif grant.get("funding_agency") == "NSF":
                    institution_data[org_name]["nsf_funding"] += amount
                    
            except (ValueError, TypeError):
                pass
    
    # Process terminated grants (NIH only for now)
    for grant in terminated_grants:
        org_info = grant.get("organization", {})
        if isinstance(org_info, list) and len(org_info) > 0:
            org_name = org_info[0].get("org_name", "Unknown")
        elif isinstance(org_info, dict):
            org_name = org_info.get("org_name", "Unknown")
        else:
            continue
            
        if org_name in institution_data:
            institution_data[org_name]["terminated_grants"].append(grant)
            try:
                amount = float(grant.get("award_amount", 0))
                institution_data[org_name]["total_terminated_funding"] += amount
            except (ValueError, TypeError):
                pass
    
    # Calculate risk scores for each institution
    risk_rankings = []
    
    for institution, data in institution_data.items():
        if data["total_active_funding"] < 100000:  # Skip institutions with minimal funding
            continue
            
        # Determine department composition for this institution
        department_breakdown = defaultdict(lambda: {"grants": 0, "funding": 0})
        
        # Analyze grants by department
        for grant in data["active_grants"]:
            dept = _estimate_grant_department(grant)
            department_breakdown[dept]["grants"] += 1
            try:
                amount = float(grant.get("award_amount", 0))
                department_breakdown[dept]["funding"] += amount
            except (ValueError, TypeError):
                pass
        
        # Calculate weighted average cost per researcher based on department mix
        total_funding = data["total_active_funding"]
        weighted_cost = 0
        weighted_risk_multiplier = 0
        
        for dept, info in department_breakdown.items():
            if info["funding"] > 0:
                dept_weight = info["funding"] / total_funding
                dept_cost = get_department_cost_per_researcher(dept)
                dept_risk = get_department_risk_multiplier(dept)
                
                weighted_cost += dept_cost * dept_weight
                weighted_risk_multiplier += dept_risk * dept_weight
        
        # Fallback to default if no department data
        if weighted_cost == 0:
            weighted_cost = cost_per_researcher
            weighted_risk_multiplier = 1.0
        
        # Calculate lab size using weighted department costs
        lab_size = estimate_lab_size(total_funding, weighted_cost)
        cliff_analysis = calculate_funding_cliff(data["active_grants"], months_ahead=12)
        
        # Calculate funding diversification bonus (NIH + NSF is lower risk)
        has_both_agencies = data["nih_funding"] > 0 and data["nsf_funding"] > 0
        diversification_bonus = 0.9 if has_both_agencies else 1.0  # 10% risk reduction for dual agency funding
        
        # Calculate risk score (weighted combination of factors)
        cliff_weight = cliff_analysis["cliff_percentage"] * 0.4  # 40% weight
        terminated_weight = (data["total_terminated_funding"] / data["total_active_funding"] * 100) * 0.3 if data["total_active_funding"] > 0 else 0  # 30% weight
        size_weight = min(lab_size["estimated_researchers"] * 2, 20)  # 20% weight, capped at 20
        concentration_penalty = max(0, (3 - len(data["active_grants"])) * 5)  # 10% weight - penalty for few grants
        
        # Apply department risk multiplier and diversification bonus
        base_risk_score = cliff_weight + terminated_weight + size_weight + concentration_penalty
        risk_score = base_risk_score * weighted_risk_multiplier * diversification_bonus
        
        at_risk_positions = cliff_analysis["expiring_funding"] / weighted_cost
        recent_lost_positions = data["total_terminated_funding"] / weighted_cost
        
        # Get top departments for this institution
        top_departments = sorted(
            [(dept, info) for dept, info in department_breakdown.items()],
            key=lambda x: x[1]["funding"],
            reverse=True
        )[:3]
        
        risk_rankings.append({
            "institution": institution,
            "risk_score": round(risk_score, 1),
            "estimated_lab_size": lab_size["estimated_researchers"],
            "at_risk_positions": round(at_risk_positions, 1),
            "recently_lost_positions": round(recent_lost_positions, 1),
            "funding_cliff_percentage": cliff_analysis["cliff_percentage"],
            "total_active_funding": data["total_active_funding"],
            "active_grants_count": len(data["active_grants"]),
            "terminated_grants_count": len(data["terminated_grants"]),
            "weighted_cost_per_researcher": round(weighted_cost, 0),
            "department_risk_multiplier": round(weighted_risk_multiplier, 2),
            "funding_diversification": {
                "nih_funding": data["nih_funding"],
                "nsf_funding": data["nsf_funding"],
                "nih_percentage": round(data["nih_funding"] / total_funding * 100, 1) if total_funding > 0 else 0,
                "nsf_percentage": round(data["nsf_funding"] / total_funding * 100, 1) if total_funding > 0 else 0,
                "has_both_agencies": has_both_agencies,
                "diversification_bonus": round((1 - diversification_bonus) * 100, 1)  # Show as percentage reduction
            },
            "top_departments": [
                {
                    "department": dept,
                    "grants": info["grants"],
                    "funding": info["funding"],
                    "percentage": round(info["funding"] / total_funding * 100, 1)
                }
                for dept, info in top_departments
            ],
            "risk_level": "CRITICAL" if risk_score > 70 else "HIGH" if risk_score > 50 else "MEDIUM" if risk_score > 30 else "LOW"
        })
    
    # Sort by risk score (highest first)
    risk_rankings.sort(key=lambda x: x["risk_score"], reverse=True)
    
    return {
        "data": risk_rankings[:limit],
        "total_institutions": len(risk_rankings),
        "methodology": {
            "risk_factors": [
                "Funding cliff percentage (40% weight)",
                "Recent funding loss ratio (30% weight)", 
                "Lab size impact (20% weight)",
                "Grant concentration penalty (10% weight)",
                "Department-specific risk multipliers",
                "Agency diversification bonus (10% risk reduction for NIH+NSF)"
            ],
            "cost_calculation": "Weighted average based on department composition",
            "department_costs": "Department-specific cost per researcher models",
            "data_sources": ["NIH RePORTER", "NSF Award Search API"],
            "analysis_window": "12 months ahead"
        },
        "last_updated": datetime.now().isoformat()
    }

def _estimate_grant_department(grant: Dict[str, Any]) -> str:
    """
    Estimate department for a grant based on title keywords.
    This is a simplified approach - could be enhanced with actual PI lookup.
    """
    title = grant.get("project_title", "").lower()
    
    # Medical/Clinical keywords
    if any(word in title for word in ["cancer", "tumor", "oncology", "chemotherapy"]):
        return "Oncology"
    elif any(word in title for word in ["heart", "cardiac", "cardiovascular", "cardiology"]):
        return "Cardiology"
    elif any(word in title for word in ["brain", "neural", "neuron", "neuro", "cognitive"]):
        return "Neuroscience"
    elif any(word in title for word in ["immune", "immunology", "antibody", "vaccine"]):
        return "Immunology"
    elif any(word in title for word in ["pediatric", "children", "infant", "neonatal"]):
        return "Pediatrics"
    elif any(word in title for word in ["surgery", "surgical", "transplant"]):
        return "Surgery"
    elif any(word in title for word in ["psychiatry", "psychiatric", "mental health", "depression"]):
        return "Psychiatry"
    elif any(word in title for word in ["drug", "pharmaceutical", "pharmacology", "medicine"]):
        return "Medicine"
    
    # Basic sciences
    elif any(word in title for word in ["gene", "genetic", "dna", "genome", "genomic"]):
        return "Genetics"
    elif any(word in title for word in ["cell", "cellular", "molecular", "protein", "enzyme"]):
        return "Molecular Biology"
    elif any(word in title for word in ["microbial", "bacteria", "virus", "pathogen", "infection"]):
        return "Microbiology"
    elif any(word in title for word in ["chemical", "chemistry", "compound", "synthesis"]):
        return "Chemistry"
    elif any(word in title for word in ["physics", "quantum", "particle", "electromagnetic"]):
        return "Physics"
    elif any(word in title for word in ["engineering", "device", "system", "technology"]):
        return "Engineering"
    elif any(word in title for word in ["computer", "computational", "algorithm", "software"]):
        return "Computer Science"
    elif any(word in title for word in ["data", "statistical", "analytics", "machine learning"]):
        return "Data Science"
    elif any(word in title for word in ["mathematical", "mathematics", "model", "modeling"]):
        return "Mathematics"
    elif any(word in title for word in ["environmental", "ecology", "ecosystem", "climate"]):
        return "Environmental Science"
    elif any(word in title for word in ["psychology", "psychological", "behavior", "cognitive"]):
        return "Psychology"
    elif any(word in title for word in ["material", "materials", "nanoscale", "nanoparticle"]):
        return "Materials Science"
    elif any(word in title for word in ["bioengineering", "biomedical engineering", "tissue engineering"]):
        return "Biomedical Engineering"
    elif any(word in title for word in ["biology", "biological", "organism", "species"]):
        return "Biology"
    
    # Default fallback
    return "Unknown"
