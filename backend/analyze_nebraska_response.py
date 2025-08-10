import json

# Load the API response
with open('nebraska_response.json', 'r') as f:
    data = json.load(f)

print('=== University of Nebraska - API Response Analysis ===')
print()

# Check financial overview
if 'financial_overview' in data:
    fo = data['financial_overview']
    print('FINANCIAL OVERVIEW:')
    print(f'  total_awarded: ${fo.get("total_awarded", 0):,.2f}')
    print(f'  total_obligated: ${fo.get("total_obligated", 0):,.2f}')  
    print(f'  total_disbursed: ${fo.get("total_disbursed", 0):,.2f}')
    print(f'  undisbursed_amount: ${fo.get("undisbursed_amount", 0):,.2f}')
    print()

# Check cash flow risk
if 'cash_flow_risk' in data:
    cfr = data['cash_flow_risk']
    print('CASH FLOW RISK:')
    print(f'  score: {cfr.get("score", 0)}')
    print(f'  level: {cfr.get("level", "Unknown")}')
    print()

# Check institution
print('INSTITUTION CHECK:')
print(f'  institution: {data.get("institution", "Not specified")}')
print()

# Check if cancelled/nonrenewal grants impact exists
if 'cancelled_grants_impact' in data:
    print(f'CANCELLED GRANTS IMPACT: ${data["cancelled_grants_impact"]:,.2f}')
if 'nonrenewal_grants_impact' in data:
    print(f'NON-RENEWAL GRANTS IMPACT: ${data["nonrenewal_grants_impact"]:,.2f}')
print()

# Look for any large numbers that might explain the 530M
print('LARGE NUMBERS IN RESPONSE (>100M):')
def find_large_numbers(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_path = f"{path}.{k}" if path else k
            find_large_numbers(v, new_path)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            new_path = f"{path}[{i}]"
            find_large_numbers(v, new_path)
    elif isinstance(obj, (int, float)):
        if obj > 100000000:  # > 100M
            print(f'  {path}: ${obj:,.2f}')

find_large_numbers(data)

# Check the total size of response
print('\n=== RESPONSE SUMMARY ===')
print(f'Total response keys: {len(data)}')
print(f'Available keys: {list(data.keys())}')

# Look specifically for the exact amount mentioned (530,863,516)
target_amount = 530863516
print(f'\nSearching for specific amount ${target_amount:,}:')
def search_for_amount(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_path = f"{path}.{k}" if path else k
            search_for_amount(v, new_path)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            new_path = f"{path}[{i}]"
            search_for_amount(v, new_path)
    elif isinstance(obj, (int, float)):
        if abs(obj - target_amount) < 1000:  # Within $1000 of target
            print(f'  FOUND: {path}: ${obj:,.2f}')

search_for_amount(data)
