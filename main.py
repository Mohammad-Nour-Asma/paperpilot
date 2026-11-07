"""CLI for PaperPilot. Run:  uv run main.py"""

from agent import Agent
from llm import MODEL


def main() -> None:
    agent = Agent()
    print(f"PaperPilot (model: {MODEL}). Type 'exit' to stop.\n")
    while True:
        try:
            user_text = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if user_text.lower() in {"exit", "quit"}:
            break
        if not user_text:
            continue
        answer = agent.run(user_text)
        print(f"\npaperpilot> {answer}\n")


if __name__ == "__main__":
    main()
