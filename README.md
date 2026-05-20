# AI Researcher
[![Twitter Follow](https://img.shields.io/twitter/follow/mattshumer_?style=social)](https://twitter.com/mattshumer_)

[Be the first to know when I publish new AI builds + demos!](https://tally.so/r/w2M17p)

An autonomous AI researcher. It takes a research objective, breaks it into experiments, spins up separate agents with access to their own GPUs to run these experiments, and delivers a paper-style writeup with findings.

## How it Works
- Decomposes your prompt into experiments and assigns them to specialist researcher agents.
- Each agent can launch GPU-enabled sandboxes to train models/run inference/etc., evaluate, and collect evidence.
- Based on the results of these experiments, the orchestrator can decide to finalize, or run more experiments.
- The orchestrator goes over all of the results and turns them into a coherent "paper".

## Run it (web notebook, one command)
The fastest way to use it:
```
python run_app.py
```
This installs missing deps, starts the API + frontend, and opens the notebook. If Google/Modal keys aren’t set, the UI will prompt you and save them locally before the run starts.

## Keys Needed
- **LLM key** (at least one):
  - Google AI Studio: `GOOGLE_API_KEY` (for Gemini 3 Pro)
  - Anthropic: `ANTHROPIC_API_KEY` (for Claude Opus 4.5)
- **Modal tokens**: `MODAL_TOKEN_ID` and `MODAL_TOKEN_SECRET` (for GPU sandboxes)
- Add them to `.env` in the repo root, or paste them into the web prompt when asked.

## Model Selection
Choose between **Gemini 3 Pro** and **Claude Opus 4.5** from the dropdown in the web UI, or via CLI with `--model`.

## Optional CLI
Prefer the terminal?
```
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python main.py "Does label smoothing improve ViT-Base on CIFAR-10?" --mode single --gpu any --model gemini-3-pro-preview
```
Orchestrator (multi-agent):
```
python main.py "Characterize scaling laws for sparse attention transformers" \
  --mode orchestrator --num-agents 3 --max-rounds 3 --max-parallel 2 --gpu any
```
Dry run:
```
python main.py "Sanity check the pipeline" --mode orchestrator --test-mode
```

## Deploy to Railway

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template?template=https://github.com/mattshumer/ai-researcher&referralCode=mattshumer)

**Steps:**
1. Click the button above (or go to Railway and select "Deploy from GitHub repo")
2. Connect your GitHub account and select this repo (or your fork)
3. Railway will automatically detect the Dockerfile and build the app
4. Once deployed, open the app URL and enter your API keys in the UI

**Optional environment variables** (if you want server-side defaults):
- `GOOGLE_API_KEY` - Google AI Studio key for Gemini 3 Pro
- `ANTHROPIC_API_KEY` - Anthropic key for Claude Opus 4.5
- `MODAL_TOKEN_ID` and `MODAL_TOKEN_SECRET` - For GPU sandboxes

Note: Users can also enter their own keys directly in the web UI without setting environment variables.

## Cyber Research Bot (GitHub → Discord)

A second mode of this repo runs as a GitHub-driven cybersecurity research bot
that posts to a Discord channel. It pulls from a curated set of security feeds
(news, advisories, CISA KEV, NVD CVEs ≥7.0, vendor research, arXiv cs.CR),
uses an LLM to score relevance and write short briefings, and posts the highest-
signal items via a Discord webhook. It also accepts deep-dive research
requests filed as GitHub Issues.

**Set up:**
1. Create a Discord webhook in your channel (Server Settings → Integrations → Webhooks).
2. In this repo: Settings → Secrets and variables → Actions → add secrets:
   - `CYBER_BOT_DISCORD_WEBHOOK_URL` — the webhook URL
   - `ANTHROPIC_API_KEY` and/or `GOOGLE_API_KEY`
3. (Optional) under *Variables*, set `CYBER_BOT_MODEL` to `claude` (default) or `gemini`.

**What it does:**
- `.github/workflows/cyber_research_digest.yml` — runs on cron (twice a day),
  posts a digest of the top scored items to Discord, and commits an updated
  dedup state file back to the repo so the same items aren't re-posted.
- `.github/workflows/cyber_research_on_demand.yml` — fires when an issue is
  opened with the `research-request` label. The bot rephrases the issue title
  / `topic:` line into a research topic, narrows recent feed material to the
  most relevant items, asks the LLM for an analyst-style writeup, and posts
  the deep-dive to Discord. Use the *Cyber Research Request* issue template.

**Run locally:**
```
pip install -r requirements.txt
export DISCORD_WEBHOOK_URL=...   # webhook URL
export ANTHROPIC_API_KEY=...
python -m cyber_bot.digest --dry-run    # score + print without posting
python -m cyber_bot.digest              # post a digest
python -m cyber_bot.on_demand "BGP hijacking incidents this month" --dry-run
```

Sources are configured in `cyber_bot/config.py` — add or remove feeds there.

## Status/Contribution
This is a super-early, experimental harness. There are a number of improvements to be worked out (i.e. dataset sharing between agents, key management, etc.), literature search, that would make this way more capable. If anyone wants to add these in, feel free!