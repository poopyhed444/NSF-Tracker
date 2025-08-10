import json

# Load the response
with open('nebraska_response.json', 'r') as f:
    data = json.load(f)

print('=== NEBRASKA ISSUE ANALYSIS ===')
print()

# Focus on financial overview
fo = data.get('financial_overview', {})
print('FINANCIAL OVERVIEW:')
print(f'  Total Awarded: ${fo.get("total_awarded", 0):,.2f}')
print(f'  Total Obligated: ${fo.get("total_obligated", 0):,.2f}')  
print(f'  Total Disbursed: ${fo.get("total_disbursed", 0):,.2f}')
print(f'  Undisbursed Amount: ${fo.get("undisbursed_amount", 0):,.2f}')

# The undisbursed calculation is: total_awarded - total_disbursed
# So: $965,206,392.78 - $0.00 = $965,206,392.78
# But the API shows $530,863,516.03

print()
print('CALCULATION CHECK:')
total_awarded = fo.get("total_awarded", 0)
total_disbursed = fo.get("total_disbursed", 0)
expected_undisbursed = total_awarded - total_disbursed
actual_undisbursed = fo.get("undisbursed_amount", 0)

print(f'Expected undisbursed (awarded - disbursed): ${expected_undisbursed:,.2f}')
print(f'Actual undisbursed from API: ${actual_undisbursed:,.2f}')
print(f'Difference: ${expected_undisbursed - actual_undisbursed:,.2f}')

# Check if the cash flow analysis has grants
if 'cash_flow_analysis' in data:
    cfa = data['cash_flow_analysis']
    grants = cfa.get('grants', [])
    print(f'\nGrants in cash flow analysis: {len(grants)}')
    
    if grants:
        print('\nFirst few grants:')
        for i, grant in enumerate(grants[:5]):
            award_amount = grant.get('total_award_amount', 0)
            print(f'  {i+1}. {grant.get("award_number", "N/A")}: ${award_amount:,.2f}')
            
        # Calculate total from grants
        total_from_grants = sum(grant.get('total_award_amount', 0) for grant in grants)
        print(f'\nTotal from all grants: ${total_from_grants:,.2f}')

# Print all response keys to see what else is available
print(f'\nAll response keys: {list(data.keys())}')
