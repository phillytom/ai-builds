# 01 · Frontier APIs side by side

> **Status:** In progress · **Target:** Mon Sep 21 · **Timebox:** 2 hours

| Model | intent | order id | SKU | sentiment | urgency | action | all 6 right | median latency | p95 latency | cost per email | cost per day at 1,000 emails |
|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-haiku-4-5 | 90% | 100% | 93% | 90% | 80% | 90% | 60% | 1,041 ms | 1,540 ms | $0.00171 | $1.71 |
| gpt-5.4-mini | 87% | 100% | 100% | 80% | 77% | 90% | 67% | 1,120 ms | 2,310 ms | $0.00092 | $0.92 |
| gemini-3.8-flash | 100% | 100% | 100% | 93% | 80% | 93% | 80% | 960 ms | 3,429 ms | $0.00094 | $0.94 |

10 emails × 3 runs per model, 90 calls, run on 2026-09-21. Accuracy is exact match per field against hand labels. No call returned invalid JSON and none needed a retry. Two labels were adjusted after the first scoring pass (see the notes under What I built). Raw output for every call is in [results.json](results.json).

## The brief

Seed the shared store data in `data/` (small: ~20 products, ~30 orders, 10 messy support emails with hand labels). Then send the same 10 emails to all three providers with one forced JSON schema (intent, order id, sentiment, urgency, suggested action) and score each against the labels.

- **Touch:** Anthropic, OpenAI and Gemini APIs; structured outputs / tool calling
- **Reuses:** —
- **Done when:** A results table (accuracy, latency, cost per call) for all three providers is in this README.

## What I built

Shared demo data for the whole series, in [`../data/`](../data/): a fictional store called Tom's Kitchen with 30 products, 30 orders and 10 messy support emails. Claude wrote the data and the labels, and I reviewed the labels. The emails include typos, an order number that appears only in a subject line, a mistyped order number, a tracking number placed next to the order number, a vague email with no details, and two angry customers.

One function, `classify(provider, model, email)` in [classify.ts](classify.ts), sends an email to Anthropic, OpenAI or Gemini and returns the parsed result, latency and token counts. All three use the same Zod schema and the same system prompt, which includes the 30-line product catalog so the model can return a SKU. Each provider uses its own structured-output feature, so the JSON is constrained by the API and not just requested in the prompt:

| Provider | Call | Schema goes in | Reasoning setting |
|---|---|---|---|
| Anthropic | `messages.create` | `output_config.format` via `zodOutputFormat` | thinking off (the default on Haiku 4.5) |
| OpenAI | `responses.create` | `text.format` via `zodTextFormat` | `reasoning.effort: "none"` |
| Gemini | `models.generateContent` | `responseJsonSchema` via `z.toJSONSchema` | `thinkingLevel: LOW`, the lowest this model accepts (`MINIMAL` returns a 400) |

The schema has seven fields: intent, order id, product SKU, sentiment, urgency, suggested action, and a free-text product issue that is not scored.

[run.ts](run.ts) sends every email to every model three times, one call at a time so latency is clean. It scores the six labeled fields by exact match and works out cost from real token counts and the `PRICES` table at the top of the file. Invalid JSON gets up to 2 retries. Rate-limit and server errors get up to 3 retries with backoff, and calls the API refuses are kept out of the scores and flagged in the table.

Things to know before reading the numbers:

- Ten emails is a small set. One email is worth 10 points of accuracy, and nearly every miss came from the same few emails.
- The labels are one person's judgment, and I changed two after seeing the first scores. On EM-003 (a polite "is this normal?" about a faulty kettle lid) the action label was `replace`, all three models said `answer_question` on all nine calls, and I decided they were right. On EM-010 (a deliberately vague email) the intent now accepts either `return_request` or `other`. The same 90 model answers were re-scored with `npm start -- --rescore`, with no new API calls. Before the changes the "all 6 right" column read 50%, 50% and 70%.
- One prompt rule misfired, and I left it in. "Escalate when there is a safety risk" led two models to escalate a customer who only said a Dutch oven was too heavy to lift safely (EM-007). Fixing the prompt after seeing the results would have flattered the scores.
- A Claude model wrote the labels and the prompt. That could favor Claude. It did not: Gemini matched the labels best.
- Gemini's free tier allows 20 requests a day per model, which is fewer than this run needs. The Gemini project needs billing turned on.

SDK versions: `@anthropic-ai/sdk` 0.127.0, `openai` 7.20.0, `@google/genai` 2.23.0, `zod` 4.6.5, Node 26.

## How to run it

You need Node 22 or newer and an API key for each provider. The Gemini key needs billing enabled.

```bash
git clone <this repo> && cd ai-builds
cp .env.example .env.local        # then fill in ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY
cd 01-frontier-apis
npm install
npm run smoke                     # one email to Claude, about a fifth of a cent
npm start                         # all 90 calls, about 2 minutes and $0.11
```

`npm start` prints the results table and writes `results.json`. `npm start -- --rescore` re-scores the saved answers against the current labels without calling any API. To run one provider, use `npm start -- --only openai` (or `anthropic`, `gemini`). To test one provider on a single email, use `npx tsx run.ts --smoke --only gemini`.

To change models or prices, edit `MODELS` and `PRICES` at the top of [run.ts](run.ts). To rebuild the demo data, run `python3 data/seed_store.py` from the repo root.

## What surprised me

Claude was 2x the price of the others - still negligible at fractions of a penny per email, but it does add up.

## What it cost

| Item | Amount |
|---|---|
| Time spent | about 1 h 20 min (TOM: confirm) |
| API / credits, final run (90 calls) | $0.107: Claude $0.051, GPT $0.028, Gemini $0.028 |
| API / credits, whole session | about $0.30, including two earlier runs that Gemini errors cut short and the single-email tests |
| Would cost at 1,000 requests a day | Claude Haiku 4.5 $1.71 a day ($51 a month); GPT-5.4-mini $0.92 a day ($28 a month); Gemini 3.8 Flash $0.94 a day ($28 a month) |

Average tokens per email:

| Model | input | output | price per 1M tokens, input / output |
|---|---|---|---|
| claude-haiku-4-5 | 1,426 | 57 | $1.00 / $5.00 |
| gpt-5.4-mini | 890 | 56 | $0.75 / $4.50 |
| gemini-3.8-flash | 854 | 80 | $0.75 / $3.75 |

The prompt is identical for all three. Claude's tokenizer counts it as about 1,430 tokens where the other two count about 870, and that, more than the list price, is why Claude costs more here. Gemini's output count includes its thinking tokens, which are billed as output. Prices are from each provider's pricing page on 2026-09-21. None of this uses prompt caching or batch pricing, which would cut the input cost of the repeated system prompt on all three.

## When I'd use this in production, and when I wouldn't

Gemini did the best here in my opinion, but we are using fake emails and fake data.  We’d need to test this on a richer, larger real product catalog using real emails to make a call.
In my opinion, this test makes it clear that *any* online ecommerce store needs AI pre-processing of emails.

## Links

- Docs I actually used: Anthropic structured outputs (from the API reference bundled with Claude Code; TOM: add the public link), [OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs), [OpenAI reasoning](https://developers.openai.com/api/docs/guides/reasoning), [Gemini structured output](https://ai.google.dev/gemini-api/docs/structured-output), [Gemini thinking](https://ai.google.dev/gemini-api/docs/thinking), [Gemini rate limits](https://ai.google.dev/gemini-api/docs/rate-limits)
- Post:
