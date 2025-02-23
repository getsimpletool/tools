import os
import re
import anthropic
from simpletool import SimpleTool, SimpleInputModel, Field, Dict, Any
from simpletool.types import TextContent
from rich.console import Console
from rich.panel import Panel
from pathlib import Path
from dotenv import load_dotenv
from anthropic.types import ContentBlock, TextBlock


load_dotenv()


class InputModel(SimpleInputModel):
    """Input model for tool creation."""
    tool_description: str = Field(
        description="Natural language description of what the tool should do",
        examples=["Create a tool to fetch weather data from OpenWeatherMap API"]
    )


class ToolCreatorTool(SimpleTool):
    name = "tool_creator"
    description = '''Creates a new tool based on a natural language description.
    Use this when you need a new capability that isn't available in current tools.
    The tool will be automatically generated and saved to the tools directory.
    Returns the generated tool code and creation status.
    '''
    input_model = InputModel

    def _sanitize_filename(self, name: str) -> str:
        """Convert tool name to valid Python filename"""
        return name + '.py'  # Keep exact name, just add .py

    def _validate_tool_name(self, name: str) -> bool:
        """Validate tool name matches required pattern"""
        return bool(re.match(r'^[a-zA-Z0-9_-]{1,64}$', name))

    async def run(self, arguments: Dict[str, Any]) -> list[TextContent]:
        arg = InputModel(**arguments)
        tool_description = arg.tool_description

        client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        Console()
        tools_dir = Path(__file__).parent.parent / "tools"  # Fixed path

        if not tool_description:
            return [TextContent(type="text", text="No tool description provided")]

        # Create exact same prompt as the original
        prompt = f"""Create a Python tool class that follows our BaseTool interface. The tool should:

1. {tool_description}

Important:
- The class name must have: 'name', 'description', 'input_schema' attributes, and execute 'run' method.
- For example, if the class is `WeatherTool`, then:
  - name property must be "weathertool"
  - file must be weathertool.py

Here's the required structure (including imports and format):

```python
from basetool import BaseTool  # This import must be present
import requests  # Add any other required imports
from mcp.types import TextContent

class ToolName(BaseTool):  # Class name must match name property in uppercase first letter
    name = 'toolname'
    description = '''Detailed description here.
    Multiple lines for clarity.
    '''
    input_schema = {
            "type": "object",
        "properties": {
                "parameter_name": {
                    "type": "string",
                "description": "This is parameter_name Description"
            }
        },
        "required": ["parameter_name"]  # List required parameters
    }

    def run(self, arguments: dict) -> list[TextContent]:
        # Implementation here
        return [TextContent(type="text", text="Result")]
```

Generate the complete tool implementation following this exact structure.
Return ONLY the Python code without any explanation or markdown formatting.
"""

        try:
            # Get tool implementation from Claude with animation
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4000,
                temperature=0,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            tool_code = ""
            if response.content[0] is not None:
                response_block: ContentBlock = response.content[0]
                if isinstance(response_block, TextBlock):
                    tool_code = response_block.text.strip()

            # Extract tool name from the generated code
            name_match = re.search(r'name\s*=\s*["\']([a-zA-Z0-9_-]+)["\']', tool_code)
            if not name_match:
                return [TextContent(type="text", text="Error: Could not extract tool name from generated code")]

            tool_name = name_match.group(1)
            filename = self._sanitize_filename(tool_name)

            # Ensure the tools directory exists
            tools_dir.mkdir(exist_ok=True)

            # Save tool to file
            file_path = tools_dir / filename
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(tool_code)

            # Format the response using Panel like the original
            result = f"""[bold green]✅ Tool created successfully![/bold green]
Tool name: [cyan]{tool_name}[/cyan]
File created: [cyan]{filename}[/cyan]

[bold]Generated Tool Code:[/bold]
{Panel(tool_code, border_style="green")}

[bold green]✨ Tool is ready to use![/bold green]
Type 'refresh' to load your new tool."""

            return [TextContent(type="text", text=result)]

        except Exception as e:
            return [TextContent(type="text", text=f"Error creating tool: {str(e)}")]
