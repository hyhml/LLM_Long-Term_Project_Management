#!/usr/bin/env python3
"""Export and inspect consent-based single-file framework feedback."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import stat
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath


FORMAT = "ltpm-framework-feedback"
SCHEMA = "ltpm-framework-feedback/v1"
SCHEMA_VERSION = 1
REDACTION_SCHEMA = "ltpm-feedback-redaction-report/v1"
MAX_ENTRIES = 64
MAX_ENTRY_BYTES = 10 * 1024 * 1024
MAX_TOTAL_BYTES = 25 * 1024 * 1024

KINDS = {"bug", "ambiguity", "missing-capability", "usability", "compatibility", "data-loss-risk"}
CATEGORIES = {
    "framework-defect-candidate",
    "child-adapter-defect",
    "project-data",
    "project-specific",
    "environment",
    "external-tool",
    "usage-or-documentation",
    "unknown",
}
REMEDIATIONS = {
    "shared-runtime-fix",
    "child-adapter-upgrade",
    "project-data-migration",
    "documentation-only",
    "environment-only",
    "unknown",
}
EXPORT_SECTIONS = {
    "producer",
    "problem",
    "classification_proposal",
    "context",
    "evidence",
    "privacy",
    "request",
    "redaction-report",
}


class FeedbackError(ValueError):
    pass


def canonical_json(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_member(name: object) -> str:
    if not isinstance(name, str) or not name or "\\" in name or name.startswith("/"):
        raise FeedbackError(f"unsafe archive path: {name!r}")
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise FeedbackError(f"unsafe archive path: {name}")
    return path.as_posix()


def require_object(value: object, label: str, fields: set[str]) -> dict:
    if not isinstance(value, dict):
        raise FeedbackError(f"{label} must be an object")
    missing = fields - set(value)
    unknown = set(value) - fields
    if missing or unknown:
        raise FeedbackError(f"{label} fields mismatch; missing={sorted(missing)}, unknown={sorted(unknown)}")
    return value


def require_string(value: object, label: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value):
        raise FeedbackError(f"{label} must be a {'possibly empty ' if allow_empty else 'non-empty '}string")
    return value


def require_string_list(value: object, label: str, *, nonempty: bool = False) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise FeedbackError(f"{label} must be a list of strings")
    if nonempty and not value:
        raise FeedbackError(f"{label} must not be empty")
    return value


def validate_datetime(value: object, label: str) -> str:
    text = require_string(value, label)
    try:
        dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise FeedbackError(f"{label} must be an ISO-8601 date-time") from exc
    return text


def validate_issue(value: object) -> dict:
    issue = require_object(
        value,
        "issue",
        {
            "schema", "feedback_id", "created_at", "producer", "problem",
            "classification_proposal", "context", "evidence", "privacy", "consent", "request",
        },
    )
    if issue["schema"] != SCHEMA:
        raise FeedbackError(f"unsupported issue schema: {issue['schema']!r}")
    feedback_id = require_string(issue["feedback_id"], "feedback_id")
    if re.fullmatch(r"fb-[A-Za-z0-9][A-Za-z0-9._-]{5,127}", feedback_id) is None:
        raise FeedbackError("feedback_id must be a safe stable identifier beginning with fb-")
    validate_datetime(issue["created_at"], "created_at")

    producer = require_object(
        issue["producer"], "producer", {"framework_version", "child_protocol_version", "platform", "tool_versions"}
    )
    require_string(producer["framework_version"], "producer.framework_version")
    protocol = producer["child_protocol_version"]
    if protocol is not None and (not isinstance(protocol, int) or isinstance(protocol, bool) or protocol < 1):
        raise FeedbackError("producer.child_protocol_version must be null or a positive integer")
    require_string(producer["platform"], "producer.platform")
    require_string_list(producer["tool_versions"], "producer.tool_versions")

    problem = require_object(
        issue["problem"],
        "problem",
        {"kind", "title", "observed_behavior", "expected_behavior", "reproduction_steps", "frequency", "impact", "blocking"},
    )
    if problem["kind"] not in KINDS:
        raise FeedbackError("problem.kind is unsupported")
    for key in ("title", "observed_behavior", "expected_behavior", "impact"):
        require_string(problem[key], f"problem.{key}")
    require_string_list(problem["reproduction_steps"], "problem.reproduction_steps")
    if problem["frequency"] not in {"once", "intermittent", "always", "unknown"}:
        raise FeedbackError("problem.frequency is unsupported")
    if not isinstance(problem["blocking"], bool):
        raise FeedbackError("problem.blocking must be boolean")

    classification = require_object(
        issue["classification_proposal"],
        "classification_proposal",
        {"category", "reasoning", "confidence", "suspected_component", "remediation_scope"},
    )
    if classification["category"] not in CATEGORIES:
        raise FeedbackError("classification_proposal.category is unsupported")
    require_string(classification["reasoning"], "classification_proposal.reasoning", allow_empty=True)
    if classification["confidence"] not in {"low", "medium", "high"}:
        raise FeedbackError("classification_proposal.confidence is unsupported")
    if classification["suspected_component"] is not None:
        require_string(classification["suspected_component"], "classification_proposal.suspected_component")
    if classification["remediation_scope"] not in REMEDIATIONS:
        raise FeedbackError("classification_proposal.remediation_scope is unsupported")

    context = require_object(issue["context"], "context", {"project_alias", "project_revision", "task_id"})
    for key in ("project_alias", "task_id"):
        if context[key] is not None:
            require_string(context[key], f"context.{key}")
    revision = context["project_revision"]
    if revision is not None and (not isinstance(revision, int) or isinstance(revision, bool) or revision < 0):
        raise FeedbackError("context.project_revision must be null or a non-negative integer")

    evidence = require_object(
        issue["evidence"],
        "evidence",
        {"included_items", "errors", "artifact_hashes", "inspected_scope", "uninspected_scope", "known_gaps"},
    )
    for key in ("included_items", "errors", "inspected_scope", "uninspected_scope", "known_gaps"):
        require_string_list(evidence[key], f"evidence.{key}")
    if not isinstance(evidence["artifact_hashes"], list):
        raise FeedbackError("evidence.artifact_hashes must be a list")
    for index, item in enumerate(evidence["artifact_hashes"]):
        item = require_object(item, f"evidence.artifact_hashes[{index}]", {"label", "sha256"})
        require_string(item["label"], f"evidence.artifact_hashes[{index}].label")
        digest = require_string(item["sha256"], f"evidence.artifact_hashes[{index}].sha256")
        if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
            raise FeedbackError(f"evidence.artifact_hashes[{index}].sha256 is invalid")

    privacy = require_object(issue["privacy"], "privacy", {"sensitivity", "redactions", "excluded_items"})
    if privacy["sensitivity"] not in {"public", "internal", "private", "unknown"}:
        raise FeedbackError("privacy.sensitivity is unsupported")
    require_string_list(privacy["redactions"], "privacy.redactions")
    require_string_list(privacy["excluded_items"], "privacy.excluded_items")

    consent = require_object(issue["consent"], "consent", {"local_collection", "export", "developer_use"})
    local = require_object(consent["local_collection"], "consent.local_collection", {"approved", "approved_at", "scope"})
    if local["approved"] is not True:
        raise FeedbackError("local evidence collection was not approved")
    validate_datetime(local["approved_at"], "consent.local_collection.approved_at")
    require_string_list(local["scope"], "consent.local_collection.scope", nonempty=True)
    export = require_object(
        consent["export"], "consent.export", {"approved", "approved_at", "approved_fields", "approved_attachments"}
    )
    if export["approved"] is not True:
        raise FeedbackError("feedback export was not approved")
    validate_datetime(export["approved_at"], "consent.export.approved_at")
    approved_fields = require_string_list(export["approved_fields"], "consent.export.approved_fields", nonempty=True)
    if set(approved_fields) != EXPORT_SECTIONS or len(approved_fields) != len(EXPORT_SECTIONS):
        raise FeedbackError(
            "approved_fields must exactly approve each exported content section: "
            + ", ".join(sorted(EXPORT_SECTIONS))
        )
    attachments = require_string_list(export["approved_attachments"], "consent.export.approved_attachments")
    if len(attachments) != len(set(attachments)):
        raise FeedbackError("approved attachment paths must be unique")
    for item in attachments:
        if not safe_member(item).startswith("attachments/"):
            raise FeedbackError("approved attachment paths must start with attachments/")
    developer = require_object(
        consent["developer_use"], "consent.developer_use", {"read_approved", "retention", "allow_synthetic_derivative"}
    )
    if developer["read_approved"] is not True:
        raise FeedbackError("developer reading was not approved")
    if developer["retention"] not in {"one-shot", "until-resolved", "long-term-regression-candidate"}:
        raise FeedbackError("consent.developer_use.retention is unsupported")
    if not isinstance(developer["allow_synthetic_derivative"], bool):
        raise FeedbackError("consent.developer_use.allow_synthetic_derivative must be boolean")

    request = require_object(issue["request"], "request", {"desired_outcome", "acceptable_workaround"})
    require_string(request["desired_outcome"], "request.desired_outcome")
    if request["acceptable_workaround"] is not None:
        require_string(request["acceptable_workaround"], "request.acceptable_workaround")
    return issue


def validate_redaction(value: object, feedback_id: str) -> dict:
    report = require_object(
        value,
        "redaction report",
        {"schema", "feedback_id", "reviewed_at", "included", "excluded", "detected_sensitive", "residual_risks", "user_confirmed"},
    )
    if report["schema"] != REDACTION_SCHEMA or report["feedback_id"] != feedback_id:
        raise FeedbackError("redaction report schema or feedback_id does not match")
    validate_datetime(report["reviewed_at"], "redaction_report.reviewed_at")
    for key in ("included", "excluded", "detected_sensitive", "residual_risks"):
        require_string_list(report[key], f"redaction_report.{key}")
    if report["user_confirmed"] is not True:
        raise FeedbackError("redaction report was not confirmed by the user")
    return report


def load_json(path: Path, label: str) -> object:
    try:
        return json.loads(path.expanduser().resolve().read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FeedbackError(f"cannot read {label}: {exc}") from exc


def parse_attachment(spec: str) -> tuple[Path, str]:
    if "=" not in spec:
        raise FeedbackError("attachment must use SOURCE=attachments/RELATIVE_PATH")
    source_text, destination = spec.split("=", 1)
    source = Path(source_text).expanduser().resolve()
    destination = safe_member(destination)
    if not destination.startswith("attachments/"):
        raise FeedbackError("attachment destination must start with attachments/")
    if not source.is_file() or source.is_symlink():
        raise FeedbackError(f"attachment must be a regular non-symlink file: {source}")
    return source, destination


def export_package(args: argparse.Namespace) -> dict:
    issue = validate_issue(load_json(args.issue, "issue"))
    redaction = validate_redaction(load_json(args.redaction_report, "redaction report"), issue["feedback_id"])
    entries: dict[str, bytes | Path] = {
        "issue.json": canonical_json(issue),
        "redaction-report.json": canonical_json(redaction),
    }
    supplied: set[str] = set()
    for spec in args.attachment:
        source, destination = parse_attachment(spec)
        if destination in entries:
            raise FeedbackError(f"duplicate archive destination: {destination}")
        entries[destination] = source
        supplied.add(destination)
    approved = set(issue["consent"]["export"]["approved_attachments"])
    if supplied != approved:
        raise FeedbackError(f"attachment approval mismatch; supplied={sorted(supplied)}, approved={sorted(approved)}")

    manifest_entries = []
    for name in sorted(entries):
        value = entries[name]
        size = len(value) if isinstance(value, bytes) else value.stat().st_size
        digest = sha256_bytes(value) if isinstance(value, bytes) else sha256_file(value)
        if size > MAX_ENTRY_BYTES:
            raise FeedbackError(f"entry exceeds {MAX_ENTRY_BYTES} bytes: {name}")
        manifest_entries.append({"path": name, "size": size, "sha256": digest})
    if len(manifest_entries) > MAX_ENTRIES or sum(item["size"] for item in manifest_entries) > MAX_TOTAL_BYTES:
        raise FeedbackError("feedback package exceeds entry or total-size limits")

    manifest = {
        "format": FORMAT,
        "schema_version": SCHEMA_VERSION,
        "feedback_id": issue["feedback_id"],
        "created_at": issue["created_at"],
        "producer": {
            "framework_version": issue["producer"]["framework_version"],
            "platform": issue["producer"]["platform"],
        },
        "entries": manifest_entries,
    }
    output = args.output.expanduser().resolve()
    if output.suffix != ".ltpm-feedback":
        raise FeedbackError("output filename must end with .ltpm-feedback")
    if output.exists():
        raise FeedbackError(f"output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=output.parent, prefix=".ltpm-feedback-", delete=False) as temporary:
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
        temporary_path.replace(output)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()
    return {
        "feedback_id": issue["feedback_id"],
        "path": str(output),
        "package_sha256": sha256_file(output),
        "uploaded": False,
        "warning": "Integrity is verified; authenticity, truth, acceptance, and submission are not.",
    }


def read_verified(path: Path) -> tuple[dict, dict, dict, dict[str, bytes]]:
    path = path.expanduser().resolve()
    if not path.is_file() or path.suffix != ".ltpm-feedback":
        raise FeedbackError(f"feedback package not found or has the wrong extension: {path}")
    try:
        archive = zipfile.ZipFile(path, "r")
    except (OSError, zipfile.BadZipFile) as exc:
        raise FeedbackError(f"cannot open feedback package: {exc}") from exc
    with archive:
        infos = archive.infolist()
        if len(infos) > MAX_ENTRIES + 1:
            raise FeedbackError("archive contains too many members")
        names = [safe_member(info.filename) for info in infos]
        if len(names) != len(set(names)):
            raise FeedbackError("archive contains duplicate members")
        for info in infos:
            mode = (info.external_attr >> 16) & 0o170000
            if mode == stat.S_IFLNK or info.is_dir():
                raise FeedbackError(f"archive contains a symlink or directory member: {info.filename}")
            if info.file_size > MAX_ENTRY_BYTES:
                raise FeedbackError(f"archive member exceeds size limit: {info.filename}")
        if "manifest.json" not in names:
            raise FeedbackError("manifest.json is missing")
        try:
            manifest = json.loads(archive.read("manifest.json"))
        except (json.JSONDecodeError, UnicodeDecodeError, KeyError) as exc:
            raise FeedbackError(f"invalid manifest: {exc}") from exc
        expected_manifest_fields = {"format", "schema_version", "feedback_id", "created_at", "producer", "entries"}
        require_object(manifest, "manifest", expected_manifest_fields)
        if manifest["format"] != FORMAT or manifest["schema_version"] != SCHEMA_VERSION:
            raise FeedbackError("unsupported feedback package format")
        manifest_feedback_id = require_string(manifest["feedback_id"], "manifest.feedback_id")
        if re.fullmatch(r"fb-[A-Za-z0-9][A-Za-z0-9._-]{5,127}", manifest_feedback_id) is None:
            raise FeedbackError("manifest.feedback_id is unsafe")
        validate_datetime(manifest["created_at"], "manifest.created_at")
        producer = require_object(manifest["producer"], "manifest.producer", {"framework_version", "platform"})
        require_string(producer["framework_version"], "manifest.producer.framework_version")
        require_string(producer["platform"], "manifest.producer.platform")
        entries = manifest["entries"]
        if not isinstance(entries, list) or len(entries) > MAX_ENTRIES:
            raise FeedbackError("manifest entries are invalid")
        payload: dict[str, bytes] = {}
        expected = {"manifest.json"}
        total = 0
        for entry in entries:
            entry = require_object(entry, "manifest entry", {"path", "size", "sha256"})
            member = safe_member(entry["path"])
            size = entry["size"]
            digest = entry["sha256"]
            if member in expected:
                raise FeedbackError(f"duplicate manifest member: {member}")
            if not isinstance(size, int) or isinstance(size, bool) or size < 0 or size > MAX_ENTRY_BYTES:
                raise FeedbackError(f"invalid manifest size: {member}")
            if not isinstance(digest, str) or len(digest) != 64:
                raise FeedbackError(f"invalid manifest hash: {member}")
            total += size
            if total > MAX_TOTAL_BYTES:
                raise FeedbackError("feedback package exceeds total-size limit")
            try:
                info = archive.getinfo(member)
                data = archive.read(member)
            except KeyError as exc:
                raise FeedbackError(f"manifest member is missing: {member}") from exc
            if info.file_size != size or len(data) != size or sha256_bytes(data) != digest:
                raise FeedbackError(f"integrity check failed: {member}")
            expected.add(member)
            payload[member] = data
        if set(names) != expected:
            raise FeedbackError("archive and manifest member sets do not match")
        if "issue.json" not in payload or "redaction-report.json" not in payload:
            raise FeedbackError("issue.json or redaction-report.json is missing")
        try:
            issue = validate_issue(json.loads(payload["issue.json"]))
            redaction = validate_redaction(json.loads(payload["redaction-report.json"]), issue["feedback_id"])
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise FeedbackError(f"invalid feedback JSON: {exc}") from exc
        attachments = {name for name in payload if name.startswith("attachments/")}
        approved = set(issue["consent"]["export"]["approved_attachments"])
        if attachments != approved or manifest_feedback_id != issue["feedback_id"]:
            raise FeedbackError("manifest, consent, and payload identities do not match")
        return manifest, issue, redaction, payload


def verify_package(path: Path) -> dict:
    manifest, issue, _, payload = read_verified(path)
    return {
        "verified": True,
        "feedback_id": manifest["feedback_id"],
        "framework_version": manifest["producer"]["framework_version"],
        "entry_count": len(payload),
        "retention": issue["consent"]["developer_use"]["retention"],
        "package_sha256": sha256_file(path.expanduser().resolve()),
        "warning": "Integrity is verified; authenticity, truth, acceptance, and root cause are not.",
    }


def inspect_package(path: Path) -> dict:
    manifest, issue, redaction, payload = read_verified(path)
    return {
        "feedback_id": manifest["feedback_id"],
        "title": issue["problem"]["title"],
        "kind": issue["problem"]["kind"],
        "classification_is_provisional": True,
        "classification_proposal": issue["classification_proposal"],
        "impact": issue["problem"]["impact"],
        "blocking": issue["problem"]["blocking"],
        "coverage": {
            "inspected": issue["evidence"]["inspected_scope"],
            "uninspected": issue["evidence"]["uninspected_scope"],
            "gaps": issue["evidence"]["known_gaps"],
        },
        "privacy": {
            "sensitivity": issue["privacy"]["sensitivity"],
            "redactions": issue["privacy"]["redactions"],
            "residual_risks": redaction["residual_risks"],
        },
        "consent": issue["consent"],
        "attachments": sorted(name for name in payload if name.startswith("attachments/")),
        "automatic_upload": False,
    }


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    export = commands.add_parser("export", help="Create one approved .ltpm-feedback package")
    export.add_argument("--issue", type=Path, required=True)
    export.add_argument("--redaction-report", type=Path, required=True)
    export.add_argument("--output", type=Path, required=True)
    export.add_argument("--attachment", action="append", default=[], metavar="SOURCE=attachments/RELATIVE_PATH")
    verify = commands.add_parser("verify", help="Verify package structure and integrity")
    verify.add_argument("package", type=Path)
    inspect = commands.add_parser("inspect", help="Show a safe summary without extracting attachments")
    inspect.add_argument("package", type=Path)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "export":
            result = export_package(args)
        elif args.command == "verify":
            result = verify_package(args.package)
        else:
            result = inspect_package(args.package)
    except FeedbackError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
