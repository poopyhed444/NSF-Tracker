import asyncio
import sys
sys.path.append('.')
from enhanced_main import get_comprehensive_delayed_funding_analysis

async def test():
    print("Testing enhanced delayed funding analysis with non-renewal grants...")
    result = await get_comprehensive_delayed_funding_analysis('University of California, San Diego')
    
    print('\nFields present:')
    if 'cancelled_grants_impact' in result:
        print('  ✅ cancelled_grants_impact')
    else:
        print('  ❌ cancelled_grants_impact MISSING')
    
    if 'nonrenewal_grants_impact' in result:
        print('  ✅ nonrenewal_grants_impact') 
    else:
        print('  ❌ nonrenewal_grants_impact MISSING')
    
    print('\nSample data:')
    if 'cancelled_grants_impact' in result:
        cgi = result['cancelled_grants_impact']
        print(f'  Cancelled total lost: ${cgi.get("total_lost_funding", 0):,.2f}')
        print(f'  Cancelled PIs impacted: {cgi.get("pis_impacted", 0)}')
        print(f'  Cancelled methodology: {cgi.get("methodology_note", "N/A")}')
    
    if 'nonrenewal_grants_impact' in result:
        ngi = result['nonrenewal_grants_impact']
        print(f'  Non-renewal total lost: ${ngi.get("total_lost_funding", 0):,.2f}')
        print(f'  Non-renewal PIs impacted: {ngi.get("pis_impacted", 0)}')
        print(f'  Non-renewal methodology: {ngi.get("methodology_note", "N/A")}')
        if 'analysis_period' in ngi:
            print(f'  Analysis period: {ngi["analysis_period"]}')
    
    # Check if risk scoring was updated
    if 'cash_flow_risk' in result:
        risk = result['cash_flow_risk']
        print(f'\nRisk scoring:')
        print(f'  Score: {risk.get("score", 0)}/100')
        print(f'  Risk factors: {len(risk.get("risk_factors", []))} factors')
        for factor in risk.get("risk_factors", []):
            if 'cancellation' in factor.lower() or 'renewal' in factor.lower():
                print(f'    - {factor}')

if __name__ == "__main__":
    asyncio.run(test())
