import re
from pathlib import Path

RUNBOOK_PATH = Path("data/runbooks/payment_incidents.txt")


def _sections(text: str) -> list[str]:
    return [
        section.strip()
        for section in re.split(r"\n(?=[A-Z][A-Z0-9 _-]+\n)", text)
        if section.strip()
    ]


def search_knowledge(query: str) -> str:
    if not RUNBOOK_PATH.exists():
        return ""

    text = RUNBOOK_PATH.read_text(encoding="utf-8")
    sections = _sections(text)
    if not sections:
        return ""

    query_words = {
        word.lower()
        for word in re.findall(r"[A-Za-z][A-Za-z0-9_-]+", query)
        if len(word) > 2
    }

    def score(section: str) -> int:
        normalized = section.lower()
        return sum(1 for word in query_words if word in normalized)

    best = max(sections, key=score)
    return best if score(best) > 0 else ""
