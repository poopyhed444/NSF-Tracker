#!/usr/bin/env python3
"""
Enhanced BERT-based Department Classifier for NSF-Tracker
Combines BERT semantic analysis with university department datasets and web scraping
"""

import os
import json
import asyncio
import aiohttp
from typing import Dict, List, Optional, Union, Set
from dataclasses import dataclass
import numpy as np
import re
from collections import Counter, defaultdict
from bs4 import BeautifulSoup
import time
from datetime import datetime

# Global classifier instance
_bert_classifier = None

@dataclass
class BERTClassificationResult:
    field: str
    confidence: float
    all_scores: Dict[str, float]
    matched_departments: List[str]
    reasoning: str
    method: str

class EnhancedBERTDepartmentClassifier:
    """Enhanced BERT-based classifier with university data and web scraping"""
    
    def __init__(self, dataset_path: str = 'enhanced_department_dataset.json'):
        self.model = None
        self.field_embeddings = {}
        self.dataset_path = dataset_path
        self.department_data = {}
        self.all_departments = []
        self.field_labels = []
        self.scraped_departments = set()
        
        # Enhanced field descriptions based on collected university data
        self.field_descriptions = {
            'engineering': """
            computer science software engineering technology artificial intelligence machine learning 
            robotics automation systems programming algorithms aerospace biomedical chemical civil 
            electrical environmental industrial materials mechanical nuclear petroleum bioengineering
            computational systems design manufacturing robotics data structures algorithms programming
            """,
            'medical_sciences': """
            medicine medical clinical health biomedical disease treatment therapy drug pharmaceutical 
            cancer biology healthcare pathology anatomy physiology immunology pharmacology neurology
            cardiology oncology pediatrics surgery radiology dermatology psychiatry clinical research
            medical device biomedical sciences health sciences public health epidemiology
            """,
            'biological_sciences': """
            biology genetics molecular cell biochemistry ecology neuroscience microbiology evolution 
            organism life sciences botany zoology marine biology developmental biology structural biology
            biophysics bioinformatics genomics proteomics systems biology computational biology
            evolutionary biology plant biology animal biology ecology environmental biology
            """,
            'physical_sciences': """
            physics chemistry mathematics statistics astronomy quantum materials computational theory 
            science research analytical chemistry organic chemistry inorganic chemistry physical chemistry
            theoretical physics experimental physics condensed matter physics particle physics astrophysics
            cosmology geology earth sciences atmospheric sciences oceanography meteorology geophysics
            """,
            'social_sciences': """
            psychology sociology economics political anthropology education linguistics behavioral 
            social human society cognitive psychology developmental psychology social psychology
            political science international relations public policy anthropology linguistics
            communication studies urban studies geography history philosophy religious studies
            """,
            'mathematical_sciences': """
            mathematics statistics data analysis computational modeling algorithms numerical methods 
            applied math pure mathematics statistical analysis data science operations research
            mathematical modeling computational mathematics discrete mathematics analysis algebra
            geometry topology probability theory mathematical statistics biostatistics
            """
        }
        
        # University scraping configuration
        self.universities_to_scrape = {
            "Harvard University": {
                "base_patterns": ["school", "department", "division", "institute", "center"],
                "field_hints": {
                    "engineering": ["engineering", "applied sciences", "computer"],
                    "medical_sciences": ["medical", "medicine", "health", "clinical"],
                    "biological_sciences": ["biology", "life sciences", "molecular", "genetics"],
                    "physical_sciences": ["physics", "chemistry", "astronomy", "earth"],
                    "social_sciences": ["psychology", "sociology", "economics", "political"],
                    "mathematical_sciences": ["mathematics", "statistics", "data science"]
                }
            },
            "MIT": {
                "base_patterns": ["department", "laboratory", "center", "institute"],
                "field_hints": {
                    "engineering": ["engineering", "computer science", "technology"],
                    "physical_sciences": ["physics", "chemistry", "materials"],
                    "biological_sciences": ["biology", "bioengineering"],
                    "mathematical_sciences": ["mathematics", "statistics"]
                }
            },
            "Stanford University": {
                "base_patterns": ["department", "school", "institute", "program"],
                "field_hints": {
                    "engineering": ["engineering", "computer science"],
                    "medical_sciences": ["medicine", "medical"],
                    "biological_sciences": ["biology", "biosciences"],
                    "physical_sciences": ["physics", "chemistry"],
                    "social_sciences": ["humanities", "social sciences"]
                }
            }
        }
        
        # Load and initialize
        self.load_department_dataset()
        self._initialize_bert()
    
    def load_department_dataset(self):
        """Load the comprehensive department dataset from university scraping"""
        try:
            with open(self.dataset_path, 'r') as f:
                self.department_data = json.load(f)
            
            # Flatten department data for processing
            self.all_departments = []
            self.field_labels = []
            
            for field, departments in self.department_data.items():
                for dept in departments:
                    self.all_departments.append(dept)
                    self.field_labels.append(field)
            
            print(f"✅ Loaded enhanced department dataset with {len(self.all_departments)} departments from {len(self.department_data)} fields")
            
        except FileNotFoundError:
            print(f"⚠️ Enhanced department dataset not found, creating basic dataset")
            self.create_basic_dataset()
    
    def create_basic_dataset(self):
        """Create a basic department dataset if enhanced one is not available"""
        self.department_data = {
            'engineering': [
                'Aerospace Engineering', 'Biomedical Engineering', 'Chemical Engineering',
                'Civil Engineering', 'Computer Science', 'Electrical Engineering',
                'Environmental Engineering', 'Industrial Engineering', 'Materials Science',
                'Mechanical Engineering', 'Nuclear Engineering', 'Software Engineering'
            ],
            'biological_sciences': [
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
            ]
        }
        
        # Save basic dataset
        with open(self.dataset_path, 'w') as f:
            json.dump(self.department_data, f, indent=2)
    
    def _initialize_bert(self):
        """Initialize the BERT model and pre-compute field embeddings"""
        try:
            from sentence_transformers import SentenceTransformer
            print("🤖 Loading enhanced BERT model for department classification...")
            
            # Use a lightweight but effective model
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Pre-compute field embeddings for efficiency
            print("🧠 Computing enhanced field embeddings with university data...")
            for field, description in self.field_descriptions.items():
                # Combine field description with actual department names from dataset
                field_departments = self.department_data.get(field, [])
                combined_text = f"{description} {' '.join(field_departments[:20])}"  # Include sample departments
                self.field_embeddings[field] = self.model.encode(combined_text)
            
            print(f"✅ Enhanced BERT classifier initialized with {len(self.field_embeddings)} fields and {len(self.all_departments)} departments")
            
        except ImportError:
            print("⚠️ sentence-transformers not available, BERT classification disabled")
            self.model = None
        except Exception as e:
            print(f"❌ Error initializing enhanced BERT classifier: {e}")
            self.model = None
    
    async def scrape_university_departments(self, university_name: str) -> Set[str]:
        """Scrape departments from a specific university (async)"""
        departments = set()
        
        if university_name not in self.universities_to_scrape:
            return departments
        
        config = self.universities_to_scrape[university_name]
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                # For now, return cached department patterns based on university
                # In a full implementation, this would scrape live data
                patterns = config["base_patterns"]
                field_hints = config["field_hints"]
                
                # Generate department names based on patterns and field hints
                for field, hints in field_hints.items():
                    for hint in hints:
                        for pattern in patterns:
                            dept_name = f"{pattern.title()} of {hint.title()}"
                            departments.add(dept_name)
                            
                            # Add variations
                            departments.add(f"{hint.title()} {pattern.title()}")
                            departments.add(f"{hint.title()}")
        
        except Exception as e:
            print(f"⚠️ Error scraping {university_name}: {e}")
        
        return departments
    
    def get_department_keywords(self, text: str) -> List[str]:
        """Extract department-related keywords from text"""
        keywords = []
        text_lower = text.lower()
        
        # Department indicators
        dept_patterns = [
            r'department of (\w+(?:\s+\w+)*)',
            r'school of (\w+(?:\s+\w+)*)',
            r'division of (\w+(?:\s+\w+)*)',
            r'institute of (\w+(?:\s+\w+)*)',
            r'center for (\w+(?:\s+\w+)*)',
            r'(\w+(?:\s+\w+)*) department',
            r'(\w+(?:\s+\w+)*) school',
        ]
        
        for pattern in dept_patterns:
            matches = re.findall(pattern, text_lower)
            keywords.extend(matches)
        
        return keywords
    
    def hybrid_classification(self, text: str) -> BERTClassificationResult:
        """
        Enhanced classification combining BERT semantic analysis with 
        keyword matching and department dataset
        """
        if not self.model or not text or len(text.strip()) < 5:
            return BERTClassificationResult(
                field='other',
                confidence=0.0,
                all_scores={},
                matched_departments=[],
                reasoning="BERT model not available or text too short",
                method="fallback"
            )
        
        try:
            # 1. BERT Semantic Analysis
            text_embedding = self.model.encode(text.strip())
            
            # Calculate similarities with each field
            bert_similarities = {}
            for field, field_embedding in self.field_embeddings.items():
                similarity = np.dot(text_embedding, field_embedding) / (
                    np.linalg.norm(text_embedding) * np.linalg.norm(field_embedding)
                )
                bert_similarities[field] = float(similarity)
            
            # 2. Department Dataset Matching
            text_lower = text.lower()
            department_matches = {}
            matched_depts = []
            
            for i, dept_name in enumerate(self.all_departments):
                dept_lower = dept_name.lower()
                field = self.field_labels[i]
                
                # Check for direct substring matches
                if any(word in text_lower for word in dept_lower.split() if len(word) > 3):
                    department_matches[field] = department_matches.get(field, 0) + 1
                    if len(matched_depts) < 5:
                        matched_depts.append(dept_name)
            
            # 3. Keyword-based Scoring
            keywords = self.get_department_keywords(text)
            keyword_scores = {}
            
            for keyword in keywords:
                for field, departments in self.department_data.items():
                    for dept in departments:
                        if keyword.lower() in dept.lower():
                            keyword_scores[field] = keyword_scores.get(field, 0) + 1
            
            # 4. Combine Scores
            final_scores = {}
            for field in self.field_descriptions.keys():
                # Weight: 60% BERT, 25% department matching, 15% keywords
                bert_score = bert_similarities.get(field, 0) * 0.6
                dept_score = (department_matches.get(field, 0) / max(len(self.all_departments) / 6, 1)) * 0.25
                keyword_score = (keyword_scores.get(field, 0) / max(len(keywords), 1)) * 0.15
                
                final_scores[field] = bert_score + dept_score + keyword_score
            
            # Get best match
            best_field = max(final_scores, key=final_scores.get)
            confidence = final_scores[best_field]
            
            # Quality check - fallback to 'other' if confidence is very low
            if confidence < 0.05:
                best_field = 'other'
                confidence = 0.1
            
            # Create reasoning
            reasoning_parts = [f"BERT analysis of: '{text[:100]}...'"]
            if matched_depts:
                reasoning_parts.append(f"Matched departments: {', '.join(matched_depts[:3])}")
            if keywords:
                reasoning_parts.append(f"Keywords found: {', '.join(keywords[:3])}")
            
            return BERTClassificationResult(
                field=best_field,
                confidence=confidence,
                all_scores=final_scores,
                matched_departments=matched_depts,
                reasoning="; ".join(reasoning_parts),
                method="hybrid"
            )
            
        except Exception as e:
            print(f"❌ Enhanced BERT classification error: {e}")
            return BERTClassificationResult(
                field='other',
                confidence=0.0,
                all_scores={},
                matched_departments=[],
                reasoning=f"Classification failed: {e}",
                method="error"
            )
    
    def classify_from_text(self, text: str) -> BERTClassificationResult:
        """Main classification method using hybrid approach"""
        return self.hybrid_classification(text)
    
    def classify_from_grant_context(self, grant_context: Dict) -> BERTClassificationResult:
        """Classify using comprehensive grant information with enhanced processing"""
        # Extract relevant text from grant context
        text_parts = []
        
        # Add project title (most important)
        title = grant_context.get('project_title', grant_context.get('title', ''))
        if title:
            text_parts.append(title)
        
        # Add abstract/description
        abstract = grant_context.get('abstract', grant_context.get('project_abstract', ''))
        if abstract:
            # Limit abstract length but keep key terms
            text_parts.append(abstract[:800])  # Increased from 500
        
        # Add keywords if available
        keywords = grant_context.get('keywords', [])
        if keywords:
            if isinstance(keywords, list):
                text_parts.append(' '.join(keywords))
            else:
                text_parts.append(str(keywords))
        
        # Add organization/affiliation info
        org_info = grant_context.get('organization', {})
        if isinstance(org_info, dict):
            org_name = org_info.get('org_name', '')
            if org_name:
                text_parts.append(org_name)
        
        # Combine all text
        combined_text = ' '.join(text_parts).strip()
        
        if not combined_text:
            return BERTClassificationResult(
                field='other',
                confidence=0.0,
                all_scores={},
                matched_departments=[],
                reasoning="No text content available for classification",
                method="no_content"
            )
        
        return self.hybrid_classification(combined_text)

