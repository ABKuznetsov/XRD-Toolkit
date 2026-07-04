# XRD Analysis Toolkit 1.0.1

Patch release for XRD Finder.

## Fixed

- Restored automatic plot fitting after adding one or more calculated phases when a single XRD pattern is displayed.
- Candidate preview still preserves the current zoom while browsing the candidate table.
- Removed the old `Standalone Finder Project` default name from the standalone GUI.
- Replaced remaining public `XRD Manager` window labels with `XRD Analysis Toolkit` / `XRD Finder` names.
- Clarified that setup scripts create a shared Toolkit `.venv` in the repository root.
- Synchronized package metadata version with the release number.

## Verification

- Python package compilation passed with Python 3.11.
- GUI and CLI imports passed.
- Phase Finder window smoke test passed in offscreen mode.
