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
        
        # Create tracker and perform analysis
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
