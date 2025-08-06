import asyncio
import httpx
import logging

async def lookup_pi_by_award_id(award_id):
    """Simple PI lookup using NIH REPORTER API."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            payload = {
                "criteria": {"award_nums": [award_id]},
                "include_fields": ["ContactPiName", "OtherPiNames"],
                "offset": 0, "limit": 10
            }
            response = await client.post(
                "https://api.reporter.nih.gov/v2/projects/search",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                if results:
                    pi_name = results[0].get("contact_pi_name")
                    if pi_name:
                        return pi_name
    except Exception as e:
        print(f"Error: {e}")
    return None

async def test_lookup():
    result = await lookup_pi_by_award_id("U19AI057229")
    print(f"PI found: {result}")

if __name__ == "__main__":
    asyncio.run(test_lookup())
