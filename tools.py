"""The 3 tools of PaperPilot Stage 1, plus their JSON schemas for the LLM.

A tool is a normal Python function. The LLM never runs it.
The LLM only asks for it by name; agent.py runs it.
"""

from __future__ import annotations

import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

ARXIV_API = "https://export.arxiv.org/api/query"
NS = {"atom": "http://www.w3.org/2005/Atom"}
NOTES_FILE = Path(__file__).parent / "notes.md"
ARXIV_ID_RE = re.compile(r"^\d{4}\.\d{4,5}(v\d+)?$")


def _fetch_entries(params: dict) -> list[ET.Element]:
    url = f"{ARXIV_API}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=20) as resp:
        root = ET.fromstring(resp.read())
    return root.findall("atom:entry", NS)


def _text(entry: ET.Element, tag: str) -> str:
    node = entry.find(f"atom:{tag}", NS)
    return " ".join(node.text.split()) if node is not None and node.text else ""


def _short_id(entry: ET.Element) -> str:
    # <id>http://arxiv.org/abs/2401.12345v2</id>  ->  2401.12345v2
    return _text(entry, "id").rsplit("/", 1)[-1]


# ---------- tools ----------

def search_arxiv(query: str, max_results: int = 5) -> list[dict]:
    """Search arXiv. Return id, title, authors, and date for each result."""
    max_results = max(1, min(int(max_results), 10))
    entries = _fetch_entries({
        "search_query": f"all:{query}",
        "max_results": max_results,
        "sortBy": "relevance",
    })
    return [
        {
            "arxiv_id": _short_id(e),
            "title": _text(e, "title"),
            "authors": [_text(a, "name") for a in e.findall("atom:author", NS)][:4],
            "published": _text(e, "published")[:10],
        }
        for e in entries
    ]


def get_paper(arxiv_id: str) -> dict:
    """Get the title, abstract, authors, and PDF link of one paper."""
    arxiv_id = arxiv_id.strip()
    if not ARXIV_ID_RE.match(arxiv_id):
        raise ValueError(f"'{arxiv_id}' is not a valid arXiv id. Example of a valid id: 2005.11401")
    entries = _fetch_entries({"id_list": arxiv_id})
    if not entries or not _text(entries[0], "title"):
        raise LookupError(f"No paper found with id {arxiv_id}")
    e = entries[0]
    return {
        "arxiv_id": _short_id(e),
        "title": _text(e, "title"),
        "authors": [_text(a, "name") for a in e.findall("atom:author", NS)],
        "abstract": _text(e, "summary"),
        "pdf_url": f"https://arxiv.org/pdf/{_short_id(e)}",
    }


def save_note(title: str, text: str) -> str:
    """Append a note to notes.md."""
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    with NOTES_FILE.open("a", encoding="utf-8") as f:
        f.write(f"\n## {title}\n_{stamp}_\n\n{text}\n")
    return f"saved to {NOTES_FILE.name}"


# ---------- registry: name -> function ----------

TOOLS = {
    "search_arxiv": search_arxiv,
    "get_paper": get_paper,
    "save_note": save_note,
}

# ---------- schemas: what the LLM sees ----------

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_arxiv",
            "description": "Search arXiv for research papers. Returns id, title, authors, and date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search words, in English."},
                    "max_results": {"type": "integer", "description": "1 to 10. Default 5."},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_paper",
            "description": "Get the abstract, authors, and PDF link of one arXiv paper.",
            "parameters": {
                "type": "object",
                "properties": {
                    "arxiv_id": {"type": "string", "description": "arXiv id, for example 2005.11401"},
                },
                "required": ["arxiv_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_note",
            "description": "Save a short research note for the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "text": {"type": "string", "description": "The note, in markdown."},
                },
                "required": ["title", "text"],
            },
        },
    },
]
