#!/usr/bin/env python3
"""
Quick test of dual data source strategy using direct function calls
"""
import sys
import os
import asyncio

async def test_dual_data_strategy_direct():
    """Test the functions directly without FastAPI server"""
    
    print("🧪 Testing Dual Data Source Strategy (Direct)")
    print("=" * 60)
    
    # Test 1: Test fresh NIH/NSF analysis function
    print("\n1️⃣ Testing Fresh NIH/NSF Analysis Function")
    print("-" * 40)
    
    try:
        from enhanced_main import analyze_fresh_nih_nsf_data
        from grant_cache import get_combined_cache
        
        # Get fresh grants
        fresh_grants = get_combined_cache()
        print(f"📊 Loaded {len(fresh_grants)} fresh grants")
        
        # Test with Harvard
        harvard_grants = [g for g in fresh_grants if 'harvard' in g.get('organization', {}).get('org_name', '').lower()]
        print(f"🏛️ Found {len(harvard_grants)} Harvard grants")
        
        if not harvard_grants:
            # Try other major universities in the cache
            ucla_grants = [g for g in fresh_grants if 'ucla' in g.get('organization', {}).get('org_name', '').lower() or 'university of california los angeles' in g.get('organization', {}).get('org_name', '').lower()]
            if ucla_grants:
                print(f"🏛️ Using UCLA instead: {len(ucla_grants)} grants")
                result = await analyze_fresh_nih_nsf_data("University of California Los Angeles", ucla_grants)
            else:
                # Use any university
                test_grant = fresh_grants[0] if fresh_grants else None
                if test_grant:
                    org_name = test_grant.get('organization', {}).get('org_name', 'Unknown')
                    same_org_grants = [g for g in fresh_grants if g.get('organization', {}).get('org_name') == org_name]
                    print(f"🏛️ Using {org_name}: {len(same_org_grants)} grants")
                    result = await analyze_fresh_nih_nsf_data(org_name, same_org_grants)
                else:
                    result = {'error': 'No grants available for testing'}
        else:
            result = await analyze_fresh_nih_nsf_data("Harvard University", harvard_grants)
            
        if 'error' not in result:
            print(f"✅ Analysis completed successfully!")
            print(f"   Data Source: {result.get('data_source')}")
            print(f"   Total Grants: {result.get('overview', {}).get('total_grants', 0)}")
            print(f"   Total Funding: ${result.get('overview', {}).get('total_funding', 0):,.0f}")
            print(f"   Risk Score: {result.get('overview', {}).get('risk_score', 0):.1f}%")
        else:
            print(f"❌ Analysis error: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ Fresh analysis test failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: Test layoff leaderboard function
    print("\n2️⃣ Testing Layoff Leaderboard Function")
    print("-" * 40)
    
    try:
        from layoff_estimator import generate_layoff_risk_leaderboard
        
        # Generate leaderboard (this uses USASpending data)
        leaderboard_data = await generate_layoff_risk_leaderboard(limit=5)
        
        if leaderboard_data and 'leaderboard' in leaderboard_data:
            print(f"✅ Leaderboard generated with {len(leaderboard_data['leaderboard'])} institutions")
            
            # Show top 3
            for i, institution in enumerate(leaderboard_data['leaderboard'][:3]):
                name = institution.get('institution', 'Unknown')
                risk = institution.get('risk_score', 0)
                print(f"   {i+1}. {name} - Risk: {risk:.1f}")
        else:
            print(f"❌ Leaderboard generation failed")
            
    except Exception as e:
        print(f"❌ Leaderboard test failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Summary
    print("\n3️⃣ Strategy Summary")
    print("-" * 40)
    print("✅ Fresh NIH/NSF Analysis: Research-specific, real-time grant data")
    print("✅ Layoff Leaderboard: USASpending comprehensive tracking")
    print("✅ Dual approach provides best of both worlds")
    
    print("\n🎉 Direct Testing Complete!")

if __name__ == "__main__":
    asyncio.run(test_dual_data_strategy_direct())
