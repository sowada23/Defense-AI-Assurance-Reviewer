# Defense AI Assurance Reviewer

Defense AI Assurance Reviewer is a proof-of-concept project that adapts the Automated Reviewer pattern from The AI Scientist from ML-paper review to fictional, non-operational Japanese defense/government AI assurance documents.

The project reviews documentation quality rather than operational behavior. It evaluates governance, safety, human oversight, privacy, security, risk controls, evaluation evidence, and deployment readiness for support-domain AI systems.

This is not a tactical or operational military tool. It does not provide weapons, targeting, surveillance, cyber, battlefield, or mission-execution advice. All included documents are fictional, non-sensitive examples.

## Research Question

Can an AI Scientist-style Automated Reviewer be repurposed from ML paper review into a structured assurance reviewer for Japanese defense AI governance documents?

## Why This Project Exists

The AI Scientist includes an Automated Reviewer designed around ML research-paper assessment. That review style is useful for judging originality, soundness, clarity, and significance, but it is not well matched to assurance documents used in government or defense AI governance.

This project tests a small domain adaptation:

- Replace the ML-paper review form with a defense AI assurance rubric.
- Create a synthetic dataset of fictional assurance documents.
- Review the same documents with both the adapted defense rubric and an ML-paper-style baseline.
- Compare score ordering, known-issue detection, and domain relevance.

## Safety Boundary

Allowed fictional document topics include:

- Logistics prioritization
- Non-combat vehicle maintenance prediction
- Disaster-response coordination
- Internal document triage
- Supply-chain risk monitoring
- Training schedule optimization
- Administrative workload routing

Avoided topics include:

- Target selection
- Weapons use or weapons control
- Battlefield planning
- Surveillance tasking
- Cyber operations
- Evasion or attack instructions
- Real classified, sensitive, or operational material

The reviewer should only discuss assurance documentation, governance controls, responsible deployment, safety processes, oversight, privacy, security, and evaluation evidence.

## Project Layout

```text
defense_ai_assurance_reviewer/
├── .gitignore
├── .gitmodules
├── README.md
├── requirements.txt
├── review_defense_doc.py
├── review_schema.py
├── compare_reviewers.py
├── report.md
├── rubrics/
│   ├── defense_assurance_rubric.md
│   └── ml_paper_rubric_summary.md
├── sample_docs/
│   ├── English/
│   │   ├── strong_logistics_ai_safety_case.txt
│   │   ├── medium_logistics_ai_safety_case.txt
│   │   ├── weak_logistics_ai_safety_case.txt
│   │   ├── strong_maintenance_model_eval_report.txt
│   │   ├── medium_maintenance_model_eval_report.txt
│   │   ├── weak_maintenance_model_eval_report.txt
│   │   ├── strong_disaster_response_oversight_plan.txt
│   │   ├── medium_disaster_response_oversight_plan.txt
│   │   └── weak_disaster_response_oversight_plan.txt
│   └── Japanese/
│       ├── strong_logistics_ai_safety_case.txt
│       ├── medium_logistics_ai_safety_case.txt
│       ├── weak_logistics_ai_safety_case.txt
│       ├── strong_maintenance_model_eval_report.txt
│       ├── medium_maintenance_model_eval_report.txt
│       ├── weak_maintenance_model_eval_report.txt
│       ├── strong_disaster_response_oversight_plan.txt
│       ├── medium_disaster_response_oversight_plan.txt
│       └── weak_disaster_response_oversight_plan.txt
├── metadata/
│   ├── sample_doc_labels.json
│   └── sample_doc_labels_japanese.json
├── outputs/
│   ├── 20260504T151137Z_ollama_llama3.1-8b/
│   │   ├── defense_reviews.json
│   │   ├── ml_baseline_reviews.json
│   │   ├── comparison_summary.json
│   │   └── run_metadata.json
│   └── llama3.1-8b-test-run2-2/
│       ├── defense_reviews.json
│       ├── ml_baseline_reviews.json
│       ├── comparison_summary.json
│       └── run_metadata.json
├── tests/
│   ├── test_review_validation.py
│   └── test_run_outputs.py
└── external/
    └── AI-Scientist/
```

