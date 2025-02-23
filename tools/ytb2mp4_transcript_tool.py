from simpletool import SimpleTool, SimpleInputModel, Field, Dict, Any, List
from simpletool.types import TextContent
import httpx


class InputModel(SimpleInputModel):
    """Input model for YouTube to MP4 Transcript Tool."""
    url: str = Field(
        description="The URL of the YouTube video to fetch transcript for"
    )


class Ytb2Mp4TranscriptTool(SimpleTool):
    name = "ytb2mp4_transcript"
    description = "Fetches and returns the transcript of a YouTube video using ytb2mp4 API."
    input_model = InputModel

    async def run(self, arguments: Dict[str, Any]) -> List[TextContent]:
        # Validation and parsing of input arguments
        arg = InputModel(**arguments)
        url = arg.url

        if not url:
            return [TextContent(type="text", text="Error: URL is required")]

        api_url = f"https://ytb2mp4.com/api/fetch-transcript?url={url}"
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(api_url)
                response.raise_for_status()
                data = response.json()
                transcript_text = data.get("transcript", "")
                return [TextContent(type="text", text=transcript_text)]
        except httpx.HTTPError as e:
            return [TextContent(type="text", text=f"Error fetching transcript: {str(e)}")]
        except Exception as e:
            return [TextContent(type="text", text=f"An unexpected error occurred: {str(e)}")]
