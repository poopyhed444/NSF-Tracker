import json

# Compare what the backend returns vs what frontend expects
print("=== FRONTEND DATA COMPATIBILITY CHECK ===")

with open('comprehensive_nebraska_response.json', 'r') as f:
    backend_data = json.load(f)

print("BACKEND RESPONSE STRUCTURE:")
print(f"  Top-level keys: {list(backend_data.keys())}")

# Check if the data structure matches what frontend expects
# Frontend expects: institutionDetails.delayed_funding.cancelled_grants_impact

print("\nFRONTEND EXPECTED PATH:")
print("  institutionDetails.delayed_funding.cancelled_grants_impact")

# Check if this path exists in backend response
if 'cancelled_grants_impact' in backend_data:
    print("  ✅ cancelled_grants_impact exists at root level")
    cgi = backend_data['cancelled_grants_impact']
    print(f"     - total_lost_funding: ${cgi.get('total_lost_funding', 0):,.2f}")
    print(f"     - pis_impacted: {cgi.get('pis_impacted', 0)}")
    print(f"     - top_pis: {len(cgi.get('top_pis', []))} PIs")
    print(f"     - department_losses: {len(cgi.get('department_losses', {}))} departments")
else:
    print("  ❌ cancelled_grants_impact NOT found at root level")

# Check if it might be nested differently
print("\nLOOKING FOR NESTED STRUCTURE...")
for key, value in backend_data.items():
    if isinstance(value, dict) and 'cancelled_grants_impact' in value:
        print(f"  Found cancelled_grants_impact in: {key}")

print("\n=== POTENTIAL FRONTEND ISSUE ===")
print("The frontend expects the data structure:")
print("  institutionDetails.delayed_funding.cancelled_grants_impact")
print("\nBut the backend returns:")
print("  result.cancelled_grants_impact")
print("\nThe frontend might need to access it as:")
print("  institutionDetails.cancelled_grants_impact")
print("  (without the .delayed_funding part)")

# Check what's in delayed_funding if it exists
if 'delayed_funding' in backend_data:
    print(f"\nBACKEND HAS 'delayed_funding' KEY with: {list(backend_data['delayed_funding'].keys())}")
else:
    print("\nBACKEND DOES NOT HAVE 'delayed_funding' KEY")
    print("This could explain why frontend doesn't show the cancelled grants section!")
