from simpletool import SimpleTool, SimpleInputModel, Field, Dict, Any, List, ClassVar
from simpletool.types import TextContent
import logging
import sys
import traceback
import os
import json
import mimetypes


class InputModel(SimpleInputModel):
    """Input model for OS File Content Reader."""
    file_paths: List[str] = Field(
        description="List of file paths to read"
    )


class OsFileContentReaderTool(SimpleTool):
    name = "os_file_content_reader"
    description = '''
    Reads and extracts content from files across various formats.
    Skips binary and common ignore patterns.
    Supports reading multiple files with configurable filtering.
    '''
    input_model = InputModel

    # Files and directories to ignore
    IGNORE_PATTERNS: ClassVar[set[str]] = {
        # Hidden files and directories
        '.git', '.svn', '.hg', '.DS_Store', '.env', '.idea', '.vscode', '.settings',
        # Build directories
        'node_modules', '__pycache__', 'build', 'dist', 'venv', 'env', 'bin', 'obj',
        'target', 'out', 'Debug', 'Release', 'x64', 'x86', 'builds', 'coverage',
        # Binary file extensions
        '.pyc', '.pyo', '.so', '.dll', '.dylib', '.pdb', '.ilk', '.exp', '.map',
        '.exe', '.bin', '.dat', '.db', '.sqlite', '.sqlite3', '.o', '.cache',
        '.lib', '.a', '.sys', '.ko', '.obj', '.iso', '.msi', '.msp', '.msm',
        '.img', '.dmg', '.class', '.jar', '.war', '.ear', '.aar', '.apk',
        # Media files
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.psd', '.ai', '.eps',
        '.mp3', '.mp4', '.avi', '.mov', '.wav', '.aac', '.m4a', '.wma', '.midi',
        '.flv', '.mkv', '.wmv', '.m4v', '.webm', '.3gp', '.mpg', '.mpeg', '.m2v',
        '.ogg', '.ogv', '.webp', '.heic', '.raw', '.svg', '.ico', '.icns',
        # Archive files
        '.zip', '.tar', '.gz', '.rar', '.7z', '.pkg', '.deb', '.rpm', '.snap',
        '.bz2', '.xz', '.cab', '.tar.gz', '.tgz', '.tbz2', '.lz', '.lzma', '.tlz',
        # IDE and editor files
        '.sln', '.suo', '.user', '.workspace', '.project', '.classpath', '.iml',
        # Log and temp files
        '.log', '.tmp', '.temp', '.swp', '.bak', '.old', '.orig', '.pid'}

    def __init__(self):
        # Call the parent class's __init__ method
        super().__init__()

        # Add diagnostic logging during initialization
        try:
            logging.debug("Initializing %s tool", self.name)
            logging.debug("Current Python Path: %s", sys.path)
            logging.debug("Current Working Directory: %s", os.getcwd())
        except Exception as e:
            logging.error("Initialization diagnostic failed: %s", e)
            logging.error(traceback.format_exc())
            raise

    def _should_skip(self, path: str) -> bool:
        """Determine if a file or directory should be skipped."""
        try:
            name = os.path.basename(path)
            ext = os.path.splitext(name)[1].lower()

            # Skip if name or extension matches ignore patterns
            if name in self.IGNORE_PATTERNS or ext in self.IGNORE_PATTERNS:
                return True

            # Skip hidden files/directories (starting with .)
            if name.startswith('.'):
                return True

            # If it's a file, check if it's binary using mimetype
            if os.path.isfile(path):
                mime_type, _ = mimetypes.guess_type(path)
                if mime_type and not mime_type.startswith('text/'):
                    return True

            return False
        except Exception as e:
            logging.error("Error in _should_skip for %s: %s", path, e)
            return True

    def _read_file(self, file_path: str) -> str:
        """Safely read a file and handle errors."""
        try:
            if not os.path.exists(file_path):
                return "Error: File not found"

            if self._should_skip(file_path):
                return "Skipped: Binary or ignored file type"

            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()

        except PermissionError:
            return "Error: Permission denied"
        except IsADirectoryError:
            return "Error: Path is a directory"
        except UnicodeDecodeError:
            return "Error: Unable to decode file (likely binary)"
        except Exception as e:
            return f"Error: {str(e)}"

    def _read_directory(self, dir_path: str) -> dict:
        """Recursively read all files in a directory."""
        results = {}

        try:
            for root, dirs, files in os.walk(dir_path):
                # Filter out directories to skip
                dirs[:] = [d for d in dirs if not self._should_skip(os.path.join(root, d))]

                # Process files
                for file in files:
                    file_path = os.path.join(root, file)
                    if not self._should_skip(file_path):
                        content = self._read_file(file_path)
                        results[file_path] = content

        except Exception as e:
            results[dir_path] = f"Error reading directory: {str(e)}"

        return results

    async def run(self, arguments: Dict[str, Any]) -> List[TextContent]:
        arg = InputModel(**arguments)
        file_paths = arg.file_paths

        # Add diagnostic logging
        logging.debug("FileContentReaderTool: run method called")
        logging.debug("Arguments received: %s", arguments)

        results = {}

        try:
            for path in file_paths:
                if os.path.isdir(path):
                    # If it's a directory, read it recursively
                    dir_results = self._read_directory(path)
                    results.update(dir_results)
                else:
                    # If it's a file, read it directly
                    content = self._read_file(path)
                    results[path] = content

            return [TextContent(type="text", text=json.dumps(results, indent=2))]

        except Exception as e:
            logging.error("Error in run method: %s", e)
            logging.error(traceback.format_exc())
            return [TextContent(type="text", text=json.dumps({"error": str(e)}, indent=2))]
