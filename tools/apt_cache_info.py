import subprocess
from simpletool import SimpleTool, SimpleInputModel, Field, Sequence, Dict, Any
from simpletool.types import TextContent


class InputModel(SimpleInputModel):
    """Input model for APT cache information retrieval."""
    operation: str = Field(
        description="Type of cache information to retrieve",
        examples=["stats", "search", "policy"],
        default="stats"
    )
    package_name: str = Field(
        description="Optional package name for specific queries",
        default=""
    )
    use_sudo: bool = Field(
        description="Whether to use sudo for the command",
        default=False
    )


class AptCacheInfoTool(SimpleTool):
    name = "apt_cache_info"
    description = '''
    Retrieves and displays information about the APT package cache.
    Provides details about installed, available, and cached packages.
    '''
    input_model = InputModel

    async def run(self, arguments: Dict[str, Any]) -> Sequence[TextContent]:
        arg = InputModel(**arguments)
        operation = arg.operation
        package_name = arg.package_name
        use_sudo = arg.use_sudo

        try:
            # Construct the base command
            cmd = ["apt-cache"]

            # Add sudo if requested
            if use_sudo:
                cmd.insert(0, "sudo")

            # Add specific command
            if operation == "show":
                cmd.append("show")
                cmd.append(package_name)
            elif operation == "search":
                cmd.append("search")
                cmd.append(package_name)
            elif operation == "policy":
                cmd.append("policy")
                if package_name:
                    cmd.append(package_name)
            else:
                cmd.append("stats")

            # Run the command
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)

            # Check for errors
            if result.returncode != 0:
                return [TextContent(type="text", text=f"Error: {result.stderr}")]

            # Return the command output
            return [TextContent(type="text", text=result.stdout)]

        except Exception as e:
            return [TextContent(type="text", text=f"Unexpected error: {str(e)}")]
