import asyncio
import json
from enhanced_main import get_comprehensive_delayed_funding_analysis

async def compare_analyses():
    print("=== COMPARING DIFFERENT ANALYSIS TYPES ===")
    
    institution = "University of Nebraska"
    
    # Get the comprehensive analysis (what the frontend calls)
    result = await get_comprehensive_delayed_funding_analysis(institution, force_refresh=True)
    
    print("1. MAIN DELAYED FUNDING ANALYSIS:")
    if 'financial_overview' in result:
        fo = result['financial_overview']
        print(f"   undisbursed_amount: ${fo.get('undisbursed_amount', 0):,.2f}")
        print(f"   Source: Main delayed funding calculation (Times-style)")
    
    print("\n2. CANCELLED GRANTS ANALYSIS:")
    if 'cancelled_grants_impact' in result:
        cgi = result['cancelled_grants_impact']
        print(f"   total_lost_funding: ${cgi.get('total_lost_funding', 0):,.2f}")
        print(f"   pis_impacted: {cgi.get('pis_impacted', 0)}")
        print(f"   Source: Specific cancelled grants analysis")
        
        if cgi.get('top_pis'):
            print(f"   Top PIs ({len(cgi['top_pis'])}):")
            for i, pi in enumerate(cgi['top_pis'][:3]):
                print(f"     {i+1}. {pi}")
    else:
        print("   ❌ No cancelled grants impact data")
    
    print("\n3. NON-RENEWAL GRANTS ANALYSIS:")
    if 'nonrenewal_grants_impact' in result:
        ngi = result['nonrenewal_grants_impact']
        print(f"   total_lost_funding: ${ngi.get('total_lost_funding', 0):,.2f}")
        print(f"   pis_impacted: {ngi.get('pis_impacted', 0)}")
        print(f"   Source: Specific non-renewal grants analysis")
        
        if ngi.get('top_pis'):
            print(f"   Top PIs ({len(ngi['top_pis'])}):")
            for i, pi in enumerate(ngi['top_pis'][:3]):
                print(f"     {i+1}. {pi}")
    else:
        print("   ❌ No non-renewal grants impact data")
    
    print("\n=== KEY INSIGHT ===")
    print("The $530M 'undisbursed' is from Times-style analysis of renewal delays")
    print("The $0 'non-renewal impact' is from specific terminated/non-renewed grants")
    print("These are measuring different things!")
    
    # Save full response for inspection
    with open('comprehensive_nebraska_response.json', 'w') as f:
        json.dump(result, f, indent=2, default=str)
    print("\nFull response saved to: comprehensive_nebraska_response.json")

if __name__ == "__main__":
    asyncio.run(compare_analyses())
