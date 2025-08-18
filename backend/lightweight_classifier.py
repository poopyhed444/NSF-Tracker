#!/usr/bin/env python3
"""
Lightweight Enhanced Department Classifier
Uses TF-IDF and keyword matching without PyTorch dependencies.
"""

import json
import re
import math
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from collections import Counter, defaultdict

@dataclass
class ClassificationResult:
    field: str
    confidence: float
    matched_departments: List[str]
    reasoning: str

class LightweightDepartmentClassifier:
    def __init__(self, dataset_path: str = 'enhanced_department_dataset.json'):
        self.dataset_path = dataset_path
        self.department_data = {}
        self.field_keywords = {}
        self.department_vectors = {}
        self.vocabulary = set()
        
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
        for field, departments in self.department_data.items():
            for dept in departments:
                words = self.tokenize(dept.lower())
                self.vocabulary.update(words)
        
        # Add field keywords to vocabulary
        for field, keywords in self.field_keywords.items():
            self.vocabulary.update(keywords['primary'])
            self.vocabulary.update(keywords['secondary'])
        
        self.vocabulary = list(self.vocabulary)
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
enhanced_classifier = LightweightDepartmentClassifier()

def classify_text(text: str) -> ClassificationResult:
    """Convenience function for backward compatibility"""
    return enhanced_classifier.classify_department(text)
