from __future__ import annotations

import os
from pathlib import Path


APP_DATA_ENV = "XRD_MANAGER_DATA_DIR"
APP_DATA_DIR_NAME = "XRD Finder"


def default_data_root() -> Path:
    env_path = os.environ.get(APP_DATA_ENV)
    if env_path:
        return Path(env_path).expanduser()

    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA")
        if base:
            return Path(base) / APP_DATA_DIR_NAME
        return Path.home() / "AppData" / "Local" / APP_DATA_DIR_NAME

    if sys_platform() == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_DATA_DIR_NAME

    base = os.environ.get("XDG_DATA_HOME")
    if base:
        return Path(base) / "xrd-finder"
    return Path.home() / ".local" / "share" / "xrd-finder"


def default_phase_cache_root() -> Path:
    return default_data_root() / "cod_cache"


def sys_platform() -> str:
    import sys

    return sys.platform
