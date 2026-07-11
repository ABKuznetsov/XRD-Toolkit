from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

from xrd_finder.services.preprocessing_service import auto_smoothing_window, smooth_observed_curve
from xrd_finder.ui.preprocessing_dialogs import BackgroundRemovalPanel, SmoothPanel, background_method_label
from xrd_finder.ui.theme import preprocessing_panel_style


class PhaseFinderPreprocessingActionsMixin:
    def _close_preprocessing_panel(self) -> None:
        panel = getattr(self, "_preprocessing_panel", None)
        if panel is not None:
            panel.hide()
            panel.deleteLater()
        self._preprocessing_panel = None
        self._preprocessing_panel_key = None

    def _show_preprocessing_panel(
        self,
        key: str,
        button: QWidget,
        panel: QWidget,
        preview_callback,
        cancel_callback,
    ) -> None:
        if getattr(self, "_preprocessing_panel", None) is not None:
            if getattr(self, "_preprocessing_panel_key", None) == key:
                self._close_preprocessing_panel()
                return
            self._close_preprocessing_panel()

        panel.setParent(self)
        panel.setWindowFlags(Qt.WindowType.Widget)
        panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        panel.setAutoFillBackground(True)
        panel.setStyleSheet(preprocessing_panel_style(self._is_dark_theme()))
        panel.adjustSize()
        position = button.mapTo(self, button.rect().bottomLeft())
        max_x = max(0, self.width() - panel.width() - 8)
        max_y = max(0, self.height() - panel.height() - 8)
        panel.move(min(max(position.x(), 8), max_x), min(max(position.y() + 4, 8), max_y))
        panel.raise_()

        def accept_panel() -> None:
            preview_callback()
            self._close_preprocessing_panel()

        def cancel_panel() -> None:
            cancel_callback()
            self._close_preprocessing_panel()

        panel.previewRequested.connect(preview_callback)
        panel.applyRequested.connect(accept_panel)
        panel.cancelRequested.connect(cancel_panel)
        self._preprocessing_panel = panel
        self._preprocessing_panel_key = key
        panel.show()

    def _smooth_active_pattern_plot(self) -> None:
        data = self._active_observed_data()
        if data is None:
            return
        x = np.asarray(data[:, 0], dtype=float)
        y = np.asarray(data[:, 1], dtype=float)
        pattern = self._active_pattern()
        if pattern is None:
            return
        original_processed_points = [list(point) for point in pattern.processed_points]
        original_processed_label = pattern.processed_label
        original_background_removed = pattern.processed_background_removed
        auto_window = auto_smoothing_window(x, y)
        panel = SmoothPanel(auto_window, self)

        def preview_smoothing() -> None:
            window = panel.window_size()
            method = panel.method()
            smooth_y = np.asarray(y, dtype=float)
            for _ in range(panel.passes()):
                smooth_y = smooth_observed_curve(smooth_y, method, window, panel.polyorder(), panel.gaussian_sigma())
            label_method = {
                "savgol": "Savitzky-Golay",
                "moving": "moving average",
                "gaussian": "Gaussian",
            }.get(method, method)
            pass_text = "pass" if panel.passes() == 1 else "passes"
            self._set_preprocessed_observed_curve(
                x,
                smooth_y,
                f"Observed smoothed ({label_method}, window {window}, {panel.passes()} {pass_text})",
                pattern.processed_background_removed,
            )

        def cancel_smoothing() -> None:
            pattern.processed_points = original_processed_points
            pattern.processed_label = original_processed_label
            pattern.processed_background_removed = original_background_removed
            self._clear_probability_caches()
            if hasattr(self, "_invalidate_match_profile_cache"):
                self._invalidate_match_profile_cache(pattern.id if pattern is not None else None)
            self._refresh_observed_pattern_plot()
            self._rerun_active_calculation()

        self._show_preprocessing_panel(
            "smooth",
            self.finder_action_bar.smooth_button,
            panel,
            preview_smoothing,
            cancel_smoothing,
        )

    def _subtract_active_background_plot(self) -> None:
        data = self._active_observed_data()
        if data is None:
            return
        x = np.asarray(data[:, 0], dtype=float)
        y = np.asarray(data[:, 1], dtype=float)
        pattern = self._active_pattern()
        if pattern is None:
            return
        original_processed_points = [list(point) for point in pattern.processed_points]
        original_processed_label = pattern.processed_label
        original_background_removed = pattern.processed_background_removed
        panel = BackgroundRemovalPanel(parent=self)

        def preview_background_removal() -> None:
            method = panel.method()
            if method == "constant":
                background = np.full_like(y, float(np.nanpercentile(y, panel.floor_percentile())))
                label = f"Observed - background constant floor {panel.floor_percentile()}%"
            else:
                background = self._estimate_background(x, y, degree=panel.degree(), method=method)
                label_method = background_method_label(method, panel.degree())
                label = f"Observed - background {label_method}"
            corrected = np.clip(y - background, 0.0, None)
            self._set_preprocessed_observed_curve(x, corrected, label, True)

        def cancel_background_removal() -> None:
            pattern.processed_points = original_processed_points
            pattern.processed_label = original_processed_label
            pattern.processed_background_removed = original_background_removed
            self._clear_probability_caches()
            if hasattr(self, "_invalidate_match_profile_cache"):
                self._invalidate_match_profile_cache(pattern.id if pattern is not None else None)
            self._refresh_observed_pattern_plot()
            self._rerun_active_calculation()

        self._show_preprocessing_panel(
            "background",
            self.finder_action_bar.background_button,
            panel,
            preview_background_removal,
            cancel_background_removal,
        )

    def _reset_observed_preprocessing(self) -> None:
        pattern = self._active_pattern()
        if pattern is not None:
            pattern.processed_points.clear()
            pattern.processed_label = ""
            pattern.processed_background_removed = False
            self.project.touch()
            self.project_changed.emit()
        self._clear_probability_caches()
        if hasattr(self, "_invalidate_match_profile_cache"):
            self._invalidate_match_profile_cache(pattern.id if pattern is not None else None)
        self._refresh_observed_pattern_plot()
        self._rerun_active_calculation()

    def _set_preprocessed_observed_curve(
        self,
        x: np.ndarray,
        y: np.ndarray,
        name: str,
        background_removed: bool,
    ) -> None:
        pattern = self._active_pattern()
        if pattern is None:
            return
        processed = np.column_stack([x, y])
        pattern.processed_points = processed.astype(float).tolist()
        pattern.processed_label = name
        pattern.processed_background_removed = background_removed
        self.project.touch()
        self.project_changed.emit()
        self._clear_probability_caches()
        if hasattr(self, "_invalidate_match_profile_cache"):
            self._invalidate_match_profile_cache(pattern.id)
        self._replace_observed_curve(x, y, name)
        self._rerun_active_calculation()

    def _rerun_active_calculation(self) -> None:
        has_profile_candidates = bool(self.match_candidates)
        if self.show_all_selected_patterns and hasattr(self, "_profile_candidates_for_pattern"):
            has_profile_candidates = has_profile_candidates or any(
                self._profile_candidates_for_pattern(pattern)
                for pattern in self._patterns_to_display()
            )
        if has_profile_candidates:
            self._recalculate_match_profile()
        elif self.active_overlay_entry_id:
            candidate = self._selected_candidate_row()
            if candidate is not None:
                self.active_overlay_entry_id = None
                self._calculate_candidate_overlay(candidate, show_errors=False)

    def _replace_observed_curve(self, x: np.ndarray, y: np.ndarray, name: str) -> None:
        pattern = self._active_pattern()
        self._draw_observed_patterns(
            active_override=(pattern.id if pattern is not None else "", np.column_stack([x, y]), name)
        )
