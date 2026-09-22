#!/usr/bin/env python3
"""Verify, quarantine, triage, and resolve external framework feedback."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from feedback import FeedbackError, inspect_package, read_verified, sha256_file, verify_package  # noqa: E402


TRIAGE_SCHEMA = "ltpm-feedback-triage/v1"
RESOLUTION_SCHEMA = "ltpm-feedback-resolution/v1"


class IntakeError(ValueError):
    pass


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def write_new_json(path: Path, value: object) -> None:
    path = path.expanduser().resolve()
    if path.exists():
        raise IntakeError(f"output already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def require_external(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    if resolved == ROOT or resolved.is_relative_to(ROOT):
        raise IntakeError("real feedback must be quarantined outside the framework repository")
    return resolved


def quarantine(package: Path, inbox: Path) -> dict:
    manifest, issue, _, _ = read_verified(package)
    inbox = require_external(inbox)
    destination = inbox / manifest["feedback_id"]
    if destination.exists():
        raise IntakeError(f"feedback quarantine already exists: {destination}")
    inbox.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=inbox, prefix=".feedback-intake-") as temporary_text:
        temporary = Path(temporary_text)
        stored = temporary / "original.ltpm-feedback"
        shutil.copyfile(package.expanduser().resolve(), stored)
        intake = {
            "schema": "ltpm-feedback-intake/v1",
            "feedback_id": manifest["feedback_id"],
            "received_at": now(),
            "status": "received-untrusted",
            "package_sha256": sha256_file(stored),
            "consent": issue["consent"]["developer_use"],
            "classification_is_provisional": True,
            "attachments_executed": False,
            "repository_storage_allowed": False,
        }
        (temporary / "intake.json").write_text(
            json.dumps(intake, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        temporary.replace(destination)
    return {**intake, "quarantine": str(destination)}


def triage_template(package: Path, output: Path) -> dict:
    _, issue, _, _ = read_verified(package)
    output = require_external(output)
    proposal = {
        "schema": TRIAGE_SCHEMA,
        "feedback_id": issue["feedback_id"],
        "created_at": now(),
        "user_classification": issue["classification_proposal"],
        "developer_classification": {
            "category": None,
            "reasoning": None,
            "remediation_scope": None,
        },
        "decisions": {
            "disposition": "pending",
            "retain_original": "pending",
            "request_more_information": "pending",
            "derive_synthetic_test": "pending",
        },
        "constraints": {
            "retention_authorized": issue["consent"]["developer_use"]["retention"],
            "synthetic_derivative_authorized": issue["consent"]["developer_use"]["allow_synthetic_derivative"],
            "real_case_repository_storage_allowed": False,
        },
        "proposed_invariant": None,
        "minimal_synthetic_reproduction": None,
        "notes": [],
    }
    write_new_json(output, proposal)
    return {"feedback_id": issue["feedback_id"], "triage_template": str(output.expanduser().resolve())}


def validated_triage(path: Path, issue: dict) -> dict:
    path = require_external(path)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IntakeError(f"cannot read triage decision: {exc}") from exc
    required = {
        "schema", "feedback_id", "created_at", "user_classification", "developer_classification",
        "decisions", "constraints", "proposed_invariant", "minimal_synthetic_reproduction", "notes",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise IntakeError("triage decision does not match ltpm-feedback-triage/v1")
    if value["schema"] != TRIAGE_SCHEMA or value["feedback_id"] != issue["feedback_id"]:
        raise IntakeError("triage schema or feedback_id does not match")
    classification = value["developer_classification"]
    if not isinstance(classification, dict) or set(classification) != {"category", "reasoning", "remediation_scope"}:
        raise IntakeError("developer classification is invalid")
    if any(not isinstance(classification[key], str) or not classification[key] for key in classification):
        raise IntakeError("developer classification must be completed before resolution")
    decisions = value["decisions"]
    if not isinstance(decisions, dict) or set(decisions) != {
        "disposition", "retain_original", "request_more_information", "derive_synthetic_test"
    }:
        raise IntakeError("triage decisions are invalid")
    if decisions["disposition"] not in {
        "accepted-framework-defect", "accepted-feature-request", "project-data", "environment",
        "usage-documentation", "external-tool", "duplicate", "non-reproducible", "needs-information", "rejected",
    }:
        raise IntakeError("triage disposition is pending or unsupported")
    if decisions["retain_original"] not in {"delete-after-triage", "delete-after-resolution", "retain-long-term"}:
        raise IntakeError("triage retention decision is pending or unsupported")
    if not isinstance(decisions["request_more_information"], bool) or not isinstance(decisions["derive_synthetic_test"], bool):
        raise IntakeError("triage information and test decisions must be boolean")
    authorization = issue["consent"]["developer_use"]
    if decisions["retain_original"] == "retain-long-term" and authorization["retention"] != "long-term-regression-candidate":
        raise IntakeError("long-term retention exceeds the user's authorization")
    if authorization["retention"] == "one-shot" and decisions["retain_original"] != "delete-after-triage":
        raise IntakeError("one-shot consent requires deletion after triage")
    if decisions["derive_synthetic_test"]:
        if not authorization["allow_synthetic_derivative"]:
            raise IntakeError("synthetic derivation was not authorized")
        if not isinstance(value["proposed_invariant"], str) or not value["proposed_invariant"]:
            raise IntakeError("synthetic derivation requires a proposed invariant")
        if not isinstance(value["minimal_synthetic_reproduction"], str) or not value["minimal_synthetic_reproduction"]:
            raise IntakeError("synthetic derivation requires a minimal reproduction proposal")
    if not isinstance(value["notes"], list) or any(not isinstance(item, str) for item in value["notes"]):
        raise IntakeError("triage notes must be a list of strings")
    return value


def resolution(args: argparse.Namespace) -> dict:
    manifest, issue, _, _ = read_verified(args.package)
    triage = validated_triage(args.triage, issue)
    args.output = require_external(args.output)
    value = {
        "schema": RESOLUTION_SCHEMA,
        "feedback_id": manifest["feedback_id"],
        "created_at": now(),
        "result": args.result,
        "final_classification": triage["developer_classification"],
        "affected_versions": args.affected_version,
        "fixed_in_version": args.fixed_in_version,
        "fix_reference": args.fix_reference,
        "child_action": args.child_action,
        "notes": args.note,
        "triage_disposition": triage["decisions"]["disposition"],
        "original_retention_decision": triage["decisions"]["retain_original"],
        "synthetic_test_proposed": triage["decisions"]["derive_synthetic_test"],
        "automatic_project_mutation": False,
    }
    write_new_json(args.output, value)
    return {"feedback_id": manifest["feedback_id"], "resolution": str(args.output.expanduser().resolve())}


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    verify = commands.add_parser("verify", help="Verify without accepting or extracting")
    verify.add_argument("package", type=Path)
    inspect = commands.add_parser("inspect", help="Show the safe feedback summary")
    inspect.add_argument("package", type=Path)
    quarantine_command = commands.add_parser("quarantine", help="Copy verified feedback to an external inert inbox")
    quarantine_command.add_argument("package", type=Path)
    quarantine_command.add_argument("--inbox", type=Path, required=True)
    triage = commands.add_parser("triage-template", help="Create an itemized external triage proposal")
    triage.add_argument("package", type=Path)
    triage.add_argument("--output", type=Path, required=True)
    resolved = commands.add_parser("resolution", help="Create a non-mutating resolution receipt")
    resolved.add_argument("package", type=Path)
    resolved.add_argument("--triage", type=Path, required=True)
    resolved.add_argument("--output", type=Path, required=True)
    resolved.add_argument("--result", required=True, choices=["accepted", "rejected", "duplicate", "needs-information", "resolved-outside-framework"])
    resolved.add_argument("--affected-version", action="append", default=[])
    resolved.add_argument("--fixed-in-version")
    resolved.add_argument("--fix-reference")
    resolved.add_argument("--child-action", required=True, choices=["none", "refresh-runtime", "upgrade-adapter", "migrate-project-data", "unknown"])
    resolved.add_argument("--note", action="append", default=[])
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "verify":
            result = verify_package(args.package)
        elif args.command == "inspect":
            result = inspect_package(args.package)
        elif args.command == "quarantine":
            result = quarantine(args.package, args.inbox)
        elif args.command == "triage-template":
            result = triage_template(args.package, args.output)
        else:
            result = resolution(args)
    except (FeedbackError, IntakeError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