## What The Code Does

### `review_defense_doc.py`

Reviews one text document and prints a structured JSON review.

Main responsibilities:

- Loads a `.txt` assurance document.
- Loads either the defense assurance rubric or the ML baseline rubric.
- Builds a review prompt.
- Runs either local Ollama chat, deterministic mock review logic, OpenAI chat completions, or Gemini content generation.
- Extracts JSON from the model response.
- Validates the parsed review against the selected rubric schema.
- Retries malformed or schema-invalid real LLM responses with targeted repair prompts.
- Optionally writes the review to a JSON file.

Supported rubrics:

- `defense`: domain-specific assurance reviewer.
- `ml_baseline`: intentionally mismatched ML-paper-style baseline reviewer.

Supported providers:

- `mock`: deterministic local mode, no API key required.
- `ollama`: default local LLM mode using the Ollama API at `http://localhost:11434`.
- `openai`: real LLM mode using the `openai` Python package and `OPENAI_API_KEY`.
- `gemini`: real LLM mode using the `google-genai` Python package and `GEMINI_API_KEY`.

### `review_schema.py`

Defines and validates the expected JSON output schemas for both reviewer modes.

Validation checks include:

- Required fields for the selected rubric.
- List fields containing only strings.
- Boolean fields.
- Integer score fields and valid ranges.
- Valid `Decision` values.

The validator safely coerces integer-like floats, such as `7.0`, and valid rating strings, such as `7/10` or `3.5/4`, into the integer schema used internally. It does not coerce ambiguous values such as plain string scores like `"7"`.

### `compare_reviewers.py`

Runs both reviewers over every sample document and writes comparison outputs.

Main responsibilities:

- Loads document labels from `metadata/sample_doc_labels.json` for English or `metadata/sample_doc_labels_japanese.json` for Japanese.
- Reviews each sample document with the defense rubric.
- Reviews each sample document with the ML baseline rubric.
- Counts how many known issues are detected by the defense review text.
- Saves complete review JSON files, a comparison summary, and per-run metadata.
- Writes both top-level latest-result files and a dedicated `outputs/<run_id>/` folder for each comparison run.
- Supports `--en`, `--jp`, and `--language` so the same workflow can run against either corpus.

### `rubrics/defense_assurance_rubric.md`

Defines the adapted defense AI assurance review form. It asks the reviewer to score:

- Mission Clarity
- Human Oversight
- Data Governance
- Privacy and Security
- Safety and Reliability
- Robustness Testing
- Failure Mode Coverage
- Legal and Policy Alignment
- Deployment Readiness
- Operational Risk
- Overall
- Confidence
- Decision

Most category ratings use a 1 to 4 scale:

- `1`: poor, missing, or high risk
- `2`: partially addressed, incomplete, or weak evidence
- `3`: mostly adequate with manageable gaps
- `4`: strong, concrete, and well supported

`Overall` uses a 1 to 10 scale. `Confidence` uses a 1 to 5 scale. `Decision` is one of `Ready`, `Needs Revision`, or `Not Ready`.

### `rubrics/ml_paper_rubric_summary.md`

Defines the baseline ML-paper review framing. It scores originality, quality, clarity, significance, soundness, presentation, contribution, overall score, confidence, and accept/reject decision.

This baseline is included to show why a generic ML-paper rubric is not ideal for assurance documentation.

### `sample_docs/`

Contains two parallel sets of fictional assurance documents:

- 3 logistics AI safety cases
- 3 non-combat vehicle maintenance model evaluation reports
- 3 disaster-response oversight plans

`sample_docs/English/` contains the original nine English documents. `sample_docs/Japanese/` contains nine Japanese documents with matching document IDs and the same strong, medium, and weak structure. The Japanese documents are synthetic and focus on three non-combat Japanese defense support situations selected from the broader topic list: logistics prioritization, non-combat vehicle maintenance prediction, and disaster-response coordination.

