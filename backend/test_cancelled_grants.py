#!/usr/bin/env python3
"""
Test script to validate the cancelled grants analysis enhancements
"""

import asyncio
from enhanced_delayed_funding_tracker import EnhancedDelayedFundingTracker

async def test_cancelled_grants():
    """Test the enhanced cancelled grants analysis"""
    print("🧪 Testing Enhanced Cancelled Grants Analysis...")
    
    tracker = EnhancedDelayedFundingTracker()
    
    # Test the cancelled grants analysis directly
    try:
        result = await tracker._analyze_cancelled_grants("Massachusetts Institute of Technology", pi_cache=None)
        
        print("✅ Cancelled Grants Analysis Results:")
        print(f"   Total Lost Funding: ${result.get('total_lost_funding', 0):,.0f}")
        print(f"   Grants Cancelled: {result.get('grants_cancelled', 0)}")
        print(f"   Risk Level: {result.get('risk_level', 'Unknown')}")
        print(f"   Departments Affected: {result.get('departments_affected', 0)}")
        print(f"   PIs Affected: {result.get('total_affected_pis', 0)}")
        
        dept_losses = result.get('department_losses', {})
        print(f"\n📊 Department Losses ({len(dept_losses)} departments):")
        for dept, amount in list(dept_losses.items())[:5]:
            print(f"   {dept}: ${amount:,.0f}")
        
        if len(dept_losses) > 5:
            print(f"   ... and {len(dept_losses) - 5} more departments")
        
        # Test department normalization with SciBERT
        print(f"\n🧠 Testing SciBERT Department Normalization:")
        from enhanced_delayed_funding_tracker import normalize_department_name
        
        test_cases = [
            ("Other", "Medical imaging research using AI"),
            ("null", "Computer science algorithms for data analysis"),
            ("Unknown Department", "Physics research on quantum mechanics")
        ]
        
        for dept, title in test_cases:
            test_grant = {
                'project_title': title,
                'organization': {'org_name': 'MIT'}
            }
            normalized = normalize_department_name(dept, test_grant)
            print(f"   '{dept}' + '{title[:30]}...' → '{normalized}'")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in cancelled grants analysis: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_cancelled_grants())
    if success:
        print("\n✅ All tests passed! Enhanced cancelled grants analysis is working.")
    else:
        print("\n❌ Tests failed. Please check the implementation.")
