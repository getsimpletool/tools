from simpletool import SimpleTool, SimpleInputModel, Field, Dict, Any, List, Union
from simpletool.types import TextContent
import json
from pathlib import Path


class FileEntry(SimpleInputModel):
    """Model for individual file creation entry."""
    path: str = Field(
        description="Path to the file to be created"
    )
    content: str = Field(
        description="Content to write to the file"
    )
    binary: bool = Field(
        default=False,
        description="Whether the file is binary (default: false)"
    )
    encoding: str = Field(
        default="utf-8",
        description="File encoding (default: utf-8)"
    )


class InputModel(SimpleInputModel):
    """Input model for OS File Creator."""
    files: Union[FileEntry, List[FileEntry]] = Field(
        description="File(s) to create"
    )


class OsFileCreatorTool(SimpleTool):
    name = "os_file_creator"
    description = '''
OS File Creator: A versatile tool for creating files with flexible options.

Key Features:
- Create single or multiple files in one operation
- Automatically create parent directories
- Support for text and binary file creation
- Handles JSON content seamlessly

Input Structure:
1. Single File:
{
    "files": {
        "path": "path/to/file.txt",
        "content": "file content"
    }
}

2. Multiple Files:
{
    "files": [
        {
            "path": "file1.py",
            "content": "# File 1 content"
        },
        {
            "path": "file2.py",
            "content": "# File 2 content"
        }
    ]
}

Optional Parameters:
- binary: Create binary files (default: false)
- encoding: Specify file encoding (default: "utf-8")
'''
    input_model = InputModel

    async def run(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """
        Execute the file creation process.

        Args:
            arguments: Must contain 'files' key with either a dict or list of dicts
                     Each dict must have 'path' and 'content' keys

        Returns:
            list[TextContent]: Results of file creation operations
        """
        arg = InputModel(**arguments)
        files = arg.files

        # If a single file is passed, convert it to a list
        if isinstance(files, FileEntry):
            files = [files]

        results = []
        for file_spec in files:
            path = Path(file_spec.path)
            if path.exists():
                return [TextContent(type="text", text=f"File {path} already exists.")]

            try:
                content = file_spec.content
                binary = file_spec.binary
                encoding = file_spec.encoding

                # Create parent directories
                path.parent.mkdir(parents=True, exist_ok=True)

                # Handle content
                if isinstance(content, dict):
                    content = json.dumps(content, indent=2)

                # Write file
                mode = 'wb' if binary else 'w'
                if binary:
                    if isinstance(content, str):
                        content = content.encode(encoding)
                    with open(path, mode) as f:
                        f.write(content)
                else:
                    with open(path, mode, encoding=encoding, newline='') as f:
                        f.write(content)

                results.append({
                    'path': str(path),
                    'success': True,
                    'size': path.stat().st_size
                })

            except Exception as e:
                results.append({
                    'path': str(path) if path is not None else None,
                    'success': False,
                    'error': str(e)
                })

        result_json = json.dumps({
            'created_files': len([r for r in results if r['success']]),
            'failed_files': len([r for r in results if not r['success']]),
            'results': results
        }, indent=2)

        return [TextContent(type="text", text=result_json)]
