#!/usr/bin/env python3
"""
Test NSF API to see if we can find any terminated grants with different criteria
"""

import asyncio
import httpx
from datetime import datetime, timedelta

async def test_nsf_terminated_criteria():
    """Test different criteria for finding terminated NSF grants"""
    
    nsf_url = "https://www.research.gov/awardapi-service/v1/awards.json"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            # Search for NSF grants from various universities that ended recently
            nsf_params = {
                'printFields': 'id,title,startDate,expDate,awardeeName,fundsObligatedAmt,pdPIName',
                'rpp': '100',
                'offset': '1',
                'awardeeName': 'University'  # Broad search for universities
            }
            
            response = await client.get(nsf_url, params=nsf_params)
            response.raise_for_status()
            data = response.json()
            
            nsf_awards = data.get('response', {}).get('award', [])
            print(f"Found {len(nsf_awards)} NSF awards to analyze")
            
            terminated_count = 0
            normal_count = 0
            
            for award in nsf_awards:
                exp_date_str = award.get('expDate', '')
                start_date_str = award.get('startDate', '')
                
                if exp_date_str and start_date_str:
                    try:
                        exp_date_obj = datetime.strptime(exp_date_str[:10], '%Y-%m-%d')
                        start_date_obj = datetime.strptime(start_date_str[:10], '%Y-%m-%d')
                        
                        # Calculate grant duration in months
                        duration_months = (exp_date_obj - start_date_obj).days / 30.44
                        
                        # Check if it ended in the last year
                        if start_date <= exp_date_obj <= end_date:
                            if duration_months < 18:
                                terminated_count += 1
                                print(f"  POTENTIAL TERMINATED: {award.get('title', '')[:50]}...")
                                print(f"    Duration: {duration_months:.1f} months")
                                print(f"    Institution: {award.get('awardeeName', '')}")
                                print(f"    Amount: ${award.get('fundsObligatedAmt', 0):,}")
                                print()
                            else:
                                normal_count += 1
                    except ValueError:
                        continue
            
            print(f"Summary:")
            print(f"  Potentially terminated (< 18 months): {terminated_count}")
            print(f"  Normal duration grants: {normal_count}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_nsf_terminated_criteria())
