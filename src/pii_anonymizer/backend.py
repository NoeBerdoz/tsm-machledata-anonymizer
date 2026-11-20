"""Backend API. It receives pseudonymized content from the app and returns the LLM's response.

Start it with: PII_BACKEND_TOKEN=... uv run python -m pii_anonymizer.backend

It never logs a prompt or a response: only uvicorn's access line (method, path, status).
"""

import os
import secrets

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from pii_anonymizer import engine

app = FastAPI(title="PII anonymizer backend")


class Prompt(BaseModel):
    text: str


class Answer(BaseModel):
    response: str


def _check_token(authorization: str | None) -> None:
    """Refuse the request unless it carries the shared token. Without a configured token,
    every request is refused."""
    token = os.environ.get("PII_BACKEND_TOKEN", "")
    given, expected = (authorization or "").encode(), f"Bearer {token}".encode()
    if not token or not secrets.compare_digest(given, expected):
        raise HTTPException(401, "Missing or wrong token.")


@app.post("/answer")
def answer(prompt: Prompt, authorization: str | None = Header(None)) -> Answer:
    """Return the response to pseudonymized content, with its placeholders unchanged."""
    _check_token(authorization)
    try:
        # shortcut: Ollama (qwen3:4b) answers instead of the OpenAI Responses API, swap it here
        # when the group has an API key; the key then stays on this side only.
        return Answer(response=engine.answer(prompt.text))
    except ValueError as error:  # too long: the message holds counts, never content
        raise HTTPException(413, str(error)) from None
    except OSError:
        raise HTTPException(502, "The LLM could not answer.") from None


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("PII_BACKEND_PORT", "8000")))
