#!/usr/bin/env python3
"""
Test the fresh grant data to verify it's being used
"""

import asyncio
import sys
import os

# Add the backend directory to path
sys.path.append(os.path.join(os.path.dirname(__file__)))

async def test_fresh_data():
    """Test that the system is using fresh grant data"""
    try:
        from layoff_estimator import get_institution_total_funding
        
        print("🧪 Testing fresh grant data...")
        
        # Test a major university that should have substantial funding
        test_institutions = [
            "Harvard University",
            "Stanford University", 
            "University of California, Los Angeles",
            "Johns Hopkins University"
        ]
        
        for institution in test_institutions:
            print(f"\n🏛️ Testing {institution}...")
            result = await get_institution_total_funding(institution)
            
            if result and 'total_funding' in result:
                funding = result['total_funding']
                active_grants = result.get('active_grants_count', 0)
                print(f"   💰 Total funding: ${funding:,.2f}")
                print(f"   📊 Active grants: {active_grants}")
                
                if funding > 0:
                    print(f"   ✅ Fresh data detected!")
                else:
                    print(f"   ⚠️ No funding found")
            else:
                print(f"   ❌ No data returned")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_fresh_data())
