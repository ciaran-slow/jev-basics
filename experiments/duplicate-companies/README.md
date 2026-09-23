# Experiment 3: Spotting duplicate companies in jobfinder

**In one sentence:** before jobfinder saves a new company, check whether it's really a company already in the database under a slightly different name. Plain code handles the obvious cases, and Jev is asked only about the unclear ones.

This is the third of three experiments for Launchpad Mission 11, step 3.

## Background: the problem

jobfinder links opportunities, prospects and contacts to a company **by its name as plain text**, not by an ID. The schema (`docs/schema.md`) says the `company.name` column "is indexed but not unique. Nothing prevents two companies with the same name". The search is a simple text match.

So if one agent run saves "Kōwhai Labs" and a later one saves "Kowhai Labs Limited", jobfinder treats them as two different companies. My research notes, contacts and opportunities for one employer get split across two rows.

This idea came from the earlier jobfinder session's list of places Jev could fit: "Do the obvious normalisation in code first and only ask Jev about the ambiguous pairs."

## How this differs from experiments 1 and 2

| | Exp 1: scope gate | Exp 2: prospect triage | **Exp 3: duplicate companies** |
|---|---|---|---|
| Question type | Choice | Choice | **Noul** (a probability that a statement is true) |
| State | One listing (text) | One prospect (JSON) | **Two companies to compare** (JSON) |
| Who decides first | Jev, every time | Jev, every time | **Code first; Jev only for near misses** |
| Confidence | Separate `confidence` field | Separate `confidence` field | **No confidence field.** The probability itself is the signal |

## How it works

```
 new company name + existing company
              │
              ▼
 ┌──────────────────────────┐
 │ Code: normalise names    │  same after normalising?  ──► "same" (no Jev call)
 │                          │  share no words and not    ──► "different" (no Jev call)
 │                          │  similar?
 └──────────────────────────┘
              │ near miss
              ▼
 ┌──────────────────────────┐
 │ Jev: one Noul question   │  p(same company) from 0 to 1
 └──────────────────────────┘
              │
              ▼
 ┌──────────────────────────┐
 │ Code: turn p into action │  ≥ 0.8 warn  ·  ≤ 0.2 separate  ·  between: ask me
 └──────────────────────────┘
```

### Step 1: code normalises the names

```python
LEGAL_SUFFIXES = {"ltd", "limited", "inc", "llc", "pty", "co", "company"}

def normalise(name):
    """Lowercase, strip macrons and punctuation, drop legal suffixes."""
    text = unicodedata.normalize("NFKD", name)
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).lower()
    text = re.sub(r"[^a-z0-9 ]+", " ", text.replace("&", " and "))
    return [word for word in text.split() if word not in LEGAL_SUFFIXES]
```

So "Kōwhai Labs" and "Kowhai Labs Limited" both become `["kowhai", "labs"]`. Stripping macrons matters in New Zealand, where names like Kōwhai, Tūī and Pūkeko are often typed without them.

### Step 2: code decides whether Jev needs asking

This is the v1 filter. v2 adds a website and notes check (see "What changed for v2").

```python
def code_decision(a, b):
    """Returns 'same' or 'different' when code can settle it, else None (ask Jev)."""
    words_a, words_b = normalise(a), normalise(b)
    if "".join(words_a) == "".join(words_b):
        return "same"
    shares_a_word = bool(set(words_a) & set(words_b))
    similar = SequenceMatcher(None, " ".join(words_a), " ".join(words_b)).ratio() >= SIMILARITY_TO_ASK
    return None if shares_a_word or similar else "different"
```

In plain English:
- **Identical after normalising** (ignoring spaces too, so "Tradewind" matches "TradeWind") → code says **same**.
- **Share a word, or the names look similar** → a near miss, so **ask Jev**.
- **Otherwise** → code says **different**, and Jev is never asked.

### Step 3: Jev's question (v1)

Jev gets both companies' name, website and notes as JSON:

```json
{
  "a": {"name": "Moana Systems", "website": "https://moanasystems.example", "notes": "Wellington."},
  "b": {"name": "Moana Systems Australia", "website": "https://moanasystems.example/au", "notes": "Sydney office of Moana Systems. Hires separately from the NZ team."}
}
```

And one Noul question:

