from __future__ import annotations

import importlib
import json
import os
from importlib.metadata import entry_points
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "mouse_engine.json"
ENTRY_POINT_GROUP = "runescapetwo.mouse_engines"
SUPPORTED_API_VERSION = 1

DEFAULT_SETTINGS: dict[str, Any] = {
    "enabled": False,
    "provider": "ai_mouse_lab",
    "package_url": "",
    "profile_path": "",
    "fallback_on_error": True,
    "default_target_radius_px": 6,
    "default_padding_px": 0,
}

_provider: Any | None = None
_provider_name: str | None = None


class MouseEngineError(RuntimeError):
    pass


class MouseEngineDisabled(MouseEngineError):
    pass


class MouseEngineUnavailable(MouseEngineError):
    pass


def _expand_path(value: str | os.PathLike[str]) -> Path:
    return Path(os.path.expanduser(os.path.expandvars(os.fspath(value))))


def load_settings(path: Path = CONFIG_PATH) -> dict[str, Any]:
    settings = dict(DEFAULT_SETTINGS)
    try:
        stored = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        stored = {}
    except json.JSONDecodeError as exc:
        raise MouseEngineError(f"Invalid mouse-engine config: {path}") from exc
    if not isinstance(stored, dict):
        raise MouseEngineError(f"Mouse-engine config must be an object: {path}")
    settings.update(stored)
    return settings


def save_settings(settings: Mapping[str, Any], path: Path = CONFIG_PATH) -> dict[str, Any]:
    clean = dict(DEFAULT_SETTINGS)
    clean.update(dict(settings))
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(clean, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)
    return clean


def configured_profile_path(settings: Mapping[str, Any] | None = None) -> Path | None:
    value = str((settings or load_settings()).get("profile_path", "")).strip()
    return _expand_path(value) if value else None


def reset_provider_cache() -> None:
    global _provider, _provider_name
    _provider = None
    _provider_name = None
    importlib.invalidate_caches()


def get_provider(
    settings: Mapping[str, Any] | None = None,
    *,
    refresh: bool = False,
) -> Any:
    global _provider, _provider_name
    selected = dict(settings or load_settings())
    if not bool(selected.get("enabled")):
        raise MouseEngineDisabled("External mouse engine is disabled")

    name = str(selected.get("provider", "")).strip()
    if not name:
        raise MouseEngineUnavailable("No mouse-engine provider is configured")
    if refresh:
        reset_provider_cache()
    if _provider is not None and _provider_name == name:
        return _provider

    matches = [point for point in entry_points(group=ENTRY_POINT_GROUP) if point.name == name]
    if not matches:
        raise MouseEngineUnavailable(
            f"Mouse provider '{name}' is not installed. Open Mouse Engine Setup."
        )
    if len(matches) > 1:
        raise MouseEngineUnavailable(
            f"Multiple installed mouse providers use the name '{name}'"
        )

    provider = matches[0].load()()
    manifest = provider.manifest()
    api_version = int(manifest.get("api_version", 0))
    if api_version != SUPPORTED_API_VERSION:
        raise MouseEngineUnavailable(
            f"Provider API {api_version} is unsupported; expected {SUPPORTED_API_VERSION}"
        )
    if not callable(getattr(provider, "create_plan", None)):
        raise MouseEngineUnavailable(f"Provider '{name}' has no create_plan function")

    _provider = provider
    _provider_name = name
    return provider


def create_plan(
    start: Sequence[float],
    target: Mapping[str, Any] | Sequence[float],
    *,
    target_radius: float | None = None,
    padding_px: float | None = None,
    coordinate_size: Sequence[float] = (1920, 1080),
    settings: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    selected = dict(settings or load_settings())
    provider = get_provider(selected)
    profile = configured_profile_path(selected)
    if profile is None:
        raise MouseEngineUnavailable("No personal mouse profile is configured")
    if not profile.is_file():
        raise MouseEngineUnavailable(f"Personal mouse profile not found: {profile}")

    chosen_padding = (
        float(selected.get("default_padding_px", 0))
        if padding_px is None
        else float(padding_px)
    )
    return provider.create_plan(
        start=start,
        target=target,
        target_radius=target_radius,
        padding_px=chosen_padding,
        coordinate_size=coordinate_size,
        profile_path=profile,
    )


def provider_status(settings: Mapping[str, Any] | None = None) -> dict[str, Any]:
    selected = dict(settings or load_settings())
    profile = configured_profile_path(selected)
    result: dict[str, Any] = {
        "enabled": bool(selected.get("enabled")),
        "provider": str(selected.get("provider", "")),
        "package_url": str(selected.get("package_url", "")),
        "profile_path": str(profile) if profile else "",
        "profile_found": bool(profile and profile.is_file()),
        "ready": False,
    }
    try:
        provider = get_provider(selected, refresh=True)
        result["manifest"] = provider.manifest()
        result["ready"] = result["profile_found"]
    except MouseEngineError as exc:
        result["error"] = str(exc)
    return result


def install_configured_package(
    settings: Mapping[str, Any] | None = None,
) -> subprocess.CompletedProcess[str]:
    selected = dict(settings or load_settings())
    package_url = str(selected.get("package_url", "")).strip()
    if not package_url:
        raise MouseEngineError("No package URL is configured")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--upgrade",
            "--force-reinstall",
            "--no-deps",
            package_url,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "pip install failed"
        raise MouseEngineError(message)
    reset_provider_cache()
    return result


__all__ = [
    "CONFIG_PATH",
    "MouseEngineDisabled",
    "MouseEngineError",
    "MouseEngineUnavailable",
    "configured_profile_path",
    "create_plan",
    "get_provider",
    "install_configured_package",
    "load_settings",
    "provider_status",
    "reset_provider_cache",
    "save_settings",
]
