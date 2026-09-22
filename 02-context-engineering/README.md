# 02 · Context engineering: caching, long context, reasoning budgets

> **Status:** Shipped Sep 22 · **Target:** Wed Sep 23 · **Timebox:** 2 hours

| Claude Sonnet 5, 50.8k-token prompt | quality (of 20) | all 10 fully right? | median time to first answer text | median total time | cost per question | cost per day at 1,000 questions |
|---|---|---|---|---|---|---|
| caching off, effort low | 20 | 10 / 10 | 3,459 ms | 5,288 ms | $0.1052 | $105 |
| caching off, effort high | 19 | 9 / 10 | 4,666 ms | 7,142 ms | $0.1074 | $107 |
| **caching on, effort low** | 19 | 9 / 10 | **2,417 ms** | **4,145 ms** | **$0.0254** | **$25** (about $13 once the cache is warm) |
| caching on, effort high | 19 | 9 / 10 | 3,828 ms | 6,091 ms | $0.0272 | $27 (about $15 once the cache is warm) |

10 customer questions × 4 configurations, 40 calls, run on 2026-09-22, graded 0–2 per question by Claude Haiku 4.5 against hand-written answer keys. The one dropped point in three configurations is the same question (Q04, see below). Raw answers, timings, token counts and the judge's reasons for every call are in [results.json](results.json).

**What the numbers say**

- **Caching is the big lever.** A warm cache read costs $0.0133 per question against $0.1052 without caching (8× cheaper), and the first answer text arrives about a second sooner. The only cost is the first call in each block, which pays 1.25× to write the cache: $0.134, more than an uncached call. Every call after that is cheap. The "cost per question" column averages one write with nine reads; with steady traffic (a question at least every 5 minutes) nearly every call is a read.
- **Effort high bought nothing here.** It used 50–60% more output tokens and added about 1.2–1.4 seconds before the first answer text (1.9 seconds to the end of the answer), and quality didn't move. Effort low already scored 19–20 out of 20. These questions, including the multi-step arithmetic ones, were not hard enough for Sonnet 5 to need extra thinking. A harder question set, or a smaller model, is where effort would earn its cost.
- **Effort changes are cache-busting.** Switching effort invalidates the cached prompt, so a system that picks effort per question would pay a cache write far more often. The harness runs each effort level as its own block for exactly this reason.
- **Quality doesn't depend on caching.** Cached and uncached calls see identical prompt bytes, and the scores match to within one point. Caching is a pure cost and speed lever.

**Rule of thumb (from this run):** if the same large block of reference text goes into every call, turn caching on. It pays for itself from the second call within five minutes and makes answers start faster. Leave effort at low for lookup-and-policy questions like these, and only raise it after an eval shows a question type it gets wrong. Then route just those questions to a separate high-effort path, rather than switching effort call by call and losing the cache.

**Q04, the one question that lost points.** The customer asks for a price adjustment on a pan that turns out to be a final-sale item. Every answer correctly said no and gave the right reason. The key also requires saying the pan is still under its 120-month warranty; three of the four answers left that out or only hinted at it, and the judge marked those 1 of 2. The answer key was not changed after seeing the results.

## The brief

Put the store's full policy handbook and a long catalog export in the prompt (aim for 50k+ tokens). Ask 10 customer questions four ways: caching off/on x reasoning low/high. Chart cost, latency and answer quality.

- **Touch:** Prompt caching, long-context prompting, reasoning / thinking-effort settings
- **Reuses:** 01 (client code), `data/`
- **Done when:** A 2x2 table of cost / latency / quality, and a one-paragraph rule of thumb for when each lever pays.

## What I built

**The long context.** A policy handbook and a full catalog export for Tom's Kitchen, both new in [`../data/`](../data/) and both written by Claude, go into the system prompt verbatim. Together they come to **50,798 input tokens** on Claude Sonnet 5.

- [`data/policies/`](../data/policies/) has nine Markdown pages: returns and exchanges, shipping, warranty, prices and promotions, payments and gift cards, the Pantry Club loyalty program, care and use, FAQ, and an internal support playbook. They are written to agree with the session 01 data (30-day returns, free shipping over $75, the $15 Dutch oven surcharge, kettle known issue KI-001). They also carry the kinds of rule interactions that trip up support agents: bundle discounts shared across pieces, final sale overriding every other return route, label fees taken from the card share of a split payment first, and so on. Session 03's RAG bot will use the same pages.
- [`data/catalog-export.csv`](../data/catalog-export.csv) has 157 products as 217 variant rows (one per color or size, the way a merchandising system exports them). The first 30 products are `products.json`, unchanged; the rest come from [`catalog_export.py`](../data/catalog_export.py), which is deterministic. The columns include list and sale price, a final-sale flag, induction and dishwasher compatibility, warranty months, voltage, heavy-item surcharge and restock date.

