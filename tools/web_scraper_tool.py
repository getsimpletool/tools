from simpletool import SimpleTool, SimpleInputModel, Field, Optional, Dict, Any
from simpletool.types import TextContent
import httpx
from bs4 import BeautifulSoup
from lxml import html


def _extract_text(element):
    """Extracts text content from an element, handling None and missing text_content."""
    if element is None:
        return ""
    if hasattr(element, 'text_content') and callable(getattr(element, 'text_content')):
        text = element.text_content()
        if text:  # Check if text is not None or empty string
            return text.strip()
    return str(element).strip()


class InputModel(SimpleInputModel):
    """Input model for Web Scraper Tool."""
    url: str = Field(
        description="URL of the webpage to scrape"
    )
    selector: Optional[str] = Field(
        default="body",
        description="CSS or XPath selector to extract specific content from the webpage. If you not sure what selector use - leave it empty and use default body"
    )


class WebScraperTool(SimpleTool):
    name = "web_scraper_tool"
    description = "Web scraping tool that extracts text content from web pages. Supports various HTML parsing and extraction methods."
    input_model = InputModel

    async def run(self, arguments: Dict[str, Any]) -> list[TextContent]:
        # Validation and parsing of input arguments
        arg = InputModel(**arguments)

        url = arg.url
        selector = arg.selector or "body"
        if not url:
            return [TextContent(type="text", text="Error: URL is required")]
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(url)

                # Explicitly handle 301 Moved Permanently redirects
                if response.status_code == 301:
                    redirect_url = response.headers.get('location', '')
                    if redirect_url:
                        response = await client.get(redirect_url)

                response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            if selector:
                # Try CSS selector first
                elements = soup.select(selector)
                if not elements:
                    # If CSS selector fails, try XPath
                    try:
                        tree = html.fromstring(response.text)
                        elements = tree.xpath(selector)
                    except Exception:
                        return [TextContent(type="text", text=f"Error: Invalid selector '{selector}'")]

                # Extract text from elements
                extracted_texts = [_extract_text(element) for element in elements]
                extracted_texts = [text for text in extracted_texts if text]  # Remove empty texts

                if not extracted_texts:
                    return [TextContent(type="text", text=f"No content found for selector '{selector}'")]

                return [TextContent(type="text", text="\n\n".join(extracted_texts))]
            else:
                # If no selector, extract all text from the body
                return [TextContent(type="text", text=soup.get_text(strip=True))]

        except httpx.RequestError as e:
            return [TextContent(type="text", text=f"Error fetching URL: {str(e)}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Unexpected error: {str(e)}")]
