from __future__ import annotations

import numpy as np
from scipy.signal import find_peaks, peak_widths

from xrd_manager.finder.models import (
    FinderCandidateInput,
    FinderCandidateResult,
    FinderInput,
    FinderResult,
)
from xrd_manager.io.cif_loader import create_phase_from_cif
from xrd_manager.io.xy_loader import load_xy
from xrd_manager.services.calculated_pattern_service import (
    CU_KA1_WAVELENGTH,
    CalculatedPatternService,
    HKLPeak,
    calculated_profile_from_peaks,
    radiation_lines_from_wavelength,
)


class FinderService:
    """Standalone phase-finder core.

    This class intentionally knows nothing about project trees, Qt widgets, or
    ecosystem workflows. GUI apps and future command-line/packaged tools should
    translate their state into FinderInput and render FinderResult.
    """

    def __init__(self, calculated_pattern_service: CalculatedPatternService | None = None) -> None:
        self.calculated_pattern_service = calculated_pattern_service or CalculatedPatternService()

    def run(self, finder_input: FinderInput) -> FinderResult:
        observed = load_xy(finder_input.pattern_path)
        x_grid = np.asarray(observed[:, 0], dtype=float)
        observed_y = np.asarray(observed[:, 1], dtype=float)
        background = self._estimate_background(observed_y)
        target_y = np.clip(observed_y - background, 0.0, None)
        wavelength = finder_input.wavelength or CU_KA1_WAVELENGTH
        primary_wavelength = radiation_lines_from_wavelength(wavelength)[0][0]
        fwhm = finder_input.fwhm or self._estimate_fwhm(x_grid, target_y)
        observed_peaks = self._observed_peak_positions(x_grid, target_y)

        candidate_data = []
        for candidate in finder_input.candidates:
            try:
                _phase, structure = create_phase_from_cif(candidate.cif_path)
                two_theta_min = finder_input.two_theta_min or float(np.nanmin(x_grid))
                two_theta_max = finder_input.two_theta_max or float(np.nanmax(x_grid))
                peaks = self.calculated_pattern_service.calculate_sticks(
                    structure,
                    two_theta_min=two_theta_min,
                    two_theta_max=two_theta_max,
                    wavelength=primary_wavelength,
                    use_lp=True,
                )
            except Exception:
                continue
            candidate_data.append((candidate, peaks))

        global_zero = self._estimate_global_zero_shift(candidate_data, observed_peaks)
        profiles = []
        for candidate, peaks in candidate_data:
            adjusted = self._shift_peaks(peaks, global_zero)
            _x, profile = calculated_profile_from_peaks(
                adjusted,
                x_grid,
                fwhm=fwhm,
                wavelength=wavelength,
            )
            profiles.append((candidate, adjusted, profile))

        scales = self._fit_scales(target_y, [profile for _candidate, _peaks, profile in profiles])
        total_scale = float(np.sum(scales)) if len(scales) else 0.0
        calculated_total = np.zeros_like(x_grid)
        results = []
        for (candidate, peaks, profile), scale in zip(profiles, scales):
            scaled_profile = profile * float(scale)
            calculated_total += scaled_profile
            matched, total = self._count_matches(peaks, observed_peaks)
            score = float(matched / max(total, 1))
            results.append(
                FinderCandidateResult(
                    entry_id=candidate.entry_id,
                    name=candidate.name,
                    formula=candidate.formula,
                    source=candidate.source,
                    scale=float(scale),
                    quantity_percent=float(scale / total_scale * 100.0) if total_scale else 0.0,
                    score=score,
                    matched_peaks=matched,
                    total_peaks=total,
                    status=self._status(score, matched, total),
                    two_theta=x_grid.tolist(),
                    profile=scaled_profile.tolist(),
                    peak_two_theta=[float(peak.two_theta) for peak in peaks],
                )
            )

        return FinderResult(
            pattern_x=x_grid.tolist(),
            pattern_y=observed_y.tolist(),
            background=background.tolist(),
            calculated_total=(calculated_total + background).tolist(),
            global_zero_shift=float(global_zero),
            fwhm=float(fwhm),
            candidates=results,
        )

    def _estimate_background(self, y: np.ndarray) -> np.ndarray:
        if len(y) < 5:
            return np.zeros_like(y)
        window = max(31, (len(y) // 80) | 1)
        padded = np.pad(y, (window // 2, window // 2), mode="edge")
        baseline = np.empty_like(y, dtype=float)
        for index in range(len(y)):
            baseline[index] = float(np.nanpercentile(padded[index:index + window], 15))
        return baseline

    def _estimate_fwhm(self, x: np.ndarray, y: np.ndarray) -> float:
        if len(x) < 5 or float(np.nanmax(y)) <= 0:
            return 0.18
        prominence = max(float(np.nanmax(y)) * 0.08, 1.0)
        indices, _properties = find_peaks(y, prominence=prominence, distance=max(3, len(y) // 1000))
        if len(indices) == 0:
            return 0.18
        widths = peak_widths(y, indices, rel_height=0.5)[0]
        step = abs(float(np.nanmedian(np.diff(x)))) if len(x) > 1 else 0.02
        return float(np.clip(np.nanmedian(widths) * step, 0.05, 0.35))

    def _observed_peak_positions(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        if len(x) < 5 or float(np.nanmax(y)) <= 0:
            return np.array([], dtype=float)
        prominence = max(float(np.nanmax(y)) * 0.03, 1.0)
        indices, _properties = find_peaks(y, prominence=prominence, distance=max(3, len(y) // 1000))
        if len(indices) > 150:
            heights = y[indices]
            indices = indices[np.argsort(heights)[-150:]]
        return np.sort(x[indices])

    def _estimate_global_zero_shift(
        self,
        candidate_data: list[tuple[FinderCandidateInput, list[HKLPeak]]],
        observed_positions: np.ndarray,
    ) -> float:
        if len(observed_positions) == 0:
            return 0.0
        deltas = []
        weights = []
        for _candidate, peaks in candidate_data:
            strong = sorted(
                [peak for peak in peaks if peak.intensity >= 8.0],
                key=lambda peak: peak.intensity,
                reverse=True,
            )[:25]
            for peak in strong:
                nearest_index = int(np.argmin(np.abs(observed_positions - peak.two_theta)))
                delta = float(observed_positions[nearest_index] - peak.two_theta)
                if abs(delta) <= 0.4:
                    deltas.append(delta)
                    weights.append(max(float(peak.intensity), 1.0))
        if len(deltas) < 3:
            return 0.0
        deltas = np.asarray(deltas, dtype=float)
        weights = np.asarray(weights, dtype=float)
        center = float(np.average(deltas, weights=weights))
        keep = np.abs(deltas - center) <= 0.15
        if np.count_nonzero(keep) >= 3:
            center = float(np.average(deltas[keep], weights=weights[keep]))
        return float(np.clip(center, -0.5, 0.5))

    def _shift_peaks(self, peaks: list[HKLPeak], zero_shift: float) -> list[HKLPeak]:
        return [
            HKLPeak(
                h=peak.h,
                k=peak.k,
                l=peak.l,
                d=peak.d,
                two_theta=float(peak.two_theta) + zero_shift,
                intensity=peak.intensity,
                multiplicity=peak.multiplicity,
                f2=peak.f2,
                lp=peak.lp,
                raw_intensity=peak.raw_intensity,
            )
            for peak in peaks
        ]

    def _fit_scales(self, target_y: np.ndarray, profiles: list[np.ndarray]) -> np.ndarray:
        if not profiles:
            return np.array([], dtype=float)
        matrix = np.column_stack(profiles)
        try:
            scales, *_rest = np.linalg.lstsq(matrix, target_y, rcond=None)
        except Exception:
            scales = np.ones(len(profiles), dtype=float)
        scales = np.clip(np.asarray(scales, dtype=float), 0.0, None)
        if not np.any(scales):
            scales = np.ones(len(profiles), dtype=float)
        return scales

    def _count_matches(self, peaks: list[HKLPeak], observed_positions: np.ndarray) -> tuple[int, int]:
        strong = sorted(
            [peak for peak in peaks if peak.intensity >= 5.0],
            key=lambda peak: peak.intensity,
            reverse=True,
        )[:30]
        matched = 0
        for peak in strong:
            if len(observed_positions) and float(np.min(np.abs(observed_positions - peak.two_theta))) <= 0.25:
                matched += 1
        return matched, len(strong)

    def _status(self, score: float, matched: int, total: int) -> str:
        if matched < 2:
            return "weak"
        if score >= 0.35:
            return "good"
        if score >= 0.18:
            return "ok"
        return "weak"