**The questions.** [questions.json](questions.json) has 10 customer questions, each with an answer key worked out by hand from the handbook and catalog (Claude wrote the questions and the keys): the facts a correct answer must contain, plus one wrong claim that scores zero. Most need a policy and a catalog row together, and six involve arithmetic. For example, Q10 asks for the total on a first order of a bundle plus a knife with `WELCOME10`. The code doesn't apply to bundles, so the right answer is $199.10, not $187.20.

**The harness.** [run.ts](run.ts) asks every question four ways, one call at a time, with streaming:

| | effort low | effort high |
|---|---|---|
| **caching off** | no `cache_control` | no `cache_control` |
| **caching on** | `cache_control: ephemeral` on the system block | same |

The only code difference between caching off and on is one `cache_control` marker on the system prompt. Adaptive thinking is on in all four configurations, and `output_config.effort` sets how hard the model thinks. Each call records the time to the first visible answer text, the total time, and all four usage counts: uncached input, cache write, cache read and output (which includes thinking tokens). Cost is computed from those counts at Sonnet 5 list prices: $2 per 1M input tokens, $2.50 cache write (5-minute TTL), $0.20 cache read, $10 output. The harness warns if a caching-off call shows any cache activity, or if a caching-on call after the first shows no cache read. It stops cleanly at a $4.00 spend cap.

Two details the docs made clear before any code ran:

- **Changing effort invalidates the cache.** So each effort level runs as its own block of 10, and each caching-on block pays for one cache write on its first question.
- **The prompt contains nothing that varies.** "Today" is fixed to 2026-09-23 so date questions have one right answer, and a clock-based date would break the prefix match on every call anyway.

**Grading.** Claude Haiku 4.5 judges each answer against the key with a forced JSON schema: 2 = every required fact right, 1 = some, 0 = none or the forbidden claim. `--rescore` re-grades saved answers without re-asking the questions.

Versions: `@anthropic-ai/sdk` 0.128.0, `zod` 4.6.5, Node 26. Models `claude-sonnet-5` (answers) and `claude-haiku-4-5` (judge).

## How to run it

You need Node 22 or newer and an Anthropic API key with a few dollars of credit.

```bash
cd ai-builds
cp .env.example .env.local        # then fill in ANTHROPIC_API_KEY
cd 02-context-engineering
npm install
npm run tokens                    # counts the prompt's tokens, free
npm run smoke                     # one question, caching off, about 11 cents
npm start                         # 40 calls plus 40 judge calls, about 5 minutes and $2.70
```

`npm start` writes every answer, timing and token count to `results.json` as it goes, then prints the tables. `npm start -- --report` reprints the tables from `results.json` without calling the API. `npm start -- --rescore` re-runs only the judge (about 6 cents).

To change the model, prices or spend cap, edit the constants at the top of [run.ts](run.ts). To rebuild the catalog export, run `python3 data/catalog_export.py` from the repo root. Changing the handbook or catalog changes the token count and the answer keys, so check [questions.json](questions.json) afterwards.

## What surprised me

_TODO (Tom writes this, not the agent)_

## What it cost

| Item | Amount |
|---|---|
| Time spent | TOM: fill in (the full run itself took 5 minutes of wall-clock) |
| API / credits, final run (40 answers + 40 judge calls) | $2.70: answers $2.65 (caching off $2.13, caching on $0.52), judge $0.05 |
| API / credits, whole session | about $2.81, including the one-question smoke test ($0.11). Token counting is free. |
| Would cost at 1,000 requests a day | Caching off: about $105 a day ($3,200 a month). Caching on: about $13–15 a day ($400–450 a month) with steady traffic |

Tokens across the final 40 answers: 1,016,692 uncached input, 101,454 cache write, 913,086 cache read, 18,261 output (output includes thinking). Prices used: Sonnet 5 at $2 / $10 per 1M input / output tokens, cache writes 1.25× input, cache reads 0.1× input; Haiku 4.5 at $1 / $5. The prompt counts as 50,798 tokens on Sonnet 5 and 39,236 on Haiku 4.5; the same text costs 30% more tokens on the newer tokenizer.

## When I'd use this in production, and when I wouldn't

_TODO (Tom writes this, not the agent)_

## Links

- Docs I actually used: [Anthropic prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching), [Anthropic effort](https://platform.claude.com/docs/en/build-with-claude/effort), [Anthropic adaptive thinking](https://platform.claude.com/docs/en/build-with-claude/adaptive-thinking), [token counting](https://platform.claude.com/docs/en/build-with-claude/token-counting), [pricing](https://platform.claude.com/docs/en/about-claude/pricing)
- Post:
