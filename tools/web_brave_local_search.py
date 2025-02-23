from simpletool import SimpleTool, SimpleInputModel, Field, Dict, Any, List, Optional
from simpletool.types import TextContent, ErrorContent
import httpx
import asyncio
from datetime import datetime

# Rate limiting configuration
RATE_LIMIT = 1  # Requests per second
LAST_REQUEST_TIME = None


class InputModel(SimpleInputModel):
    """Input model for Brave Local Search."""
    query: str = Field(
        description="Local search query (e.g. 'pizza near Central Park')"
    )
    count: Optional[int] = Field(
        default=5,
        description="Number of results (1-20, default 5)",
        ge=1,
        le=20
    )


class WebBraveLocalSearchTool(SimpleTool):
    name = "web_brave_local_search"
    description = '''Searches for local businesses and places using Brave's Local Search API.
    Best for queries related to physical locations, businesses, restaurants, services, etc.
    Returns detailed information including:
    - Business names and addresses
    - Ratings and review counts
    - Phone numbers and opening hours
    Use this when the query implies 'near me' or mentions specific locations.
    Automatically falls back to web search if no local results are found.
    '''
    input_model = InputModel

    def __init__(self) -> None:
        super().__init__()
        self.env = {}

    async def run(self, arguments: Dict[str, Any]) -> List[TextContent | ErrorContent]:
        try:
            self.env = self.get_env(arguments, prefix="BRAVE_")
            if not self.env.get('BRAVE_API_KEY'):
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
            count = int(arg.count) if arg.count is not None else 5

            if not query:
                return [TextContent(type="text", text="Missing required argument: query")]

            # First get location IDs
            web_url = "https://api.search.brave.com/res/v1/web/search"
            web_params = {
                "q": query,
                "search_lang": "en",
                "result_filter": "locations",
                "count": min(count, 20)
            }

            headers = {
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": self.env.get('BRAVE_API_KEY')
            }

            async with httpx.AsyncClient() as client:
                # Get location IDs
                response = await client.get(web_url, params=web_params, headers=headers)
                if response.status_code == 429:
                    # Rate limit exceeded - implement exponential backoff
                    retry_after = int(response.headers.get('Retry-After', 1))
                    await asyncio.sleep(retry_after)
                    return await self.run(arguments)
                elif response.status_code != 200:
                    error_text = response.text
                    return [ErrorContent(code=response.status_code, error=f"Brave API error: {response.status_code} {error_text}")]

                web_data = response.json()
                location_ids = [r["id"] for r in web_data.get("locations", {}).get("results", []) if r.get("id")]

                if not location_ids:
                    return await self._perform_web_search(query, count)

                # Get POI details and descriptions in parallel
                poi_url = "https://api.search.brave.com/res/v1/local/pois"
                desc_url = "https://api.search.brave.com/res/v1/local/descriptions"

                poi_params = {"ids": location_ids}
                desc_params = {"ids": location_ids}

                poi_response, desc_response = await asyncio.gather(
                    client.get(poi_url, params=poi_params, headers=headers),
                    client.get(desc_url, params=desc_params, headers=headers)
                )

                if poi_response.status_code != 200:
                    error_text = poi_response.text
                    return [ErrorContent(code=poi_response.status_code, error=f"Brave API error: {poi_response.status_code} {error_text}")]

                if desc_response.status_code != 200:
                    error_text = desc_response.text
                    return [ErrorContent(code=desc_response.status_code, error=f"Brave API error: {desc_response.status_code} {error_text}")]

                pois_data = poi_response.json()
                desc_data = desc_response.json()

                return self._format_local_results(pois_data, desc_data)

        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _perform_web_search(self, query: str, count: int) -> List[TextContent | ErrorContent]:
        """Perform a web search as fallback when no local results are found."""
        url = "https://api.search.brave.com/res/v1/web/search"
        params = {
            "q": query,
            "count": min(count, 20)
        }

        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self.env.get('BRAVE_API_KEY')
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, headers=headers)
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 1))
                await asyncio.sleep(retry_after)
                return await self._perform_web_search(query, count)
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

    def _format_local_results(self, pois_data: dict, desc_data: dict) -> List[TextContent | ErrorContent]:
        results = []
        for poi in pois_data.get("results", []):
            address_parts = [
                poi.get("address", {}).get("streetAddress", ""),
                poi.get("address", {}).get("addressLocality", ""),
                poi.get("address", {}).get("addressRegion", ""),
                poi.get("address", {}).get("postalCode", "")
            ]
            address = ", ".join(filter(None, address_parts)) or "N/A"

            results.append(TextContent(
                type="text",
                text=f"Name: {poi.get('name', 'N/A')}\n"
                     f"Address: {address}\n"
                     f"Phone: {poi.get('phone', 'N/A')}\n"
                     f"Rating: {poi.get('rating', {}).get('ratingValue', 'N/A')} "
                     f"({poi.get('rating', {}).get('ratingCount', 0)} reviews)\n"
                     f"Price Range: {poi.get('priceRange', 'N/A')}\n"
                     f"Hours: {', '.join(poi.get('openingHours', [])) or 'N/A'}\n"
                     f"Description: {desc_data.get('descriptions', {}).get(poi.get('id', ''), 'No description available')}"
            ))

        return results
