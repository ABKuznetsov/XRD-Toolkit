from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import nnls
from scipy.signal import find_peaks

from xrd_finder.finder.assignment_builder import AssignmentBuilder, nearest_index as nearest_peak_index, nearest_phase_peak
from xrd_finder.finder.context import CalculationContext
from xrd_finder.finder.models import (
    FinderCandidateInput,
    FinderCandidateResult,
    FinderInput,
    FinderResult,
    ObservedPeak,
)
from xrd_finder.finder.observed_pattern_processor import ObservedPatternProcessor
from xrd_finder.finder.profile_calculator import CachedProfileCalculator, array_fingerprint
from xrd_finder.services.calculated_pattern_service import (
    CU_KA1_WAVELENGTH,
    CalculatedPatternService,
    HKLPeak,
    radiation_lines_from_wavelength,
)


@dataclass(frozen=True, slots=True)
class FinderHeuristics:
    trusted_peak_tolerance: float = 0.38
    zero_outlier_tolerance: float = 0.14
    zero_consensus_tolerance: float = 0.12
    trusted_zero_max_residual: float = 0.18
    zero_consensus_min_residual: float = 0.16
    zero_consensus_residual_margin: float = 0.08
    zero_min_matched_fraction: float = 0.18
    zero_max_residual: float = 0.22
    trusted_peak_intensity_min: float = 6.0
    strong_peak_intensity_min: float = 8.0
    zero_candidate_peak_tolerance: float = 0.4
    cell_scale_peak_tolerance: float = 0.35
    cell_scale_min: float = 0.97
    cell_scale_max: float = 1.03
    match_tolerance: float = 0.25
    match_peak_intensity_min: float = 5.0
    good_score: float = 0.35
    ok_score: float = 0.18
    snap_min_delta: float = 0.08
    snap_max_delta: float = 0.45
    snap_intensity_min: float = 4.0


