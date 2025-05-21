from fastmcp import FastMCP, Context
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import json
import os
from typing import List, Dict, Optional
from urllib.parse import quote

# Initialize FastMCP server
mcp = FastMCP("LinkedIn MCP Server")

def check_auth() -> bool:
    """Check if authentication file exists and is valid"""
    return os.path.exists("storage.json")

@mcp.tool()
async def login() -> Dict[str, str]:
    """
    Logs into LinkedIn using credentials from environment variables.
    Requires LINKEDIN_EMAIL and LINKEDIN_PASSWORD environment variables to be set.
    
    Returns:
        Dictionary with login status
    """
    email = os.getenv("LINKEDIN_EMAIL")
    password = os.getenv("LINKEDIN_PASSWORD")
    
    if not email or not password:
        return {
            "status": "error",
            "message": "LinkedIn credentials not found in environment variables. Please set LINKEDIN_EMAIL and LINKEDIN_PASSWORD."
        }
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)  # Use headless=False for login
            context = await browser.new_context()
            page = await context.new_page()
            
            # Navigate to LinkedIn login
            await page.goto("https://www.linkedin.com/login")
            
            # Fill in login form
            await page.fill("#username", email)
            await page.fill("#password", password)
            
            # Click login button
            await page.click("button[type='submit']")
            
            # Wait for navigation and check for successful login
            try:
                await page.wait_for_selector("div.feed-shared-update-v2", timeout=10000)
                # Save authentication state
                await context.storage_state(path="storage.json")
                await browser.close()
                return {"status": "success", "message": "Successfully logged in to LinkedIn"}
            except PlaywrightTimeoutError:
                # Check for error messages
                error_elem = await page.query_selector(".alert-content")
                if error_elem:
                    error_msg = await error_elem.inner_text()
                    await browser.close()
                    return {"status": "error", "message": f"Login failed: {error_msg}"}
                else:
                    await browser.close()
                    return {"status": "error", "message": "Login failed: Could not verify successful login"}
                    
    except Exception as e:
        return {"status": "error", "message": f"Login error: {str(e)}"}

@mcp.tool()
async def fetch_feed(topic: str, max_posts: int = 5) -> List[str]:
    """
    Scrapes recent LinkedIn feed posts related to a specific topic.
    
    Args:
        topic: The topic to search for in feed posts
        max_posts: Maximum number of posts to return (default: 5)
    
    Returns:
        List of post contents matching the topic
    """
    if not check_auth():
        raise Exception("Not authenticated. Please login first.")
    
    try:
        async with async_playwright() as p:
            # Launch browser with specific arguments to avoid detection
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--disable-site-isolation-trials',
                    '--no-sandbox',
                    '--disable-setuid-sandbox'
                ]
            )
            
            # Create context with specific settings
            context = await browser.new_context(
                storage_state="storage.json",
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                ignore_https_errors=True
            )
            
            page = await context.new_page()
            
            # Navigate to feed with retry
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    print(f"Attempting to load feed (attempt {attempt + 1}/{max_retries})")
                    
                    # First navigate to LinkedIn home to ensure we're logged in
                    await page.goto("https://www.linkedin.com/", wait_until="networkidle")
                    await page.wait_for_timeout(2000)
                    
                    # Check if we need to re-authenticate
                    if await page.query_selector("input#username"):
                        print("Session expired, need to re-authenticate")
                        raise Exception("Session expired")
                    
                    # Now navigate to feed
                    await page.goto("https://www.linkedin.com/feed/", wait_until="networkidle")
                    await page.wait_for_timeout(5000)  # Wait longer for initial load
                    
                    # Try multiple selectors that indicate we're on the feed page
                    feed_indicators = [
                        "div.feed-shared-update-v2",
                        "div.feed-identity-module",
                        "div.feed-shared-control-menu",
                        "div.feed-shared-text-view"
                    ]
                    
                    found_indicator = False
                    for selector in feed_indicators:
                        try:
                            await page.wait_for_selector(selector, timeout=5000)
                            print(f"Found feed indicator: {selector}")
                            found_indicator = True
                            break
                        except PlaywrightTimeoutError:
                            continue
                    
                    if not found_indicator:
                        # Take a screenshot for debugging
                        await page.screenshot(path="feed_debug.png")
                        raise Exception("No feed indicators found")
                    
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise Exception(f"Failed to load LinkedIn feed after multiple attempts: {str(e)}")
                    print(f"Attempt {attempt + 1} failed: {str(e)}")
                    await page.wait_for_timeout(2000)
                    continue

            # Scroll to load more content
            print("Scrolling to load more content...")
            for _ in range(3):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(3000)  # Wait longer between scrolls

            # Wait for content to load after scrolling
            await page.wait_for_timeout(5000)

            posts = await page.query_selector_all("div.feed-shared-update-v2")
            print(f"Found {len(posts)} posts")
            results = []
            
            for post in posts:
                try:
                    text = await post.inner_text()
                    if topic.lower() in text.lower():
                        # Extract more structured data
                        author = await post.query_selector("span.feed-shared-actor__name")
                        author_name = await author.inner_text() if author else "Unknown"
                        
                        content = text[:300].replace('\n', ' ')
                        results.append(f"{author_name}: {content}")
                        
                        if len(results) >= max_posts:
                            break
                except Exception as e:
                    print(f"Error processing post: {str(e)}")
                    continue
                    
            await browser.close()
            print(f"Successfully processed {len(results)} posts")
            return results
            
    except Exception as e:
        raise Exception(f"Error fetching LinkedIn feed: {str(e)}")

