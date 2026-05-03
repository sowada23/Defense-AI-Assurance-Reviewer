#!/usr/bin/env python3
"""Compare ML-style and defense-specific reviewers over the sample dataset."""

from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from review_defense_doc import DEFAULT_GEMINI_MODEL, DEFAULT_OLLAMA_MODEL, DEFAULT_OPENAI_MODEL, DEFAULT_PROVIDER, review_document


PROJECT_DIR = Path(__file__).resolve().parent
SAMPLE_DOCS_DIR = PROJECT_DIR / "sample_docs"
METADATA_PATH = PROJECT_DIR / "metadata" / "sample_doc_labels.json"
OUTPUTS_DIR = PROJECT_DIR / "outputs"


def load_metadata() -> list[dict[str, Any]]:
    return json.loads(METADATA_PATH.read_text(encoding="utf-8"))


def issue_found(review: dict[str, Any], issue: str) -> bool:
    haystack = " ".join(
        [
            " ".join(str(x) for x in review.get("Weaknesses", [])),
            " ".join(str(x) for x in review.get("Recommended Improvements", [])),
            " ".join(str(x) for x in review.get("Questions", [])),
        ]
    ).lower()
    tokens = [token for token in issue.lower().replace("-", " ").split() if len(token) > 4]
    return any(token in haystack for token in tokens)


