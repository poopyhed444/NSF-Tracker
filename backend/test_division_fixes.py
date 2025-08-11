#!/usr/bin/env python3
"""
Test division by zero fixes in delayed funding calculations.
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from delayed_funding_tracker import analyze_delayed_funding_for_institution

async def test_division_by_zero_fixes():
    """Test that division by zero issues are properly handled"""
    
    print("🧪 Testing division by zero fixes in delayed funding calculations...")
    
    # Test cases that might cause division by zero
    test_institutions = [
        "Nonexistent University",
        "Test Institution With No Data", 
        "Empty Data University"
    ]
    
    for institution in test_institutions:
        print(f"\n🔍 Testing: {institution}")
        try:
            result = await analyze_delayed_funding_for_institution(institution)
            
            if result and 'summary' in result:
                summary = result['summary']
                
                # Check for NaN values
                fields_to_check = [
                    'total_undisbursed',
                    'disbursement_efficiency', 
                    'delayed_funding_risk'
                ]
                
                for field in fields_to_check:
                    value = summary.get(field, 0)
                    if isinstance(value, float) and (value != value):  # Check for NaN
                        print(f"  ❌ Found NaN in {field}: {value}")
                    elif isinstance(value, float) and value == float('inf'):
                        print(f"  ❌ Found infinity in {field}: {value}")
                    else:
                        print(f"  ✅ {field}: {value}")
                        
            else:
                print(f"  ✅ No data returned (expected for nonexistent institution)")
                
        except Exception as e:
            print(f"  ❌ Error testing {institution}: {e}")

if __name__ == "__main__":
    asyncio.run(test_division_by_zero_fixes())
