#!/usr/bin/env python3
"""
Simple working version of the comprehensive delayed funding analysis function
that uses optimized caching and the enhanced tracker.
"""

async def get_comprehensive_delayed_funding_analysis_clean(
    institution_name: str,
    include_departments: bool = True,
    method: str = "comprehensive",
    force_refresh: bool = False
):
    """
    Clean comprehensive delayed funding analysis with optimized caching.
    """
    from datetime import datetime as dt
    from optimized_cache import get_cached_analysis, save_cached_analysis
    
    try:
        print(f"🔍 Comprehensive delayed funding analysis for: {institution_name} (method: {method}, departments: {include_departments})")
        
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
        
        # Load PI cache (function defined in enhanced_main.py)
        import os
        import json
        
        def load_pi_cache():
            try:
                cache_file = "pi_department_cache.json"
                if os.path.exists(cache_file):
                    with open(cache_file, 'r') as f:
                        return json.load(f)
                return {}
            except Exception as e:
                print(f"Error loading PI department cache: {e}")
                return {}
        
        # Create tracker and perform analysis
        tracker = EnhancedDelayedFundingTracker()
        pi_cache = load_pi_cache()
        
        result = await tracker.analyze_comprehensive_delays(
            institution_name=institution_name,
            pi_cache=pi_cache
        )
        
        # Add metadata
        result.update({
            'institution': institution_name,
            'analysis_date': dt.now().isoformat(),
            'method': method,
            'include_departments': include_departments
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
            'analysis_date': dt.now().isoformat()
        }
