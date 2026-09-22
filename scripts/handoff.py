#!/usr/bin/env python3
"""Export, verify, and safely unpack single-file .llmpack handoffs."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import stat
import sys
import tempfile
import uuid
import zipfile
from pathlib import Path, PurePosixPath

from project_binding import require_binding

FORMAT = "llm-long-term-project-handoff"
SCHEMA_VERSION = 1
MAX_ENTRIES = 1000
MAX_ENTRY_BYTES = 256 * 1024 * 1024
MAX_TOTAL_BYTES = 512 * 1024 * 1024
HANDOFF_REQUIRED = {
    "task_id": str,
    "completion_criteria": list,
    "summary": str,
    "findings": list,
    "attempts": list,
    "failed_directions": list,
    "evidence": list,
    "artifacts": list,
    "candidate_tools": list,
    "proposed_changes": list,
    "open_questions": list,
    "next_task_candidates": list,
}
HANDOFF_OPTIONAL = {"execution_environment_summary"}


class PackageError(ValueError):
    pass


def canonical_json(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_member(name: str) -> str:
    if not isinstance(name, str):
        raise PackageError("archive path must be a string")
    if "\\" in name or name.startswith("/"):
        raise PackageError(f"unsafe archive path: {name}")
    path = PurePosixPath(name)
    if not name or path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise PackageError(f"unsafe archive path: {name}")
    return path.as_posix()


def validate_handoff(value: object) -> dict:
    if not isinstance(value, dict):
        raise PackageError("handoff must be a JSON object")
    unknown = set(value) - set(HANDOFF_REQUIRED) - HANDOFF_OPTIONAL
    if unknown:
        raise PackageError(f"unknown handoff fields: {', '.join(sorted(unknown))}")
    for key, expected in HANDOFF_REQUIRED.items():
        if key not in value or not isinstance(value[key], expected):
            raise PackageError(f"handoff field {key} must be {expected.__name__}")
    if not value["task_id"]:
        raise PackageError("task_id must not be empty")
    if any(not isinstance(item, str) for item in value["completion_criteria"]):
        raise PackageError("completion_criteria items must be strings")
    object_lists = (
        "findings",
        "attempts",
        "failed_directions",
        "evidence",
        "artifacts",
        "candidate_tools",
        "proposed_changes",
        "open_questions",
        "next_task_candidates",
    )
    for field in object_lists:
        if any(not isinstance(item, dict) for item in value[field]):
            raise PackageError(f"{field} items must be objects")
    if "execution_environment_summary" in value and not isinstance(value["execution_environment_summary"], dict):
        raise PackageError("execution_environment_summary must be an object")
    change_ids: set[str] = set()
    for index, change in enumerate(value["proposed_changes"]):
        if not isinstance(change, dict):
            raise PackageError(f"proposed_changes[{index}] must be an object")
        missing = {"change_id", "operation", "target", "reason", "value"} - set(change)
        if missing:
            raise PackageError(f"proposed_changes[{index}] missing: {', '.join(sorted(missing))}")
        change_id = change["change_id"]
        if not isinstance(change_id, str) or not change_id or change_id in change_ids:
            raise PackageError("change_id values must be non-empty and unique")
        change_ids.add(change_id)
    return value


def parse_artifact(spec: str) -> tuple[Path, str]:
    if "=" not in spec:
        raise PackageError("artifact must use SOURCE=artifacts/RELATIVE_PATH")
    source_text, archive_name = spec.split("=", 1)
    source = Path(source_text).expanduser().resolve()
    archive_name = safe_member(archive_name)
    if not archive_name.startswith("artifacts/"):
        raise PackageError("artifact destination must start with artifacts/")
    if not source.is_file() or source.is_symlink():
        raise PackageError(f"artifact must be a regular non-symlink file: {source}")
    return source, archive_name


def package_plan(args: argparse.Namespace) -> tuple[dict, dict, dict, dict[str, bytes | Path], Path]:
    project_skill = args.project_skill.expanduser().resolve()
    binding = require_binding(project_skill, write=True)
    project_state = json.loads((project_skill / "state" / "project.json").read_text(encoding="utf-8"))
    handoff_path = args.handoff.expanduser().resolve()
    handoff = validate_handoff(json.loads(handoff_path.read_text(encoding="utf-8")))
    handoff_bytes = canonical_json(handoff)

    entries: dict[str, bytes | Path] = {"handoff.json": handoff_bytes}
    sources = [{"source": str(handoff_path), "archive_path": "handoff.json"}]
    for spec in args.artifact:
        source, archive_name = parse_artifact(spec)
        if archive_name in entries:
            raise PackageError(f"duplicate archive destination: {archive_name}")
        entries[archive_name] = source
        sources.append({"source": str(source), "archive_path": archive_name})

    manifest_entries = []
    for name in sorted(entries):
        value = entries[name]
        if isinstance(value, bytes):
            size = len(value)
            digest = sha256_bytes(value)
        else:
            size = value.stat().st_size
            digest = sha256_file(value)
        if size > MAX_ENTRY_BYTES:
            raise PackageError(f"entry exceeds {MAX_ENTRY_BYTES} bytes: {name}")
        manifest_entries.append({"path": name, "size": size, "sha256": digest})
    if sum(item["size"] for item in manifest_entries) > MAX_TOTAL_BYTES:
        raise PackageError(f"package payload exceeds {MAX_TOTAL_BYTES} bytes")

    output = args.output.expanduser().resolve()
    if output.exists():
        raise PackageError(f"output already exists: {output}")
    if output.suffix != ".llmpack":
        raise PackageError("output filename must end with .llmpack")
    plan = {
        "package_type": "llmpack",
        "framework_version": binding["manager_framework_version"],
        "entry_protocol": binding["entry_protocol"],
        "project_id": project_state["project_id"],
        "task_id": handoff["task_id"],
        "base_revision": project_state["revision"],
        "destination": str(output),
        "sources": sources,
        "entries": manifest_entries,
        "privacy_exclusions": ["private machine profile", "credentials", "unlisted files"],
        "local_creation_only": True,
        "automatic_upload": False,
    }
    return plan, binding, handoff, entries, output


def preview_package(args: argparse.Namespace) -> dict:
    plan, _, _, _, _ = package_plan(args)
    return {**plan, "preview_sha256": sha256_bytes(canonical_json(plan))}


def export_package(args: argparse.Namespace) -> dict:
    plan, binding, handoff, entries, output = package_plan(args)
    expected_approval = sha256_bytes(canonical_json(plan))
    if not args.approved_preview_sha256:
        raise PackageError("approved preview SHA-256 is required before package creation")
    if args.approved_preview_sha256 != expected_approval:
        raise PackageError("approved preview SHA-256 does not match the current package preview")

    manifest = {
        "format": FORMAT,
        "schema_version": SCHEMA_VERSION,
        "framework_version": binding["manager_framework_version"],
        "entry_protocol": binding["entry_protocol"],
        "package_id": f"pkg-{uuid.uuid4()}",
        "project_id": plan["project_id"],
        "task_id": handoff["task_id"],
        "base_revision": plan["base_revision"],
        "created_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "entries": plan["entries"],
    }
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(dir=output.parent, prefix=".llmpack-", delete=False) as temporary:
        temporary_path = Path(temporary.name)
    try:
        with zipfile.ZipFile(temporary_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("manifest.json", canonical_json(manifest))
            for name in sorted(entries):
                value = entries[name]
                if isinstance(value, bytes):
                    archive.writestr(name, value)
                else:
                    archive.write(value, arcname=name)
        # Verify the temporary archive against the approved manifest before it becomes final.
        read_verified(temporary_path)
        temporary_path.replace(output)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()
    return {
        **manifest,
        "path": str(output),
        "package_sha256": sha256_file(output),
        "approved_preview_sha256": expected_approval,
    }


def read_verified(path: Path) -> tuple[dict, dict[str, bytes]]:
    if not path.is_file():
        raise PackageError(f"package not found: {path}")
    with zipfile.ZipFile(path, "r") as archive:
        infos = archive.infolist()
        if len(infos) > MAX_ENTRIES + 1:
            raise PackageError(f"archive contains more than {MAX_ENTRIES} payload entries")
        names = [safe_member(info.filename) for info in infos]
        if len(names) != len(set(names)):
            raise PackageError("archive contains duplicate members")
        for info in infos:
            mode = (info.external_attr >> 16) & 0o170000
            if mode == stat.S_IFLNK:
                raise PackageError(f"archive contains a symlink: {info.filename}")
            if info.is_dir():
                raise PackageError(f"archive contains an unexpected directory member: {info.filename}")
        if "manifest.json" not in names:
            raise PackageError("manifest.json is missing")
        try:
            manifest = json.loads(archive.read("manifest.json"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise PackageError(f"invalid manifest: {exc}") from exc
        if manifest.get("format") != FORMAT or manifest.get("schema_version") != SCHEMA_VERSION:
            raise PackageError("unsupported package format or schema version")
        entry_specs = manifest.get("entries")
        if not isinstance(entry_specs, list):
            raise PackageError("manifest entries must be a list")
        if len(entry_specs) > MAX_ENTRIES:
            raise PackageError(f"manifest contains more than {MAX_ENTRIES} entries")
        expected = {"manifest.json"}
        payload: dict[str, bytes] = {}
        total_size = 0
        for spec in entry_specs:
            if not isinstance(spec, dict) or set(spec) != {"path", "size", "sha256"}:
                raise PackageError("invalid manifest entry")
            member = safe_member(spec["path"])
            size = spec["size"]
            digest = spec["sha256"]
            if not isinstance(size, int) or isinstance(size, bool) or size < 0 or size > MAX_ENTRY_BYTES:
                raise PackageError(f"invalid or excessive entry size: {member}")
            if not isinstance(digest, str) or len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
                raise PackageError(f"invalid SHA-256 value: {member}")
            total_size += size
            if total_size > MAX_TOTAL_BYTES:
                raise PackageError(f"package payload exceeds {MAX_TOTAL_BYTES} bytes")
            if member in expected:
                raise PackageError(f"duplicate manifest path: {member}")
            expected.add(member)
            try:
                info = archive.getinfo(member)
                if info.file_size != size:
                    raise PackageError(f"declared size does not match archive metadata: {member}")
                data = archive.read(member)
            except KeyError as exc:
                raise PackageError(f"manifest member is missing: {member}") from exc
            if len(data) != size or sha256_bytes(data) != digest:
                raise PackageError(f"integrity check failed: {member}")
            payload[member] = data
        if set(names) != expected:
            extras = sorted(set(names) - expected)
            missing = sorted(expected - set(names))
            raise PackageError(f"archive member set mismatch; extra={extras}, missing={missing}")
        if "handoff.json" not in payload:
            raise PackageError("handoff.json is missing from manifest")
        try:
            validate_handoff(json.loads(payload["handoff.json"]))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise PackageError(f"invalid handoff JSON: {exc}") from exc
    return manifest, payload


def verify_package(path: Path) -> dict:
    manifest, _ = read_verified(path)
    return {**manifest, "path": str(path), "package_sha256": sha256_file(path), "verified": True}


def check_destination(path: Path, project_skill: Path) -> dict:
    manifest, _ = read_verified(path)
    binding = require_binding(project_skill, write=False)
    if manifest.get("project_id") != binding["project_id"]:
        raise PackageError(
            f"package project_id {manifest.get('project_id')} does not match destination {binding['project_id']}"
        )
    revision_match = manifest.get("base_revision") == binding["project_revision"]
    return {
        "package_id": manifest.get("package_id"),
        "project_id": binding["project_id"],
        "destination": str(project_skill),
        "binding_status": binding["status"],
        "base_revision": manifest.get("base_revision"),
        "destination_revision": binding["project_revision"],
        "revision_match": revision_match,
        "formal_commit_allowed": revision_match and binding["write_allowed"],
        "verified": True,
    }


def unpack_package(path: Path, destination: Path) -> dict:
    manifest, payload = read_verified(path)
    if destination.exists():
        raise PackageError(f"output directory already exists: {destination}")
    destination.mkdir(parents=True)
    try:
        (destination / "manifest.json").write_bytes(canonical_json(manifest))
        for name, data in payload.items():
            target = destination.joinpath(*PurePosixPath(name).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    except Exception:
        # Leave a partial directory visible for diagnosis; never overwrite another destination.
        raise
    return {"unpacked": str(destination), "package_id": manifest["package_id"], "verified": True}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    def add_package_arguments(command_parser: argparse.ArgumentParser) -> None:
        command_parser.add_argument("--project-skill", type=Path, required=True)
        command_parser.add_argument("--handoff", type=Path, required=True)
        command_parser.add_argument("--output", type=Path, required=True)
        command_parser.add_argument("--artifact", action="append", default=[])

    preview_parser = subparsers.add_parser("preview")
    add_package_arguments(preview_parser)
    export_parser = subparsers.add_parser("export")
    add_package_arguments(export_parser)
    export_parser.add_argument("--approved-preview-sha256")
    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("package", type=Path)
    unpack_parser = subparsers.add_parser("unpack")
    unpack_parser.add_argument("package", type=Path)
    unpack_parser.add_argument("--output-dir", type=Path, required=True)
    destination_parser = subparsers.add_parser("check-destination")
    destination_parser.add_argument("package", type=Path)
    destination_parser.add_argument("--project-skill", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.command == "preview":
            result = preview_package(args)
        elif args.command == "export":
            result = export_package(args)
        elif args.command == "verify":
            result = verify_package(args.package.expanduser().resolve())
        elif args.command == "unpack":
            result = unpack_package(args.package.expanduser().resolve(), args.output_dir.expanduser().resolve())
        else:
            result = check_destination(
                args.package.expanduser().resolve(), args.project_skill.expanduser().resolve()
            )
    except (OSError, KeyError, ValueError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    print(json.dumps({"ok": True, **result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
