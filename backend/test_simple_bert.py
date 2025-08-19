#!/usr/bin/env python3
"""
Simple BERT-based classifier with fallback to TF-IDF
"""

import sys
import os
sys.path.append('/Users/minervagao/Desktop/NSF-Tracker/backend')

def test_simple_bert():
    print("🔬 Testing Simple BERT Classification for Grant Descriptions")
    print("=" * 70)
    
    try:
        # Try to load BERT classifier
        print("🤖 Attempting to load BERT classifier...")
        from sentence_transformers import SentenceTransformer
        import numpy as np
        
        # Use a smaller, faster model
        model = SentenceTransformer('all-MiniLM-L6-v2')
        print("✅ BERT model loaded successfully!")
        
        # Field descriptions for semantic matching
        field_descriptions = {
            'engineering': 'computer science software engineering technology artificial intelligence machine learning robotics',
            'medical_sciences': 'medicine medical clinical health biomedical disease treatment therapy drug pharmaceutical',
            'biological_sciences': 'biology genetics molecular cell biochemistry ecology neuroscience microbiology',
            'physical_sciences': 'physics chemistry mathematics statistics astronomy quantum materials computational',
            'social_sciences': 'psychology sociology economics political anthropology education linguistics behavioral'
        }
        
        # Pre-compute field embeddings
        print("🧠 Computing field embeddings...")
        field_embeddings = {}
        for field, description in field_descriptions.items():
            field_embeddings[field] = model.encode(description)
        
        # Test grants
        test_grants = [
            "Machine learning approaches for protein structure prediction using deep neural networks",
            "Climate change impact on coral reef ecosystems and marine biodiversity",
            "Quantum computing applications in cryptography and secure communications",
            "Social media influence on political behavior and voter engagement",
            "Gene therapy for rare genetic disorders using CRISPR technology"
        ]
        
        print("\n🧪 Classification Results:")
        print("-" * 50)
        
        for i, grant_text in enumerate(test_grants, 1):
            print(f"\n{i}. Grant: {grant_text}")
            
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
            
            print(f"   🎯 Classified as: {best_field}")
            print(f"   📊 Confidence: {confidence:.3f}")
            print(f"   📈 All scores: {', '.join([f'{field}: {score:.3f}' for field, score in similarities.items()])}")
        
        print("\n✅ BERT classification completed successfully!")
        return True
        
    except ImportError:
        print("⚠️ sentence-transformers not available, installing...")
        import subprocess
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "sentence-transformers"])
            print("✅ Installed sentence-transformers, please run the test again")
            return False
        except:
            print("❌ Could not install sentence-transformers")
            return False
    except Exception as e:
        print(f"❌ Error with BERT classifier: {e}")
        print("🔄 Falling back to TF-IDF approach...")
        
        # Fallback to TF-IDF
        try:
            from lightweight_classifier import enhanced_classifier
            
            test_grants = [
                "Machine learning approaches for protein structure prediction using deep neural networks",
                "Climate change impact on coral reef ecosystems and marine biodiversity", 
                "Quantum computing applications in cryptography and secure communications",
                "Social media influence on political behavior and voter engagement",
                "Gene therapy for rare genetic disorders using CRISPR technology"
            ]
            
            print("\n📊 TF-IDF Classification Results:")
            print("-" * 50)
            
            for i, grant_text in enumerate(test_grants, 1):
                print(f"\n{i}. Grant: {grant_text}")
                
                result = enhanced_classifier.classify_department(grant_text)
                print(f"   🎯 Classified as: {result.field}")
                print(f"   📊 Confidence: {result.confidence:.3f}")
                print(f"   🏢 Top departments: {', '.join(result.matched_departments[:2])}")
            
            print("\n✅ TF-IDF fallback completed!")
            return True
            
        except Exception as fallback_error:
            print(f"❌ Fallback also failed: {fallback_error}")
            return False

if __name__ == "__main__":
    test_simple_bert()
