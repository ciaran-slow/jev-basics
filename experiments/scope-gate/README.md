# Experiment 1: A scope gate for jobfinder

**In one sentence:** before jobfinder spends a full grading call on a job listing, ask Jev one quick multiple-choice question, "is this even a software development role?", and skip the grading when the answer is clear.

**Result in one sentence:** Jev got every clear case right with near-certain confidence, struggled with a listing that mixes coding and non-coding work, and became safe to use once ordinary code only trusted its "skip" answers when confidence was at least 0.9.

This is the first of three experiments for Launchpad Mission 11, step 3.

---

## Contents

1. [Background: the problem this solves](#1-background-the-problem-this-solves)
2. [What Jev is, and why it fits here](#2-what-jev-is-and-why-it-fits-here)
3. [How the gate works](#3-how-the-gate-works)
4. [The question we ask Jev](#4-the-question-we-ask-jev)
5. [What the code does with the answer](#5-what-the-code-does-with-the-answer)
6. [What a real request and response look like](#6-what-a-real-request-and-response-look-like)
7. [The test listings](#7-the-test-listings)
8. [How the experiment was run](#8-how-the-experiment-was-run)
9. [Results: v1](#9-results-v1)
10. [What we changed for v2, and why](#10-what-we-changed-for-v2-and-why)
11. [Results: v2](#11-results-v2)
12. [Conclusion](#12-conclusion)
13. [Limits: what this does not show](#13-limits-what-this-does-not-show)
14. [Running it yourself](#14-running-it-yourself)
15. [Files in this folder](#15-files-in-this-folder)

---

## 1. Background: the problem this solves

**jobfinder** is my job-search app. It finds job listings, and a grader (an AI model call) scores each one from 1 to 10 against my criteria, such as mentorship, whether it's junior-friendly and location.

The grading criteria (`docs/grading-criteria.md` in jobfinder) start with a **scope rule** that is applied before any points are given:

> Only software development roles are scored normally. A role whose main work is not writing software (technical support, data engineering, machine learning research, firmware, testing only, project management) gets a fixed score of 1 [...] A page that is not a role at all, such as an expression of interest or a careers page with no position, has unknown scope: it also scores 1 [...] A role that writes code as its main work is in scope even when its title says AI, automation, integration or platform.

So for a large share of listings, such as support roles or careers pages, the answer is already fixed at 1 before any real grading happens. Today the grader still reads the whole listing and all the criteria to get there.

**The idea:** pull the scope rule out into its own small, fast question. If the answer is "not a software role" or "not a role at all", the app sets the score to 1 itself and never calls the grader. If the answer is "software", the grader runs as normal.

This idea came from an earlier Claude Code session that looked at where Jev could fit in jobfinder. It picked the scope gate as "the smallest possible first experiment".

---

## 2. What Jev is, and why it fits here

Jev is a model from TypeSafe AI that makes **small, structured decisions**. You send it:

- a **state**: the text it should judge (here, one job listing), and
- one or more **typed questions**, each with a fixed set of possible answers.

It sends back an answer for each question with probabilities and a confidence number. It never writes sentences. A good way to picture it: you hand it a reading passage and a multiple-choice answer sheet, and it fills in the bubbles and tells you how sure it is.

There are three question types:

| Type | What it returns | Example |
|---|---|---|
| **Choice** | One of several named options | "software / not_software / not_a_role / unknown" |
| **Score** | A level on an ordered scale | "none / some / strong mentorship" |
| **Noul** | A probability from 0 to 1 that a statement is true | "the title says senior" → 0.92 |

The scope rule is naturally a **Choice**: there are a few named outcomes and each leads to a different action. That's why this experiment uses a single Choice question.

---

## 3. How the gate works

```
 job listing text
        │
        ▼
 ┌─────────────────────┐
 │ Jev: one Choice     │   "Is this a software development role?"
 │ question            │   → choice + probabilities + confidence
 └─────────────────────┘
        │
        ▼
 ┌─────────────────────┐
 │ Plain Python        │   decides what to do:
 │ (action + threshold)│   grade / skip with score 1 / grade and flag
 └─────────────────────┘
```

The important design point: **Jev only picks an option. Ordinary code decides what that option means.** Jev never sees the score, the threshold or the actions. This matches the pattern in every JevMade project I looked at in step 2: Jev judges, code decides.

In this experiment nothing is actually graded or saved to jobfinder. The script only prints what the app *would* do, so it's safe to run.

---

## 4. The question we ask Jev

Each question version lives in `scope_gate.py` in a dictionary called `QUESTION_VERSIONS`. New versions are added alongside old ones rather than replacing them, so earlier results can always be rerun exactly.

**v1** follows jobfinder's scope rule almost word for word:

```python
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
```

How to read this:

- `"scope"` is the name we give the question. The answer comes back under the same name.
- `"type": "choice"` means Jev must pick exactly one of the options.
- `"instructions"` is the question itself.
- `"criteria"` lists the allowed answers. The key (for example `not_software`) is what Jev returns, and the text describes when that answer applies.
- **`unknown` is a deliberate escape option.** Without it, Jev would be forced to guess `software` or `not_software` even when the listing says nothing useful. The mission README recommends this.

**v2** is identical except for a wider `unknown` description. Section 10 explains why:

```python
"unknown": "It is a role, but the text does not establish the main work, such as a title with no description, or a mix of duties where coding may or may not be the main part.",
```

---

## 5. What the code does with the answer

Once Jev answers, the app acts on the choice:

| Choice | What code does |
|---|---|
| `software` | Run the grader as normal |
| `not_software` | Skip the grader, score 1, reason "not a software development role" |
| `not_a_role` | Skip the grader, score 1, every criterion unknown |
| `unknown` | Run the grader, but flag the listing for review |

In `scope_gate.py` this is plain Python:

```python
ACTIONS = {
    "software": "grade normally",
    "not_software": "skip grader; score 1, 'not a software development role'",
    "not_a_role": "skip grader; score 1, every criterion unknown",
    "unknown": "grade normally, flag for review",
}
```

From v2 onward there is also a **confidence threshold**:

```python
# Skipping the grader hides a listing, so only skip when Jev is this sure.
# Wrongly grading costs one call; wrongly skipping loses a job.
SKIP_THRESHOLD = 0.9

SKIPS = {"not_software", "not_a_role"}

def action(answer, threshold):
    """Turn a scope answer into what the app would do."""
    if answer["choice"] in SKIPS and answer["confidence"] < threshold:
        return f"grade normally, flag for review (conf < {threshold:g})"
    return ACTIONS[answer["choice"]]
```

In plain English: **if Jev says "skip this one" but is less than 90% confident, don't skip. Grade it anyway and flag it for me to look at.**

The reason is that the two kinds of mistake cost very different amounts:

| Mistake | What happens | Cost |
|---|---|---|
| Grading a listing that should have been skipped | One extra grader call | A fraction of a cent |
| Skipping a listing that should have been graded | A job I might want gets a score of 1 and is hidden | A missed opportunity |

So the code leans towards grading whenever Jev is unsure.

---

## 6. What a real request and response look like

The shared file `jev_client.py` at the repo root sends each request. It's the same calling code as the step 1 starter (`demo.py`), moved into its own file so all three experiments can use it:

```python
def call(key, state, questions):
    """Make one request. Returns (payload, response, elapsed seconds). No retries."""
    payload = {"model": MODEL, "state": state, "questions": questions}
    request = Request(
        ENDPOINT,
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    ...
```

The request goes to Jev (`typesafe/jev-1.13`) through OpenRouter. What gets sent for one listing is roughly:

```json
{
  "model": "typesafe/jev-1.13",
  "state": "Title: Developer\nCompany: Weta Ridge Ltd (fictional)",
  "questions": { "scope": { "type": "choice", "instructions": "...", "criteria": { "...": "..." } } }
}
```

And this is the real, unedited response for that listing in the v2 run:

```json
{
  "model": "typesafe/jev-1.13-20260917",
  "answers": {
    "scope": {
      "type": "choice",
      "choice": "unknown",
      "probabilities": {
        "unknown": 0.74,
        "not_a_role": 0,
        "software": 0.26,
        "not_software": 0
      },
      "confidence": 0.66
    }
  },
  "usage": { "input_tokens": 469, "output_tokens": 50, "cost": 1.9698e-05 },
  "id": "gen-dec-1790119301-zVjZLopOypZfYoLkoyI0",
  "provider": "TypeSafe"
}
```

What each part means:

- **`choice`**: Jev's pick, here `unknown`.
- **`probabilities`**: how Jev spread its belief across all four options. They add up to 1. Here it was 74% `unknown` and 26% `software`.
- **`confidence`**: a separate 0–1 number for how sure Jev is overall. **This is what the threshold checks.** It isn't simply the top probability (0.66 here, while the top probability is 0.74).
- **`usage`**: tokens used and cost. This request cost about $0.00002.

Before using a response, the code checks it with `validate_choices()` in `jev_client.py`. The choice must be one of the options we offered, confidence and probabilities must be between 0 and 1, and the probabilities must add up to 1. This only checks that the reply is *well-formed*. It says nothing about whether the answer is *right*.

---

## 7. The test listings

All nine listings are **fictional**, written for this experiment (see `cases.json`). They were picked to cover different kinds of difficulty:

| Case | Listing | Why it's included |
|---|---|---|
| `clear-dev` | Junior Full-Stack Developer, TypeScript/React/Python | **Clear case.** Obviously in scope |
| `clear-support` | Technical Support Specialist, "no coding required" | **Clear case.** Obviously out of scope |
| `ai-title-dev` | "AI Automation Engineer" who writes TypeScript services | **Trap.** The title sounds non-dev, but the rule says coding roles with AI titles are in scope |
| `data-eng` | Graduate Data Engineer, dbt/Airflow/Snowflake | Named in the rule as out of scope |
| `qa-only` | Manual QA Tester, follows test scripts | Named in the rule ("testing only") |
| `careers-page` | "No open roles right now" | Named in the rule as not a role |
| `eoi` | "Expression of Interest – Future Opportunities" | Named in the rule as not a role |
| `ambiguous-integration` | Integration Specialist: configures a platform, maps data, writes *some* JavaScript, runs workshops | **Ambiguous.** Part coding, part not |
| `title-only` | Just "Title: Developer" and a company name | **Incomplete.** Not enough information |

The mission asked for at least one clear case and one ambiguous or incomplete case. This set has two clear cases, one ambiguous case and one incomplete case.

---

## 8. How the experiment was run

Following the mission's step 3 method:

1. **Wrote down the input, question and usable answers** (sections 4 and 5).
2. **Wrote the expected answers before running anything.** They're saved in `expected.json`, with separate v1 and v2 sets, each written before its run. This matters because it's easy to convince yourself afterwards that you "would have said that".
3. **Ran v1 live**: one request per listing, 9 requests. Every request and raw response was saved to `results/`.
4. **Read the results** and looked for where Jev disagreed with my expectations, and where a correct-looking answer was still risky.
5. **Made two changes** (section 10), one to the question and one to the code.
6. **Ran v2 live on exactly the same nine listings**, and kept both result files to compare.
7. **Wrote a conclusion** (section 12).

The script processes each listing like this, simplified from `live_run()`:

```python
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
```

A few safety choices are built in:

- **No automatic retries.** A failed request is shown as an error, not silently retried, which could cost money.
- **One failure doesn't lose the others.** Each listing is recorded separately.
- **Results are never overwritten.** Each run writes a new timestamped file, and the script refuses to write over an existing one.
- **The API key never leaves `.env`.** It's read at runtime and isn't saved in any results file.

---

## 9. Results: v1

Live run, 2026-09-23. Raw data: [results/v1-2026-09-23T111849.json](results/v1-2026-09-23T111849.json)

**8 of 9 matched my expected answers.**

| Case | Expected | Jev said | Confidence | Probabilities |
|---|---|---|---|---|
| clear-dev | software | software ✅ | 1 | software 1 |
| clear-support | not_software | not_software ✅ | 1 | not_software 1 |
| ai-title-dev | software | software ✅ | 1 | software 1 |
| data-eng | not_software | not_software ✅ | 0.98 | not_software 0.99, software 0.01 |
| qa-only | not_software | not_software ✅ | 1 | not_software 1 |
| careers-page | not_a_role | not_a_role ✅ | 1 | not_a_role 1 |
| eoi | not_a_role | not_a_role ✅ | 1 | not_a_role 1 |
| ambiguous-integration | not_software | not_software ✅ | 0.79 | not_software 0.84, software 0.15, unknown 0.01 |
| title-only | unknown | **software** ❌ | 0.38 | software 0.54, unknown 0.46 |

What I noticed:

- **Every clear case, and every case the rule names, came back at 0.98–1 confidence.** That includes the "AI Automation Engineer" trap, which Jev correctly kept in scope.
- **The one miss, `title-only`, was close to a coin flip** (54% vs 46%). In practice the miss didn't matter, because both `software` and `unknown` send the listing to the grader. Only the "flag for review" note was lost.
- **The riskiest result was one that "matched".** For the Integration Specialist, Jev said `not_software` with 0.79 confidence, which agreed with my own guess. But this is a mixed role, and the answer would have made the app skip grading and score it 1. If I'd have liked the job, it would have been hidden from me. A "correct" answer on an unclear case can still be a bad basis for an irreversible action.

---

## 10. What we changed for v2, and why

Two changes: one to the **question** (what Jev is asked) and one to the **code** (what we do with the answer).

### Change 1: a wider `unknown` option

| | `unknown` description |
|---|---|
| v1 | "It is a role, but the text does not establish what the main work is." |
| v2 | "It is a role, but the text does not establish the main work, **such as a title with no description, or a mix of duties where coding may or may not be the main part.**" |

The goal was to give Jev explicit permission to say "I can't tell" for the two unclear kinds of listing we saw in v1. Because of this, I changed my expected answer for `ambiguous-integration` from `not_software` to `unknown` for v2, before running it.

**The risk to watch:** a wider `unknown` might also swallow clear cases, such as data engineering, which would make the gate less useful.

### Change 2: the 0.9 confidence threshold

This is the `SKIP_THRESHOLD` code from section 5. Because it's a code rule and not a question change, **I could test it on the v1 results without making any new requests**:

```sh
python3 experiments/scope-gate/scope_gate.py --replay experiments/scope-gate/results/v1-2026-09-23T111849.json --threshold 0.9
```

On the v1 data it changed exactly one action. The Integration Specialist (confidence 0.79) went from "skip grader, score 1" to "grade normally, flag for review". Every other skip was at 0.98–1 and was unaffected.

---

## 11. Results: v2

Live run, 2026-09-23. Raw data: [results/v2-2026-09-23T112138.json](results/v2-2026-09-23T112138.json)

**8 of 9 matched expected**, the same count as v1 but a different miss. With the threshold, **no listing was wrongly skipped** (v1 without the threshold: 1 wrong skip).

| Case | Expected (v2) | Choice v1 → v2 | Confidence v1 → v2 | v2 probabilities | v2 action |
|---|---|---|---|---|---|
| clear-dev | software | software → software | 1 → 1 | software 1 | grade |
| clear-support | not_software | not_software → not_software | 1 → 1 | not_software 1 | skip |
| ai-title-dev | software | software → software | 1 → 1 | software 1 | grade |
| data-eng | not_software | not_software → not_software | 0.98 → **0.95** | not_software 0.97, software 0.03 | skip |
| qa-only | not_software | not_software → not_software | 1 → 1 | not_software 1 | skip |
| careers-page | not_a_role | not_a_role → not_a_role | 1 → 1 | not_a_role 1 | skip |
| eoi | not_a_role | not_a_role → not_a_role | 1 → 1 | not_a_role 1 | skip |
| ambiguous-integration | unknown | not_software → **not_software** ❌ | 0.79 → **0.61** | not_software 0.71, unknown 0.20, software 0.09 | **grade + flag** (below 0.9) |
| title-only | unknown | software → **unknown** ✅ | 0.38 → 0.66 | unknown 0.74, software 0.26 | grade + flag |

What I noticed:

- **The wider `unknown` fixed `title-only`.** It moved from 54% `software` to 74% `unknown`.
- **It only nudged the Integration Specialist.** Its `unknown` share rose from 1% to 20% and confidence dropped from 0.79 to 0.61, but Jev still picked `not_software`.
- **The threshold is what prevented the wrong skip, not the new wording.** Replaying v2 with the threshold turned off (`--threshold 0`) shows the app would still have skipped the Integration Specialist.
- **The side effect we worried about barely happened.** No clear case moved to `unknown`. Data engineering's confidence slipped slightly, from 0.98 to 0.95. It still skips, but it's now closer to the 0.9 line.
- **Cost and speed:** about $0.00002 per request, so about $0.0002 for all nine. Each request took 0.3–0.6 seconds.

---

## 12. Conclusion

_Drafted by Claude from the two runs; edit to make it your own._

**What worked:** Jev handled every clear case and every role type the rule names, at 0.95–1 confidence, including the "AI Automation Engineer" trap. That's exactly the job a gate exists for: cheaply removing listings that are obviously out of scope before the more expensive grader runs.

**What failed:** the mixed-duties role. Under both wordings Jev leaned towards `not_software`, and rewording the question didn't fully change that. Title-only listings did improve with the new wording.

**The key lesson:** Jev's **confidence number was a useful signal.** Every confident skip was correct, and the one bad call came with noticeably lower confidence. The threshold in code turns that into a safe rule: *when unsure, grade.*

**Would I use it?** Yes, as a gate, **but only with the confidence threshold in code.** I wouldn't let Jev's choice alone decide to skip listings.

**Next step if I kept going:** run it on jobfinder's hand-graded eval listings (`evals/dev.jsonl`) to see how it does on real listings, and run each version several times to measure how much answers vary between runs.

---

## 13. Limits: what this does not show

- **Nine fictional listings is a small sample.** Real listings are longer, messier and more varied.
- **Each version ran once.** Some v1 vs v2 differences, such as data engineering's 0.98 → 0.95, may be ordinary run-to-run variation rather than an effect of the wording.
- **The expected answers are my judgement**, not an objective truth. The Integration Specialist in particular could reasonably be called either way.
- **The gate isn't connected to jobfinder.** The script prints what the app *would* do. Nothing is graded, scored or saved in the real app.
- **High confidence isn't proof.** Confidence was a useful signal on these nine cases, but that needs checking on real data before relying on it.

---

## 14. Running it yourself

You need Python 3 and an OpenRouter API key in `.env` at the repo root:

```sh
OPENROUTER_API_KEY=your-key-here
```

`.env` is ignored by git, so the key is never committed. From the repo root:

```sh
# Live run with the current question (v2). Makes 9 paid requests, about $0.0002 in total.
python3 experiments/scope-gate/scope_gate.py --live

# Live run with the original question
python3 experiments/scope-gate/scope_gate.py --live --version v1

# Replay a saved run. No request, no cost. Uses the 0.9 threshold by default.
python3 experiments/scope-gate/scope_gate.py --replay experiments/scope-gate/results/v2-2026-09-23T112138.json

# Replay with the threshold turned off, to see what Jev's choice alone would do
python3 experiments/scope-gate/scope_gate.py --replay experiments/scope-gate/results/v2-2026-09-23T112138.json --threshold 0
```

Replayed output is always labelled `OFFLINE REPLAY (recorded, not a fresh prediction)`, so recorded results can't be mistaken for new ones.

To try your own listing, add an entry to `cases.json` and an expected answer to `expected.json` **before** running it live.

---

## 15. Files in this folder

| File | What it is |
|---|---|
| `scope_gate.py` | The experiment: question versions, actions, threshold, live run and replay |
| `cases.json` | The nine fictional test listings |
| `expected.json` | My expected answers, one set per question version, each written before its run |
| `results/v1-...json` | Every request and raw response from the v1 live run |
| `results/v2-...json` | Every request and raw response from the v2 live run |
| `../../jev_client.py` | Shared calling and validation code for all three experiments |

**Inspired by:** jobfinder's scope rule (`docs/grading-criteria.md`), and the pattern seen in step 2's JevMade projects ([jev-review](https://github.com/devagrawal09/jev-review), [jev-search](https://github.com/superagents-lab/jev-search), [Claude Code Trace](https://github.com/delexw/claude-code-trace)), where Jev judges and ordinary code decides.