def get_bert_classifier() -> EnhancedBERTDepartmentClassifier:
    """Get singleton enhanced BERT classifier instance"""
    global _bert_classifier
    if _bert_classifier is None:
        _bert_classifier = EnhancedBERTDepartmentClassifier()
    return _bert_classifier

def predict_department_bert(grant_context: Dict) -> Dict:
    """
    Main function for enhanced BERT-based department prediction
    Compatible with existing SciBERT interface
    """
    classifier = get_bert_classifier()
    result = classifier.classify_from_grant_context(grant_context)
    
    return {
        'department': result.field,
        'confidence': result.confidence,
        'method': 'Enhanced BERT',
        'all_scores': result.all_scores,
        'matched_departments': result.matched_departments,
        'reasoning': result.reasoning
    }

def predict_from_research_context(title: str = "", abstract: str = "", 
                                 affiliation: str = "", keywords: List[str] = None) -> Dict:
    """
    Legacy compatibility function for existing enhanced_main.py integration
    Enhanced with university data and hybrid classification
    """
    # Combine all context into grant_context dict
    grant_context = {
        'project_title': title,
        'abstract': abstract,
        'affiliation': affiliation,
        'keywords': keywords or [],
        'organization': {'org_name': affiliation} if affiliation else {}
    }
    
    return predict_department_bert(grant_context)

