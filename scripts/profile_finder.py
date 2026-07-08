from __future__ import annotations

import argparse
import cProfile
import pstats
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = ROOT / "XRD_Finder"
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from xrd_finder.finder.models import FinderCandidateInput, FinderInput  # noqa: E402


def load_finder_service_class():
    try:
        from xrd_finder.finder.service import FinderService
    except ModuleNotFoundError as exc:
        missing = exc.name or "dependency"
        raise SystemExit(
            f"Missing Python dependency: {missing}. Install project requirements before profiling."
        ) from exc
    return FinderService


def candidate_inputs(paths: list[Path]) -> list[FinderCandidateInput]:
    candidates = []
    for path in paths:
        candidates.append(
            FinderCandidateInput(
                cif_path=str(path),
                entry_id=path.stem,
                name=path.stem,
                source="PROFILE",
            )
        )
    return candidates


def collect_cifs(paths: list[Path], limit: int | None) -> list[Path]:
    cifs = []
    for path in paths:
        if path.is_dir():
            cifs.extend(sorted(item for item in path.rglob("*.cif") if item.is_file()))
        elif path.is_file() and path.suffix.lower() == ".cif":
            cifs.append(path)
    if limit is not None:
        cifs = cifs[: max(0, int(limit))]
    return cifs


def run_once(service: FinderService, finder_input: FinderInput):
    started = time.perf_counter()
    result = service.run(finder_input)
    elapsed = time.perf_counter() - started
    return result, elapsed


def profile_run(service: FinderService, finder_input: FinderInput, output: Path | None):
    profiler = cProfile.Profile()
    started = time.perf_counter()
    result = profiler.runcall(service.run, finder_input)
    elapsed = time.perf_counter() - started
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        profiler.dump_stats(str(output))
    return result, profiler, elapsed


def print_stats(profiler: cProfile.Profile, sort: str, limit: int) -> None:
    stats = pstats.Stats(profiler, stream=sys.stdout)
    stats.strip_dirs().sort_stats(sort).print_stats(limit)


def print_cache_info(service: FinderService) -> None:
    cache_info = getattr(service, "cache_info", lambda: {})()
    if cache_info:
        normalized = dict(cache_info)
        if "profile_bytes" in normalized:
            normalized["profile_mb"] = f"{normalized['profile_bytes'] / (1024 * 1024):.1f}"
        details = ", ".join(f"{name}={value}" for name, value in sorted(normalized.items()))
        print(f"cache: {details}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Profile FinderService on a real XRD pattern and CIF candidates.")
    parser.add_argument("--pattern", required=True, type=Path, help="Observed XRD pattern file (.xy/.txt/.dat/.csv/.xye).")
    parser.add_argument("--cif", required=True, nargs="+", type=Path, help="CIF files or folders containing CIF files.")
    parser.add_argument("--limit", type=int, default=100, help="Maximum number of CIF candidates to profile.")
    parser.add_argument("--repeat", type=int, default=1, help="Repeat runs after the profiled first run to measure cache reuse.")
    parser.add_argument("--wavelength", type=float, default=1.54051, help="Radiation wavelength; default Cu K-alpha.")
    parser.add_argument("--fwhm", type=float, default=None, help="Optional fixed FWHM.")
    parser.add_argument("--sort", default="cumtime", help="pstats sort key, for example cumtime, tottime, calls.")
    parser.add_argument("--stats-limit", type=int, default=40, help="Number of profiler rows to print.")
    parser.add_argument("--profile-output", type=Path, help="Optional .prof output path for snakeviz/gprof2dot.")
    parser.add_argument("--sticks-cache-limit", type=int, default=256, help="Maximum cached CIF-to-HKL entries.")
    parser.add_argument("--profile-cache-limit", type=int, default=256, help="Maximum cached calculated profiles.")
    parser.add_argument("--profile-cache-mb", type=float, default=128.0, help="Maximum calculated profile cache size in MiB.")
    args = parser.parse_args(argv)

    cifs = collect_cifs(args.cif, args.limit)
    if not cifs:
        raise SystemExit("No CIF files found.")

    FinderService = load_finder_service_class()
    service = FinderService(
        sticks_cache_limit=args.sticks_cache_limit,
        profile_cache_limit=args.profile_cache_limit,
        profile_cache_max_bytes=int(max(args.profile_cache_mb, 0.0) * 1024 * 1024),
    )
    finder_input = FinderInput(
        pattern_path=str(args.pattern),
        candidates=candidate_inputs(cifs),
        wavelength=args.wavelength,
        fwhm=args.fwhm,
        subtract_background=True,
    )

    print(f"pattern: {args.pattern}")
    print(f"candidates: {len(cifs)}")
    result, profiler, elapsed = profile_run(service, finder_input, args.profile_output)
    first_elapsed = elapsed
    print(f"first run (profiled): {elapsed:.3f}s, returned candidates: {len(result.candidates)}")
    print_cache_info(service)
    print_stats(profiler, args.sort, args.stats_limit)

    repeat_times = []
    for index in range(max(0, args.repeat)):
        result, elapsed = run_once(service, finder_input)
        repeat_times.append(elapsed)
        speedup = (repeat_times[0] / elapsed) if repeat_times and elapsed > 0 else 0.0
        print(f"repeat {index + 1}: {elapsed:.3f}s, returned candidates: {len(result.candidates)}")
        print_cache_info(service)
        if index > 0 and speedup:
            print(f"repeat speedup vs repeat 1: {speedup:.2f}x")
    if repeat_times:
        best_repeat = min(repeat_times)
        if best_repeat > 0:
            print(f"best repeat speedup vs profiled first run: {first_elapsed / best_repeat:.2f}x")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
