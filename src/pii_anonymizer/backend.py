"""Backend API. It receives pseudonymized content from the app and returns the LLM's response.

Start it with: PII_BACKEND_TOKEN=... uv run python -m pii_anonymizer.backend

The LLM is any endpoint that speaks the OpenAI-compatible Chat Completions API. LLM_BASE_URL,
LLM_MODEL and LLM_API_KEY choose it. By default it is the local Ollama, so nothing leaves the
machine and nothing is paid.

It never logs a prompt or a response: only uvicorn's access line (method, path, status).
"""

import json
import os
import secrets
import urllib.request

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "http://127.0.0.1:11434/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "qwen3:4b")
# A secret saved with a trailing newline would make an invalid header.
LLM_API_KEY = os.environ.get("LLM_API_KEY", "").strip()

# Ollama's OpenAI-compatible endpoint ignores num_ctx and cuts what exceeds the server's
# context without any error, so Ollama must run with OLLAMA_CONTEXT_LENGTH=16384 (README).
# Measured: 1.4 characters per token on text full of placeholders, 3.2 on French. This limit
# leaves about 6000 of those tokens for the reasoning of the model and its response.
MAX_ANSWER_CHARS = 14000

ANSWER_PROMPT = """Answer the request of the user. Placeholders such as <PERSON_1> hide personal \
data: keep them exactly as they are in your answer, and never invent a value for them. Answer in \
the language of the user."""

# urllib follows the proxy of the system, and the content must not go through a proxy.
_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

app = FastAPI(title="PII anonymizer backend")


class ContentTooLong(Exception):
    """The content does not fit in the LLM's context. Its message holds counts, never content."""


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


def ask_llm(text: str) -> str:
    """Return the LLM's response to pseudonymized content.

    Raises ContentTooLong if the text is too long, OSError if the LLM cannot answer.
    """
    if len(text) > MAX_ANSWER_CHARS:
        raise ContentTooLong(
            f"The content is too long ({len(text)} of {MAX_ANSWER_CHARS} characters)."
        )
    body = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": ANSWER_PROMPT},
            {"role": "user", "content": text},
        ],
    }
    headers = {"Content-Type": "application/json"}
    if LLM_API_KEY:
        headers["Authorization"] = f"Bearer {LLM_API_KEY}"
    request = urllib.request.Request(
        f"{LLM_BASE_URL.rstrip('/')}/chat/completions", json.dumps(body).encode(), headers
    )
    with _opener.open(request, timeout=300) as response:
        data = response.read()
    # A reasoning model such as qwen3 puts its reasoning in a separate field, not in content.
    try:
        content = json.loads(data)["choices"][0]["message"]["content"]
    except (ValueError, LookupError, TypeError):
        content = None
    if not isinstance(content, str):
        raise OSError("The LLM sent no response text.")
    return content


@app.post("/answer")
def answer(prompt: Prompt, authorization: str | None = Header(None)) -> Answer:
    """Return the response to pseudonymized content, with its placeholders unchanged."""
    _check_token(authorization)
    try:
        return Answer(response=ask_llm(prompt.text))
    except ContentTooLong as error:  # the message holds counts, never content
        raise HTTPException(413, str(error)) from None
    except Exception:
        # Any other message may hold the API key (an invalid header) or content, so the app and
        # the logs only ever get this fixed text.
        raise HTTPException(502, "The LLM could not answer.") from None


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("PII_BACKEND_PORT", "8000")))
