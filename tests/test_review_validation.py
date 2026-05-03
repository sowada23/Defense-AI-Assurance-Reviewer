from __future__ import annotations

import copy
import io
import json
import os
import unittest
from unittest.mock import patch

from review_defense_doc import call_gemini, call_ollama, extract_json_between_markers, repair_unquoted_rating_fractions, review_with_model_retries, review_with_openai_retries
from review_schema import assert_valid_review, coerce_review, format_review_scores, validate_review


VALID_DEFENSE_REVIEW = {
    "Summary": "A review summary.",
    "Strengths": ["Clear purpose."],
    "Weaknesses": ["Needs more evidence."],
    "Mission Clarity": 3,
    "Human Oversight": 3,
    "Data Governance": 3,
    "Privacy and Security": 3,
    "Safety and Reliability": 3,
    "Robustness Testing": 3,
    "Failure Mode Coverage": 3,
    "Legal and Policy Alignment": 3,
    "Deployment Readiness": 3,
    "Operational Risk": 3,
    "Questions": ["Who owns rollback?"],
    "Recommended Improvements": ["Add acceptance thresholds."],
    "Ethical Concerns": False,
    "Overall": 7,
    "Confidence": 4,
    "Decision": "Needs Revision",
}

VALID_ML_REVIEW = {
    "Summary": "A baseline review summary.",
    "Strengths": ["Readable."],
    "Weaknesses": ["Limited contribution."],
    "Originality": 2,
    "Quality": 3,
    "Clarity": 3,
    "Significance": 2,
    "Soundness": 3,
    "Presentation": 3,
    "Contribution": 2,
    "Questions": ["What is the contribution?"],
    "Limitations": ["Mismatched rubric."],
    "Ethical Concerns": False,
    "Overall": 6,
    "Confidence": 3,
    "Decision": "Reject",
}


def fenced_json(review: dict[str, object]) -> str:
    return "THOUGHT:\nshort\n\nREVIEW JSON:\n```json\n" + json.dumps(review) + "\n```"