@mcp.tool()
async def search_jobs(query: str, location: str, max_jobs: int = 3) -> List[Dict[str, str]]:
    """
    Searches LinkedIn jobs with enhanced data extraction.
    
    Args:
        query: Job search keywords
        location: Location to search in
        max_jobs: Maximum number of jobs to return (default: 3)
    
    Returns:
        List of job details including title, company, location, and description
    """
    if not check_auth():
        raise Exception("Not authenticated. Please login first.")
    
    try:
        async with async_playwright() as p:
            # Launch browser with specific arguments to avoid detection
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--disable-site-isolation-trials'
                ]
            )
            
            # Create context with specific settings
            context = await browser.new_context(
                storage_state="storage.json",
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
            
            # Create new page
            page = await context.new_page()
            
            # Construct and navigate to search URL
            search_url = f"https://www.linkedin.com/jobs/search/?keywords={quote(query)}&location={quote(location)}"
            print(f"Navigating to: {search_url}")
            
            # Navigate with retry
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # Navigate to the page and wait for network to be idle
                    await page.goto(search_url, wait_until="networkidle")
                    print(f"Waiting for job cards... (attempt {attempt + 1}/{max_retries})")
                    
                    # Wait for either the job cards or the "no results" message
                    try:
                        await page.wait_for_selector("div.base-search-card__info", timeout=15000)
                        print("Job cards found!")
                    except PlaywrightTimeoutError:
                        # Check if we got a "no results" message
                        no_results = await page.query_selector("div.jobs-search-no-results-banner")
                        if no_results:
                            print("No jobs found matching the criteria")
                            await browser.close()
                            return []
                        raise  # Re-raise if it's not a "no results" case
                    
                    break
                except PlaywrightTimeoutError:
                    if attempt == max_retries - 1:
                        raise Exception("Failed to load LinkedIn jobs after multiple attempts")
                    print(f"Attempt {attempt + 1} failed, retrying...")
                    continue

            # Scroll to load more content
            print("Scrolling to load more content...")
            for _ in range(2):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(2000)

            # Wait for job cards to be fully loaded
            await page.wait_for_timeout(2000)
            
            jobs = await page.query_selector_all("div.base-search-card__info")
            print(f"Found {len(jobs)} job cards")
            results = []
            
            for i, job in enumerate(jobs[:max_jobs]):
                try:
                    print(f"\nProcessing job {i + 1}/{min(max_jobs, len(jobs))}")
                    
                    # Extract structured data with better error handling
                    title_elem = await job.query_selector("h3.base-search-card__title")
                    company_elem = await job.query_selector("h4.base-search-card__subtitle")
                    location_elem = await job.query_selector("span.job-search-card__location")
                    
                    job_data = {
                        "title": await title_elem.inner_text() if title_elem else "Unknown",
                        "company": await company_elem.inner_text() if company_elem else "Unknown",
                        "location": await location_elem.inner_text() if location_elem else "Unknown",
                    }
                    
                    # Try to get job description
                    try:
                        job_link = await job.query_selector("a.base-card__full-link")
                        if job_link:
                            job_url = await job_link.get_attribute("href")
                            if job_url:
                                print(f"Fetching description from: {job_url}")
                                # Open job in new page
                                job_page = await context.new_page()
                                try:
                                    await job_page.goto(job_url, wait_until="networkidle")
                                    await job_page.wait_for_selector("div.show-more-less-html__markup", timeout=5000)
                                    desc_elem = await job_page.query_selector("div.show-more-less-html__markup")
                                    if desc_elem:
                                        job_data["description"] = (await desc_elem.inner_text())[:500] + "..."
                                except Exception as e:
                                    print(f"Error fetching job description: {str(e)}")
                                finally:
                                    await job_page.close()
                    except Exception as e:
                        print(f"Error processing job link: {str(e)}")
                    
                    results.append(job_data)
                    print(f"Successfully processed job {i + 1}")
                    
                except Exception as e:
                    print(f"Error processing job {i + 1}: {str(e)}")
                    continue
                    
            await browser.close()
            print(f"\nSuccessfully processed {len(results)} jobs")
            return results
            
    except Exception as e:
        print(f"Error in search_jobs: {str(e)}")
        raise Exception(f"Error searching LinkedIn jobs: {str(e)}")

if __name__ == "__main__":
    # Run the server with SSE transport
    mcp.run(transport="sse", host="0.0.0.0", port=8000)