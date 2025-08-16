#!/usr/bin/env python3
"""
Test script to verify NSF terminated grants functionality
"""

import asyncio
from enhanced_delayed_funding_tracker import EnhancedDelayedFundingTracker

async def test_nsf_terminated_grants():
    """Test the new NSF terminated grants functionality"""
    
    tracker = EnhancedDelayedFundingTracker()
    
    # Test with Oregon State University which we know has data
    institution_name = "Oregon State University"
    
    print(f"🧪 Testing terminated grants analysis for {institution_name}")
    print("=" * 60)
    
    try:
        # Call the private method directly to test NSF integration
        result = await tracker._analyze_cancelled_grants(institution_name)
        
        print(f"✅ Analysis completed successfully!")
        print(f"Total cancelled funding: ${result.get('total_lost_funding', 0):,.2f}")
        print(f"Total affected PIs: {result.get('total_affected_pis', 0)}")
        print(f"Grants cancelled: {result.get('grants_cancelled', 0)}")
        
        # Debug: Show raw values
        print(f"\nDEBUG INFO:")
        print(f"  Raw total_lost_funding: {result.get('total_lost_funding')}")
        print(f"  Department losses keys: {list(result.get('department_losses', {}).keys())}")
        print(f"  Department losses values: {list(result.get('department_losses', {}).values())}")
        print(f"  Sum of dept losses: {sum(result.get('department_losses', {}).values())}")
        
        # Show breakdown by agency if available
        if 'agency_breakdown' in result:
            print("\nAgency Breakdown:")
            for agency, amount in result['agency_breakdown'].items():
                print(f"  {agency}: ${amount:,.2f}")
        
        # Show top affected departments
        if 'department_losses' in result and result['department_losses']:
            print("\nTop Affected Departments:")
            sorted_depts = sorted(result['department_losses'].items(), 
                                key=lambda x: x[1], reverse=True)[:5]
            for dept, amount in sorted_depts:
                print(f"  {dept}: ${amount:,.2f}")
        
        # Show top affected PIs
        if 'top_pis' in result and result['top_pis']:
            print("\nTop Affected PIs:")
            for pi in result['top_pis'][:5]:
                print(f"  {pi['pi_name']} ({pi['department']}): ${pi['lost_funding']:,.2f}")
        
        print(f"\n🔍 Analysis included both NIH and NSF terminated grants")
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_nsf_terminated_grants())
