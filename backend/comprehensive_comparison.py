#!/usr/bin/env python3
"""
Comprehensive comparison: Enhanced BERT vs TF-IDF vs Original SciBERT
Shows the improvement from integrating university data and BERT
"""

import sys
import os
sys.path.append('/Users/minervagao/Desktop/NSF-Tracker/backend')

def comprehensive_comparison():
    print("🔬 COMPREHENSIVE CLASSIFIER COMPARISON")
    print("=" * 80)
    print("🆚 Enhanced BERT (with university data) vs TF-IDF vs Original SciBERT")
    print("=" * 80)
    
    # Realistic test cases from various domains
    test_grants = [
        {
            "text": "Machine learning approaches for protein structure prediction using deep neural networks and computational biology methods",
            "expected": "biological_sciences",
            "description": "AI + Biology crossover"
        },
        {
            "text": "Climate change impact on coral reef ecosystems and marine biodiversity conservation strategies",
            "expected": "biological_sciences", 
            "description": "Environmental biology"
        },
        {
            "text": "Quantum computing applications in cryptography and secure communications for next-generation networks",
            "expected": "physical_sciences",
            "description": "Quantum physics + CS"
        },
        {
            "text": "Social media influence on political behavior and voter engagement in democratic processes",
            "expected": "social_sciences",
            "description": "Political science"
        },
        {
            "text": "Development of novel drug delivery systems for targeted cancer therapy using nanoparticles",
            "expected": "medical_sciences",
            "description": "Medical nanotechnology"
        },
        {
            "text": "Statistical methods for analyzing large-scale genomic data and population genetics studies",
            "expected": "mathematical_sciences",
            "description": "Statistics + Genomics"
        },
        {
            "text": "Sustainable materials engineering for renewable energy applications and environmental protection",
            "expected": "engineering",
            "description": "Environmental engineering"
        },
        {
            "text": "Behavioral economics and decision-making under uncertainty in financial markets",
            "expected": "social_sciences",
            "description": "Economics + Psychology"
        },
        {
            "text": "CRISPR gene editing technology for treating rare genetic disorders in pediatric patients",
            "expected": "medical_sciences",
            "description": "Medical genetics"
        },
        {
            "text": "Artificial intelligence algorithms for autonomous vehicle navigation and computer vision",
            "expected": "engineering",
            "description": "AI Engineering"
        }
    ]
    
    results = {
        'enhanced_bert': {'correct': 0, 'total': 0, 'details': []},
        'tfidf': {'correct': 0, 'total': 0, 'details': []},
        'original_scibert': {'correct': 0, 'total': 0, 'details': []}
    }
    
    # Test 1: Enhanced BERT with University Data
    print("\n🤖 ENHANCED BERT CLASSIFICATION (with university data)")
    print("-" * 60)
    
    try:
        from bert_classifier import get_bert_classifier
        
        bert_classifier = get_bert_classifier()
        
        for i, test_case in enumerate(test_grants, 1):
            result = bert_classifier.classify_from_text(test_case["text"])
            is_correct = result.field == test_case["expected"]
            
            if is_correct:
                results['enhanced_bert']['correct'] += 1
            results['enhanced_bert']['total'] += 1
            
            print(f"{i:2d}. {'✅' if is_correct else '❌'} {test_case['description']}")
            print(f"    Expected: {test_case['expected']} | Predicted: {result.field} | Confidence: {result.confidence:.3f}")
            print(f"    Matched departments: {', '.join(result.matched_departments[:2])}")
            
            results['enhanced_bert']['details'].append({
                'test': test_case['description'],
                'expected': test_case['expected'],
                'predicted': result.field,
                'confidence': result.confidence,
                'correct': is_correct
            })
        
        bert_accuracy = results['enhanced_bert']['correct'] / results['enhanced_bert']['total']
        print(f"\n🎯 Enhanced BERT Accuracy: {bert_accuracy:.1%} ({results['enhanced_bert']['correct']}/{results['enhanced_bert']['total']})")
        
    except Exception as e:
        print(f"❌ Enhanced BERT test failed: {e}")
        bert_accuracy = 0
    
    # Test 2: TF-IDF Approach
    print("\n📊 TF-IDF CLASSIFICATION (lightweight)")
    print("-" * 60)
    
    try:
        from lightweight_classifier import enhanced_classifier
        
        for i, test_case in enumerate(test_grants, 1):
            result = enhanced_classifier.classify_department(test_case["text"])
            is_correct = result.field == test_case["expected"]
            
            if is_correct:
                results['tfidf']['correct'] += 1
            results['tfidf']['total'] += 1
            
            print(f"{i:2d}. {'✅' if is_correct else '❌'} {test_case['description']}")
            print(f"    Expected: {test_case['expected']} | Predicted: {result.field} | Confidence: {result.confidence:.3f}")
            
            results['tfidf']['details'].append({
                'test': test_case['description'],
                'expected': test_case['expected'],
                'predicted': result.field,
                'confidence': result.confidence,
                'correct': is_correct
            })
        
        tfidf_accuracy = results['tfidf']['correct'] / results['tfidf']['total']
        print(f"\n🎯 TF-IDF Accuracy: {tfidf_accuracy:.1%} ({results['tfidf']['correct']}/{results['tfidf']['total']})")
        
    except Exception as e:
        print(f"❌ TF-IDF test failed: {e}")
        tfidf_accuracy = 0
    
    # Test 3: Original SciBERT (TF-IDF based)
    print("\n🧬 ORIGINAL SCIBERT CLASSIFICATION (TF-IDF based)")
    print("-" * 60)
    
    try:
        from enhanced_scibert_classifier import EnhancedSciBERTClassifier
        
        scibert_classifier = EnhancedSciBERTClassifier()
        
        for i, test_case in enumerate(test_grants, 1):
            result = scibert_classifier.classify_department(test_case["text"])
            is_correct = result.field == test_case["expected"]
            
            if is_correct:
                results['original_scibert']['correct'] += 1
            results['original_scibert']['total'] += 1
            
            print(f"{i:2d}. {'✅' if is_correct else '❌'} {test_case['description']}")
            print(f"    Expected: {test_case['expected']} | Predicted: {result.field} | Confidence: {result.confidence:.3f}")
            
            results['original_scibert']['details'].append({
                'test': test_case['description'],
                'expected': test_case['expected'],
                'predicted': result.field,
                'confidence': result.confidence,
                'correct': is_correct
            })
        
        scibert_accuracy = results['original_scibert']['correct'] / results['original_scibert']['total']
        print(f"\n🎯 Original SciBERT Accuracy: {scibert_accuracy:.1%} ({results['original_scibert']['correct']}/{results['original_scibert']['total']})")
        
    except Exception as e:
        print(f"❌ Original SciBERT test failed: {e}")
        scibert_accuracy = 0
    
    # Final Comparison
    print("\n📈 FINAL COMPARISON SUMMARY")
    print("=" * 80)
    
    if all(results[method]['total'] > 0 for method in results):
        accuracies = {
            'Enhanced BERT (with university data)': results['enhanced_bert']['correct'] / results['enhanced_bert']['total'],
            'TF-IDF (lightweight)': results['tfidf']['correct'] / results['tfidf']['total'],
            'Original SciBERT (TF-IDF)': results['original_scibert']['correct'] / results['original_scibert']['total']
        }
        
        # Sort by accuracy
        sorted_results = sorted(accuracies.items(), key=lambda x: x[1], reverse=True)
        
        print("🏆 RANKING:")
        for rank, (method, accuracy) in enumerate(sorted_results, 1):
            emoji = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉"
            print(f"{emoji} {rank}. {method}: {accuracy:.1%}")
        
        best_method, best_accuracy = sorted_results[0]
        worst_method, worst_accuracy = sorted_results[-1]
        improvement = best_accuracy - worst_accuracy
        
        print(f"\n🚀 IMPROVEMENT: {best_method} outperforms {worst_method} by {improvement:.1%}!")
        
        # Detailed analysis
        print(f"\n🔍 DETAILED ANALYSIS:")
        print(f"   📊 Enhanced BERT: {accuracies['Enhanced BERT (with university data)']:.1%} accuracy")
        print(f"   📈 Uses 303 university departments + live scraping")
        print(f"   🧠 Combines BERT semantic analysis + keyword matching")
        print(f"   ⚡ Hybrid scoring for better accuracy")
        
        print(f"\n   📊 TF-IDF: {accuracies['TF-IDF (lightweight)']:.1%} accuracy") 
        print(f"   📈 Uses enhanced department dataset")
        print(f"   🔤 Traditional TF-IDF + cosine similarity")
        print(f"   💨 Fast but limited semantic understanding")
        
        print(f"\n   📊 Original SciBERT: {accuracies['Original SciBERT (TF-IDF)']:.1%} accuracy")
        print(f"   📈 Uses basic department dataset")
        print(f"   🔤 TF-IDF based (not actual BERT)")
        print(f"   ⚠️ Misleading name - actually TF-IDF")
    
    print("\n✅ Comprehensive comparison completed!")
    
    # Show specific improvements
    if results['enhanced_bert']['total'] > 0 and results['tfidf']['total'] > 0:
        print(f"\n💡 KEY IMPROVEMENTS FROM ENHANCED BERT:")
        
        for i, test_case in enumerate(test_grants):
            bert_result = results['enhanced_bert']['details'][i]
            tfidf_result = results['tfidf']['details'][i]
            
            if bert_result['correct'] and not tfidf_result['correct']:
                print(f"   ✨ {test_case['description']}: Enhanced BERT ✅ vs TF-IDF ❌")
                print(f"      BERT: {bert_result['predicted']} ({bert_result['confidence']:.3f}) | TF-IDF: {tfidf_result['predicted']} ({tfidf_result['confidence']:.3f})")

if __name__ == "__main__":
    comprehensive_comparison()
