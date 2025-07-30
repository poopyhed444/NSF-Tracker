#!/usr/bin/env python3

import asyncio
import json
from federal_agency_integrator import FederalAgencyIntegrator

async def test_recipient_analysis():
    """Test the enhanced recipient analysis functionality"""
    
    print("="*60)
    print("TESTING ENHANCED RECIPIENT ANALYSIS")
    print("="*60)
    
    integrator = FederalAgencyIntegrator()
    
    # Test DoD analysis
    print("\n--- TESTING DOD RECIPIENT ANALYSIS ---")
    try:
        dod_data = await integrator.get_comprehensive_federal_data(
            agencies=['DOD'],
            include_opportunities=False,
            include_awards=True
        )
        
        if 'recipient_analysis' in dod_data:
            analysis = dod_data['recipient_analysis']
            
            print(f"\nDoD Awards Summary:")
            print(f"  Total Awards: {analysis['summary']['total_awards']}")
            print(f"  Total Recipients: {analysis['summary']['total_recipients']}")
            print(f"  Total Amount: ${analysis['summary']['total_amount']:,.2f}")
            
            print(f"\nRecipient Categories:")
            for category, data in analysis['summary']['categories'].items():
                print(f"  {category.title()}: {data['count']} recipients, ${data['total_amount']:,.2f} ({data['percentage']:.1f}%)")
            
            print(f"\nTop 5 DoD Recipients by Amount:")
            for i, (recipient, amount) in enumerate(analysis['top_recipients']['by_amount'][:5]):
                print(f"  {i+1}. {recipient}: ${amount:,.2f}")
            
            print(f"\nTop Companies:")
            for i, company in enumerate(analysis['categories']['companies'][:3]):
                print(f"  {i+1}. {company['name']}: ${company['amount']:,.2f}")
                
        else:
            print("No recipient analysis available")
            
    except Exception as e:
        print(f"Error analyzing DoD: {e}")
    
    # Test DoE analysis  
    print("\n--- TESTING DOE RECIPIENT ANALYSIS ---")
    try:
        doe_data = await integrator.get_comprehensive_federal_data(
            agencies=['DOE'],
            include_opportunities=False,
            include_awards=True
        )
        
        if 'recipient_analysis' in doe_data:
            analysis = doe_data['recipient_analysis']
            
            print(f"\nDoE Awards Summary:")
            print(f"  Total Awards: {analysis['summary']['total_awards']}")
            print(f"  Total Recipients: {analysis['summary']['total_recipients']}")
            print(f"  Total Amount: ${analysis['summary']['total_amount']:,.2f}")
            
            print(f"\nRecipient Categories:")
            for category, data in analysis['summary']['categories'].items():
                print(f"  {category.title()}: {data['count']} recipients, ${data['total_amount']:,.2f} ({data['percentage']:.1f}%)")
            
            print(f"\nTop Universities:")
            for i, univ in enumerate(analysis['categories']['universities'][:3]):
                print(f"  {i+1}. {univ['name']}: ${univ['amount']:,.2f}")
            
            print(f"\nTop National Labs:")
            for i, lab in enumerate(analysis['categories']['national_labs'][:3]):
                print(f"  {i+1}. {lab['name']}: ${lab['amount']:,.2f}")
                
        else:
            print("No recipient analysis available")
            
    except Exception as e:
        print(f"Error analyzing DoE: {e}")

async def test_multi_agency_analysis():
    """Test analysis across multiple agencies"""
    
    print("\n" + "="*60)
    print("MULTI-AGENCY RECIPIENT ANALYSIS")
    print("="*60)
    
    integrator = FederalAgencyIntegrator()
    
    try:
        data = await integrator.get_comprehensive_federal_data(
            agencies=['DOD', 'DOE', 'NASA'],
            include_opportunities=False,
            include_awards=True
        )
        
        if 'recipient_analysis' in data:
            analysis = data['recipient_analysis']
            
            print(f"\nMulti-Agency Summary:")
            print(f"  Total Awards: {analysis['summary']['total_awards']}")
            print(f"  Total Recipients: {analysis['summary']['total_recipients']}")
            print(f"  Total Amount: ${analysis['summary']['total_amount']:,.2f}")
            
            print(f"\nBreakdown by Recipient Type:")
            for category, data in analysis['summary']['categories'].items():
                if data['count'] > 0:
                    print(f"  {category.title()}: {data['count']} recipients, ${data['total_amount']:,.2f} ({data['percentage']:.1f}%)")
            
            print(f"\nTop 10 Recipients Across All Agencies:")
            for i, (recipient, amount) in enumerate(analysis['top_recipients']['by_amount'][:10]):
                print(f"  {i+1}. {recipient}: ${amount:,.2f}")
                
        else:
            print("No recipient analysis available")
            
    except Exception as e:
        print(f"Error in multi-agency analysis: {e}")

if __name__ == "__main__":
    asyncio.run(test_recipient_analysis())
    asyncio.run(test_multi_agency_analysis())
