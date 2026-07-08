from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.signal import find_peaks, peak_widths, savgol_filter

from xrd_finder.finder.models import FinderInput, ObservedPeak
from xrd_finder.io.xy_loader import load_xy
from xrd_finder.services.preprocessing_service import estimate_background as estimate_xrd_background


@dataclass(slots=True)
class ObservedPatternData:
    x_grid: np.ndarray
    observed_y: np.ndarray
    background: np.ndarray
    target_y: np.ndarray
    fwhm: float
    peaks: list[ObservedPeak]
    peak_positions: np.ndarray


class ObservedPatternProcessor:
    def prepare(self, finder_input: FinderInput) -> ObservedPatternData:
        x_grid, observed_y = self.observed_arrays(finder_input)
        observed_y = self.smooth_y(observed_y, finder_input.smoothing_window)
        background = self.estimate_background(x_grid, observed_y) if finder_input.subtract_background else np.zeros_like(observed_y)
        target_y = np.clip(observed_y - background, 0.0, None)
        fwhm = finder_input.fwhm or self.estimate_fwhm(x_grid, target_y)
        peaks = self.observed_peaks(x_grid, target_y, fwhm)
        peak_positions = np.asarray([peak.two_theta for peak in peaks], dtype=float)
        return ObservedPatternData(
            x_grid=x_grid,
            observed_y=observed_y,
            background=background,
            target_y=target_y,
            fwhm=float(fwhm),
            peaks=peaks,
            peak_positions=peak_positions,
        )

    def observed_arrays(self, finder_input: FinderInput) -> tuple[np.ndarray, np.ndarray]:
        if finder_input.observed_x is not None and finder_input.observed_y is not None:
            x = np.asarray(finder_input.observed_x, dtype=float)
            y = np.asarray(finder_input.observed_y, dtype=float)
            if len(x) != len(y) or len(x) == 0:
                raise ValueError("Observed X/Y arrays must be non-empty and have equal length.")
            return x, y
        observed = load_xy(finder_input.pattern_path)
        return np.asarray(observed[:, 0], dtype=float), np.asarray(observed[:, 1], dtype=float)

    def smooth_y(self, y: np.ndarray, window: int) -> np.ndarray:
        if window <= 2 or len(y) < 5:
            return y
        window = min(int(window), len(y) - 1 if len(y) % 2 == 0 else len(y))
        if window % 2 == 0:
            window -= 1
        if window < 5:
            return y
        try:
            return np.asarray(savgol_filter(y, window_length=window, polyorder=2, mode="interp"), dtype=float)
        except Exception:
            kernel = np.ones(window, dtype=float) / float(window)
            return np.convolve(y, kernel, mode="same")

    def estimate_background(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        if len(y) < 5:
            return np.zeros_like(y)
        try:
            return np.asarray(estimate_xrd_background(x, y, method="auto"), dtype=float)
        except Exception:
            return np.full_like(y, float(np.nanpercentile(y, 15)))

    def estimate_fwhm(self, x: np.ndarray, y: np.ndarray) -> float:
        if len(x) < 5 or float(np.nanmax(y)) <= 0:
            return 0.18
        prominence = max(float(np.nanmax(y)) * 0.08, 1.0)
        indices, _properties = find_peaks(y, prominence=prominence, distance=max(3, len(y) // 1000))
        if len(indices) == 0:
            return 0.18
        widths = peak_widths(y, indices, rel_height=0.5)[0]
        step = abs(float(np.nanmedian(np.diff(x)))) if len(x) > 1 else 0.02
        return float(np.clip(np.nanmedian(widths) * step, 0.05, 0.35))

    def observed_peak_positions(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        return np.asarray([peak.two_theta for peak in self.observed_peaks(x, y, 0.18)], dtype=float)

    def observed_peaks(self, x: np.ndarray, y: np.ndarray, fwhm: float) -> list[ObservedPeak]:
        if len(x) < 5 or float(np.nanmax(y)) <= 0:
            return []
        prominence = max(float(np.nanmax(y)) * 0.03, 1.0)
        indices, _properties = find_peaks(y, prominence=prominence, distance=max(3, len(y) // 1000))
        if len(indices) > 150:
            heights = y[indices]
            indices = indices[np.argsort(heights)[-150:]]
        ordered = indices[np.argsort(np.asarray(x, dtype=float)[indices])]
        return [
            ObservedPeak(
                two_theta=float(x[index]),
                intensity=float(y[index]),
                fwhm=float(fwhm),
            )
            for index in ordered
        ]
