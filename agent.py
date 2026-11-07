"""The agent loop. YOU write this file (no AI code generation here).

Read Part A5 of README.md first. Then replace each TODO.

Hints (facts about the API, not code):
- chat(self.messages, TOOL_SCHEMAS) returns (message, usage).
- message.tool_calls is None or a list. Each tool call has:
    call.id                   -> a string. You must send it back with the result.
    call.function.name        -> the tool name, for example "get_paper"
    call.function.arguments   -> a JSON STRING. Use json.loads() to get a dict.
- To add the assistant message to the history, use:
    message.model_dump(exclude_none=True)
- A tool result message has this shape:
    {"role": "tool", "tool_call_id": <call.id>, "content": <a string>}
  The content must be a string. Use json.dumps() for lists and dicts.
"""

from __future__ import annotations

import json

from llm import chat
from tools import TOOLS, TOOL_SCHEMAS

MAX_STEPS = 6

SYSTEM_PROMPT = """You are PaperPilot, a research assistant for AI papers on arXiv.
Use the tools to find real papers. Do not invent papers, ids, or authors.
Always give the arXiv id when you mention a paper.
If a tool returns an error, read it and try to fix the problem, or explain it to the user.
Keep answers short and clear."""


class Agent:
    def __init__(self):
        # The history. The LLM has no memory, so we keep all of it here.
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    def run(self, user_text: str) -> str:
        """Run one user turn. Return the final answer text."""
        # TODO 1: Add the user message to self.messages.

        # TODO 2: Loop at most MAX_STEPS times:
        #   a. Call the LLM with the history and the tool schemas.
        #   b. Print the token usage (your simple cost trace).
        #   c. Add the assistant message to the history.
        #   d. If there are no tool calls: return the text. The turn is done.
        #   e. For EACH tool call:
        #        - print the tool name and arguments (your simple trace)
        #        - run the tool with self._run_tool(...)
        #        - add a "tool" message with the result to the history

        # TODO 3: If the loop ends without a final answer, return a clear message
        #         that says the step limit is reached.
        raise NotImplementedError("Write the agent loop")

    def _run_tool(self, name: str, arguments_json: str) -> str:
        """Run one tool. ALWAYS return a string. NEVER raise an exception."""
        # TODO 4: Find the function in TOOLS. Parse the JSON arguments. Call it.
        #         Return the result as a JSON string.
        #         If the tool name is unknown, or the JSON is bad, or the tool fails:
        #         return a string that starts with "ERROR:" and explains the problem.
        raise NotImplementedError("Write the tool runner")
