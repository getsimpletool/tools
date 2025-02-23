from simpletool import SimpleTool, SimpleInputModel, Field, Dict, Any, List, Optional, Union
from simpletool.types import TextContent, ErrorContent
import logging
import subprocess


class InputModel(SimpleInputModel):
    """Input model for UV Package Manager."""
    command: str = Field(
        description="Primary command (install, remove, update, init, venv, etc.)"
    )
    packages: List[str] = Field(
        default=[],
        description="List of packages to operate on"
    )
    python_version: Optional[str] = Field(
        default=None,
        description="Python version for operations that require it"
    )
    project_path: str = Field(
        default=".",
        description="Path to project directory"
    )
    requirements_file: Optional[str] = Field(
        default=None,
        description="Path to requirements file"
    )
    global_install: bool = Field(
        default=False,
        description="Whether to install packages globally"
    )


class OsUVPackageManager(SimpleTool):
    name = "os_uv_package_manager"
    description = '''
    Comprehensive interface to the uv package manager providing package management,
    project management, Python version management, tool management, and script support.
    Supports all major platforms with pip compatibility.
    '''
    input_model = InputModel

    async def run(self, arguments: Dict[str, Any]) -> List[Union[TextContent, ErrorContent]]:
        arg = InputModel(**arguments)
        command = arg.command
        packages = arg.packages
        python_version = arg.python_version
        project_path = arg.project_path
        requirements_file = arg.requirements_file
        global_install = arg.global_install

        try:
            if command == "install":
                return await self._install_packages(packages, requirements_file, global_install)
            elif command == "remove":
                return await self._remove_packages(packages)
            elif command == "update":
                return await self._update_packages(packages)
            elif command == "list":
                return await self._list_packages()
            elif command == "init":
                return await self._init_project(project_path)
            elif command == "venv":
                return await self._create_venv(project_path, python_version)
            elif command == "python":
                return await self._manage_python(python_version)
            elif command == "compile":
                return await self._compile_requirements()
            elif command == "run":
                return await self._run_script(arguments.get("script", None), packages)
            else:
                return [TextContent(type="text", text=f"Unknown command: {command}")]

        except Exception as e:
            logging.error("Error executing UV command: %s", str(e))
            return [TextContent(type="text", text=f"Error: {e!s}")]

    async def _run_uv_command(self, args: List[str]) -> str:
        try:
            result = subprocess.run(
                ["uv"] + args,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            return f"UV command failed: {e}"

    async def _install_packages(self, packages: List[str], requirements_file: Optional[str], global_install: bool) -> List[Union[TextContent, ErrorContent]]:
        args = ["pip", "install"]
        if global_install:
            args.append("--global")
        if requirements_file:
            args.extend(["-r", requirements_file])
        if packages:
            args.extend(packages)
        result = await self._run_uv_command(args)
        return [TextContent(type="text", text=result)]

    async def _remove_packages(self, packages: List[str]) -> List[Union[TextContent, ErrorContent]]:
        result = await self._run_uv_command(["pip", "uninstall", "-y"] + packages)
        return [TextContent(type="text", text=result)]

    async def _update_packages(self, packages: List[str]) -> List[Union[TextContent, ErrorContent]]:
        args = ["pip", "install", "--upgrade"]
        if packages:
            args.extend(packages)
        result = await self._run_uv_command(args)
        return [TextContent(type="text", text=result)]

    async def _list_packages(self) -> List[Union[TextContent, ErrorContent]]:
        result = await self._run_uv_command(["pip", "list"])
        return [TextContent(type="text", text=result)]

    async def _init_project(self, project_path: str) -> List[Union[TextContent, ErrorContent]]:
        result = await self._run_uv_command(["init", project_path])
        return [TextContent(type="text", text=result)]

    async def _create_venv(self, path: str, python_version: Optional[str]) -> List[Union[TextContent, ErrorContent]]:
        args = ["venv"]
        if python_version:
            args.extend(["--python", python_version])
        args.append(path)
        result = await self._run_uv_command(args)
        return [TextContent(type="text", text=result)]

    async def _manage_python(self, version: Optional[str]) -> List[Union[TextContent, ErrorContent]]:
        if not version:
            result = await self._run_uv_command(["python", "list"])
            return [TextContent(type="text", text=result)]
        result = await self._run_uv_command(["python", "install", version])
        return [TextContent(type="text", text=result)]

    async def _compile_requirements(self) -> List[Union[TextContent, ErrorContent]]:
        result = await self._run_uv_command(["pip", "compile", "requirements.in"])
        return [TextContent(type="text", text=result)]

    async def _run_script(self, script: str, packages: List[str]) -> List[Union[TextContent, ErrorContent]]:
        args = ["run"]
        if packages:
            args.extend(["--with"] + packages)
        args.extend(["--", "python", script])
        result = await self._run_uv_command(args)
        return [TextContent(type="text", text=result)]
