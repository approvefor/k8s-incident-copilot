from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel


RUNBOOK_DIR = Path(__file__).resolve().parent.parent / "runbooks"
TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_-]*", re.IGNORECASE)


class RunbookMatch(BaseModel):
    id: str
    title: str
    path: str
    score: float
    excerpt: str


@dataclass(frozen=True)
class Runbook:
    id: str
    title: str
    path: Path
    content: str


def tokenize(text: str) -> set[str]:
    return {token.lower() for token in TOKEN_RE.findall(text)}


def load_runbooks() -> list[Runbook]:
    if not RUNBOOK_DIR.exists():
        return []

    runbooks: list[Runbook] = []
    for path in sorted(RUNBOOK_DIR.glob("*.md")):
        content = path.read_text(encoding="utf-8")
        title = path.stem.replace("-", " ").title()
        for line in content.splitlines():
            if line.startswith("# "):
                title = line.removeprefix("# ").strip()
                break
        runbooks.append(Runbook(id=path.stem, title=title, path=path, content=content))
    return runbooks


def search_runbooks(query: str, limit: int = 5) -> list[RunbookMatch]:
    query_tokens = tokenize(query)
    if not query_tokens:
        return []

    matches: list[RunbookMatch] = []
    for runbook in load_runbooks():
        content_tokens = tokenize(runbook.content)
        overlap = query_tokens & content_tokens
        if not overlap:
            continue

        score = len(overlap) / max(len(query_tokens), 1)
        excerpt = best_excerpt(runbook.content, overlap)
        matches.append(
            RunbookMatch(
                id=runbook.id,
                title=runbook.title,
                path=str(runbook.path.relative_to(RUNBOOK_DIR.parent)),
                score=round(score, 3),
                excerpt=excerpt,
            )
        )

    return sorted(matches, key=lambda item: item.score, reverse=True)[:limit]


def best_excerpt(content: str, terms: set[str]) -> str:
    paragraphs = [paragraph.strip() for paragraph in content.split("\n\n") if paragraph.strip()]
    if not paragraphs:
        return ""

    ranked = sorted(
        paragraphs,
        key=lambda paragraph: len(tokenize(paragraph) & terms),
        reverse=True,
    )
    excerpt = ranked[0].replace("\n", " ")
    return excerpt[:360]
