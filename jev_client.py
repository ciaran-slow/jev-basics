"""Shared Jev calling code for the step 3 experiments (standard library only)."""

import json
import os
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ENDPOINT = "https://openrouter.ai/api/v1/systemone"
MODEL = "typesafe/jev-1.13"
ENV_FILE = Path(__file__).with_name(".env")


class JevError(Exception):
    """A request failed or the reply did not match the questions asked."""


def load_env(path=ENV_FILE):
    """Read KEY=value lines into os.environ without replacing shell values."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.removeprefix("export ").split("=", 1)
        os.environ.setdefault(name.strip(), value.strip().strip("\"'"))


def api_key():
    load_env()
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise JevError(f"Set OPENROUTER_API_KEY in {ENV_FILE.name} or this shell")
    return key


def call(key, state, questions):
    """Make one request. Returns (payload, response, elapsed seconds). No retries."""
    payload = {"model": MODEL, "state": state, "questions": questions}
    request = Request(
        ENDPOINT,
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    started = time.monotonic()
    try:
        with urlopen(request, timeout=30) as response:
            data = json.load(response)
    except HTTPError as error:
        raise JevError(f"Jev returned HTTP {error.code}; no automatic retry") from error
    except (URLError, TimeoutError) as error:
        raise JevError("Jev request failed or timed out; no automatic retry") from error
    return payload, data, round(time.monotonic() - started, 3)


def validate_choices(data, questions):
    """Check each Choice answer against the options that were asked."""
    if not isinstance(data, dict) or not isinstance(data.get("answers"), dict):
        raise JevError("Response has no answers object")
    for name, question in questions.items():
        answer = data["answers"].get(name)
        options = set(question["criteria"])
        if not isinstance(answer, dict) or answer.get("choice") not in options:
            raise JevError(f"Invalid choice for {name}")
        confidence = answer.get("confidence")
        if type(confidence) not in (int, float) or not 0 <= confidence <= 1:
            raise JevError(f"Invalid confidence for {name}")
        probabilities = answer.get("probabilities")
        if not isinstance(probabilities, dict) or set(probabilities) != options:
            raise JevError(f"Invalid probability keys for {name}")
        if any(type(p) not in (int, float) or not 0 <= p <= 1 for p in probabilities.values()):
            raise JevError(f"Invalid probabilities for {name}")
        if abs(sum(probabilities.values()) - 1) > 0.02:
            raise JevError(f"Probabilities do not sum to one for {name}")
    return data
