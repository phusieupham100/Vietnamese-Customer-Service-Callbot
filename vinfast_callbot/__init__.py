"""Development shim for running `python -m vinfast_callbot.cli` from the repo root.

The actual package lives in `src/vinfast_callbot`, matching the architecture
document. This shim keeps the requested command runnable before installation.
"""

from pathlib import Path

_SRC_PACKAGE = Path(__file__).resolve().parent.parent / "src" / "vinfast_callbot"

if _SRC_PACKAGE.exists():
    __path__.append(str(_SRC_PACKAGE))  # type: ignore[name-defined]

