#!/usr/bin/env python3
"""
Debug script to test the layoff leaderboard endpoint error
"""

import asyncio
import traceback
import sys
import os

async def debug_leaderboard_error():
    """Debug the specific layoff leaderboard error"""
    
    try:
        print("🔍 Testing layoff leaderboard function directly...")
        
        # Import the function
        from layoff_estimator import generate_layoff_risk_leaderboard
        
        print("✅ Successfully imported generate_layoff_risk_leaderboard")
        
        # Call the function with same parameters as endpoint
        print("📊 Calling generate_layoff_risk_leaderboard(200000, 25)...")
        result = await generate_layoff_risk_leaderboard(cost_per_researcher=200000, limit=25)
        
        print("✅ Function completed successfully!")
        print(f"Result keys: {list(result.keys())}")
        
        if 'data' in result:
            print(f"Number of institutions: {len(result['data'])}")
        
        if 'error' in result:
            print(f"⚠️ Function returned error: {result['error']}")
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        traceback.print_exc()
    except Exception as e:
        print(f"❌ Error during execution: {e}")
        print("Full traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_leaderboard_error())
