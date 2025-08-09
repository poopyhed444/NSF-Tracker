import requests
import json

def test_university_nebraska():
    print('=== University of Nebraska - Cash Flow & Delayed Funding Analysis ===')
    print()
    
    try:
        response = requests.get('http://localhost:8000/api/delayed-funding/University of Nebraska')
        response.raise_for_status()
        data = response.json()
        
        # Check if we have the main fields
        if 'cancelled_grants_impact' in data:
            cgi = data['cancelled_grants_impact']
            print('🚫 CANCELLED GRANTS IMPACT:')
            print(f'  Total Lost Funding: ${cgi.get("total_lost_funding", 0):,.2f}')
            print(f'  PIs Impacted: {cgi.get("pis_impacted", 0)}')
            
            # Show top PIs
            if cgi.get('top_pis') and len(cgi['top_pis']) > 0:
                print('  Top Impacted PIs:')
                for pi in cgi['top_pis'][:3]:
                    print(f'    - {pi["pi_name"]} ({pi["department"]}) - ${pi["lost_funding"]:,.2f}')
            
            # Show department losses
            if cgi.get('department_losses') and len(cgi['department_losses']) > 0:
                print('  Department Losses:')
                for dept, amount in list(cgi['department_losses'].items())[:3]:
                    print(f'    - {dept}: ${amount:,.2f}')
        else:
            print('❌ No cancelled_grants_impact found')

        print()

        if 'nonrenewal_grants_impact' in data:
            ngi = data['nonrenewal_grants_impact']
            print('📉 NON-RENEWAL GRANTS IMPACT:')
            print(f'  Total Lost Funding: ${ngi.get("total_lost_funding", 0):,.2f}')
            print(f'  PIs Affected: {ngi.get("pis_impacted", 0)}')
            
            # Show analysis period
            if ngi.get('analysis_period'):
                print(f'  Analysis Period: {ngi["analysis_period"]}')
            
            # Show top PIs if any
            if ngi.get('top_pis') and len(ngi['top_pis']) > 0:
                print('  Most Affected PIs:')
                for pi in ngi['top_pis'][:3]:
                    print(f'    - {pi["pi_name"]} ({pi["department"]}) - ${pi["lost_funding"]:,.2f}')
            
            # Show department losses if any
            if ngi.get('department_losses') and len(ngi['department_losses']) > 0:
                print('  Department Losses:')
                for dept, amount in list(ngi['department_losses'].items())[:3]:
                    print(f'    - {dept}: ${amount:,.2f}')
            else:
                print('  ✅ No non-renewal issues detected')
        else:
            print('❌ No nonrenewal_grants_impact found')

        print()
        print('=== Additional Analysis Fields ===')
        if 'cash_flow_risk' in data:
            risk = data['cash_flow_risk']
            print(f'Cash Flow Risk Score: {risk.get("score", 0)}/100')
            print(f'Risk Level: {risk.get("level", "Unknown")}')

        print(f'Total fields in response: {len(data)}')
        
        return True
        
    except requests.exceptions.ConnectionError:
        print('❌ Could not connect to backend server. Is it running on port 8000?')
        return False
    except Exception as e:
        print(f'❌ Error: {e}')
        return False

if __name__ == "__main__":
    test_university_nebraska()
