"""One Jev request against fictional text, or replay a saved response offline."""

import argparse
import json
import os
from pathlib import Path
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ENDPOINT = "https://openrouter.ai/api/v1/systemone"
MODEL = "typesafe/jev-1.13"
ENV_FILE = Path(__file__).with_name(".env")
STATE = "Graduate developer. Weekly 1:1 mentoring with a senior engineer. Based in our Sydney office."
QUESTIONS = {
    "remote_nz": {
        "type": "choice",
        "instructions": "Does the listing explicitly allow remote work from New Zealand?",
        "criteria": {
            "yes": "Explicitly allows remote work from New Zealand.",
            "no": "Explicitly requires on-site work or excludes remote work from New Zealand.",
            "unknown": "The location or remote-work eligibility is not established.",
        },
    },
    "mentoring": {
        "type": "choice",
        "instructions": "Does the listing explicitly promise scheduled mentoring by a senior developer?",
        "criteria": {
            "yes": "Scheduled mentoring by a senior developer is explicitly promised.",
            "no": "The listing explicitly says this mentoring is unavailable.",
            "unknown": "Not established. A supportive team alone does not establish scheduled mentoring.",
        },
    },
}


def load_env(path):
    """Read KEY=value lines into os.environ without replacing shell values."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.removeprefix("export ").split("=", 1)
        os.environ.setdefault(name.strip(), value.strip().strip("\"'"))


def validate_response(data):
    """Validate the fields used by this demo, not the full provider schema."""
    if not isinstance(data, dict) or not isinstance(data.get("answers"), dict):
        raise ValueError("Response has no answers object")
    for name, question in QUESTIONS.items():
        answer = data["answers"].get(name)
        options = set(question["criteria"])
        if not isinstance(answer, dict) or answer.get("choice") not in options:
            raise ValueError(f"Invalid choice for {name}")
        confidence = answer.get("confidence")
        if type(confidence) not in (int, float) or not 0 <= confidence <= 1:
            raise ValueError(f"Invalid confidence for {name}")
        probabilities = answer.get("probabilities")
        if not isinstance(probabilities, dict) or set(probabilities) != options:
            raise ValueError(f"Invalid probability keys for {name}")
        if any(type(p) not in (int, float) or not 0 <= p <= 1 for p in probabilities.values()):
            raise ValueError(f"Invalid probabilities for {name}")
        if abs(sum(probabilities.values()) - 1) > 0.02:
            raise ValueError(f"Probabilities do not sum to one for {name}")
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--live", action="store_true", help="Make one paid API request")
    mode.add_argument("--replay", type=Path, help="Read a saved response without calling Jev")
    parser.add_argument("--output", type=Path, help="Save the record to a new JSON file")
    args = parser.parse_args()
    if args.output and args.output.exists():
        parser.error("Output file exists; choose a new filename")

    if args.live:
        load_env(ENV_FILE)
        key = os.environ.get("OPENROUTER_API_KEY")
        if not key:
            parser.error(f"Set OPENROUTER_API_KEY in {ENV_FILE.name} or this shell")
        payload = {"model": MODEL, "state": STATE, "questions": QUESTIONS}
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
            sys.exit(f"Jev returned HTTP {error.code}; no automatic retry")
        except (URLError, TimeoutError):
            sys.exit("Jev request failed or timed out; no automatic retry")
        record = {"mode": "live", "request": payload, "response": data,
                  "elapsed_seconds": round(time.monotonic() - started, 3)}
    else:
        record = json.loads(args.replay.read_text())
        data = record["response"]

    # Preserve returned data even if local validation fails.
    if args.output:
        with args.output.open("x") as handle:
            json.dump(record, handle, indent=2)
            handle.write("\n")
    try:
        validate_response(data)
    except ValueError as error:
        sys.exit(str(error))
    print("LIVE REQUEST" if args.live else "OFFLINE REPLAY (not a fresh prediction)")
    print(json.dumps(data, indent=2))
    print(f"Recorded client elapsed time: {record.get('elapsed_seconds', 'unknown')} seconds")


if __name__ == "__main__":
    main()