```python
"same_company": {
    "type": "noul",
    "instructions": "Do `a` and `b` refer to the same company: the same employer someone would apply to?",
    "criteria": {
        "true": "The same organisation, written differently: another spelling, a shortened name, a legal suffix, or a new name after a rename.",
        "false": "Different organisations, even if the names share words. This includes related but separate companies, such as a parent and a company it owns, or an overseas office that hires separately.",
    },
}
```

The answer is a single probability, for example `{"type": "noul", "noul": 0.93}`. Unlike Choice, **Noul has no separate confidence number**, so the probability is the only signal.

"The same employer someone would apply to" is deliberate. For jobfinder, what matters is whether my notes and contacts belong on the same row, not whether two companies are legally connected.

### Step 4: code turns the probability into an action

| p(same) | Decision | What the app would do |
|---|---|---|
| 0.8 or more | `same` | Warn: likely duplicate |
| 0.2 or less | `different` | Save as a separate company |
| In between | `unsure` | Ask me before saving |

Nothing is ever merged automatically. Merging the wrong companies would mix up research and contacts, which is hard to undo. The worst the app does on its own is show a warning.

## The test pairs

11 fictional pairs in [cases.json](cases.json). Websites use the reserved `.example` domain, so none of them are real.

| Pair | Names | Why it's included | Settled by |
|---|---|---|---|
| `legal-suffix` | Tradewind / TradeWind Ltd | Only capitals and "Ltd" differ | Code |
| `macron` | Kōwhai Labs / Kowhai Labs Limited | A macron and "Limited" | Code |
| `short-name` | Fernbird Digital / Fernbird | **Clear case:** same website | Jev |
| `shared-word` | Tūī Analytics / Tui Health | **Clear case:** a shared word, different businesses and cities | Jev |
| `parent-company` | Harbourline Software / Harbourline Group | **Ambiguous:** a holding company and a company it owns | Jev |
| `overseas-office` | Moana Systems / Moana Systems Australia | **Ambiguous:** the same brand, but the Sydney office hires separately | Jev |
| `country-suffix` | Rātā Health / Rata Health NZ | Same website; "NZ" isn't stripped by code | Jev |
| `same-animal` | Pūkeko Games / Pukeko Studios | Games vs film animation, different cities | Jev |
| `no-evidence` | Kahu / Kahu Cloud | **Incomplete:** two names and nothing else | Jev |
| `partial-evidence` | Kererū Tech / Kereru Technologies | Only one has a website; the notes fit | Jev |
| `rename` | Weta Ridge / WR Digital | **Blind-spot test:** same company after a rebrand, but the names share nothing, so code never asks Jev | Code |

Expected answers (`same`, `different` or `unsure`) are in [expected.json](expected.json), one set per version, each written before that version's live run. A decision "matches" when it lands in the same band as expected.

## Running

From the repo root, with `OPENROUTER_API_KEY` in `.env`:

```sh
python3 experiments/duplicate-companies/duplicate_companies.py --dry-run                # v2 filter: which pairs go to Jev; no request
python3 experiments/duplicate-companies/duplicate_companies.py --dry-run --version v1   # the original names-only filter
python3 experiments/duplicate-companies/duplicate_companies.py --live                   # v2: 9 paid requests (only pairs code can't settle)
python3 experiments/duplicate-companies/duplicate_companies.py --live --version v1      # v1: 8 paid requests
python3 experiments/duplicate-companies/duplicate_companies.py --replay experiments/duplicate-companies/results/<file>.json
```

Each live run saves every request and raw response to `results/`. Replay makes no request and is labelled as recorded.

## Results

### v1 (live, 2026-09-23, run twice)

Raw data: [results/v1-2026-09-23T121224.json](results/v1-2026-09-23T121224.json) (run 1) and [results/v1-2026-09-23T121339.json](results/v1-2026-09-23T121339.json) (run 2). The Noul reply format matched what the script expected: `{"type": "noul", "noul": 0.84}`. About $0.000019 per request, 0.3–0.5 s each.

**9/11 matched expected in both runs.** Of the 8 pairs Jev saw, 7 matched. Code settled 3 pairs, and 2 of those matched.