class FinderService:
    """Standalone phase-finder core.

    This class intentionally knows nothing about project trees, Qt widgets, or
    ecosystem workflows. GUI apps and future command-line/packaged tools should
    translate their state into FinderInput and render FinderResult.
    """

    def __init__(
        self,
        calculated_pattern_service: CalculatedPatternService | None = None,
        sticks_cache_limit: int = 256,
        profile_cache_limit: int = 256,
        profile_cache_max_bytes: int = 128 * 1024 * 1024,
        heuristics: FinderHeuristics | None = None,
    ) -> None:
        self.calculated_pattern_service = calculated_pattern_service or CalculatedPatternService()
        self.heuristics = heuristics or FinderHeuristics()
        self.profile_calculator = CachedProfileCalculator(
            self.calculated_pattern_service,
            sticks_cache_limit=sticks_cache_limit,
            profile_cache_limit=profile_cache_limit,
            profile_cache_max_bytes=profile_cache_max_bytes,
        )
        self.assignment_builder = AssignmentBuilder()
        self.observed_processor = ObservedPatternProcessor()

    def run(self, finder_input: FinderInput) -> FinderResult:
        observed = self.observed_processor.prepare(finder_input)
        x_grid = observed.x_grid
        wavelength = finder_input.wavelength or CU_KA1_WAVELENGTH
        primary_wavelength = radiation_lines_from_wavelength(wavelength)[0][0]

        candidate_data = []
        two_theta_min = finder_input.two_theta_min or float(np.nanmin(x_grid))
        two_theta_max = finder_input.two_theta_max or float(np.nanmax(x_grid))
        context = CalculationContext(
            wavelength=float(wavelength),
            primary_wavelength=float(primary_wavelength),
            fwhm=float(observed.fwhm),
            two_theta_min=float(two_theta_min),
            two_theta_max=float(two_theta_max),
            x_grid_fingerprint=array_fingerprint(x_grid),
        )
        for candidate in finder_input.candidates:
            try:
                peaks = self.profile_calculator.candidate_sticks(
                    candidate.cif_path,
                    context=context,
                    use_lp=True,
                )
            except Exception:
                continue
            candidate_data.append((candidate, peaks))

        trusted_zero = self._estimate_global_zero_shift_from_trusted_assignments(candidate_data, observed.peaks)
        global_zero = (
            trusted_zero
            if trusted_zero is not None
            else self._estimate_global_zero_shift(candidate_data, observed.peak_positions)
        )
        profiles = []
        for candidate, peaks in candidate_data:
            cell_scale = self._estimate_phase_cell_scale(peaks, observed.peak_positions, global_zero, context.primary_wavelength)
            phase_context = context.with_alignment(global_zero, cell_scale)
            reference_peaks = self._apply_peak_model(peaks, phase_context)
            adjusted = (
                self._snap_peaks_to_observed(reference_peaks, observed.peak_positions)
                if finder_input.snap_peak_positions
                else reference_peaks
            )
            profile = self.profile_calculator.profile_from_peaks(
                adjusted,
                x_grid,
                context=phase_context,
            )
            profiles.append((candidate, reference_peaks, adjusted, profile, cell_scale))

        scales = self._fit_scales(observed.target_y, [profile for _candidate, _reference_peaks, _peaks, profile, _cell_scale in profiles])
        total_scale = float(np.sum(scales)) if len(scales) else 0.0
        calculated_total = np.zeros_like(x_grid)
        results = []
        assignment_phase_sets = []
        for (candidate, reference_peaks, peaks, profile, cell_scale), scale in zip(profiles, scales):
            scaled_profile = profile * float(scale)
            calculated_total += scaled_profile
            matched, total = self._count_matches(peaks, observed.peak_positions)
            score = float(matched / max(total, 1))
            candidate_result = FinderCandidateResult(
                candidate_key=self._candidate_key(candidate),
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
                cell_scale=float(cell_scale),
                two_theta=x_grid.tolist(),
                profile=scaled_profile.tolist(),
                peak_two_theta=[float(peak.two_theta) for peak in peaks],
                peak_reference_two_theta=[float(peak.two_theta) for peak in reference_peaks],
                peak_intensity=[float(peak.intensity) for peak in peaks],
            )
            results.append(candidate_result)
            if float(scale) > 1e-9:
                assignment_phase_sets.append((candidate_result, peaks))

        assigned_peaks = self.assignment_builder.assign_observed_peaks(
            observed.peaks,
            assignment_phase_sets,
            tolerance=max(0.28, min(0.55, observed.fwhm * 2.8)),
        )

        return FinderResult(
            pattern_x=x_grid.tolist(),
            pattern_y=observed.observed_y.tolist(),
            background=observed.background.tolist(),
            calculated_total=(calculated_total + observed.background).tolist(),
            global_zero_shift=float(global_zero),
            fwhm=float(observed.fwhm),
            candidates=results,
            observed_peaks=assigned_peaks,
        )

    def cache_info(self) -> dict[str, int]:
        return self.profile_calculator.cache_info()

    def _candidate_key(self, candidate: FinderCandidateInput) -> str:
        if candidate.entry_id:
            return f"{candidate.source or 'UNKNOWN'}:{candidate.entry_id}"
        if candidate.source and candidate.formula:
            return f"{candidate.source}:{candidate.formula}"
        return candidate.cif_path

    def _estimate_global_zero_shift(
        self,
        candidate_data: list[tuple[FinderCandidateInput, list[HKLPeak]]],
        observed_positions: np.ndarray,
    ) -> float:
        if len(observed_positions) == 0:
            return 0.0
        estimates = []
        for _candidate, peaks in candidate_data:
            estimate = self._candidate_zero_shift_estimate(peaks, observed_positions)
            if estimate is not None:
                estimates.append(estimate)
        if not estimates:
            return 0.0
        estimates.sort(key=lambda item: item["quality"], reverse=True)
        best = estimates[0]
        consensus = [
            item
            for item in estimates
            if abs(float(item["zero"]) - float(best["zero"])) <= self.heuristics.zero_consensus_tolerance
            and float(item["residual"]) <= max(
                self.heuristics.zero_consensus_min_residual,
                float(best["residual"]) + self.heuristics.zero_consensus_residual_margin,
            )
        ]
        if not consensus:
            consensus = [best]
        zeros = np.asarray([item["zero"] for item in consensus], dtype=float)
        weights = np.asarray([item["quality"] for item in consensus], dtype=float)
        center = float(np.average(zeros, weights=weights))
        return float(np.clip(center, -0.5, 0.5))

    def _estimate_global_zero_shift_from_trusted_assignments(
        self,
        candidate_data: list[tuple[FinderCandidateInput, list[HKLPeak]]],
        observed_peaks: list[ObservedPeak],
    ) -> float | None:
        if not candidate_data or len(observed_peaks) < 3:
            return None
        deltas = []
        weights = []
        for observed in observed_peaks:
            possible = []
            for _candidate, peaks in candidate_data:
                nearest = nearest_phase_peak(observed.two_theta, peaks, tolerance=self.heuristics.trusted_peak_tolerance)
                if nearest is None:
                    continue
                peak, delta = nearest
                if peak.intensity < self.heuristics.trusted_peak_intensity_min:
                    continue
                possible.append((peak, delta))
            if len(possible) != 1:
                continue
            peak, delta = possible[0]
            deltas.append(float(delta))
            weights.append(max(float(observed.intensity), 1.0) * max(float(peak.intensity), 1.0))
        if len(deltas) < 3:
            return None
        deltas_array = np.asarray(deltas, dtype=float)
        weights_array = np.asarray(weights, dtype=float)
        center = float(np.average(deltas_array, weights=weights_array))
        keep = np.abs(deltas_array - center) <= self.heuristics.zero_outlier_tolerance
        if np.count_nonzero(keep) >= 3:
            deltas_array = deltas_array[keep]
            weights_array = weights_array[keep]
            center = float(np.average(deltas_array, weights=weights_array))
        residual = float(np.average(np.abs(deltas_array - center), weights=weights_array))
        if len(deltas_array) < 3 or residual > self.heuristics.trusted_zero_max_residual:
            return None
        return float(np.clip(center, -0.5, 0.5))

    def _candidate_zero_shift_estimate(self, peaks: list[HKLPeak], observed_positions: np.ndarray) -> dict[str, float] | None:
        strong = sorted(
            [peak for peak in peaks if peak.intensity >= self.heuristics.strong_peak_intensity_min],
            key=lambda peak: peak.intensity,
            reverse=True,
        )[:25]
        if len(strong) < 3:
            return None
        deltas = []
        weights = []
        for peak in strong:
            index = nearest_peak_index(observed_positions, float(peak.two_theta))
            delta = float(observed_positions[index] - peak.two_theta)
            if abs(delta) <= self.heuristics.zero_candidate_peak_tolerance:
                deltas.append(delta)
                weights.append(max(float(peak.intensity), 1.0))
        if len(deltas) < 3:
            return None
        deltas_array = np.asarray(deltas, dtype=float)
        weights_array = np.asarray(weights, dtype=float)
        center = float(np.average(deltas_array, weights=weights_array))
        keep = np.abs(deltas_array - center) <= self.heuristics.zero_outlier_tolerance
        if np.count_nonzero(keep) >= 3:
            deltas_array = deltas_array[keep]
            weights_array = weights_array[keep]
            center = float(np.average(deltas_array, weights=weights_array))
        residual = float(np.average(np.abs(deltas_array - center), weights=weights_array))
        matched_fraction = len(deltas_array) / max(len(strong), 1)
        if (
            len(deltas_array) < 3
            or matched_fraction < self.heuristics.zero_min_matched_fraction
            or residual > self.heuristics.zero_max_residual
        ):
            return None
        quality = (len(deltas_array) * matched_fraction * float(np.nanmean(weights_array))) / (residual + 0.03)
        return {
            "zero": float(np.clip(center, -0.5, 0.5)),
            "residual": residual,
            "quality": max(quality, 1e-6),
        }

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

    def _estimate_phase_cell_scale(
        self,
        peaks: list[HKLPeak],
        observed_positions: np.ndarray,
        zero_shift: float,
        wavelength: float,
    ) -> float:
        if len(observed_positions) == 0:
            return 1.0
        strong = sorted(
            [peak for peak in peaks if peak.intensity >= self.heuristics.strong_peak_intensity_min and peak.d > 0],
            key=lambda peak: peak.intensity,
            reverse=True,
        )[:30]
        if len(strong) < 4:
            return 1.0
        scales = []
        weights = []
        before_residuals = []
        for peak in strong:
            predicted = float(peak.two_theta) + zero_shift
            index = nearest_peak_index(observed_positions, predicted)
            observed_two_theta = float(observed_positions[index])
            delta = observed_two_theta - predicted
            if abs(delta) > self.heuristics.cell_scale_peak_tolerance:
                continue
            d_observed = self._d_from_two_theta(observed_two_theta - zero_shift, wavelength)
            if d_observed is None:
                continue
            scales.append(d_observed / float(peak.d))
            weights.append(max(float(peak.intensity), 1.0))
            before_residuals.append(abs(delta))
        if len(scales) < 4:
            return 1.0
        scales_array = np.asarray(scales, dtype=float)
        weights_array = np.asarray(weights, dtype=float)
        center = float(np.average(scales_array, weights=weights_array))
        keep = np.abs(scales_array - center) <= 0.004
        if np.count_nonzero(keep) >= 4:
            scales_array = scales_array[keep]
            weights_array = weights_array[keep]
            center = float(np.average(scales_array, weights=weights_array))
        if not self.heuristics.cell_scale_min <= center <= self.heuristics.cell_scale_max:
            return 1.0
        after_residuals = []
        for peak in strong:
            shifted = self._two_theta_from_scaled_d(peak.d, center, wavelength)
            if shifted is None:
                continue
            predicted = shifted + zero_shift
            index = nearest_peak_index(observed_positions, predicted)
            delta = float(observed_positions[index] - predicted)
            if abs(delta) <= self.heuristics.cell_scale_peak_tolerance:
                after_residuals.append(abs(delta))
        if len(after_residuals) < 4:
            return 1.0
        before = float(np.nanmedian(before_residuals))
        after = float(np.nanmedian(after_residuals))
        if after > before * 0.9:
            return 1.0
        return float(np.clip(center, self.heuristics.cell_scale_min, self.heuristics.cell_scale_max))

    def _apply_peak_model(
        self,
        peaks: list[HKLPeak],
        context: CalculationContext,
    ) -> list[HKLPeak]:
        zero_shift = context.global_zero_shift
        cell_scale = context.cell_scale
        if abs(cell_scale - 1.0) < 1e-7:
            return self._shift_peaks(peaks, zero_shift)
        adjusted = []
        for peak in peaks:
            d_scaled = float(peak.d) * float(cell_scale)
            two_theta = self._two_theta_from_d(d_scaled, context.primary_wavelength)
            if two_theta is None:
                continue
            adjusted.append(
                HKLPeak(
                    h=peak.h,
                    k=peak.k,
                    l=peak.l,
                    d=d_scaled,
                    two_theta=two_theta + zero_shift,
                    intensity=peak.intensity,
                    multiplicity=peak.multiplicity,
                    f2=peak.f2,
                    lp=peak.lp,
                    raw_intensity=peak.raw_intensity,
                )
            )
        return adjusted

    def _two_theta_from_scaled_d(self, d_spacing: float, cell_scale: float, wavelength: float) -> float | None:
        return self._two_theta_from_d(float(d_spacing) * float(cell_scale), wavelength)

    def _two_theta_from_d(self, d_spacing: float, wavelength: float) -> float | None:
        if d_spacing <= 0:
            return None
        argument = float(wavelength) / (2.0 * float(d_spacing))
        if not 0.0 < argument < 1.0:
            return None
        return float(np.rad2deg(2.0 * np.arcsin(argument)))

    def _d_from_two_theta(self, two_theta: float, wavelength: float) -> float | None:
        theta = np.deg2rad(float(two_theta) / 2.0)
        sine = float(np.sin(theta))
        if sine <= 0:
            return None
        return float(wavelength) / (2.0 * sine)

    def _snap_peaks_to_observed(
        self,
        peaks: list[HKLPeak],
        observed_positions: np.ndarray,
    ) -> list[HKLPeak]:
        if len(observed_positions) == 0:
            return peaks
        snapped = []
        for peak in peaks:
            two_theta = float(peak.two_theta)
            if peak.intensity >= self.heuristics.snap_intensity_min:
                index = nearest_peak_index(observed_positions, two_theta)
                observed_two_theta = float(observed_positions[index])
                delta = observed_two_theta - two_theta
                if self.heuristics.snap_min_delta <= abs(delta) <= self.heuristics.snap_max_delta:
                    two_theta = observed_two_theta
            snapped.append(
                HKLPeak(
                    h=peak.h,
                    k=peak.k,
                    l=peak.l,
                    d=peak.d,
                    two_theta=two_theta,
                    intensity=peak.intensity,
                    multiplicity=peak.multiplicity,
                    f2=peak.f2,
                    lp=peak.lp,
                    raw_intensity=peak.raw_intensity,
                )
            )
        return snapped

    def _fit_scales(self, target_y: np.ndarray, profiles: list[np.ndarray]) -> np.ndarray:
        if not profiles:
            return np.array([], dtype=float)
        matrix = np.column_stack(profiles)
        weights = self._fit_weights(target_y)
        try:
            scales, _residual = nnls(matrix * weights[:, None], target_y * weights)
        except Exception:
            try:
                scales, *_rest = np.linalg.lstsq(matrix * weights[:, None], target_y * weights, rcond=None)
            except Exception:
                scales = np.ones(len(profiles), dtype=float)
        scales = np.clip(np.asarray(scales, dtype=float), 0.0, None)
        if not np.any(scales):
            scales = np.ones(len(profiles), dtype=float)
        return scales

    def _fit_weights(self, target_y: np.ndarray) -> np.ndarray:
        y = np.asarray(target_y, dtype=float)
        if len(y) == 0:
            return np.ones_like(y)
        positive = np.clip(y, 0.0, None)
        noise_floor = max(float(np.nanpercentile(positive, 55)), 1.0)
        high_cap = max(float(np.nanpercentile(positive, 96)), noise_floor)
        compressed = np.sqrt(np.clip(positive, noise_floor, high_cap))
        weights = 1.0 / compressed
        peak_indices, _properties = find_peaks(
            positive,
            prominence=max(float(np.nanpercentile(positive, 98)) * 0.025, float(np.nanstd(positive)) * 2.0, 1.0),
            distance=max(3, len(positive) // 1000),
        )
        half_width = max(2, len(positive) // 900)
        for index in peak_indices:
            left = max(0, index - half_width)
            right = min(len(positive), index + half_width + 1)
            weights[left:right] *= 2.5
        return weights / max(float(np.nanmedian(weights)), 1e-9)

    def _count_matches(self, peaks: list[HKLPeak], observed_positions: np.ndarray) -> tuple[int, int]:
        strong = sorted(
            [peak for peak in peaks if peak.intensity >= self.heuristics.match_peak_intensity_min],
            key=lambda peak: peak.intensity,
            reverse=True,
        )[:30]
        matched = 0
        for peak in strong:
            if len(observed_positions):
                index = nearest_peak_index(observed_positions, float(peak.two_theta))
                if abs(float(observed_positions[index]) - float(peak.two_theta)) <= self.heuristics.match_tolerance:
                    matched += 1
        return matched, len(strong)

    def _status(self, score: float, matched: int, total: int) -> str:
        if matched < 2:
            return "weak"
        if score >= self.heuristics.good_score:
            return "good"
        if score >= self.heuristics.ok_score:
            return "ok"
        return "weak"
