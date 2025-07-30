print("--- Script starting ---")
# test_federal_grants.py
import asyncio
import time
from layoff_estimator import fetch_dod_grants, fetch_doe_grants

async def test_grant_fetching():
    print("===== TESTING DOD GRANT FETCHING =====")
    start_time = time.time()
    
    try:
        print("Fetching DoD grants...")
        dod_grants = await fetch_dod_grants(max_records=10)
        print(f"✅ SUCCESS: Got {len(dod_grants)} DoD grants")
        print(f"Time taken: {time.time() - start_time:.2f} seconds")
        
        if dod_grants:
            print("\nSample DoD grant:")
            sample = dod_grants[0]
            print(f"  Title: {sample.get('project_title', 'N/A')}")
            print(f"  Amount: ${sample.get('award_amount', 0):,.2f}")
            print(f"  Organization: {sample.get('organization', [{}])[0].get('org_name', 'N/A')}")
            print(f"  Source: {sample.get('source', 'N/A')}")
    except Exception as e:
        print(f"❌ ERROR with DoD grants: {str(e)}")
    
    print("\n===== TESTING DOE GRANT FETCHING =====")
    start_time = time.time()
    
    try:
        print("Fetching DoE grants...")
        doe_grants = await fetch_doe_grants(max_records=10)
        print(f"✅ SUCCESS: Got {len(doe_grants)} DoE grants")
        print(f"Time taken: {time.time() - start_time:.2f} seconds")
        
        if doe_grants:
            print("\nSample DoE grant:")
            sample = doe_grants[0]
            print(f"  Title: {sample.get('project_title', 'N/A')}")
            print(f"  Amount: ${sample.get('award_amount', 0):,.2f}")
            print(f"  Organization: {sample.get('organization', [{}])[0].get('org_name', 'N/A')}")
            print(f"  Source: {sample.get('source', 'N/A')}")
    except Exception as e:
        print(f"❌ ERROR with DoE grants: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_grant_fetching())