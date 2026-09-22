"""Experiment 1: a Jev scope gate that runs before jobfinder's grader.

One Choice question per listing decides whether the grader should run at all.
Code, not Jev, turns the answer into an action.
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

# Skipping the grader hides a listing, so only skip when Jev is this sure.
# Wrongly grading costs one call; wrongly skipping loses a job.
SKIP_THRESHOLD = 0.9

# Each version is a full question set. Add a new version rather than editing an
# old one, so earlier results stay reproducible.
QUESTION_VERSIONS = {
    # v1: jobfinder's scope rule (docs/grading-criteria.md), close to word for word.
    "v1": {
        "scope": {
            "type": "choice",
            "instructions": "Is this listing a software development role?",
            "criteria": {
                "software": "A role whose main work is writing software. This includes roles whose title says AI, automation, integration or platform when writing code is the main work.",
                "not_software": "A role whose main work is not writing software, such as technical support, data engineering, machine learning research, firmware, testing only or project management.",
                "not_a_role": "The page is not a specific role, such as an expression of interest or a careers page with no position.",
                "unknown": "It is a role, but the text does not establish what the main work is.",
            },
        }
    },
    # v2: after v1, widen unknown to cover title-only listings and mixed duties.
    "v2": {
        "scope": {
            "type": "choice",
            "instructions": "Is this listing a software development role?",
            "criteria": {
                "software": "A role whose main work is writing software. This includes roles whose title says AI, automation, integration or platform when writing code is the main work.",
                "not_software": "A role whose main work is not writing software, such as technical support, data engineering, machine learning research, firmware, testing only or project management.",
                "not_a_role": "The page is not a specific role, such as an expression of interest or a careers page with no position.",
                "unknown": "It is a role, but the text does not establish the main work, such as a title with no description, or a mix of duties where coding may or may not be the main part.",
            },
        }
    },
}

# What ordinary code does with the answer. Jev never sees this.
ACTIONS = {
    "software": "grade normally",
    "not_software": "skip grader; score 1, 'not a software development role'",
    "not_a_role": "skip grader; score 1, every criterion unknown",
    "unknown": "grade normally, flag for review",
}
SKIPS = {"not_software", "not_a_role"}


def action(answer, threshold):
    """Turn a scope answer into what the app would do."""
    if answer["choice"] in SKIPS and answer["confidence"] < threshold:
        return f"grade normally, flag for review (conf < {threshold:g})"
    return ACTIONS[answer["choice"]]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--live", action="store_true",
                      help=f"Make one paid request per case ({len(CASES)} requests)")
    mode.add_argument("--replay", type=Path, help="Show a saved results file without calling Jev")
    parser.add_argument("--version", choices=QUESTION_VERSIONS, default="v2")
    parser.add_argument("--threshold", type=float, default=SKIP_THRESHOLD,
                        help="Minimum confidence to skip the grader (0 disables; code only, no request)")
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
    show(run, args.threshold)


def live_run(key, version):
    questions = QUESTION_VERSIONS[version]
    started = datetime.now().isoformat(timespec="seconds")
    records = []
    for case in CASES:
        record = {"id": case["id"], "expected": EXPECTED[version].get(case["id"])}
        try:
            payload, data, elapsed = call(key, case["listing"], questions)
            record.update(request=payload, response=data, elapsed_seconds=elapsed)
            validate_choices(data, questions)
            record["choice"] = data["answers"]["scope"]["choice"]
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


def show(run, threshold):
    rows = []
    matches = 0
    for record in run["cases"]:
        if "error" in record:
            rows.append((record["id"], record["expected"], "ERROR", "", "", record["error"]))
            continue
        answer = record["response"]["answers"]["scope"]
        ok = answer["choice"] == record["expected"]
        matches += ok
        spread = " ".join(f"{k}={v:g}" for k, v in sorted(
            answer["probabilities"].items(), key=lambda item: -item[1]) if v)
        rows.append((record["id"], record["expected"], answer["choice"],
                     f"{answer['confidence']:g}", "yes" if ok else "NO",
                     f"{spread} -> {action(answer, threshold)}"))

    headers = ("case", "expected", "jev", "conf", "match", "probabilities -> action")
    widths = [max(len(str(row[i])) for row in rows + [headers]) for i in range(5)]
    for row in [headers] + rows:
        print("  ".join(str(cell).ljust(width) for cell, width in zip(row, widths)) + "  " + row[5])
    print(f"\n{matches}/{len(run['cases'])} matched expected ({run['version']}, {run['mode']}, "
          f"skip threshold {threshold:g})")


if __name__ == "__main__":
    main()
