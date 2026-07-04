from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class DatabasePanelWidget(QWidget):
    sourceToggled = Signal(str, bool)
    materialsProjectToggled = Signal(bool)
    saveMaterialsProjectRequested = Signal()
    rebuildUserIndexRequested = Signal()
    indexCodFolderRequested = Signal()
    indexCodZipRequested = Signal()
    downloadCodArchiveRequested = Signal()
    downloadRruffRequested = Signal()
    indexRruffRequested = Signal()

    def __init__(
        self,
        rows: list[list[str]],
        source_states: dict[str, bool],
        materials_project_enabled: bool,
        materials_project_status_text: str,
        materials_project_api_key: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.source_checkboxes: dict[str, QCheckBox] = {}
        self.database_table: QTableWidget | None = None
        self.materials_project_checkbox: QCheckBox | None = None
        self.materials_project_status_label: QLabel | None = None
        self.materials_project_api_key_input: QLineEdit | None = None
        self._build_ui(
            rows,
            source_states,
            materials_project_enabled,
            materials_project_status_text,
            materials_project_api_key,
        )

    def api_key(self) -> str:
        return self.materials_project_api_key_input.text().strip() if self.materials_project_api_key_input else ""

    def materials_project_enabled(self) -> bool:
        return bool(self.materials_project_checkbox and self.materials_project_checkbox.isChecked())

    def set_materials_project_status(self, text: str) -> None:
        if self.materials_project_status_label is not None:
            self.materials_project_status_label.setText(text)

    def set_source_checked(self, setting_key: str, checked: bool) -> None:
        checkbox = self.source_checkboxes.get(setting_key)
        if checkbox is not None and checkbox.isChecked() != checked:
            checkbox.blockSignals(True)
            checkbox.setChecked(checked)
            checkbox.blockSignals(False)

    def update_row(self, source_name: str, values: list[str]) -> None:
        if self.database_table is None:
            return
        for row in range(self.database_table.rowCount()):
            name_item = self.database_table.item(row, 0)
            if name_item is None or name_item.text() != source_name:
                continue
            for column, value in enumerate(values[: self.database_table.columnCount()]):
                self.database_table.setItem(row, column, QTableWidgetItem(value))
            self.database_table.resizeColumnsToContents()
            self.database_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
            return

    def _build_ui(
        self,
        rows: list[list[str]],
        source_states: dict[str, bool],
        materials_project_enabled: bool,
        materials_project_status_text: str,
        materials_project_api_key: str,
    ) -> None:
        layout = QVBoxLayout(self)

        self.database_table = self._table(["Source", "State", "Details", "Location"], rows)
        self.database_table.setMinimumHeight(230)
        self.database_table.setMaximumHeight(320)
        self.database_table.setWordWrap(True)
        self.database_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.database_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.database_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.database_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.database_table.setColumnWidth(2, 230)
        layout.addWidget(self.database_table)

        source_box = QWidget()
        source_layout = QGridLayout(source_box)
        source_layout.setContentsMargins(0, 0, 0, 0)
        source_layout.addWidget(QLabel("Use in search"), 0, 0, 1, 2)
        for label, key, row, column in [
            ("User library", "sources/user_library", 1, 0),
            ("COD local", "sources/cod_local", 1, 1),
            ("COD online", "sources/cod_online", 2, 0),
            ("RRUFF", "sources/rruff", 2, 1),
        ]:
            checkbox = QCheckBox(label)
            checkbox.setChecked(bool(source_states.get(key, False)))
            checkbox.toggled.connect(lambda checked, setting_key=key: self.sourceToggled.emit(setting_key, checked))
            self.source_checkboxes[key] = checkbox
            source_layout.addWidget(checkbox, row, column)
        layout.addWidget(source_box)

        self.materials_project_checkbox = QCheckBox("Use Materials Project in phase search")
        self.materials_project_checkbox.setChecked(materials_project_enabled)
        self.materials_project_checkbox.toggled.connect(self.materialsProjectToggled)
        layout.addWidget(self.materials_project_checkbox)

        self.materials_project_status_label = QLabel(materials_project_status_text)
        layout.addWidget(self.materials_project_status_label)

        key_row = QWidget()
        key_layout = QHBoxLayout(key_row)
        key_layout.setContentsMargins(0, 0, 0, 0)
        self.materials_project_api_key_input = QLineEdit()
        self.materials_project_api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.materials_project_api_key_input.setPlaceholderText("Materials Project API key")
        self.materials_project_api_key_input.setText(materials_project_api_key)
        save_key = QPushButton("Save API key")
        save_key.clicked.connect(self.saveMaterialsProjectRequested)
        key_layout.addWidget(self.materials_project_api_key_input, 1)
        key_layout.addWidget(save_key)
        layout.addWidget(key_row)

        build_index = QPushButton("Rebuild user phase library index")
        build_index.clicked.connect(self.rebuildUserIndexRequested)
        layout.addWidget(build_index)

        cod_tools = QWidget()
        cod_tools_layout = QGridLayout(cod_tools)
        cod_tools_layout.setContentsMargins(0, 0, 0, 0)
        cod_tools_layout.setHorizontalSpacing(6)
        cod_tools_layout.setVerticalSpacing(6)
        index_cod_folder = QPushButton("Index COD CIF folder")
        index_cod_folder.clicked.connect(self.indexCodFolderRequested)
        index_cod_archive = QPushButton("Index COD ZIP archive")
        index_cod_archive.clicked.connect(self.indexCodZipRequested)
        download_cod_archive = QPushButton("Download COD archive URL")
        download_cod_archive.clicked.connect(self.downloadCodArchiveRequested)
        cod_tools_layout.addWidget(index_cod_folder, 0, 0)
        cod_tools_layout.addWidget(index_cod_archive, 0, 1)
        cod_tools_layout.addWidget(download_cod_archive, 1, 0, 1, 2)
        layout.addWidget(cod_tools)

        rruff_tools = QWidget()
        rruff_tools_layout = QHBoxLayout(rruff_tools)
        rruff_tools_layout.setContentsMargins(0, 0, 0, 0)
        download_rruff = QPushButton("Download RRUFF")
        download_rruff.clicked.connect(self.downloadRruffRequested)
        index_rruff = QPushButton("Index RRUFF")
        index_rruff.clicked.connect(self.indexRruffRequested)
        rruff_tools_layout.addWidget(download_rruff)
        rruff_tools_layout.addWidget(index_rruff)
        layout.addWidget(rruff_tools)

        layout.addWidget(QLabel("Data sources"))
        help_label = QLabel(
            "Search uses only checked sources. COD/RRUFF bulk databases are downloaded and indexed manually."
        )
        help_label.setWordWrap(True)
        layout.addWidget(help_label)
        layout.addStretch(1)

    def _table(self, headers: list[str], rows: list[list[str]]) -> QTableWidget:
        table = QTableWidget(len(rows), len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setAlternatingRowColors(True)
        for row_index, row in enumerate(rows):
            for col_index, value in enumerate(row[: len(headers)]):
                table.setItem(row_index, col_index, QTableWidgetItem(value))
        table.resizeColumnsToContents()
        return table
