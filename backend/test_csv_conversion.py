#!/usr/bin/env python3
"""
Test CSV conversion function in isolation
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_main import convert_enhanced_analysis_to_csv
import json

# Test data
test_data = {
    'summary': {
        'total_undisbursed': 1234567.89,
        'disbursement_efficiency': '85.5%',
        'delayed_funding_risk': 3,
        'cash_flow_risk': {
            'level': 'Medium',
            'score': 75
        }
    },
    'grants_with_undisbursed': [
        {
            'award_id': 'TEST123',
            'title': 'Test Grant Title',
            'pi_name': 'Dr. Test PI',
            'funding_agency': 'NSF',
            'total_award_amount': 500000,
            'undisbursed_amount': 150000,
            'award_start_date': '2023-01-01',
            'award_end_date': '2025-12-31'
        }
    ]
}

try:
    print("Testing CSV conversion...")
    csv_result = convert_enhanced_analysis_to_csv(test_data, "Test University")
    print("CSV conversion successful!")
    print("\nFirst 500 characters of CSV:")
    print(csv_result[:500])
    print("\n...CSV continues...")
    
except Exception as e:
    print(f"Error in CSV conversion: {e}")
    import traceback
    traceback.print_exc()
