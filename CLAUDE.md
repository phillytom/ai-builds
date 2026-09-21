# CLAUDE.md

Working rules for this repo. It is a public portfolio: 20 small AI builds, one folder each (`01-…` to `20-…`), all set in the same fictional online store. Optimize for a working result inside a two-hour timebox, and for small, readable code that is easy to explain in a write-up.

## Session protocol

When Tom says "start session NN":

1. Read `NN-*/README.md` (the brief) and the README of every build it reuses.
2. Check the current docs for each tool in the brief before writing code. This stack changes monthly. State the versions you are using.
3. Propose a plan in 8 bullets or fewer that fits in about 75 minutes of build time. Cut scope now, not at minute 70. Wait for a go-ahead.
4. Build inside `NN-*/` only. Shared synthetic data lives in `data/`.
5. To close out: run `git status` and `git diff --stat`, then list every file you created or changed, including anything outside the session folder or outside the repo (memory files, settings, configs). No silent changes.

## Hard rules

- **Secrets:** only in `.env.local` (gitignored). Never print, echo, log or pass a credential on the command line. Add new variable names, never values, to `.env.example`.
- **Data:** synthetic only. No real customer, tenant or personal data. Anything sensitive goes in `data/private/` (gitignored).
- **Write-ups:** do not write "What surprised me" or "When I'd use this in production" in any README. Those sections are Tom's. You may fill in "What I built", "How to run it" and the cost table, using real numbers.
- **Cost:** default to the cheapest adequate model and set spend caps where the tool supports them. Ask before anything likely to cost more than $5. Record actual tokens, credits and wall-clock time in the session README.
- **Isolation:** each build is self-contained with its own `package.json` or `requirements.txt`. No root-level dependencies.
- **Languages:** prefer TypeScript / Node. Use Python where the ecosystem lives there (fine-tuning, some agent and browser libraries).
- **Edits:** for scripted file edits, prefer a small Python script over `sed`.
- **Large files:** do not commit model weights, datasets, or media over 10 MB. Link to them.
- **Git:** commit early and often with plain messages (`03: add reranker`). Never rewrite history. Never push unless asked.

## Definition of done

- It runs from a clean clone by following "How to run it".
- The session README leads with a screenshot, GIF or results table.
- The tracker row in the root `README.md` is updated with status and date.
