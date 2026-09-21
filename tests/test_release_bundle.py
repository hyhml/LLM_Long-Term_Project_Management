from __future__ import annotations

import json
import shutil
from pathlib import Path

from support import ROOT, ProjectTestCase, read_json, run


BUILDER = ROOT / "development" / "release" / "build_runtime.py"
ALLOWLIST = ROOT / "development" / "release" / "runtime-allowlist.json"


class RuntimeReleaseBundleTest(ProjectTestCase):
    """Feature contract: user releases contain exactly the declared runtime files."""

    def build(self, output: Path, archive: Path | None = None, source: Path = ROOT, expected: int = 0):
        arguments: list[object] = [
            BUILDER,
            "--source-root",
            source,
            "--release-version",
            "0.5.0",
            "--output-dir",
            output,
        ]
        if archive is not None:
            arguments.extend(["--archive", archive])
        return run(*arguments, expected=expected)

    def copy_source(self, name: str) -> Path:
        destination = self.temp / name
        shutil.copytree(
            ROOT,
            destination,
            ignore=shutil.ignore_patterns(".git", "private", "__pycache__", "*.pyc"),
        )
        return destination

    def test_bundle_matches_allowlist_and_generates_a_valid_child_skill(self) -> None:
        runtime = self.temp / "runtime"
        archive = self.temp / "runtime.zip"
        report = json.loads(self.build(runtime, archive).stdout)
        allowlist = read_json(ALLOWLIST)["runtime_files"]
        produced = {
            path.relative_to(runtime).as_posix()
            for path in runtime.rglob("*")
            if path.is_file()
        }
        self.assertEqual(produced, set(allowlist))
        self.assertEqual(report["file_count"], len(allowlist))
        self.assertEqual(report["release_version"], "0.5.0")
        self.assertEqual(read_json(runtime / "references" / "framework-map.json")["framework_version"], "0.5.0")
        self.assertNotEqual(
            read_json(ROOT / "references" / "framework-map.json")["framework_version"], "0.5.0"
        )
        for excluded in ("AGENTS.md", "development", "tests", "private"):
            self.assertFalse((runtime / excluded).exists())
        self.assertTrue(archive.is_file())
        self.assertEqual(len(report["archive_sha256"]), 64)

        project = self.temp / "runtime-project"
        project.mkdir()
        created = json.loads(
            run(
                runtime / "scripts" / "init_project.py",
                "--project-root",
                project,
                "--skill-name",
                "runtime-validation",
                "--project-name",
                "Runtime validation",
                "--goal",
                "Validate the built runtime",
                "--scope",
                "Release bundle",
                "--evidence-standard",
                "Validator output",
                "--criterion",
                "Generated child validates",
                "--high-task",
                "Validate child",
            ).stdout
        )
        child = Path(created["created"])
        validation = json.loads(run(runtime / "scripts" / "validate_project.py", child).stdout)
        self.assertTrue(validation["valid"])
        instance = read_json(child / "framework" / "instance.json")
        self.assertEqual(instance["last_adapter_update_with"], "0.5.0")
        self.assertFalse((child / "framework" / "conditional").exists())
        self.assertTrue((child / "project-instructions.md").is_file())

    def test_unclassified_or_missing_source_file_blocks_release(self) -> None:
        source = self.copy_source("source-unclassified")
        (source / "unexpected-root-file.txt").write_text("unclassified\n", encoding="utf-8")
        rejected = self.build(self.temp / "rejected-unclassified", source=source, expected=1)
        self.assertIn("unclassified source files", rejected.stderr)
        self.assertFalse((self.temp / "rejected-unclassified").exists())

        source = self.copy_source("source-missing")
        (source / "SKILL.md").unlink()
        rejected = self.build(self.temp / "rejected-missing", source=source, expected=1)
        self.assertIn("runtime allowlist files are missing", rejected.stderr)
        self.assertFalse((self.temp / "rejected-missing").exists())

    def test_archive_is_reproducible_for_the_same_runtime_source(self) -> None:
        first_archive = self.temp / "first.zip"
        second_archive = self.temp / "second.zip"
        first = json.loads(self.build(self.temp / "first-runtime", first_archive).stdout)
        second = json.loads(self.build(self.temp / "second-runtime", second_archive).stdout)
        self.assertEqual(first["tree_sha256"], second["tree_sha256"])
        self.assertEqual(first["archive_sha256"], second["archive_sha256"])
        self.assertEqual(first_archive.read_bytes(), second_archive.read_bytes())
