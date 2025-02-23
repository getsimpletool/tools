#!/bin/bash
set -eo pipefail

# Ensure script is running with bash
if [ -z "$BASH_VERSION" ]; then
    echo "Error: This script must be run with bash"
    exit 1
fi

# Disable __pycache__ generation
export PYTHONDONTWRITEBYTECODE=1

# Remove any existing __pycache__ directories
find . -type d -name "__pycache__" ! -path "*/venv/*" -exec rm -rf {} +

VENV_DIR="venv"
COV_ARGS="--cov=simpletool --cov-report=term-missing --cov-report=html"
COV_ARGS=""

install_dependencies() {
    echo "### Installing test dependencies..."
    pip install pytest pytest-cov coverage > /dev/null 2>&1
}

run_tests() {
    echo "### Running pytest with coverage..."
    cd /mnt/github/simpletool-tools
    export PYTHONPATH=$PYTHONPATH:.
    export PYTEST_PLUGINS=pytest_asyncio
    pytest tests/ -v $COV_ARGS
}

cleanup() {
    if [ -d ".vscode" ]; then
        echo "### Cleaning test artifacts..."
        rm -rf htmlcov .pytest_cache .coverage
    fi
}

main() {
    if [ ! -d "$VENV_DIR" ]; then
        echo "### Creating virtual environment..."
        python3 -m venv "$VENV_DIR"
        source "$VENV_DIR/bin/activate"
        pip install -e . -r requirements.txt
    else
        echo "### Virtual environment already exists. Activating..."
        { source "$VENV_DIR/bin/activate"; } 2>/dev/null
    fi

    # Run Autopep8 amd Flake8 if --lint argument is provided
    if [ "$1" = "--lint" ]; then
        echo "### Running Autopep8 to fix formatting issues..."
        # E701 - multiple statements on one line (colon)
        # E302 - expected 2 blank lines, found 1
        # W293 - blank line contains whitespace
        # W291 - trailing whitespace
        # F401 - imported but unused (not working for some reason)
        # E306 - expected 1 blank line after class or function definition, found 0
        # E303 - expected 1 blank line after function or class definition, found 0
        for f in `find tests/ -name "*.py"`; do autopep8 --in-place --select=E701,E302,W293,W291,F401,E303,E306 $f; done

        # Run Flake8 on test files
        echo "### Running Flake8 linting on test files..."
        flake8 tests/
    fi

    install_dependencies
    run_tests
    cleanup
}

main "$@"
