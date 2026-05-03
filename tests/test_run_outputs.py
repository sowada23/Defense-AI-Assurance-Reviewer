from __future__ import annotations

import argparse
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from compare_reviewers import build_run_metadata, create_run_dir, sanitize_run_component


class RunOutputTests(unittest.TestCase):
    def test_sanitize_run_component(self) -> None:
        self.assertEqual(sanitize_run_component("gpt-4o mini / test"), "gpt-4o-mini-test")
        self.assertEqual(sanitize_run_component("..."), "unknown")

    def test_create_run_dir_with_unique_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            first = create_run_dir(output_dir, "mock", "gpt-4o-mini", "same-run")
            second = create_run_dir(output_dir, "mock", "gpt-4o-mini", "same-run")

            self.assertTrue(first.exists())
            self.assertTrue(second.exists())
            self.assertEqual(first.parent, output_dir)
            self.assertEqual(second.parent, output_dir)
            self.assertEqual(first.name, "same-run")
            self.assertEqual(second.name, "same-run-2")

    def test_build_run_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            run_dir = create_run_dir(output_dir, "mock", "gpt-4o-mini", "metadata-run")
            args = argparse.Namespace(
                output_dir=str(output_dir),
                model="gpt-4o-mini",
                temperature=0.1,
                max_retries=2,
                retry_temperature=None,
            )
            labels = [{"document_id": "doc_a"}, {"document_id": "doc_b"}]
            started_at = datetime(2026, 5, 2, 12, 0, 0, tzinfo=UTC)
            finished_at = datetime(2026, 5, 2, 12, 0, 3, tzinfo=UTC)
            output_files = {
                "defense_reviews": run_dir / "defense_reviews.json",
                "ml_baseline_reviews": run_dir / "ml_baseline_reviews.json",
                "comparison_summary": run_dir / "comparison_summary.json",
                "run_metadata": run_dir / "run_metadata.json",
            }

            metadata = build_run_metadata(
                args=args,
                provider="mock",
                labels=labels,
                run_dir=run_dir,
                output_files=output_files,
                started_at=started_at,
                finished_at=finished_at,
            )

            self.assertEqual(metadata["run_id"], "metadata-run")
            self.assertEqual(metadata["status"], "success")
            self.assertEqual(metadata["provider"], "mock")
            self.assertEqual(metadata["document_count"], 2)
            self.assertEqual(metadata["duration_seconds"], 3.0)
            self.assertIn("run_metadata", metadata["output_files"])
            self.assertIn("comparison_summary", metadata["legacy_output_files"])


if __name__ == "__main__":
    unittest.main()