### `metadata/`

Stores expected quality labels and known issues for each sample corpus. `sample_doc_labels.json` describes the English corpus, and `sample_doc_labels_japanese.json` describes the Japanese corpus.

Each record has this shape:

```json
{
  "document_id": "weak_logistics_ai_safety_case",
  "domain": "defense logistics",
  "document_type": "safety case",
  "expected_quality": "weak",
  "known_issues": [
    "unclear human oversight",
    "missing failure mode analysis",
    "weak evaluation evidence",
    "no privacy discussion"
  ]
}
```

### `outputs/`

Stores generated experiment outputs. The current local workspace includes two saved Ollama run folders:

- `outputs/llama3.1-8b-test-run2-2/`: English corpus run with `llama3.1:8b`.
- `outputs/20260504T151137Z_ollama_llama3.1-8b/`: Japanese corpus run with `llama3.1:8b`.

The `outputs/` directory is listed in `.gitignore`, so newly generated outputs are treated as local experiment artifacts unless they are explicitly force-added.

### `report.md`

Short project report covering the motivation, relationship to The AI Scientist, dataset, rubric, method, experiment, limitations, safety boundary, future work, and citations.

### `tests/`

Contains unit tests for schema validation, JSON repair behavior, language-specific metadata, output run folder creation, and run metadata construction.

### `requirements.txt`

Lists optional Python packages for cloud LLM providers and test/development workflows. Mock mode and Ollama mode only use the Python standard library from this repository.

### `external/AI-Scientist/`

Local reference copy of The AI Scientist project, configured as a git submodule in `.gitmodules`. This proof of concept does not need to modify those files. The relevant conceptual reference is the Automated Reviewer flow in:

```text
external/AI-Scientist/ai_scientist/perform_review.py
```

## Dataset Design

The synthetic dataset is designed to test whether the adapted reviewer can distinguish documentation quality and identify governance issues.

Each document is written as a fictional assurance artifact with sections such as:

```text
1. System Purpose
2. Intended Users
3. Data Sources
4. Model or System Evaluation
5. Human Oversight
6. Failure Modes
7. Risk Mitigations
8. Privacy and Security Considerations
9. Deployment Readiness
10. Known Limitations
```

Quality levels:

- `strong`: clear purpose, explicit oversight, concrete evaluation evidence, documented risks, privacy/security controls, deployment criteria, and limitations.
- `medium`: partially documented controls with gaps in testing, escalation, rollback, privacy, or metrics.
- `weak`: missing or vague oversight, weak evaluation, poor failure-mode coverage, incomplete data governance, and unclear readiness criteria.

The English and Japanese corpora share matching document IDs, so `compare_reviewers.py` can reuse the same comparison logic while switching document text and metadata with `--en`, `--jp`, or `--language`.

## Review Output Schema

Reviewer outputs are validated before they are returned or written. Mock mode is validated too; real LLM mode is parsed, validated, and retried when the response is malformed or schema-invalid.

A defense review returns JSON like:

```json
{
  "Summary": "",
  "Strengths": [],
  "Weaknesses": [],
  "Mission Clarity": "3/4",
  "Human Oversight": "3/4",
  "Data Governance": "3/4",
  "Privacy and Security": "3/4",
  "Safety and Reliability": "3/4",
  "Robustness Testing": "2/4",
  "Failure Mode Coverage": "3/4",
  "Legal and Policy Alignment": "3/4",
  "Deployment Readiness": "3/4",
  "Operational Risk": "3/4",
  "Questions": [],
  "Recommended Improvements": [],
  "Ethical Concerns": false,
  "Overall": "7/10",
  "Confidence": "4/5",
  "Decision": "Needs Revision"
}
```

All returned and saved rating fields use `value/max` strings so the scale is visible everywhere. The validator accepts model responses with plain integers, integer `value/max` strings, and half-point `value/max` strings such as `"3.5/4"`. Half-point ratings are rounded onto the required integer schema before being normalized to the display format.

