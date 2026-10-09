"""Loads the business facts the agent is allowed to use."""

import re
from pathlib import Path

_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)


def load_business_facts(knowledge_dir: Path) -> str:
    text = (knowledge_dir / "business.md").read_text(encoding="utf-8")
    return _COMMENT.sub("", text).strip()
