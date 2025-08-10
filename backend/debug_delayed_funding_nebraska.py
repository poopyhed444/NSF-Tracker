import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from delayed_funding_tracker import analyze_delayed_funding_for_institution

async def check_nebraska_delayed_funding():
    print("=== CHECKING DELAYED FUNDING ANALYSIS FOR UNIVERSITY OF NEBRASKA ===")
    
    institution = "University of Nebraska"
    result = await analyze_delayed_funding_for_institution(institution)
    
    if result and not result.get('error'):
        print(f"Institution: {result.get('institution', 'N/A')}")
        print()
        
        # Check the analysis section
        if 'disbursement_analysis' in result:
            analysis = result['disbursement_analysis']
            print("DISBURSEMENT ANALYSIS:")
            print(f"  total_awarded_amount: ${analysis.get('total_awarded_amount', 0):,.2f}")
            print(f"  total_obligated_amount: ${analysis.get('total_obligated_amount', 0):,.2f}")
            print(f"  total_outlayed_amount: ${analysis.get('total_outlayed_amount', 0):,.2f}")
            print(f"  undisbursed_amount: ${analysis.get('undisbursed_amount', 0):,.2f}")
            print(f"  disbursement_efficiency: {analysis.get('disbursement_efficiency', 0)*100:.2f}%")
            print()
            
            # Check the calculation
            total_awarded = analysis.get('total_awarded_amount', 0)
            total_outlayed = analysis.get('total_outlayed_amount', 0)
            calculated_undisbursed = total_awarded - total_outlayed
            reported_undisbursed = analysis.get('undisbursed_amount', 0)
            
            print("CALCULATION CHECK:")
            print(f"  Expected undisbursed (awarded - outlayed): ${calculated_undisbursed:,.2f}")
            print(f"  Reported undisbursed: ${reported_undisbursed:,.2f}")
            print(f"  Match: {'✓' if abs(calculated_undisbursed - reported_undisbursed) < 1 else '✗'}")
            print()
        
        # Check summary
        if 'summary' in result:
            summary = result['summary']
            print("SUMMARY:")
            print(f"  total_awards: {summary.get('total_awards', 0)}")
            print(f"  total_awarded: ${summary.get('total_awarded', 0):,.2f}")
            print(f"  total_undisbursed: ${summary.get('total_undisbursed', 0):,.2f}")
            print()
    else:
        print(f"Error or no data: {result.get('error', 'Unknown error')}")

# Run the analysis
asyncio.run(check_nebraska_delayed_funding())
