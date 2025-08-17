"""
Enhanced University Department Scraper and Classifier

This module scrapes department names from major universities and creates
a comprehensive dataset for improved SciBERT classification.
"""

import asyncio
import aiohttp
import re
import json
import os
from typing import List, Dict, Set, Optional
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import time
from datetime import datetime

class UniversityDepartmentScraper:
    """Scrapes department information from major universities."""
    
    def __init__(self):
        self.departments = set()
        self.university_mappings = {}
        self.session_timeout = aiohttp.ClientTimeout(total=30)
        
        # Major universities to scrape
        self.universities = {
            "Harvard University": {
                "base_url": "https://www.harvard.edu",
                "department_pages": [
                    "/schools/harvard-medical-school/departments",
                    "/schools/harvard-school-of-engineering-and-applied-sciences/areas-of-study",
                    "/schools/faculty-arts-sciences/departments"
                ]
            },
            "MIT": {
                "base_url": "https://web.mit.edu",
                "department_pages": [
                    "/academics/schools-departments",
                    "/academics/undergraduate-programs",
                    "/academics/graduate-programs"
                ]
            },
            "Stanford University": {
                "base_url": "https://www.stanford.edu",
                "department_pages": [
                    "/academics/schools",
                    "/academics/departments",
                    "/school-of-medicine/departments"
                ]
            },
            "UC Berkeley": {
                "base_url": "https://www.berkeley.edu",
                "department_pages": [
                    "/academics/schools-colleges",
                    "/academics/departments-programs"
                ]
            },
            "Caltech": {
                "base_url": "https://www.caltech.edu",
                "department_pages": [
                    "/academics/divisions",
                    "/academics/majors-minors"
                ]
            },
            "Yale University": {
                "base_url": "https://www.yale.edu",
                "department_pages": [
                    "/academics/departments",
                    "/academics/schools-programs"
                ]
            },
            "Princeton University": {
                "base_url": "https://www.princeton.edu",
                "department_pages": [
                    "/academics/departments",
                    "/academics/areas-of-study"
                ]
            }
        }
        
        # Common department patterns to look for
        self.department_patterns = [
            r"Department of ([A-Za-z\s&\-,]+)",
            r"School of ([A-Za-z\s&\-,]+)",
            r"Division of ([A-Za-z\s&\-,]+)",
            r"Institute of ([A-Za-z\s&\-,]+)",
            r"Center for ([A-Za-z\s&\-,]+)",
            r"Program in ([A-Za-z\s&\-,]+)"
        ]
    
    async def scrape_university_departments(self, university: str, config: Dict) -> Set[str]:
        """Scrape departments from a specific university."""
        departments = set()
        
        async with aiohttp.ClientSession(timeout=self.session_timeout) as session:
            try:
                print(f"🔍 Scraping departments from {university}...")
                
                for page_path in config["department_pages"]:
                    try:
                        url = urljoin(config["base_url"], page_path)
                        async with session.get(url, headers={
                            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                        }) as response:
                            if response.status == 200:
                                html = await response.text()
                                page_departments = self.extract_departments_from_html(html)
                                departments.update(page_departments)
                                print(f"  📄 Found {len(page_departments)} departments from {page_path}")
                            
                        # Rate limiting
                        await asyncio.sleep(1)
                        
                    except Exception as e:
                        print(f"  ⚠️ Error scraping {page_path}: {str(e)}")
                        continue
                        
            except Exception as e:
                print(f"❌ Error scraping {university}: {str(e)}")
        
        print(f"✅ Total departments found for {university}: {len(departments)}")
        return departments
    
    def extract_departments_from_html(self, html: str) -> Set[str]:
        """Extract department names from HTML content."""
        departments = set()
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        text = soup.get_text()
        
        # Extract using patterns
        for pattern in self.department_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                cleaned = self.clean_department_name(match)
                if cleaned and len(cleaned) > 3:
                    departments.add(cleaned)
        
        # Also look for common department keywords in links and headings
        for tag in soup.find_all(['a', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            text = tag.get_text().strip()
            if any(keyword in text.lower() for keyword in [
                'department', 'school', 'division', 'institute', 'center', 'program'
            ]):
                cleaned = self.clean_department_name(text)
                if cleaned and 5 < len(cleaned) < 100:
                    departments.add(cleaned)
        
        return departments
    
    def clean_department_name(self, name: str) -> Optional[str]:
        """Clean and normalize department names."""
        if not name:
            return None
            
        # Remove common prefixes/suffixes
        cleaned = re.sub(r'^(Department of|School of|Division of|Institute of|Center for|Program in)\s*', '', name, flags=re.IGNORECASE)
        cleaned = re.sub(r'\s*(Department|School|Division|Institute|Center|Program)$', '', cleaned, flags=re.IGNORECASE)
        
        # Clean up formatting
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        cleaned = cleaned.title()
        
        # Filter out too short or generic names
        if len(cleaned) < 3 or cleaned.lower() in ['home', 'about', 'contact', 'news', 'events']:
            return None
            
        return cleaned
    
    async def scrape_all_universities(self) -> Dict[str, Set[str]]:
        """Scrape departments from all configured universities."""
        all_departments = {}
        
        print("🚀 Starting comprehensive university department scraping...")
        
        for university, config in self.universities.items():
            departments = await self.scrape_university_departments(university, config)
            all_departments[university] = departments
            self.departments.update(departments)
            
            # Save progress incrementally
            await asyncio.sleep(2)  # Rate limiting between universities
        
        print(f"🎯 Total unique departments collected: {len(self.departments)}")
        return all_departments
    
    def create_enhanced_department_dataset(self) -> Dict[str, List[str]]:
        """Create an enhanced dataset with department categories and examples."""
        
        # Enhanced department categories with more granular classification
        enhanced_categories = {
            "Biological Sciences": [
                "Biology", "Molecular Biology", "Cell Biology", "Developmental Biology",
                "Evolutionary Biology", "Marine Biology", "Microbiology", "Biochemistry",
                "Biophysics", "Biotechnology", "Genetics", "Genomics", "Proteomics",
                "Ecology", "Botany", "Zoology", "Physiology", "Anatomy"
            ],
            "Medical Sciences": [
                "Medicine", "Surgery", "Pediatrics", "Cardiology", "Neurology",
                "Psychiatry", "Radiology", "Pathology", "Pharmacology", "Immunology",
                "Oncology", "Dermatology", "Ophthalmology", "Orthopedics", "Anesthesiology",
                "Emergency Medicine", "Family Medicine", "Internal Medicine", "Obstetrics",
                "Gynecology", "Urology", "Otolaryngology", "Plastic Surgery"
            ],
            "Physical Sciences": [
                "Physics", "Chemistry", "Astronomy", "Astrophysics", "Atmospheric Sciences",
                "Earth Sciences", "Geology", "Geophysics", "Oceanography", "Meteorology",
                "Materials Science", "Crystallography", "Spectroscopy", "Quantum Physics",
                "Nuclear Physics", "Particle Physics", "Condensed Matter Physics"
            ],
            "Engineering": [
                "Mechanical Engineering", "Electrical Engineering", "Civil Engineering",
                "Chemical Engineering", "Aerospace Engineering", "Biomedical Engineering",
                "Computer Engineering", "Environmental Engineering", "Industrial Engineering",
                "Materials Engineering", "Nuclear Engineering", "Petroleum Engineering",
                "Systems Engineering", "Software Engineering", "Robotics Engineering"
            ],
            "Computer Science & Technology": [
                "Computer Science", "Information Technology", "Data Science", "Artificial Intelligence",
                "Machine Learning", "Cybersecurity", "Software Engineering", "Human-Computer Interaction",
                "Computer Graphics", "Computational Biology", "Bioinformatics", "Digital Media",
                "Information Systems", "Computer Networks", "Database Systems"
            ],
            "Mathematical Sciences": [
                "Mathematics", "Applied Mathematics", "Statistics", "Probability",
                "Operations Research", "Actuarial Science", "Mathematical Physics",
                "Computational Mathematics", "Pure Mathematics", "Discrete Mathematics",
                "Analysis", "Algebra", "Geometry", "Topology", "Number Theory"
            ],
            "Neuroscience & Psychology": [
                "Neuroscience", "Psychology", "Cognitive Science", "Behavioral Science",
                "Neuropsychology", "Psychobiology", "Developmental Psychology",
                "Social Psychology", "Clinical Psychology", "Experimental Psychology",
                "Computational Neuroscience", "Systems Neuroscience", "Behavioral Neuroscience"
            ],
            "Social Sciences": [
                "Economics", "Political Science", "Sociology", "Anthropology", "Geography",
                "History", "Philosophy", "Linguistics", "Communication", "International Relations",
                "Public Policy", "Urban Planning", "Criminology", "Social Work", "Archaeology"
            ],
            "Environmental Sciences": [
                "Environmental Science", "Environmental Engineering", "Climate Science",
                "Conservation Biology", "Sustainability", "Environmental Policy",
                "Renewable Energy", "Green Technology", "Environmental Chemistry",
                "Environmental Health", "Forest Sciences", "Wildlife Biology"
            ],
            "Business & Management": [
                "Business Administration", "Management", "Marketing", "Finance", "Accounting",
                "Economics", "Entrepreneurship", "Operations Management", "Supply Chain Management",
                "Human Resources", "Strategic Management", "International Business"
            ],
            "Education": [
                "Education", "Curriculum Studies", "Educational Psychology", "Special Education",
                "Higher Education", "Educational Technology", "Teacher Education",
                "Educational Leadership", "Educational Research", "Learning Sciences"
            ],
            "Arts & Humanities": [
                "Art", "Music", "Literature", "Creative Writing", "Theater", "Film Studies",
                "Art History", "Musicology", "Philosophy", "Religion", "Cultural Studies",
                "Media Studies", "Digital Arts", "Fine Arts", "Performing Arts"
            ]
        }
        
        # Add scraped departments to appropriate categories
        for dept in self.departments:
            categorized = False
            for category, keywords in enhanced_categories.items():
                if any(keyword.lower() in dept.lower() for keyword in keywords):
                    if dept not in enhanced_categories[category]:
                        enhanced_categories[category].append(dept)
                        categorized = True
                        break
            
            # If not categorized, add to a miscellaneous category
            if not categorized:
                if "Interdisciplinary" not in enhanced_categories:
                    enhanced_categories["Interdisciplinary"] = []
                enhanced_categories["Interdisciplinary"].append(dept)
        
        return enhanced_categories

# Fallback comprehensive department list for immediate use
COMPREHENSIVE_DEPARTMENTS = {
    "Biological Sciences": [
        "Biology", "Molecular Biology", "Cell Biology", "Developmental Biology",
        "Evolutionary Biology", "Marine Biology", "Microbiology", "Biochemistry",
        "Biophysics", "Biotechnology", "Genetics", "Genomics", "Proteomics",
        "Ecology", "Botany", "Zoology", "Physiology", "Anatomy", "Neurobiology",
        "Structural Biology", "Systems Biology", "Chemical Biology", "Plant Biology",
        "Animal Sciences", "Entomology", "Ornithology", "Herpetology", "Ichthyology"
    ],
    "Medical Sciences": [
        "Medicine", "Surgery", "Pediatrics", "Cardiology", "Neurology", "Psychiatry",
        "Radiology", "Pathology", "Pharmacology", "Immunology", "Oncology",
        "Dermatology", "Ophthalmology", "Orthopedics", "Anesthesiology",
        "Emergency Medicine", "Family Medicine", "Internal Medicine", "Obstetrics",
        "Gynecology", "Urology", "Otolaryngology", "Plastic Surgery", "Rehabilitation",
        "Public Health", "Epidemiology", "Health Policy", "Global Health", "Nursing"
    ],
    "Physical Sciences": [
        "Physics", "Chemistry", "Astronomy", "Astrophysics", "Atmospheric Sciences",
        "Earth Sciences", "Geology", "Geophysics", "Oceanography", "Meteorology",
        "Materials Science", "Crystallography", "Spectroscopy", "Quantum Physics",
        "Nuclear Physics", "Particle Physics", "Condensed Matter Physics",
        "Physical Chemistry", "Theoretical Physics", "Applied Physics", "Optics"
    ],
    "Engineering": [
        "Mechanical Engineering", "Electrical Engineering", "Civil Engineering",
        "Chemical Engineering", "Aerospace Engineering", "Biomedical Engineering",
        "Computer Engineering", "Environmental Engineering", "Industrial Engineering",
        "Materials Engineering", "Nuclear Engineering", "Petroleum Engineering",
        "Systems Engineering", "Software Engineering", "Robotics Engineering",
        "Ocean Engineering", "Agricultural Engineering", "Mining Engineering"
    ],
    "Computer Science & Technology": [
        "Computer Science", "Information Technology", "Data Science", "Artificial Intelligence",
        "Machine Learning", "Cybersecurity", "Software Engineering", "Human-Computer Interaction",
        "Computer Graphics", "Computational Biology", "Bioinformatics", "Digital Media",
        "Information Systems", "Computer Networks", "Database Systems", "Robotics",
        "Computer Vision", "Natural Language Processing", "Distributed Systems"
    ],
    "Mathematical Sciences": [
        "Mathematics", "Applied Mathematics", "Statistics", "Probability",
        "Operations Research", "Actuarial Science", "Mathematical Physics",
        "Computational Mathematics", "Pure Mathematics", "Discrete Mathematics",
        "Analysis", "Algebra", "Geometry", "Topology", "Number Theory",
        "Mathematical Biology", "Financial Mathematics", "Cryptography"
    ],
    "Neuroscience & Psychology": [
        "Neuroscience", "Psychology", "Cognitive Science", "Behavioral Science",
        "Neuropsychology", "Psychobiology", "Developmental Psychology",
        "Social Psychology", "Clinical Psychology", "Experimental Psychology",
        "Computational Neuroscience", "Systems Neuroscience", "Behavioral Neuroscience",
        "Cognitive Neuroscience", "Neuroimaging", "Behavioral Economics"
    ],
    "Social Sciences": [
        "Economics", "Political Science", "Sociology", "Anthropology", "Geography",
        "History", "Philosophy", "Linguistics", "Communication", "International Relations",
        "Public Policy", "Urban Planning", "Criminology", "Social Work", "Archaeology",
        "Cultural Anthropology", "Physical Anthropology", "Comparative Politics"
    ],
    "Environmental Sciences": [
        "Environmental Science", "Environmental Engineering", "Climate Science",
        "Conservation Biology", "Sustainability", "Environmental Policy",
        "Renewable Energy", "Green Technology", "Environmental Chemistry",
        "Environmental Health", "Forest Sciences", "Wildlife Biology",
        "Marine Sciences", "Atmospheric Chemistry", "Environmental Toxicology"
    ]
}

async def scrape_and_enhance_departments():
    """Main function to scrape departments and create enhanced dataset."""
    scraper = UniversityDepartmentScraper()
    
    try:
        # Scrape from universities
        scraped_data = await scraper.scrape_all_universities()
        
        # Create enhanced dataset
        enhanced_dataset = scraper.create_enhanced_department_dataset()
        
        # Save the data
        output_file = "enhanced_department_dataset.json"
        with open(output_file, 'w') as f:
            json.dump({
                "scraped_departments": {k: list(v) for k, v in scraped_data.items()},
                "enhanced_categories": enhanced_dataset,
                "total_departments": len(scraper.departments),
                "scraped_at": datetime.now().isoformat()
            }, f, indent=2)
        
        print(f"✅ Enhanced department dataset saved to {output_file}")
        return enhanced_dataset
        
    except Exception as e:
        print(f"❌ Error in scraping: {str(e)}")
        print("🔄 Using fallback comprehensive department list")
        return COMPREHENSIVE_DEPARTMENTS

if __name__ == "__main__":
    # Run the scraping process
    enhanced_departments = asyncio.run(scrape_and_enhance_departments())
    print(f"📊 Enhanced dataset contains {len(enhanced_departments)} categories")
    for category, depts in enhanced_departments.items():
        print(f"  {category}: {len(depts)} departments")