The JSON parser also repairs common local-LLM formatting mistakes. It quotes unquoted rating fractions such as `"Overall": 7/10`, preserves decimal fractions such as `"Mission Clarity": 3.5/4`, and strips `//` line comments that models sometimes add inside JSON objects before validation.

Validation catches examples such as:

- Missing fields, such as no `Human Oversight`.
- Wrong types, such as `"Overall": "7"`.
- Out-of-range scores, such as `"Overall": 11` or `"Confidence": 9`.
- Mismatched rating denominators, such as `"Mission Clarity": "3/5"` when that field is scored out of 4.
- Invalid decisions, such as `"Decision": "Maybe Ready"`.

## Output Folder

After running the full comparison, `outputs/` should look like:

```text
outputs/
├── defense_reviews.json
├── ml_baseline_reviews.json
├── comparison_summary.json
└── 20260502T153000Z_mock_gpt-4o-mini/
    ├── defense_reviews.json
    ├── ml_baseline_reviews.json
    ├── comparison_summary.json
    └── run_metadata.json
```

The top-level JSON files are compatibility copies from the latest comparison run and are created by `compare_reviewers.py`. Each run folder directly under `outputs/` preserves one complete run with metadata. Because `outputs/` is gitignored, a fresh clone may not include top-level latest-result files until the comparison script is run.

The current local workspace includes these complete saved runs:

```text
outputs/
├── 20260504T151137Z_ollama_llama3.1-8b/
│   ├── defense_reviews.json
│   ├── ml_baseline_reviews.json
│   ├── comparison_summary.json
│   └── run_metadata.json
└── llama3.1-8b-test-run2-2/
    ├── defense_reviews.json
    ├── ml_baseline_reviews.json
    ├── comparison_summary.json
    └── run_metadata.json
```

### `outputs/defense_reviews.json`

Dictionary keyed by `document_id`. Each value is a full defense assurance review with category scores, weaknesses, questions, recommended improvements, ethical concern flag, overall score, confidence, and readiness decision.

### `outputs/ml_baseline_reviews.json`

Dictionary keyed by `document_id`. Each value is a baseline ML-paper-style review with fields such as originality, quality, clarity, significance, soundness, presentation, contribution, overall score, confidence, and accept/reject decision.

### `outputs/comparison_summary.json`

Summary object containing:

- The research question.
- One row per document.
- Expected quality label.
- ML baseline overall score.
- Defense reviewer overall score.
- Defense readiness decision.
- Known issues found by the defense review.
- Score-alignment view sorted by expected quality.
- Notes about the experiment.

Example row:

```json
{
  "document_id": "weak_maintenance_model_eval_report",
  "expected_quality": "weak",
  "ml_overall": "2/10",
  "defense_overall": "2/10",
  "defense_decision": "Needs Revision",
  "known_issues_found": 4,
  "known_issues_total": 4
}
```

### `outputs/<run_id>/run_metadata.json`

Run metadata records provider, model, temperature, retry settings, start/end time, duration, document IDs, and the generated file paths for that run.

Example metadata shape:

```json
{
  "run_id": "20260502T153000Z_mock_gpt-4o-mini",
  "status": "success",
  "started_at": "2026-05-02T15:30:00+00:00",
  "finished_at": "2026-05-02T15:30:03+00:00",
  "duration_seconds": 3.0,
  "provider": "mock",
  "model": "gpt-4o-mini",
  "temperature": 0.1,
  "max_retries": 2,
  "retry_temperature": null,
  "document_language": "en",
  "sample_docs_dir": "sample_docs/English",
  "metadata_file": "metadata/sample_doc_labels.json",
  "document_count": 9,
  "document_ids": [
    "strong_logistics_ai_safety_case",
    "medium_logistics_ai_safety_case"
  ],
  "output_files": {
    "defense_reviews": "outputs/20260502T153000Z_mock_gpt-4o-mini/defense_reviews.json",
    "ml_baseline_reviews": "outputs/20260502T153000Z_mock_gpt-4o-mini/ml_baseline_reviews.json",
    "comparison_summary": "outputs/20260502T153000Z_mock_gpt-4o-mini/comparison_summary.json",
    "run_metadata": "outputs/20260502T153000Z_mock_gpt-4o-mini/run_metadata.json"
  },
  "legacy_output_files": {
    "defense_reviews": "outputs/defense_reviews.json",
    "ml_baseline_reviews": "outputs/ml_baseline_reviews.json",
    "comparison_summary": "outputs/comparison_summary.json"
  }
}
```

