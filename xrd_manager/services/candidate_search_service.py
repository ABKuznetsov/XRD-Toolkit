from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import re

from xrd_manager.services.ccdc_service import CcdcService, extract_doi
from xrd_manager.services.cod_online_service import CodEntry, CodOnlineService, formula_elements
from xrd_manager.services.local_phase_cache import LocalPhaseCache
from xrd_manager.services.materials_project_service import MaterialsProjectService
from xrd_manager.services.rruff_service import RruffService


@dataclass(slots=True)
class CandidateSearchOptions:
    local_sources: list[str]
    excluded_elements: list[str]
    cod_online_enabled: bool
    rruff_enabled: bool
    materials_project_enabled: bool
    material_class_allowed: Callable[[str], bool]


class CandidateSearchService:
    def __init__(
        self,
        local_phase_cache: LocalPhaseCache,
        cod_online: CodOnlineService,
        ccdc: CcdcService,
        rruff: RruffService,
        materials_project: MaterialsProjectService,
    ) -> None:
        self.local_phase_cache = local_phase_cache
        self.cod_online = cod_online
        self.ccdc = ccdc
        self.rruff = rruff
        self.materials_project = materials_project

    def search_text(self, query: str, options: CandidateSearchOptions) -> list[list[str]]:
        query = query.strip()
        if not query:
            return []

        rows = []
        query_elements = self.element_query_tokens(query)
        doi = extract_doi(query)
        if doi:
            try:
                entry = self.download_ccdc_doi_to_cache(doi)
                rows.extend(self.cache_rows([entry]))
            except Exception as exc:
                rows.append(["CCDC", doi, "", "CCDC CIF not available", "", str(exc)])

        ccdc_key = self.search_cache_key("text", query)
        if not self.local_phase_cache.search_is_fresh("CCDC", ccdc_key):
            try:
                ccdc_entries = self.ccdc.search_text(
                    query=query,
                    target_dir=self.local_phase_cache.root / "ccdc_cif",
                    limit=80,
                )
                self.index_ccdc_entries(ccdc_entries)
                self.local_phase_cache.mark_search("CCDC", ccdc_key)
                rows = self.dedupe_candidate_rows(
                    rows
                    + self.cache_rows(
                        self.search_local_cache(
                            options,
                            text="" if query_elements else query,
                            elements=query_elements or None,
                        )
                    )
                )
            except Exception as exc:
                if not rows and self.ccdc.status().installed:
                    rows.append(["CCDC", "", "", "CSD search failed", "", str(exc)])

        if options.local_sources:
            rows.extend(
                self.cache_rows(
                    self.search_local_cache(
                        options,
                        text="" if query_elements else query,
                        elements=query_elements or None,
                    )
                )
            )

        if options.rruff_enabled:
            rows.extend(
                self.rruff_rows(
                    self.rruff.search(
                        text="" if query_elements else query,
                        elements=query_elements or None,
                        excluded_elements=options.excluded_elements,
                    )
                )
            )

        if options.cod_online_enabled:
            cod_key = self.search_cache_key("text", query, options.excluded_elements)
            if not self.local_phase_cache.search_is_fresh("COD", cod_key):
                try:
                    if query_elements:
                        cod_entries = self.cod_online.search_elements(
                            query_elements,
                            excluded_elements=options.excluded_elements,
                            limit=100,
                        )
                    else:
                        cod_entries = self.cod_online.search_text(query=query, limit=100)
                    cod_entries = self.filter_cod_entries(cod_entries, options)
                    self.local_phase_cache.upsert_cod_entries(cod_entries)
                    errors = self.download_cod_entries_to_cache(cod_entries)
                    self.local_phase_cache.mark_search("COD", cod_key)
                    rows = self.dedupe_candidate_rows(
                        rows
                        + self.cache_rows(
                            self.local_phase_cache.search(
                                text="" if query_elements else query,
                                elements=query_elements or None,
                                excluded_elements=options.excluded_elements,
                                sources=["COD"],
                                limit=100,
                            )
                        )
                    )
                    if errors:
                        rows.append(["COD", "", "", f"{errors} COD CIF downloads failed", "", ""])
                except Exception:
                    pass

        if options.materials_project_enabled:
            mp_key = self.search_cache_key("text", query)
            if not self.local_phase_cache.search_is_fresh("MP", mp_key):
                try:
                    mp_entries = self.materials_project.search_text(query=query, limit=80)
                    self.download_mp_entries_to_cache(mp_entries)
                    self.local_phase_cache.mark_search("MP", mp_key)
                    rows = self.dedupe_candidate_rows(
                        rows
                        + self.cache_rows(
                            self.search_local_cache(
                                options,
                                text="" if query_elements else query,
                                elements=query_elements or None,
                            )
                        )
                    )
                except Exception as exc:
                    if not rows:
                        rows.append(["MP", "", "", "Materials Project search failed", "", str(exc)])

        return self.dedupe_candidate_rows(self.filter_candidate_rows_by_excluded_elements(rows, options))

    def search_elements(self, elements: list[str], options: CandidateSearchOptions) -> list[list[str]]:
        rows = []
        if options.local_sources:
            rows.extend(self.cache_rows(self.search_local_cache(options, elements=elements)))
        if options.rruff_enabled:
            rows.extend(
                self.rruff_rows(
                    self.rruff.search(
                        elements=elements,
                        excluded_elements=options.excluded_elements,
                    )
                )
            )
        if options.cod_online_enabled:
            cod_key = self.search_cache_key("elements", elements, options.excluded_elements)
            if not self.local_phase_cache.search_is_fresh("COD", cod_key):
                try:
                    cod_entries = self.cod_online.search_elements(
                        elements,
                        excluded_elements=options.excluded_elements,
                        limit=100,
                    )
                    cod_entries = self.filter_cod_entries(cod_entries, options)
                    self.local_phase_cache.upsert_cod_entries(cod_entries)
                    errors = self.download_cod_entries_to_cache(cod_entries)
                    self.local_phase_cache.mark_search("COD", cod_key)
                    rows = self.dedupe_candidate_rows(
                        rows
                        + self.cache_rows(
                            self.local_phase_cache.search(
                                elements=elements,
                                excluded_elements=options.excluded_elements,
                                sources=["COD"],
                                limit=100,
                            )
                        )
                    )
                    if errors:
                        rows.append(["", "COD", "", "", f"{errors} COD CIF downloads failed", "", "", "", "", ""])
                except Exception as exc:
                    rows.append(["", "COD", "", "", f"COD search failed: {exc}", "", "", "", "", ""])
        if options.materials_project_enabled:
            mp_key = self.search_cache_key("elements", elements)
            if not self.local_phase_cache.search_is_fresh("MP", mp_key):
                try:
                    mp_entries = self.materials_project.search_elements(elements, limit=80)
                    self.download_mp_entries_to_cache(mp_entries)
                    self.local_phase_cache.mark_search("MP", mp_key)
                    rows = self.dedupe_candidate_rows(
                        rows + self.cache_rows(self.search_local_cache(options, elements=elements))
                    )
                except Exception as exc:
                    rows.append(["MP", "", "", "Materials Project search failed", "", str(exc)])
        return self.dedupe_candidate_rows(self.filter_candidate_rows_by_excluded_elements(rows, options))

    def search_local_cache(
        self,
        options: CandidateSearchOptions,
        text: str = "",
        elements: list[str] | None = None,
    ):
        return self.local_phase_cache.search(
            text=text,
            elements=elements,
            excluded_elements=options.excluded_elements,
            sources=options.local_sources,
            limit=100,
        )

    def download_cod_entries_to_cache(self, entries) -> int:
        errors = 0
        for entry in entries:
            try:
                self.local_phase_cache.download_cod_entry(entry, self.cod_online)
            except Exception:
                errors += 1
        return errors

    def download_mp_entries_to_cache(self, entries) -> int:
        errors = 0
        if not entries:
            return errors
        target_dir = self.local_phase_cache.root / "materials_project_cif"
        for entry in entries:
            try:
                cif_path = self.materials_project.download_cif(entry.material_id, target_dir)
                self.local_phase_cache.index_cif(cif_path, source="MP", entry_id=entry.material_id)
            except Exception:
                errors += 1
        return errors

    def download_ccdc_doi_to_cache(self, doi: str):
        target_dir = self.local_phase_cache.root / "ccdc_cif"
        cif_path = self.ccdc.download_cif_by_doi(doi, target_dir)
        entry_id = cif_path.stem
        self.local_phase_cache.index_cif(cif_path, source="CCDC", entry_id=entry_id)
        entry = self.local_phase_cache.get("CCDC", entry_id)
        if entry is None:
            raise ValueError("CCDC CIF was downloaded but could not be indexed.")
        return entry

    def index_ccdc_entries(self, entries) -> None:
        for entry in entries:
            cif_path = self.local_phase_cache.root / "ccdc_cif" / f"{self.ccdc._safe_id(entry.identifier)}.cif"
            if cif_path.exists():
                self.local_phase_cache.index_cif(cif_path, source="CCDC", entry_id=entry.identifier)

    def cache_rows(self, entries) -> list[list[str]]:
        return [
            [
                entry.source,
                entry.entry_id,
                self.display_formula(entry.formula),
                entry.name or self.display_formula(entry.formula),
                "",
                entry.source_text or entry.spacegroup,
            ]
            for entry in entries
        ]

    def rruff_rows(self, entries) -> list[list[str]]:
        return [
            [
                "RRUFF",
                entry.rruff_id,
                self.display_formula(entry.formula),
                entry.name or entry.rruff_id,
                "",
                entry.source_text,
            ]
            for entry in entries
        ]

    def dedupe_candidate_rows(self, rows: list[list[str]]) -> list[list[str]]:
        unique = []
        seen = set()
        for row in rows:
            normalized = normalize_candidate_row(row)
            key = tuple(value.strip().lower() for value in normalized[:4])
            if key in seen:
                continue
            seen.add(key)
            unique.append(normalized)
        return unique

    def filter_candidate_rows_by_excluded_elements(
        self,
        rows: list[list[str]],
        options: CandidateSearchOptions,
    ) -> list[list[str]]:
        excluded = set(options.excluded_elements)
        filtered = []
        for row in rows:
            normalized = normalize_candidate_row(row)
            formula = normalized[2] if len(normalized) > 2 else ""
            if excluded and formula and formula_elements(formula) & excluded:
                continue
            if formula and not options.material_class_allowed(formula):
                continue
            filtered.append(row)
        return filtered

    def filter_cod_entries(self, entries: list[CodEntry], options: CandidateSearchOptions) -> list[CodEntry]:
        return [entry for entry in entries if options.material_class_allowed(entry.formula)]

    def display_formula(self, formula: str) -> str:
        parts = re.findall(r"[A-Z][a-z]?[0-9.]*", formula or "")
        return " ".join(parts) if parts else formula

    def element_query_tokens(self, query: str) -> list[str]:
        tokens = re.findall(r"[A-Z][a-z]?", query)
        if not tokens:
            return []
        residue = re.sub(r"[A-Z][a-z]?|\s|,|;|/|-|_", "", query)
        return tokens if not residue else []

    def search_cache_key(self, mode: str, query, excluded: list[str] | None = None) -> str:
        if isinstance(query, (list, tuple, set)):
            query_text = " ".join(sorted(str(item).strip() for item in query if str(item).strip()))
        else:
            query_text = re.sub(r"\s+", " ", str(query or "").strip().lower())
        excluded_text = " ".join(sorted(str(item).strip() for item in excluded or [] if str(item).strip()))
        return f"{mode}|{query_text}|exclude:{excluded_text}"


def normalize_candidate_row(row: list[str]) -> list[str]:
    if len(row) == 6:
        return row
    if len(row) >= 10:
        return [
            row[1],
            row[2],
            row[3],
            row[4],
            row[8],
            row[9],
        ]
    if len(row) >= 5:
        return ["", "", "", row[4], "", ""]
    padded = list(row) + [""] * 6
    return padded[:6]
