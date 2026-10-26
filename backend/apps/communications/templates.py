"""
Message template rendering.
Substitutes candidate-specific placeholders at send time.
Supported tokens: {{full_name}}, {{name}}, {{candidate_id}}, {{mobile_number}}, {{phone}}, {{email}}
"""

import re
from typing import Any, Dict

PLACEHOLDER_PATTERN = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")

TEMPLATE_PLACEHOLDERS = (
    ("{{full_name}}", "Candidate full name"),
    ("{{candidate_id}}", "Candidate ID"),
    ("{{mobile_number}}", "Mobile number"),
    ("{{email}}", "Email address"),
)


def candidate_placeholder_map(candidate: Any) -> Dict[str, str]:
    email = getattr(candidate, "email", None) or ""
    return {
        "full_name": getattr(candidate, "full_name", "") or "",
        "name": getattr(candidate, "full_name", "") or "",
        "candidate_id": getattr(candidate, "candidate_id", "") or "",
        "mobile_number": getattr(candidate, "mobile_number", "") or "",
        "phone": getattr(candidate, "mobile_number", "") or "",
        "email": email,
    }


def render_message_content(content: str, candidate: Any) -> str:
    """Replace {{placeholders}} with candidate fields. Unknown tokens are left intact."""
    mapping = candidate_placeholder_map(candidate)

    def _replace(match: re.Match) -> str:
        key = (match.group(1) or "").strip().lower()
        if key in mapping:
            return mapping[key]
        return match.group(0)

    return PLACEHOLDER_PATTERN.sub(_replace, content or "")
