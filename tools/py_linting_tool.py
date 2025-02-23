from simpletool import SimpleTool, SimpleInputModel, Field, Dict, Any, Optional, List
from simpletool.types import TextContent
import subprocess


class InputModel(SimpleInputModel):
    """Input model for Python Linting Tool."""
    paths: Optional[List[str]] = Field(
        default=None,
        description="List of file or directory paths to lint. Defaults to current directory if none provided."
    )
    fix: bool = Field(
        default=False,
        description="Whether to automatically fix fixable issues."
    )
    unsafe_fixes: bool = Field(
        default=False,
        description="Enable unsafe fixes."
    )
    add_noqa: bool = Field(
        default=False,
        description="Add noqa directives to all lines with violations."
    )
    select: Optional[List[str]] = Field(
        default=None,
        description="List of rule codes to exclusively enforce."
    )
    extend_select: Optional[List[str]] = Field(
        default=None,
        description="List of additional rule codes to enforce alongside the default selection."
    )
    watch: bool = Field(
        default=False,
        description="Watch for file changes and re-run linting on change."
    )
    exit_zero: bool = Field(
        default=False,
        description="Exit with code 0 even if violations are found."
    )
    exit_non_zero_on_fix: bool = Field(
        default=False,
        description="Exit with non-zero even if all violations were fixed automatically."
    )


class PyLintingTool(SimpleTool):
    name = "py_linting_tool"
    description = '''
    Runs the Ruff linter on the given Python files or directories to detect and fix coding style or syntax issues.
    Supports configurable rule selection, automatic fixes, unsafe fixes, adding noqa directives, and watch mode.
    Returns the linter output as a string.
    '''
    input_model = InputModel

    async def run(self, arguments: Dict[str, Any]) -> List[TextContent]:
        arg = InputModel(**arguments)
        paths = arg.paths
        fix = arg.fix
        unsafe_fixes = arg.unsafe_fixes
        add_noqa = arg.add_noqa
        select = arg.select
        extend_select = arg.extend_select
        watch = arg.watch
        exit_zero = arg.exit_zero
        exit_non_zero_on_fix = arg.exit_non_zero_on_fix

        cmd = ["uv", "run", "ruff", "check"]

        if fix:
            cmd.append("--fix")
        if unsafe_fixes:
            cmd.append("--unsafe-fixes")
        if add_noqa:
            cmd.append("--add-noqa")
        if watch:
            cmd.append("--watch")
        if exit_zero:
            cmd.append("--exit-zero")
        if exit_non_zero_on_fix:
            cmd.append("--exit-non-zero-on-fix")

        for rule in select or []:
            cmd.extend(["--select", rule])
        for rule in extend_select or []:
            cmd.extend(["--extend-select", rule])

        if not paths:
            paths = ["."]
        cmd.extend(paths)

        try:
            result = subprocess.run(
                cmd,
                text=True,
                capture_output=True,
                check=False
            )
            return [TextContent(type="text", text=result.stdout + result.stderr)]
        except Exception as e:
            return [TextContent(type="text", text=f"Error running ruff check: {str(e)}")]
