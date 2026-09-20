#!/usr/bin/env python3
"""Build an exact runtime-only skill directory and optional deterministic ZIP."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath


MANIFEST_RELATIVE = Path("development/release/runtime-allowlist.json")
STABLE_VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


class ReleaseError(ValueError):
    pass


def load_object(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ReleaseError(f"expected JSON object: {path}")
    return value


def safe_relative(value: object, *, directory: bool = False) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ReleaseError(f"invalid manifest path: {value!r}")
    candidate = value[:-1] if directory and value.endswith("/") else value
    path = PurePosixPath(candidate)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ReleaseError(f"unsafe manifest path: {value}")
    normalized = path.as_posix()
    return f"{normalized}/" if directory else normalized


def string_list(manifest: dict, key: str, *, directory: bool = False) -> list[str]:
    values = manifest.get(key)
    if not isinstance(values, list):
        raise ReleaseError(f"manifest {key} must be a list")
    normalized = [safe_relative(value, directory=directory) for value in values]
    if len(normalized) != len(set(normalized)):
        raise ReleaseError(f"manifest {key} contains duplicates")
    return normalized


def load_manifest(source_root: Path) -> dict:
    manifest = load_object(source_root / MANIFEST_RELATIVE)
    if manifest.get("schema") != "ltpm-runtime-allowlist/v1":
        raise ReleaseError("unsupported runtime allowlist schema")
    result = {
        "runtime_files": string_list(manifest, "runtime_files"),
        "developer_files": string_list(manifest, "developer_files"),
        "developer_prefixes": string_list(manifest, "developer_prefixes", directory=True),
        "local_excluded_prefixes": string_list(manifest, "local_excluded_prefixes", directory=True),
        "local_excluded_names": string_list(manifest, "local_excluded_names"),
        "local_excluded_suffixes": string_list(manifest, "local_excluded_suffixes"),
    }
    runtime = set(result["runtime_files"])
    developer = set(result["developer_files"])
    overlap = runtime & developer
    if overlap:
        raise ReleaseError(f"paths cannot be both runtime and developer: {', '.join(sorted(overlap))}")
    for path in runtime:
        if any(path.startswith(prefix) for prefix in result["developer_prefixes"]):
            raise ReleaseError(f"runtime path is under a developer prefix: {path}")
    return result


def excluded(relative: str, manifest: dict) -> bool:
    path = PurePosixPath(relative)
    if any(part in manifest["local_excluded_names"] for part in path.parts):
        return True
    if any(relative == prefix[:-1] or relative.startswith(prefix) for prefix in manifest["local_excluded_prefixes"]):
        return True
    return any(relative.endswith(suffix) for suffix in manifest["local_excluded_suffixes"])


def source_files(source_root: Path, manifest: dict) -> tuple[set[str], list[str]]:
    found: set[str] = set()
    symlinks: list[str] = []
    for current, directories, filenames in os.walk(source_root, followlinks=False):
        current_path = Path(current)
        retained_directories = []
        for name in directories:
            path = current_path / name
            relative = path.relative_to(source_root).as_posix()
            if excluded(relative, manifest):
                continue
            if path.is_symlink():
                symlinks.append(relative)
                continue
            retained_directories.append(name)
        directories[:] = retained_directories
        for name in filenames:
            path = current_path / name
            relative = path.relative_to(source_root).as_posix()
            if excluded(relative, manifest):
                continue
            if path.is_symlink():
                symlinks.append(relative)
                continue
            if path.is_file():
                found.add(relative)
    return found, symlinks


def audit_source(source_root: Path, manifest: dict) -> None:
    runtime = set(manifest["runtime_files"])
    developer_files = set(manifest["developer_files"])
    found, symlinks = source_files(source_root, manifest)
    missing = sorted(runtime - found)
    if missing:
        raise ReleaseError(f"runtime allowlist files are missing: {', '.join(missing)}")
    runtime_symlinks = sorted(path for path in runtime if (source_root / path).is_symlink())
    if runtime_symlinks:
        raise ReleaseError(f"runtime files must not be symlinks: {', '.join(runtime_symlinks)}")
    if symlinks:
        raise ReleaseError(f"unclassified symlinks are not allowed: {', '.join(sorted(symlinks))}")
    classified = runtime | developer_files
    unknown = sorted(
        path
        for path in found - classified
        if not any(path.startswith(prefix) for prefix in manifest["developer_prefixes"])
    )
    if unknown:
        raise ReleaseError(f"unclassified source files block release: {', '.join(unknown)}")


def is_within(path: Path, parent: Path) -> bool:
    return path == parent or parent in path.parents


def replace_framework_version(path: Path, release_version: str) -> str:
    value = load_object(path)
    source_version = value.get("framework_version")
    if not isinstance(source_version, str) or not source_version:
        raise ReleaseError("source framework_version is missing")
    text = path.read_text(encoding="utf-8")
    old = f'"framework_version": {json.dumps(source_version)}'
    new = f'"framework_version": {json.dumps(release_version)}'
    if text.count(old) != 1:
        raise ReleaseError("framework_version could not be replaced exactly once")
    path.write_text(text.replace(old, new), encoding="utf-8")
    return source_version


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tree_report(root: Path, runtime_files: list[str]) -> tuple[list[dict], str]:
    entries = []
    tree_digest = hashlib.sha256()
    for relative in sorted(runtime_files):
        path = root / relative
        digest = sha256_file(path)
        size = path.stat().st_size
        entries.append({"path": relative, "size": size, "sha256": digest})
        tree_digest.update(relative.encode("utf-8"))
        tree_digest.update(b"\0")
        tree_digest.update(digest.encode("ascii"))
        tree_digest.update(b"\n")
    return entries, tree_digest.hexdigest()


def create_archive(root: Path, runtime_files: list[str], archive_path: Path) -> str:
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=archive_path.parent, prefix=".runtime-archive-", delete=False) as temporary:
        temporary_path = Path(temporary.name)
    try:
        with zipfile.ZipFile(temporary_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for relative in sorted(runtime_files):
                source = root / relative
                info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = (stat.S_IMODE(source.stat().st_mode) & 0xFFFF) << 16
                archive.writestr(info, source.read_bytes())
        temporary_path.replace(archive_path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()
    return sha256_file(archive_path)


def git_revision(source_root: Path) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(source_root), "rev-parse", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def build(source_root: Path, output_dir: Path, release_version: str, archive_path: Path | None) -> dict:
    source_root = source_root.resolve()
    output_dir = output_dir.resolve()
    archive_path = archive_path.resolve() if archive_path else None
    if not source_root.is_dir():
        raise ReleaseError(f"source root is not a directory: {source_root}")
    if not STABLE_VERSION_RE.fullmatch(release_version):
        raise ReleaseError("release version must be stable MAJOR.MINOR.PATCH")
    if output_dir.exists():
        raise ReleaseError(f"output directory already exists: {output_dir}")
    if is_within(output_dir, source_root):
        raise ReleaseError("output directory must be outside the source tree")
    if archive_path:
        if archive_path.exists():
            raise ReleaseError(f"archive already exists: {archive_path}")
        if is_within(archive_path, source_root):
            raise ReleaseError("archive must be outside the source tree")

    manifest = load_manifest(source_root)
    audit_source(source_root, manifest)
    runtime_files = manifest["runtime_files"]
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary_root = Path(tempfile.mkdtemp(prefix=".runtime-build-", dir=output_dir.parent))
    try:
        for relative in runtime_files:
            source = source_root / relative
            destination = temporary_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        source_version = replace_framework_version(
            temporary_root / "references" / "framework-map.json", release_version
        )
        produced = {
            path.relative_to(temporary_root).as_posix()
            for path in temporary_root.rglob("*")
            if path.is_file()
        }
        if produced != set(runtime_files):
            raise ReleaseError("runtime output does not exactly match the allowlist")
        entries, tree_sha256 = tree_report(temporary_root, runtime_files)
        temporary_root.replace(output_dir)
    except Exception:
        if temporary_root.exists():
            shutil.rmtree(temporary_root)
        raise

    archive_sha256 = create_archive(output_dir, runtime_files, archive_path) if archive_path else None
    return {
        "schema": "ltpm-runtime-build-report/v1",
        "source_revision": git_revision(source_root),
        "source_framework_version": source_version,
        "release_version": release_version,
        "output_dir": str(output_dir),
        "file_count": len(entries),
        "total_bytes": sum(entry["size"] for entry in entries),
        "tree_sha256": tree_sha256,
        "archive": str(archive_path) if archive_path else None,
        "archive_sha256": archive_sha256,
        "files": entries,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--release-version", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--archive", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = build(args.source_root, args.output_dir, args.release_version, args.archive)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"built": False, "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    print(json.dumps({"built": True, **report}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