| Pair | Expected | Decided by | p(same) run 1 | p(same) run 2 | Decision | Match |
|---|---|---|---|---|---|---|
| legal-suffix | same | code | – | – | same | ✅ |
| macron | same | code | – | – | same | ✅ |
| short-name | same | Jev | 0.85 | 0.84 | same | ✅ |
| shared-word | different | Jev | 0.04 | 0.04 | different | ✅ |
| parent-company | different | Jev | 0.09 | 0.08 | different | ✅ |
| overseas-office | different | Jev | 0.12 | 0.12 | different | ✅ |
| country-suffix | same | Jev | 0.84 | 0.83 | same | ✅ |
| same-animal | different | Jev | 0.05 | 0.04 | different | ✅ |
| no-evidence | unsure | Jev | 0.68 | 0.66 | unsure | ✅ |
| partial-evidence | same | Jev | 0.78 | 0.78 | **unsure** | ❌ |
| rename | same | code | – | – | **different** | ❌ |

What I noticed:
- **Very stable between runs.** No probability moved by more than 0.02 across the two runs. It's the first time in any of the three experiments that I've run the same question twice. It suggests the small shifts in experiments 1 and 2 were probably caused by the wording changes, not by random variation.
- **"Different" was confident; "same" was not.** Every different pair came back at 0.04–0.12. Even pairs with the same website only reached 0.83–0.85, just above the 0.8 line.
- **The `partial-evidence` miss is a safe miss.** At 0.78 it fell just short of 0.8, so the app would ask me instead of warning. I'm not lowering the threshold to 0.75 to make this one case pass. With 11 examples, that would be tuning the rule to the test.
- **Names alone push Jev towards "same".** "Kahu" vs "Kahu Cloud", with no other information, came back at 0.66–0.68. That's "unsure", as I expected, but leaning towards a duplicate on name similarity alone.
- **The parent and overseas-office pairs were correctly "different", but I gave Jev the answer.** My `false` criterion names both situations explicitly, so this mainly shows that Jev follows the criteria, not that it would work out these cases on its own.
- **`rename` is the code filter's blind spot, as designed.** "Weta Ridge" and "WR Digital" share no words, so code called them different and Jev was never asked, even though b's notes say "Formerly Weta Ridge".

### What changed for v2, and why

Two changes, one to the code filter and one to the question. `--version v2` switches both.

**1. Code: look beyond the names before deciding "different".**

In v1, a pair whose names shared no words was called different without asking Jev. That silently missed the rebrand. v2 still settles those pairs in code, *unless* the websites match or one company's notes mention the other's name:

```python
def host(url):
    """The website's host without scheme, path or www, e.g. 'fernbird.example'."""
    if not url:
        return None
    return re.sub(r"^(https?://)?(www\.)?", "", url.lower()).split("/")[0]


def mentions(company, other_name):
    """Do company's notes contain other_name (after normalising both)?"""
    words = " ".join(normalise(other_name))
    return bool(company.get("notes")) and f" {words} " in f" {' '.join(normalise(company['notes']))} "

# inside code_decision(), after the name checks:
    if version != "v1":
        same_site = host(a.get("website")) is not None and host(a.get("website")) == host(b.get("website"))
        if same_site or mentions(a, b["name"]) or mentions(b, a["name"]):
            return None   # ask Jev
    return "different"
```

The mention check matches whole words only, so notes saying "Weta Ridgeway" wouldn't count as mentioning "Weta Ridge". Checked with `--dry-run`, with no request: v2 sends **9 of 11** pairs to Jev instead of 8. The new one is `rename`.

**2. Question: tell Jev how to weigh the evidence.** The `true`/`false` criteria are unchanged. The instructions gain one sentence:

| | Instructions |
|---|---|
| v1 | "Do `a` and `b` refer to the same company: the same employer someone would apply to?" |
| v2 | "...someone would apply to? **Weigh the evidence: the same website, or notes saying one is a former or other name of the other, is strong evidence. Similar names alone are weak evidence either way.**" |

In v1, pairs with the same website only just cleared 0.8 (0.83–0.85), and the name-only pair leaned towards "same" (0.67). The hope is that website-backed pairs move clearly above 0.8, name-only pairs move towards the middle, and the rebrand scores high now that Jev can see it. Expected answers for v2 are the same as v1.

