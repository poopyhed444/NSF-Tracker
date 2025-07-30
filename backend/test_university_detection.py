#!/usr/bin/env python3
"""
Test university detection function directly
"""

from federal_agency_integrator import FederalAgencyIntegrator

def test_university_detection():
    integrator = FederalAgencyIntegrator()
    
    test_names = [
        'Trustees of Columbia University in the City of New York',
        'The Trustees of Princeton University', 
        'Harvard University',
        'Massachusetts Institute of Technology',
        'Stanford University',
        'University of California, Berkeley',
        'The Regents of the University of California',
        'PricewaterhouseCoopers LLP',
        'GlaxoSmithKline LLC',
        'Boeing Company',
        'University Corporation for Atmospheric Research',
        'Institute for Defense Analyses'
    ]
    
    print("Testing university detection:")
    print("=" * 60)
    
    for name in test_names:
        is_univ = integrator.is_research_institution(name)
        status = "✅ UNIVERSITY" if is_univ else "❌ NOT UNIVERSITY"
        print(f"{status}: {name}")
    
    print()

if __name__ == "__main__":
    test_university_detection()
