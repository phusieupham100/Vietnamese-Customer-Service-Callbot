"""Transcript-mode CLI for the Dialogue Engine."""

from __future__ import annotations

import argparse
import json
import os
import sys

from .dialogue import DialogueOrchestrator
from .models import DialogueInput


def configure_console_encoding() -> None:
    """Prefer UTF-8 output for Vietnamese text on Windows consoles."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def load_dotenv(path: str = ".env") -> None:
    """Load simple KEY=VALUE lines from .env without adding dependencies."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def run_transcript(transcript: str, session_id: str = "cli-session", *, debug_log: bool = False) -> dict[str, object]:
    """Run one transcript through DialogueOrchestrator and return output dict."""
    engine = DialogueOrchestrator()
    output = engine.handle(
        DialogueInput(
            session_id=session_id,
            turn_id=1,
            transcript=transcript,
            input_mode="transcript",
            metadata={"is_final_transcript": True, "event_type": "user_utterance"},
        )
    )
    if debug_log:
        print(json.dumps(engine.last_turn_log, ensure_ascii=False), file=sys.stderr)
    return output.to_dict()


def run_interactive(session_id: str = "cli-session", *, debug_log: bool = False) -> None:
    """Start a simple transcript chat loop."""
    engine = DialogueOrchestrator()
    turn_id = 1
    while True:
        try:
            transcript = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if transcript.lower() in {"exit", "quit"}:
            break
        output = engine.handle(
            DialogueInput(
                session_id=session_id,
                turn_id=turn_id,
                transcript=transcript,
                input_mode="transcript",
                metadata={"is_final_transcript": True, "event_type": "user_utterance"},
            )
        )
        turn_id += 1
        if debug_log:
            print(json.dumps(engine.last_turn_log, ensure_ascii=False), file=sys.stderr)
        print(output.response_text)


def main() -> None:
    """Parse CLI arguments and run transcript or interactive mode."""
    configure_console_encoding()
    load_dotenv()
    parser = argparse.ArgumentParser(description="VinFast callbot Dialogue Engine CLI")
    parser.add_argument("--transcript", help="Run one transcript turn")
    parser.add_argument("--interactive", action="store_true", help="Start transcript chat loop")
    parser.add_argument("--session-id", default="cli-session")
    parser.add_argument("--debug-log", action="store_true", help="Print internal LLM analyzer log to stderr")
    args = parser.parse_args()

    if args.interactive:
        run_interactive(args.session_id, debug_log=args.debug_log)
        return
    if args.transcript is not None:
        print(json.dumps(run_transcript(args.transcript, args.session_id, debug_log=args.debug_log), ensure_ascii=False, indent=2))
        return
    parser.print_help()


if __name__ == "__main__":
    main()
