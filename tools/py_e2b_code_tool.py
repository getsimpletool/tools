import json
import base64
from simpletool import SimpleTool, SimpleInputModel, Field, Dict, Any, List, Optional
from simpletool.types import TextContent
from e2b_code_interpreter import Sandbox
from dotenv import load_dotenv


class FileUpload(SimpleInputModel):
    """Model for file upload to sandbox."""
    local_path: Optional[str] = Field(
        default=None,
        description="Local path of the file to upload"
    )
    sandbox_path: str = Field(
        description="Path in the sandbox where the file will be uploaded"
    )
    content: str = Field(
        description="Content of the file to upload"
    )


class InputModel(SimpleInputModel):
    """Input model for Python E2B Code Tool."""
    code: str = Field(
        description="Python code to execute"
    )
    env_vars: Optional[Dict[str, str]] = Field(
        default=None,
        description="Dictionary of environment variables"
    )
    upload_files: Optional[List[FileUpload]] = Field(
        default=None,
        description="List of files to upload to sandbox"
    )
    download_paths: Optional[List[str]] = Field(
        default=None,
        description="List of file paths to download from sandbox"
    )


class PyE2bCodeTool(SimpleTool):
    name = "py_e2b_code_tool"
    description = '''
    Executes Python code in a sandboxed environment using e2b-code-interpreter.
    Features:
    - Execute Python code safely in isolation
    - Upload files to sandbox
    - Download files from sandbox
    - Support for environment variables
    Returns execution results including stdout, stderr, and file contents.
    '''
    input_model = InputModel

    async def run(self, arguments: Dict[str, Any]) -> List[TextContent]:
        try:
            load_dotenv()
            arg = InputModel(**arguments)
            code = arg.code
            upload_files = arg.upload_files
            download_paths = arg.download_paths

            # Create sandbox instance
            sandbox = Sandbox()

            # Upload files if specified
            uploaded_files = []
            for file_spec in upload_files or []:
                try:
                    # Check if sandbox_path is defined in upload_files
                    sandbox_path = file_spec.sandbox_path

                    content = file_spec.content

                    # Handle both text and base64 content
                    if ";base64," in content:
                        # Extract base64 data
                        content = content.split(";base64,")[1]
                        file_content = base64.b64decode(content)
                    else:
                        file_content = content.encode('utf-8')

                    sandbox.files.write(sandbox_path, file_content)
                    uploaded_files.append(sandbox_path)
                except Exception as e:
                    return [TextContent(type="text", text=json.dumps({
                        "success": False,
                        "error": f"Failed to upload file: {str(e)}",
                        "stdout": "",
                        "stderr": ""
                    }, indent=2))]

            # Execute code
            result = sandbox.run_code(code)

            # Download requested files
            downloaded_files = {}
            for file_path in download_paths or []:
                try:
                    content = sandbox.files.read(file_path)
                    # Convert binary content to base64
                    if isinstance(content, bytes):
                        content = base64.b64encode(content).decode('utf-8')
                        content = f"data:application/octet-stream;base64,{content}"
                    downloaded_files[file_path] = content
                except Exception as e:
                    downloaded_files[file_path] = f"Error downloading: {str(e)}"

            response = {
                "stdout": result.logs.stdout,
                "stderr": result.logs.stderr,
                "success": True,
                "error": None,
                "uploaded_files": uploaded_files,
                "downloaded_files": downloaded_files
            }

            return [TextContent(type="text", text=json.dumps(response, indent=2))]

        except Exception as e:
            return [TextContent(type="text", text=json.dumps({"success": False,
                                                              "error": f"Tool execution failed: {str(e)}",
                                                              "stdout": "",
                                                              "stderr": "",
                                                              "uploaded_files": [],
                                                              "downloaded_files": {}}, indent=2))]
