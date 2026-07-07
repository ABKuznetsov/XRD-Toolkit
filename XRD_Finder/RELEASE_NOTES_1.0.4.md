# XRD Phase Finder 1.0.4

Patch release focused on Windows 10 startup reliability, in-app update testing, and basic project tree management.

## Changed
- Pinned PySide6 to a Windows 10 friendly Qt runtime line instead of installing the newest available Qt wheel.
- Setup now upgrades or downgrades existing packages to match the packaged requirements, so old shared environments are repaired during install.
- Automatic updates now try PowerShell download, BITS, and curl.exe before falling back to the browser.
- Added earlier launcher diagnostics for startup failures before the main application window appears.
- The startup preview closes when the visible application window appears, not only when Python exposes a main window handle.
- Kept software rendering defaults for Qt on older graphics drivers.
- Added right-click project tree actions for XRD/CIF entries: Open, Rename, and Delete.
- Added F2 rename and Delete key shortcuts for project tree items.

## Verification
- PowerShell launcher syntax check passes.
- Python UI modules compile successfully.
- Windows installer builds as `XRD_Phase_Finder_Setup_1.0.4.exe`.
- Setup log should show `PySide6==6.7.3` being installed or already satisfied.
