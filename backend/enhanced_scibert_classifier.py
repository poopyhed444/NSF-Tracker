#!/usr/bin/env python3
"""
Enhanced SciBERT Department Classifier
Uses comprehensive university department dataset for accurate classification.
"""

import json
import numpy as np
from typing import Dict, List, Optional
import re
import os
from dataclasses import dataclass
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

@dataclass
class ClassificationResult:
    field: str
    confidence: float
    matched_departments: List[str]
    reasoning: str

class EnhancedSciBERTClassifier:
    def __init__(self, dataset_path: str = 'enhanced_department_dataset.json'):
        self.dataset_path = dataset_path
        self.department_data = {}
        self.tfidf_vectorizer = None
        self.tfidf_matrix = None
        self.department_list = []
        self.field_labels = []
        
        # Load and initialize
        self.load_department_dataset()
        self.initialize_tfidf()
        
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
                'Environmental Engineering', 'Industrial Engineering', 'Materials Science',
                'Mechanical Engineering', 'Nuclear Engineering', 'Software Engineering'
            ],
            'life_sciences': [
                'Biology', 'Biochemistry', 'Biophysics', 'Botany', 'Cell Biology',
                'Ecology', 'Genetics', 'Marine Biology', 'Microbiology',
                'Molecular Biology', 'Neuroscience', 'Physiology', 'Zoology'
            ],
            'physical_sciences': [
                'Astronomy', 'Astrophysics', 'Chemistry', 'Earth Sciences',
                'Geology', 'Geophysics', 'Materials Science', 'Meteorology',
                'Oceanography', 'Physics', 'Planetary Sciences'
            ],
            'mathematical_sciences': [
                'Applied Mathematics', 'Computer Science', 'Data Science',
                'Mathematics', 'Statistics', 'Computational Biology',
                'Operations Research', 'Pure Mathematics'
            ],
            'medical_sciences': [
                'Biomedical Sciences', 'Clinical Research', 'Epidemiology',
                'Health Sciences', 'Medical Sciences', 'Medicine',
                'Pharmacology', 'Public Health', 'Veterinary Medicine'
            ],
            'social_sciences': [
                'Anthropology', 'Economics', 'Geography', 'History',
                'Linguistics', 'Philosophy', 'Political Science',
                'Psychology', 'Sociology', 'Urban Studies'
            ],
            'other': [
                'Art', 'Business', 'Education', 'Law', 'Literature',
                'Music', 'Theater', 'Architecture', 'Design'
            ]
        }

    def initialize_tfidf(self):
        """Initialize TF-IDF vectorizer"""
        print("🔧 Initializing TF-IDF vectorizer...")
        
        # Prepare department corpus
        self.department_list = []
        self.field_labels = []
        
        for field, departments in self.department_data.items():
            for dept in departments:
                self.department_list.append(dept)
                self.field_labels.append(field)
        
        # Create TF-IDF matrix
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 3),
            stop_words='english',
            lowercase=True
        )
        
        self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(self.department_list)
        print(f"✅ TF-IDF initialized with {len(self.department_list)} departments")

    def classify_department(self, department_name: str) -> ClassificationResult:
        """Main classification method using TF-IDF similarity"""
        if not department_name or len(department_name.strip()) < 2:
            return ClassificationResult(
                field='other',
                confidence=0.0,
                matched_departments=[],
                reasoning="Invalid or empty department name"
            )
        
        # Clean input
        clean_dept = self.clean_department_name(department_name)
        
        # Vectorize input
        input_vector = self.tfidf_vectorizer.transform([clean_dept])
        
        # Calculate similarities
        similarities = cosine_similarity(input_vector, self.tfidf_matrix).flatten()
        
        # Get best matches
        best_indices = np.argsort(similarities)[-10:][::-1]  # Top 10
        
        # Count field occurrences in top matches
        field_scores = {}
        matched_departments = []
        
        for idx in best_indices:
            if similarities[idx] > 0.1:  # Minimum similarity threshold
                field = self.field_labels[idx]
                dept = self.department_list[idx]
                
                field_scores[field] = field_scores.get(field, 0) + similarities[idx]
                if len(matched_departments) < 5:
                    matched_departments.append(dept)
        
        if not field_scores:
            # Fallback to keyword matching
            return self.classify_with_keywords(clean_dept)
        
        # Get best field
        best_field = max(field_scores.keys(), key=lambda k: field_scores[k])
        confidence = field_scores[best_field] / len(field_scores)
        
        return ClassificationResult(
            field=best_field,
            confidence=confidence,
            matched_departments=matched_departments,
            reasoning=f"TF-IDF similarity with {len(matched_departments)} matches"
        )

    def classify_with_keywords(self, department_name: str) -> ClassificationResult:
        """Fallback classification using keyword matching"""
        field_keywords = {
            'engineering': ['engineering', 'mechanical', 'electrical', 'civil', 'chemical', 'computer'],
            'life_sciences': ['biology', 'bio', 'life', 'cell', 'molecular', 'genetic', 'neuroscience'],
            'physical_sciences': ['physics', 'chemistry', 'astronomy', 'geology', 'earth'],
            'mathematical_sciences': ['mathematics', 'math', 'statistics', 'data', 'computational'],
            'medical_sciences': ['medical', 'medicine', 'health', 'clinical'],
            'social_sciences': ['psychology', 'sociology', 'economics', 'political', 'history'],
            'other': ['art', 'business', 'education', 'law', 'literature']
        }
        
        dept_lower = department_name.lower()
        field_scores = {}
        
        for field, keywords in field_keywords.items():
            score = sum(1 for keyword in keywords if keyword in dept_lower)
            if score > 0:
                field_scores[field] = score
        
        if not field_scores:
            return ClassificationResult(
                field='other',
                confidence=0.1,
                matched_departments=[],
                reasoning="No keyword matches found"
            )
        
        best_field = max(field_scores.keys(), key=lambda k: field_scores[k])
        confidence = field_scores[best_field] / max(field_scores.values())
        
        return ClassificationResult(
            field=best_field,
            confidence=confidence,
            matched_departments=[],
            reasoning=f"Keyword matching: {field_scores[best_field]} matches"
        )

    def clean_department_name(self, name: str) -> str:
        """Clean and normalize department names"""
        # Remove common prefixes and suffixes
        cleaned = re.sub(r'^(the |department of |school of |college of |division of )', '', name.lower())
        cleaned = re.sub(r'( department| school| college| division)$', '', cleaned)
        
        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned

    def classify_pi_department(self, pi_name: str, department: str, institution: str = None) -> Dict:
        """Enhanced PI department classification"""
        result = self.classify_department(department)
        
        return {
            'pi_name': pi_name,
            'department': department,
            'institution': institution,
            'classified_field': result.field,
            'confidence': result.confidence,
            'matched_departments': result.matched_departments,
            'reasoning': result.reasoning
        }

def test_classifier():
    """Test the enhanced classifier"""
    print("🧪 Testing Enhanced Department Classifier...")
    
    classifier = EnhancedSciBERTClassifier()
    
    # Test cases
    test_departments = [
        "Department of Computer Science",
        "Mechanical Engineering",
        "Biology Department",
        "School of Medicine",
        "Physics and Astronomy",
        "Department of Psychology",
        "Chemical Engineering",
        "Neuroscience Program",
        "Economics Department",
        "Materials Science and Engineering"
    ]
    
    print("\n📊 Classification Results:")
    print("=" * 80)
    
    for dept in test_departments:
        result = classifier.classify_department(dept)
        print(f"\nDepartment: {dept}")
        print(f"Field: {result.field}")
        print(f"Confidence: {result.confidence:.3f}")
        print(f"Reasoning: {result.reasoning}")
        if result.matched_departments:
            print(f"Similar: {', '.join(result.matched_departments[:3])}")

if __name__ == "__main__":
    test_classifier()
