# XRD Toolkit

Standalone XRD phase finder for Windows.

## Install

1. Install Python 3.11 or newer.
2. Double-click:

```bat
setup_env.bat
```

This creates `.venv` and installs the required packages.

## Run

Double-click:

```bat
run_finder.bat
```

Optional startup files:

```bat
run_finder.bat --pattern "path\to\pattern.txt" --cif "path\to\phase.cif"
```

## CLI

```bat
run_finder_cli.bat "path\to\pattern.txt" "path\to\phase.cif"
```

## Optional Materials Project Support

Materials Project is not installed by default because it is a heavy optional dependency.

To enable it:

```bat
.venv\Scripts\python.exe -m pip install -r requirements-optional.txt
```

Then add your Materials Project API key in the app settings.

## Repository Contents

```text
xrd_manager/              application code
requirements.txt          required dependencies
requirements-optional.txt optional online database dependencies
setup_env.bat             create Windows virtual environment
run_finder.bat            launch GUI
run_finder_cli.bat        launch CLI
pyproject.toml            package metadata
```

Local downloaded databases and user caches are intentionally ignored by git.
