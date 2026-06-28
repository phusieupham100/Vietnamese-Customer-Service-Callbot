"""Markdown report generation for dialogue evaluation results."""

from __future__ import annotations

from typing import Any


def generate_markdown_report(results: dict[str, Any]) -> str:
    """Generate a compact Markdown report from evaluation results."""
    lines: list[str] = [
        "# Dialogue Engine Evaluation Report",
        "",
        "## Objective",
        "Evaluate routing, field extraction, dialogue behavior, vehicle model handling, exceptions, and output validity using actual DialogueOrchestrator outputs.",
        "",
        "## Scenario Set",
        f"- Scenarios: {results.get('scenario_count', 0)}",
        f"- Turns: {results.get('turn_count', 0)}",
        "",
        "## Metrics",
    ]
    for group, metrics in results.get("metrics", {}).items():
        lines.append(f"### {group}")
        lines.append("| Metric | Value |")
        lines.append("|---|---:|")
        for name, value in metrics.items():
            lines.append(f"| `{name}` | {_format_value(value)} |")
        lines.append("")

    lines.extend(
        [
            "## Overall Results",
            f"- Failure records: {len(results.get('failure_details', []))}",
            "",
            "## Results By Category",
        ]
    )
    category_counts: dict[str, int] = {}
    for scenario in results.get("scenario_results", []):
        category = scenario.get("final_actual", {}).get("category") or "unresolved"
        category_counts[str(category)] = category_counts.get(str(category), 0) + 1
    for category, count in sorted(category_counts.items()):
        lines.append(f"- {category}: {count}")

    lines.extend(["", "## Exception Results"])
    for scenario in results.get("scenario_results", []):
        if "exception" in scenario.get("tags", []):
            lines.append(f"- `{scenario['id']}`: final action `{scenario.get('final_actual', {}).get('next_action')}`")

    lines.extend(
        [
            "",
            "## Latency Breakdown",
            "Latency is measured per dialogue turn inside the evaluation runner.",
        ]
    )
    latencies = [
        turn["latency_ms"]
        for scenario in results.get("scenario_results", [])
        for turn in scenario.get("turns", [])
    ]
    if latencies:
        lines.append(f"- average_dialogue_turn_ms: {sum(latencies) / len(latencies):.3f}")
        lines.append(f"- max_dialogue_turn_ms: {max(latencies):.3f}")
    else:
        lines.append("- No turns were executed.")

    lines.extend(["", "## Failure Cases"])
    failures = results.get("failure_details", [])
    if not failures:
        lines.append("- No failures recorded.")
    for failure in failures:
        lines.append(
            f"- `{failure['scenario_id']}` turn `{failure['turn_index']}` metric `{failure['metric']}`: "
            f"expected `{failure['expected']}`, actual `{failure['actual']}`"
        )

    lines.extend(
        [
            "",
            "## Limitations",
            "- Metrics are computed from the scenarios in this repository only.",
            "- Post-call JSON completeness is reported as not applicable unless scenarios include post_call expectations.",
            "",
            "## Improvement Plan",
            "- Add more ASR-noise and long multi-turn scenarios.",
            "- Add final post-call JSON evaluation once finalization is wired into the runtime.",
            "",
        ]
    )
    return "\n".join(lines)


def _format_value(value: Any) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)
