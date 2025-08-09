import asyncio
import sys
sys.path.append('.')
from enhanced_main import get_comprehensive_delayed_funding_analysis

async def test():
    result = await get_comprehensive_delayed_funding_analysis('University of California, San Diego')
    print('Keys in result:', list(result.keys()))
    if 'cancelled_grants_impact' in result:
        print('✅ cancelled_grants_impact present')
        cgi = result['cancelled_grants_impact']
        print(f'  Total lost: ${cgi.get("total_lost_funding", 0):,.2f}')
        print(f'  PIs impacted: {cgi.get("pis_impacted", 0)}')
    else:
        print('❌ cancelled_grants_impact missing')
    
    if 'nonrenewal_grants_impact' in result:
        print('✅ nonrenewal_grants_impact present')
        ngi = result['nonrenewal_grants_impact']
        print(f'  Total lost: ${ngi.get("total_lost_funding", 0):,.2f}')
        print(f'  PIs impacted: {ngi.get("pis_impacted", 0)}')
    else:
        print('❌ nonrenewal_grants_impact missing')
    
    return result

if __name__ == "__main__":
    result = asyncio.run(test())
    print(f"\nResult has {len(result)} total fields")
