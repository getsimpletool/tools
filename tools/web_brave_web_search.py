from simpletool import SimpleTool, SimpleInputModel, Field, Dict, Any, List, Optional
from simpletool.types import TextContent, ErrorContent
import httpx
import asyncio
from datetime import datetime

# Rate limiting configuration
RATE_LIMIT = 1  # Requests per second
LAST_REQUEST_TIME = None


class InputModel(SimpleInputModel):
    """Input model for Brave Web Search."""
    query: str = Field(
        description="Search query (max 400 chars, 50 words)",
        max_length=400
    )
    count: int = Field(
        default=10,
        description="Number of results (1-20, default 10)",
        ge=1,
        le=20
    )
    offset: Optional[int] = Field(
        default=0,
        description="Pagination offset (max 9, default 0)",
        ge=0,
        le=9
    )


class WebBraveWebSearchTool(SimpleTool):
    name = "web_brave_web_search"
    description = '''
    Performs a web search using the Brave Search API, ideal for general queries, news, articles, and online content.
    Use this for broad information gathering, recent events, or when you need diverse web sources.
    Supports pagination, content filtering, and freshness controls.
    Maximum 20 results per request, with offset for pagination.
    '''
    input_model = InputModel

    async def run(self, arguments: Dict[str, Any]) -> List[TextContent | ErrorContent]:
        env = self.get_env(arguments, prefix="BRAVE_")
        if not env.get('BRAVE_API_KEY'):
            return [TextContent(type="text", text="Missing required BRAVE_API_KEY environment variables")]

        # Rate limiting
        global LAST_REQUEST_TIME
        if LAST_REQUEST_TIME:
            elapsed = (datetime.now() - LAST_REQUEST_TIME).total_seconds()
            if elapsed < 1 / RATE_LIMIT:
                await asyncio.sleep(1 / RATE_LIMIT - elapsed)
        LAST_REQUEST_TIME = datetime.now()

        arg = InputModel(**arguments)
        query = arg.query
        count = arg.count
        offset = arg.offset

        url = "https://api.search.brave.com/res/v1/web/search"
        params = {
            "q": query,
            "count": min(count, 20),
            "offset": offset
        }

        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": env.get('BRAVE_API_KEY')
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, headers=headers)
            if response.status_code == 429:
                # Rate limit exceeded - implement exponential backoff
                retry_after = int(response.headers.get('Retry-After', 1))
                await asyncio.sleep(retry_after)
                return await self.run(arguments)
            elif response.status_code != 200:
                error_text = response.text
                return [ErrorContent(code=response.status_code, error=f"Brave API error: {response.status_code} {error_text}")]

            data = response.json()
            results = data.get("web", {}).get("results", [])

            return [
                TextContent(
                    type="text",
                    text=f"Title: {result.get('title', '')}\n"
                    f"Description: {result.get('description', '')}\n"
                    f"URL: {result.get('url', '')}"
                )
                for result in results
            ]
