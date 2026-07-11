from __future__ import annotations

import numpy as np
import pyqtgraph as pg

from xrd_finder.core.pattern import Pattern
from xrd_finder.ui.observed_patterns import apply_pattern_offsets, load_observed_patterns, normalize_intensity, observed_pattern_data, processed_pattern_data
from xrd_finder.ui.pattern_plot_helpers import (
    calculate_profile_for_structure,
    ensure_right_legend,
    plot_hkl_sticks,
    plot_profile,
    scale_profile_to_reference,
)


class PhaseFinderObservedPatternActionsMixin:
    def _set_pattern_display_mode(self, mode: str) -> None:
        if hasattr(self, "_save_active_profile_state"):
            self._save_active_profile_state()
        self.show_all_selected_patterns = mode == "All selected"
        if hasattr(self, "_clear_profile_plot_layers"):
            self._clear_profile_plot_layers(include_observed=True, rebuild_legend=False)
            self.active_overlay_entry_id = None
        else:
            if hasattr(self, "_clear_calculated_overlay"):
                self._clear_calculated_overlay()
            if hasattr(self, "_clear_preview_overlay"):
                self._clear_preview_overlay()
        self._refresh_observed_pattern_plot()
        self._rerun_active_calculation()
        if hasattr(self, "_update_profile_view_context"):
            self._update_profile_view_context()

    def _set_pattern_stack_offset(self, percent: int) -> None:
        self.pattern_stack_offset_percent = max(0, int(percent))
        if self.show_all_selected_patterns:
            self._refresh_observed_pattern_plot()
            self._rerun_active_calculation()

    def _set_pattern_normalization(self, enabled: bool) -> None:
        self.normalize_observed_patterns = bool(enabled)
        if hasattr(self, "_invalidate_match_profile_cache"):
            self._invalidate_match_profile_cache()
        self._clear_probability_caches()
        self._refresh_observed_pattern_plot()
        self._rerun_active_calculation()

    def _normalized_observed_data(self, data: np.ndarray | None) -> np.ndarray | None:
        if data is None or not self.normalize_observed_patterns:
            return data
        return normalize_intensity(data)

    def _pattern_processed_observed_data(self, pattern: Pattern | None) -> np.ndarray | None:
        processed = processed_pattern_data(pattern)
        if processed is not None:
            return self._normalized_observed_data(processed)
        if not self.normalize_observed_patterns:
            return None
        return self._normalized_observed_data(observed_pattern_data(pattern))

    def _active_processed_observed_data(self) -> np.ndarray | None:
        return self._pattern_processed_observed_data(self._active_pattern())

    def _active_background_removed(self) -> bool:
        pattern = self._active_pattern()
        return bool(pattern is not None and pattern.processed_background_removed)

    def _active_observed_data(self):
        return self._normalized_observed_data(observed_pattern_data(self._active_pattern()))

    def _refresh_observed_pattern_plot(self) -> None:
        self._draw_observed_patterns()

    def _patterns_to_display(self):
        if self.show_all_selected_patterns:
            checked = set(self.tree.checked_pattern_ids())
            patterns = [pattern for pattern in self.project.patterns if pattern.id in checked]
            if patterns:
                return patterns
        pattern = self._active_pattern()
        return [pattern] if pattern is not None else []

    def _draw_observed_patterns(self, active_override=None) -> None:
        if hasattr(self, "_clear_profile_plot_layers"):
            self._clear_profile_plot_layers(include_observed=True, rebuild_legend=False)
        else:
            for item in self.plot_layers.get("observed", []):
                self.match_plot.removeItem(item)
            self.plot_layers["observed"] = []
        legend_visible = bool(getattr(getattr(self, "plot_view_settings", None), "legend_visible", True))
        self.legend_item = ensure_right_legend(self.match_plot, clear=True)
        self.legend_item.setVisible(legend_visible)
        self.observed_pattern_plot_context = {}

        patterns = self._patterns_to_display()
        active_pattern = self._active_pattern()
        active_id = active_pattern.id if active_pattern is not None else ""
        x_values = []
        y_values = []
        loaded_patterns = apply_pattern_offsets(
            load_observed_patterns(patterns, active_override, normalize=self.normalize_observed_patterns),
            self.show_all_selected_patterns,
            self.pattern_stack_offset_percent,
        )

        for item in loaded_patterns:
            y = item.plotted_y
            plot_style = getattr(self, "plot_style", None)
            active = item.pattern.id == active_id
            color = self._observed_pattern_color(item.pattern.id)
            base_width = float(getattr(getattr(plot_style, "observed", None), "width", 1.35))
            width = base_width + 0.75 if active else max(base_width, 0.5)
            curve_item = self.match_plot.plot(item.x, y, pen=pg.mkPen(color, width=width))
            try:
                curve_item._xrd_pattern_id = item.pattern.id
            except Exception:
                pass
            self._make_observed_curve_selectable(curve_item, item.pattern.id)
            legend_proxy = self.match_plot.plot(
                [],
                [],
                pen=pg.mkPen(color, width=width),
                symbol="o" if active else None,
                symbolSize=int(getattr(getattr(plot_style, "marker", None), "size", 7)) + (2 if active else 0),
                symbolBrush=pg.mkBrush(color) if active else None,
                symbolPen=pg.mkPen("#111111", width=1.2) if active else None,
                name=(f"* {item.name}" if active else item.name),
            )
            try:
                legend_proxy._xrd_pattern_id = item.pattern.id
            except Exception:
                pass
            self.plot_layers["observed"].extend([curve_item, legend_proxy])
            self.observed_pattern_plot_context[item.pattern.id] = item.context
            x_values.append(item.x)
            y_values.append(y)

        self._draw_checked_phase_profiles(loaded_patterns)
        if hasattr(self, "_apply_plot_layer_visibility_settings"):
            self._apply_plot_layer_visibility_settings(self.plot_view_settings)

        if x_values and y_values and not self.match_plot_view_initialized:
            self._reset_match_plot_view()


    def _observed_pattern_color(self, pattern_id: str) -> str:
        palette = [
            getattr(getattr(getattr(self, "plot_style", None), "observed", None), "color", None) or "#202124",
            "#d93025",
            "#1a73e8",
            "#188038",
            "#f9ab00",
            "#8e24aa",
            "#00acc1",
            "#c5221f",
            "#6d4c41",
            "#5f6368",
        ]
        colors = getattr(self, "observed_pattern_colors", None)
        if colors is None:
            self.observed_pattern_colors = {}
            colors = self.observed_pattern_colors
        if pattern_id not in colors:
            used = len(colors)
            colors[pattern_id] = palette[used % len(palette)]
        return colors[pattern_id]

    def _make_observed_curve_selectable(self, curve_item, pattern_id: str) -> None:
        try:
            curve_item.curve.setClickable(True, width=10)
        except Exception:
            pass
        signal = getattr(curve_item, "sigClicked", None) or getattr(getattr(curve_item, "curve", None), "sigClicked", None)
        if signal is None:
            return
        try:
            signal.connect(lambda *_args, pid=pattern_id: self._set_active_pattern_from_plot(pid))
        except Exception:
            pass

    def _set_active_pattern_from_plot(self, pattern_id: str) -> None:
        if not pattern_id:
            return
        current = self.tree.current_pattern_id() if hasattr(self, "tree") else None
        if current == pattern_id:
            return
        self.tree.select_object("pattern", pattern_id)
        if hasattr(self, "_update_profile_view_context"):
            self._update_profile_view_context()

    def _draw_checked_phase_profiles(self, loaded_patterns) -> None:
        for layer in ["calculated_profile", "hkl"]:
            for item in self.plot_layers.get(layer, []):
                self.match_plot.removeItem(item)
            self.plot_layers[layer] = []
        checked = set(self.tree.checked_phase_ids())
        if not checked:
            return
        phases = [phase for phase in self.project.phases if phase.id in checked]
        if not phases:
            return
        structures = {structure.id: structure for structure in self.project.structures}
        if loaded_patterns:
            x_grid = loaded_patterns[0].x
            reference_max = max((float(np.nanmax(item.y)) for item in loaded_patterns if len(item.y)), default=100.0)
            y_offset = max((float(np.nanmax(item.plotted_y)) for item in loaded_patterns if len(item.plotted_y)), default=0.0)
            y_offset += max(reference_max * 0.12, 1.0) if self.show_all_selected_patterns else 0.0
        else:
            x_grid = np.linspace(5.0, 120.0, 5000)
            reference_max = 100.0
            y_offset = 0.0
        colors = ["#d93025", "#1a73e8", "#188038", "#f9ab00", "#8e24aa"]
        for index, phase in enumerate(phases):
            structure = structures.get(phase.structure_id or "") or next(
                (item for item in self.project.structures if item.phase_id == phase.id),
                None,
            )
            if structure is None:
                continue
            try:
                structure.wavelength = self._active_wavelength()
                x, y, peaks = calculate_profile_for_structure(
                    self.calculated_pattern_service,
                    structure,
                    x_grid,
                    fwhm=0.18,
                )
            except Exception:
                continue
            y = scale_profile_to_reference(y, reference_max)
            if self.show_all_selected_patterns:
                y = y + y_offset
                y_offset += max(float(np.nanmax(y) - np.nanmin(y)), reference_max, 1.0) * (self.pattern_stack_offset_percent / 100.0)
            color = colors[index % len(colors)]
            item = plot_profile(self.match_plot, x, y, color, f"calc: {phase.name}", width=1.35)
            self.plot_layers["calculated_profile"].append(item)
            if self.show_hkl_labels:
                baseline = float(np.nanmin(y))
                top = baseline + max(reference_max * 0.18, 1.0)
                self.plot_layers["hkl"].extend(plot_hkl_sticks(self.match_plot, peaks, color, baseline, top, label=f"hkl: {phase.name}"))

    def _plot_view_range(self) -> tuple[tuple[float, float], tuple[float, float]]:
        view_range = self.match_plot.plotItem.vb.viewRange()
        return (tuple(view_range[0]), tuple(view_range[1]))

    def _restore_plot_view_range(self, view_range: tuple[tuple[float, float], tuple[float, float]] | None) -> None:
        if view_range is None:
            return
        (xmin, xmax), (ymin, ymax) = view_range
        self.match_plot.setXRange(float(xmin), float(xmax), padding=0.0)
        self.match_plot.setYRange(float(ymin), float(ymax), padding=0.0)

    def _active_pattern_plot_context(self) -> dict[str, float]:
        pattern = self._active_pattern()
        if pattern is None:
            return {"offset": 0.0, "raw_min": 0.0, "raw_max": 1.0, "plot_min": 0.0, "plot_max": 1.0, "height": 1.0}
        return self.observed_pattern_plot_context.get(
            pattern.id,
            {"offset": 0.0, "raw_min": 0.0, "raw_max": 1.0, "plot_min": 0.0, "plot_max": 1.0, "height": 1.0},
        )

    def _reset_match_plot_view(self) -> None:
        self.match_plot.autoRange()
        self.match_plot_view_initialized = True
