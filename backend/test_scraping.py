#!/usr/bin/env python3

import asyncio
import sys
import os

# Add the current directory to the path so we can import enhanced_main
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_scraping():
    """Test the scraping functionality"""
    from enhanced_main import scrape_all_grants_and_filter, validate_grant_institution_match
    
    print("🧪 Testing bulk scraping for Stanford University...")
    
    # Test the scraping function
    try:
        grants = await scrape_all_grants_and_filter("Stanford University", max_grants=1000)
        print(f"✅ Found {len(grants)} grants for Stanford University")
        
        # Show a few examples
        for i, grant in enumerate(grants[:3]):
            org = grant.get('organization', {})
            org_name = org.get('org_name', 'Unknown') if isinstance(org, dict) else str(org)
            pi_name = grant.get('contact_pi_name', 'Unknown')
            title = grant.get('project_title', 'No title')[:50]
            amount = grant.get('award_amount', 0)
            
            print(f"{i+1}. {pi_name}")
            print(f"   Org: {org_name}")
            print(f"   Title: {title}...")
            print(f"   Amount: ${amount:,.0f}")
            print()
            
        return grants
        
    except Exception as e:
        print(f"❌ Error during scraping test: {e}")
        return []

if __name__ == "__main__":
    # Run the test
    grants = asyncio.run(test_scraping())
    print(f"📊 Total grants found: {len(grants)}")
