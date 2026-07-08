from __future__ import annotations

from pathlib import Path

from xrd_finder.io.cif_loader import create_phase_from_cif


class PhaseFinderProjectTreeActionsMixin:
    def _after_cif_import(self, path: Path, phase, structure) -> None:
        try:
            entry = self.local_phase_cache.add_user_cif(path)
        except Exception:
            return
        if entry.cif_path:
            phase.source_path = entry.cif_path
            structure.source_path = entry.cif_path

    def _project_phase_user_entry(self, phase) -> str:
        if not phase.source_path:
            return phase.id
        path = Path(phase.source_path)
        entry_id = path.stem
        cached_path = self.local_phase_cache.cif_path("USER", entry_id)
        if cached_path is not None:
            return entry_id
        try:
            entry = self.local_phase_cache.add_user_cif(path)
        except Exception:
            return phase.id
        if entry.cif_path:
            phase.source_path = entry.cif_path
            structure = self._structure_for_phase(phase.id)
            if structure is not None:
                structure.source_path = entry.cif_path
        return entry.entry_id or phase.id

    def _structure_for_phase(self, phase_id: str):
        phase = next((item for item in self.project.phases if item.id == phase_id), None)
        if phase is None:
            return None
        if phase.structure_id:
            structure = next((item for item in self.project.structures if item.id == phase.structure_id), None)
            if structure is not None:
                return structure
        return next((item for item in self.project.structures if item.phase_id == phase_id), None)

    def _current_tree_phase_structure(self):
        current = self.tree.current_object()
        if current is None:
            return None
        object_type, object_id = current
        if object_type != "phase":
            return None
        structure = self._structure_for_phase(object_id)
        if structure is not None:
            return structure
        phase = next((item for item in self.project.phases if item.id == object_id), None)
        if phase is None or not phase.source_path:
            return None
        try:
            _phase, structure = create_phase_from_cif(phase.source_path)
            structure.name = phase.name or structure.name
            structure.formula = phase.formula or structure.formula
            structure.phase_id = phase.id
            structure.id = phase.structure_id or structure.id
            return structure
        except Exception:
            return None

    def _refresh_project_phase_candidates(self) -> None:
        if not hasattr(self, "candidate_table"):
            return
        rows = [
            ["USER", self._project_phase_user_entry(phase), phase.formula, phase.name, "", "loaded structure"]
            for phase in self.project.phases
        ]
        if not rows:
            rows = [["", "", "", "No phases yet", "", ""]]
        self._set_candidate_rows(rows)

    def _on_project_tree_selection_changed(self) -> None:
        if not hasattr(self, "match_plot"):
            return
        self._clear_probability_caches()
        view_range = self._plot_view_range() if self.show_all_selected_patterns else None
        try:
            self._refresh_observed_pattern_plot()
            tree_structure = self._current_tree_phase_structure()
            if tree_structure is not None:
                self.active_overlay_entry_id = None
                self._clear_preview_overlay()
                self._calculate_structure_overlay(tree_structure, preview=False)
            elif self.match_candidates:
                self._recalculate_match_profile()
            elif self.active_overlay_entry_id:
                candidate = self._selected_candidate_row()
                if candidate is not None:
                    self.active_overlay_entry_id = None
                    self._calculate_candidate_overlay(candidate, show_errors=False)
        finally:
            self._restore_plot_view_range(view_range)
