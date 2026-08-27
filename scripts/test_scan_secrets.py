from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from scan_secrets import is_scannable_path, run_scan, scan_files


class SecretScanTests(unittest.TestCase):
    def test_detects_common_credentials_without_returning_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source_file = Path(directory) / "config.py"
            openai_candidate = "sk-" + ("x" * 32)
            github_candidate = "ghp_" + ("y" * 36)
            source_file.write_text(
                f"openai = '{openai_candidate}'\ngithub = '{github_candidate}'\n",
                encoding="utf-8",
            )

            findings = scan_files([source_file])

        assert {(finding.path.name, finding.rule_name) for finding in findings} == {
            ("config.py", "openai-api-key"),
            ("config.py", "github-token"),
        }

    def test_ignores_local_environment_files_and_scans_private_key_markers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            local_environment = root / ".env.local"
            key_file = root / "credentials.pem"
            local_environment.write_text("OPENAI_API_KEY=not-scanned", encoding="utf-8")
            key_file.write_text(
                "-----BEGIN " + "PRIVATE KEY-----\nplaceholder\n",
                encoding="utf-8",
            )

            findings = scan_files([local_environment, key_file])

        assert is_scannable_path(local_environment) is False
        assert [(finding.path.name, finding.rule_name) for finding in findings] == [
            ("credentials.pem", "private-key"),
        ]

    def test_failure_output_exposes_only_path_and_rule_name(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source_file = Path(directory) / "settings.py"
            candidate = "AKIA" + ("Z" * 16)
            source_file.write_text(f"access_key = '{candidate}'\n", encoding="utf-8")
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = run_scan([source_file])

        assert exit_code == 1
        assert "settings.py: aws-access-key" in output.getvalue()
        assert candidate not in output.getvalue()


if __name__ == "__main__":
    unittest.main()
