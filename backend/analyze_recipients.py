#!/usr/bin/env python3

import requests
import json
from collections import Counter, defaultdict

def analyze_award_recipients():
    """Analyze who receives federal awards from DoD and DoE"""
    
    print("Analyzing federal award recipients...")
    
    url = "https://api.usaspending.gov/api/v2/search/spending_by_award"
    
    # Get more detailed fields including recipient information
    payload = {
        "filters": {
            "award_type_codes": ["B", "C", "D"],
            "agencies": [{
                "type": "awarding",
                "tier": "toptier",
                "name": "Department of Defense"
            }]
        },
        "fields": [
            "Award ID", "Recipient Name", "Award Amount", "Awarding Agency",
            "Start Date", "End Date", "Award Description", "Award Type",
            "Prime Award Base Transaction Description", "Recipient State Code",
            "Recipient City Name", "Recipient Country Name", 
            "Primary Place of Performance City", "Primary Place of Performance State",
            "NAICS Code", "NAICS Description", "PSC Code", "PSC Description"
        ],
        "page": 1,
        "limit": 100,
        "sort": "Award Amount",
        "order": "desc"
    }
    
    try:
        print("Fetching DoD awards with detailed recipient info...")
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        awards = data.get('results', [])
        
        if not awards:
            print("No awards found")
            return
        
        print(f"\n=== ANALYSIS OF {len(awards)} DOD AWARDS ===")
        
        # Analyze recipients
        recipients = Counter()
        recipient_amounts = defaultdict(float)
        recipient_types = defaultdict(int)
        locations = Counter()
        award_types = Counter()
        naics_codes = Counter()
        
        universities = []
        companies = []
        government_entities = []
        nonprofits = []
        
        for award in awards:
            recipient = award.get('Recipient Name', 'Unknown')
            amount = award.get('Award Amount', 0) or 0
            location = f"{award.get('Recipient City Name', '')}, {award.get('Recipient State Code', '')}"
            award_type = award.get('Award Type', 'Unknown')
            naics = award.get('NAICS Description', 'Unknown')
            
            recipients[recipient] += 1
            recipient_amounts[recipient] += amount
            locations[location] += 1
            award_types[award_type] += 1
            naics_codes[naics] += 1
            
            # Categorize recipients
            recipient_lower = recipient.lower()
            if any(keyword in recipient_lower for keyword in ['university', 'college', 'institute of technology', 'school']):
                universities.append((recipient, amount))
            elif any(keyword in recipient_lower for keyword in ['inc', 'corp', 'llc', 'ltd', 'company', 'technologies', 'systems']):
                companies.append((recipient, amount))
            elif any(keyword in recipient_lower for keyword in ['government', 'department', 'agency', 'bureau', 'federal']):
                government_entities.append((recipient, amount))
            else:
                nonprofits.append((recipient, amount))
        
        # Print analysis
        print(f"\n--- TOP 10 RECIPIENTS BY NUMBER OF AWARDS ---")
        for recipient, count in recipients.most_common(10):
            total_amount = recipient_amounts[recipient]
            print(f"{recipient}: {count} awards, ${total_amount:,.2f} total")
        
        print(f"\n--- TOP 10 RECIPIENTS BY AWARD AMOUNT ---")
        sorted_by_amount = sorted(recipient_amounts.items(), key=lambda x: x[1], reverse=True)
        for recipient, amount in sorted_by_amount[:10]:
            count = recipients[recipient]
            print(f"{recipient}: ${amount:,.2f} ({count} awards)")
        
        print(f"\n--- RECIPIENT CATEGORIES ---")
        print(f"Universities: {len(universities)}")
        print(f"Companies: {len(companies)}")
        print(f"Government: {len(government_entities)}")
        print(f"Other/Nonprofits: {len(nonprofits)}")
        
        if universities:
            print(f"\n--- TOP UNIVERSITIES ---")
            universities.sort(key=lambda x: x[1], reverse=True)
            for univ, amount in universities[:5]:
                print(f"{univ}: ${amount:,.2f}")
        
        if companies:
            print(f"\n--- TOP COMPANIES ---")
            companies.sort(key=lambda x: x[1], reverse=True)
            for company, amount in companies[:5]:
                print(f"{company}: ${amount:,.2f}")
        
        print(f"\n--- TOP LOCATIONS ---")
        for location, count in locations.most_common(5):
            print(f"{location}: {count} awards")
        
        print(f"\n--- AWARD TYPES ---")
        for award_type, count in award_types.most_common():
            print(f"{award_type}: {count} awards")
        
        print(f"\n--- TOP NAICS CATEGORIES ---")
        for naics, count in naics_codes.most_common(5):
            print(f"{naics}: {count} awards")
        
        # Show sample awards with details
        print(f"\n--- SAMPLE AWARD DETAILS ---")
        for i, award in enumerate(awards[:3]):
            print(f"\nAward {i+1}:")
            print(f"  Recipient: {award.get('Recipient Name', 'N/A')}")
            print(f"  Amount: ${award.get('Award Amount', 0):,.2f}")
            print(f"  Location: {award.get('Recipient City Name', 'N/A')}, {award.get('Recipient State Code', 'N/A')}")
            print(f"  Description: {award.get('Award Description', 'N/A')[:100]}...")
            print(f"  NAICS: {award.get('NAICS Description', 'N/A')}")
            print(f"  Start: {award.get('Start Date', 'N/A')}")
            print(f"  End: {award.get('End Date', 'N/A')}")
            
    except Exception as e:
        print(f"Error: {e}")

