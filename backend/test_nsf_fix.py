import asyncio
import sys
sys.path.append('.')
from enhanced_main import get_comprehensive_delayed_funding_analysis

async def test():
    print("Testing enhanced delayed funding analysis with force refresh to test NSF PI lookup fix...")
    result = await get_comprehensive_delayed_funding_analysis(
        'University of California, San Diego', 
        force_refresh=True  # Force refresh to test NSF API fix
    )
    
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
    
    if 'nonrenewal_grants_impact' in result:
        ngi = result['nonrenewal_grants_impact']
        print(f'  Non-renewal total lost: ${ngi.get("total_lost_funding", 0):,.2f}')
        print(f'  Non-renewal PIs impacted: {ngi.get("pis_impacted", 0)}')

if __name__ == "__main__":
    asyncio.run(test())
