from __future__ import annotations

import numpy as np

from xrd_finder.ui.pattern_plot_helpers import add_hkl_labels, plot_peak_intensity_sticks, plot_profile, scale_profile_to_reference


def draw_rruff_reference(
    *,
    plot,
    plot_layers: dict[str, list],
    data: np.ndarray,
    observed,
    label: str,
) -> None:
    y = np.asarray(data[:, 1], dtype=float)
    if observed is not None and len(observed):
        observed_max = max(float(np.nanmax(observed[:, 1])), 1.0)
        y = scale_profile_to_reference(y, observed_max * 0.92)
    item = plot_profile(
        plot,
        np.asarray(data[:, 0], dtype=float),
        y,
        "#1a73e8",
        f"RRUFF reference {label}",
        width=1.7,
    )
    plot_layers["calculated_profile"].append(item)
    plot.setTitle(f"RRUFF reference overlay: {label}", color="#111111", size="13pt")


def draw_pdf2_reference(
    *,
    plot,
    plot_layers: dict[str, list],
    peaks,
    observed,
    active_plot_context: dict[str, float],
    label: str,
    show_hkl_labels: bool,
) -> None:
    if observed is not None and len(observed):
        x_grid = np.asarray(observed[:, 0], dtype=float)
        active_plot_offset = float(active_plot_context.get("offset", 0.0))
        baseline_value = float(np.nanmin(observed[:, 1])) + active_plot_offset
        top_value = float(np.nanmax(observed[:, 1])) + active_plot_offset
        height = max(top_value - baseline_value, float(active_plot_context.get("height", 0.0)), 1.0)
    else:
        x_grid = np.linspace(5.0, 120.0, 5000)
        baseline_value = 0.0
        height = 100.0

    baseline = np.full_like(x_grid, baseline_value, dtype=float)
    stick_item = plot_peak_intensity_sticks(
        plot,
        peaks,
        "#1a73e8",
        x_grid,
        baseline,
        height,
        f"PDF-2 reference {label}",
        width=3.0,
    )
    plot_layers["preview_peak_positions"].append(stick_item)
    hkl_peaks = [peak for peak in peaks if getattr(peak, "h", "") or getattr(peak, "k", "") or getattr(peak, "l", "")]
    if show_hkl_labels and hkl_peaks:
        hkl_items = add_hkl_labels(
            plot,
            hkl_peaks,
            "#1a73e8",
            baseline_value,
            height,
            limit=18,
            above_peaks=True,
        )
        plot_layers["preview_hkl"].extend(hkl_items)
    plot.setTitle(
        f"PDF-2 peak preview for {label} ({len(peaks)} lines)",
        color="#111111",
        size="13pt",
    )
