# Experiment 2: Prospect triage hints for jobfinder

**In one sentence:** for each prospect in jobfinder's review queue, ask Jev whether it looks worth promoting, worth watching, worth dropping, or too thin to judge, and use the answer to sort the queue. I still make every decision.

This is the second of three experiments for Launchpad Mission 11, step 3.

## Background

In jobfinder, a **prospect** is a lead I'm still looking into, not yet a job I can apply for. The schema (`docs/schema.md`) says only `company` is required. `title`, `url` and `notes` are often empty. I review prospects by hand on the Queue page and promote the good ones to opportunities or drop the rest.

The idea came from the earlier jobfinder session: a hint badge per prospect would let me look at the most promising ones first. It keeps jobfinder's rule that "the agent finds, you decide".

## How this differs from experiment 1

| | Experiment 1: scope gate | Experiment 2: prospect triage |
|---|---|---|
| What the answer does | Decides whether the grader runs | Only suggests a badge and a sort order |
| If Jev is wrong | A listing can be hidden (serious) | A prospect sits lower in my queue (mild, I still see it) |
| State sent | Plain text (the listing) | **Structured JSON**: what I'm looking for, plus the prospect's fields, some of them `null` |
| Main challenge | Mixed-duty roles | **Very sparse input**: sometimes just a company name |

## Input, question and answers

**Input (state)** is a JSON object with two parts:

```json
{
  "looking_for": "A first junior or graduate software developer role. Wellington, New Zealand (hybrid or on-site) or remote within New Zealand. Mentorship matters. Not interested in senior roles, support, data engineering or testing-only roles, or roles that need relocating overseas.",
  "prospect": {"company": "Weta Ridge Ltd (fictional)", "title": null, "url": null, "source": "manual", "notes": null}
}
```

`looking_for` tells Jev what "a good prospect" means for me. `prospect` has the same fields as jobfinder's `prospect` table.

**Question:** one Choice, defined in `prospect_triage.py`:

```python
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
```

**What the code does with each answer.** It never changes a prospect's status:

| Choice | Badge on the Queue page | Queue position |
|---|---|---|
| `promote` | "look at first" | Top |
| `watch` | "check back later" | Second |
| `unknown` | "needs digging" | Third |
| `drop` | "probably drop" | Bottom |

In v1, more confident hints came first within each group. v2 changes the sort order and adds an "unsure" badge (see "What changed for v2"). If a request fails, the prospect still appears, marked "no hint".

## Cases

10 fictional prospects in [cases.json](cases.json):

| Case | What it looks like | Why it's included |
|---|---|---|
| `strong-lead` | Named grad roles, a manager met at a meetup, a buddy system | **Clear case:** promote |
| `clear-senior` | Senior, 8+ years, on-site in Auckland | **Clear case:** drop |
| `not-dev` | Customer Support Lead | **Clear case:** drop |
| `growth-signal` | No role; just raised funding and plans to grow the Wellington team | A real signal but nothing to act on yet |
| `name-only` | Company name only; everything else `null` | **Incomplete** |
| `url-only` | Company plus a careers link; no title or notes | **Incomplete**. Jev can't open the link |
| `word-of-mouth` | A friend says they "sometimes take juniors" | **Ambiguous:** second-hand and vague |
| `wrong-location` | Good junior role with mentoring, but Sydney only, no visa | Good fit except for one rule that rules it out |
| `closed-posting` | Great fit, but the posting closed three months ago | **Ambiguous:** watch or drop? |
| `mixed-signals` | An engineer says juniors, the recruiter says seniors only | **Ambiguous:** the notes contradict each other |

Expected answers are in [expected.json](expected.json), one set per question version, each written before that version's live run.

## Running

From the repo root, with `OPENROUTER_API_KEY` in `.env`:

```sh
python3 experiments/prospect-triage/prospect_triage.py --live                 # 10 paid requests, question v2
python3 experiments/prospect-triage/prospect_triage.py --live --version v1    # rerun the original question
python3 experiments/prospect-triage/prospect_triage.py --replay experiments/prospect-triage/results/<file>.json
# Replay with v1's queue logic (sort by confidence, no unsure badge):
python3 experiments/prospect-triage/prospect_triage.py --replay <file> --sort confidence --unsure-below 0
```

Each live run saves every request and raw response to `results/`. Replay makes no request and is labelled as recorded.

## Results

### v1 (live, 2026-09-23, [results/v1-2026-09-23T114212.json](results/v1-2026-09-23T114212.json))

**8/10 matched expected.** JSON state worked through OpenRouter with no changes. About $0.000025 per request, 0.3–0.6 s each.