class ReviewSchemaTests(unittest.TestCase):
    def test_valid_defense_review(self) -> None:
        self.assertEqual(validate_review(VALID_DEFENSE_REVIEW, "defense"), [])
        assert_valid_review(VALID_DEFENSE_REVIEW, "defense")

    def test_valid_ml_review(self) -> None:
        self.assertEqual(validate_review(VALID_ML_REVIEW, "ml_baseline"), [])
        assert_valid_review(VALID_ML_REVIEW, "ml_baseline")

    def test_missing_required_field(self) -> None:
        review = copy.deepcopy(VALID_DEFENSE_REVIEW)
        del review["Human Oversight"]
        errors = validate_review(review, "defense")
        self.assertIn("Missing required field: Human Oversight.", errors)

    def test_wrong_score_type_is_invalid(self) -> None:
        review = copy.deepcopy(VALID_DEFENSE_REVIEW)
        review["Overall"] = "7"
        errors = validate_review(review, "defense")
        self.assertIn("Field Overall must be an integer from 1 to 10.", errors)

    def test_integer_like_float_is_coerced(self) -> None:
        review = copy.deepcopy(VALID_DEFENSE_REVIEW)
        review["Overall"] = 7.0
        coerced = coerce_review(review, "defense")
        self.assertEqual(coerced["Overall"], 7)
        assert_valid_review(coerced, "defense")

    def test_rating_string_is_coerced_when_denominator_matches_schema(self) -> None:
        review = copy.deepcopy(VALID_DEFENSE_REVIEW)
        review["Overall"] = "7/10"
        review["Confidence"] = "4/5"
        review["Mission Clarity"] = "3/4"
        coerced = coerce_review(review, "defense")
        self.assertEqual(coerced["Overall"], 7)
        self.assertEqual(coerced["Confidence"], 4)
        self.assertEqual(coerced["Mission Clarity"], 3)
        assert_valid_review(coerced, "defense")

    def test_review_scores_are_formatted_with_denominators(self) -> None:
        formatted = format_review_scores(VALID_DEFENSE_REVIEW, "defense")
        self.assertEqual(formatted["Mission Clarity"], "3/4")
        self.assertEqual(formatted["Overall"], "7/10")
        self.assertEqual(formatted["Confidence"], "4/5")

    def test_out_of_range_score_is_invalid(self) -> None:
        review = copy.deepcopy(VALID_DEFENSE_REVIEW)
        review["Confidence"] = 9
        errors = validate_review(review, "defense")
        self.assertIn("Field Confidence must be from 1 to 5, got 9.", errors)

    def test_invalid_decision_is_invalid(self) -> None:
        review = copy.deepcopy(VALID_DEFENSE_REVIEW)
        review["Decision"] = "Maybe Ready"
        errors = validate_review(review, "defense")
        self.assertIn(
            "Field Decision must be one of: Needs Revision, Not Ready, Ready. Got 'Maybe Ready'.",
            errors,
        )

    def test_extract_json_from_fenced_response(self) -> None:
        self.assertEqual(extract_json_between_markers(fenced_json(VALID_DEFENSE_REVIEW)), VALID_DEFENSE_REVIEW)

    def test_extract_json_from_unfenced_response(self) -> None:
        text = "prefix " + json.dumps(VALID_ML_REVIEW) + " suffix"
        self.assertEqual(extract_json_between_markers(text), VALID_ML_REVIEW)

    def test_repair_unquoted_rating_fractions(self) -> None:
        text = '{"Mission Clarity": 3/4, "Overall": 7/10, "Confidence": 4/5}'
        repaired = repair_unquoted_rating_fractions(text)
        self.assertEqual(
            repaired,
            '{"Mission Clarity": "3/4", "Overall": "7/10", "Confidence": "4/5"}',
        )

    def test_extract_json_repairs_ollama_bare_rating_fractions(self) -> None:
        response = """THOUGHT:
short

REVIEW JSON:
```json
{
  "Summary": "A review summary.",
  "Strengths": ["Clear purpose."],
  "Weaknesses": ["Needs more evidence."],
  "Mission Clarity": 3/4,
  "Human Oversight": 3/4,
  "Data Governance": 3/4,
  "Privacy and Security": 3/4,
  "Safety and Reliability": 3/4,
  "Robustness Testing": 3/4,
  "Failure Mode Coverage": 3/4,
  "Legal and Policy Alignment": 3/4,
  "Deployment Readiness": 3/4,
  "Operational Risk": 3/4,
  "Questions": ["Who owns rollback?"],
  "Recommended Improvements": ["Add acceptance thresholds."],
  "Ethical Concerns": false,
  "Overall": 7/10,
  "Confidence": 4/5,
  "Decision": "Needs Revision"
}
```
"""
        extracted = extract_json_between_markers(response)
        self.assertEqual(extracted["Mission Clarity"], "3/4")
        self.assertEqual(extracted["Overall"], "7/10")
        self.assertEqual(extracted["Confidence"], "4/5")


