from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import httpx
import asyncio
import os
from typing import List, Dict, Any
import json
from collections import defaultdict
from pi_department_lookup import get_pi_department
from scibert_classifier import predict_department_scibert, train_classifier
from layoff_api import layoff_router
from grant_cache import get_cache_status, clear_cache

app = FastAPI(title="NIH/NSF At-Risk Labs Tracker", version="1.0.0")

# Include the layoff analysis router
app.include_router(layoff_router)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# NIH RePORTER API endpoint
NIH_API_URL = "https://api.reporter.nih.gov/v2/projects/search"

async def fetch_terminated_grants() -> List[Dict[str, Any]]:
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    search_criteria = {
        "criteria": {
            "project_end_date": {
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
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(NIH_API_URL, json=search_criteria)
            response.raise_for_status()
            data = response.json()
            print(f"Fetched {len(data.get('results', []))} terminated grants from NIH API")
            return data.get("results", [])
        except httpx.RequestError as e:
            print(f"Error fetching data from NIH API: {e}")
            return []
        except httpx.HTTPStatusError as e:
            print(f"HTTP error from NIH API: {e}")
            return []

async def guess_department(grant: Dict[str, Any]) -> Dict[str, str]:
    """
    Guess the department for a grant using PI lookup and fallback methods.
    Returns dict with department, source, and confidence.
    """
    # Try PI-based lookup first
    pi_name = grant.get("contact_pi_name") or grant.get("pi_name")
    org_info = grant.get("organization", {})
    
    # Get institution name
    institution_name = "Unknown"
    if isinstance(org_info, list) and len(org_info) > 0:
        institution_name = org_info[0].get("org_name", "Unknown")
    elif isinstance(org_info, dict):
        institution_name = org_info.get("org_name", "Unknown")
    
    if pi_name and isinstance(pi_name, str) and institution_name != "Unknown":
        try:
            # Use the PI lookup module with force_refresh to ensure we get the latest enhanced results
            result = await get_pi_department(pi_name.strip(), institution_name, force_refresh=True)
            if result['department'] != "Unknown":
                return result
        except Exception as e:
            print(f"Error in PI lookup for {pi_name}: {e}")
    
    # Fallback to organization-based guessing
    if isinstance(org_info, list) and len(org_info) > 0:
        org_info = org_info[0]
    if isinstance(org_info, dict):
        dept = org_info.get("org_dept") or org_info.get("division")
        if dept and isinstance(dept, str) and dept.strip():
            return {
                'department': dept.strip(),
                'source': 'organization',
                'confidence': 'medium'
            }
    
    # Fallback to title-based guessing
    title = grant.get("project_title", "")
    if isinstance(title, str):
        title_lower = title.lower()
        keywords = {
            "neuro": "Neuroscience",
            "chem": "Chemistry", 
            "bio": "Biology",
            "physic": "Physics",
            "engineer": "Engineering",
            "math": "Mathematics",
            "computer": "Computer Science",
            "psych": "Psychology",
            "medic": "Medicine",
            "pharma": "Pharmacy",
            "cancer": "Oncology",
            "cardio": "Cardiology",
            "immun": "Immunology"
        }
        for k, v in keywords.items():
            if k in title_lower:
                return {
                    'department': v,
                    'source': 'title_keywords',
                    'confidence': 'low'
                }
    
    return {
        'department': 'Unknown',
        'source': 'none',
        'confidence': 'none'
    }
    """
    Calculate risk scores for institutions based on terminated grants.
    Risk score = (terminated_grants * 3) + (non_renewed * 2) + (funding_drop / 500000)
    For now, non_renewed = 0 and funding_drop = 0
    """
    institution_counts = defaultdict(int)
    
    # Group terminated grants by institution
    for grant in terminated_grants:
        org_info = grant.get("organization", {})
        if isinstance(org_info, list) and len(org_info) > 0:
            org_name = org_info[0].get("org_name", "Unknown")
        elif isinstance(org_info, dict):
            org_name = org_info.get("org_name", "Unknown")
        else:
            org_name = "Unknown"
        
        institution_counts[org_name] += 1
    
    # Calculate risk scores
    risk_data = []
    for institution, terminated_count in institution_counts.items():
        if institution != "Unknown" and terminated_count > 0:
            # Risk score = (terminated_grants * 3) + (non_renewed * 2) + (funding_drop / 500000)
            # For now: non_renewed = 0, funding_drop = 0
            risk_score = terminated_count * 3
            
            risk_data.append({
                "institution": institution,
                "score": risk_score,
                "terminated": terminated_count
            })
    
    # Sort by risk score (highest first)
    risk_data.sort(key=lambda x: x["score"], reverse=True)
    
    return risk_data

@app.get("/")
async def root():
    return {"message": "NIH/NSF At-Risk Labs Tracker API"}

@app.get("/api/risk-leaderboard")
async def get_risk_leaderboard():
    """
    Get the risk leaderboard for institutions based on terminated grants.
    """
    try:
        terminated_grants = await fetch_terminated_grants()
        
        if not terminated_grants:
            return {
                "data": [
                    {"institution": "UCLA", "score": 9.5, "terminated": 4, "departments": ["Biology", "Chemistry"]},
                    {"institution": "Harvard", "score": 7.2, "terminated": 3, "departments": ["Neuroscience"]},
                    {"institution": "MIT", "score": 6.0, "terminated": 2, "departments": ["Engineering"]}
                ],
                "total": 3,
                "note": "Sample data - API may be unavailable"
            }
        
        # Group by institution and collect departments
        institution_data = {}
        
        for grant in terminated_grants:
            org_info = grant.get("organization", {})
            if isinstance(org_info, list) and len(org_info) > 0:
                org_name = org_info[0].get("org_name", "Unknown")
            elif isinstance(org_info, dict):
                org_name = org_info.get("org_name", "Unknown")
            else:
                org_name = "Unknown"
            
            if org_name == "Unknown":
                continue
            
            # Get department information
            dept_info = await guess_department(grant)
            dept_name = dept_info['department']
            
            if org_name not in institution_data:
                institution_data[org_name] = {
                    "terminated": 0, 
                    "departments": set(),
                    "dept_details": []
                }
            
            institution_data[org_name]["terminated"] += 1
            institution_data[org_name]["departments"].add(dept_name)
            institution_data[org_name]["dept_details"].append({
                "department": dept_name,
                "source": dept_info['source'],
                "confidence": dept_info['confidence']
            })
        
        # Build risk data
        risk_data = []
        for institution, info in institution_data.items():
            risk_score = info["terminated"] * 3
            
            # Calculate department confidence stats
            dept_sources = {}
            for detail in info["dept_details"]:
                source = detail["source"]
                dept_sources[source] = dept_sources.get(source, 0) + 1
            
            risk_data.append({
                "institution": institution,
                "score": risk_score,
                "terminated": info["terminated"],
                "departments": sorted(list(info["departments"])),
                "lookup_stats": dept_sources
            })
        
        # Sort by risk score (highest first)
        risk_data.sort(key=lambda x: x["score"], reverse=True)
        
        return {
            "data": risk_data[:20],
            "total": len(risk_data),
            "last_updated": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing data: {str(e)}")

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/api/test-scibert")
async def test_scibert_classifier(text: str):
    """
    Test endpoint for SciBERT department classification.
    Usage: /api/test-scibert?text=protein folding molecular dynamics
    """
    try:
        result = predict_department_scibert(text)
        return {
            "input_text": text,
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in SciBERT classification: {str(e)}")

@app.get("/api/train-classifier")
async def train_scibert_classifier(force_retrain: bool = False):
    """
    Train or retrain the SciBERT classifier.
    Usage: /api/train-classifier?force_retrain=true
    """
    try:
        train_classifier(force_retrain=force_retrain)
        return {
            "status": "success",
            "message": "Classifier training completed"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error training classifier: {str(e)}")

@app.get("/api/test-pi-lookup")
async def test_pi_lookup(name: str, institution: str, force_refresh: bool = False):
    """
    Test endpoint for PI department lookup.
    Usage: /api/test-pi-lookup?name=Jennifer Doudna&institution=UC Berkeley&force_refresh=true
    """
    try:
        result = await get_pi_department(name, institution, force_refresh=force_refresh)
        return {
            "pi_name": name,
            "institution": institution,
            "force_refresh": force_refresh,
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in PI lookup: {str(e)}")

@app.post("/api/test-multiple-lookups")
async def test_multiple_lookups(force_refresh: bool = False):
    """
    Test multiple PI lookups to verify the enhanced classification system.
    This is useful for testing cache regeneration and classification accuracy.
    """
    try:
        test_cases = [
            ("Kjersti Aagaard", "Baylor College of Medicine"),
            ("aagaard, kjersti marie", "baylor college of medicine"),  # Test name normalization
            ("Jennifer Doudna", "University of California, Berkeley"),
            ("Craig Venter", "J. Craig Venter Institute"),
            ("Frances Arnold", "California Institute of Technology"),
            ("George Church", "Harvard Medical School")
        ]
        
        results = []
        for name, institution in test_cases:
            try:
                result = await get_pi_department(name, institution, force_refresh=force_refresh)
                results.append({
                    "pi_name": name,
                    "institution": institution,
                    "result": result
                })
            except Exception as e:
                results.append({
                    "pi_name": name,
                    "institution": institution,
                    "error": str(e)
                })
        
        return {
            "status": "success",
            "test_cases": len(test_cases),
            "force_refresh": force_refresh,
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in multiple PI lookup test: {str(e)}")
        for name, institution in test_cases:
            try:
                result = await get_pi_department(name, institution, force_refresh=force_refresh)
                results.append({
                    "pi_name": name,
                    "institution": institution,
                    "result": result
                })
            except Exception as e:
                results.append({
                    "pi_name": name,
                    "institution": institution,
                    "error": str(e)
                })
        
        return {
            "status": "success",
            "test_cases": len(test_cases),
            "force_refresh": force_refresh,
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in multiple PI lookup test: {str(e)}")

@app.post("/api/refresh-specific-pi")
async def refresh_specific_pi(name: str, institution: str):
    """
    Force refresh a specific PI's department classification.
    Usage: POST /api/refresh-specific-pi?name=Kjersti Aagaard&institution=Baylor College of Medicine
    """
    try:
        # Force refresh this specific PI
        result = await get_pi_department(name, institution, force_refresh=True)
        
        return {
            "status": "success",
            "pi_name": name,
            "institution": institution,
            "message": "PI department classification refreshed with latest enhanced system",
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error refreshing PI: {str(e)}")

@app.get("/api/test-grant-mining")
async def test_grant_mining(name: str, institution: str):
    """
    Test endpoint for grant database mining.
    Usage: /api/test-grant-mining?name=Jennifer Doudna&institution=University of California, Berkeley
    """
    try:
        from grant_mining import classify_pi_from_grants
        
        result = await classify_pi_from_grants(name, institution)
        return {
            "pi_name": name,
            "institution": institution,
            "grant_mining_result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in grant mining: {str(e)}")

@app.get("/api/collect-training-data")
async def collect_training_data():
    """
    Collect training data from external sources (university descriptions, arXiv mappings, etc.).
    This expands the training dataset beyond ORCID data.
    """
    try:
        from training_data_sources import TrainingDataCollector
        
        collector = TrainingDataCollector()
        data = await collector.collect_all_data()
        
        # Save the enhanced training data
        final_data = collector.save_training_data(data)
        
        # Get statistics
        from collections import Counter
        label_counts = Counter(final_data['labels'])
        
        return {
            "status": "success",
            "message": "Training data collected and saved",
            "total_examples": len(final_data['texts']),
            "distribution": dict(label_counts.most_common()),
            "sources": ["university_descriptions", "arxiv_mappings", "synthetic_examples"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error collecting training data: {str(e)}")

@app.post("/api/cache/clear")
async def clear_cache():
    """
    Clear the entire PI department cache.
    This will force all future lookups to use the improved classification system.
    """
    try:
        from cache_refresh import CacheManager
        import os
        
        manager = CacheManager()
        success = manager.clear_cache()
        
        # Ensure the cache file is completely removed
        cache_file = "pi_department_cache.json"
        if os.path.exists(cache_file):
            os.remove(cache_file)
        
        return {
            "status": "success",
            "message": "Cache cleared successfully. New lookups will use the improved classification system with fresh ORCID and enhanced SciBERT analysis.",
            "note": "Next lookup will regenerate the cache with the latest classification improvements."
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing cache: {str(e)}")

@app.get("/api/cache/stats")
async def get_cache_stats():
    """Get statistics about the current cache state."""
    try:
        from cache_refresh import CacheManager
        
        manager = CacheManager()
        stats = manager.get_cache_stats()
        
        if "error" in stats:
            return {"error": stats["error"]}
        
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting cache stats: {str(e)}")

@app.post("/api/cache/refresh-unknowns")
async def refresh_unknown_pis():
    return await _refresh_unknown_pis_impl()

@app.get("/api/cache/refresh-unknowns")
async def refresh_unknown_pis_get():
    return await _refresh_unknown_pis_impl()

async def _refresh_unknown_pis_impl():
    """
    Refresh all PIs marked as 'Unknown' in the cache using the improved classification system.
    This is useful after enhancing thresholds or adding new classification methods.
    """
    try:
        import json
        import os
        cache_file = os.path.join(os.path.dirname(__file__), "pi_department_cache.json")
        
        if not os.path.exists(cache_file):
            return {"error": "Cache file not found", "refreshed": 0}
        
        # Read current cache
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache = json.load(f)
        
        unknown_entries = []
        for key, entry in cache.items():
            if entry.get('department') == 'Unknown':
                # Parse the key to get name and institution
                if '|' in key:
                    name_normalized, institution = key.split('|', 1)
                    # Convert normalized name back to readable format
                    name_parts = name_normalized.split()
                    if len(name_parts) == 2:
                        name = f"{name_parts[1].title()} {name_parts[0].title()}"
                    else:
                        name = name_normalized.title()
                    
                    unknown_entries.append((name, institution.title(), key))
        
        refreshed_count = 0
        successful_classifications = []
        
        # Refresh each unknown entry
        for name, institution, cache_key in unknown_entries[:10]:  # Limit to 10 to avoid timeouts
            try:
                result = await get_pi_department(name, institution, force_refresh=True)
                if result['department'] != 'Unknown':
                    refreshed_count += 1
                    successful_classifications.append({
                        "name": name,
                        "institution": institution,
                        "old_department": "Unknown",
                        "new_department": result['department'],
                        "source": result['source'],
                        "confidence": result['confidence']
                    })
            except Exception as e:
                print(f"Error refreshing {name}: {e}")
                continue
        
        return {
            "message": f"Refreshed {refreshed_count} out of {len(unknown_entries)} unknown PIs",
            "total_unknown": len(unknown_entries),
            "refreshed": refreshed_count,
            "successful_classifications": successful_classifications,
            "note": "Limited to 10 entries per request to avoid timeouts. Run again for more."
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error refreshing unknowns: {str(e)}")

async def fetch_active_grants(organization: str = None, pi_name: str = None) -> List[Dict[str, Any]]:
    """Fetch currently active grants for analysis - now includes both NIH and NSF."""
    from layoff_estimator import fetch_combined_grants
    return await fetch_combined_grants(organization=organization, pi_name=pi_name, active_only=True)

def estimate_lab_size(total_annual_funding: float, cost_per_researcher: float = 200000) -> Dict[str, Any]:
    """
    Estimate lab size based on total funding and cost per researcher.
    Default: $200k/year per researcher (salary + benefits + overhead)
    """
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

# Grant Cache Management Endpoints
@app.get("/api/grant-cache/status")
async def get_grant_cache_status():
    """Get status of grant data cache."""
    try:
        status = get_cache_status()
        return {
            "cache_status": status,
            "cache_duration_hours": 6,
            "description": "Cache status for NIH, NSF, and combined grant data"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting cache status: {str(e)}")

@app.post("/api/grant-cache/clear")
async def clear_grant_cache():
    """Clear all grant data cache."""
    try:
        clear_cache()
        return {"message": "Grant cache cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing cache: {str(e)}")

@app.post("/api/grant-cache/refresh")
async def refresh_grant_cache(max_records_per_source: int = 10000):
    """Force refresh of grant data cache with more records."""
    try:
        from layoff_estimator import fetch_combined_grants
        
        # Clear existing cache and fetch fresh data
        clear_cache()
        
        # Fetch with higher limits and force no cache usage
        grants = await fetch_combined_grants(
            use_cache=False, 
            max_records_per_source=max_records_per_source
        )
        
        nih_count = len([g for g in grants if g.get("funding_agency") == "NIH"])
        nsf_count = len([g for g in grants if g.get("funding_agency") == "NSF"])
        
        return {
            "message": "Grant cache refreshed successfully",
            "total_grants": len(grants),
            "nih_grants": nih_count,
            "nsf_grants": nsf_count,
            "max_records_per_source": max_records_per_source
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error refreshing cache: {str(e)}")

@app.get("/api/lab-size-estimator")
async def estimate_lab_impact(institution: str, cost_per_researcher: float = 200000):
    """
    Estimate lab sizes and potential layoff impact for an institution.
    Usage: /api/lab-size-estimator?institution=Harvard University&cost_per_researcher=200000
    """
    try:
        # Fetch active grants for the institution
        active_grants = await fetch_active_grants(organization=institution)
        terminated_grants = await fetch_terminated_grants()
        
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
            "funding_cliff": cliff_analysis,
            "layoff_risk": {
                "at_risk_positions": round(at_risk_positions, 1),
                "recently_lost_positions": round(recent_lost_positions, 1),
                "risk_level": "HIGH" if cliff_analysis["cliff_percentage"] > 50 else "MEDIUM" if cliff_analysis["cliff_percentage"] > 25 else "LOW"
            },
            "methodology": {
                "cost_per_researcher": cost_per_researcher,
                "analysis_window": "12 months ahead",
                "confidence": lab_size.get("confidence", "medium")
            },
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error estimating lab impact: {str(e)}")

@app.get("/api/pi-lab-analysis") 
async def analyze_pi_lab(pi_name: str, institution: str, cost_per_researcher: float = 200000):
    """
    Analyze a specific PI's lab for funding and layoff risk.
    Usage: /api/pi-lab-analysis?pi_name=Jennifer Doudna&institution=University of California, Berkeley
    """
    try:
        # Fetch grants for this specific PI
        active_grants = await fetch_active_grants(pi_name=pi_name)
        
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
        
        lab_size = estimate_lab_size(total_funding, cost_per_researcher)
        cliff_analysis = calculate_funding_cliff(active_grants, months_ahead=12)
        
        # Get department classification
        dept_result = await get_pi_department(pi_name, institution)
        
        return {
            "pi_name": pi_name,
            "institution": institution,
            "department": dept_result.get("department", "Unknown"),
            "lab_analysis": {
                "estimated_lab_size": lab_size,
                "funding_cliff": cliff_analysis,
                "grant_count": len(active_grants),
                "funding_diversification": "HIGH" if len(active_grants) >= 3 else "MEDIUM" if len(active_grants) == 2 else "LOW"
            },
            "layoff_risk": {
                "at_risk_positions": round(cliff_analysis["expiring_funding"] / cost_per_researcher, 1),
                "risk_level": "HIGH" if cliff_analysis["cliff_percentage"] > 60 else "MEDIUM" if cliff_analysis["cliff_percentage"] > 30 else "LOW",
                "primary_risk_factor": "Funding concentration" if len(active_grants) <= 2 else "Funding cliff" if cliff_analysis["cliff_percentage"] > 40 else "Normal"
            },
            "grants": [
                {
                    "title": grant.get("project_title", "Unknown")[:100] + "...",
                    "amount": grant.get("award_amount"),
                    "end_date": grant.get("project_end_date"),
                    "fiscal_year": grant.get("fiscal_year")
                }
                for grant in active_grants[:5]  # Show top 5 grants
            ],
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing PI lab: {str(e)}")

@app.get("/api/test-combined-grants")
async def test_combined_grants_endpoint():
    """Test endpoint to verify NIH + NSF grant fetching."""
    try:
        from layoff_estimator import fetch_combined_grants
        grants = await fetch_combined_grants(active_only=True)
        
        nih_count = sum(1 for g in grants if g.get("funding_agency") == "NIH")
        nsf_count = sum(1 for g in grants if g.get("funding_agency") == "NSF")
        
        return {
            "status": "success",
            "total_grants": len(grants),
            "nih_grants": nih_count,
            "nsf_grants": nsf_count,
            "sample_grants": grants[:3] if grants else []
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error testing combined grants: {str(e)}")

@app.get("/api/layoff-leaderboard")
async def get_layoff_risk_leaderboard(cost_per_researcher: float = 200000, limit: int = 20):
    """ Get institutions ranked by layoff risk using combined NIH+NSF data. """
    try:
        from layoff_estimator import generate_layoff_risk_leaderboard
        return await generate_layoff_risk_leaderboard(cost_per_researcher, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating leaderboard: {str(e)}")

@app.get("/api/institution-details")
async def get_institution_details(institution: str):
    """
    Get detailed information about a specific institution including PI details from cache.
    Uses the pi_department_cache to get enhanced PI information.
    """
    try:
        from layoff_estimator import fetch_combined_grants
        import json
        import os
        
        # Fetch grants for this institution
        active_grants = await fetch_combined_grants(organization=institution, active_only=True)
        
        if not active_grants:
            return {
                "error": f"No grants found for {institution}",
                "institution": institution
            }
        
        # Load PI department cache to get detailed PI information
        cache_file = os.path.join(os.path.dirname(__file__), "pi_department_cache.json")
        pi_cache = {}
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    pi_cache = json.load(f)
            except Exception as e:
                print(f"Error loading PI cache: {e}")
        
        # Group grants by PI and collect detailed information
        pi_details = {}
        
        for grant in active_grants:
            pi_name = grant.get("contact_pi_name", "Unknown")
            if not pi_name or pi_name == "Unknown":
                continue
                
            if pi_name not in pi_details:
                # Look up PI in cache
                pi_info = {"department": "Unknown", "source": "none", "confidence": "none"}
                
                # Try to find PI in cache (normalize name for lookup)
                normalized_name = pi_name.lower().strip()
                for key in pi_cache.keys():
                    if institution.lower() in key.lower() and normalized_name in key.lower():
                        pi_info = pi_cache[key]
                        break
                
                pi_details[pi_name] = {
                    "name": pi_name,
                    "department": pi_info.get("department", "Unknown"),
                    "source": pi_info.get("source", "none"),
                    "confidence": pi_info.get("confidence", "none"),
                    "grants": [],
                    "total_funding": 0,
                    "grant_count": 0
                }
            
            # Add grant to PI
            try:
                grant_amount = float(grant.get("award_amount", 0))
                pi_details[pi_name]["total_funding"] += grant_amount
                pi_details[pi_name]["grant_count"] += 1
                pi_details[pi_name]["grants"].append({
                    "title": grant.get("project_title", "Unknown"),
                    "amount": grant_amount,
                    "agency": grant.get("funding_agency", "Unknown"),
                    "end_date": grant.get("project_end_date", "Unknown")
                })
            except (ValueError, TypeError):
                pi_details[pi_name]["grant_count"] += 1
                pi_details[pi_name]["grants"].append({
                    "title": grant.get("project_title", "Unknown"),
                    "amount": 0,
                    "agency": grant.get("funding_agency", "Unknown"),
                    "end_date": grant.get("project_end_date", "Unknown")
                })
        
        # Sort PIs by total funding
        sorted_pis = sorted(
            pi_details.values(), 
            key=lambda x: x["total_funding"], 
            reverse=True
        )
        
        # Add recent grants to each PI (top 3 most recent)
        for pi in sorted_pis:
            pi["recent_grants"] = sorted(
                pi["grants"], 
                key=lambda x: x.get("end_date", ""), 
                reverse=True
            )[:3]
        
        return {
            "institution": institution,
            "pi_details": sorted_pis,
            "total_pis": len(sorted_pis),
            "total_grants": len(active_grants),
            "total_funding": sum(pi["total_funding"] for pi in sorted_pis),
            "department_breakdown": {
                dept: len([pi for pi in sorted_pis if pi["department"] == dept])
                for dept in set(pi["department"] for pi in sorted_pis)
            },
            "cache_info": {
                "cache_entries": len(pi_cache),
                "cache_hit_rate": len([pi for pi in sorted_pis if pi["source"] != "none"]) / len(sorted_pis) if sorted_pis else 0
            },
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting institution details: {str(e)}")

def group_grants_by_institution(active_grants, terminated_grants):
    """
    Group active and terminated grants by institution and sum funding.
    Returns a dict mapping institution name to grant lists and funding totals.
    """
    institution_data = defaultdict(lambda: {
        "active_grants": [],
        "terminated_grants": [],
        "total_active_funding": 0,
        "total_terminated_funding": 0
    })
    
    def extract_name(org_info):
        if isinstance(org_info, list) and org_info:
            return org_info[0].get("org_name", "Unknown")
        if isinstance(org_info, dict):
            return org_info.get("org_name", "Unknown")
        return "Unknown"

    for grant in active_grants:
        name = extract_name(grant.get("organization", {}))
        if name != "Unknown":
            institution_data[name]["active_grants"].append(grant)
            try:
                institution_data[name]["total_active_funding"] += float(grant.get("award_amount", 0))
            except (ValueError, TypeError):
                pass

    for grant in terminated_grants:
        name = extract_name(grant.get("organization", {}))
        if name in institution_data:
            institution_data[name]["terminated_grants"].append(grant)
            try:
                institution_data[name]["total_terminated_funding"] += float(grant.get("award_amount", 0))
            except (ValueError, TypeError):
                pass

    return institution_data


def calculate_institution_risk(institution, data, cost_per_researcher):
    """
    Calculate layoff risk metrics for one institution.
    Returns a dict of summarized risk values or None if skipped.
    """
    if data["total_active_funding"] < 100000:
        return None

    lab = estimate_lab_size(data["total_active_funding"], cost_per_researcher)
    cliff = calculate_funding_cliff(data["active_grants"], months_ahead=12)

    cliff_weight = cliff["cliff_percentage"] * 0.4
    term_weight = (data["total_terminated_funding"] / data["total_active_funding"] * 100) * 0.3 if data["total_active_funding"] > 0 else 0
    size_weight = min(lab["estimated_researchers"] * 2, 20)
    penalty = max(0, (3 - len(data["active_grants"])) * 5)

    score = cliff_weight + term_weight + size_weight + penalty
    at_risk = cliff["expiring_funding"] / cost_per_researcher
    lost = data["total_terminated_funding"] / cost_per_researcher

    level = (
        "CRITICAL" if score > 70 else
        "HIGH" if score > 50 else
        "MEDIUM" if score > 30 else
        "LOW"
    )

    return {
        "institution": institution,
        "risk_score": round(score, 1),
        "estimated_lab_size": lab["estimated_researchers"],
        "at_risk_positions": round(at_risk, 1),
        "recently_lost_positions": round(lost, 1),
        "funding_cliff_percentage": cliff["cliff_percentage"],
        "total_active_funding": data["total_active_funding"],
        "active_grants_count": len(data["active_grants"]),
        "terminated_grants_count": len(data["terminated_grants"]),
        "risk_level": level
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)


