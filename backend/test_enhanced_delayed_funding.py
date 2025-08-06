"""
Comprehensive test for the enhanced delayed funding analysis system.
Tests both disbursement delays and renewal delays across multiple agencies.
"""

import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Import the enhanced functionality
from delayed_funding_tracker import DelayedFundingTracker, EnhancedDelayedFundingTracker
from grant_cache import clear_cache
from usaspending_cache_loader import USASpendingCacheLoader

# Configuration
TEST_INSTITUTIONS = [
    "Stanford University",
    "Harvard University",
    "Massachusetts Institute of Technology",
    "University of California Berkeley"
]

async def test_comprehensive_delayed_funding():
    """
    Test the comprehensive delayed funding analysis system.
    Combines both disbursement analysis and renewal analysis.
    """
    print("\n===== COMPREHENSIVE DELAYED FUNDING ANALYSIS TEST =====")
    
    # Create tracker instances
    standard_tracker = DelayedFundingTracker()
    enhanced_tracker = EnhancedDelayedFundingTracker()
    
    # Load PI department cache for department-level analysis
    pi_cache = {}
    try:
        if os.path.exists("pi_department_cache.json"):
            with open("pi_department_cache.json", "r") as f:
                pi_cache = json.load(f)
            print(f"Loaded PI cache with {len(pi_cache)} entries")
        else:
            print("PI cache not found. Department analysis will use 'Unknown Department'")
    except Exception as e:
        print(f"Error loading PI cache: {e}")
    
    # Test each institution
    for institution in TEST_INSTITUTIONS:
        print(f"\n----- Testing: {institution} -----")
        
        # 1. Standard Disbursement Analysis
        print("\n1. DISBURSEMENT DELAY ANALYSIS (Original Method):")
        try:
            standard_results = await standard_tracker.analyze_delayed_funding_for_institution(institution)
            print(f"  • Total Undisbursed: ${standard_results['undisbursed_amount']:,.2f}")
            print(f"  • Disbursement Efficiency: {standard_results['disbursement_efficiency']:.1f}%")
            print(f"  • Cash Flow Risk: {standard_results['cash_flow_risk']}")
            print(f"  • Delayed Awards: {standard_results['delayed_awards_count']} of {standard_results['awards_count']}")
        except Exception as e:
            print(f"  Error in disbursement analysis: {e}")
        
        # 2. Enhanced Renewal Analysis (Times Method)
        print("\n2. RENEWAL DELAY ANALYSIS (Times Method):")
        try:
            current_date = datetime.now()
            start_date = (current_date - timedelta(days=100)).strftime("%Y-%m-%d")
            end_date = current_date.strftime("%Y-%m-%d")
            
            renewal_results = await enhanced_tracker.analyze_renewal_delays(
                institution_name=institution,
                start_date=start_date,
                end_date=end_date
            )
            
            print(f"  • Expected Renewals: {renewal_results['expected_renewals']}")
            print(f"  • Missing Renewals: {renewal_results['missing_renewals']}")
            print(f"  • Renewal Rate: {renewal_results['renewal_rate']:.1f}%")
            print(f"  • At-Risk Funding: ${renewal_results['at_risk_amount']:,.2f}")
            print(f"  • Renewal Risk Level: {renewal_results['risk_level']}")
        except Exception as e:
            print(f"  Error in renewal analysis: {e}")
        
        # 3. Department-Level Analysis
        print("\n3. DEPARTMENT-LEVEL ANALYSIS:")
        try:
            dept_results = await enhanced_tracker.analyze_delays_by_department(
                institution_name=institution, 
                pi_cache=pi_cache
            )
            
            print(f"  Found {len(dept_results['departments'])} departments with delays:")
            for i, dept in enumerate(dept_results['departments'][:3]):  # Show top 3
                print(f"  {i+1}. {dept['name']}:")
                print(f"     - Undisbursed: ${dept['undisbursed']:,.2f}")
                print(f"     - Delayed Renewals: {dept['delayed_renewals']}")
                print(f"     - Risk Level: {dept['risk_level']}")
            
            if len(dept_results['departments']) > 3:
                print(f"  ...and {len(dept_results['departments'])-3} more departments")
        except Exception as e:
            print(f"  Error in department analysis: {e}")
        
        # 4. Comprehensive Analysis
        print("\n4. COMPREHENSIVE ANALYSIS (Combined Method):")
        try:
            comprehensive_results = await enhanced_tracker.analyze_comprehensive_delays(
                institution_name=institution,
                pi_cache=pi_cache
            )
            
            print(f"  • Overall Risk Level: {comprehensive_results['overall_risk_level']}")
            print(f"  • Combined Risk Score: {comprehensive_results['combined_risk_score']:.1f}/100")
            print(f"  • Total At-Risk Funding: ${comprehensive_results['total_at_risk']:,.2f}")
            print(f"  • Agencies with Delays: {', '.join(comprehensive_results['agencies_with_delays'][:3])}")
            print(f"  • Most Impacted Department: {comprehensive_results['most_impacted_department']}")
        except Exception as e:
            print(f"  Error in comprehensive analysis: {e}")
    
    # 5. Test Caching
    print("\n5. TESTING CACHE EFFICIENCY:")
    try:
        start_time = datetime.now()
        # First run (no cache)
        clear_cache("delayed_funding_cache")
        await enhanced_tracker.analyze_comprehensive_delays(TEST_INSTITUTIONS[0], pi_cache)
        first_run = (datetime.now() - start_time).total_seconds()
        
        # Second run (with cache)
        start_time = datetime.now()
        await enhanced_tracker.analyze_comprehensive_delays(TEST_INSTITUTIONS[0], pi_cache)
        second_run = (datetime.now() - start_time).total_seconds()
        
        print(f"  • First run (no cache): {first_run:.2f} seconds")
        print(f"  • Second run (cached): {second_run:.2f} seconds")
        print(f"  • Speed improvement: {((first_run - second_run) / first_run * 100):.1f}%")
    except Exception as e:
        print(f"  Error testing cache: {e}")
    
    print("\n===== TEST COMPLETE =====")

if __name__ == "__main__":
    asyncio.run(test_comprehensive_delayed_funding())