**The risk to watch:** "similar names alone are weak evidence" could pull down `partial-evidence`, where only one company has a website. It could also pull down `short-name`, where the websites share a host but the paths differ (`/careers`).

### v2 (live, 2026-09-23, run twice)

Raw data: [results/v2-2026-09-23T121541.json](results/v2-2026-09-23T121541.json) (run 1) and [results/v2-2026-09-23T122314.json](results/v2-2026-09-23T122314.json) (run 2). About $0.00018 for 9 requests, 0.3–0.9 s each.

**9/11 matched expected in both runs**, the same count as v1 but with different misses. **Every v2 mistake is "ask me", never a wrong action.**

| Pair | Expected | v1 p(same) | v2 p(same) run 1 / run 2 | v1 → v2 decision | Match |
|---|---|---|---|---|---|
| legal-suffix | same | code | code | same → same | ✅ |
| macron | same | code | code | same → same | ✅ |
| short-name | same | 0.84 | **0.79 / 0.79** | same → **unsure** | ❌ |
| shared-word | different | 0.04 | 0.04 / 0.04 | different → different | ✅ |
| parent-company | different | 0.08 | 0.08 / 0.08 | different → different | ✅ |
| overseas-office | different | 0.12 | 0.13 / 0.12 | different → different | ✅ |
| country-suffix | same | 0.83 | 0.87 / 0.86 | same → same | ✅ |
| same-animal | different | 0.04 | 0.06 / 0.06 | different → different | ✅ |
| no-evidence | unsure | 0.66 | 0.54 / 0.56 | unsure → unsure | ✅ |
| partial-evidence | same | 0.78 | **0.65 / 0.66** | unsure → unsure | ❌ |
| rename | same | code (not asked) | **0.96 / 0.96** | **different → same** | ✅ |

v1 values are from run 2. v1 run 1 was within 0.02 of it.

What I noticed:
- **The code change fixed the rebrand completely.** Once the filter sent it to Jev, Jev scored it 0.96, the highest "same" in the whole experiment. The problem in v1 was never Jev's judgement; Jev just never saw the pair.
- **The question change worked on the name-only pair.** "Kahu" vs "Kahu Cloud" moved from 0.66 to 0.55, close to the middle, which is honest for two names and nothing else. The same-website pair `country-suffix` rose slightly, from 0.83 to 0.86.
- **The risk I flagged happened.** "Similar names are weak evidence" also pulled down `short-name` (0.84 → 0.79, just under the line) and `partial-evidence` (0.78 → 0.66). In `short-name` the websites differ only by `/careers`. Jev seems not to treat that as "the same website", even though code already knows the hosts match.
- **The type of mistake improved even though the count didn't.** v1's miss on `rename` was **unsafe**: the app would have silently saved a duplicate. Both v2 misses are **safe**: the app asks me. For a tool that shouldn't merge by itself, that's the direction I want mistakes to go.
- **Stable again.** Across the two v2 runs, nothing moved by more than 0.02.

## Conclusion

_Drafted by Claude from the four runs; edit to make it your own._

**What worked:** splitting the work between code and Jev. Code settled the easy pairs (capitals, macrons, legal suffixes) for free, and Jev handled the judgement calls well. It was confidently "different" for unrelated businesses sharing a word (0.04–0.06), and confidently "same" for the rebrand once it could see the notes (0.96). Answers were very stable across repeated runs, within 0.02.

**What failed:** Jev was cautious about "same". Only 3 pairs ever went above 0.85, and my evidence-weighing sentence made it more cautious, pushing two genuine duplicates into "ask me".

**The key lesson:** **give Jev facts that code has already worked out.** Code already knows that `fernbird.example` and `fernbird.example/careers` share a host. Jev had to infer it from two URL strings and didn't give it full weight. Following the mission's advice to keep arithmetic and checks in code, the next version should put facts like `"same_website_host": true` into the state, instead of asking Jev to spot them.

**Would I use it?** Yes, as a **warning before saving**, never to merge automatically. It's cheap (a fraction of a cent per check, and most pairs never reach Jev), fast (under a second), and every v2 mistake was a safe "ask me".

**Next step if I kept going:** add code-computed facts (same website host, notes mention the other name) to the state as a v3, and try it on the real company names in jobfinder's database.
