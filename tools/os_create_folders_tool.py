from simpletool import SimpleTool, SimpleInputModel, Field, Dict, Any, List
from simpletool.types import TextContent
import os


class InputModel(SimpleInputModel):
    """Input model for OS Create Folders Tool."""
    folder_paths: List[str] = Field(
        description="List of folder paths to create"
    )


class OsCreateFoldersTool(SimpleTool):
    name = "os_create_folders_tool"
    description = '''
    Creates new folders at specified paths, including nested directories if needed.
    Accepts a list of folder paths and creates each folder along with any necessary parent directories.
    Supports both absolute and relative paths.
    Returns status messages for each folder creation attempt.
    '''
    input_model = InputModel

    async def run(self, arguments: Dict[str, Any]) -> List[TextContent]:
        arg = InputModel(**arguments)
        folder_paths: List[str] = arg.folder_paths
        if not folder_paths:
            return [TextContent(type="text", text="No folder paths provided")]

        results = []
        for path in folder_paths:
            try:
                # Normalize path
                normalized_path = os.path.normpath(path)
                absolute_path = os.path.abspath(normalized_path)

                # Validate path
                if not all(c not in '<>:"|?*' for c in absolute_path):
                    results.append(f"Invalid characters in path: {path}")
                    continue

                # Create directory
                os.makedirs(absolute_path, exist_ok=True)
                results.append(f"Successfully created folder: {path}")

            except PermissionError:
                results.append(f"Permission denied: Unable to create folder {path}")
            except Exception as e:
                results.append(f"Error creating folder {path}: {str(e)}")

        return [TextContent(type="text", text="\n".join(results))]
