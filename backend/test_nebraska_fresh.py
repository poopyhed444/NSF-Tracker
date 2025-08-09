import asyncio
from enhanced_main import get_comprehensive_delayed_funding_analysis

async def test():
    result = await get_comprehensive_delayed_funding_analysis('University of Nebraska', force_refresh=True)
    
    print('=== Fresh API Call (force refresh) ===')
    print(f'Total fields: {len(result)}')
    
    if 'cancelled_grants_impact' in result:
        cgi = result['cancelled_grants_impact']
        print()
        print('CANCELLED GRANTS IMPACT:')
        print(f'  total_lost_funding: {cgi.get("total_lost_funding")}')
        print(f'  pis_impacted: {cgi.get("pis_impacted")}')
        print(f'  Data type of total_lost_funding: {type(cgi.get("total_lost_funding"))}')
        
        if cgi.get('top_pis'):
            print(f'  Number of top_pis: {len(cgi["top_pis"])}')
            for i, pi in enumerate(cgi['top_pis'][:2]):
                print(f'    PI {i+1}: {pi}')
    else:
        print('❌ No cancelled_grants_impact field')
    
    if 'nonrenewal_grants_impact' in result:
        ngi = result['nonrenewal_grants_impact']
        print()
        print('NON-RENEWAL GRANTS IMPACT:')
        print(f'  total_lost_funding: {ngi.get("total_lost_funding")}')
        print(f'  pis_impacted: {ngi.get("pis_impacted")}')
        print(f'  Data type of total_lost_funding: {type(ngi.get("total_lost_funding"))}')
    else:
        print('❌ No nonrenewal_grants_impact field')

    return result

if __name__ == "__main__":
    result = asyncio.run(test())
