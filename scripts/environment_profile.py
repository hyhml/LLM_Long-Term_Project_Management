#!/usr/bin/env python3
"""Detect a private machine-profile draft or save a user-confirmed profile."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import platform
import shutil
import sys
from pathlib import Path


COMMANDS = (
    "codex",
    "git",
    "python3",
    "node",
    "npm",
    "uv",
    "rg",
    "jq",
    "ffmpeg",
    "docker",
    "nvidia-smi",
)
PROHIBITED_KEY_PARTS = ("password", "passwd", "secret", "token", "credential", "api_key", "private_key")


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def memory_bytes() -> int | None:
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("MemTotal:"):
                return int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        return None
    return None


def skill_names() -> list[str]:
    names: set[str] = set()
    for base in (Path.home() / ".agents" / "skills", Path.home() / ".codex" / "skills"):
        if not base.is_dir():
            continue
        try:
            for marker in base.glob("*/SKILL.md"):
                names.add(marker.parent.name)
        except OSError:
            pass
    return sorted(names)


def model_names() -> list[str]:
    names: set[str] = set()
    candidates = [Path.home() / ".cache" / "huggingface" / "hub", Path.home() / "models"]
    custom = os.environ.get("HF_HOME")
    if custom:
        candidates.insert(0, Path(custom).expanduser() / "hub")
    for base in candidates:
        if not base.is_dir():
            continue
        try:
            for item in base.iterdir():
                if item.is_dir() and (item.name.startswith("models--") or base.name == "models"):
                    names.add(item.name.replace("models--", "").replace("--", "/"))
        except OSError:
            pass
    return sorted(names)


def detect() -> dict:
    commands = {name: bool(shutil.which(name)) for name in COMMANDS}
    accelerators = []
    if commands["nvidia-smi"]:
        accelerators.append({"type": "nvidia", "status": "command-detected-not-verified"})
    return {
        "schema_version": 1,
        "profile_revision": 0,
        "status": "draft-unconfirmed",
        "generated_at": utc_now(),
        "system": {
            "os": platform.system(),
            "os_release": platform.release(),
            "architecture": platform.machine(),
            "python": platform.python_version(),
        },
        "resources": {
            "logical_cpu_count": os.cpu_count(),
            "memory_bytes": memory_bytes(),
            "accelerators": accelerators,
        },
        "commands": commands,
        "installed_skills": skill_names(),
        "local_model_names": model_names(),
        "user_notes": [],
    }


def reject_sensitive_keys(value: object, prefix: str = "") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = str(key).lower()
            if any(part in lowered for part in PROHIBITED_KEY_PARTS):
                raise ValueError(f"sensitive key is not allowed in machine profile: {prefix}{key}")
            reject_sensitive_keys(child, f"{prefix}{key}.")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            reject_sensitive_keys(child, f"{prefix}{index}.")


def save(input_path: Path) -> dict:
    profile = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(profile, dict):
        raise ValueError("confirmed profile must be a JSON object")
    reject_sensitive_keys(profile)
    destination = Path(__file__).resolve().parents[1] / "private" / "local-environment.json"
    previous_revision = 0
    if destination.is_file():
        previous = json.loads(destination.read_text(encoding="utf-8"))
        previous_revision = int(previous.get("profile_revision", 0))
    profile["schema_version"] = 1
    profile["profile_revision"] = previous_revision + 1
    profile["status"] = "user-confirmed"
    profile["confirmed_at"] = utc_now()
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".tmp")
    temporary.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(destination)
    return {"saved": str(destination), "profile_revision": profile["profile_revision"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("detect")
    save_parser = subparsers.add_parser("save")
    save_parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "detect":
        print(json.dumps(detect(), ensure_ascii=False, indent=2))
        return 0
    try:
        result = save(args.input.expanduser().resolve())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"saved": False, "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