## Requirements

Mock mode uses only the Python standard library.

Real LLM mode requires one of these provider setups:

- Python 3.10 or newer recommended.
- Ollama, default: Ollama running locally with an installed model such as `llama3.2`.
- OpenAI: `openai` Python package and `OPENAI_API_KEY`.
- Gemini: `google-genai` Python package and `GEMINI_API_KEY`.
- Optional test/development dependency: `pytest`. The standard-library `unittest` runner also works.

The optional Python package requirements are listed in `requirements.txt`.

If you are using the included virtual environment, activate it first:

```bash
source .venv/bin/activate
```

If you need OpenAI support:

```bash
python3 -m pip install openai
```

If you need Gemini support:

```bash
python3 -m pip install google-genai
```

If you use the default Ollama provider, no Python package or API key is required. Make sure Ollama is running and the model exists:

```bash
ollama list
ollama pull llama3.2
```

If Ollama is already running, `ollama serve` may print `address already in use`; that is normal.

## Validation And Retry Behavior

The project includes a built-in schema validator for review JSON. The validator is used for `mock`, `ollama`, `openai`, and `gemini` providers.

Defense reviews must include all defense assurance fields, 1 to 4 category scores, `Overall` from 1 to 10, `Confidence` from 1 to 5, and a decision of `Ready`, `Needs Revision`, or `Not Ready`.

ML baseline reviews must include all baseline paper-review fields, 1 to 4 category scores, `Overall` from 1 to 10, `Confidence` from 1 to 5, and a decision of `Accept` or `Reject`.

Returned review JSON displays those ratings as `value/max`, such as `4/4`, `8/10`, or `5/5`.

For real LLM runs, invalid responses are retried with a repair prompt. This keeps successful output file shapes unchanged while making Ollama, OpenAI, and Gemini runs more reliable.

## Quick Start Without API Keys

From this project folder:

```bash
cd /Users/sora/defense_ai_assurance_reviewer
python3 review_defense_doc.py \
  --doc sample_docs/English/weak_logistics_ai_safety_case.txt \
  --mock
```

This uses deterministic mock mode, so it does not require API keys or a running local LLM. If you omit `--mock`, the default provider is local Ollama with `llama3.2`.

Save a single review to a file:

```bash
python3 review_defense_doc.py \
  --doc sample_docs/English/weak_logistics_ai_safety_case.txt \
  --mock \
  --output outputs/weak_logistics_single_review.json
```

Run the full comparison over all sample documents:

```bash
python3 compare_reviewers.py
```

This regenerates:

```text
outputs/defense_reviews.json
outputs/ml_baseline_reviews.json
outputs/comparison_summary.json
outputs/<run_id>/
```

The printed `Run folder:` line shows the exact run directory for that execution.

## Run With A Real LLM

Ollama, OpenAI, and Gemini responses are parsed, schema-validated, and retried when the model returns malformed JSON or a review that does not match the selected rubric.

Before retrying, the parser applies narrow repairs for common local-model output issues, including unquoted rating fractions, half-point rating fractions, and `//` comments inside JSON. Responses that still fail parsing or schema validation are sent through the repair-prompt retry flow.

Retry behavior:

- `--max-retries 2` means one initial attempt plus up to two repair attempts.
- Repair prompts include the validation errors and the previous raw response.
- `--retry-temperature` can be used to set a separate temperature for repair attempts.
- If all attempts fail, the script raises a clear error with the validation failures and a preview of the last response.

