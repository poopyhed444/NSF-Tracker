from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import httpx
import asyncio
import os
from typing import List, Dict, Any
import json
from collections import defaultdict

# Simple imports that don't require problematic dependencies
from layoff_estimator import generate_layoff_risk_leaderboard
from grant_cache import get_cache_status, clear_cache

app = FastAPI(title="NIH/NSF At-Risk Labs Tracker", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add a basic health check endpoint
@app.get("/")
async def root():
    return {"message": "NIH/NSF At-Risk Labs Tracker API"}

@app.get("/api/layoff-leaderboard")
async def get_layoff_leaderboard(limit: int = 25):
    """Get institutions ranked by estimated layoff risk"""
    try:
        print(f"\n=== Fetching layoff leaderboard with limit: {limit} ===")
        
        # Use the existing leaderboard function
        result = await generate_layoff_risk_leaderboard(limit=limit)
        
        # Reformat the result to match expected frontend structure
        leaderboard_data = result.get('institutions', [])
        
        return {
            "data": leaderboard_data,
            "total_count": len(leaderboard_data),
            "showing_count": len(leaderboard_data),
            "timestamp": datetime.now().isoformat(),
            "grants_analyzed": result.get('total_grants_analyzed', 0)
        }
        
    except Exception as e:
        print(f"Error in get_layoff_leaderboard: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error calculating leaderboard: {str(e)}")

@app.get("/api/grant-cache/status")
async def get_grant_cache_status():
    """Get current grant cache status"""
    try:
        status = get_cache_status()
        return {"status": "success", "cache_info": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting cache status: {str(e)}")

@app.get("/api/grant-cache/clear") 
async def clear_grant_cache():
    """Clear all grant caches"""
    try:
        clear_cache()
        return {"status": "success", "message": "All grant caches cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing cache: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
