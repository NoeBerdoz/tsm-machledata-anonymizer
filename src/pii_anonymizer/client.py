"""Send pseudonymized content to our backend. Only this module talks to it."""

import json
import os
import urllib.request

BACKEND_URL = os.environ.get("PII_BACKEND_URL", "http://127.0.0.1:8000")


def ask_backend(text: str) -> str:
    """Return the backend's response to pseudonymized content.

    Raises OSError if the backend cannot be reached or refuses the request.
    """
    request = urllib.request.Request(
        f"{BACKEND_URL}/answer",
        json.dumps({"text": text}).encode(),
        {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ.get('PII_BACKEND_TOKEN', '')}",
        },
    )
    with urllib.request.urlopen(request, timeout=300) as response:
        return json.load(response)["response"]
