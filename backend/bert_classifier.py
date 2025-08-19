#!/usr/bin/env python3
"""
BERT-based Department Classifier for NSF-Tracker
High-performance classification using sentence-transformers
"""

import os
import json
from typing import Dict, List, Optional, Union
from dataclasses import dataclass
import numpy as np

# Global classifier instance
_bert_classifier = None

@dataclass
class BERTClassificationResult:
    field: str
    confidence: float
    all_scores: Dict[str, float]
    reasoning: str

class BERTDepartmentClassifier:
    """BERT-based classifier using sentence-transformers for semantic analysis"""
    
    def __init__(self):
        self.model = None
        self.field_embeddings = {}
        self.field_descriptions = {
            'engineering': 'computer science software engineering technology artificial intelligence machine learning robotics automation systems programming algorithms',
            'medical_sciences': 'medicine medical clinical health biomedical disease treatment therapy drug pharmaceutical cancer biology healthcare',
            'biological_sciences': 'biology genetics molecular cell biochemistry ecology neuroscience microbiology evolution organism life sciences',
            'physical_sciences': 'physics chemistry mathematics statistics astronomy quantum materials computational theory science research',
            'social_sciences': 'psychology sociology economics political anthropology education linguistics behavioral social human society',
            'mathematical_sciences': 'mathematics statistics data analysis computational modeling algorithms numerical methods applied math'
        }
        self._initialize()
    
    def _initialize(self):
        """Initialize the BERT model and pre-compute field embeddings"""
        try:
            from sentence_transformers import SentenceTransformer
            print("🤖 Loading BERT model for department classification...")
            
            # Use a lightweight but effective model
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Pre-compute field embeddings for efficiency
            print("🧠 Computing field embeddings...")
            for field, description in self.field_descriptions.items():
                self.field_embeddings[field] = self.model.encode(description)
            
            print(f"✅ BERT classifier initialized with {len(self.field_embeddings)} fields")
            
        except ImportError:
            print("⚠️ sentence-transformers not available, BERT classification disabled")
            self.model = None
        except Exception as e:
            print(f"❌ Error initializing BERT classifier: {e}")
            self.model = None
    
    def classify_from_text(self, text: str) -> BERTClassificationResult:
        """Classify department based on text content (grant title, abstract, etc.)"""
        if not self.model or not text or len(text.strip()) < 5:
            return BERTClassificationResult(
                field='other',
                confidence=0.0,
                all_scores={},
                reasoning="BERT model not available or text too short"
            )
        
        try:
            # Get text embedding
            text_embedding = self.model.encode(text.strip())
            
            # Calculate similarities with each field
            similarities = {}
            for field, field_embedding in self.field_embeddings.items():
                similarity = np.dot(text_embedding, field_embedding) / (
                    np.linalg.norm(text_embedding) * np.linalg.norm(field_embedding)
                )
                similarities[field] = float(similarity)
            
            # Get best match
            best_field = max(similarities, key=similarities.get)
            confidence = similarities[best_field]
            
            # Fallback to 'other' if confidence is very low
            if confidence < 0.05:
                best_field = 'other'
                confidence = 0.1
            
            return BERTClassificationResult(
                field=best_field,
                confidence=confidence,
                all_scores=similarities,
                reasoning=f"BERT semantic analysis of: '{text[:100]}...'"
            )
            
        except Exception as e:
            print(f"❌ BERT classification error: {e}")
            return BERTClassificationResult(
                field='other',
                confidence=0.0,
                all_scores={},
                reasoning=f"Classification failed: {e}"
            )
    
    def classify_from_grant_context(self, grant_context: Dict) -> BERTClassificationResult:
        """Classify using comprehensive grant information"""
        # Extract relevant text from grant context
        text_parts = []
        
        # Add project title (most important)
        title = grant_context.get('project_title', grant_context.get('title', ''))
        if title:
            text_parts.append(title)
        
        # Add abstract/description
        abstract = grant_context.get('abstract', grant_context.get('project_abstract', ''))
        if abstract:
            # Limit abstract length to avoid overwhelming the model
            text_parts.append(abstract[:500])
        
        # Add keywords if available
        keywords = grant_context.get('keywords', [])
        if keywords:
            if isinstance(keywords, list):
                text_parts.append(' '.join(keywords))
            else:
                text_parts.append(str(keywords))
        
        # Combine all text
        combined_text = ' '.join(text_parts).strip()
        
        if not combined_text:
            return BERTClassificationResult(
                field='other',
                confidence=0.0,
                all_scores={},
                reasoning="No text content available for classification"
            )
        
        return self.classify_from_text(combined_text)

def get_bert_classifier() -> BERTDepartmentClassifier:
    """Get singleton BERT classifier instance"""
    global _bert_classifier
    if _bert_classifier is None:
        _bert_classifier = BERTDepartmentClassifier()
    return _bert_classifier

def predict_department_bert(grant_context: Dict) -> Dict:
    """
    Main function for BERT-based department prediction
    Compatible with existing SciBERT interface
    """
    classifier = get_bert_classifier()
    result = classifier.classify_from_grant_context(grant_context)
    
    return {
        'department': result.field,
        'confidence': result.confidence,
        'method': 'BERT',
        'all_scores': result.all_scores,
        'reasoning': result.reasoning
    }

def predict_from_research_context(title: str = "", abstract: str = "", 
                                 affiliation: str = "", keywords: List[str] = None) -> Dict:
    """
    Legacy compatibility function for existing enhanced_main.py integration
    """
    # Combine all context into grant_context dict
    grant_context = {
        'project_title': title,
        'abstract': abstract,
        'affiliation': affiliation,
        'keywords': keywords or []
    }
    
    return predict_department_bert(grant_context)

if __name__ == "__main__":
    # Test the classifier
    test_grants = [
        "Machine learning approaches for protein structure prediction using deep neural networks",
        "Climate change impact on coral reef ecosystems and marine biodiversity",
        "Quantum computing applications in cryptography and secure communications"
    ]
    
    classifier = get_bert_classifier()
    for grant in test_grants:
        result = classifier.classify_from_text(grant)
        print(f"Text: {grant}")
        print(f"Predicted: {result.field} (confidence: {result.confidence:.3f})")
        print()
