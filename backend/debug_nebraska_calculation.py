import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from delayed_funding_tracker import analyze_delayed_funding_for_institution

async def debug_nebraska_calculation():
    print("=== DEBUGGING NEBRASKA CALCULATION ===")
    
    institution = "University of Nebraska"
    result = await analyze_delayed_funding_for_institution(institution)
    
    if result and not result.get('error'):
        analysis = result['disbursement_analysis']
        
        print("KEY VALUES:")
        print(f"  total_awarded_amount: ${analysis.get('total_awarded_amount', 0):,.2f}")
        print(f"  total_outlayed_amount: ${analysis.get('total_outlayed_amount', 0):,.2f}")
        print(f"  undisbursed_amount: ${analysis.get('undisbursed_amount', 0):,.2f}")
        print(f"  delayed_awards_count: {analysis.get('delayed_awards_count', 0)}")
        print(f"  total_awards: {analysis.get('total_awards', 0)}")
        print(f"  disbursement_efficiency: {analysis.get('disbursement_efficiency', 0)*100:.2f}%")
        print(f"  methodology_note: {analysis.get('methodology_note', 'N/A')}")
        print()
        
        # Calculate what the non_delayed_rate would be
        delayed_awards_count = analysis.get('delayed_awards_count', 0)
        total_awards = analysis.get('total_awards', 0)
        
        if total_awards > 0:
            non_delayed_rate = max(0, 1 - (delayed_awards_count / total_awards))
            print("CALCULATION BREAKDOWN:")
            print(f"  delayed_awards_count: {delayed_awards_count}")
            print(f"  total_awards: {total_awards}")
            print(f"  delay_rate: {delayed_awards_count / total_awards if total_awards > 0 else 0:.4f}")
            print(f"  non_delayed_rate: {non_delayed_rate:.4f}")
            print()
            
            # Times-style calculation
            times_undisbursed = analysis.get('total_awarded_amount', 0) * (1 - non_delayed_rate)
            # Traditional calculation  
            traditional_undisbursed = analysis.get('total_awarded_amount', 0) - analysis.get('total_outlayed_amount', 0)
            
            print("CALCULATION METHODS:")
            print(f"  Times-style undisbursed: ${times_undisbursed:,.2f}")
            print(f"  Traditional undisbursed: ${traditional_undisbursed:,.2f}")
            print(f"  Actual reported: ${analysis.get('undisbursed_amount', 0):,.2f}")
            print()
            
            print("WHICH METHOD IS BEING USED?")
            if abs(times_undisbursed - analysis.get('undisbursed_amount', 0)) < 1:
                print("  ✓ Using Times-style calculation")
                print(f"  Formula: ${analysis.get('total_awarded_amount', 0):,.2f} * (1 - {non_delayed_rate:.4f}) = ${times_undisbursed:,.2f}")
            elif abs(traditional_undisbursed - analysis.get('undisbursed_amount', 0)) < 1:
                print("  ✓ Using Traditional calculation")
            else:
                print("  ❌ Unknown calculation method")

# Run the analysis
asyncio.run(debug_nebraska_calculation())
