from simpletool import SimpleTool, SimpleInputModel, Field, Dict, Any, List, Optional
from simpletool.types import TextContent
from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
from unidecode import unidecode
import asyncio


class InputModel(SimpleInputModel):
    """Input model for Wikipedia Search."""
    query: str = Field(description="The search query to find information on Wikipedia")
    num_results: Optional[int] = Field(default=8, description="Number of results to return")
    region: Optional[str] = Field(default="en", description="Wikipedia language region")


class WikipediaSearchTool(SimpleTool):

    name = "wikipedia_search"
    description = "Search Wikipedia articles and get summaries of the content"
    input_model = InputModel

    async def run(self, arguments: Dict[str, Any]) -> List[TextContent]:
        arg = InputModel(**arguments)
        query = arg.query
        num_results = arg.num_results or 8
        region = arg.region or "en"

        if not query:
            return [TextContent(type="text", text="Missing required argument: query")]

        try:
            api_wrapper = WikipediaAPIWrapper(top_k_results=num_results, doc_content_chars_max=500)
            tool = WikipediaQueryRun(api_wrapper=api_wrapper)
            result = await asyncio.to_thread(tool.run, query)
            return [TextContent(type="text", text=result)]
        except Exception as e:
            return [TextContent(type="text", text=f"Error performing search: {str(e)}")]