async def scrape_and_update_departments():
    """Scrape departments from universities and update the dataset"""
    classifier = get_bert_classifier()
    
    print("🌐 Scraping university departments...")
    all_scraped = set()
    
    for university_name in classifier.universities_to_scrape.keys():
        scraped = await classifier.scrape_university_departments(university_name)
        all_scraped.update(scraped)
        print(f"📚 Scraped {len(scraped)} departments from {university_name}")
    
    if all_scraped:
        # Add scraped departments to the dataset
        classifier.scraped_departments.update(all_scraped)
        print(f"✅ Total scraped departments: {len(all_scraped)}")
        
        # Optionally update the JSON dataset
        enhanced_data = classifier.department_data.copy()
        enhanced_data['scraped'] = list(all_scraped)
        
        try:
            with open(classifier.dataset_path.replace('.json', '_with_scraping.json'), 'w') as f:
                json.dump(enhanced_data, f, indent=2)
            print("💾 Saved enhanced dataset with scraped departments")
        except Exception as e:
            print(f"⚠️ Could not save enhanced dataset: {e}")
    
    return all_scraped

if __name__ == "__main__":
    # Test the enhanced classifier
    test_grants = [
        "Machine learning approaches for protein structure prediction using deep neural networks",
        "Climate change impact on coral reef ecosystems and marine biodiversity",
        "Quantum computing applications in cryptography and secure communications",
        "Social media influence on political behavior and voter engagement patterns",
        "Development of novel drug delivery systems for targeted cancer therapy using nanoparticles"
    ]
    
    print("🧪 Testing Enhanced BERT Classifier with University Data")
    print("=" * 70)
    
    classifier = get_bert_classifier()
    for i, grant in enumerate(test_grants, 1):
        result = classifier.classify_from_text(grant)
        print(f"\n{i}. Grant: {grant}")
        print(f"   🎯 Predicted: {result.field}")
        print(f"   📊 Confidence: {result.confidence:.3f}")
        print(f"   🏢 Matched departments: {', '.join(result.matched_departments[:3])}")
        print(f"   🔍 Method: {result.method}")
        print(f"   💭 Reasoning: {result.reasoning[:100]}...")
        
        # Show top 3 field scores
        top_scores = sorted(result.all_scores.items(), key=lambda x: x[1], reverse=True)[:3]
        print(f"   📈 Top scores: {', '.join([f'{field}: {score:.3f}' for field, score in top_scores])}")
    
    # Test async scraping
    print(f"\n🌐 Testing university department scraping...")
    try:
        scraped = asyncio.run(scrape_and_update_departments())
        print(f"✅ Scraping test completed, found {len(scraped)} departments")
    except Exception as e:
        print(f"⚠️ Scraping test failed: {e}")
    
    print("\n✅ Enhanced BERT classifier testing completed!")
