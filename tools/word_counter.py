from simpletool import SimpleTool, SimpleInputModel, Field, Dict, Any
from simpletool.types import TextContent, ErrorContent
from typing import List


class WordCounterInput(SimpleInputModel):
    """Input schema for WordCounterTool."""
    text: str = Field(..., description="The text to count words in.")


class WordCounterTool(SimpleTool):
    name = "Word Counter Tool"
    description = "Counts the number of words in a given text."
    input_model = WordCounterInput

    async def run(self, arguments: Dict[str, Any]) -> List[TextContent | ErrorContent]:
        word_count = len(arguments["text"].split())
        return [TextContent(text=f"Word count: {word_count}")]
