#!/usr/bin/env python3
"""
Test the enhanced SciBERT classifier
"""

import sys
import os
sys.path.append('/Users/minervagao/Desktop/NSF-Tracker/backend')

from enhanced_scibert_classifier import EnhancedSciBERTClassifier

def test_enhanced_classifier():
    print("🔬 Testing Enhanced SciBERT Classifier...")
    
    try:
        # Initialize classifier
        classifier = EnhancedSciBERTClassifier()
        print("✅ Classifier initialized successfully")
        
        # Test cases
        test_cases = [
            "Department of Computer Science and Engineering at Stanford University",
            "Biomedical Engineering laboratory studying neural networks",
            "Chemistry department researching molecular dynamics",
            "Physics research on quantum computing applications",
            "Department of Medicine, Cardiology Division",
            "School of Psychology and Cognitive Science"
        ]
        
        print("\n🧪 Testing classification on sample texts:")
        print("-" * 50)
        
        for i, text in enumerate(test_cases, 1):
            result = classifier.classify_department(text)
            print(f"\n{i}. Text: {text[:60]}...")
            print(f"   Field: {result.field}")
            print(f"   Confidence: {result.confidence:.3f}")
            print(f"   Matched Departments: {', '.join(result.matched_departments[:3])}")
            print(f"   Reasoning: {result.reasoning[:100]}...")
        
        print("\n✅ Enhanced classifier test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing classifier: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_enhanced_classifier()
