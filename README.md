# Vietnamese Customer Service Callbot

Repository for a VinFast Vietnamese customer-service callbot. The current
implemented scope is the Dialogue Engine owned by Nguoi 2, plus thin transcript
and pipeline interfaces that Nguoi 1 can integrate with ASR/microphone/TTS.

## Current Implementation

Implemented:

- Category schemas for `G_1` to `G_5`.
- Dialogue contracts, state models, and final JSON helpers.
- Vehicle model catalog, normalizer, matcher, and ASR hotword list.
- LLM-first turn analyzer for semantic intent, emergency, fields, correction, and ambiguity.
- Deterministic validation for phone, VIN/plate, ODO, order code, and vehicle model normalization.
- State updater, no-reask policy, and deterministic action policy.
- Exception handling for the required cases.
- Deterministic Vietnamese response generator.
- Dialogue orchestrator for transcript mode.
- Evaluation scenarios, metrics, runner, results JSON, and Markdown report.
- Thin `CallbotPipeline`, `InputAdapter`, and ASR interface stubs for integration tests.

Required for production transcript CLI:

- An OpenAI API key in `OPENAI_API_KEY`.
- Optional model/config overrides: `VINFAST_OPENAI_MODEL`, `VINFAST_OPENAI_RESPONSES_URL`, `VINFAST_OPENAI_TIMEOUT_SECONDS`.

Example `.env`:

```env
OPENAI_API_KEY=sk-...
VINFAST_OPENAI_MODEL=gpt-4.1
```

Not implemented in this repository yet:

- Real microphone recording.
- Real ASR backend.
- Real TTS backend.
- Production post-call finalization flow inside the runtime orchestrator.

Nguoi 1 should provide concrete ASR/microphone/TTS implementations and call the
Dialogue Engine through `DialogueInput` / `DialogueOutput` or the thin pipeline
wrapper.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

No heavy runtime dependency is required for the Dialogue Engine tests.

## Transcript Demo

Run one transcript turn with analyzer debug log:

```powershell
python -m vinfast_callbot.cli --transcript "Tôi cần cứu hộ xe" --debug-log
```

Run an interactive transcript loop:

```powershell
python -m vinfast_callbot.cli --interactive
```

## Evaluation

```powershell
python evaluation\run_evaluation.py
```

Outputs:

- `evaluation/results.json`
- `evaluation/report.md`

## Tests

```powershell
python -m pytest
```

## Integration Interfaces For Nguoi 1

Primary contract:

- `vinfast_callbot.models.DialogueInput`
- `vinfast_callbot.models.DialogueOutput`
- `vinfast_callbot.dialogue.DialogueOrchestrator.handle(...)`

Thin pipeline wrapper:

- `vinfast_callbot.input_adapter.InputAdapter`
- `vinfast_callbot.asr.ASRResult`
- `vinfast_callbot.asr.ASRAdapter`
- `vinfast_callbot.pipeline.CallbotPipeline`

Voice runtime should send only final transcripts for state updates. Partial
transcripts should use metadata `is_final_transcript=False` and must not commit
fields.