def summarize(
    labels: list[dict[str, Any]],
    defense_reviews: dict[str, dict[str, Any]],
    ml_reviews: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    rows = []
    for item in labels:
        document_id = item["document_id"]
        known_issues = item.get("known_issues", [])
        defense = defense_reviews[document_id]
        ml = ml_reviews[document_id]
        found = sum(1 for issue in known_issues if issue_found(defense, issue))
        rows.append(
            {
                "document_id": document_id,
                "expected_quality": item["expected_quality"],
                "ml_overall": ml.get("Overall"),
                "defense_overall": defense.get("Overall"),
                "defense_decision": defense.get("Decision"),
                "known_issues_found": found,
                "known_issues_total": len(known_issues),
            }
        )

    quality_order = {"weak": 1, "medium": 2, "strong": 3}
    sorted_rows = sorted(rows, key=lambda row: quality_order[row["expected_quality"]])
    score_alignment = [
        {
            "expected_quality": row["expected_quality"],
            "document_id": row["document_id"],
            "defense_overall": row["defense_overall"],
        }
        for row in sorted_rows
    ]
    return {
        "research_question": (
            "Can an AI Scientist-style Automated Reviewer be repurposed from ML paper "
            "review into a structured assurance reviewer for Japanese defense AI "
            "governance documents?"
        ),
        "rows": rows,
        "score_alignment": score_alignment,
        "notes": [
            "The ML baseline is intentionally mismatched to assurance documents.",
            "The defense reviewer is expected to produce more domain-relevant weaknesses and recommendations.",
            "Mock mode is deterministic and intended for local testing before real LLM runs."
        ],
    }


def json_write(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def sanitize_run_component(value: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip())
    sanitized = sanitized.strip("-_.")
    return sanitized or "unknown"


def create_run_dir(outputs_dir: Path, provider: str, model: str, run_name: str | None) -> Path:
    outputs_dir.mkdir(parents=True, exist_ok=True)
    if run_name:
        base_name = sanitize_run_component(run_name)
    else:
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        base_name = "_".join(
            [
                timestamp,
                sanitize_run_component(provider),
                sanitize_run_component(model),
            ]
        )

    run_dir = outputs_dir / base_name
    suffix = 2
    while run_dir.exists():
        run_dir = outputs_dir / f"{base_name}-{suffix}"
        suffix += 1
    run_dir.mkdir()
    return run_dir


def relative_to_project(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_DIR))
    except ValueError:
        return str(path)


def build_run_metadata(
    *,
    args: argparse.Namespace,
    provider: str,
    labels: list[dict[str, Any]],
    run_dir: Path,
    output_files: dict[str, Path],
    started_at: datetime,
    finished_at: datetime,
) -> dict[str, Any]:
    return {
        "run_id": run_dir.name,
        "status": "success",
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "duration_seconds": round((finished_at - started_at).total_seconds(), 3),
        "provider": provider,
        "model": args.model,
        "temperature": args.temperature,
        "max_retries": args.max_retries,
        "retry_temperature": args.retry_temperature,
        "document_count": len(labels),
        "document_ids": [item["document_id"] for item in labels],
        "output_files": {name: relative_to_project(path) for name, path in output_files.items()},
        "legacy_output_files": {
            "defense_reviews": relative_to_project(Path(args.output_dir) / "defense_reviews.json"),
            "ml_baseline_reviews": relative_to_project(Path(args.output_dir) / "ml_baseline_reviews.json"),
            "comparison_summary": relative_to_project(Path(args.output_dir) / "comparison_summary.json"),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run reviewer comparison over sample documents.")
    parser.add_argument("--provider", choices=["mock", "openai", "gemini", "ollama"], default=DEFAULT_PROVIDER)
    parser.add_argument("--model", help="Model name for OpenAI, Gemini, or Ollama mode.")
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--max-retries", type=int, default=2)
    parser.add_argument("--retry-temperature", type=float)
    parser.add_argument("--output-dir", default=str(OUTPUTS_DIR))
    parser.add_argument("--run-name", help="Optional explicit name for this run folder.")
    parser.add_argument("--mock", action="store_true", help="Alias for --provider mock.")
    args = parser.parse_args()

    started_at = datetime.now(UTC)
    provider = "mock" if args.mock else args.provider
    if args.model is None:
        if provider == "gemini":
            args.model = DEFAULT_GEMINI_MODEL
        elif provider == "ollama":
            args.model = DEFAULT_OLLAMA_MODEL
        else:
            args.model = DEFAULT_OPENAI_MODEL
    output_dir = Path(args.output_dir)
    run_dir = create_run_dir(output_dir, provider, args.model, args.run_name)
    labels = load_metadata()
    defense_reviews: dict[str, dict[str, Any]] = {}
    ml_reviews: dict[str, dict[str, Any]] = {}

    for item in labels:
        document_id = item["document_id"]
        path = SAMPLE_DOCS_DIR / f"{document_id}.txt"
        defense_reviews[document_id] = review_document(
            path,
            rubric="defense",
            provider=provider,
            model=args.model,
            temperature=args.temperature,
            max_retries=args.max_retries,
            retry_temperature=args.retry_temperature,
        )
        ml_reviews[document_id] = review_document(
            path,
            rubric="ml_baseline",
            provider=provider,
            model=args.model,
            temperature=args.temperature,
            max_retries=args.max_retries,
            retry_temperature=args.retry_temperature,
        )

    summary = summarize(labels, defense_reviews, ml_reviews)
    run_output_files = {
        "defense_reviews": run_dir / "defense_reviews.json",
        "ml_baseline_reviews": run_dir / "ml_baseline_reviews.json",
        "comparison_summary": run_dir / "comparison_summary.json",
        "run_metadata": run_dir / "run_metadata.json",
    }

    json_write(run_output_files["defense_reviews"], defense_reviews)
    json_write(run_output_files["ml_baseline_reviews"], ml_reviews)
    json_write(run_output_files["comparison_summary"], summary)

    output_dir.mkdir(parents=True, exist_ok=True)
    json_write(output_dir / "defense_reviews.json", defense_reviews)
    json_write(output_dir / "ml_baseline_reviews.json", ml_reviews)
    json_write(output_dir / "comparison_summary.json", summary)

    finished_at = datetime.now(UTC)
    metadata = build_run_metadata(
        args=args,
        provider=provider,
        labels=labels,
        run_dir=run_dir,
        output_files=run_output_files,
        started_at=started_at,
        finished_at=finished_at,
    )
    json_write(run_output_files["run_metadata"], metadata)

    print(json.dumps(summary, indent=2))
    print(f"\nRun folder: {run_dir}")


if __name__ == "__main__":
    main()
