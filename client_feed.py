from fastmcp import Client
import asyncio
import json
import time
import os
import argparse

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

async def main(topic: str, max_posts: int):
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
            
            # Fetch feed posts
            print(f"\nFetching feed posts about '{topic}'...")
            posts = await retry_with_backoff(
                lambda: client.call_tool("fetch_feed", {
                    "topic": topic,
                    "max_posts": max_posts
                })
            )
            
            parsed_posts = parse_response(posts)
            if not parsed_posts:
                print("No posts found matching the criteria")
            else:
                print(f"\nFound {len(parsed_posts)} posts:")
                for i, post in enumerate(parsed_posts, 1):
                    print(f"\nPost {i}:")
                    print(json.dumps(post, indent=2))
                    
        except Exception as e:
            print(f"Error: {str(e)}")
            if hasattr(e, 'response'):
                print(f"Response: {e.response}")

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Fetch LinkedIn feed posts about a specific topic')
    parser.add_argument('topic', type=str, help='Topic to search for in feed posts')
    parser.add_argument('--max-posts', type=int, default=5, help='Maximum number of posts to fetch (default: 5)')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Run the async main function with arguments
    asyncio.run(main(args.topic, args.max_posts)) 