# Mission 11: Experiment with Jev

Start by getting a simple Jev call working. Then explore what people are
building on JevMade and try three different use cases yourself.

Work in your own project or learning repo. Keep each experiment small: a
script, notebook or simple interface that shows the input and Jev's answer.

## 1. Get a simple call working

This folder includes a Python starter that uses the standard library. It
asks two Choice questions about a fictional job listing.

From your local copy of the Launchpad repo:

```sh
cd missions/11-build-with-jev
```

TypeSafe has paused new sign-ups, so the starter calls Jev through
OpenRouter. Create an [OpenRouter API key](https://openrouter.ai/keys) and
put it in a `.env` file in this folder (already gitignored):

```sh
OPENROUTER_API_KEY=your-key-here
```

Then run:

```sh
python3 demo.py --live --output my-first-run.json
```

This makes one API request and saves the input and response. Calls may incur
charges. Use a new output filename each time. Keep your key out of commits,
screenshots, browser frontends and coding-agent conversations.

Open the saved JSON beside `demo.py`. Find the state, questions, allowed
choices and returned answers. Explain what you sent and what came back.

Copy the starter into your own repo. Change the listing text in `STATE`
and predict the answers before making another call. Compare the prediction
with the actual response.

If you are waiting for a key, inspect the recorded call:

```sh
python3 demo.py --replay sample-response.json
```

Replay makes no request. It always shows the saved response, even if you
change `STATE`. Arrange access for a live call and mark any replayed results
as recorded rather than fresh predictions.

## 2. Explore JevMade

Browse [JevMade](https://jevmade.com/). Choose three projects that use Jev
for different purposes and follow their links to the original repos or demos.

For each, write a few notes:

- What does the application do?
- What state does Jev receive, and what decision does it return?
- What does ordinary code do with that answer?
- What small part could you try yourself?

Distinguish what you can verify from the maker's claims. If the code or
question format is unavailable, say so.

Some starting points from the session:

| Project | What to investigate |
|---|---|
| [DMX preview](https://x.com/thekitze/status/2100570975175877106) | Simple rules alongside judgements about usefulness, post type and topic |
| [Your Signal](https://github.com/MithrilMan/your-signal) | Source code for reversible X timeline filtering |
| [Jev Ultrafast](https://github.com/browser-use/jev-ultrafast) | Choosing a browser action and target |
| [Jev Trader](https://github.com/jarrodwatts/jev-trader) | Buy/sell choices with limits checked in code |
| [Elevator Three](https://github.com/mrmt/elevator-three) | Choosing the next scene or phrase in an instrument |

DMX's linked announcement is a next-version preview. Keep any trading
experiment simulated. Review what data a demo sends before trying it.

## 3. Experiment with three different use cases

Choose three distinct things to try, inspired by your exploration or your
own ideas. For example:

- Filter saved posts against your interests.
- Route support messages to a team.
- Choose the next action for a character or interactive scene.

Three prompt variations for the same task count as one use case. You can
share the API-calling code across all three experiments.

For each use case:

1. Write down the input, the question and the answers your code can use.
2. Build a small working call. Show the input and the raw response.
3. Try a handful of examples, including a clear case and an ambiguous or
   incomplete one. Write your expected answers before running them.
4. Read the results. Change the question, criteria or state and rerun the
   same examples. Keep both sets of results.
5. Write a short conclusion: what worked, what failed and whether you would
   use Jev for this task.

For a creative task, describe acceptable behaviour rather than insisting
there is one correct answer. You might want a range of musical choices but
still require them to belong to the current scene's allowed options.

### Tips while experimenting

Start with Choice if named options fit your task. Score uses ordered
criteria; Noul returns a probability from 0 to 1 for a proposition.
Use the [quickstart](https://docs.typesafe.ai/introduction/quickstart)
and [question-type reference](https://docs.typesafe.ai/introduction).

The starter's validator checks Choice answers against `QUESTIONS`. Adapt it
if you switch to Score or Noul. Explicit checks or Pydantic can validate the
reply; neither establishes that the decision is correct.

Keep requests deliberate and bounded. Use safe sample data and reversible
local actions. Handle failed requests visibly, and keep arithmetic and
permission checks in code. An `unknown` choice can be useful when the input
does not establish an answer.

Questions in one request are independent. Sequence dependent decisions in
code. The hosted model takes text or JSON state, so describe a visual scene
rather than sending it an image.

Confidence is not proof of correctness. Choice and Score include confidence;
Noul has no separate confidence field. Read outputs yourself before deciding
whether a threshold would help.

## Finish with a comparison

Save all three experiments and a short comparison in your repo:

| Use case | What you tried | What happened | Would you use it? |
|---|---|---|---|
| Your first experiment | Input and question | Observations from your runs | Why or why not? |
| Your second experiment | Input and question | Observations from your runs | Why or why not? |
| Your third experiment | Input and question | Observations from your runs | Why or why not? |

Include links to the projects that inspired you, instructions for running
your code and saved results without credentials. Link the work from your
learning repo if you used a separate project repo.

Be ready to show an interesting result from each use case and explain which
one you would explore further. Label any fixtures or recorded responses;
model behaviour on new inputs remains untested until you make live calls.

If you have time, trace an experiment in Langfuse or expand the most promising
one using the eval approach from [Mission 10](../10-evaluate-jobfinder/).
