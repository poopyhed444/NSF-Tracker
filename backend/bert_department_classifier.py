#!/usr/bin/env python3
"""
BERT-based Department Classifier for Grant Descriptions
Uses SciBERT or similar models optimized for scientific text classification.
"""

import json
import re
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import torch
from transformers import AutoTokenizer, AutoModel
import torch.nn.functional as F
from collections import defaultdict

@dataclass
class ClassificationResult:
    field: str
    confidence: float
    matched_departments: List[str]
    reasoning: str
    embeddings: Optional[np.ndarray] = None

class BERTDepartmentClassifier:
    def __init__(self, model_name: str = "allenai/scibert_scivocab_uncased"):
        """
        Initialize BERT-based classifier for scientific grant descriptions.
        
        Args:
            model_name: HuggingFace model name (SciBERT recommended for scientific text)
        """
        self.model_name = model_name
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        print(f"🤖 Initializing BERT classifier with {model_name}")
        print(f"📱 Using device: {self.device}")
        
        # Load model and tokenizer
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModel.from_pretrained(model_name, trust_remote_code=False)
            self.model.to(self.device)
            self.model.eval()
            print("✅ BERT model loaded successfully")
        except Exception as e:
            print(f"❌ Failed to load {model_name}: {e}")
            print("🔄 Falling back to distilbert-base-uncased")
            self.model_name = "distilbert-base-uncased"
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModel.from_pretrained(self.model_name, trust_remote_code=False)
            self.model.to(self.device)
            self.model.eval()
        
        # Load department dataset
        self.load_department_data()
        
        # Pre-compute embeddings for department descriptions
        self.compute_department_embeddings()
        
    def load_department_data(self):
        """Load department data and create field descriptions"""
        try:
            with open('enhanced_department_dataset.json', 'r') as f:
                self.department_data = json.load(f)
        except FileNotFoundError:
            print("⚠️ Department dataset not found, using basic set")
            self.department_data = self.create_basic_dataset()
        
        # Create detailed field descriptions for better BERT matching
        self.field_descriptions = {
            'engineering': {
                'description': 'Engineering, computer science, software development, systems design, technology innovation, artificial intelligence, machine learning, robotics, automation, infrastructure, telecommunications, aerospace, mechanical, electrical, chemical, biomedical, civil engineering, materials science, nanotechnology',
                'keywords': ['engineering', 'computer science', 'software', 'technology', 'AI', 'machine learning', 'robotics', 'automation', 'telecommunications', 'aerospace', 'mechanical', 'electrical', 'chemical', 'biomedical', 'civil', 'materials', 'nanotechnology']
            },
            'medical_sciences': {
                'description': 'Medicine, healthcare, clinical research, biomedical sciences, public health, epidemiology, pharmacology, pathology, medical devices, drug development, clinical trials, patient care, disease treatment, diagnostic methods, therapeutic interventions, medical imaging, surgery, nursing, dentistry',
                'keywords': ['medicine', 'medical', 'clinical', 'healthcare', 'biomedical', 'health', 'disease', 'patient', 'treatment', 'therapy', 'drug', 'pharmaceutical', 'epidemiology', 'pathology', 'surgery', 'nursing', 'dentistry']
            },
            'biological_sciences': {
                'description': 'Biology, life sciences, genetics, molecular biology, cell biology, biochemistry, biotechnology, ecology, evolution, neuroscience, microbiology, immunology, developmental biology, structural biology, systems biology, bioinformatics, genomics, proteomics',
                'keywords': ['biology', 'biological', 'genetics', 'molecular', 'cell', 'biochemistry', 'biotechnology', 'ecology', 'evolution', 'neuroscience', 'microbiology', 'immunology', 'genomics', 'proteomics', 'bioinformatics']
            },
            'physical_sciences': {
                'description': 'Physics, chemistry, mathematics, statistics, astronomy, earth sciences, materials science, quantum mechanics, thermodynamics, electromagnetism, optics, spectroscopy, crystallography, computational science, theoretical physics, applied mathematics, geophysics, atmospheric science',
                'keywords': ['physics', 'chemistry', 'mathematics', 'statistics', 'astronomy', 'quantum', 'materials', 'computational', 'theoretical', 'geophysics', 'atmospheric', 'spectroscopy']
            },
            'social_sciences': {
                'description': 'Psychology, sociology, economics, political science, anthropology, education, linguistics, cognitive science, behavioral science, social work, public policy, international relations, communication, media studies, cultural studies, urban planning',
                'keywords': ['psychology', 'sociology', 'economics', 'political', 'anthropology', 'education', 'linguistics', 'cognitive', 'behavioral', 'social', 'policy', 'communication', 'cultural']
            }
        }
        
        print(f"📚 Loaded {sum(len(depts) for depts in self.department_data.values())} departments across {len(self.field_descriptions)} fields")
    
    def create_basic_dataset(self):
        """Create basic department dataset"""
        return {
            'engineering': [
                'Computer Science', 'Electrical Engineering', 'Mechanical Engineering',
                'Chemical Engineering', 'Biomedical Engineering', 'Civil Engineering',
                'Aerospace Engineering', 'Materials Engineering', 'Software Engineering'
            ],
            'medical_sciences': [
                'Medicine', 'Public Health', 'Biomedical Sciences', 'Clinical Medicine',
                'Pharmacology', 'Pathology', 'Epidemiology', 'Medical Research'
            ],
            'biological_sciences': [
                'Biology', 'Genetics', 'Molecular Biology', 'Cell Biology',
                'Neuroscience', 'Ecology', 'Microbiology', 'Biochemistry'
            ],
            'physical_sciences': [
                'Physics', 'Chemistry', 'Mathematics', 'Statistics',
                'Astronomy', 'Earth Sciences', 'Materials Science'
            ],
            'social_sciences': [
                'Psychology', 'Economics', 'Political Science', 'Sociology',
                'Anthropology', 'Education', 'Linguistics'
            ]
        }
    
    def get_bert_embeddings(self, text: str) -> np.ndarray:
        """Get BERT embeddings for text"""
        # Truncate text if too long
        if len(text) > 500:
            text = text[:500]
        
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512
        )
        
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            # Use CLS token embedding (first token)
            embeddings = outputs.last_hidden_state[:, 0, :].cpu().numpy()
        
        return embeddings[0]
    
    def compute_department_embeddings(self):
        """Pre-compute embeddings for all field descriptions"""
        print("🧠 Computing BERT embeddings for field descriptions...")
        
        self.field_embeddings = {}
        for field, data in self.field_descriptions.items():
            # Combine description with department names for richer context
            field_text = data['description']
            if field in self.department_data:
                dept_names = ', '.join(self.department_data[field][:10])  # Use top 10 dept names
                field_text += f". Common departments: {dept_names}"
            
            embedding = self.get_bert_embeddings(field_text)
            self.field_embeddings[field] = embedding
        
        print("✅ Field embeddings computed")
    
    def cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    
    def classify_grant_description(self, grant_text: str, grant_title: str = "", pi_info: str = "") -> ClassificationResult:
        """
        Classify a grant based on its description, title, and PI information.
        
        Args:
            grant_text: Grant description/abstract
            grant_title: Grant title (optional)
            pi_info: PI name and affiliation info (optional)
        
        Returns:
            ClassificationResult with field classification
        """
        # Combine all available text
        combined_text = f"{grant_title} {grant_text} {pi_info}".strip()
        
        # Get BERT embedding for the grant
        grant_embedding = self.get_bert_embeddings(combined_text)
        
        # Calculate similarities with each field
        field_scores = {}
        for field, field_embedding in self.field_embeddings.items():
            similarity = self.cosine_similarity(grant_embedding, field_embedding)
            field_scores[field] = similarity
        
        # Find best match
        best_field = max(field_scores, key=field_scores.get)
        confidence = field_scores[best_field]
        
        # Get relevant departments for the classified field
        matched_departments = []
        if best_field in self.department_data:
            # Use keyword matching to find most relevant departments within the field
            field_depts = self.department_data[best_field]
            text_lower = combined_text.lower()
            
            dept_relevance = []
            for dept in field_depts:
                dept_lower = dept.lower()
                # Check if department name appears in text
                if dept_lower in text_lower:
                    dept_relevance.append((dept, 2.0))  # High relevance
                else:
                    # Check for keyword overlap
                    dept_words = set(dept_lower.split())
                    text_words = set(text_lower.split())
                    overlap = len(dept_words.intersection(text_words))
                    if overlap > 0:
                        dept_relevance.append((dept, overlap))
            
            # Sort by relevance and take top matches
            dept_relevance.sort(key=lambda x: x[1], reverse=True)
            matched_departments = [dept for dept, _ in dept_relevance[:5]]
            
            # If no matches found, use top departments from field
            if not matched_departments:
                matched_departments = field_depts[:3]
        
        # Create reasoning
        confidence_level = "high" if confidence > 0.8 else "medium" if confidence > 0.6 else "low"
        reasoning = f"BERT semantic analysis with {confidence_level} confidence. "
        
        if grant_title:
            reasoning += f"Analyzed grant title and description. "
        if pi_info:
            reasoning += f"Included PI affiliation context. "
        
        reasoning += f"Top field similarities: {', '.join([f'{field}: {score:.3f}' for field, score in sorted(field_scores.items(), key=lambda x: x[1], reverse=True)[:3]])}"
        
        return ClassificationResult(
            field=best_field,
            confidence=confidence,
            matched_departments=matched_departments,
            reasoning=reasoning,
            embeddings=grant_embedding
        )
    
    def classify_department_name(self, department_name: str, institution: str = "") -> ClassificationResult:
        """
        Classify a department name using BERT embeddings.
        Backward compatibility method for existing code.
        """
        context_text = f"{department_name} at {institution}".strip() if institution else department_name
        return self.classify_grant_description(context_text)

# Create global instance
bert_classifier = BERTDepartmentClassifier()

def classify_grant_text(grant_text: str, title: str = "", pi_info: str = "") -> ClassificationResult:
    """Convenience function for grant classification"""
    return bert_classifier.classify_grant_description(grant_text, title, pi_info)

def classify_department(dept_name: str) -> ClassificationResult:
    """Convenience function for backward compatibility"""
    return bert_classifier.classify_department_name(dept_name)
