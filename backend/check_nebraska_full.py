import json

with open('nebraska_response.json', 'r') as f:
    data = json.load(f)

print('=== UNIVERSITY OF NEBRASKA API RESPONSE ===')
print(f'Institution: {data.get("institution", "N/A")}')
print()

print('FINANCIAL OVERVIEW:')
fo = data.get('financial_overview', {})
print(f'  total_awarded: ${fo.get("total_awarded", 0):,.2f}')
print(f'  total_obligated: ${fo.get("total_obligated", 0):,.2f}')
print(f'  total_disbursed: ${fo.get("total_disbursed", 0):,.2f}')
print(f'  undisbursed_amount: ${fo.get("undisbursed_amount", 0):,.2f}')
print()

# Check the cash flow analysis section  
if 'cash_flow_analysis' in data:
    cfa = data['cash_flow_analysis']
    print('CASH FLOW ANALYSIS:')
    print(f'  Total grants: {len(cfa.get("grants", []))}')
    if cfa.get('grants'):
        print('  Sample grants:')
        for i, grant in enumerate(cfa['grants'][:3]):
            print(f'    Grant {i+1}: {grant.get("award_number", "N/A")} - ${grant.get("total_award_amount", 0):,.2f}')
print()

# Check cancelled/nonrenewal impact
print('IMPACT ANALYSIS:')
if 'cancelled_grants_impact' in data:
    print(f'  Cancelled grants impact: ${data["cancelled_grants_impact"]:,.2f}')
if 'nonrenewal_grants_impact' in data:  
    print(f'  Non-renewal grants impact: ${data["nonrenewal_grants_impact"]:,.2f}')

print()
print('=== ALL TOP-LEVEL KEYS ===')
for key in data.keys():
    print(f'  {key}')
