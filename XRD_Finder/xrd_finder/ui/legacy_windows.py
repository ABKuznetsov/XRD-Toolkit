from __future__ import annotations

import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QComboBox, QFormLayout, QLabel, QPushButton, QToolBar, QVBoxLayout, QWidget

from xrd_finder.core.project import Project
from xrd_finder.io.xy_loader import load_xy
from xrd_finder.ui.analysis_windows import AnalysisWindow


class RefinementWindow(AnalysisWindow):
    def __init__(self, project: Project) -> None:
        super().__init__(project, "Refinement: Le Bail / Rietveld")

        plot = self._plot_widget("Refinement workspace: observed / calculated / difference / HKL")
        plot.setLabel("bottom", "2theta")
        plot.setLabel("left", "Intensity")
        pattern = self._active_pattern()
        if pattern is not None:
            try:
                data = load_xy(pattern.source_path)
                plot.plot(data[:, 0], data[:, 1], pen=pg.mkPen("#202124", width=1.0), name="Observed")
            except Exception:
                pass

        rows = [
            ["Mode", "Le Bail / Rietveld"],
            ["Patterns in project", str(len(project.patterns))],
            ["Phases in project", str(len(project.phases))],
            ["Refinements in project", str(len(project.refinements))],
        ]
        self.center_layout.addWidget(plot, 4)
        self.center_layout.addWidget(self._table(["Parameter", "Value"], rows), 1)

        self.right_tabs.addTab(self._workflow_tab(), "Main")
        self.right_tabs.addTab(self._layer_tab(), "View")
        self.right_tabs.addTab(self._settings_tab(), "Settings")

    def _workflow_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        mode = QComboBox()
        mode.addItems(["Le Bail", "Rietveld"])
        layout.addWidget(QLabel("Refinement mode"))
        layout.addWidget(mode)
        for label in ["Select pattern", "Select phases", "Background", "Profile", "Cell", "Atoms"]:
            layout.addWidget(QPushButton(label))
        layout.addStretch(1)
        return widget

    def _layer_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        for label in ["Observed", "Calculated", "Difference", "Phase contributions", "HKL ticks"]:
            checkbox = QCheckBox(label)
            checkbox.setChecked(True)
            layout.addWidget(checkbox)
        layout.addStretch(1)
        return widget

    def _settings_tab(self) -> QWidget:
        widget = QWidget()
        layout = QFormLayout(widget)
        wavelength = QComboBox()
        wavelength.addItems(["Cu-Ka", "Co-Ka", "Mo-Ka", "Custom"])
        profile = QComboBox()
        profile.addItems(["Pseudo-Voigt", "Thompson-Cox-Hastings", "Gaussian"])
        layout.addRow("Wavelength", wavelength)
        layout.addRow("Profile", profile)
        return widget


class StructureWindow(AnalysisWindow):
    def __init__(self, project: Project) -> None:
        super().__init__(project, "Structure analysis")

        toolbar = QToolBar()
        for label in ["a", "b", "c", "a*", "b*", "c*", "Rotate", "Move", "Zoom", "Export"]:
            toolbar.addAction(label)

        viewport = QLabel("Structure viewport\n\nVESTA-like view for original and refined structures")
        viewport.setAlignment(Qt.AlignmentFlag.AlignCenter)
        viewport.setStyleSheet("background: white; border: 1px solid #cfd3d7; font-size: 24px;")

        rows = [[structure.name, structure.origin, structure.source_path] for structure in project.structures]
        if not rows:
            rows = [["No structures yet", "", "import CIF or run refinement later"]]

        self.center_layout.addWidget(toolbar)
        self.center_layout.addWidget(viewport, 4)
        self.center_layout.addWidget(self._table(["Structure", "Origin", "Source"], rows), 1)

        self.right_tabs.addTab(self._tools_tab(), "Tools")
        self.right_tabs.addTab(self._style_tab(), "Style")
        self.right_tabs.addTab(self._objects_tab(), "Objects")

    def _tools_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        for label in ["Show models", "Only asymmetric unit", "Unit cell", "Bonds", "Polyhedra", "Labels"]:
            layout.addWidget(QCheckBox(label))
        layout.addWidget(QPushButton("Boundary"))
        layout.addWidget(QPushButton("Orientation"))
        layout.addStretch(1)
        return widget

    def _style_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        for label in ["Ball-and-stick", "Space-filling", "Polyhedral", "Wireframe", "Stick"]:
            layout.addWidget(QCheckBox(label))
        layout.addStretch(1)
        return widget

    def _objects_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        for item in self.project.structures:
            checkbox = QCheckBox(item.name)
            checkbox.setChecked(True)
            layout.addWidget(checkbox)
        layout.addStretch(1)
        return widget


class ThermalWindow(AnalysisWindow):
    def __init__(self, project: Project) -> None:
        super().__init__(project, "Thermal / composition analysis")

        plot = self._plot_widget("Thermal analysis: parameters, fits, alpha")
        plot.setLabel("bottom", "T or x")
        plot.setLabel("left", "Parameter / alpha")

        rows = [
            ["T / x", "a", "b", "c", "V", "alpha11", "alpha33", "alphaV"],
            ["", "", "", "", "", "", "", ""],
        ]
        self.center_layout.addWidget(plot, 4)
        self.center_layout.addWidget(
            self._table(["Variable", "a", "b", "c", "V", "alpha11", "alpha33", "alphaV"], rows[1:]),
            1,
        )

        self.right_tabs.addTab(self._main_tab(), "Main")
        self.right_tabs.addTab(self._view_tab(), "View")
        self.right_tabs.addTab(self._settings_tab(), "Settings")

    def _main_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QPushButton("Build series from refinements"))
        layout.addWidget(QPushButton("Paste table"))
        layout.addWidget(QPushButton("Calculate alpha"))
        layout.addWidget(QPushButton("Export figure/table"))
        layout.addStretch(1)
        return widget

    def _view_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        for label in ["a", "b", "c", "V", "alpha11", "alpha22", "alpha33", "alphaV", "Fit", "Residuals"]:
            checkbox = QCheckBox(label)
            checkbox.setChecked(label in {"a", "c", "V", "Fit"})
            layout.addWidget(checkbox)
        layout.addStretch(1)
        return widget

    def _settings_tab(self) -> QWidget:
        widget = QWidget()
        layout = QFormLayout(widget)
        degree = QComboBox()
        degree.addItems(["1", "2", "3", "4", "5"])
        variable = QComboBox()
        variable.addItems(["Temperature", "Composition", "Pressure", "Time"])
        layout.addRow("Variable", variable)
        layout.addRow("Polynomial degree", degree)
        return widget
