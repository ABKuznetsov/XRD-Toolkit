# XRD Phase Finder 1.1.0

Feature release focused on Phase Finder maintainability, background correction and cross-platform setup improvements.

## Download

- Windows: [XRD_Phase_Finder_Setup_1.1.0.exe](https://github.com/ABKuznetsov/XRD_Analysis_Toolkit/releases/download/v1.1.0/XRD_Phase_Finder_Setup_1.1.0.exe)
- macOS: [XRD_Phase_Finder_macOS_1.1.0.zip](https://github.com/ABKuznetsov/XRD_Analysis_Toolkit/releases/download/v1.1.0/XRD_Phase_Finder_macOS_1.1.0.zip)

Checksums:

```text
SHA256  4d1b7c9e6e788fecd0ce7c3b66a529c5b3641fb18a2cb20866454d46e737eeb7  XRD_Phase_Finder_Setup_1.1.0.exe
SHA256  c1a10cc8b97bf2c8035762e8b1346c205e942a2bdfcafa5d2c33ee721b1884dd  XRD_Phase_Finder_macOS_1.1.0.zip
```

## Changed
- Refactored the Phase Finder workspace into smaller action, renderer and state modules.
- Added pybaselines-backed background estimation with conservative fallbacks when pybaselines is unavailable.
- Improved Finder project-state persistence for observed patterns, selected candidates and workspace settings.
- Added macOS setup/update helpers and release archive tooling.
- Added a startup notice for first launch after install or update, explaining that setup, cache creation and database preparation can take time.
- Kept PySide6 pinned to 6.7.3 for Windows 10 startup stability.

## Verification
- Python modules compile successfully.
- Ruff checks pass with Miller-index `h, k, l` notation allowed.
- Offscreen Phase Finder window smoke test passes.
- Preprocessing/background smoke test passes with pybaselines installed.
