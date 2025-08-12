#!/usr/bin/env python3
"""
Test the complete dual data source strategy:
- Layoff leaderboard using USASpending data
- Enhanced analysis using fresh NIH/NSF data
"""

import requests
import json

# Use the running server on port 8001
BASE_URL = "http://localhost:8001"

def test_dual_data_strategy():
    """Test both leaderboard and enhanced analysis work correctly"""
    
    print("🧪 Testing Dual Data Source Strategy")
    print("=" * 60)
    
    # Test 1: Layoff Leaderboard (USASpending data)
    print("\n1️⃣ Testing Layoff Leaderboard (USASpending)")
    print("-" * 40)
    
    try:
        response = requests.get(f"{BASE_URL}/layoff-leaderboard?limit=5", timeout=30)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Leaderboard returned {len(data.get('leaderboard', []))} institutions")
            
            # Show top 3
            for i, institution in enumerate(data.get('leaderboard', [])[:3]):
                print(f"   {i+1}. {institution.get('institution')} - Risk: {institution.get('risk_score', 0):.1f}")
        else:
            print(f"❌ Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Leaderboard test failed: {e}")
    
    # Test 2: Enhanced Analysis (Fresh NIH/NSF data)
    print("\n2️⃣ Testing Enhanced Analysis (Fresh NIH/NSF)")
    print("-" * 40)
    
    test_institutions = ["Harvard University", "Duke University", "University of California"]
    
    for institution in test_institutions:
        try:
            print(f"\n🏛️ Testing: {institution}")
            response = requests.get(f"{BASE_URL}/university-details/{institution}", timeout=30)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                source = data.get('data_source', 'Unknown')
                total_grants = data.get('overview', {}).get('total_grants', 0)
                total_funding = data.get('overview', {}).get('total_funding', 0)
                
                print(f"   ✅ Data Source: {source}")
                print(f"   📊 Grants: {total_grants:,}")
                print(f"   💰 Funding: ${total_funding:,.0f}")
                
                # Check if using fresh NIH/NSF data
                if 'Fresh NIH/NSF' in source:
                    print(f"   🎯 SUCCESS: Using fresh NIH/NSF data!")
                elif 'enhanced_delayed_funding' in source.lower():
                    print(f"   ⚠️  Using enhanced delayed funding (fallback)")
                else:
                    print(f"   ❓ Using: {source}")
                    
            else:
                print(f"   ❌ Error: {response.text}")
                
        except Exception as e:
            print(f"   ❌ Analysis test failed: {e}")
    
    # Test 3: Compare Data Sources
    print("\n3️⃣ Data Source Strategy Summary")
    print("-" * 40)
    print("✅ Layoff Leaderboard: USASpending.gov (comprehensive tracking)")
    print("✅ Enhanced Analysis: NIH/NSF APIs (research-specific, real-time)")
    print("✅ Fallback Strategy: USASpending for institutions without NIH/NSF data")
    
    print("\n🎉 Dual Data Source Strategy Testing Complete!")

if __name__ == "__main__":
    test_dual_data_strategy()