def analyze_doe_recipients():
    """Analyze DoE recipients"""
    
    print("\n" + "="*60)
    print("ANALYZING DOE AWARD RECIPIENTS")
    print("="*60)
    
    url = "https://api.usaspending.gov/api/v2/search/spending_by_award"
    
    payload = {
        "filters": {
            "award_type_codes": ["B", "C", "D"],
            "agencies": [{
                "type": "awarding",
                "tier": "toptier",
                "name": "Department of Energy"
            }]
        },
        "fields": [
            "Award ID", "Recipient Name", "Award Amount", "Awarding Agency",
            "Award Description", "Recipient State Code", "Recipient City Name",
            "NAICS Description", "PSC Description"
        ],
        "page": 1,
        "limit": 100,
        "sort": "Award Amount",
        "order": "desc"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        awards = data.get('results', [])
        
        print(f"\n=== ANALYSIS OF {len(awards)} DOE AWARDS ===")
        
        recipients = Counter()
        recipient_amounts = defaultdict(float)
        
        universities = []
        companies = []
        national_labs = []
        
        for award in awards:
            recipient = award.get('Recipient Name', 'Unknown')
            amount = award.get('Award Amount', 0) or 0
            
            recipients[recipient] += 1
            recipient_amounts[recipient] += amount
            
            recipient_lower = recipient.lower()
            if any(keyword in recipient_lower for keyword in ['university', 'college', 'institute of technology']):
                universities.append((recipient, amount))
            elif any(keyword in recipient_lower for keyword in ['national laboratory', 'national lab', 'brookhaven', 'argonne', 'oak ridge', 'lawrence', 'sandia', 'los alamos']):
                national_labs.append((recipient, amount))
            elif any(keyword in recipient_lower for keyword in ['inc', 'corp', 'llc', 'company', 'technologies']):
                companies.append((recipient, amount))
        
        print(f"\n--- TOP 10 DOE RECIPIENTS BY AMOUNT ---")
        sorted_by_amount = sorted(recipient_amounts.items(), key=lambda x: x[1], reverse=True)
        for recipient, amount in sorted_by_amount[:10]:
            print(f"{recipient}: ${amount:,.2f}")
        
        print(f"\n--- DOE RECIPIENT CATEGORIES ---")
        print(f"Universities: {len(universities)}")
        print(f"National Labs: {len(national_labs)}")
        print(f"Companies: {len(companies)}")
        print(f"Other: {len(awards) - len(universities) - len(national_labs) - len(companies)}")
        
        if national_labs:
            print(f"\n--- TOP NATIONAL LABS ---")
            national_labs.sort(key=lambda x: x[1], reverse=True)
            for lab, amount in national_labs[:5]:
                print(f"{lab}: ${amount:,.2f}")
                
    except Exception as e:
        print(f"Error analyzing DoE: {e}")

if __name__ == "__main__":
    analyze_award_recipients()
    analyze_doe_recipients()
