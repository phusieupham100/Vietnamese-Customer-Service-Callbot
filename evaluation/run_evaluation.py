"""Evaluation runner for the Dialogue Engine.

This runner executes JSON scenarios through `DialogueOrchestrator`, records the
actual per-turn outputs, computes metrics from those outputs, and writes both
`results.json` and a Markdown report.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from time import perf_counter
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from evaluation.metrics import evaluate_results
from evaluation.report_generator import generate_markdown_report
from vinfast_callbot.dialogue import DialogueOrchestrator
from vinfast_callbot.models import DialogueInput


def configure_console_encoding() -> None:
    """Prefer UTF-8 output for Vietnamese text on Windows consoles."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def load_scenarios(path: Path) -> list[dict[str, Any]]:
    """Load evaluation scenarios from JSON."""
    return json.loads(path.read_text(encoding="utf-8"))


def run_scenario(scenario: dict[str, Any]) -> dict[str, Any]:
    """Run one scenario with a fresh orchestrator state."""
    engine = DialogueOrchestrator()
    scenario_id = str(scenario["id"])
    initial_state = dict(scenario.get("initial_state", {}))
    if initial_state:
        initial_state.setdefault("session_id", scenario_id)

    turn_results: list[dict[str, Any]] = []
    use_initial_state = bool(initial_state)
    for index, turn in enumerate(scenario.get("turns", [])):
        metadata = {"is_final_transcript": True, "event_type": "user_utterance"}
        metadata.update(turn.get("metadata", {}))
        start = perf_counter()
        output = engine.handle(
            DialogueInput(
                session_id=scenario_id,
                turn_id=index + 1,
                transcript=str(turn.get("user", "")),
                input_mode="transcript",
                history=[],
                state=initial_state if use_initial_state else {},
                metadata=metadata,
            )
        )
        elapsed_ms = (perf_counter() - start) * 1000.0
        use_initial_state = False
        actual = output.to_dict()
        turn_results.append(
            {
                "turn_index": index,
                "user": turn.get("user", ""),
                "expected": turn.get("expected", {}),
                "actual": actual,
                "latency_ms": round(elapsed_ms, 3),
            }
        )

    final_actual = turn_results[-1]["actual"] if turn_results else {}
    return {
        "id": scenario_id,
        "description": scenario.get("description", ""),
        "tags": list(scenario.get("tags", [])),
        "final_expected": scenario.get("final_expected", {}),
        "turns": turn_results,
        "final_actual": final_actual,
    }


def run(
    scenarios_path: Path | None = None,
    results_path: Path | None = None,
    report_path: Path | None = None,
) -> dict[str, Any]:
    """Run all scenarios and persist results/report."""
    scenarios_path = scenarios_path or Path(__file__).with_name("scenarios.json")
    results_path = results_path or Path(__file__).with_name("results.json")
    report_path = report_path or Path(__file__).with_name("report.md")

    scenarios = load_scenarios(scenarios_path)
    scenario_results = [run_scenario(scenario) for scenario in scenarios]
    evaluation = evaluate_results(scenarios, scenario_results)
    payload = {
        "status": "complete",
        "scenario_count": len(scenarios),
        "turn_count": sum(len(result["turns"]) for result in scenario_results),
        "metrics": evaluation["metrics"],
        "failure_details": evaluation["failure_details"],
        "scenario_results": scenario_results,
    }
    results_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path.write_text(generate_markdown_report(payload), encoding="utf-8")
    return payload


if __name__ == "__main__":
    configure_console_encoding()
    print(json.dumps(run(), ensure_ascii=False, indent=2))
