import subprocess
from simpletool import SimpleTool, SimpleInputModel, Field, Dict, Any
from simpletool.types import TextContent
from typing import List


class InputModel(SimpleInputModel):
    """Input model for APT Package Manager."""
    command: str = Field(
        description="The apt-get command to execute",
        examples=["install", "remove", "update", "upgrade", "autoremove"]
    )
    packages: List[str] = Field(
        default=[],
        description="List of packages to install or remove"
    )
    use_sudo: bool = Field(
        default=False,
        description="Whether to run the command with sudo privileges"
    )
    assume_yes: bool = Field(
        default=True,
        description="Automatically answer yes to prompts"
    )


class AptPackageManagerTool(SimpleTool):
    name = "apt_package_manager"
    description = '''
    Manages package installation and removal on Ubuntu/Debian systems using apt-get.
    Supports:
    - Installing packages
    - Removing packages
    - Updating package lists
    - Upgrading system packages
    - Optional sudo execution for system-level operations
    Provides a safe and flexible interface for package management.
    '''
    input_model = InputModel

    async def run(self, arguments: Dict[str, Any]) -> List[TextContent]:
        arg = InputModel(**arguments)
        command = arg.command
        packages = arg.packages
        use_sudo = arg.use_sudo
        assume_yes = arg.assume_yes

        try:
            # Construct the base command
            cmd = ["apt-get"]

            # Add sudo if requested
            if use_sudo:
                cmd.insert(0, "sudo")

            # Add assume-yes flag if set
            if assume_yes:
                cmd.append("-y")

            # Add specific command
            if command == "install":
                cmd.append("install")
                cmd.extend(packages)
            elif command == "remove":
                cmd.append("remove")
                cmd.extend(packages)
            elif command == "update":
                cmd.append("update")
            elif command == "upgrade":
                cmd.append("upgrade")
            elif command == "autoremove":
                cmd.append("autoremove")
            else:
                return [TextContent(type="text", text=f"Unsupported command: {command}")]

            # Run the command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )

            # Return output as TextContent
            return [TextContent(
                type="text",
                text=f"Command '{' '.join(cmd)}' executed successfully:\n{result.stdout}\n{result.stderr}"
            )]

        except subprocess.CalledProcessError as e:
            # Handle command execution errors
            return [TextContent(
                type="text",
                text=f"Error executing apt-get command:\nCommand: {' '.join(e.cmd)}\n"
                     f"Return Code: {e.returncode}\n"
                     f"Standard Output: {e.stdout}\n"
                     f"Standard Error: {e.stderr}"
            )]
        except Exception as e:
            # Handle any other unexpected errors
            return [TextContent(
                type="text",
                text=f"Unexpected error in AptPackageManager: {str(e)}"
            )]
