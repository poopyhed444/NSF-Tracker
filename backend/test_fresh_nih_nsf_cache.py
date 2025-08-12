#!/usr/bin/env python3
"""
Test the fresh NIH/NSF grant cache data directly
"""

import asyncio
import sys
import os
import json

# Add the backend directory to path
sys.path.append(os.path.join(os.path.dirname(__file__)))

async def test_fresh_nih_nsf_data():
    """Test the fresh NIH/NSF grant cache data"""
    try:
        print("🧪 Testing fresh NIH/NSF grant cache data...")
        
        # Load the fresh grant cache files
        from grant_cache import get_nih_cache, get_nsf_cache, get_combined_cache
        
        print("\n📂 Loading fresh cache files...")
        nih_grants = get_nih_cache()
        nsf_grants = get_nsf_cache()
        combined_grants = get_combined_cache()
        
        print(f"✅ NIH grants loaded: {len(nih_grants)}")
        print(f"✅ NSF grants loaded: {len(nsf_grants)}")
        print(f"✅ Combined grants loaded: {len(combined_grants)}")
        
        if not combined_grants:
            print("❌ No grants found in cache!")
            return
            
        # Test specific institutions from our fresh data
        test_institutions = [
            "DUKE UNIVERSITY",
            "UNIVERSITY OF CALIFORNIA LOS ANGELES", 
            "JOHNS HOPKINS UNIVERSITY",
            "HARVARD UNIVERSITY"
        ]
        
        print(f"\n🔍 Analyzing fresh grant data...")
        
        for institution_name in test_institutions:
            print(f"\n🏛️ Testing {institution_name}...")
            
            # Filter grants for this institution
            institution_grants = []
            total_funding = 0
            
            for grant in combined_grants:
                # Check organization info
                org_info = grant.get('organization', {})
                if isinstance(org_info, list) and org_info:
                    org_name = org_info[0].get('org_name', '')
                elif isinstance(org_info, dict):
                    org_name = org_info.get('org_name', '')
                else:
                    continue
                
                # Normalize names for comparison
                if institution_name.upper() in org_name.upper() or org_name.upper() in institution_name.upper():
                    institution_grants.append(grant)
                    try:
                        amount = float(grant.get('award_amount', 0) or 0)
                        total_funding += amount
                    except:
                        pass
            
            print(f"   📊 Grants found: {len(institution_grants)}")
            print(f"   💰 Total funding: ${total_funding:,.2f}")
            
            if len(institution_grants) > 0:
                print(f"   ✅ Fresh NIH/NSF data found!")
                
                # Show sample grant
                sample_grant = institution_grants[0]
                print(f"   📋 Sample grant: {sample_grant.get('project_title', 'N/A')[:60]}...")
                print(f"   🏢 Agency: {sample_grant.get('funding_agency', 'N/A')}")
                print(f"   💵 Amount: ${float(sample_grant.get('award_amount', 0) or 0):,.2f}")
            else:
                print(f"   ⚠️ No grants found for this institution")
                
        # Show overall cache statistics
        print(f"\n📈 Fresh Cache Statistics:")
        total_funding = 0
        nih_count = 0
        nsf_count = 0
        
        for grant in combined_grants:
            try:
                amount = float(grant.get('award_amount', 0) or 0)
                total_funding += amount
                agency = grant.get('funding_agency', '').upper()
                if agency == 'NIH':
                    nih_count += 1
                elif agency == 'NSF':
                    nsf_count += 1
            except:
                pass
                
        print(f"   💰 Total funding: ${total_funding:,.2f}")
        print(f"   🏥 NIH grants: {nih_count}")
        print(f"   🔬 NSF grants: {nsf_count}")
        print(f"   📅 Data freshly scraped from APIs!")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_fresh_nih_nsf_data())
