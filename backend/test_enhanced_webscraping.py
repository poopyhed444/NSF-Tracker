#!/usr/bin/env python3
"""
Test the enhanced classifier with webscraping capabilities
"""

import asyncio
import sys
import os
sys.path.append('/Users/minervagao/Desktop/NSF-Tracker/backend')

from lightweight_classifier import EnhancedLightweightClassifier

async def test_webscraping_classifier():
    print("🔬 Testing Enhanced Classifier with Web Scraping...")
    
    try:
        # Initialize classifier
        classifier = EnhancedLightweightClassifier()
        print("✅ Enhanced classifier initialized successfully")
        
        # Test basic classification first
        test_text = "Department of Computer Science and Artificial Intelligence"
        result = classifier.classify_department(test_text)
        print(f"\n🧪 Basic Test: {test_text}")
        print(f"   Field: {result.field}")
        print(f"   Confidence: {result.confidence:.3f}")
        
        # Test webscraping enhancement (with a small test)
        print("\n🕷️ Testing department data enhancement...")
        print("   Note: This will make web requests, so it may take a moment...")
        
        # Get current department count
        original_count = sum(len(depts) for depts in classifier.department_data.values())
        print(f"   Original department count: {original_count}")
        
        # Run enhancement (this will scrape web data)
        await classifier.enhance_department_dataset()
        
        # Get new department count
        new_count = sum(len(depts) for depts in classifier.department_data.values())
        print(f"   New department count: {new_count}")
        print(f"   Added {new_count - original_count} departments")
        
        # Test classification again with enhanced data
        result2 = classifier.classify_department(test_text)
        print(f"\n🧪 Enhanced Test: {test_text}")
        print(f"   Field: {result2.field}")
        print(f"   Confidence: {result2.confidence:.3f}")
        
        print("\n✅ Enhanced classifier with webscraping test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing enhanced classifier: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test_webscraping_classifier())
