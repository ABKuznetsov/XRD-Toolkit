from __future__ import annotations

import json
from dataclasses import asdict, fields, is_dataclass
from pathlib import Path
from types import UnionType
from typing import Any, Union, get_args, get_origin, get_type_hints

from xrd_finder.core.pattern import Pattern
from xrd_finder.core.finder_state import FinderProjectState
from xrd_finder.core.phase import Phase
from xrd_finder.core.project import Project
from xrd_finder.core.refinement import RefinementMetrics, RefinementResult
from xrd_finder.core.result import AnalysisResult
from xrd_finder.core.series import SeriesAnalysis, SeriesPoint
from xrd_finder.core.structure import AtomSite, CellParameters, Structure


def _to_plain(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _to_plain(item) for key, item in asdict(value).items()}
    if isinstance(value, list):
        return [_to_plain(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_plain(item) for key, item in value.items()}
    return value


def save_project_manifest(project: Project, path: str | Path) -> None:
    target = Path(path)
    target.write_text(json.dumps(_to_plain(project), indent=2), encoding="utf-8")


def load_project_manifest(path: str | Path) -> Project:
    source = Path(path)
    data = json.loads(source.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("Project manifest must contain a JSON object.")
    project = _from_dataclass(Project, data)
    project.root_path = str(source)
    return project


def _from_dataclass(cls: type, data: Any):
    if not isinstance(data, dict):
        return data
    values = {}
    type_hints = get_type_hints(cls)
    for field in fields(cls):
        if field.name in data:
            values[field.name] = _convert_value(type_hints.get(field.name, field.type), data[field.name])
    return cls(**values)


def _convert_value(annotation: Any, value: Any) -> Any:
    origin = get_origin(annotation)
    if origin is list:
        item_type = get_args(annotation)[0] if get_args(annotation) else Any
        return [_convert_value(item_type, item) for item in value or []]
    if origin in {UnionType, Union}:
        args = [arg for arg in get_args(annotation) if arg is not type(None)]
        return None if value is None else _convert_value(args[0], value) if args else value
    if annotation in {
        Project,
        Pattern,
        Phase,
        Structure,
        CellParameters,
        AtomSite,
        RefinementResult,
        RefinementMetrics,
        AnalysisResult,
        SeriesAnalysis,
        SeriesPoint,
        FinderProjectState,
    }:
        return _from_dataclass(annotation, value)
    return value
