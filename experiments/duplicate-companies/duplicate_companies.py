"""Experiment 3: spotting duplicate companies before jobfinder saves one.

Code settles the obvious pairs itself (spelling, capitals, macrons, legal
suffixes) and skips pairs whose names share nothing. Only the near misses go to
Jev, as one Noul question: the probability that the two refer to the same company.
"""

import argparse
from datetime import datetime
from difflib import SequenceMatcher
import json
from pathlib import Path
import re
import sys
import unicodedata

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from jev_client import JevError, api_key, call, validate_nouls  # noqa: E402


HERE = Path(__file__).parent
CASES = json.loads((HERE / "cases.json").read_text())
EXPECTED = json.loads((HERE / "expected.json").read_text())
RESULTS = HERE / "results"

# Each version is a full question set. Add a new version rather than editing an
# old one, so earlier results stay reproducible.
QUESTION_VERSIONS = {
    "v1": {
        "same_company": {
            "type": "noul",
            "instructions": "Do `a` and `b` refer to the same company: the same employer someone would apply to?",
            "criteria": {
                "true": "The same organisation, written differently: another spelling, a shortened name, a legal suffix, or a new name after a rename.",
                "false": "Different organisations, even if the names share words. This includes related but separate companies, such as a parent and a company it owns, or an overseas office that hires separately.",
            },
        }
    },
    # v2: after v1, say how to weigh evidence. v1 put website-backed pairs only
    # just above 0.8, and name-only pairs leaning towards "same".
    "v2": {
        "same_company": {
            "type": "noul",
            "instructions": "Do `a` and `b` refer to the same company: the same employer someone would apply to? Weigh the evidence: the same website, or notes saying one is a former or other name of the other, is strong evidence. Similar names alone are weak evidence either way.",
            "criteria": {
                "true": "The same organisation, written differently: another spelling, a shortened name, a legal suffix, or a new name after a rename.",
                "false": "Different organisations, even if the names share words. This includes related but separate companies, such as a parent and a company it owns, or an overseas office that hires separately.",
            },
        }
    },
}

# Code's own rules, applied before Jev is asked anything.
LEGAL_SUFFIXES = {"ltd", "limited", "inc", "llc", "pty", "co", "company"}
SIMILARITY_TO_ASK = 0.6

# What code does with Jev's probability.
SAME_AT_OR_ABOVE = 0.8
DIFFERENT_AT_OR_BELOW = 0.2
ACTIONS = {
    "same": "warn: likely duplicate",
    "different": "save as a separate company",
    "unsure": "ask me before saving",
}


def normalise(name):
    """Lowercase, strip macrons and punctuation, drop legal suffixes."""
    text = unicodedata.normalize("NFKD", name)
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).lower()
    text = re.sub(r"[^a-z0-9 ]+", " ", text.replace("&", " and "))
    return [word for word in text.split() if word not in LEGAL_SUFFIXES]


def host(url):
    """The website's host without scheme, path or www, e.g. 'fernbird.example'."""
    if not url:
        return None
    return re.sub(r"^(https?://)?(www\.)?", "", url.lower()).split("/")[0]


def mentions(company, other_name):
    """Do company's notes contain other_name (after normalising both)?"""
    words = " ".join(normalise(other_name))
    return bool(company.get("notes")) and f" {words} " in f" {' '.join(normalise(company['notes']))} "


def code_decision(a, b, version):
    """Returns 'same' or 'different' when code can settle it, else None (ask Jev).

    v1 looks at names only. v2 also asks Jev when the notes mention the other
    name or the websites match, which v1 missed for a rebrand."""
    words_a, words_b = normalise(a["name"]), normalise(b["name"])
    if "".join(words_a) == "".join(words_b):
        return "same"
    shares_a_word = bool(set(words_a) & set(words_b))
    similar = SequenceMatcher(None, " ".join(words_a), " ".join(words_b)).ratio() >= SIMILARITY_TO_ASK
    if shares_a_word or similar:
        return None
    if version != "v1":
        same_site = host(a.get("website")) is not None and host(a.get("website")) == host(b.get("website"))
        if same_site or mentions(a, b["name"]) or mentions(b, a["name"]):
            return None
    return "different"


