"""Text input security validation for the Private Reading web interface.

Adapted from StrategicKnowledgeEngine/src/content_sanitizer.py. Tuned for
TTS use: URLs and code snippets are legitimate reading material and are not
flagged, but prompt-injection command patterns are blocked.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class TextCheckResult:
    """Result of a text safety check."""

    is_safe: bool
    risk_level: str
    warnings: list[str] = field(default_factory=list)


_INJECTION_PATTERNS: list[str] = [
    # Instruction-override commands
    r"(?i)(ignore|forget|disregard|clear|reset)\s+(all\s+)?(previous|prior|above|earlier|my|your)\s+(instructions?|prompts?|commands?|context|rules?|system)",
    # Role-reassignment commands
    r"(?i)(you\s+are\s+now|act\s+as|pretend\s+(to\s+be)?|become|simulate|roleplay\s+as)\s+(a\s+|an\s+)?(jailbroken|unfiltered|unrestricted|uncensored|evil|malicious)",
    # Known jailbreak keywords
    r"(?i)\b(jailbreak|do\s+anything\s+now)\b",
    # Temporal override commands
    r"(?i)\b(from\s+now\s+on|starting\s+(now|immediately)|henceforth)\b",
    # Security bypass commands
    r"(?i)(override|bypass|circumvent|disable)\s+(security|filter|restriction|validation|safety)",
    # Structural injection delimiters used in LLM prompts
    r"(?i)(\[SYSTEM\]|\[INST\]|\[ADMIN\]|<\|system\|>|<\|user\|>|<\|assistant\|>)",
    # Encoding-based obfuscation attacks
    r"(?i)(base64|rot13)\s+(decode|encode|translate|convert)",
]

_ZERO_WIDTH_RE = re.compile(r"[​-‍﻿⁠᠎]")

_MAX_CHARS = 100_000
_REPETITION_THRESHOLD = 0.15
_REPETITION_MIN_WORDS = 50


def check_text(text: str) -> TextCheckResult:
    """Check user-submitted text for prompt injection and DoS patterns.

    Args:
        text: Raw text submitted via the web form.

    Returns:
        TextCheckResult with safety verdict and human-readable warnings.
    """
    if len(text) > _MAX_CHARS:
        return TextCheckResult(
            is_safe=False,
            risk_level="high",
            warnings=[f"Text exceeds {_MAX_CHARS:,} character limit ({len(text):,} characters)."],
        )

    if _ZERO_WIDTH_RE.search(text):
        return TextCheckResult(
            is_safe=False,
            risk_level="critical",
            warnings=["Text contains hidden zero-width characters, which may indicate an injection attempt."],
        )

    for pattern in _INJECTION_PATTERNS:
        if re.search(pattern, text):
            return TextCheckResult(
                is_safe=False,
                risk_level="critical",
                warnings=["Text contains a prompt-injection pattern and cannot be processed."],
            )

    words = text.split()
    if len(words) >= _REPETITION_MIN_WORDS:
        unique_ratio = len(set(words)) / len(words)
        if unique_ratio < _REPETITION_THRESHOLD:
            return TextCheckResult(
                is_safe=False,
                risk_level="high",
                warnings=["Text contains excessive word repetition and cannot be processed."],
            )

    return TextCheckResult(is_safe=True, risk_level="low")
