import asyncio
from layoff_estimator import fetch_terminated_grants, normalize_institution_name

async def check_nebraska_data():
    print('=== Checking Cancelled Grants Data for Nebraska Institutions ===')
    terminated_grants = await fetch_terminated_grants()
    
    print(f'Total terminated grants: {len(terminated_grants)}')
    print()
    
    # Find all Nebraska-related institutions
    nebraska_institutions = []
    nebraska_grants = []
    
    for grant in terminated_grants:
        org_info = grant.get('organization', {})
        if isinstance(org_info, list) and org_info:
            org_name = org_info[0].get('org_name','')
        elif isinstance(org_info, dict):
            org_name = org_info.get('org_name','')
        else:
            continue
            
        if 'nebraska' in org_name.lower():
            normalized = normalize_institution_name(org_name)
            nebraska_institutions.append((org_name, normalized))
            nebraska_grants.append(grant)
    
    # Remove duplicates and show unique institutions
    unique_institutions = list(set(nebraska_institutions))
    
    print(f'Nebraska institutions found in cancelled grants data: {len(unique_institutions)}')
    for original, normalized in sorted(unique_institutions):
        print(f'  Original: "{original}"')
        print(f'  Normalized: "{normalized}"')
        print()
    
    # Now check what 'University of Nebraska' normalizes to and if it matches any
    target_normalized = normalize_institution_name('University of Nebraska')
    print(f'Target search: "University of Nebraska" -> "{target_normalized}"')
    
    matches = [norm for orig, norm in unique_institutions if norm == target_normalized]
    if matches:
        print(f'✅ Found {len(matches)} matches!')
        
        # Show some sample grants for this institution
        matching_grants = []
        for grant in nebraska_grants:
            org_info = grant.get('organization', {})
            if isinstance(org_info, list) and org_info:
                org_name = org_info[0].get('org_name','')
            elif isinstance(org_info, dict):
                org_name = org_info.get('org_name','')
            else:
                continue
            
            if normalize_institution_name(org_name) == target_normalized:
                matching_grants.append(grant)
        
        print(f'Found {len(matching_grants)} cancelled grants for this institution')
        if matching_grants:
            print('Sample grants:')
            for grant in matching_grants[:3]:
                amount = grant.get('award_amount', 0)
                pi_name = grant.get('contact_pi_name', 'Unknown PI')
                award_id = grant.get('core_project_num', 'Unknown ID')
                print(f'  - {award_id}: {pi_name} - ${amount:,.2f}')
                
    else:
        print('❌ No matches found - this explains why no data is returned')
        print('Available normalized Nebraska names:')
        for orig, norm in sorted(unique_institutions):
            print(f'  - "{norm}"')

if __name__ == "__main__":
    asyncio.run(check_nebraska_data())
