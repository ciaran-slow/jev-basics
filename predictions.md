# Step 1: predictions vs actual results

## Run 1: `my-first-run.json` (live)

State: "Junior Python developer. Remote within New Zealand. Supportive team."

| Question | Actual | Notes |
|---|---|---|
| remote_nz | yes (confidence 1) | The listing says "Remote within New Zealand" outright |
| mentoring | unknown (confidence 1) | "Supportive team" doesn't promise mentoring, as the criteria say |

## Run 2: `run-2.json` (live)

State: "Graduate developer. Weekly 1:1 mentoring with a senior engineer. Based in our Sydney office."

Written down before running:

| Question | Prediction | Reasoning | Actual | Match? |
|---|---|---|---|---|
| remote_nz | no | The job is based in a Sydney office, so it isn't remote from NZ | no (no 0.89, unknown 0.11, confidence 0.83) | ✅ |
| mentoring | yes | "Weekly 1:1 mentoring with a senior engineer" is scheduled mentoring, stated outright | yes (confidence 1) | ✅ |

What I noticed:
- Both predictions matched.
- `remote_nz` is the first answer that isn't fully certain. The listing never says "on-site only", so Jev gave `unknown` 11%. That makes sense: the `no` criterion asks for something *explicit*, and "based in Sydney" is only implied.
- `mentoring` went from `unknown` in run 1 to `yes` here with full confidence, because this listing states a schedule (weekly) and who does it (a senior engineer).
