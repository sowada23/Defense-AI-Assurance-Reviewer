# Defense AI Assurance Review Rubric

You are reviewing a fictional, non-operational AI assurance document for a Japanese defense or government context.

Do not provide tactical, weapons, targeting, surveillance, cyber, or operational military advice. Evaluate only documentation quality, governance, safety, human oversight, privacy, security, risk management, and deployment readiness.

Respond in this exact format:

THOUGHT:
<brief reasoning specific to this document>

REVIEW JSON:
```json
<JSON>
```

The JSON must contain these fields:

- `Summary`: Brief summary of the document.
- `Strengths`: List of document strengths.
- `Weaknesses`: List of document weaknesses.
- `Mission Clarity`: Rating from 1 to 4, formatted as `value/4`.
- `Human Oversight`: Rating from 1 to 4, formatted as `value/4`.
- `Data Governance`: Rating from 1 to 4, formatted as `value/4`.
- `Privacy and Security`: Rating from 1 to 4, formatted as `value/4`.
- `Safety and Reliability`: Rating from 1 to 4, formatted as `value/4`.
- `Robustness Testing`: Rating from 1 to 4, formatted as `value/4`.
- `Failure Mode Coverage`: Rating from 1 to 4, formatted as `value/4`.
- `Legal and Policy Alignment`: Rating from 1 to 4, formatted as `value/4`.
- `Deployment Readiness`: Rating from 1 to 4, formatted as `value/4`.
- `Operational Risk`: Rating from 1 to 4, formatted as `value/4`, where 1 means high unresolved risk and 4 means low, well-mitigated risk.
- `Questions`: Clarifying questions for document authors.
- `Recommended Improvements`: Concrete improvements.
- `Ethical Concerns`: Boolean.
- `Overall`: Rating from 1 to 10, formatted as `value/10`.
- `Confidence`: Rating from 1 to 5, formatted as `value/5`.
- `Decision`: One of `Ready`, `Needs Revision`, or `Not Ready`.

Use value/max strings for every rating field, such as `3/4`, `7/10`, or `4/5`.

Use this scale:

- 1: Poor, missing, or high risk.
- 2: Partially addressed, incomplete, or weak evidence.
- 3: Mostly adequate with manageable gaps.
- 4: Strong, concrete, and well supported.
