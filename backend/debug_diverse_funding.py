#!/usr/bin/env python3

import asyncio
import json
from layoff_estimator import generate_layoff_risk_leaderboard

async def find_diverse_institutions():
    result = await generate_layoff_risk_leaderboard(limit=50)
    institutions = result.get('data', [])
    
    print('Looking for institutions with diverse funding sources...')
    diverse_count = 0
    nsf_count = 0
    doe_count = 0
    dod_count = 0
    
    for inst in institutions:
        funding = inst.get('funding_diversification', {})
        agencies = funding.get('agencies_with_funding', 0)
        
        if funding.get('nsf_percentage', 0) > 0:
            nsf_count += 1
            print(f'NSF Institution: {inst["institution"]} - NSF: {funding.get("nsf_percentage", 0)}%')
            
        if funding.get('doe_percentage', 0) > 0:
            doe_count += 1
            print(f'DOE Institution: {inst["institution"]} - DOE: {funding.get("doe_percentage", 0)}%')
            
        if funding.get('dod_percentage', 0) > 0:
            dod_count += 1
            print(f'DOD Institution: {inst["institution"]} - DOD: {funding.get("dod_percentage", 0)}%')
            
        if agencies > 1:
            diverse_count += 1
            print(f'Multi-Agency: {inst["institution"]} - {agencies} agencies')
    
    print(f'\nSummary:')
    print(f'Total institutions analyzed: {len(institutions)}')
    print(f'Institutions with NSF funding: {nsf_count}')
    print(f'Institutions with DOE funding: {doe_count}')
    print(f'Institutions with DOD funding: {dod_count}')
    print(f'Institutions with multiple agencies: {diverse_count}')

if __name__ == "__main__":
    asyncio.run(find_diverse_institutions())
