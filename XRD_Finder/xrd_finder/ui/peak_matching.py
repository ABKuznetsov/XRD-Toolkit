from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.signal import find_peaks


@dataclass(slots=True)
class PhaseAlignmentEstimate:
    zero_shift: float = 0.0
    matched_peaks: int = 0
    total_peaks: int = 0
    score: float = float("inf")
    status: str = "unmatched"


def nearest_index(sorted_values: np.ndarray, value: float) -> int:
    index = int(np.searchsorted(sorted_values, value, side="left"))
    if index <= 0:
        return 0
    if index >= len(sorted_values):
        return len(sorted_values) - 1
    before = index - 1
    return before if abs(float(sorted_values[before]) - value) <= abs(float(sorted_values[index]) - value) else index


def observed_peak_positions(x, corrected_y) -> np.ndarray:
    y = np.asarray(corrected_y, dtype=float)
    if len(y) < 5 or float(np.nanmax(y)) <= 0:
        return np.array([], dtype=float)
    prominence = max(float(np.nanmax(y)) * 0.04, float(np.nanstd(y)) * 3.5, 1.0)
    peak_indices, _properties = find_peaks(y, prominence=prominence, distance=max(5, len(y) // 700))
    if len(peak_indices) > 80:
        heights = y[peak_indices]
        keep = np.argsort(heights)[-80:]
        peak_indices = peak_indices[keep]
    return np.sort(np.asarray(x, dtype=float)[peak_indices])


def observed_peak_records(x, corrected_y, limit: int = 24) -> list[tuple[float, float]]:
    y = np.asarray(corrected_y, dtype=float)
    x_values = np.asarray(x, dtype=float)
    if len(y) < 5 or float(np.nanmax(y)) <= 0:
        return []
    prominence = max(float(np.nanmax(y)) * 0.025, float(np.nanstd(y)) * 2.5, 1.0)
    peak_indices, _properties = find_peaks(y, prominence=prominence, distance=max(5, len(y) // 800))
    if len(peak_indices) == 0:
        return []
    records = [
        (float(x_values[index]), max(float(y[index]), 0.0))
        for index in peak_indices
        if np.isfinite(x_values[index]) and np.isfinite(y[index]) and y[index] > 0
    ]
    records.sort(key=lambda item: item[1], reverse=True)
    return records[:limit]


def estimate_phase_alignment(peaks, observed_positions: np.ndarray, structure) -> PhaseAlignmentEstimate:
    if len(observed_positions) == 0 or not peaks:
        return PhaseAlignmentEstimate()
    strong_peaks = [
        peak
        for peak in peaks
        if getattr(peak, "intensity", 0.0) >= 5.0 and 5.0 <= getattr(peak, "two_theta", 0.0) <= 120.0
    ]
    strong_peaks = sorted(strong_peaks, key=lambda peak: peak.intensity, reverse=True)[:35]
    pairs = []
    for peak in strong_peaks:
        calc_tt = float(peak.two_theta)
        nearest = nearest_index(observed_positions, calc_tt)
        obs_tt = float(observed_positions[nearest])
        delta = obs_tt - calc_tt
        if abs(delta) > 0.45:
            continue
        pairs.append((peak, obs_tt))
    total_peaks = len(strong_peaks)
    if len(pairs) < 3:
        return PhaseAlignmentEstimate(matched_peaks=len(pairs), total_peaks=total_peaks, status="weak")
    residuals = []
    weights = []
    for peak, obs_tt in pairs:
        residuals.append(obs_tt - float(peak.two_theta))
        weights.append(max(float(getattr(peak, "intensity", 1.0)), 1.0))
    residuals = np.asarray(residuals, dtype=float)
    weights = np.asarray(weights, dtype=float)
    best_zero = float(np.average(residuals, weights=weights))
    centered = residuals - best_zero
    best_score = float(np.average(np.abs(centered), weights=weights))
    if not np.isfinite(best_score):
        return PhaseAlignmentEstimate(matched_peaks=len(pairs), total_peaks=total_peaks, status="weak")

    matched_fraction = len(pairs) / max(total_peaks, 1)
    if best_score > 0.18 or matched_fraction < 0.18:
        return PhaseAlignmentEstimate(
            matched_peaks=len(pairs),
            total_peaks=total_peaks,
            score=best_score,
            status="weak",
        )
    status = "good" if best_score <= 0.08 and matched_fraction >= 0.3 else "ok"
    return PhaseAlignmentEstimate(
        zero_shift=float(np.clip(best_zero, -0.5, 0.5)),
        matched_peaks=len(pairs),
        total_peaks=total_peaks,
        score=best_score,
        status=f"{status} shift-only",
    )


def peak_probability_from_alignment(alignment: PhaseAlignmentEstimate) -> float:
    if alignment.total_peaks <= 0:
        return 0.0
    matched_fraction = alignment.matched_peaks / max(alignment.total_peaks, 1)
    residual_penalty = 1.0
    if alignment.score > 0:
        residual_penalty = max(0.15, 1.0 - min(alignment.score / 0.45, 1.0))
    enough_peaks_factor = min(alignment.matched_peaks / 8.0, 1.0)
    return float(np.clip(100.0 * matched_fraction * residual_penalty * enough_peaks_factor, 0.0, 100.0))


def peak_presence_probability(peaks, observed_x: np.ndarray, corrected_y: np.ndarray, structure) -> float:
    records = observed_peak_records(observed_x, corrected_y, limit=32)
    if not records or not peaks:
        return 0.0
    observed_positions = np.asarray([position for position, _height in records], dtype=float)
    strong_calc = [
        peak
        for peak in peaks
        if getattr(peak, "intensity", 0.0) >= 2.0 and 5.0 <= getattr(peak, "two_theta", 0.0) <= 120.0
    ]
    strong_calc = sorted(strong_calc, key=lambda peak: float(getattr(peak, "intensity", 0.0)), reverse=True)[:36]
    if not strong_calc:
        return 0.0
    alignment = estimate_phase_alignment(strong_calc, observed_positions, structure)
    zero_shift = alignment.zero_shift if alignment.matched_peaks >= 3 else 0.0
    calc_positions = np.asarray([float(peak.two_theta) + zero_shift for peak in strong_calc], dtype=float)
    calc_intensities = np.asarray([max(float(getattr(peak, "intensity", 0.0)), 1.0) for peak in strong_calc], dtype=float)

    tolerance = 0.45
    observed_weighted = 0.0
    observed_total = 0.0
    for obs_position, obs_height in records[:24]:
        weight = max(obs_height, 1.0) ** 0.65
        observed_total += weight
        nearest = _nearest_delta(calc_positions, obs_position)
        if nearest <= tolerance:
            quality = max(0.0, 1.0 - nearest / tolerance)
            observed_weighted += weight * (0.45 + 0.55 * quality)
    observed_coverage = observed_weighted / observed_total if observed_total > 0 else 0.0

    top_count = min(14, len(calc_positions))
    calc_weighted = 0.0
    calc_total = 0.0
    for calc_position, calc_intensity in zip(calc_positions[:top_count], calc_intensities[:top_count]):
        weight = max(calc_intensity, 1.0) ** 0.55
        calc_total += weight
        nearest = _nearest_delta(observed_positions, calc_position)
        if nearest <= tolerance:
            quality = max(0.0, 1.0 - nearest / tolerance)
            calc_weighted += weight * (0.45 + 0.55 * quality)
    calc_coverage = calc_weighted / calc_total if calc_total > 0 else 0.0

    alignment_probability = peak_probability_from_alignment(alignment) / 100.0
    matched_factor = min(alignment.matched_peaks / 12.0, 1.0)
    diagnostic_score = max(calc_coverage, alignment_probability)
    probability = 100.0 * (
        0.52 * diagnostic_score
        + 0.28 * observed_coverage
        + 0.20 * matched_factor
    )
    top_calc_matches = 0
    for calc_position in calc_positions[:min(8, len(calc_positions))]:
        if _nearest_delta(observed_positions, calc_position) <= tolerance:
            top_calc_matches += 1
    if top_calc_matches < 1:
        probability = min(probability, 25.0)
    elif top_calc_matches < 2:
        probability = min(probability, 55.0)
    if alignment.score > 0.22:
        probability *= max(0.85, 1.0 - min((alignment.score - 0.22) / 0.5, 0.15))
    return float(np.clip(probability, 0.0, 100.0))


def _nearest_delta(sorted_values: np.ndarray, value: float) -> float:
    if len(sorted_values) == 0:
        return 999.0
    index = nearest_index(sorted_values, float(value))
    return abs(float(sorted_values[index]) - float(value))
