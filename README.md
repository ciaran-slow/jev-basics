# Jev basics: Launchpad Mission 11

My work for Launchpad Mission 11, "Experiment with Jev". The mission instructions are in [MISSION.md](MISSION.md).

**Jev** is a decision model from TypeSafe AI. You send it some **state** (text or JSON) and one or more **typed questions**, and it sends back structured answers with probabilities, never prose. I tried it on three decisions from my job-search app, **jobfinder**. Each experiment ran two versions of its question on the same fictional examples, with my expected answers written down before each run.

_The conclusions below were drafted with Claude from the saved results. I'll edit them into my own words._

---

## The comparison

| Use case | What I tried | What happened | Would I use it? |
|---|---|---|---|
| **[1. Scope gate](experiments/scope-gate/)**<br>Should jobfinder's grader run at all? | **Input:** one job listing as text.<br>**Question:** one **Choice**: `software` / `not_software` / `not_a_role` / `unknown`, taken from jobfinder's scope rule.<br>**Code:** skip the grader and score 1 for out-of-scope listings; grade the rest.<br>**v2:** a wider `unknown`, and skip only when confidence ≥ 0.9. | 8/9 matched in both versions. Every clear case scored 0.95–1, including an "AI Automation Engineer" trap. A mixed-duties role was called `not_software` both times. The **0.9 threshold in code**, not the rewording, stopped it from being wrongly skipped. | **Yes, with the threshold.** It cheaply removes obviously out-of-scope listings. I wouldn't let the choice alone skip listings. |
| **[2. Prospect triage](experiments/prospect-triage/)**<br>Which leads should I look at first? | **Input:** a prospect as **JSON**, with `null` fields, plus what I'm looking for.<br>**Question:** one **Choice**: `promote` / `watch` / `drop` / `unknown`.<br>**Code:** a badge and a queue order only; no status is ever changed.<br>**v2:** stop `promote` and `watch` overlapping; sort by `promote` probability; an "unsure" badge below 0.5. | 8/10 → 9/10. Clear drops always scored 1.0, and sparse prospects were correctly `unknown`. The best lead was labelled `watch` both times, but it always had the highest `promote` probability, so **sorting by probability** put it first. The 9/10 overstates things: one "fix" was a 0.53/0.47 coin flip. | **Yes, as a sort order and hint.** A wrong answer only moves a prospect up or down the queue. Never to auto-promote or auto-drop. |
| **[3. Duplicate companies](experiments/duplicate-companies/)**<br>Is this new company already in the database? | **Input:** two companies (name, website, notes) as JSON.<br>**Question:** one **Noul**: p(same company).<br>**Code:** normalise names first (macrons, "Ltd") and only ask Jev about near misses; ≥ 0.8 warn, ≤ 0.2 separate, otherwise ask me.<br>**v2:** also ask when websites match or notes mention the other name; tell Jev how to weigh evidence. | 9/11 in both versions, and each version run twice. Answers were **stable within 0.02** between runs. The rebrand was missed by the v1 code filter, then scored 0.96 once v2 sent it to Jev. The evidence wording made Jev more cautious, so two real duplicates became "ask me". Every v2 mistake was safe. | **Yes, as a warning before saving.** Never to merge automatically. Next I'd pass facts code already knows, like "same website host", in the state. |

### What all three had in common

- **The code change mattered more than the wording change, every time.** A confidence threshold (experiment 1), a sort by probability (experiment 2) and a wider filter (experiment 3) each fixed the main problem. Rewording the question only nudged the probabilities.
- **Read the probabilities, not just the label.** The most useful signal was often the probability spread: a 17% `promote` share, a 0.61 confidence, a 0.79 p(same). Matching the label alone hid how close some calls were.
- **Choose which way mistakes go.** Each design leans towards the safe mistake: grade rather than skip, sort lower rather than drop, ask me rather than merge.
- **Criteria wording can backfire.** Words like "yet", "soon" and "weak evidence" shifted answers in ways I didn't fully predict, including on cases I wasn't trying to change.

## One interesting result from each

- **Scope gate:** the Integration Specialist was answered "correctly" (`not_software`, matching my guess) with 0.79 confidence. That's exactly the answer that would have hidden a job I might want. Being right on an unclear case can still be a bad basis for an irreversible action.
- **Prospect triage:** a friend's vague tip was the most *confident* answer (`watch`, 1.0), so v1 put it at the top of the queue. Confidence measures how sure Jev is of the category, not how good the prospect is.
- **Duplicate companies:** "Weta Ridge" and "WR Digital" went from a silent miss in v1 to 0.96 in v2, the most confident "same" in the experiment. It only needed code to let Jev see the "Formerly Weta Ridge" note.

