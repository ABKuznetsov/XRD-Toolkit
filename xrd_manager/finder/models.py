from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class FinderCandidateInput:
    cif_path: str
    entry_id: str = ""
    name: str = ""
    formula: str = ""
    source: str = ""


@dataclass(slots=True)
class FinderInput:
    pattern_path: str
    candidates: list[FinderCandidateInput]
    wavelength: float | None = None
    two_theta_min: float | None = None
    two_theta_max: float | None = None
    fwhm: float | None = None


@dataclass(slots=True)
class FinderCandidateResult:
    entry_id: str
    name: str
    formula: str
    source: str
    scale: float = 0.0
    quantity_percent: float = 0.0
    score: float = 0.0
    matched_peaks: int = 0
    total_peaks: int = 0
    status: str = "unmatched"
    two_theta: list[float] = field(default_factory=list)
    profile: list[float] = field(default_factory=list)
    peak_two_theta: list[float] = field(default_factory=list)


@dataclass(slots=True)
class FinderResult:
    pattern_x: list[float]
    pattern_y: list[float]
    background: list[float]
    calculated_total: list[float]
    global_zero_shift: float
    fwhm: float
    candidates: list[FinderCandidateResult]