Run one document with the default local Ollama model:

```bash
python3 review_defense_doc.py \
  --doc sample_docs/English/strong_maintenance_model_eval_report.txt
```

Run the full comparison with default Ollama:

```bash
python3 compare_reviewers.py --run-name ollama-test-run
```

Use another installed Ollama model:

```bash
python3 review_defense_doc.py \
  --doc sample_docs/English/strong_maintenance_model_eval_report.txt \
  --provider ollama \
  --model mistral
```

Set your OpenAI API key:

```bash
export OPENAI_API_KEY="your-key"
```

Or for Gemini:

```bash
export GEMINI_API_KEY="your-key"
```

Review one document with OpenAI:

```bash
python3 review_defense_doc.py \
  --doc sample_docs/English/strong_maintenance_model_eval_report.txt \
  --provider openai \
  --model gpt-4o-mini
```

Review one document with Gemini:

```bash
python3 review_defense_doc.py \
  --doc sample_docs/English/strong_maintenance_model_eval_report.txt \
  --provider gemini \
  --model gemini-2.0-flash
```

Run the full comparison with Gemini:

```bash
python3 compare_reviewers.py \
  --provider gemini \
  --model gemini-2.0-flash
```

Run the full comparison with OpenAI:

```bash
python3 compare_reviewers.py \
  --provider openai \
  --model gpt-4o-mini
```

Adjust generation randomness if needed:

```bash
python3 compare_reviewers.py \
  --provider ollama \
  --model llama3.2 \
  --temperature 0.1 \
  --max-retries 2
```

## Command Reference

Single-document reviewer:

```bash
python3 review_defense_doc.py \
  --doc sample_docs/English/PATH_TO_DOCUMENT.txt \
  --rubric defense \
  --provider ollama \
  --model llama3.2 \
  --temperature 0.1 \
  --max-retries 2 \
  --output outputs/example_review.json
```

Options:

- `--doc`: required path to a text document.
- `--rubric`: `defense` or `ml_baseline`.
- `--provider`: `ollama`, `mock`, `openai`, or `gemini`. Defaults to `ollama`.
- `--model`: model name for Ollama, OpenAI, or Gemini mode. Defaults to `llama3.2` for Ollama, `gpt-4o-mini` for OpenAI/mock, and `gemini-2.0-flash` for Gemini.
- `--temperature`: model temperature for real LLM mode.
- `--max-retries`: number of repair attempts for malformed or schema-invalid real LLM responses.
- `--retry-temperature`: optional temperature for retry/repair attempts.
- `--mock`: alias for `--provider mock`.
- `--output`: optional path for writing review JSON.

Dataset comparison:

```bash
python3 compare_reviewers.py \
  --provider ollama \
  --model llama3.2 \
  --en \
  --temperature 0.1 \
  --max-retries 2 \
  --output-dir outputs
```

Run the Japanese sample corpus:

```bash
python3 compare_reviewers.py \
  --provider ollama \
  --model llama3.2 \
  --jp \
  --run-name japanese-ollama-run
```

Options:

- `--provider`: `ollama`, `mock`, `openai`, or `gemini`. Defaults to `ollama`.
- `--model`: model name for Ollama, OpenAI, or Gemini mode. Defaults to `llama3.2` for Ollama, `gpt-4o-mini` for OpenAI/mock, and `gemini-2.0-flash` for Gemini.
- `--language`: sample corpus language, either `en` or `jp`. Defaults to `en`.
- `--en`: alias for `--language en`.
- `--jp`: alias for `--language jp`.
- `--temperature`: model temperature for real LLM mode.
- `--max-retries`: number of repair attempts for malformed or schema-invalid real LLM responses.
- `--retry-temperature`: optional temperature for retry/repair attempts.
- `--output-dir`: output directory for latest-result files and timestamped run folders.
- `--run-name`: optional explicit folder name under the output directory.
- `--mock`: alias for `--provider mock`.

