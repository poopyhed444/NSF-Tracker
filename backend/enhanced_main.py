#!/usr/bin/env python3
"""
Clean FastAPI server for NSF-Tracker with enhanced multi-agency integration.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import asyncio
from layoff_estimator import generate_layoff_risk_leaderboard, fetch_combined_grants
from grant_cache import clear_cache

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

@app.get("/api/layoff-leaderboard")
async def get_layoff_risk_leaderboard(cost_per_researcher: float = 200000, limit: int = 20):
    """Get institutions ranked by layoff risk using enhanced multi-agency data."""
    try:
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
                institution_samples[agency] = {
                    "institution": sample.get('organization', [{}])[0].get('org_name', 'Unknown'),
                    "amount": sample.get('award_amount', 0),
                    "title": sample.get('project_title', '')[:100] + "..." if len(sample.get('project_title', '')) > 100 else sample.get('project_title', ''),
                    "source": sample.get('source', 'Unknown')
                }
        
        funding_samples = {}
        for agency in list(funding_agency_counts.keys())[:3]:  # Top 3 agencies
            agency_grants = [g for g in funding_grants if g.get("funding_agency") == agency]
            if agency_grants:
                sample = agency_grants[0]
                funding_samples[agency] = {
                    "institution": sample.get('organization', [{}])[0].get('org_name', 'Unknown'),
                    "amount": sample.get('award_amount', 0),
                    "title": sample.get('project_title', '')[:100] + "..." if len(sample.get('project_title', '')) > 100 else sample.get('project_title', ''),
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
        
        # Force fresh data fetch
        fresh_grants = await fetch_combined_grants(use_cache=False)
        
        # Count by agency
        nih_count = len([g for g in fresh_grants if g.get("funding_agency") == "NIH"])
        nsf_count = len([g for g in fresh_grants if g.get("funding_agency") == "NSF"])
        dod_count = len([g for g in fresh_grants if g.get("funding_agency") == "DOD"])
        doe_count = len([g for g in fresh_grants if g.get("funding_agency") == "DOE"])
        
        return {
            "status": "success",
            "message": "Grant cache refreshed successfully with enhanced integration",
            "total_grants": len(fresh_grants),
            "agency_breakdown": {
                "NIH": nih_count,
                "NSF": nsf_count,
                "DOD": dod_count,
                "DOE": doe_count
            },
            "refreshed_at": datetime.now().isoformat(),
            "data_sources": [
                "NIH Reporter API (direct)",
                "NSF Awards API (direct)",
                "USASpending.gov API (DoD/DoE)"
            ]
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
