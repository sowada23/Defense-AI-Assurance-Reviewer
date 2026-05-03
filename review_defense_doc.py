#!/usr/bin/env python3
"""
Review fictional defense AI assurance documents.

This is a small, standalone adaptation of The AI Scientist's reviewer pattern:
build a review prompt, call an LLM, extract JSON, and save structured output.
It also includes a deterministic mock mode so the project can be tested without
API keys.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

from review_schema import ReviewSchemaError, assert_valid_review, coerce_review, format_review_scores

PROJECT_DIR = Path(__file__).resolve().parent
DEFENSE_RUBRIC_PATH = PROJECT_DIR / "rubrics" / "defense_assurance_rubric.md"
ML_RUBRIC_PATH = PROJECT_DIR / "rubrics" / "ml_paper_rubric_summary.md"

DEFENSE_SYSTEM_PROMPT = (
    "You are a cautious AI assurance reviewer evaluating fictional, "
    "non-operational defense AI governance documents for safety, oversight, "
    "compliance, and deployment readiness. Do not provide tactical, weapons, "
    "targeting, surveillance, cyber, or operational military advice. Focus only "
    "on documentation quality, risk management, human oversight, privacy, "
    "security, and responsible deployment."
)

ML_BASELINE_SYSTEM_PROMPT = (
    "You are an AI researcher reviewing a technical AI paper. Be critical and "
    "focus on originality, quality, clarity, significance, soundness, "
    "presentation, and contribution."
)

DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"
DEFAULT_OLLAMA_MODEL = "llama3.2"
DEFAULT_PROVIDER = "ollama"


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def repair_unquoted_rating_fractions(json_text: str) -> str:
    """Quote bare rating fractions in object values, e.g. "Overall": 7/10."""
    return re.sub(
        r'(:\s*)([1-9]\d*)\s*/\s*([1-9]\d*)(\s*[,}\]])',
        r'\1"\2/\3"\4',
        json_text,
    )


def parse_json_with_repairs(json_text: str) -> dict[str, Any]:
    try:
        return json.loads(json_text)
    except json.JSONDecodeError:
        repaired = repair_unquoted_rating_fractions(json_text)
        if repaired == json_text:
            raise
        return json.loads(repaired)


def extract_json_between_markers(text: str) -> dict[str, Any]:
    fenced = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        return parse_json_with_repairs(fenced.group(1))

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in model response")
    return parse_json_with_repairs(text[start : end + 1])


def parse_and_validate_review(response_text: str, rubric: str) -> dict[str, Any]:
    parsed = extract_json_between_markers(response_text)
    if not isinstance(parsed, dict):
        raise ReviewSchemaError([f"Review must be a JSON object, got {type(parsed).__name__}."])
    review = coerce_review(parsed, rubric)
    assert_valid_review(review, rubric)
    return format_review_scores(review, rubric)


def build_defense_prompt(document_text: str) -> str:
    rubric = load_text(DEFENSE_RUBRIC_PATH)
    return f"""{rubric}

Here is the assurance document you are asked to review:

```text
{document_text}
```
"""


def build_ml_baseline_prompt(document_text: str) -> str:
    rubric = load_text(ML_RUBRIC_PATH)
    return f"""{rubric}

Respond in this exact format:

THOUGHT:
<brief reasoning specific to this document>

REVIEW JSON:
```json
{{
  "Summary": "",
  "Strengths": [],
  "Weaknesses": [],
  "Originality": "1/4",
  "Quality": "1/4",
  "Clarity": "1/4",
  "Significance": "1/4",
  "Soundness": "1/4",
  "Presentation": "1/4",
  "Contribution": "1/4",
  "Questions": [],
  "Limitations": [],
  "Ethical Concerns": false,
  "Overall": "1/10",
  "Confidence": "1/5",
  "Decision": "Reject"
}}
```

Use value/max strings for every rating field, such as "3/4", "7/10", or "4/5".

Here is the document you are asked to review:

```text
{document_text}
```
"""


def keyword_score(document_text: str, positive_terms: list[str]) -> int:
    text = document_text.lower()
    hits = sum(1 for term in positive_terms if term in text)
    if hits >= 6:
        return 4
    if hits >= 4:
        return 3
    if hits >= 2:
        return 2
    return 1


def quality_hint(document_text: str) -> str:
    lower = document_text.lower()
    if "expected quality: strong" in lower or "strong" in lower[:120]:
        return "strong"
    if "expected quality: medium" in lower or "medium" in lower[:120]:
        return "medium"
    if "expected quality: weak" in lower or "weak" in lower[:120]:
        return "weak"
    return "unknown"


def clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def mock_defense_review(document_text: str, doc_name: str = "") -> dict[str, Any]:
    hint = quality_hint(document_text + "\n" + doc_name)
    base = {"strong": 4, "medium": 3, "weak": 2}.get(hint, 2)
    if hint == "weak":
        base = 1

    scores = {
        "Mission Clarity": keyword_score(document_text, ["purpose", "users", "scope", "not intended", "limitations", "approval"]),
        "Human Oversight": keyword_score(document_text, ["human", "review", "override", "escalation", "operator", "approval"]),
        "Data Governance": keyword_score(document_text, ["data", "source", "retention", "lineage", "quality", "access"]),
        "Privacy and Security": keyword_score(document_text, ["privacy", "security", "encrypted", "access", "audit", "personal"]),
        "Safety and Reliability": keyword_score(document_text, ["safety", "reliability", "fallback", "monitoring", "incident", "threshold"]),
        "Robustness Testing": keyword_score(document_text, ["robustness", "stress", "drift", "test", "scenario", "validation"]),
        "Failure Mode Coverage": keyword_score(document_text, ["failure", "mode", "mitigation", "false", "fallback", "risk"]),
        "Legal and Policy Alignment": keyword_score(document_text, ["legal", "policy", "compliance", "procurement", "audit", "approval"]),
        "Deployment Readiness": keyword_score(document_text, ["deployment", "readiness", "pilot", "rollback", "monitoring", "training"]),
        "Operational Risk": keyword_score(document_text, ["non-operational", "advisory", "human", "limited", "no autonomous", "risk"]),
    }

    # Keep mock outputs aligned with labels so tests are predictable.
    for key in scores:
        scores[key] = clamp(round((scores[key] + base) / 2), 1, 4)

    known_weaknesses = []
    lower = document_text.lower()
    checks = [
        ("human oversight is underspecified", ["human", "override", "escalation"]),
        ("failure modes are incomplete", ["failure", "mode", "mitigation"]),
        ("privacy and security controls need more detail", ["privacy", "security", "access"]),
        ("evaluation evidence is too thin", ["validation", "test", "metric"]),
        ("deployment readiness lacks concrete rollback criteria", ["rollback", "deployment", "monitoring"]),
    ]
    for weakness, terms in checks:
        if sum(1 for term in terms if term in lower) < 2:
            known_weaknesses.append(weakness)

    strengths = []
    if scores["Mission Clarity"] >= 3:
        strengths.append("The document states a clear administrative or support purpose.")
    if scores["Human Oversight"] >= 3:
        strengths.append("Human review and escalation are described.")
    if scores["Data Governance"] >= 3:
        strengths.append("Data sources and handling controls are documented.")
    if scores["Safety and Reliability"] >= 3:
        strengths.append("Safety monitoring and reliability controls are present.")

    if not strengths:
        strengths.append("The document provides a starting point for assurance review.")

    overall = clamp(round(sum(scores.values()) / len(scores) * 2.5), 1, 10)
    if overall >= 8:
        decision = "Ready"
    elif overall >= 5:
        decision = "Needs Revision"
    else:
        decision = "Not Ready"

    return {
        "Summary": "Fictional review of a non-operational defense/government AI assurance document.",
        "Strengths": strengths,
        "Weaknesses": known_weaknesses or ["No major weakness detected by the deterministic mock reviewer."],
        **scores,
        "Questions": [
            "What evidence supports the stated deployment readiness?",
            "Who has authority to pause or roll back the system?"
        ],
        "Recommended Improvements": [
            "Add explicit acceptance thresholds for pilot deployment.",
            "Map each known failure mode to an owner, mitigation, and monitoring signal.",
            "Document human override and escalation steps in operationally neutral governance terms."
        ],
        "Ethical Concerns": scores["Privacy and Security"] <= 2 or scores["Human Oversight"] <= 2,
        "Overall": overall,
        "Confidence": 4,
        "Decision": decision,
    }


def mock_ml_baseline_review(document_text: str, doc_name: str = "") -> dict[str, Any]:
    hint = quality_hint(document_text + "\n" + doc_name)
    base = {"strong": 6, "medium": 5, "weak": 4}.get(hint, 4)
    clarity = keyword_score(document_text, ["purpose", "evaluation", "limitations", "risk", "data", "deployment"])
    overall = clamp(base + (clarity - 2), 1, 10)
    return {
        "Summary": "Baseline ML-style review of a governance document treated as a technical AI submission.",
        "Strengths": ["The document describes an AI-enabled process and some evaluation considerations."],
        "Weaknesses": [
            "The ML-paper rubric does not directly evaluate assurance readiness.",
            "Domain controls such as human oversight and deployment governance are not central in this baseline."
        ],
        "Originality": 2,
        "Quality": clamp(clarity, 1, 4),
        "Clarity": clamp(clarity, 1, 4),
        "Significance": 2,
        "Soundness": clamp(clarity, 1, 4),
        "Presentation": clamp(clarity, 1, 4),
        "Contribution": 2,
        "Questions": ["What is the technical contribution beyond documenting a system?"],
        "Limitations": ["This baseline rubric is mismatched to assurance documentation."],
        "Ethical Concerns": "privacy" not in document_text.lower(),
        "Overall": overall,
        "Confidence": 3,
        "Decision": "Accept" if overall >= 7 else "Reject",
    }


def call_openai(prompt: str, system_prompt: str, model: str, temperature: float) -> str:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("Install openai or use --mock") from exc

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set. Use --mock for local testing.")

    client = OpenAI()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
    )
    return response.choices[0].message.content or ""


def call_gemini(prompt: str, system_prompt: str, model: str, temperature: float) -> str:
    if not os.getenv("GEMINI_API_KEY"):
        raise RuntimeError("GEMINI_API_KEY is not set. Use --mock for local testing.")

    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise RuntimeError("Install google-genai or use --mock") from exc

    client = genai.Client()
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=temperature,
        ),
    )
    return response.text or ""


def call_ollama(prompt: str, system_prompt: str, model: str, temperature: float) -> str:
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    url = f"{base_url}/api/chat"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "options": {"temperature": temperature},
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Ollama API request failed with HTTP {exc.code}: {details}") from exc
    except OSError as exc:
        raise RuntimeError(
            "Could not reach Ollama. Make sure the Ollama app is running or start it with `ollama serve`."
        ) from exc

    content = data.get("message", {}).get("content")
    if not isinstance(content, str):
        raise RuntimeError(f"Ollama response did not include message.content: {data}")
    return content


def build_retry_prompt(original_prompt: str, raw_response: str, errors: list[str]) -> str:
    error_text = "\n".join(f"- {error}" for error in errors)
    clipped_response = raw_response[-6000:] if raw_response else "<empty response>"
    return f"""{original_prompt}