## Which one I'd explore further

**The scope gate.** It has the most direct value, since it saves a grader call on every out-of-scope listing. It's also the easiest to test on real data: jobfinder already has hand-graded eval listings (`evals/dev.jsonl`) and a runner. The next step is to run the gate on those, compare it with the hand grades, and repeat each version several times. The mission also suggests Mission 10's eval approach for exactly this.

---

## Earlier steps

- **Step 1: first call.** [demo.py](demo.py) makes one call about a fictional job listing. My two live runs are in [my-first-run.json](my-first-run.json) and [run-2.json](run-2.json), and my predictions and comparison are in [predictions.md](predictions.md).
- **Step 2: exploring JevMade.** Notes on three projects are in [jevmade-notes.md](jevmade-notes.md): what Jev receives, what it returns, what code does with the answer, and what I could and couldn't verify.

## Inspiration

- **jobfinder** (my app, in a private repo): all three use cases come from its scope rule, prospect queue and company table.
- **[jev-review](https://github.com/devagrawal09/jev-review)** (devagrawal09): Jev judges, code applies thresholds; separate calls for dependent steps.
- **[jev-search](https://github.com/superagents-lab/jev-search)** (superagents-lab): a Noul probability per result, used directly as a ranking score. This fed into the sort-by-probability idea in experiment 2.
- **[Claude Code Trace](https://github.com/delexw/claude-code-trace)** (delexw): Noul and Score answers combined with fixed weights in code.
- **[JevMade](https://jevmade.com/)**, where I found them.

## Running the code

You need **Python 3** (standard library only) and an **OpenRouter API key**. Create `.env` in the repo root:

```sh
OPENROUTER_API_KEY=your-key-here
```

`.env` is git-ignored and never committed. No saved result contains the key.

Replay a saved run. This makes no request and costs nothing:

```sh
python3 demo.py --replay sample-response.json
python3 experiments/scope-gate/scope_gate.py --replay experiments/scope-gate/results/v2-2026-09-23T112138.json
python3 experiments/prospect-triage/prospect_triage.py --replay experiments/prospect-triage/results/v2-2026-09-23T114450.json
python3 experiments/duplicate-companies/duplicate_companies.py --replay experiments/duplicate-companies/results/v2-2026-09-23T122314.json
```

Make fresh live calls. These are paid, but each is well under a cent:

```sh
python3 demo.py --live --output my-new-run.json                              # 1 request
python3 experiments/scope-gate/scope_gate.py --live                          # 9 requests
python3 experiments/prospect-triage/prospect_triage.py --live                # 10 requests
python3 experiments/duplicate-companies/duplicate_companies.py --dry-run     # free: shows which pairs would go to Jev
python3 experiments/duplicate-companies/duplicate_companies.py --live        # 9 requests
```

Every experiment script accepts `--version v1` to rerun the original question. Each experiment's README explains its other options.

### About the results

- **Every result file in `experiments/*/results/` is a recorded live response** from 2026-09-23 (model `typesafe/jev-1.13-20260917`), saved with its full request.
- **Replayed output is always labelled** `OFFLINE REPLAY (recorded, not a fresh prediction)`. A replay shows what Jev said then, not what it would say now.
- **All test inputs are fictional**, and websites use the reserved `.example` domain. How Jev behaves on real listings, prospects and companies is **still untested**.
- In total: **74 live requests, about $0.0016**, each taking 0.3–0.9 seconds.

## Repo layout

| Path | What it is |
|---|---|
| [MISSION.md](MISSION.md) | The mission instructions |
| [demo.py](demo.py), [test_demo.py](test_demo.py) | Step 1 starter and its tests (`python3 -m unittest test_demo`) |
| [predictions.md](predictions.md), `my-first-run.json`, `run-2.json` | Step 1 predictions and live results |
| [jevmade-notes.md](jevmade-notes.md) | Step 2 notes on three JevMade projects |
| [jev_client.py](jev_client.py) | Shared calling and validation code for all three experiments |
| [experiments/scope-gate/](experiments/scope-gate/) | Experiment 1 |
| [experiments/prospect-triage/](experiments/prospect-triage/) | Experiment 2 |
| [experiments/duplicate-companies/](experiments/duplicate-companies/) | Experiment 3 |
