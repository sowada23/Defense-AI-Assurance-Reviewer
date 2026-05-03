# Defense AI Assurance Reviewer

## Summary

This project adapts the Automated Reviewer concept from The AI Scientist to fictional, non-operational Japanese defense/government AI assurance documents. The proof of concept reviews safety cases, model evaluation reports, and oversight plans using a domain-specific assurance rubric.

## Motivation

AI assurance documents are often reviewed for governance, safety, human oversight, privacy, and deployment readiness. A reviewer designed for ML papers is poorly matched to that task. This project tests whether a structured LLM reviewer can be repurposed for a practical assurance-review setting.

## Relationship To The AI Scientist Automated Reviewer

The project mirrors the AI Scientist reviewer pattern:

- Build a review prompt.
- Ask for a structured thought and JSON review.
- Parse the JSON response.
- Optionally compare multiple rubrics or review configurations.

Unlike the original ML-paper reviewer, this project uses a defense assurance rubric rather than a NeurIPS-style review form.

## Dataset

The dataset contains nine fictional assurance documents:

- Three logistics safety cases.
- Three non-combat vehicle maintenance evaluation reports.
- Three disaster-response oversight plans.

Each group contains strong, medium, and weak examples. Labels and known issues are stored in `metadata/sample_doc_labels.json`.

## Rubric

The defense rubric scores mission clarity, human oversight, data governance, privacy and security, safety and reliability, robustness testing, failure mode coverage, legal and policy alignment, deployment readiness, operational risk, overall quality, confidence, and readiness decision.

## Method

Run `compare_reviewers.py` to review each document with:

- A defense assurance reviewer.
- An ML-paper-style baseline reviewer.

The mock mode is deterministic and requires no API key. It is included so the workflow can be tested locally. A real LLM can be used with the `--provider openai` option.

## Experiment

Research question:

Can an AI Scientist-style Automated Reviewer be repurposed from ML paper review into a structured assurance reviewer for Japanese defense AI governance documents?

Procedure:

1. Review all nine documents with both rubrics.
2. Save structured JSON reviews.
3. Compare score ordering and known-issue detection.
4. Inspect whether recommendations are relevant to assurance review rather than ML-paper review.

## Results

Run this command to generate results:

```bash
cd /Users/sora/AIResearcher/defense_ai_assurance_reviewer
python3 compare_reviewers.py --mock
```

The generated result files are:

```text
outputs/defense_reviews.json
outputs/ml_baseline_reviews.json
outputs/comparison_summary.json
```

## Limitations

- The included dataset is synthetic and small.
- Mock mode is heuristic and not a substitute for a real LLM evaluation.
- Real reviewer quality depends on the selected model and prompt reliability.
- The system is a documentation review assistant, not a compliance authority.

## Safety Boundary

The project uses fictional, non-sensitive documents only. It avoids operational military advice, weapons, targeting, surveillance tasking, cyber operations, and battlefield planning.

## Future Work

- Add expert-written labels for issue detection.
- Add more document types, such as procurement checklists and model cards.
- Compare multiple LLMs and rubric variants.
- Add reflection or ensemble review similar to the original AI Scientist reviewer.
- Add a document-improvement loop and measure before/after scores.

## Citations

- The AI Scientist Nature paper: https://www.nature.com/articles/s41586-026-10265-5
- Sakana AI blog: https://sakana.ai/ai-scientist-nature
- Local AI Scientist repository: `/Users/sora/AI-Scientist`

