from __future__ import annotations

import json

from llm import chat
from tools import TOOLS, TOOL_SCHEMAS


SYSTEM_PROMPT = """You are PaperPilot, a research assistant for AI papers on arXiv.
Use the tools to find real papers. Do not invent papers, ids, or authors.
Always give the arXiv id when you mention a paper.
If a tool returns an error, read it and try to fix the problem, or explain it to the user.
Keep answers short and clear."""


class Agent:
    def __init__(self):
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    def run(self, prompt: str) -> str:
        """Send one prompt to the local LLM and return its answer text."""
        # 1. Add the prompt to the history
        self.messages.append({"role": "user", "content": prompt})

        # 2. Send the whole history to the local LLM (Ollama)
        message, usage = chat(self.messages)
        print(f"[tokens] {usage.total_tokens}")

        # 3. Add the model's reply to the history so it remembers it next turn
        self.messages.append(message.model_dump(exclude_none=True))

        # 4. Return the answer text
        return message.content or ""
