from __future__ import annotations

import numpy as np
import pyqtgraph as pg

from xrd_finder.core.pattern import Pattern
from xrd_finder.ui.observed_patterns import apply_pattern_offsets, load_observed_patterns, observed_pattern_data, processed_pattern_data
from xrd_finder.ui.pattern_plot_helpers import ensure_right_legend


class PhaseFinderObservedPatternActionsMixin:
    def _set_pattern_display_mode(self, mode: str) -> None:
        self.show_all_selected_patterns = mode == "All selected"
        self._refresh_observed_pattern_plot()
        self._rerun_active_calculation()

    def _set_pattern_stack_offset(self, percent: int) -> None:
        self.pattern_stack_offset_percent = max(0, int(percent))
        if self.show_all_selected_patterns:
            self._refresh_observed_pattern_plot()
            self._rerun_active_calculation()

    def _pattern_processed_observed_data(self, pattern: Pattern | None) -> np.ndarray | None:
        return processed_pattern_data(pattern)

    def _active_processed_observed_data(self) -> np.ndarray | None:
        return self._pattern_processed_observed_data(self._active_pattern())

    def _active_background_removed(self) -> bool:
        pattern = self._active_pattern()
        return bool(pattern is not None and pattern.processed_background_removed)

    def _active_observed_data(self):
        return observed_pattern_data(self._active_pattern())

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
        for item in self.plot_layers.get("observed", []):
            self.match_plot.removeItem(item)
        self.plot_layers["observed"] = []
        self.legend_item = ensure_right_legend(self.match_plot, clear=True)
        self.observed_pattern_plot_context = {}

        patterns = self._patterns_to_display()
        active_pattern = self._active_pattern()
        active_id = active_pattern.id if active_pattern is not None else ""
        colors = ["#202124", "#d93025", "#1a73e8", "#188038", "#f9ab00", "#8e24aa", "#00acc1", "#c5221f"]
        x_values = []
        y_values = []
        color_index = 0
        loaded_patterns = apply_pattern_offsets(
            load_observed_patterns(patterns, active_override),
            self.show_all_selected_patterns,
            self.pattern_stack_offset_percent,
        )

        for item in loaded_patterns:
            y = item.plotted_y
            if item.pattern.id == active_id:
                color = "#202124"
            else:
                color_index += 1
                color = colors[color_index % len(colors)]
            width = 1.35 if item.pattern.id == active_id else 1.15
            curve_item = self.match_plot.plot(item.x, y, pen=pg.mkPen(color, width=width))
            legend_proxy = self.match_plot.plot(
                [],
                [],
                pen=pg.mkPen(color, width=width),
                symbol="o" if item.pattern.id == active_id else None,
                symbolSize=7,
                symbolBrush=pg.mkBrush("#e11d21") if item.pattern.id == active_id else None,
                symbolPen=pg.mkPen("#e11d21", width=1.0) if item.pattern.id == active_id else None,
                name=item.name,
            )
            self.plot_layers["observed"].extend([curve_item, legend_proxy])
            self.observed_pattern_plot_context[item.pattern.id] = item.context
            x_values.append(item.x)
            y_values.append(y)

        if x_values and y_values and not self.match_plot_view_initialized:
            self._reset_match_plot_view()

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
