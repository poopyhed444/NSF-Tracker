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

app = FastAPI(title="NIH/NSF At-Risk Labs Tracker", version="1.0.0")

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)
