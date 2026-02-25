import re
from dataclasses import dataclass, field


@dataclass
class HeuristicResult:
    is_likely_ai: bool
    confidence: float  # 0.0 - 1.0
    reasons: list[str] = field(default_factory=list)


# Commit message heuristics
_MSG_SIGNALS = [
    (re.compile(r"^(feat|fix|refactor|docs|test|chore|style|perf|ci|build)\(.+\):", re.IGNORECASE),
     0.05, "Uses conventional commit format"),
    (re.compile(r"(?:implement|add|create|update|fix|refactor)\s.{20,}", re.IGNORECASE),
     0.05, "Verbose descriptive commit message"),
    (re.compile(r"\n\n[-*]\s", re.MULTILINE),
     0.05, "Bullet-point commit body"),
]

# Diff content heuristics (applied to patch text)
_DIFF_SIGNALS = [
    # Extensive docstrings
    (re.compile(r'"""[\s\S]{50,}?"""'), 0.1, "Comprehensive docstrings added"),
    (re.compile(r"'''[\s\S]{50,}?'''"), 0.1, "Comprehensive docstrings added"),
    # Heavy inline comments
    (re.compile(r"(#\s.+\n){5,}"), 0.1, "Dense inline comments block"),
    # Type hints on every parameter (Python)
    (re.compile(r"def \w+\((?:\w+:\s*\w+,?\s*){4,}\)"), 0.05, "Extensive type annotations"),
    # Try/except with specific exceptions
    (re.compile(r"except\s+\w+Error"), 0.03, "Specific exception handling"),
    # Verbose variable names (camelCase or snake_case 20+ chars)
    (re.compile(r"\b\w{20,}\b"), 0.05, "Very verbose variable names"),
    # JSDoc / TSDoc blocks
    (re.compile(r"/\*\*[\s\S]{80,}?\*/"), 0.1, "Comprehensive JSDoc/TSDoc"),
]

# Threshold for classifying as likely AI
_AI_THRESHOLD = 0.3


def analyze_heuristics(
    commit_message: str, diff_text: str | None = None
) -> HeuristicResult:
    """Analyze commit message and optional diff for AI code patterns.

    Returns a heuristic assessment with confidence score and reasons.
    This is a secondary signal — tag detection always takes priority.
    """
    score = 0.0
    reasons: list[str] = []

    # Analyze commit message
    for pattern, weight, reason in _MSG_SIGNALS:
        if pattern.search(commit_message or ""):
            score += weight
            reasons.append(reason)

    # Analyze diff content if available
    if diff_text:
        code_lines = [
            l for l in diff_text.split("\n")
            if l.startswith("+") and not l.startswith("+++")
        ]
        total_added = len(code_lines)

        if total_added > 0:
            comment_lines = sum(
                1 for l in code_lines
                if re.match(r"^\+\s*(#|//|/\*|\*|<!--)", l)
            )
            comment_ratio = comment_lines / total_added
            if comment_ratio > 0.3:
                score += 0.15
                reasons.append(f"High comment density ({comment_ratio:.0%})")

        for pattern, weight, reason in _DIFF_SIGNALS:
            if pattern.search(diff_text):
                if reason not in reasons:
                    score += weight
                    reasons.append(reason)

    confidence = min(score, 1.0)
    is_likely_ai = confidence >= _AI_THRESHOLD

    return HeuristicResult(
        is_likely_ai=is_likely_ai,
        confidence=round(confidence, 2),
        reasons=reasons,
    )


def classify_commit(
    commit_message: str,
    diff_text: str | None = None,
    tag_classification: str = "human",
    tag_confidence: float = 1.0,
    tag_detected: bool = False,
) -> tuple[str, float, str]:
    """Combine tag detection and heuristic analysis.

    Returns (classification, confidence, detection_method).
    Tag detection takes priority over heuristics.
    """
    if tag_detected:
        heuristic = analyze_heuristics(commit_message, diff_text)
        if heuristic.is_likely_ai:
            return tag_classification, tag_confidence, "both"
        return tag_classification, tag_confidence, "co_author_tag"

    heuristic = analyze_heuristics(commit_message, diff_text)
    if heuristic.is_likely_ai:
        return "ai_other", heuristic.confidence, "heuristic"

    return "human", 1.0 - heuristic.confidence, "none"
