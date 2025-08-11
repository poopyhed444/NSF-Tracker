#!/usr/bin/env python3
"""
Standalone CSV generation script for enhanced delayed funding analysis.
"""

import asyncio
import sys
import os
import argparse
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_main import get_comprehensive_delayed_funding_analysis, convert_enhanced_analysis_to_csv
from datetime import datetime

async def generate_csv_report(institution_name: str, output_file: str = None):
    """
    Generate CSV report for a specific institution
    """
    try:
        print(f"🔍 Generating CSV report for: {institution_name}")
        
        # Get the analysis data
        analysis_data = await get_comprehensive_delayed_funding_analysis(
            institution_name, 
            include_departments=True, 
            method="comprehensive"
        )
        
        if 'error' in analysis_data:
            print(f"❌ Error: {analysis_data['error']}")
            return
        
        # Convert to CSV
        csv_content = convert_enhanced_analysis_to_csv(analysis_data, institution_name)
        
        # Generate filename if not provided
        if not output_file:
            safe_institution_name = "".join(c for c in institution_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            output_file = f"enhanced_funding_analysis_{safe_institution_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(csv_content)
        
        print(f"✅ CSV report generated: {output_file}")
        print(f"📊 File size: {len(csv_content):,} characters")
        
    except Exception as e:
        print(f"❌ Error generating CSV report: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate CSV report for university delayed funding analysis')
    parser.add_argument('institution', help='Institution name (e.g., "Harvard University")')
    parser.add_argument('-o', '--output', help='Output filename (optional)')
    
    args = parser.parse_args()
    
    asyncio.run(generate_csv_report(args.institution, args.output))
