#!/usr/bin/env python3
"""
Enhanced Lightweight Department Classifier with Web Scraping
Uses TF-IDF, keyword matching, and real-time department data scraping.
"""

import json
import re
import math
import asyncio
import aiohttp
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from collections import Counter, defaultdict
from bs4 import BeautifulSoup
import time
from datetime import datetime

@dataclass
class ClassificationResult:
    field: str
    confidence: float
    matched_departments: List[str]
    reasoning: str

class EnhancedLightweightClassifier:
    def __init__(self, dataset_path: str = 'enhanced_department_dataset.json'):
        self.dataset_path = dataset_path
        self.department_data = {}
        self.field_keywords = {}
        self.department_vectors = {}
        self.vocabulary = set()
        self.scraped_departments = set()
        
        # Load and initialize
        self.load_department_dataset()
        self.build_field_keywords()
        self.build_vocabulary()
        self.build_department_vectors()
        
        # University scraping configuration
        self.universities_to_scrape = {
            "Harvard University": ["school", "department", "division"],
            "MIT": ["department", "laboratory", "center"],
            "Stanford University": ["department", "school", "institute"],
            "UC Berkeley": ["department", "college", "school"],
            "Yale University": ["department", "school", "program"]
        }
        
        # Load and initialize
        self.load_department_dataset()
        self.build_field_keywords()
        self.build_vocabulary()
        self.build_department_vectors()
        
    def load_department_dataset(self):
        """Load the enhanced department dataset"""
        try:
            with open(self.dataset_path, 'r') as f:
                self.department_data = json.load(f)
            print(f"✅ Loaded department dataset with {sum(len(depts) for depts in self.department_data.values())} departments")
        except FileNotFoundError:
            print(f"❌ Department dataset not found, creating basic dataset")
            self.create_basic_dataset()
    
    def create_basic_dataset(self):
        """Create a basic department dataset"""
        self.department_data = {
            'engineering': [
                'Aerospace Engineering', 'Biomedical Engineering', 'Chemical Engineering',
                'Civil Engineering', 'Computer Science', 'Electrical Engineering',
                'Environmental Engineering', 'Industrial Engineering', 'Materials Engineering',
                'Mechanical Engineering', 'Software Engineering', 'Systems Engineering'
            ],
            'physical_sciences': [
                'Physics', 'Chemistry', 'Mathematics', 'Statistics', 'Astronomy',
                'Earth Sciences', 'Materials Science', 'Applied Mathematics'
            ],
            'medical_sciences': [
                'Medicine', 'Public Health', 'Biomedical Sciences', 'Clinical Medicine',
                'Health Sciences', 'Medical Research', 'Epidemiology', 'Pharmacology'
            ],
            'biological_sciences': [
                'Biology', 'Ecology', 'Genetics', 'Microbiology', 'Neuroscience',
                'Molecular Biology', 'Cell Biology', 'Biochemistry', 'Bioinformatics'
            ],
            'social_sciences': [
                'Psychology', 'Economics', 'Political Science', 'Sociology',
                'Anthropology', 'Geography', 'Linguistics', 'Education'
            ]
        }
    
    def build_field_keywords(self):
        """Build keyword mappings for each field"""
        self.field_keywords = {
            'engineering': {
                'primary': ['engineering', 'engineer', 'technology', 'computer', 'software', 'systems', 'design'],
                'secondary': ['technical', 'development', 'programming', 'architecture', 'infrastructure']
            },
            'physical_sciences': {
                'primary': ['physics', 'chemistry', 'mathematics', 'math', 'statistics', 'astronomy'],
                'secondary': ['quantum', 'molecular', 'theoretical', 'applied', 'computational']
            },
            'medical_sciences': {
                'primary': ['medicine', 'medical', 'health', 'clinical', 'patient', 'therapy'],
                'secondary': ['healthcare', 'disease', 'treatment', 'diagnosis', 'pharmaceutical']
            },
            'biological_sciences': {
                'primary': ['biology', 'biological', 'life', 'genetics', 'ecology', 'neuroscience'],
                'secondary': ['organism', 'cellular', 'molecular', 'evolution', 'biodiversity']
            },
            'social_sciences': {
                'primary': ['psychology', 'economics', 'social', 'political', 'sociology'],
                'secondary': ['behavior', 'society', 'culture', 'policy', 'human']
            }
        }
    
    def build_vocabulary(self):
        """Build vocabulary from all departments"""
        vocab_set = set()
        
        for field, departments in self.department_data.items():
            for dept in departments:
                words = self.tokenize(dept.lower())
                vocab_set.update(words)
        
        # Add field keywords to vocabulary
        for field, keywords in self.field_keywords.items():
            vocab_set.update(keywords['primary'])
            vocab_set.update(keywords['secondary'])
        
        self.vocabulary = list(vocab_set)
        print(f"🔧 Built vocabulary with {len(self.vocabulary)} unique terms")
    
    def tokenize(self, text: str) -> List[str]:
        """Simple tokenization"""
        # Remove special characters and split
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        words = text.split()
        
        # Remove common stop words
        stop_words = {'the', 'of', 'and', 'in', 'to', 'for', 'with', 'at', 'by', 'from', 'on', 'an', 'a'}
        words = [w for w in words if w not in stop_words and len(w) > 2]
        
        return words
    
    def build_department_vectors(self):
        """Build TF-IDF-like vectors for each department"""
        # Count document frequency for each term
        df = defaultdict(int)
        all_docs = []
        
        for field, departments in self.department_data.items():
            for dept in departments:
                words = self.tokenize(dept)
                all_docs.append((field, dept, words))
                unique_words = set(words)
                for word in unique_words:
                    df[word] += 1
        
        total_docs = len(all_docs)
        
        # Build vectors
        for field, dept, words in all_docs:
            vector = {}
            word_count = Counter(words)
            
            for word in self.vocabulary:
                if word in word_count:
                    tf = word_count[word] / len(words) if words else 0
                    idf = math.log(total_docs / (df[word] + 1))
                    vector[word] = tf * idf
                else:
                    vector[word] = 0.0
            
            if field not in self.department_vectors:
                self.department_vectors[field] = {}
            self.department_vectors[field][dept] = vector
        
        print(f"✅ Built vectors for {total_docs} departments")
    
    def text_to_vector(self, text: str) -> Dict[str, float]:
        """Convert input text to TF-IDF vector"""
        words = self.tokenize(text)
        word_count = Counter(words)
        
        vector = {}
        for word in self.vocabulary:
            if word in word_count:
                tf = word_count[word] / len(words) if words else 0
                # Use simple IDF approximation
                idf = 1.0 if word in words else 0.0
                vector[word] = tf * idf
            else:
                vector[word] = 0.0
        
        return vector
    
    def cosine_similarity(self, vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
        """Calculate cosine similarity between two vectors"""
        dot_product = sum(vec1[word] * vec2[word] for word in self.vocabulary)
        
        norm1 = math.sqrt(sum(vec1[word] ** 2 for word in self.vocabulary))
        norm2 = math.sqrt(sum(vec2[word] ** 2 for word in self.vocabulary))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def keyword_score(self, text: str, field: str) -> float:
        """Calculate keyword-based score for a field"""
        text_lower = text.lower()
        keywords = self.field_keywords.get(field, {'primary': [], 'secondary': []})
        
        primary_score = sum(2.0 for word in keywords['primary'] if word in text_lower)
        secondary_score = sum(1.0 for word in keywords['secondary'] if word in text_lower)
        
        return primary_score + secondary_score
    
    async def scrape_university_departments(self, university_name: str, keywords: List[str]) -> Set[str]:
        """Scrape department names from a university website"""
        departments = set()
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                # Search for university departments page
                search_url = f"https://www.google.com/search?q={university_name.replace(' ', '+')}+departments+academic"
                
                async with session.get(search_url) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Extract department names from search results
                        for link in soup.find_all('a', href=True):
                            text = link.get_text().lower()
                            for keyword in keywords:
                                if keyword in text and any(field in text for field in ['engineering', 'science', 'medicine', 'arts', 'business']):
                                    # Clean and extract department name
                                    dept_name = self.clean_department_name(link.get_text())
                                    if dept_name:
                                        departments.add(dept_name)
                                        
        except Exception as e:
            print(f"⚠️ Could not scrape {university_name}: {e}")
        
        return departments
    
    def clean_department_name(self, raw_name: str) -> Optional[str]:
        """Clean and standardize department names"""
        if not raw_name or len(raw_name) < 5:
            return None
            
        # Remove common prefixes/suffixes
        cleaned = re.sub(r'^(Department of|School of|College of|Division of|Institute of|Center for)\s+', '', raw_name, flags=re.IGNORECASE)
        cleaned = re.sub(r'\s+(Department|School|College|Division|Institute|Center)$', '', cleaned, flags=re.IGNORECASE)
        
        # Remove special characters and normalize
        cleaned = re.sub(r'[^\w\s&-]', '', cleaned)
        cleaned = ' '.join(cleaned.split())  # Normalize whitespace
        
        # Skip if too short or contains unwanted terms
        unwanted = ['home', 'about', 'contact', 'news', 'events', 'search', 'login']
        if len(cleaned) < 3 or any(word in cleaned.lower() for word in unwanted):
            return None
            
        return cleaned.title()
    
    async def enhance_department_dataset(self):
        """Enhance the department dataset with scraped data"""
        print("🔍 Enhancing department dataset with web scraping...")
        
        tasks = []
        for university, keywords in self.universities_to_scrape.items():
            task = self.scrape_university_departments(university, keywords)
            tasks.append(task)
        
        # Run scraping tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        total_new_depts = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                continue
                
            university = list(self.universities_to_scrape.keys())[i]
            new_departments = result
            
            if new_departments:
                # Categorize new departments
                for dept in new_departments:
                    field = self.categorize_department(dept)
                    if field and field in self.department_data:
                        if dept not in self.department_data[field]:
                            self.department_data[field].append(dept)
                            total_new_depts += 1
                            
                print(f"📚 Added {len(new_departments)} departments from {university}")
        
        if total_new_depts > 0:
            print(f"✅ Enhanced dataset with {total_new_depts} new departments")
            # Rebuild vectors with new data
            self.build_vocabulary()
            self.build_department_vectors()
            
            # Save updated dataset
            with open(self.dataset_path, 'w') as f:
                json.dump(self.department_data, f, indent=2)
    
    def categorize_department(self, dept_name: str) -> Optional[str]:
        """Categorize a department into a field based on keywords"""
        dept_lower = dept_name.lower()
        
        # Engineering keywords
        if any(word in dept_lower for word in ['engineering', 'computer', 'software', 'systems', 'technology']):
            return 'engineering'
        
        # Medical sciences keywords
        if any(word in dept_lower for word in ['medicine', 'medical', 'health', 'clinical', 'biomedical']):
            return 'medical_sciences'
        
        # Physical sciences keywords
        if any(word in dept_lower for word in ['physics', 'chemistry', 'mathematics', 'statistics', 'astronomy']):
            return 'physical_sciences'
        
        # Biological sciences keywords
        if any(word in dept_lower for word in ['biology', 'genetics', 'ecology', 'neuroscience', 'biochemistry']):
            return 'biological_sciences'
        
        # Social sciences keywords
        if any(word in dept_lower for word in ['psychology', 'economics', 'political', 'sociology', 'anthropology']):
            return 'social_sciences'
        
        return None

    def classify_department(self, text: str) -> ClassificationResult:
        """Classify department text using hybrid approach"""
        text_vector = self.text_to_vector(text)
        
        field_scores = {}
        best_matches = {}
        
        # Calculate similarity scores for each field
        for field, departments in self.department_vectors.items():
            max_similarity = 0.0
            best_dept_matches = []
            
            for dept, dept_vector in departments.items():
                similarity = self.cosine_similarity(text_vector, dept_vector)
                if similarity > max_similarity:
                    max_similarity = similarity
                
                # Collect good matches
                if similarity > 0.1:  # Threshold for considering a match
                    best_dept_matches.append((dept, similarity))
            
            # Add keyword-based scoring
            keyword_score = self.keyword_score(text, field)
            
            # Combine similarity and keyword scores
            combined_score = max_similarity * 10 + keyword_score
            
            field_scores[field] = combined_score
            best_matches[field] = sorted(best_dept_matches, key=lambda x: x[1], reverse=True)[:5]
        
        # Find best field
        if not field_scores:
            return ClassificationResult("Unknown", 0.0, [], "No matches found")
        
        best_field = max(field_scores, key=field_scores.get)
        confidence = field_scores[best_field]
        
        # Get matched departments
        matched_depts = [dept for dept, score in best_matches[best_field]]
        
        # Create reasoning
        reasoning = f"Hybrid scoring with {len(matched_depts)} department matches"
        if confidence > 3.0:
            reasoning += " (high confidence)"
        elif confidence > 1.0:
            reasoning += " (medium confidence)"
        else:
            reasoning += " (low confidence)"
        
        return ClassificationResult(
            field=best_field,
            confidence=confidence,
            matched_departments=matched_depts,
            reasoning=reasoning
        )

# Create global instance
enhanced_classifier = EnhancedLightweightClassifier()

def classify_text(text: str) -> ClassificationResult:
    """Convenience function for backward compatibility"""
    return enhanced_classifier.classify_department(text)
