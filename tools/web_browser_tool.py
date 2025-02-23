from simpletool import SimpleTool, SimpleInputModel, Field, Dict, Any, List, Union
from simpletool.types import TextContent
import webbrowser
import validators
from urllib.parse import urlparse


class InputModel(SimpleInputModel):
    """Input model for Web Browser Tool."""
    urls: Union[str, List[str]] = Field(
        description="Single URL or list of URLs to open"
    )


class WebBrowserTool(SimpleTool):
    name = "web_browser_tool"
    description = '''
    Opens URLs in the system's default web browser.
    Accepts a single URL or a list of URLs.
    Validates URL format and supports http/https protocols.
    Returns feedback on which URLs were successfully opened.
    '''
    input_model = InputModel

    def _validate_url(self, url: str) -> bool:
        if not isinstance(url, str):
            return False
        if not validators.url(url):
            return False
        parsed = urlparse(url)
        return parsed.scheme in ['http', 'https']

    async def run(self, arguments: Dict[str, Any]) -> List[TextContent]:
        arg = InputModel(**arguments)
        urls = arg.urls

        if isinstance(urls, str):
            urls = [urls]

        results = []
        for url in urls:
            try:
                if not self._validate_url(url):
                    results.append(f"Failed to open {url}: Invalid URL format")
                    continue

                webbrowser.open(url)
                results.append(f"Successfully opened {url}")
            except Exception as e:
                results.append(f"Error opening {url}: {str(e)}")

        return [TextContent(type="text", text="\n".join(results))]
