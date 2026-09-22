# Step 2: Exploring JevMade

Three projects from [JevMade](https://jevmade.com/), each using Jev for a different purpose:

| Project | Purpose | Question types used |
|---|---|---|
| [jev-review](https://github.com/devagrawal09/jev-review) | Review code changes | Noul, Choice, Score |
| [jev-search](https://github.com/superagents-lab/jev-search) | Interpret a search request and rank results | Choice, Noul |
| [Claude Code Trace](https://github.com/delexw/claude-code-trace) | Judge how efficiently a coding-agent session went | Noul, Score |

All notes come from reading source code on 2026-09-23. I did not run any of these projects. "Verified" means I saw it in the code; "claim" means it is only stated in a README or on JevMade.

---

## 1. jev-review (devagrawal09)

Code read at commit [`31f8960`](https://github.com/devagrawal09/jev-review/tree/31f89602797fb7bea007f8a480bf368bf564954e). Main file: `src/review/judgments.ts`.

**What it does:** A command-line code reviewer for a Git diff or a whole codebase. It saves a report and shows it in a local dashboard.

**What state Jev receives, and what it returns.** Instead of one big question, it runs a chain of small ones:

1. **Screen** each changed file. State: the file's patch and any changed tests. Five **Noul** questions give a probability for each risk: correctness, security, reliability, compatibility and test gap. Each question lists `true` and `false` criteria with examples, such as "an authorization check is removed".
2. **Profile** the riskiest files. A **Choice** picks the kind of change (behavior, interface, refactor, ...) and a **Score** rates how closely a human should review it.
3. **Locate**: for each high-risk signal, a **Choice** picks which diff hunk is the strongest evidence. It has a `noMatch` option, which works like `unknown` in our starter.
4. **Classify**: a **Choice** names the mechanism. It includes a `noIssue` option.
5. **Severity**: a **Score** rates the likely production impact.
6. **Route**: only for severe findings, a **Choice** picks which reviewer should investigate.

**What ordinary code does with the answers** (verified in `workflow.ts` and `config.ts`):
- Keeps only screening signals with probability ≥ 0.7 (`SCREEN_THRESHOLD`) and follows at most 8 (`MAX_FOLLOW_UPS`).
- Drops a finding if Jev picks `noMatch` or `noIssue`, or if location confidence is below 0.55.
- Routes to a reviewer only when severity ≥ 1.5, and marks `request_changes` instead of `comment` when severity ≥ 2 (on a 0–3 scale).
- Runs at most 3 calls at once, then sorts findings by severity.

Each step's question depends on the previous answer, so the steps are **separate requests sequenced in code**. The mission README makes the same point: questions in one request are independent.

**What I could verify vs claims:**
- ✅ Verified: every question, threshold and the sequencing described above.
- ⚠️ Claim: the README says findings are "review prompts, not proof of a defect". That's an honest caveat, but I haven't checked how accurate the findings are.
- Not checked: the codebase-scan questions (`codebase-judgments.ts`), the dashboard and the linked post on X.

**Small part I could try:** Step 1 on its own. Send one small diff as state, ask a few Noul questions (for example "does this patch introduce a bug?"), and compare the probabilities on a harmless diff with a clearly buggy one.

---

## 2. jev-search (superagents-lab)

Code read at commit [`67027d0`](https://github.com/superagents-lab/jev-search/tree/67027d0185a9b22eb2a178f0eb15250d12ddabe6). Main files: `src/lib/typesafe.ts` and `src/lib/pipeline.ts`. Live demo: [jev.s1.dev](https://jev.s1.dev).

**What it does:** Web search in plain language, such as "What do Reddit users think of the Framework laptop?". Jev works out what you mean, the search engines (through Search1API) fetch results, and Jev ranks them. It doesn't generate any answers, only links and snippets.

**What state Jev receives, and what it returns.** Two kinds of request:

1. **Understand the request** (one request, `inferIntent`). State: the request text, today's date and a few candidate keyword queries built in code.
   - **Choice** `window`: how recent the results should be (for example any time, or this month).
   - **Noul** `source_<id>` for each of 12 sources (Reddit, Hacker News, GitHub, arXiv, ...): would this source fit? For example, Reddit: yes if "the request names Reddit ... or asks what people are saying".
   - **Choice** `query`: which candidate is the best keyword query.
   - **Choice** `entity`: which candidate is just the name of the thing, for catalogue sites like IMDb.
2. **Rank the results** (`rerank`, batches of up to 40). State: the request plus each result's title and snippet. One **Noul** per result asks whether it's about the subject the user asked for. The criteria explicitly exclude "a different meaning of the same word, a different product, a person with the same name".

**What ordinary code does with the answers** (verified in `pipeline.ts`):
- Uses a source only if its probability is ≥ 0.6. If none pass, it falls back to default sources. If you set sources or a time window yourself, your choice wins over Jev's.
- Runs the searches in parallel, drops results that are clearly older than 1.5× the time window, and uses the Noul probability as each result's relevance score.
- Starts a Google search with your exact words while Jev is still thinking, and reuses it if Jev picks the same query. That's a speed trick.
- If one engine or one ranking call fails, it shows a warning on that source instead of failing the whole search.

**What I could verify vs claims:**
- ✅ Verified: the questions, the 0.6 source threshold, the batching and the error handling per source.
- ⚠️ Mismatch: JevMade lists this project as using **Choice and Score**, but the code I read uses **Choice and Noul**. "Score" only appears in the part that translates answers from the Vercel gateway.
- ⚠️ Claim: "Jev Search itself does not store queries". I didn't audit the deployment. The README itself notes that Cloudflare request logs can contain the search query.
- Not checked: the live demo, or how good the ranking is.

**Small part I could try:** The relevance question. Give one request like "python" (the programming language) with a mix of snippets about the language and about snakes, and see whether Jev's Noul probabilities separate them.

---

## 3. Claude Code Trace (delexw)

Code read at the commit pinned on JevMade, [`8495b15`](https://github.com/delexw/claude-code-trace/tree/8495b15e10f2bb6911609d0ce9b51bfa9db5428b). Main files: `src-tauri/src/efficiency/jev.rs`, `redact.rs` and `score.rs`.

**What it does:** A viewer for Claude Code session logs (the JSONL files in `~/.claude/projects`). It works as a desktop app, a web app or a terminal UI. An optional Jev feature judges how efficiently the agent worked in a session.

**What state Jev receives, and what it returns.** State is a summary of the session, not the raw log:
- `task`: the first user message, turn count, duration and total tokens.
- `actions`: each tool call's tool name, category, short summary, duration, whether it errored, and how many identical calls happened.
- `signals`: counts of tool calls, failures, repeats, subagents, context growth and thinking blocks/characters. The thinking text itself is not sent.
- `selected_excerpts`: a few selected excerpts from the session.

It asks 10 questions in one request:
- 9 **Noul** questions, for example: steady progress? useful tool calls? redundant work? excessive exploration? thrashing? effective recovery? efficient token use? useful subagents? task completed? The redundant-work question is detailed. It says re-running tests after an edit does *not* count as redundant.
- 1 **Score** question, `thinkingBalance`, on a 5-level scale from "far too little thinking" to "far more thinking than needed". The middle level is best.

**What ordinary code does with the answers** (verified in `score.rs`):
- Flips the "bad" questions (redundant work, thrashing, excessive exploration) so that higher always means better.
- Turns probabilities into 0–100 scores and combines them with fixed weights: progress 25%, tool use 20%, focus 15%, exploration 10%, recovery 10%, token use 10%, thinking 5%, task completed 5%.
- For thinking, gives full marks at the middle level, and scores too little and too much thinking the same.

**Privacy handling** (verified in `redact.rs`): before sending, regexes remove bearer tokens, `api_key=`/`password=`-style values, URL tokens, private keys and `*_KEY=`/`*_TOKEN=` environment values, and replace your home folder path with `~`. The README says the app shows you the redacted payload and waits for confirmation. I didn't check that UI step in code.

**What I could verify vs claims:**
- ✅ Verified: all 10 questions, the weights and the redaction patterns.
- ⚠️ Limitation: regex redaction only catches secrets that match those patterns. Something like a key pasted without a label would get through, so the confirmation step matters.
- ⚠️ Claim: that the score reflects real efficiency. The weights are the author's choice, and nothing in the code checks them against real outcomes.
- Not checked: the full-transcript mode, the dashboard UI and the result caching.

**Small part I could try:** Describe a short made-up agent session as JSON (a task, 5–6 actions with one repeated read, one error and a retry) and ask 2–3 of these Noul questions. Then change one detail, such as removing the repeated read, and see whether the "redundant work" probability drops.

---

## What these three have in common

- **Code decides, Jev judges.** In all three, Jev gives a probability or a choice, and ordinary code applies thresholds, weights, fallbacks and ordering.
- **An escape option.** jev-review has `noMatch` and `noIssue`, and our starter has `unknown`. They give Jev a safe answer when the evidence is missing.
- **Detailed criteria.** The best questions spell out what counts and what doesn't, with examples. That matches what we saw in step 1, where "explicitly" in the criteria affected the answer.
- **Dependent steps are sequenced in code.** jev-review makes separate calls when one answer decides the next question.
