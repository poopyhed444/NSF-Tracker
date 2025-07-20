"""
SciBERT-based Department Classifier Module

This module provides a neural classifier for determining academic departments
based on research text (titles, abstracts, affiliations) using SciBERT embeddings.
"""

import json
import os
import pickle
import numpy as np
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from sentence_transformers import SentenceTransformer
from sklearn.neighbors import KNeighborsClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics.pairwise import cosine_similarity
import torch

class SciBERTDepartmentClassifier:
    """SciBERT-based department classifier with multiple ML backends."""
    
    _lock = threading.Lock()
    _instance = None
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        if not getattr(self, '_initialized', False):
            self.model_name = "allenai/scibert_scivocab_uncased"
            self.cache_dir = Path(__file__).parent / "scibert_cache"
            self.cache_dir.mkdir(exist_ok=True)
            
            # Department categories for classification
            self.departments = [
                "Biology", "Chemistry", "Physics", "Mathematics", "Computer Science",
                "Engineering", "Medicine", "Neuroscience", "Psychology", 
                "Immunology", "Oncology", "Cardiology", "Materials Science",
                "Environmental Science", "Economics", "Sociology", "Education"
            ]
            
            self.model = None
            self.embeddings = None
            self.labels = None
            self.classifier = None
            self.confidence_threshold = 0.3
            
            self._initialized = True
    
    def _load_model(self):
        """Load SciBERT model (lazy loading)."""
        if self.model is None:
            print("Loading SciBERT model...")
            self.model = SentenceTransformer(self.model_name)
            print("SciBERT model loaded successfully")
    
    def _load_training_data(self) -> Tuple[List[str], List[str]]:
        """Load training data from enhanced dataset and cache."""
        texts, labels = [], []
        
        # First, try to load enhanced training data
        enhanced_data_file = Path(__file__).parent / "enhanced_training_data.json"
        if enhanced_data_file.exists():
            try:
                with open(enhanced_data_file, 'r', encoding='utf-8') as f:
                    enhanced_data = json.load(f)
                texts.extend(enhanced_data.get('texts', []))
                labels.extend(enhanced_data.get('labels', []))
                print(f"Loaded {len(texts)} examples from enhanced training data")
            except Exception as e:
                print(f"Error loading enhanced training data: {e}")
        
        # Also load from existing PI cache for recent successful lookups
        cache_file = Path(__file__).parent / "pi_department_cache.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                
                cache_examples = 0
                for key, entry in cache_data.items():
                    if (entry.get('department', '').lower() != 'unknown' and 
                        entry.get('source') in ['orcid', 'crossref'] and 
                        entry.get('confidence') == 'high'):
                        
                        # Extract PI name and institution from key
                        pi_name, institution = key.split('|', 1)
                        department = entry['department']
                        
                        # Create training text from available info
                        training_text = f"{pi_name} {institution} researcher {department}"
                        texts.append(training_text)
                        labels.append(department)
                        cache_examples += 1
                
                print(f"Added {cache_examples} examples from PI cache")
            except Exception as e:
                print(f"Error loading cache data: {e}")
        
        # If no enhanced data, fall back to basic synthetic examples
        if not texts:
            print("No training data found, creating basic synthetic examples...")
            synthetic_examples = self._create_basic_synthetic_examples()
            for text, label in synthetic_examples:
                texts.append(text)
                labels.append(label)
        
        return texts, labels
    
    def _create_basic_synthetic_examples(self) -> List[Tuple[str, str]]:
        """Create basic synthetic examples if no other data available."""
        examples = []
        
        basic_patterns = {
            "Biology": [
                "protein structure function research",
                "genetic analysis molecular biology",
                "cell biology developmental processes",
                "biochemistry enzyme studies",
                "microbiology bacterial research"
            ],
            "Chemistry": [
                "organic synthesis chemical reactions",
                "analytical chemistry spectroscopy",
                "physical chemistry thermodynamics",
                "medicinal chemistry drug discovery",
                "materials chemistry polymer research"
            ],
            "Physics": [
                "quantum mechanics theoretical physics",
                "condensed matter physics research",
                "particle physics accelerator studies",
                "astrophysics cosmic phenomena",
                "optics laser technology"
            ],
            "Engineering": [
                "mechanical engineering design",
                "electrical engineering circuits",
                "biomedical engineering devices",
                "chemical engineering processes",
                "computer engineering systems"
            ],
            "Computer Science": [
                "machine learning algorithms",
                "artificial intelligence systems",
                "software engineering development",
                "computer vision processing",
                "database systems design"
            ],
            "Medicine": [
                "clinical medicine patient care",
                "medical research disease treatment",
                "surgical procedures techniques",
                "diagnostic medicine imaging",
                "pharmaceutical drug therapy"
            ],
            "Neuroscience": [
                "brain function neural activity",
                "cognitive neuroscience behavior",
                "neurological disorders research",
                "synaptic transmission mechanisms",
                "behavioral neuroscience studies"
            ],
            "Psychology": [
                "cognitive psychology research",
                "behavioral psychology studies",
                "clinical psychology therapy",
                "developmental psychology growth",
                "social psychology interactions"
            ]
        }
        
        for dept, patterns in basic_patterns.items():
            for pattern in patterns:
                examples.append((pattern, dept))
        
        return examples
    
    def train_classifier(self, force_retrain: bool = False):
        """Train the department classifier."""
        model_cache_file = self.cache_dir / "classifier_model.pkl"
        embeddings_cache_file = self.cache_dir / "embeddings.npy"
        labels_cache_file = self.cache_dir / "labels.json"
        
        # Load cached model if available and not forcing retrain
        if not force_retrain and all(f.exists() for f in [model_cache_file, embeddings_cache_file, labels_cache_file]):
            print("Loading cached classifier...")
            with open(model_cache_file, 'rb') as f:
                self.classifier = pickle.load(f)
            self.embeddings = np.load(embeddings_cache_file)
            with open(labels_cache_file, 'r') as f:
                self.labels = json.load(f)
            print("Cached classifier loaded successfully")
            return
        
        print("Training new classifier...")
        self._load_model()
        
        # Get training data
        texts, labels = self._load_training_data()
        
        if not texts:
            print("No training data available")
            return
        
        print(f"Training on {len(texts)} examples across {len(set(labels))} departments")
        
        # Generate embeddings
        print("Generating embeddings...")
        embeddings = self.model.encode(texts, convert_to_tensor=False, show_progress_bar=True)
        
        # Train multiple classifiers and choose the best
        classifiers = {
            'knn': KNeighborsClassifier(n_neighbors=min(5, len(texts)//2), metric='cosine'),
            'rf': RandomForestClassifier(n_estimators=100, random_state=42),
            'lr': LogisticRegression(max_iter=1000, random_state=42)
        }
        
        best_classifier = None
        best_score = 0
        
        for name, clf in classifiers.items():
            try:
                clf.fit(embeddings, labels)
                # Simple validation score (you could use cross-validation here)
                score = clf.score(embeddings, labels)
                print(f"{name} accuracy: {score:.3f}")
                
                if score > best_score:
                    best_score = score
                    best_classifier = clf
            except Exception as e:
                print(f"Error training {name}: {e}")
        
        if best_classifier is None:
            print("Failed to train any classifier")
            return
        
        self.classifier = best_classifier
        self.embeddings = embeddings
        self.labels = labels
        
        # Cache the trained model
        print("Caching trained model...")
        with open(model_cache_file, 'wb') as f:
            pickle.dump(self.classifier, f)
        np.save(embeddings_cache_file, embeddings)
        with open(labels_cache_file, 'w') as f:
            json.dump(labels, f)
        
        print(f"Classifier trained successfully with accuracy: {best_score:.3f}")
    
    def predict_department(self, text: str, return_confidence: bool = True) -> Dict[str, any]:
        """
        Predict department from text using SciBERT classifier.
        
        Args:
            text: Input text (research description, affiliation, etc.)
            return_confidence: Whether to return confidence scores
            
        Returns:
            Dict with prediction results
        """
        if self.classifier is None:
            self.train_classifier()
        
        if self.classifier is None:
            return {
                'department': 'Unknown',
                'confidence': 0.0,
                'source': 'scibert_failed'
            }
        
        self._load_model()
        
        # Generate embedding for input text
        text_embedding = self.model.encode([text], convert_to_tensor=False)
        
        try:
            # Get prediction
            prediction = self.classifier.predict(text_embedding)[0]
            
            # Get confidence score
            if hasattr(self.classifier, 'predict_proba'):
                probabilities = self.classifier.predict_proba(text_embedding)[0]
                confidence = float(np.max(probabilities))
            else:
                # For KNN, use cosine similarity to nearest neighbors
                similarities = cosine_similarity(text_embedding, self.embeddings)[0]
                top_indices = np.argsort(similarities)[-5:]  # Top 5 similar
                top_labels = [self.labels[i] for i in top_indices]
                
                # Confidence based on label agreement in top neighbors
                label_counts = {}
                for label in top_labels:
                    label_counts[label] = label_counts.get(label, 0) + 1
                
                confidence = float(label_counts.get(prediction, 0) / len(top_labels))
            
            # Apply confidence threshold
            if confidence < self.confidence_threshold:
                prediction = 'Unknown'
                source = 'scibert_low_confidence'
            else:
                source = 'scibert'
            
            result = {
                'department': prediction,
                'confidence': confidence,
                'source': source
            }
            
            if return_confidence:
                result['raw_confidence'] = confidence
            
            return result
            
        except Exception as e:
            print(f"Error in SciBERT prediction: {e}")
            return {
                'department': 'Unknown',
                'confidence': 0.0,
                'source': 'scibert_error'
            }
    
    def predict_from_multiple_sources(self, 
                                    title: str = "", 
                                    abstract: str = "", 
                                    affiliation: str = "",
                                    keywords: List[str] = None) -> Dict[str, any]:
        """
        Predict department from multiple text sources.
        
        Args:
            title: Paper/research title
            abstract: Research abstract
            affiliation: Author affiliation
            keywords: Research keywords
            
        Returns:
            Prediction results with combined confidence
        """
        if keywords is None:
            keywords = []
        
        # Combine all available text
        text_parts = []
        if title:
            text_parts.append(f"Title: {title}")
        if abstract:
            text_parts.append(f"Abstract: {abstract}")
        if affiliation:
            text_parts.append(f"Affiliation: {affiliation}")
        if keywords:
            text_parts.append(f"Keywords: {' '.join(keywords)}")
        
        combined_text = " ".join(text_parts)
        
        if not combined_text.strip():
            return {
                'department': 'Unknown',
                'confidence': 0.0,
                'source': 'no_text'
            }
        
        return self.predict_department(combined_text)

# Global classifier instance
_classifier = SciBERTDepartmentClassifier()

def predict_department_scibert(text: str) -> Dict[str, any]:
    """Convenience function for department prediction."""
    return _classifier.predict_department(text)

def predict_from_research_context(title: str = "", 
                                abstract: str = "", 
                                affiliation: str = "",
                                keywords: List[str] = None) -> Dict[str, any]:
    """Convenience function for multi-source prediction."""
    return _classifier.predict_from_multiple_sources(title, abstract, affiliation, keywords)

def train_classifier(force_retrain: bool = False):
    """Train the global classifier."""
    _classifier.train_classifier(force_retrain)

if __name__ == "__main__":
    # Test the classifier
    train_classifier(force_retrain=True)
    
    test_cases = [
        "protein folding molecular dynamics simulation",
        "machine learning neural networks deep learning",
        "cancer immunotherapy t cell activation",
        "quantum computing algorithms optimization",
        "cardiac electrophysiology arrhythmia treatment"
    ]
    
    for test_text in test_cases:
        result = predict_department_scibert(test_text)
        print(f"Text: {test_text}")
        print(f"Predicted: {result['department']} (confidence: {result['confidence']:.3f})")
        print()
