"""Record the stars that the user gives to a response, without any prompt or response text."""

import json
from datetime import UTC, datetime
from pathlib import Path

from pii_anonymizer.engine import MODEL

# shortcut: a local file in the current folder, replace it when monitoring (Sentry) is set up
FEEDBACK_FILE = Path("feedback.jsonl")


def save_feedback(
    response_id: str, stars: int, pseudonymization_seconds: float, response_seconds: float
) -> None:
    """Add one line. If the user changes a rating, the last line of a response_id counts."""
    record = {
        "time": datetime.now(UTC).isoformat(timespec="seconds"),
        "response_id": response_id,
        "stars": stars,
        "model": MODEL,
        "pseudonymization_seconds": round(pseudonymization_seconds, 2),
        "response_seconds": round(response_seconds, 2),
    }
    with FEEDBACK_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record) + "\n")
