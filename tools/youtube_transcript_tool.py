from simpletool import SimpleTool, SimpleInputModel, Field, Dict, Any
from simpletool.types import TextContent
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptAvailable


class InputModel(SimpleInputModel):
    """Input model for YouTube Transcript Tool."""
    url: str = Field(
        description="The URL of the YouTube video to fetch transcript for"
    )
    language: str = Field(
        default="en",
        description="Language code for the transcript (default: 'en')"
    )


class YouTubeTranscriptTool(SimpleTool):
    name = "youtube_transcript"
    description = "Fetches and returns the transcript of a YouTube video. Supports multiple languages."
    input_model = InputModel

    async def run(self, arguments: Dict[str, Any]) -> list[TextContent]:
        # Validation and parsing of input arguments
        arg = InputModel(**arguments)

        url = arg.url
        language = arg.language

        if not url:
            return [TextContent(type="text", text="Error: URL is required")]

        try:
            # Extract video ID from URL
            video_id = str(url).split("v=")[1].split("&")[0]

            # Fetch transcript
            transcript = YouTubeTranscriptApi.get_transcript(
                video_id,
                languages=[language]
            )

            # Combine text from all transcript entries
            text = " ".join([entry["text"] for entry in transcript])
            return [TextContent(type="text", text=text)]

        except TranscriptsDisabled:
            return [TextContent(type="text", text="Error: Transcripts are disabled for this video")]
        except NoTranscriptAvailable:
            return [TextContent(type="text", text="Error: No transcript available for this video")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error fetching transcript: {str(e)}")]
