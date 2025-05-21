# LinkedIn MCP Server

A FastMCP server that provides tools for LinkedIn automation, including job search and feed monitoring capabilities.

## Prerequisites

- Python 3.10 or higher
- Docker (optional, for containerized deployment)
- LinkedIn account credentials

## Environment Setup

1. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
export LINKEDIN_EMAIL="your-email@example.com"
export LINKEDIN_PASSWORD="your-password"
```

## Running the Server

### Local Development

1. Start the MCP server:
```bash
python main.py
```

The server will start on `http://localhost:8000` with SSE transport.

### Docker Deployment

1. Build the Docker image:
```bash
docker build -t linkedin-mcp .
```

2. Run the container:
```bash
docker run -p 8000:8000 \
  -e LINKEDIN_EMAIL="your-email@example.com" \
  -e LINKEDIN_PASSWORD="your-password" \
  linkedin-mcp
```

## Testing the Server

### Using the Client Scripts

1. Test job search functionality:
```bash
python client.py
```

2. Test feed monitoring:
```bash
# Basic usage (fetches 5 posts by default)
python client_feed.py "Python"

# Specify number of posts to fetch
python client_feed.py "Machine Learning" --max-posts 10
```

## Available Tools

### 1. Login Tool
```python
@mcp.tool()
async def login() -> Dict[str, str]
```
Authenticates with LinkedIn using credentials from environment variables.
- Returns: Dictionary with login status and message
- Requires: LINKEDIN_EMAIL and LINKEDIN_PASSWORD environment variables

### 2. Search Jobs Tool
```python
@mcp.tool()
async def search_jobs(query: str, location: str, max_jobs: int = 3) -> List[Dict[str, str]]
```
Searches LinkedIn jobs with enhanced data extraction.
- Parameters:
  - query: Job search keywords
  - location: Location to search in
  - max_jobs: Maximum number of jobs to return (default: 3)
- Returns: List of job details including title, company, location, and description

### 3. Fetch Feed Tool
```python
@mcp.tool()
async def fetch_feed(topic: str, max_posts: int = 5) -> List[str]
```
Scrapes recent LinkedIn feed posts related to a specific topic.
- Parameters:
  - topic: The topic to search for in feed posts
  - max_posts: Maximum number of posts to return (default: 5)
- Returns: List of post contents matching the topic

## Error Handling

The server includes comprehensive error handling for:
- Authentication failures
- Network issues
- Page loading timeouts
- Content extraction errors

## Security Notes

1. Never commit your LinkedIn credentials to version control
2. Use environment variables for sensitive information
3. The server uses secure storage for authentication state
4. All tools require authentication before use

## Troubleshooting

1. If login fails:
   - Verify your credentials
   - Check if LinkedIn is blocking automated access
   - Try clearing the storage.json file

2. If feed fetching fails:
   - Ensure you're properly authenticated
   - Check the feed_debug.png screenshot for visual debugging
   - Verify your network connection

3. If job search fails:
   - Verify the search parameters
   - Check if the location is valid
   - Ensure you're properly authenticated

## Contributing

Feel free to submit issues and enhancement requests!