def band(probability):
    if probability >= SAME_AT_OR_ABOVE:
        return "same"
    if probability <= DIFFERENT_AT_OR_BELOW:
        return "different"
    return "unsure"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--live", action="store_true",
                      help="Make one paid request per pair that code sends to Jev")
    mode.add_argument("--replay", type=Path, help="Show a saved results file without calling Jev")
    mode.add_argument("--dry-run", action="store_true",
                      help="Show which pairs code settles and which it would send to Jev; no request")
    parser.add_argument("--version", choices=QUESTION_VERSIONS, default="v2",
                        help="Question and code filter version")
    args = parser.parse_args()

    if args.dry_run:
        dry_run(args.version)
    elif args.replay:
        run = json.loads(args.replay.read_text())
        print(f"OFFLINE REPLAY of {args.replay.name} (recorded, not a fresh prediction)")
        show(run)
    else:
        try:
            key = api_key()
        except JevError as error:
            sys.exit(str(error))
        show(live_run(key, args.version))


def dry_run(version):
    print(f"Code filter {version}:")
    to_ask = 0
    for case in CASES:
        decision = code_decision(case["a"], case["b"], version)
        to_ask += decision is None
        print(f"  {case['id']:<17} {case['a']['name']!r} vs {case['b']['name']!r}: "
              f"{'ask Jev' if decision is None else 'code says ' + decision}")
    print(f"\n{to_ask} of {len(CASES)} pairs would be sent to Jev (no request made)")


def live_run(key, version):
    questions = QUESTION_VERSIONS[version]
    started = datetime.now().isoformat(timespec="seconds")
    records = []
    for case in CASES:
        record = {"id": case["id"], "expected": EXPECTED[version].get(case["id"])}
        decision = code_decision(case["a"], case["b"], version)
        if decision is not None:
            record.update(decided_by="code", decision=decision)
        else:
            record["decided_by"] = "jev"
            try:
                state = {"a": case["a"], "b": case["b"]}
                payload, data, elapsed = call(key, state, questions)
                record.update(request=payload, response=data, elapsed_seconds=elapsed)
                validate_nouls(data, questions)
                record["decision"] = band(data["answers"]["same_company"]["noul"])
            except JevError as error:
                # Keep going so one failure is visible without losing the other pairs.
                record["error"] = str(error)
        records.append(record)
        print(f"  {case['id']}: {record.get('decision', record.get('error'))} ({record['decided_by']})",
              file=sys.stderr)

    run = {"mode": "live", "version": version, "started": started, "cases": records}
    RESULTS.mkdir(exist_ok=True)
    path = RESULTS / f"{version}-{started.replace(':', '')}.json"
    with path.open("x") as handle:
        json.dump(run, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    print(f"LIVE RUN ({version}), saved to {path.relative_to(HERE)}")
    return run


def show(run):
    rows = []
    matches = 0
    for record in run["cases"]:
        if "error" in record:
            rows.append((record["id"], record["expected"], "jev", "ERROR", "", "", record["error"]))
            continue
        probability = ""
        if record["decided_by"] == "jev":
            probability = f"{record['response']['answers']['same_company']['noul']:g}"
        ok = record["decision"] == record["expected"]
        matches += ok
        rows.append((record["id"], record["expected"], record["decided_by"], record["decision"],
                     probability, "yes" if ok else "NO", ACTIONS[record["decision"]]))

    headers = ("pair", "expected", "by", "decision", "p(same)", "match", "action")
    widths = [max(len(str(row[i])) for row in rows + [headers]) for i in range(6)]
    for row in [headers] + rows:
        print("  ".join(str(cell).ljust(width) for cell, width in zip(row, widths)) + "  " + row[6])
    asked = sum(record["decided_by"] == "jev" for record in run["cases"])
    print(f"\n{matches}/{len(run['cases'])} matched expected ({run['version']}, {run['mode']}); "
          f"{asked} pairs sent to Jev, {len(run['cases']) - asked} settled by code")


if __name__ == "__main__":
    main()
