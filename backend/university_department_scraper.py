#!/usr/bin/env python3
"""
University Department Scraper
Scrapes department names from major universities to build a comprehensive dataset
for improved department classification.
"""

import requests
from bs4 import BeautifulSoup
import json
import re
import time
from typing import Dict, List, Set
import urllib.parse

class UniversityDepartmentScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.departments = set()
        self.field_mappings = {
            # Engineering departments
            'engineering': ['engineering', 'mechanical', 'electrical', 'civil', 'chemical', 'computer science', 
                          'aerospace', 'biomedical', 'industrial', 'materials', 'nuclear', 'petroleum'],
            
            # Life Sciences
            'life_sciences': ['biology', 'biochemistry', 'biophysics', 'microbiology', 'neuroscience', 
                            'genetics', 'molecular biology', 'cell biology', 'ecology', 'botany', 'zoology',
                            'immunology', 'pharmacology', 'physiology', 'anatomy'],
            
            # Physical Sciences
            'physical_sciences': ['physics', 'chemistry', 'astronomy', 'astrophysics', 'geology', 
                                'geophysics', 'atmospheric', 'oceanography', 'earth sciences'],
            
            # Mathematics and Computer Science
            'mathematical_sciences': ['mathematics', 'statistics', 'computer science', 'data science',
                                    'computational', 'applied mathematics', 'pure mathematics'],
            
            # Medical and Health Sciences
            'medical_sciences': ['medicine', 'medical', 'health', 'nursing', 'pharmacy', 'dentistry',
                               'veterinary', 'public health', 'epidemiology', 'clinical'],
            
            # Social Sciences
            'social_sciences': ['psychology', 'sociology', 'anthropology', 'political science',
                              'economics', 'history', 'geography', 'linguistics', 'philosophy'],
            
            # Other
            'other': ['business', 'education', 'law', 'arts', 'humanities', 'literature', 'music']
        }

    def scrape_mit_departments(self) -> Set[str]:
        """Scrape MIT department listings"""
        departments = set()
        try:
            # MIT Schools and Departments
            urls = [
                'https://web.mit.edu/catalogs/grad/science.html',
                'https://web.mit.edu/catalogs/grad/engineering.html',
                'https://catalogue.mit.edu/schools/'
            ]
            
            for url in urls:
                try:
                    response = self.session.get(url, timeout=10)
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Look for department listings
                    for link in soup.find_all('a', href=True):
                        text = link.get_text().strip()
                        if any(keyword in text.lower() for keyword in ['department', 'school', 'program', 'lab']):
                            if len(text) > 5 and len(text) < 100:
                                departments.add(text)
                    
                    time.sleep(1)  # Be respectful
                except Exception as e:
                    print(f"Error scraping {url}: {e}")
                    continue
                    
        except Exception as e:
            print(f"Error scraping MIT: {e}")
        
        return departments

    def scrape_stanford_departments(self) -> Set[str]:
        """Scrape Stanford department listings"""
        departments = set()
        try:
            # Stanford has a comprehensive department list
            url = 'https://www.stanford.edu/list/academic/'
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for department links and names
            for link in soup.find_all('a', href=True):
                text = link.get_text().strip()
                href = link.get('href', '')
                
                # Filter for academic departments
                if any(keyword in text.lower() for keyword in ['department', 'school', 'program', 'center', 'institute']):
                    if len(text) > 5 and len(text) < 100:
                        departments.add(text)
                        
        except Exception as e:
            print(f"Error scraping Stanford: {e}")
            
        return departments

    def scrape_harvard_departments(self) -> Set[str]:
        """Scrape Harvard department listings"""
        departments = set()
        try:
            # Harvard FAS departments
            url = 'https://www.harvard.edu/schools/'
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            for link in soup.find_all('a', href=True):
                text = link.get_text().strip()
                if any(keyword in text.lower() for keyword in ['department', 'school', 'program']):
                    if len(text) > 5 and len(text) < 100:
                        departments.add(text)
                        
        except Exception as e:
            print(f"Error scraping Harvard: {e}")
            
        return departments

    def get_common_department_patterns(self) -> Set[str]:
        """Generate common department name patterns"""
        base_fields = [
            # Engineering
            "Aerospace Engineering", "Biomedical Engineering", "Chemical Engineering",
            "Civil Engineering", "Computer Science and Engineering", "Electrical Engineering",
            "Environmental Engineering", "Industrial Engineering", "Materials Science and Engineering",
            "Mechanical Engineering", "Nuclear Engineering", "Petroleum Engineering",
            
            # Life Sciences
            "Biology", "Biochemistry", "Biophysics", "Botany", "Cell and Molecular Biology",
            "Ecology and Evolution", "Genetics", "Marine Biology", "Microbiology",
            "Molecular Biology", "Neuroscience", "Physiology", "Zoology",
            
            # Physical Sciences
            "Astronomy", "Astrophysics", "Atmospheric Sciences", "Chemistry",
            "Earth Sciences", "Geology", "Geophysics", "Materials Science",
            "Oceanography", "Physics", "Planetary Sciences",
            
            # Mathematical Sciences
            "Applied Mathematics", "Computer Science", "Data Science", "Mathematics",
            "Pure Mathematics", "Statistics", "Computational Biology",
            
            # Medical/Health
            "Biomedical Sciences", "Clinical Research", "Epidemiology", "Health Sciences",
            "Medical Sciences", "Pharmacology", "Public Health",
            
            # Social Sciences
            "Anthropology", "Economics", "Geography", "History", "Linguistics",
            "Philosophy", "Political Science", "Psychology", "Sociology"
        ]
        
        # Generate variations
        departments = set()
        for field in base_fields:
            departments.add(field)
            departments.add(f"Department of {field}")
            departments.add(f"School of {field}")
            departments.add(f"{field} Department")
            departments.add(f"Division of {field}")
            
        return departments

    def classify_department(self, dept_name: str) -> str:
        """Classify department into research field"""
        dept_lower = dept_name.lower()
        
        for field, keywords in self.field_mappings.items():
            if any(keyword in dept_lower for keyword in keywords):
                return field
                
        return 'other'

    def scrape_all_departments(self) -> Dict[str, List[str]]:
        """Scrape departments from multiple universities and classify them"""
        print("🔍 Scraping department information from major universities...")
        
        all_departments = set()
        
        # Add common patterns
        print("Adding common department patterns...")
        all_departments.update(self.get_common_department_patterns())
        
        # Scrape from universities (with error handling)
        print("Scraping MIT departments...")
        try:
            mit_depts = self.scrape_mit_departments()
            all_departments.update(mit_depts)
            print(f"Found {len(mit_depts)} MIT departments")
        except Exception as e:
            print(f"MIT scraping failed: {e}")
        
        print("Scraping Stanford departments...")
        try:
            stanford_depts = self.scrape_stanford_departments()
            all_departments.update(stanford_depts)
            print(f"Found {len(stanford_depts)} Stanford departments")
        except Exception as e:
            print(f"Stanford scraping failed: {e}")
            
        print("Scraping Harvard departments...")
        try:
            harvard_depts = self.scrape_harvard_departments()
            all_departments.update(harvard_depts)
            print(f"Found {len(harvard_depts)} Harvard departments")
        except Exception as e:
            print(f"Harvard scraping failed: {e}")
        
        # Clean and classify departments
        print("Cleaning and classifying departments...")
        classified_departments = {
            'engineering': [],
            'life_sciences': [],
            'physical_sciences': [],
            'mathematical_sciences': [],
            'medical_sciences': [],
            'social_sciences': [],
            'other': []
        }
        
        for dept in all_departments:
            # Clean department name
            cleaned = self.clean_department_name(dept)
            if cleaned and len(cleaned) > 3:
                field = self.classify_department(cleaned)
                classified_departments[field].append(cleaned)
        
        # Remove duplicates and sort
        for field in classified_departments:
            classified_departments[field] = sorted(list(set(classified_departments[field])))
        
        total_depts = sum(len(depts) for depts in classified_departments.values())
        print(f"✅ Successfully collected and classified {total_depts} departments")
        
        return classified_departments

    def clean_department_name(self, name: str) -> str:
        """Clean and normalize department names"""
        # Remove extra whitespace and special characters
        cleaned = re.sub(r'\s+', ' ', name.strip())
        cleaned = re.sub(r'[^\w\s&,-]', '', cleaned)
        
        # Remove common prefixes/suffixes that don't add value
        prefixes_to_remove = ['the ', 'university ', 'college ', 'school of ']
        for prefix in prefixes_to_remove:
            if cleaned.lower().startswith(prefix):
                cleaned = cleaned[len(prefix):]
        
        return cleaned.strip()

    def save_departments(self, departments: Dict[str, List[str]], filename: str = 'enhanced_department_dataset.json'):
        """Save department dataset to JSON file"""
        with open(filename, 'w') as f:
            json.dump(departments, f, indent=2, sort_keys=True)
        print(f"💾 Department dataset saved to {filename}")

def main():
    """Main function to scrape and save department data"""
    scraper = UniversityDepartmentScraper()
    departments = scraper.scrape_all_departments()
    
    # Print summary
    print("\n📊 Department Collection Summary:")
    for field, depts in departments.items():
        print(f"  {field}: {len(depts)} departments")
    
    # Save to file
    scraper.save_departments(departments)
    
    # Also save a sample for verification
    print("\n📝 Sample departments by field:")
    for field, depts in departments.items():
        if depts:
            print(f"\n{field.upper()}:")
            for dept in depts[:5]:  # Show first 5
                print(f"  - {dept}")
            if len(depts) > 5:
                print(f"  ... and {len(depts) - 5} more")

if __name__ == "__main__":
    main()
