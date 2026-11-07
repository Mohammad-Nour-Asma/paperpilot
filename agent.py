from __future__ import annotations

import json

from llm import chat
from tools import TOOLS, TOOL_SCHEMAS


SYSTEM_PROMPT = """You are PaperPilot, a research assistant for AI papers on arXiv.
Use the tools to find real papers. Do not invent papers, ids, or authors.
Always give the arXiv id when you mention a paper.
If a tool returns an error, read it and try to fix the problem, or explain it to the user.
Keep answers short and clear."""

MAX_STEPS = 6


class Agent:
    def __init__(self):
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    def run(self, prompt: str) -> str:
        """Send one prompt to the local LLM and return its answer text."""

        # 1. Add the prompt to the history
        self.messages.append({"role": "user", "content": prompt})

        for step in range(MAX_STEPS):
            message, usage = chat(self.messages, tools=TOOL_SCHEMAS)

            # 3. Add the model's reply to the history so it remembers it next turn
            self.messages.append(message.model_dump(exclude_none=True))

            print(f"[tokens] {usage.total_tokens}")

            if not message.tool_calls:
                return message.content or ""
            for tool_call in message.tool_calls:
                tool_result = self._run_tool(
                    tool_call.function.name, tool_call.function.arguments
                )
                self.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": tool_result,
                    }
                )
        return f"I stopped because I reached the limit of {MAX_STEPS} steps. Please make the request simpler."

    def _run_tool(self, name: str, arguments_json: str) -> str:
        """Call a tool and return its result."""
        # 1. Get the function from the TOOLS dict in tools.py
        tool_function = TOOLS.get(name)
        if tool_function is None:
            return f"ERROR: unknown tool '{name}'. Available tools: {list(TOOLS)}"

        # 2. Turn the JSON string from the LLM into a dict of arguments
        try:
            arguments = json.loads(arguments_json or "{}")
        except json.JSONDecodeError as e:
            return f"ERROR: the arguments are not valid JSON ({e})"

        # 3. Call the function with those arguments
        try:
            result = tool_function(**arguments)
        except Exception as e:
            return f"ERROR: {name} failed: {type(e).__name__}: {e}"

        # 4. Return the result as a string (the LLM only reads text)
        return (
            result
            if isinstance(result, str)
            else json.dumps(result, ensure_ascii=False)
        )
