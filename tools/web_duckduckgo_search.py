from simpletool import SimpleTool, SimpleInputModel, Field, Dict, Any, List, Optional
from simpletool.types import TextContent
from langchain_community.tools import DuckDuckGoSearchResults
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
import html
from unidecode import unidecode


class InputModel(SimpleInputModel):
    """Input model for DuckDuckGo Search."""
    query: str = Field(
        description="The search query to look up"
    )
    num_results: Optional[int] = Field(
        default=8,
        description="Number of results to return (default: 8)",
        ge=1,
        le=50
    )
    region: Optional[str] = Field(
        default="en-en",
        description="The region to use for the search (default: en-en)"
    )


class WebDuckduckgoSearchTool(SimpleTool):
    name = "web_duckduckgo_search"
    description = '''
    DuckDuckGo search engine that emphasizes user privacy.
    It's often described as a privacy-focused alternative to Google Search Engine.
    '''
    input_model = InputModel

    async def run(self, arguments: Dict[str, Any]) -> List[TextContent]:
        arg = InputModel(**arguments)
        query = arg.query
        num_results = arg.num_results or 8
        region = arg.region or "en-en"

        results = []
        if not query:
            return [TextContent(type="text", text="Missing required argument: query")]

        print(f"Query: {query}, Num Results: {num_results}")
        try:
            wrapper = DuckDuckGoSearchAPIWrapper(region=region, time="d", max_results=num_results, backend="auto")
            search = DuckDuckGoSearchResults(api_wrapper=wrapper, num_results=num_results, output_format='list')
            search_results = await search.arun(query)
            for result in search_results:
                # Decode and sanitize each part of the result
                def sanitize_text(text):
                    # Convert to string
                    text = str(text)

                    # Decode HTML entities
                    text = html.unescape(text)

                    # Use unidecode to transliterate to ASCII
                    text = unidecode(text)

                    return text.strip()

                title = sanitize_text(result.get('title', ''))
                link = sanitize_text(result.get('link', ''))
                snippet = sanitize_text(result.get('snippet', ''))

                # Only add results with non-empty sanitized content
                if title or link or snippet:
                    # results += f"Title: {title}\nLink: {link}\nSnippet: {snippet}\n\n"
                    results.append(TextContent(type="text", text=f"Title: {title}\nLink: {link}\nSnippet: {snippet}\n\n"))

            return results
            # return [TextContent(type="text", text=results)]
        except Exception as e:
            print(f"Full error details: {e}")
            return [TextContent(type="text", text=f"Error performing search: {str(e)}")]
