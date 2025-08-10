import json

with open('comprehensive_nebraska_response.json', 'r') as f:
    data = json.load(f)

print('=== CHECKING PI AND DEPARTMENT DATA STRUCTURE ===')

# Check cancelled grants structure
if 'cancelled_grants_impact' in data:
    cgi = data['cancelled_grants_impact']
    print('CANCELLED GRANTS IMPACT STRUCTURE:')
    for key, value in cgi.items():
        if key == 'top_pis' and isinstance(value, list):
            print(f'  {key}: [{len(value)} PIs]')
            for i, pi in enumerate(value[:2]):
                print(f'    PI {i+1}: {pi}')
        elif key == 'department_losses' and isinstance(value, dict):
            print(f'  {key}: {len(value)} departments')
            for dept, loss in list(value.items())[:2]:
                print(f'    {dept}: ${loss:,.2f}')
        else:
            print(f'  {key}: {value}')

print()
# Check nonrenewal grants structure  
if 'nonrenewal_grants_impact' in data:
    ngi = data['nonrenewal_grants_impact']
    print('NON-RENEWAL GRANTS IMPACT STRUCTURE:')
    for key, value in ngi.items():
        print(f'  {key}: {value}')
        
print()
print('=== FRONTEND DISPLAY EXPECTATIONS ===')
print('Frontend expects:')
print('  - cancelled_grants_impact.top_pis (array)')
print('  - cancelled_grants_impact.department_losses (object)')
print('  - nonrenewal_grants_impact.top_pis (array)') 
print('  - nonrenewal_grants_impact.department_losses (object)')

# Check if the data structure matches frontend expectations
cgi = data.get('cancelled_grants_impact', {})
ngi = data.get('nonrenewal_grants_impact', {})

print()
print('=== DATA AVAILABILITY CHECK ===')
print(f'Cancelled grants - top_pis available: {bool(cgi.get("top_pis"))}')
print(f'Cancelled grants - department_losses available: {bool(cgi.get("department_losses"))}')
print(f'Non-renewal grants - top_pis available: {bool(ngi.get("top_pis"))}')
print(f'Non-renewal grants - department_losses available: {bool(ngi.get("department_losses"))}')
