from simpletool import SimpleTool, SimpleInputModel, Field, Dict, Any
from simpletool.types import TextContent
import os
import re
from typing import Optional


class InputModel(SimpleInputModel):
    """Input model for OS File Edit Tool."""
    file_path: str = Field(
        description="Path to the file to edit"
    )
    edit_type: str = Field(
        description="Type of edit operation",
        examples=["full", "partial"]
    )
    new_content: str = Field(
        description="New content to write"
    )
    start_line: Optional[int] = Field(
        default=None,
        description="Starting line number for partial edits"
    )
    end_line: Optional[int] = Field(
        default=None,
        description="Ending line number for partial edits"
    )
    search_pattern: Optional[str] = Field(
        default=None,
        description="Pattern to search for in partial edits"
    )
    replacement_text: Optional[str] = Field(
        default=None,
        description="Text to replace matched patterns"
    )


class OsFileEditTool(SimpleTool):
    name = "os_file_edit_tool"
    description = '''
    A tool for editing file contents with support for:
    - Full file content replacement
    - Partial content editing by line numbers
    - Pattern-based text search and replace
    - Multiple file type support
    - Error handling for file operations
    '''
    input_model = InputModel

    async def run(self, arguments: Dict[str, Any]) -> list[TextContent]:
        arg = InputModel(**arguments)
        file_path = arg.file_path
        edit_type = arg.edit_type
        new_content = arg.new_content
        start_line = arg.start_line
        end_line = arg.end_line
        search_pattern = arg.search_pattern
        replacement_text = arg.replacement_text

        if file_path is None:
            return [TextContent(type="text", text="Error: File path is required.")]
        if not os.path.exists(file_path):
            return [TextContent(type="text", text=f"File not found: {file_path}")]

        if edit_type is None:
            return [TextContent(type="text", text="Error: Edit type is required.")]

        if new_content is None:
            return [TextContent(type="text", text="Error: New content is required.")]

        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                original_content = file.read()
                lines = original_content.splitlines()

            if edit_type == "full":
                updated_content = new_content
            else:
                if start_line is not None and end_line is not None:
                    updated_content = self._edit_by_lines(lines, start_line, end_line, new_content)
                elif search_pattern and replacement_text:
                    updated_content = self._find_and_replace(original_content, search_pattern, replacement_text)
                else:
                    raise ValueError("Invalid partial edit parameters")

            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(updated_content)

            return [TextContent(type="text", text=f"File successfully updated: {file_path}\n{updated_content}")]

        except Exception as e:
            return [TextContent(type="text", text=f"Error editing file: {str(e)}")]

    def _edit_by_lines(self, lines: list, start_line: int, end_line: int, new_content: str) -> str:
        if start_line < 1 or end_line > len(lines) or start_line > end_line:
            raise ValueError("Invalid line numbers")

        lines[start_line - 1:end_line] = new_content.splitlines()
        return '\n'.join(lines)

    def _find_and_replace(self, content: str, pattern: str, replacement: str) -> str:
        try:
            return re.sub(pattern, replacement, content)
        except re.error as e:
            return f"Invalid regular expression pattern: {str(e)}"