## Experiment Plan

1. Build a synthetic dataset of fictional defense/government AI assurance documents.
2. Label each document with expected quality and known issues.
3. Review each document with the defense-specific assurance rubric.
4. Review each document with an ML-paper-style baseline rubric.
5. Compare score ordering, known-issue detection, and domain relevance.
6. Save latest-result JSON files in `outputs/`.
7. Preserve each full comparison run in `outputs/<run_id>/` with `run_metadata.json`.
8. Summarize results in `outputs/comparison_summary.json` and `report.md`.

The proof of concept is considered successful if it includes:

- A working defense assurance reviewer script.
- A defense-specific rubric.
- At least 6 synthetic assurance documents, preferably 9.
- JSON outputs from the reviewer.
- Schema validation and retry handling for real LLM review outputs.
- Per-run output folders with metadata.
- A comparison against an ML-paper-style baseline.
- A short report explaining method, results, limitations, and citations.

## Current Saved Results

The current saved output folders are Ollama `llama3.1:8b` runs, not mock runs. The best English result file to include in a report is:

```text
outputs/llama3.1-8b-test-run2-2/comparison_summary.json
```

That English run shows this broad defense-review score pattern:

```text
Expected quality   Defense overall pattern
Weak               2/10
Medium             5/10-6/10
Strong             6/10-7/10
```

The same folder also contains `defense_reviews.json`, `ml_baseline_reviews.json`, and `run_metadata.json`. Use `defense_reviews.json` for example assurance feedback, `ml_baseline_reviews.json` for contrast with the paper-style baseline, and `run_metadata.json` for provider/model/run settings.

The saved Japanese run is:

```text
outputs/20260504T151137Z_ollama_llama3.1-8b/
```

The ML baseline scores are less domain-sensitive because the baseline evaluates the documents as if they were AI research papers rather than assurance artifacts.

## How To Interpret Results

Useful signals:

- Strong documents should usually receive higher defense overall scores than weak documents.
- Weak documents should surface missing oversight, testing, privacy/security, failure-mode, or deployment-readiness details.
- Defense recommendations should be actionable for assurance documentation.
- ML baseline feedback should be visibly less relevant to readiness, governance, and deployment controls.

Limitations:

- Mock mode is deterministic and heuristic.
- Real LLM outputs can vary by model and temperature.
- Local Ollama quality and speed depend on the installed model and your machine.
- Retry handling improves real LLM output reliability, but it cannot guarantee reviewer quality.
- The dataset is small and synthetic.
- Known-issue matching is keyword-based and approximate.
- The tool is a reviewer assistant, not a legal, policy, or compliance authority.

## Relationship To The AI Scientist

This project borrows the review pattern from The AI Scientist Automated Reviewer:

- Use a system prompt to define reviewer role.
- Provide a rubric.
- Ask for structured reasoning plus JSON.
- Parse the JSON output.
- Compare review forms experimentally.

The key change is the review target. The original system reviews ML papers. This project reviews fictional assurance documents for governance and responsible deployment readiness.

The local reference copy is in `external/AI-Scientist/`. The most relevant file to study is:

```text
external/AI-Scientist/ai_scientist/perform_review.py
```

## Future Work

- Add expert-written labels for issue detection.
- Add more document types, such as procurement checklists, model cards, data protection reviews, and monitoring plans.
- Compare multiple LLMs and rubric variants.
- Add reflection or ensemble review similar to the original AI Scientist reviewer.
- Generate per-run Markdown reports inside timestamped output folders.
- Replace keyword-based known-issue matching with semantic matching.
- Add a document-improvement loop and measure before/after scores.

## Citations And References

- The AI Scientist Nature paper: https://www.nature.com/articles/s41586-026-10265-5
- Sakana AI blog on The AI Scientist: https://sakana.ai/ai-scientist-nature
- Local AI Scientist reference: `external/AI-Scientist/`
- NIST AI Risk Management Framework: https://www.nist.gov/itl/ai-risk-management-framework
