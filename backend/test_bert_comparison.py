#!/usr/bin/env python3
"""
Test and compare BERT-based classifier vs TF-IDF classifier
"""

import sys
import os
sys.path.append('/Users/minervagao/Desktop/NSF-Tracker/backend')

from bert_department_classifier import bert_classifier
from lightweight_classifier import enhanced_classifier

def test_bert_vs_tfidf():
    print("🔬 Comparing BERT vs TF-IDF Classifiers for Grant Descriptions")
    print("=" * 70)
    
    # Sample grant descriptions (realistic examples)
    test_grants = [
        {
            "title": "Machine Learning Approaches for Protein Structure Prediction",
            "description": "This research aims to develop novel deep learning algorithms for predicting protein folding patterns. We will use convolutional neural networks and transformer architectures to analyze amino acid sequences and predict three-dimensional protein structures. The work involves computational biology, structural bioinformatics, and artificial intelligence methodologies.",
            "pi_info": "Dr. Sarah Chen, Department of Computer Science, Stanford University"
        },
        {
            "title": "Climate Change Impact on Coral Reef Ecosystems",
            "description": "Investigation of how rising ocean temperatures and acidification affect coral reef biodiversity. This longitudinal study will monitor coral bleaching events, marine species population dynamics, and ecosystem resilience over a 5-year period. Field research will be conducted in the Great Barrier Reef and Caribbean marine protected areas.",
            "pi_info": "Dr. Michael Rodriguez, Marine Biology Institute, University of Miami"
        },
        {
            "title": "Quantum Computing Applications in Cryptography",
            "description": "Development of quantum algorithms for breaking classical encryption methods and designing quantum-resistant cryptographic protocols. This theoretical and experimental research explores quantum entanglement, superposition principles, and quantum error correction for secure communication systems.",
            "pi_info": "Dr. Lisa Wang, Department of Physics, MIT"
        },
        {
            "title": "Social Media Influence on Political Behavior",
            "description": "Comprehensive analysis of how social media platforms shape political opinions and voting behavior among young adults. This interdisciplinary study combines survey methodology, social network analysis, and behavioral economics to understand digital democracy and political engagement patterns.",
            "pi_info": "Dr. James Thompson, Department of Political Science, Harvard University"
        },
        {
            "title": "Gene Therapy for Rare Genetic Disorders",
            "description": "Clinical trial investigating CRISPR-Cas9 gene editing techniques for treating muscular dystrophy. This translational research involves developing viral vectors for gene delivery, conducting safety assessments, and evaluating therapeutic efficacy in patient populations with inherited muscle diseases.",
            "pi_info": "Dr. Amanda Foster, School of Medicine, Johns Hopkins University"
        }
    ]
    
    print("\n🧪 Testing Classification Results:")
    print("-" * 70)
    
    for i, grant in enumerate(test_grants, 1):
        print(f"\n{i}. Grant: {grant['title'][:50]}...")
        print(f"   Description: {grant['description'][:100]}...")
        
        # Test BERT classifier
        bert_result = bert_classifier.classify_grant_description(
            grant['description'], 
            grant['title'], 
            grant['pi_info']
        )
        
        # Test TF-IDF classifier (using combined text)
        combined_text = f"{grant['title']} {grant['description']}"
        tfidf_result = enhanced_classifier.classify_department(combined_text)
        
        print(f"\n   🤖 BERT Result:")
        print(f"      Field: {bert_result.field}")
        print(f"      Confidence: {bert_result.confidence:.3f}")
        print(f"      Departments: {', '.join(bert_result.matched_departments[:2])}")
        print(f"      Reasoning: {bert_result.reasoning[:80]}...")
        
        print(f"\n   📊 TF-IDF Result:")
        print(f"      Field: {tfidf_result.field}")
        print(f"      Confidence: {tfidf_result.confidence:.3f}")
        print(f"      Departments: {', '.join(tfidf_result.matched_departments[:2])}")
        
        # Compare results
        if bert_result.field == tfidf_result.field:
            print(f"   ✅ Both agree on field: {bert_result.field}")
        else:
            print(f"   ⚠️ Different classifications: BERT={bert_result.field}, TF-IDF={tfidf_result.field}")
    
    print("\n" + "=" * 70)
    print("🎯 Analysis Summary:")
    print("• BERT classifier: Better at understanding semantic context and scientific language")
    print("• TF-IDF classifier: Faster, good for keyword-based department matching")
    print("• For grant descriptions: BERT recommended due to complex scientific terminology")
    print("• For simple department names: TF-IDF may be sufficient and faster")

if __name__ == "__main__":
    test_bert_vs_tfidf()
