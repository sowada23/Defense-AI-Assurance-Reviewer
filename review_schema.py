"""
Schema validation for reviewer JSON outputs.
"""

from __future__ import annotations

from copy import deepcopy
import re
from typing import Any


class ReviewSchemaError(ValueError):
    """Raised when a review does not match the expected rubric schema."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("\n".join(errors))


COMMON_STRING_FIELDS = ["Summary", "Decision"]
COMMON_LIST_FIELDS = ["Strengths", "Weaknesses", "Questions"]
COMMON_INT_FIELDS = {"Overall": (1, 10), "Confidence": (1, 5)}
RATING_PATTERN = re.compile(r"^\s*(\d+)\s*/\s*(\d+)\s*$")

DEFENSE_INT_FIELDS = {
    "Mission Clarity": (1, 4),
    "Human Oversight": (1, 4),
    "Data Governance": (1, 4),
    "Privacy and Security": (1, 4),
    "Safety and Reliability": (1, 4),
    "Robustness Testing": (1, 4),
    "Failure Mode Coverage": (1, 4),
    "Legal and Policy Alignment": (1, 4),
    "Deployment Readiness": (1, 4),
    "Operational Risk": (1, 4),
}

ML_BASELINE_INT_FIELDS = {
    "Originality": (1, 4),
    "Quality": (1, 4),
    "Clarity": (1, 4),
    "Significance": (1, 4),
    "Soundness": (1, 4),
    "Presentation": (1, 4),
    "Contribution": (1, 4),
}

RUBRIC_SCHEMAS = {
    "defense": {
        "list_fields": COMMON_LIST_FIELDS + ["Recommended Improvements"],
        "string_fields": COMMON_STRING_FIELDS,
        "bool_fields": ["Ethical Concerns"],
        "int_fields": {**DEFENSE_INT_FIELDS, **COMMON_INT_FIELDS},
        "valid_decisions": {"Ready", "Needs Revision", "Not Ready"},
    },
    "ml_baseline": {
        "list_fields": COMMON_LIST_FIELDS + ["Limitations"],
        "string_fields": COMMON_STRING_FIELDS,
        "bool_fields": ["Ethical Concerns"],
        "int_fields": {**ML_BASELINE_INT_FIELDS, **COMMON_INT_FIELDS},
        "valid_decisions": {"Accept", "Reject"},
    },
}


def get_schema(rubric: str) -> dict[str, Any]:
    try:
        return RUBRIC_SCHEMAS[rubric]
    except KeyError as exc:
        raise ValueError(f"Unsupported rubric: {rubric}") from exc


def required_fields(rubric: str) -> list[str]:
    schema = get_schema(rubric)
    return [
        *schema["string_fields"],
        *schema["list_fields"],
        *schema["bool_fields"],
        *schema["int_fields"].keys(),
    ]


def coerce_review(review: dict[str, Any], rubric: str) -> dict[str, Any]:
    """Return a copy with only unambiguous safe type coercions applied."""
    schema = get_schema(rubric)
    coerced = deepcopy(review)
    for field, (_minimum, maximum) in schema["int_fields"].items():
        value = coerced.get(field)
        if isinstance(value, float) and value.is_integer():
            coerced[field] = int(value)
        elif isinstance(value, str):
            match = RATING_PATTERN.match(value)
            if match and int(match.group(2)) == maximum:
                coerced[field] = int(match.group(1))
    return coerced


def format_review_scores(review: dict[str, Any], rubric: str) -> dict[str, Any]:
    """Return a copy with score fields formatted as value/max strings."""
    schema = get_schema(rubric)
    formatted = deepcopy(review)
    for field, (_minimum, maximum) in schema["int_fields"].items():
        value = formatted.get(field)
        if isinstance(value, int) and not isinstance(value, bool):
            formatted[field] = f"{value}/{maximum}"
    return formatted


def validate_review(review: dict[str, Any], rubric: str) -> list[str]:
    schema = get_schema(rubric)
    errors: list[str] = []

    if not isinstance(review, dict):
        return [f"Review must be a JSON object, got {type(review).__name__}."]

    for field in required_fields(rubric):
        if field not in review:
            errors.append(f"Missing required field: {field}.")

    for field in schema["string_fields"]:
        if field in review and not isinstance(review[field], str):
            errors.append(f"Field {field} must be a string.")

    for field in schema["list_fields"]:
        if field in review:
            value = review[field]
            if not isinstance(value, list):
                errors.append(f"Field {field} must be a list.")
            elif any(not isinstance(item, str) for item in value):
                errors.append(f"Field {field} must contain only strings.")

    for field in schema["bool_fields"]:
        if field in review and not isinstance(review[field], bool):
            errors.append(f"Field {field} must be a boolean.")

    for field, (minimum, maximum) in schema["int_fields"].items():
        if field not in review:
            continue
        value = review[field]
        if isinstance(value, bool) or not isinstance(value, int):
            errors.append(f"Field {field} must be an integer from {minimum} to {maximum}.")
        elif not minimum <= value <= maximum:
            errors.append(f"Field {field} must be from {minimum} to {maximum}, got {value}.")

    decision = review.get("Decision")
    if isinstance(decision, str) and decision not in schema["valid_decisions"]:
        valid = ", ".join(sorted(schema["valid_decisions"]))
        errors.append(f"Field Decision must be one of: {valid}. Got {decision!r}.")

    return errors


def assert_valid_review(review: dict[str, Any], rubric: str) -> None:
    errors = validate_review(review, rubric)
    if errors:
        raise ReviewSchemaError(errors)
