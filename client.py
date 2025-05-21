from fastmcp import Client
import asyncio
import json
import time
import os

async def retry_with_backoff(func, max_retries=3, initial_delay=1):
    """Retry a function with exponential backoff"""
    delay = initial_delay
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            print(f"Attempt {attempt + 1} failed: {str(e)}")
            print(f"Retrying in {delay} seconds...")
            await asyncio.sleep(delay)
            delay *= 2

def parse_response(response):
    """Parse the response content from TextContent objects"""
    if isinstance(response, list):
        return [parse_response(item) for item in response]
    elif hasattr(response, 'text'):
        try:
            return json.loads(response.text)
        except json.JSONDecodeError:
            return response.text
    return response

async def main():
    # Check for environment variables
    if not os.getenv("LINKEDIN_EMAIL") or not os.getenv("LINKEDIN_PASSWORD"):
        print("Error: LinkedIn credentials not found in environment variables.")
        print("Please set LINKEDIN_EMAIL and LINKEDIN_PASSWORD environment variables.")
        return

    async with Client("http://127.0.0.1:8000/sse") as client:
        try:
            # Login first
            print("Attempting to login...")
            result = await retry_with_backoff(
                lambda: client.call_tool("login", {})
            )
            parsed_result = parse_response(result)
            print("Login result:", parsed_result)
            
            # Wait a bit after login to ensure session is established
            print("Waiting for session to be established...")
            await asyncio.sleep(3)
            
            # Then use other tools
            print("\nSearching for jobs...")
            jobs = await retry_with_backoff(
                lambda: client.call_tool("search_jobs", {
                    "query": "Python Developer",
                    "location": "New York",
                    "max_jobs": 3
                })
            )
            
            parsed_jobs = parse_response(jobs)
            if not parsed_jobs:
                print("No jobs found matching the criteria")
            else:
                print(f"\nFound {len(parsed_jobs)} jobs:")
                for i, job in enumerate(parsed_jobs, 1):
                    print(f"\nJob {i}:")
                    print(json.dumps(job, indent=2))
                    
        except Exception as e:
            print(f"Error: {str(e)}")
            if hasattr(e, 'response'):
                print(f"Response: {e.response}")

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())