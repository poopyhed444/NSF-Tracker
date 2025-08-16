#!/usr/bin/env python3
"""
Test script to verify the cancelled grants data structure and field names
"""

import asyncio
import json

async def test_cancelled_grants_structure():
    """Test the cancelled grants data structure to verify field names"""
    
    try:
        print("🧪 Testing cancelled grants data structure...")
        
        from enhanced_delayed_funding_tracker import EnhancedDelayedFundingTracker
        
        tracker = EnhancedDelayedFundingTracker()
        
        # Test with Oregon State University
        institution_name = "Oregon State University"
        
        print(f"📊 Getting cancelled grants data for {institution_name}...")
        result = await tracker._analyze_cancelled_grants(institution_name)
        
        print("✅ Cancelled grants analysis completed!")
        print(f"Data structure:")
        
        # Print the actual field names and values
        for key, value in result.items():
            if key == 'top_affected_pis' and isinstance(value, list) and len(value) > 0:
                print(f"  {key}: [")
                for i, pi in enumerate(value[:2]):  # Show first 2 PIs
                    print(f"    PI {i+1}: {json.dumps(pi, indent=6)}")
                print(f"    ... ({len(value)} total PIs)")
                print("  ]")
            elif key == 'department_losses':
                print(f"  {key}: {dict(list(value.items())[:3])}  # (showing first 3)")
            else:
                print(f"  {key}: {value}")
        
        print(f"\n🔍 Key findings:")
        print(f"  - Field name for PI count: 'total_affected_pis' = {result.get('total_affected_pis')}")
        print(f"  - Field name for total funding: 'total_lost_funding' = {result.get('total_lost_funding')}")
        print(f"  - Field name for top PIs: 'top_affected_pis' (length: {len(result.get('top_affected_pis', []))})")
        
        # Frontend should use:
        print(f"\n✅ Frontend should use:")
        print(f"  - PIs Impacted: {{data.cancelled_grants_impact.total_affected_pis || 0}}")
        print(f"  - Total Lost Funding: {{data.cancelled_grants_impact.total_lost_funding}}")
        print(f"  - Top PIs: {{data.cancelled_grants_impact.top_affected_pis}}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_cancelled_grants_structure())
