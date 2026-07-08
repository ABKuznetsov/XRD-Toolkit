from __future__ import annotations

import re
from pathlib import Path

import pyqtgraph as pg
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QFileDialog, QMenu, QMessageBox


class PhaseFinderPlotActionsMixin:
    def _show_plot_context_menu(self, point) -> None:
        menu = QMenu(self)
        menu.addAction("Export image...", self._export_plot_image)
        menu.addSeparator()
        menu.addAction("Show full pattern", self._full_pattern_range)
        grid_action = menu.addAction("Grid")
        grid_action.setCheckable(True)
        grid_action.setChecked(self.grid_visible)
        grid_action.toggled.connect(self._set_grid_visible)
        legend_action = menu.addAction("Legend")
        legend_action.setCheckable(True)
        legend_action.setChecked(self.legend_item is not None)
        legend_action.toggled.connect(self._set_legend_visible)
        hkl_action = menu.addAction("HKL labels")
        hkl_action.setCheckable(True)
        hkl_action.setChecked(self.show_hkl_labels)
        hkl_action.toggled.connect(self._set_hkl_labels_enabled)
        menu.addAction(self._layer_action("Experimental pattern", "observed"))
        menu.addAction(self._layer_action("Candidate preview", "preview_peak_positions"))
        menu.addAction(self._layer_action("Total calculated profile", "total_profile"))
        menu.addAction(self._layer_action("Individual phase profiles", "phase_profiles"))
        menu.addAction(self._layer_action("Background", "background"))
        menu.addAction(self._layer_action("Phase tick marks", "phase_ticks"))
        menu.addAction(self._layer_action("Assignment markers", "coverage_markers"))
        menu.addAction(self._layer_action("Peak labels (HKL)", "peak_labels"))
        menu.addAction(self._layer_action("Unknown peaks", "unknown_peaks"))
        menu.addSeparator()
        menu.addAction("Hide calculated overlay", lambda: self._set_calculated_visible(False))
        menu.addAction("Show calculated overlay", lambda: self._set_calculated_visible(True))
        menu.addAction("Clear calculated overlay", self._clear_calculated_overlay)
        menu.exec(self.match_plot.mapToGlobal(point))

    def _export_plot_image(self) -> None:
        path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export image",
            str(Path(self._last_directory()) / "xrd_finder_plot.png"),
            "PNG image (*.png);;JPEG image (*.jpg *.jpeg)",
        )
        if not path:
            return
        self._remember_directory(path)
        if not re.search(r"\.(png|jpe?g)$", path, flags=re.IGNORECASE):
            path += ".png"
        try:
            from pyqtgraph.exporters import ImageExporter

            exporter = ImageExporter(self.match_plot.plotItem)
            params = exporter.parameters()
            current_width = max(float(self.match_plot.width()), 1.0)
            target_width = max(3200.0, current_width * 2.0)
            params["width"] = target_width
            exporter.export(path)
        except Exception as exc:
            if not self.match_plot.grab().save(path):
                QMessageBox.warning(self, "Export image", f"Could not save current plot image:\n{exc}")

    def _layer_action(self, label: str, layer: str, checked: bool | None = None, enabled: bool = True):
        action = self._make_action(label)
        action.setCheckable(True)
        has_items = bool(self.plot_layers.get(layer, []))
        action.setEnabled(enabled and has_items)
        action.setChecked(self._layer_visible(layer) if checked is None else checked)
        if enabled and has_items:
            action.toggled.connect(lambda visible, key=layer: self._set_layer_visible(key, visible))
        return action

    def _make_action(self, label: str):
        return QAction(label, self)

    def _layer_visible(self, layer: str) -> bool:
        items = self.plot_layers.get(layer, [])
        return bool(items) and all(item.isVisible() for item in items)

    def _set_layer_visible(self, layer: str, visible: bool) -> None:
        for item in self.plot_layers.get(layer, []):
            item.setVisible(visible)

    def _set_calculated_visible(self, visible: bool) -> None:
        self._set_layer_visible("calculated_profile", visible)
        self._set_layer_visible("total_profile", visible)
        self._set_layer_visible("phase_profiles", visible)
        self._set_layer_visible("background", visible)
        self._set_layer_visible("peak_positions", visible)
        self._set_layer_visible("phase_ticks", visible)
        self._set_layer_visible("peak_links", visible)
        self._set_layer_visible("coverage_markers", visible)
        self._set_layer_visible("peak_labels", visible)
        self._set_layer_visible("unknown_peaks", visible)
        self._set_layer_visible("hkl", visible)
        self._set_layer_visible("preview_profile", visible)
        self._set_layer_visible("preview_peak_positions", visible)
        self._set_layer_visible("preview_peak_links", visible)
        self._set_layer_visible("preview_hkl", visible)

    def _clear_calculated_overlay(self) -> None:
        for layer in [
            "calculated_profile",
            "total_profile",
            "phase_profiles",
            "background",
            "peak_positions",
            "phase_ticks",
            "peak_links",
            "coverage_markers",
            "peak_labels",
            "unknown_peaks",
            "hkl",
            "preview_profile",
            "preview_peak_positions",
            "preview_peak_links",
            "preview_hkl",
            "legend_info",
        ]:
            for item in self.plot_layers.get(layer, []):
                self.match_plot.removeItem(item)
            self.plot_layers[layer] = []
        self.active_overlay_entry_id = None

    def _clear_preview_overlay(self) -> None:
        for layer in ["preview_profile", "preview_peak_positions", "preview_peak_links", "preview_hkl"]:
            for item in self.plot_layers.get(layer, []):
                self.match_plot.removeItem(item)
            self.plot_layers[layer] = []

    def _set_hkl_labels_enabled(self, visible: bool) -> None:
        self.show_hkl_labels = visible
        if self.match_candidates:
            self._recalculate_match_profile()
            row = self.candidate_table.currentRow()
            if row >= 0:
                self._preview_candidate_row(row)
        elif self.active_overlay_entry_id:
            row = self.candidate_table.currentRow()
            if row >= 0:
                self.active_overlay_entry_id = None
                self._preview_candidate_row(row)

    def _set_grid_visible(self, visible: bool) -> None:
        self.grid_visible = visible
        alpha = 0.25 if visible else 0.0
        self.match_plot.showGrid(x=True, y=True, alpha=alpha)

    def _set_legend_visible(self, visible: bool) -> None:
        if visible and self.legend_item is None:
            self.legend_item = self.match_plot.addLegend()
        elif not visible and self.legend_item is not None:
            self.legend_item.scene().removeItem(self.legend_item)
            self.legend_item = None

    def _add_legend_info(self, text: str) -> None:
        item = self.match_plot.plot([], [], pen=pg.mkPen("#00000000", width=0.1), name=text)
        self.plot_layers["legend_info"].append(item)

    def _full_pattern_range(self) -> None:
        self._reset_match_plot_view()
