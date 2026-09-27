import re
from pathlib import Path

LOG_PATH = Path("data/logs/checkout.log")

GENERIC_WORDS = {
    "a", "an", "and", "are", "for", "from", "in", "incident", "incidents",
    "logs", "log", "messages", "message", "occurred", "of", "related", "the",
    "to", "what", "with", "errors", "error", "failures", "failure", "last",
    "hours", "investigate", "investigation",
}


def normalize_text(text: str) -> str:
    return re.sub(r"[^a-z0-9_-]+", " ", text.lower()).strip()


def extract_useful_terms(query: str) -> list[str]:
    technical_tokens = re.findall(r"[A-Z][A-Za-z0-9]+(?:[A-Z][A-Za-z0-9]+)+", query)
    if technical_tokens:
        # Prefer the longest / most specific technical identifier.
        return [max(technical_tokens, key=len)]

    normalized = normalize_text(query)
    terms = [
        token
        for token in normalized.split()
        if token not in GENERIC_WORDS and len(token) > 2
    ]
    return list(dict.fromkeys(terms))


def search_logs(query: str) -> list[str]:
    if not LOG_PATH.exists():
        return []

    useful_terms = extract_useful_terms(query)
    if not useful_terms:
        return []

    matches = []
    for raw_line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        normalized_line = normalize_text(raw_line)
        if any(normalize_text(term) in normalized_line for term in useful_terms):
            matches.append(raw_line)

    return matches