| Case | Expected | Jev | Confidence | Probabilities |
|---|---|---|---|---|
| strong-lead | promote | **watch** ❌ | 0.77 | watch 0.83, promote 0.17 |
| clear-senior | drop | drop ✅ | 1 | drop 1 |
| not-dev | drop | drop ✅ | 1 | drop 1 |
| growth-signal | watch | watch ✅ | 0.97 | watch 0.98, unknown 0.01, promote 0.01 |
| name-only | unknown | unknown ✅ | 0.95 | unknown 0.96, watch 0.04 |
| url-only | unknown | unknown ✅ | 0.84 | unknown 0.88, watch 0.12 |
| word-of-mouth | watch | watch ✅ | 1 | watch 1 |
| wrong-location | drop | drop ✅ | 1 | drop 1 |
| closed-posting | watch | watch ✅ | 0.66 | watch 0.74, drop 0.25, promote 0.01 |
| mixed-signals | watch | **drop** ❌ | 0.33 | drop 0.5, watch 0.5 |

Suggested queue order from v1 (v1's code: grouped by choice, sorted by confidence, no unsure badge):

```
 1. word-of-mouth    [check back later, 100%]
 2. growth-signal    [check back later, 97%]
 3. strong-lead      [check back later, 77%]
 4. closed-posting   [check back later, 66%]
 5. name-only        [needs digging, 95%]
 6. url-only         [needs digging, 84%]
 7. clear-senior     [probably drop, 100%]
 8. not-dev          [probably drop, 100%]
 9. wrong-location   [probably drop, 100%]
10. mixed-signals    [probably drop, 33%]
```

What I noticed:
- **Clear drops and sparse prospects were handled well.** All three clear drops came back at 1, and both incomplete prospects went to `unknown`, at 0.95 and 0.84. Jev didn't guess from a bare company name.
- **The best lead wasn't promoted, and my criteria are partly to blame.** `promote` says "there is, or will soon be, a specific role", but `watch` says "no suitable role to act on **yet**". The notes say "posting goes live next month", so both descriptions fit. Jev picked `watch`, which is a defensible reading. Nothing got `promote`, so the queue has no "look at first" group at all.
- **The queue order is wrong because of how the code sorts, not because of Jev.** Within a group, the code sorts by confidence. But confidence means "how sure Jev is about the category", not "how promising the prospect is". A vague tip from a friend is *confidently* `watch` (1.0), so it came first, above the best lead (0.77).
- **`mixed-signals` was an exact coin flip** (drop 0.5, watch 0.5, confidence 0.33), but the code still showed it as "probably drop". A 50/50 answer shouldn't get a confident-sounding badge.
- **`closed-posting`** matched, and the probabilities (watch 0.74, drop 0.25) show the uncertainty I expected.

### What changed for v2, and why

Two changes, one to the question and one to the code.

**1. Question: `promote` and `watch` no longer overlap.**

| | v1 | v2 |
|---|---|---|
| `promote` | "There is, or will soon be, a specific role that fits looking_for. [...]" | "A specific role that fits looking_for exists now, **or a first-hand source (someone at the company, or the company itself) confirms one is opening soon.** [...]" |
| `watch` | "It could fit looking_for later, but there is no suitable role to act on yet, or the evidence is second-hand or uncertain." | "It could fit looking_for, but **no fitting role is confirmed: the signal is second-hand, vague, contradictory or about the future.**" |

The v1 wording gave "a posting going live next month" two homes. v2 makes the dividing line **who said it and whether it's confirmed**: an engineering manager saying they're hiring counts as `promote`; a friend saying they "sometimes take juniors" counts as `watch`. `contradictory` is added to `watch` for the mixed-signals case. Expected answers for v2 are the same as v1, because the aim is for Jev to match them, not to change what I expect.

**2. Code: sort by promise, and flag coin flips.**

```python
UNSURE_BELOW = 0.5
UNSURE_BADGE = "unsure: look yourself"

def badge(answer, unsure_below):
    if answer["confidence"] < unsure_below:
        return UNSURE_BADGE
    return BADGES[answer["choice"]]

def sort_key(answer, sort):
    if sort == "confidence":   # v1
        return (QUEUE_ORDER.index(answer["choice"]), -answer["confidence"])
    p = answer["probabilities"]  # v2
    return (-p["promote"], -p["watch"], p["drop"])
```

- **Sort by promote probability, then watch probability**, instead of by confidence. Confidence says how sure Jev is of the category, not how good the prospect is.
- **Below 0.5 confidence, show "unsure: look yourself"** instead of the top choice's badge.

Because this is code only, I tested it on the v1 results with no new calls. The v1 answers, re-sorted:

```
 1. strong-lead      [check back later, 77%]       promote 0.17, watch 0.83
 2. growth-signal    [check back later, 97%]       promote 0.01, watch 0.98
 3. closed-posting   [check back later, 66%]       promote 0.01, watch 0.74
 4. word-of-mouth    [check back later, 100%]      promote 0, watch 1
 5. mixed-signals    [unsure: look yourself, 33%]  promote 0, watch 0.5
 6. url-only         [needs digging, 84%]          promote 0, watch 0.12
 7. name-only        [needs digging, 95%]          promote 0, watch 0.04
 8. clear-senior     [probably drop, 100%]
 9. not-dev          [probably drop, 100%]
10. wrong-location   [probably drop, 100%]
```

The best lead moves from #3 to #1, and the coin flip moves out of the drop group and gets an honest badge. Even though Jev said `watch` for the strong lead, its 17% `promote` share was enough to put it first.

### v2 (live, 2026-09-23, [results/v2-2026-09-23T114450.json](results/v2-2026-09-23T114450.json))

**9/10 matched expected** (v1: 8/10). About $0.00024 for all ten requests, 0.3–0.6 s each.

| Case | Expected | Choice v1 → v2 | Confidence v1 → v2 | v2 probabilities |
|---|---|---|---|---|
| strong-lead | promote | watch → **watch** ❌ | 0.77 → 0.60 | watch 0.70, **promote 0.30** (v1: 0.17) |
| clear-senior | drop | drop → drop | 1 → 1 | drop 1 |
| not-dev | drop | drop → drop | 1 → 1 | drop 1 |
| growth-signal | watch | watch → watch | 0.97 → 0.98 | watch 0.99, unknown 0.01 |
| name-only | unknown | unknown → unknown | 0.95 → 0.98 | unknown 0.99, watch 0.01 |
| url-only | unknown | unknown → unknown | 0.84 → 0.81 | unknown 0.86, watch 0.14 |
| word-of-mouth | watch | watch → watch | 1 → 1 | watch 1 |
| wrong-location | drop | drop → drop | 1 → 1 | drop 1 |
| closed-posting | watch | watch → watch | 0.66 → **0.47** | watch 0.61, drop 0.39 |
| mixed-signals | watch | drop → **watch** ✅ | 0.33 → 0.36 | watch 0.53, drop 0.47 |

Suggested queue order from v2 (v2's code: sorted by promise, unsure badge below 0.5):

```
 1. strong-lead      [check back later, 60%]       promote 0.3, watch 0.7
 2. word-of-mouth    [check back later, 100%]      promote 0, watch 1
 3. growth-signal    [check back later, 98%]       promote 0, watch 0.99
 4. closed-posting   [unsure: look yourself, 47%]  promote 0, watch 0.61
 5. mixed-signals    [unsure: look yourself, 36%]  promote 0, watch 0.53
 6. url-only         [needs digging, 81%]
 7. name-only        [needs digging, 98%]
 8. clear-senior     [probably drop, 100%]
 9. not-dev          [probably drop, 100%]
10. wrong-location   [probably drop, 100%]
```

With v1's sorting code (`--sort confidence --unsure-below 0`), the same v2 answers would put the strong lead back at #3, behind the friend's tip and the growth signal.

What I noticed:
- **The new wording nudged the strong lead but didn't flip it.** `promote` rose from 0.17 to 0.30, but Jev still chose `watch`. Looking back, my v2 wording reintroduced an overlap: `promote` covers a role "confirmed as opening soon", but `watch` includes signals "about the future". "Posting goes live next month" is both. The wording problem moved rather than went away.
- **The code change is what got the strong lead to the top.** As in experiment 1, the fix in code mattered more than the fix in wording. Sorting by `promote` probability puts the best lead first under both v1 and v2 answers.
- **The "match" on mixed-signals is shallow.** It went from `drop` to `watch`, but at 0.53 vs 0.47 it's still a coin flip. A match count of 9/10 makes v2 look better than it is. The "unsure" badge is the honest way to show it.
- **The risk I watched for didn't happen.** `closed-posting` wasn't pulled into `promote` (0 in both runs). It did become less certain (drop rose from 0.25 to 0.39), so it now gets the unsure badge, which seems right for a closed posting.
- **Sparse and clear cases stayed stable.** The 3 clear drops stayed at 1, and both incomplete prospects stayed `unknown`, at 0.98 and 0.81.
- Each version ran once on 10 fictional prospects, so small shifts may be run-to-run variation.

## Conclusion

_Drafted by Claude from the two runs; edit to make it your own._

**What worked:** Jev reliably spotted clear drops (always 1.0) and refused to guess on prospects with almost no information (`unknown` at 0.81–0.98). Structured JSON state with `null` fields worked with no special handling. Those are the two things a triage hint most needs to get right.

**What failed:** Jev wouldn't label the best lead `promote` under either wording. I think my criteria are the main cause, since both versions left "a role is coming soon" fitting two options. Getting the words to split cleanly was harder than expected.

**The key lesson:** **use the probabilities, not just the label.** Jev's choice for the strong lead was `watch` both times, but its `promote` probability was always the highest in the set. Sorting by that probability gave a sensible queue even when the label was "wrong". And a low-confidence answer should be shown as unsure, not as its top pick.

**Would I use it?** Yes, as a **sort order and hint** on the Queue page, where a wrong answer only moves a prospect up or down and I still review everything. I wouldn't use the label alone to auto-promote or auto-drop anything.

**Next step if I kept going:** try splitting the one Choice into separate questions, for example a Noul for "a fitting role is confirmed by a first-hand source" and a Noul for "the prospect is clearly ruled out". Then combine them in code, instead of asking Jev to pick one bucket for a mixed situation.
