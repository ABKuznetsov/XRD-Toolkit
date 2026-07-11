# XRD Phase Finder 1.1.2

- Added per-profile plot visibility controls for experimental patterns, candidate preview sticks, calculated totals, individual phase profiles, backgrounds, phase tick marks, peak labels and unknown peaks.
- Improved multi-pattern plotting so the active profile can be configured independently while displayed XRD patterns keep stable colors.
- Reworked candidate preview rendering: preview sticks now follow the active profile baseline and peak labels are disabled by default.
- Improved synchronization between the View tab and plot context-menu layer toggles.
- Added caching-oriented changes for candidate previews and phase-search browsing to reduce repeated CIF enrichment and profile recalculation.
- Reduced candidate-table redraw overhead for large search results.
- Fixed normalization so unprocessed imported XRD files are also passed to the Finder calculation in normalized form when `Normalize` is enabled.
- Continued the experimental foundation for `Match (%)` and `Gain (%)`; these values are visible but still considered under tuning.

## Downloads

- Windows: [XRD_Phase_Finder_Setup_1.1.2.exe](https://github.com/ABKuznetsov/XRD_Analysis_Toolkit/releases/download/v1.1.2/XRD_Phase_Finder_Setup_1.1.2.exe)
- macOS: [XRD_Phase_Finder_macOS_1.1.2.zip](https://github.com/ABKuznetsov/XRD_Analysis_Toolkit/releases/download/v1.1.2/XRD_Phase_Finder_macOS_1.1.2.zip)

## SHA256

```text
13802bd8c48c259ecc3479c8b3e07f1487102493504ec64f64e717781a1c30e2  XRD_Phase_Finder_Setup_1.1.2.exe
24a3d395b40153fa4be22a82b7f980ed3a43934ca8145e564d01839ad60d715f  XRD_Phase_Finder_macOS_1.1.2.zip
```