class RetryTests(unittest.TestCase):
    def test_retries_after_malformed_json(self) -> None:
        calls: list[str] = []
        responses = iter(["not json", fenced_json(VALID_DEFENSE_REVIEW)])

        def fake_call(prompt: str, system_prompt: str, model: str, temperature: float) -> str:
            calls.append(prompt)
            return next(responses)

        review = review_with_openai_retries(
            prompt="original prompt",
            system_prompt="system",
            rubric="defense",
            model="test-model",
            temperature=0.2,
            max_retries=1,
            retry_temperature=0.0,
            call_model=fake_call,
        )

        self.assertEqual(review["Decision"], "Needs Revision")
        self.assertEqual(review["Overall"], "7/10")
        self.assertEqual(review["Confidence"], "4/5")
        self.assertEqual(len(calls), 2)
        self.assertIn("Validation errors:", calls[1])

    def test_retries_after_schema_invalid_json(self) -> None:
        invalid = copy.deepcopy(VALID_DEFENSE_REVIEW)
        invalid["Overall"] = 11
        responses = iter([fenced_json(invalid), fenced_json(VALID_DEFENSE_REVIEW)])

        def fake_call(prompt: str, system_prompt: str, model: str, temperature: float) -> str:
            return next(responses)

        review = review_with_openai_retries(
            prompt="original prompt",
            system_prompt="system",
            rubric="defense",
            model="test-model",
            temperature=0.2,
            max_retries=1,
            retry_temperature=0.0,
            call_model=fake_call,
        )

        self.assertEqual(review["Overall"], "7/10")

    def test_final_failure_after_all_retries(self) -> None:
        def fake_call(prompt: str, system_prompt: str, model: str, temperature: float) -> str:
            return "not json"

        with self.assertRaises(RuntimeError):
            review_with_openai_retries(
                prompt="original prompt",
                system_prompt="system",
                rubric="defense",
                model="test-model",
                temperature=0.2,
                max_retries=1,
                retry_temperature=0.0,
                call_model=fake_call,
            )

    def test_schema_error_after_zero_retries(self) -> None:
        invalid = copy.deepcopy(VALID_DEFENSE_REVIEW)
        invalid["Decision"] = "Maybe Ready"

        def fake_call(prompt: str, system_prompt: str, model: str, temperature: float) -> str:
            return fenced_json(invalid)

        with self.assertRaises(RuntimeError):
            review_with_openai_retries(
                prompt="original prompt",
                system_prompt="system",
                rubric="defense",
                model="test-model",
                temperature=0.2,
                max_retries=0,
                retry_temperature=None,
                call_model=fake_call,
            )

    def test_negative_retry_count_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            review_with_openai_retries(
                prompt="original prompt",
                system_prompt="system",
                rubric="defense",
                model="test-model",
                temperature=0.2,
                max_retries=-1,
                retry_temperature=None,
                call_model=lambda *_args: fenced_json(VALID_DEFENSE_REVIEW),
            )

    def test_generic_retry_error_names_provider(self) -> None:
        def fake_call(prompt: str, system_prompt: str, model: str, temperature: float) -> str:
            return "not json"

        with self.assertRaisesRegex(RuntimeError, "Gemini review failed schema validation"):
            review_with_model_retries(
                prompt="original prompt",
                system_prompt="system",
                rubric="defense",
                model="test-model",
                temperature=0.2,
                max_retries=0,
                retry_temperature=None,
                provider_name="Gemini",
                call_model=fake_call,
            )

    def test_call_gemini_requires_api_key_before_import(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "GEMINI_API_KEY is not set"):
                call_gemini("prompt", "system", "gemini-2.0-flash", 0.1)

    def test_call_ollama_uses_local_chat_api(self) -> None:
        class FakeResponse:
            def __enter__(self) -> "FakeResponse":
                return self

            def __exit__(self, *_args: object) -> None:
                return None

            def read(self) -> bytes:
                return json.dumps({"message": {"content": fenced_json(VALID_DEFENSE_REVIEW)}}).encode("utf-8")

        captured: dict[str, object] = {}

        def fake_urlopen(request: object, timeout: int) -> FakeResponse:
            captured["timeout"] = timeout
            captured["url"] = request.full_url
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return FakeResponse()

        with patch("urllib.request.urlopen", fake_urlopen):
            content = call_ollama("prompt", "system", "llama3.2", 0.1)

        self.assertIn("REVIEW JSON", content)
        self.assertEqual(captured["timeout"], 300)
        self.assertEqual(captured["url"], "http://localhost:11434/api/chat")
        self.assertEqual(captured["body"]["model"], "llama3.2")
        self.assertFalse(captured["body"]["stream"])

    def test_call_ollama_reports_connection_error(self) -> None:
        def fake_urlopen(_request: object, timeout: int) -> object:
            raise OSError("connection refused")

        with patch("urllib.request.urlopen", fake_urlopen):
            with self.assertRaisesRegex(RuntimeError, "Could not reach Ollama"):
                call_ollama("prompt", "system", "llama3.2", 0.1)

    def test_call_ollama_reports_http_error(self) -> None:
        def fake_urlopen(_request: object, timeout: int) -> object:
            raise __import__("urllib.error").error.HTTPError(
                url="http://localhost:11434/api/chat",
                code=404,
                msg="Not Found",
                hdrs=None,
                fp=io.BytesIO(b'{"error":"model not found"}'),
            )

        with patch("urllib.request.urlopen", fake_urlopen):
            with self.assertRaisesRegex(RuntimeError, "model not found"):
                call_ollama("prompt", "system", "missing-model", 0.1)


if __name__ == "__main__":
    unittest.main()
