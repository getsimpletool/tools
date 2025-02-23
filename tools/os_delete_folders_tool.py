from simpletool import SimpleTool, SimpleInputModel, Field, Dict, Any, List
from simpletool.types import TextContent
import os
import shutil


class InputModel(SimpleInputModel):
    """Input model for OS Delete Folders Tool."""
    folder_paths: List[str] = Field(
        description="List of folder paths to delete"
    )
    force: bool = Field(
        default=False,
        description="If true, force deletion even if folder is not empty"
    )


class OsDeleteFoldersTool(SimpleTool):
    name = "os_delete_folders_tool"
    description = '''
    Deletes folders at specified paths, with options for recursive deletion.
    Accepts a list of folder paths and removes each folder.
    Supports both absolute and relative paths.
    Returns status messages for each folder deletion attempt.
    Provides safety checks to prevent accidental deletion of root or system directories.
    '''
    input_model = InputModel

    def _is_safe_path(self, path: str) -> bool:
        """
        Check if the path is safe to delete.
        Prevents deletion of root, home, and other critical system directories.
        """
        # Normalize and get absolute path
        abs_path = os.path.abspath(path)

        # Prevent deletion of root directories
        unsafe_paths = [
            '/',
            '/home',
            '/etc',
            '/usr',
            '/var',
            '/bin',
            '/sbin',
            os.path.expanduser('~')
        ]

        return not any(
            abs_path.startswith(safe_path) or
            abs_path == safe_path
            for safe_path in unsafe_paths
        )

    async def run(self, arguments: Dict[str, Any]) -> List[TextContent]:
        arg = InputModel(**arguments)
        folder_paths = arg.folder_paths
        force = arg.force

        if not folder_paths:
            return [TextContent(type="text", text="No folder paths provided")]

        results = []
        for path in folder_paths:
            try:
                # Normalize path
                normalized_path = os.path.normpath(path)
                absolute_path = os.path.abspath(normalized_path)

                # Safety check
                if not self._is_safe_path(absolute_path):
                    results.append(f"Unsafe deletion prevented for path: {path}")
                    continue

                # Check if path exists
                if not os.path.exists(absolute_path):
                    results.append(f"Path does not exist: {path}")
                    continue

                # Check if it's a directory
                if not os.path.isdir(absolute_path):
                    results.append(f"Path is not a directory: {path}")
                    continue

                # Deletion logic
                if force:
                    # Force deletion using shutil.rmtree
                    shutil.rmtree(absolute_path)
                    results.append(f"Forcefully deleted folder: {path}")
                else:
                    # Try to remove only if directory is empty
                    if not os.listdir(absolute_path):
                        os.rmdir(absolute_path)
                        results.append(f"Successfully deleted empty folder: {path}")
                    else:
                        results.append(f"Folder not empty, deletion skipped: {path}. Use 'force=true' to delete non-empty folders.")

            except PermissionError:
                results.append(f"Permission denied: Unable to delete folder {path}")
            except OSError as e:
                results.append(f"Error deleting folder {path}: {str(e)}")
            except Exception as e:
                results.append(f"Unexpected error deleting folder {path}: {str(e)}")

        return [TextContent(type="text", text="\n".join(results))]
