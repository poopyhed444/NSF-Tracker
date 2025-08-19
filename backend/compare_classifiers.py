#!/usr/bin/env python3
"""
Comparison test between BERT and Enhanced SciBERT (TF-IDF) classifiers
"""

import sys
import os
sys.path.append('/Users/minervagao/Desktop/NSF-Tracker/backend')

def compare_classifiers():
    print("🔬 BERT vs Enhanced SciBERT Classifier Comparison")
    print("=" * 70)
    
    # Test grant descriptions
    test_grants = [
        ("Machine learning approaches for protein structure prediction using deep neural networks", "engineering"),
        ("Climate change impact on coral reef ecosystems and marine biodiversity", "biological_sciences"),
        ("Quantum computing applications in cryptography and secure communications", "physical_sciences"),
        ("Social media influence on political behavior and voter engagement", "social_sciences"),
        ("Gene therapy for rare genetic disorders using CRISPR technology", "medical_sciences"),
        ("Statistical methods for analyzing large-scale genomic data", "mathematical_sciences"),
        ("Development of sustainable materials for renewable energy applications", "engineering"),
        ("Behavioral economics and decision-making under uncertainty", "social_sciences"),
        ("Novel drug delivery systems for cancer treatment", "medical_sciences"),
        ("Artificial intelligence in autonomous vehicle navigation", "engineering")
    ]
    
    # Test 1: BERT Classification
    print("\n🤖 BERT Classification Results:")
    print("-" * 50)
    
    bert_results = []
    try:
        from sentence_transformers import SentenceTransformer
        import numpy as np
        
        # Load BERT model
        model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Field descriptions for semantic matching
        field_descriptions = {
            'engineering': 'computer science software engineering technology artificial intelligence machine learning robotics automation systems',
            'medical_sciences': 'medicine medical clinical health biomedical disease treatment therapy drug pharmaceutical cancer',
            'biological_sciences': 'biology genetics molecular cell biochemistry ecology neuroscience microbiology evolution organism',
            'physical_sciences': 'physics chemistry mathematics statistics astronomy quantum materials computational theory',
            'social_sciences': 'psychology sociology economics political anthropology education linguistics behavioral social human',
            'mathematical_sciences': 'mathematics statistics data analysis computational modeling algorithms numerical methods'
        }
        
        # Pre-compute field embeddings
        field_embeddings = {}
        for field, description in field_descriptions.items():
            field_embeddings[field] = model.encode(description)
        
        bert_correct = 0
        for i, (grant_text, expected_field) in enumerate(test_grants, 1):
            # Get grant embedding
            grant_embedding = model.encode(grant_text)
            
            # Calculate similarities
            similarities = {}
            for field, field_embedding in field_embeddings.items():
                similarity = np.dot(grant_embedding, field_embedding) / (
                    np.linalg.norm(grant_embedding) * np.linalg.norm(field_embedding)
                )
                similarities[field] = similarity
            
            # Get best match
            best_field = max(similarities, key=similarities.get)
            confidence = similarities[best_field]
            
            is_correct = best_field == expected_field
            if is_correct:
                bert_correct += 1
            
            print(f"{i:2d}. {'✅' if is_correct else '❌'} {grant_text[:60]}...")
            print(f"    Expected: {expected_field} | Predicted: {best_field} | Confidence: {confidence:.3f}")
            
            bert_results.append({
                'text': grant_text,
                'expected': expected_field,
                'predicted': best_field,
                'confidence': confidence,
                'correct': is_correct
            })
        
        bert_accuracy = bert_correct / len(test_grants)
        print(f"\n🎯 BERT Accuracy: {bert_accuracy:.1%} ({bert_correct}/{len(test_grants)})")
        
    except Exception as e:
        print(f"❌ BERT classification failed: {e}")
        bert_results = []
        bert_accuracy = 0
    
    # Test 2: Enhanced SciBERT (TF-IDF) Classification
    print("\n📊 Enhanced SciBERT (TF-IDF) Classification Results:")
    print("-" * 50)
    
    tfidf_results = []
    try:
        from enhanced_scibert_classifier import EnhancedSciBERTClassifier
        
        classifier = EnhancedSciBERTClassifier()
        
        tfidf_correct = 0
        for i, (grant_text, expected_field) in enumerate(test_grants, 1):
            result = classifier.classify_department(grant_text)
            
            is_correct = result.field == expected_field
            if is_correct:
                tfidf_correct += 1
            
            print(f"{i:2d}. {'✅' if is_correct else '❌'} {grant_text[:60]}...")
            print(f"    Expected: {expected_field} | Predicted: {result.field} | Confidence: {result.confidence:.3f}")
            
            tfidf_results.append({
                'text': grant_text,
                'expected': expected_field,
                'predicted': result.field,
                'confidence': result.confidence,
                'correct': is_correct
            })
        
        tfidf_accuracy = tfidf_correct / len(test_grants)
        print(f"\n🎯 Enhanced SciBERT Accuracy: {tfidf_accuracy:.1%} ({tfidf_correct}/{len(test_grants)})")
        
    except Exception as e:
        print(f"❌ Enhanced SciBERT classification failed: {e}")
        tfidf_results = []
        tfidf_accuracy = 0
    
    # Comparison Summary
    print("\n📈 COMPARISON SUMMARY")
    print("=" * 70)
    
    if bert_results and tfidf_results:
        print(f"🤖 BERT Accuracy:              {bert_accuracy:.1%}")
        print(f"📊 Enhanced SciBERT Accuracy:  {tfidf_accuracy:.1%}")
        
        if bert_accuracy > tfidf_accuracy:
            diff = bert_accuracy - tfidf_accuracy
            print(f"🏆 BERT wins by {diff:.1%}")
        elif tfidf_accuracy > bert_accuracy:
            diff = tfidf_accuracy - bert_accuracy
            print(f"🏆 Enhanced SciBERT wins by {diff:.1%}")
        else:
            print("🤝 Tie!")
        
        # Detailed comparison
        print("\n🔍 Detailed Analysis:")
        for i, (grant_text, expected) in enumerate(test_grants):
            if i < len(bert_results) and i < len(tfidf_results):
                bert_pred = bert_results[i]['predicted']
                tfidf_pred = tfidf_results[i]['predicted']
                
                if bert_pred != tfidf_pred:
                    print(f"\n{i+1}. Different predictions for: {grant_text[:50]}...")
                    print(f"   Expected: {expected}")
                    print(f"   BERT: {bert_pred} ({'✅' if bert_pred == expected else '❌'})")
                    print(f"   TF-IDF: {tfidf_pred} ({'✅' if tfidf_pred == expected else '❌'})")
    
    print("\n✅ Comparison completed!")

if __name__ == "__main__":
    compare_classifiers()
