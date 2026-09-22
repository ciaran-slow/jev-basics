"""Experiment 2: Jev triage hints for jobfinder's prospect review queue.

One Choice question per prospect suggests promote / watch / drop / unknown.
Code turns the answers into badges and a queue order. Nothing changes a
prospect's status: the hint is advice, and the decision stays with me.
"""

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from jev_client import JevError, api_key, call, validate_choices  # noqa: E402


HERE = Path(__file__).parent
CASES = json.loads((HERE / "cases.json").read_text())
EXPECTED = json.loads((HERE / "expected.json").read_text())
RESULTS = HERE / "results"

# Sent with every prospect so Jev knows what "worth it" means for me.
LOOKING_FOR = (
    "A first junior or graduate software developer role. Wellington, New Zealand "
    "(hybrid or on-site) or remote within New Zealand. Mentorship matters. "
    "Not interested in senior roles, support, data engineering or testing-only roles, "
    "or roles that need relocating overseas."
)

# Each version is a full question set. Add a new version rather than editing an
# old one, so earlier results stay reproducible.
QUESTION_VERSIONS = {
    "v1": {
        "triage": {
            "type": "choice",
            "instructions": "Compare prospect with looking_for. What should happen to this prospect next?",
            "criteria": {
                "promote": "There is, or will soon be, a specific role that fits looking_for. It is worth turning into an opportunity now.",
                "watch": "It could fit looking_for later, but there is no suitable role to act on yet, or the evidence is second-hand or uncertain.",
                "drop": "The prospect clearly does not fit looking_for, for example a senior role, a non-development role, or a location that is ruled out.",
                "unknown": "There is not enough information in prospect to judge the fit.",
            },
        }
    },
    # v2: after v1, stop promote and watch overlapping on "a role is coming soon".
    "v2": {
        "triage": {
            "type": "choice",
            "instructions": "Compare prospect with looking_for. What should happen to this prospect next?",
            "criteria": {
                "promote": "A specific role that fits looking_for exists now, or a first-hand source (someone at the company, or the company itself) confirms one is opening soon. It is worth turning into an opportunity now.",
                "watch": "It could fit looking_for, but no fitting role is confirmed: the signal is second-hand, vague, contradictory or about the future.",
                "drop": "The prospect clearly does not fit looking_for, for example a senior role, a non-development role, or a location that is ruled out.",
                "unknown": "There is not enough information in prospect to judge the fit.",
            },
        }
    },
}

# What ordinary code does with each hint. Jev never sees this.
BADGES = {
    "promote": "look at first",
    "watch": "check back later",
    "unknown": "needs digging",
    "drop": "probably drop",
}
QUEUE_ORDER = ["promote", "watch", "unknown", "drop"]

# Below this confidence the top choice is close to a guess, so don't show its
# badge as if it were a recommendation.
UNSURE_BELOW = 0.5
UNSURE_BADGE = "unsure: look yourself"


def badge(answer, unsure_below):
    if answer["confidence"] < unsure_below:
        return UNSURE_BADGE
    return BADGES[answer["choice"]]


def sort_key(answer, sort):
    """v1 grouped by choice, then confidence. But confidence is how sure Jev is
    of the category, not how promising the prospect is, so v2 sorts by the
    probability of promote, then watch."""
    if sort == "confidence":
        return (QUEUE_ORDER.index(answer["choice"]), -answer["confidence"])
    p = answer["probabilities"]
    return (-p["promote"], -p["watch"], p["drop"])


def state_for(case):
    return {"looking_for": LOOKING_FOR, "prospect": case["prospect"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--live", action="store_true",
                      help=f"Make one paid request per case ({len(CASES)} requests)")
    mode.add_argument("--replay", type=Path, help="Show a saved results file without calling Jev")
    parser.add_argument("--version", choices=QUESTION_VERSIONS, default="v2")
    parser.add_argument("--sort", choices=["promise", "confidence"], default="promise",
                        help="Queue order: promise (v2, default) or confidence (v1). Code only, no request")
    parser.add_argument("--unsure-below", type=float, default=UNSURE_BELOW,
                        help="Show an 'unsure' badge below this confidence (0 disables, as in v1)")
    args = parser.parse_args()

    if args.replay:
        run = json.loads(args.replay.read_text())
        print(f"OFFLINE REPLAY of {args.replay.name} (recorded, not a fresh prediction)")
    else:
        try:
            key = api_key()
        except JevError as error:
            sys.exit(str(error))
        run = live_run(key, args.version)
    show(run, args.sort, args.unsure_below)


def live_run(key, version):
    questions = QUESTION_VERSIONS[version]
    started = datetime.now().isoformat(timespec="seconds")
    records = []
    for case in CASES:
        record = {"id": case["id"], "expected": EXPECTED[version].get(case["id"])}
        try:
            payload, data, elapsed = call(key, state_for(case), questions)
            record.update(request=payload, response=data, elapsed_seconds=elapsed)
            validate_choices(data, questions)
            record["choice"] = data["answers"]["triage"]["choice"]
        except JevError as error:
            # Keep going so one failure is visible without losing the other cases.
            record["error"] = str(error)
        records.append(record)
        print(f"  {case['id']}: {record.get('choice', record.get('error'))}", file=sys.stderr)

    run = {"mode": "live", "version": version, "started": started, "cases": records}
    RESULTS.mkdir(exist_ok=True)
    path = RESULTS / f"{version}-{started.replace(':', '')}.json"
    with path.open("x") as handle:
        json.dump(run, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    print(f"LIVE RUN ({version}), saved to {path.relative_to(HERE)}")
    return run


def show(run, sort, unsure_below):
    rows = []
    answered = []
    matches = 0
    for record in run["cases"]:
        if "error" in record:
            rows.append((record["id"], record["expected"], "ERROR", "", "", record["error"]))
            continue
        answer = record["response"]["answers"]["triage"]
        answered.append((record["id"], answer))
        ok = answer["choice"] == record["expected"]
        matches += ok
        spread = " ".join(f"{k}={v:g}" for k, v in sorted(
            answer["probabilities"].items(), key=lambda item: -item[1]) if v)
        rows.append((record["id"], record["expected"], answer["choice"],
                     f"{answer['confidence']:g}", "yes" if ok else "NO", spread))

    headers = ("case", "expected", "jev", "conf", "match", "probabilities")
    print_table(headers, rows)
    print(f"\n{matches}/{len(run['cases'])} matched expected ({run['version']}, {run['mode']})")

    # The queue as the Queue page would show it.
    print(f"\nSuggested queue order (sort={sort}, unsure below {unsure_below:g}; "
          "hints only, no status is changed):")
    answered.sort(key=lambda item: sort_key(item[1], sort))
    for position, (case_id, answer) in enumerate(answered, 1):
        p = answer["probabilities"]
        print(f"  {position:>2}. {case_id:<16} [{badge(answer, unsure_below)}, {answer['confidence']:.0%}]"
              f"  promote {p['promote']:g}, watch {p['watch']:g}")
    # A failed request must not make a prospect vanish from the queue.
    for record in run["cases"]:
        if "error" in record:
            print(f"   -. {record['id']:<16} [no hint: request failed]")


def print_table(headers, rows):
    widths = [max(len(str(row[i])) for row in rows + [headers]) for i in range(5)]
    for row in [headers] + rows:
        print("  ".join(str(cell).ljust(width) for cell, width in zip(row, widths)) + "  " + row[5])


if __name__ == "__main__":
    main()
