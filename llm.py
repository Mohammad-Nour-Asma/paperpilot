"""Thin wrapper around any OpenAI-compatible LLM API.

Only this file knows the provider. To change the provider, change .env.
Works with: Ollama (local, free), OpenRouter, Groq, OpenAI, Gemini, and others.
"""

from __future__ import annotations

import os
import re

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

MODEL = os.getenv("LLM_MODEL", "qwen3:8b")

_client = OpenAI(
    base_url=os.getenv("LLM_BASE_URL", "http://localhost:11434/v1"),
    api_key=os.getenv("LLM_API_KEY", "ollama"),  # Ollama ignores the key, but the SDK needs one.
)

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


def chat(messages: list[dict], tools: list[dict] | None = None, temperature: float = 0.2):
    """Send the full message history (and tool schemas) to the LLM.

    Returns (message, usage):
      message: the assistant message object.
               message.content    -> text (can be None when the model calls tools)
               message.tool_calls -> list of tool calls, or None
      usage:   token counts (prompt_tokens, completion_tokens, total_tokens), or None
    """
    response = _client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=tools or None,
        temperature=temperature,
    )
    message = response.choices[0].message
    # Some local reasoning models put their thinking inside <think> tags. Remove it.
    if message.content:
        message.content = _THINK_RE.sub("", message.content).strip()
    return message, response.usage
