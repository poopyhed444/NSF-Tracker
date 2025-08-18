#!/usr/bin/env python3
"""
Test the lightweight classifier
"""

import sys
import os
sys.path.append('/Users/minervagao/Desktop/NSF-Tracker/backend')

from lightweight_classifier import enhanced_classifier

def test_lightweight_classifier():
    print("🔬 Testing Lightweight Department Classifier...")
    
    try:
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
            result = enhanced_classifier.classify_department(text)
            print(f"\n{i}. Text: {text[:60]}...")
            print(f"   Field: {result.field}")
            print(f"   Confidence: {result.confidence:.3f}")
            print(f"   Matched Departments: {', '.join(result.matched_departments[:3])}")
            print(f"   Reasoning: {result.reasoning}")
        
        print("\n✅ Lightweight classifier test completed successfully!")
        print("🚀 No PyTorch dependencies required!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing classifier: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_lightweight_classifier()
