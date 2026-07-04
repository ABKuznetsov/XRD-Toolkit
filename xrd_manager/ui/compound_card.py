from __future__ import annotations

from collections.abc import Mapping

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from xrd_manager.services.ccdc_service import extract_doi


class CompoundCardWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.labels: dict[str, QLabel] = {}
        self.atom_table: QTableWidget | None = None
        self._build_ui()

    def set_candidate(self, candidate: Mapping[str, object] | None) -> None:
        data = dict(candidate or {})
        if "Links" not in data:
            data["Links"] = self._links_html(data)

        for key, label in self.labels.items():
            text = str(data.get(key, "") or "")
            label.setText(text if text else "-")

        rows = data.get("_AtomRows")
        atom_rows = rows if isinstance(rows, list) else []
        if self.atom_table is not None:
            self.atom_table.setRowCount(len(atom_rows))
            for row_index, row in enumerate(atom_rows):
                values = row if isinstance(row, (list, tuple)) else []
                for col_index, value in enumerate(values[: self.atom_table.columnCount()]):
                    self.atom_table.setItem(row_index, col_index, QTableWidgetItem(str(value)))
            self.atom_table.resizeColumnsToContents()
            self.atom_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        title = QLabel("Selected compound")
        title.setStyleSheet("font-weight: 700; font-size: 13px;")
        layout.addWidget(title)

        summary = QGridLayout()
        summary.setHorizontalSpacing(14)
        summary.setVerticalSpacing(5)
        for index, (key, label) in enumerate(
            [
                ("Phase", "Phase"),
                ("Formula", "Formula"),
                ("Source", "Source"),
                ("Entry", "Entry"),
                ("I/Ic*", "I/Ic*"),
                ("Space group", "Space group"),
            ]
        ):
            row = index // 2
            col = (index % 2) * 2
            name = QLabel(label)
            name.setStyleSheet("color: #bdbdbd; font-size: 11px;")
            value = QLabel("-")
            value.setWordWrap(True)
            value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            value.setStyleSheet("font-weight: 600;")
            self.labels[key] = value
            summary.addWidget(name, row, col)
            summary.addWidget(value, row, col + 1)
        layout.addLayout(summary)

        layout.addWidget(self._section_title("Cell"))
        self.labels["Cell"] = QLabel("-")
        self.labels["Cell"].setWordWrap(True)
        self.labels["Cell"].setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.labels["Cell"])

        layout.addWidget(self._section_title("Atoms"))
        self.atom_table = self._table(["Site", "El", "x", "y", "z", "Occ."])
        self.atom_table.setMinimumHeight(155)
        self.atom_table.setMaximumHeight(230)
        self.atom_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.atom_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.atom_table)

        layout.addWidget(self._section_title("Details"))
        self.labels["Notes"] = QLabel("-")
        self.labels["Notes"].setWordWrap(True)
        self.labels["Notes"].setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.labels["Notes"].setStyleSheet("color: #d0d0d0;")
        layout.addWidget(self.labels["Notes"])

        layout.addWidget(self._section_title("Links"))
        self.labels["Links"] = QLabel("-")
        self.labels["Links"].setWordWrap(True)
        self.labels["Links"].setOpenExternalLinks(True)
        self.labels["Links"].setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        self.labels["Links"].setStyleSheet("color: #8ab4f8;")
        layout.addWidget(self.labels["Links"])

        layout.addStretch(1)

    def _section_title(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet("font-weight: 700; margin-top: 4px;")
        return label

    def _table(self, headers: list[str]) -> QTableWidget:
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        return table

    def _links_html(self, candidate: Mapping[str, object]) -> str:
        links = []
        source = str(candidate.get("Source", "") or candidate.get("Qual.", "") or "")
        entry = str(candidate.get("Entry", "") or "")
        notes = str(candidate.get("Notes", "") or "")
        explicit_doi = str(candidate.get("DOI", "") or "")

        if source == "COD" and entry:
            links.append(f'<a href="https://www.crystallography.net/cod/{entry}.html">COD {entry}</a>')
            links.append(f'<a href="https://www.crystallography.net/cod/{entry}.cif">CIF</a>')
        elif source == "MP" and entry:
            links.append(f'<a href="https://materialsproject.org/materials/{entry}">Materials Project {entry}</a>')
        elif source == "RRUFF" and entry:
            links.append(f'<a href="https://rruff.info/{entry}">RRUFF {entry}</a>')

        doi = explicit_doi or extract_doi(" ".join([entry, notes]))
        if doi:
            links.append(f'<a href="https://doi.org/{doi}">DOI {doi}</a>')

        return " &nbsp; ".join(links)
