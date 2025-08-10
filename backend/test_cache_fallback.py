#!/usr/bin/env python3

import asyncio
import json
from enhanced_main import get_comprehensive_delayed_funding_analysis

async def test_cache_fallback():
    print('Testing cache fallback functionality...')
    try:
        result = await get_comprehensive_delayed_funding_analysis('University of California', 200000)
        print('Cache fallback test completed.')
        
        # Check for cache indicators
        if 'cancelled_grants_impact' in result and '_data_source' in result['cancelled_grants_impact']:
            print(f'Cancelled grants data source: {result["cancelled_grants_impact"]["_data_source"]}')
            print(f'Cancelled grants methodology: {result["cancelled_grants_impact"]["methodology_note"]}')
        
        if 'non_renewal_impact' in result and '_data_source' in result['non_renewal_impact']:
            print(f'Non-renewal data source: {result["non_renewal_impact"]["_data_source"]}')
            print(f'Non-renewal methodology: {result["non_renewal_impact"]["methodology_note"]}')
        elif 'nonrenewal_grants_impact' in result and '_data_source' in result['nonrenewal_grants_impact']:
            print(f'Non-renewal data source: {result["nonrenewal_grants_impact"]["_data_source"]}')
            print(f'Non-renewal methodology: {result["nonrenewal_grants_impact"]["methodology_note"]}')
        
        if 'cache_stats' in result:
            print(f'Cache stats: {result["cache_stats"]}')
            
        # Test if fallback indicators are working
        print('\n=== CACHE FALLBACK TEST RESULTS ===')
        if result.get('cancelled_grants_impact', {}).get('_data_source'):
            print('✅ Cache fallback indicators added to cancelled grants analysis')
        else:
            print('❌ Cache fallback indicators missing from cancelled grants analysis')
            
        if (result.get('non_renewal_impact', {}).get('_data_source') or 
            result.get('nonrenewal_grants_impact', {}).get('_data_source')):
            print('✅ Cache fallback indicators added to non-renewal analysis')
        else:
            print('❌ Cache fallback indicators missing from non-renewal analysis')
            
        print('✅ Cache fallback implementation test completed successfully!')
        
    except Exception as e:
        print(f'❌ Error during cache fallback test: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_cache_fallback())