Your previous response could not be parsed or did not match the required review schema.
Return a corrected response in the same required format. Do not add extra fields.

Validation errors:
{error_text}

Previous response:
```text
{clipped_response}
```
"""


def review_with_model_retries(
    prompt: str,
    system_prompt: str,
    rubric: str,
    model: str,
    temperature: float,
    max_retries: int,
    retry_temperature: float | None,
    provider_name: str,
    call_model: Callable[[str, str, str, float], str] = call_openai,
) -> dict[str, Any]:
    if max_retries < 0:
        raise ValueError("max_retries must be 0 or greater.")

    attempts = max_retries + 1
    prompt_for_attempt = prompt
    last_errors: list[str] = []
    last_response = ""
    repair_temperature = temperature if retry_temperature is None else retry_temperature

    for attempt in range(attempts):
        current_temperature = temperature if attempt == 0 else repair_temperature
        last_response = call_model(prompt_for_attempt, system_prompt, model, current_temperature)
        try:
            return parse_and_validate_review(last_response, rubric)
        except (json.JSONDecodeError, ReviewSchemaError, ValueError) as exc:
            if isinstance(exc, ReviewSchemaError):
                last_errors = exc.errors
            else:
                last_errors = [str(exc)]
            prompt_for_attempt = build_retry_prompt(prompt, last_response, last_errors)

    error_text = "\n".join(f"- {error}" for error in last_errors)
    response_preview = last_response[-1000:] if last_response else "<empty response>"
    raise RuntimeError(
        f"{provider_name} review failed schema validation after {attempts} attempt(s).\n"
        f"Errors:\n{error_text}\n"
        f"Last response preview:\n{response_preview}"
    )


def review_with_openai_retries(
    prompt: str,
    system_prompt: str,
    rubric: str,
    model: str,
    temperature: float,
    max_retries: int,
    retry_temperature: float | None,
    call_model: Callable[[str, str, str, float], str] = call_openai,
) -> dict[str, Any]:
    return review_with_model_retries(
        prompt=prompt,
        system_prompt=system_prompt,
        rubric=rubric,
        model=model,
        temperature=temperature,
        max_retries=max_retries,
        retry_temperature=retry_temperature,
        provider_name="OpenAI",
        call_model=call_model,
    )


def review_document(
    document_path: Path,
    rubric: str = "defense",
    provider: str = DEFAULT_PROVIDER,
    model: str = DEFAULT_OLLAMA_MODEL,
    temperature: float = 0.1,
    max_retries: int = 2,
    retry_temperature: float | None = None,
) -> dict[str, Any]:
    document_text = load_text(document_path)
    if provider == "mock":
        if rubric == "defense":
            review = mock_defense_review(document_text, document_path.name)
        else:
            review = mock_ml_baseline_review(document_text, document_path.name)
        review = coerce_review(review, rubric)
        assert_valid_review(review, rubric)
        return format_review_scores(review, rubric)

    if rubric == "defense":
        prompt = build_defense_prompt(document_text)
        system_prompt = DEFENSE_SYSTEM_PROMPT
    else:
        prompt = build_ml_baseline_prompt(document_text)
        system_prompt = ML_BASELINE_SYSTEM_PROMPT

    if provider == "openai":
        return review_with_model_retries(
            prompt=prompt,
            system_prompt=system_prompt,
            rubric=rubric,
            model=model,
            temperature=temperature,
            max_retries=max_retries,
            retry_temperature=retry_temperature,
            provider_name="OpenAI",
            call_model=call_openai,
        )

    if provider == "gemini":
        return review_with_model_retries(
            prompt=prompt,
            system_prompt=system_prompt,
            rubric=rubric,
            model=model,
            temperature=temperature,
            max_retries=max_retries,
            retry_temperature=retry_temperature,
            provider_name="Gemini",
            call_model=call_gemini,
        )

    if provider == "ollama":
        return review_with_model_retries(
            prompt=prompt,
            system_prompt=system_prompt,
            rubric=rubric,
            model=model,
            temperature=temperature,
            max_retries=max_retries,
            retry_temperature=retry_temperature,
            provider_name="Ollama",
            call_model=call_ollama,
        )

    raise ValueError(f"Unsupported provider: {provider}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Review a fictional defense AI assurance document.")
    parser.add_argument("--doc", required=True, help="Path to a .txt document to review.")
    parser.add_argument("--rubric", choices=["defense", "ml_baseline"], default="defense")
    parser.add_argument("--provider", choices=["mock", "openai", "gemini", "ollama"], default=DEFAULT_PROVIDER)
    parser.add_argument("--model", help="Model name for OpenAI, Gemini, or Ollama mode.")
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--max-retries", type=int, default=2)
    parser.add_argument("--retry-temperature", type=float)
    parser.add_argument("--mock", action="store_true", help="Alias for --provider mock.")
    parser.add_argument("--output", help="Optional JSON output path.")
    args = parser.parse_args()

    provider = "mock" if args.mock else args.provider
    model = args.model
    if model is None:
        if provider == "gemini":
            model = DEFAULT_GEMINI_MODEL
        elif provider == "ollama":
            model = DEFAULT_OLLAMA_MODEL
        else:
            model = DEFAULT_OPENAI_MODEL
    review = review_document(
        Path(args.doc),
        rubric=args.rubric,
        provider=provider,
        model=model,
        temperature=args.temperature,
        max_retries=args.max_retries,
        retry_temperature=args.retry_temperature,
    )

    print(json.dumps(review, indent=2))
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(review, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
