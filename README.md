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

## Resource Finder (companion to `bnreplah/cybersecuritylibrary`)

The `resource_finder` module turns the researcher into a curator. Point
it at an exported `RESOURCES_DB.js` and it will:

1. **Pull** — optionally fetch recent items from public security feeds
   for grounding context (`feedparser`).
2. **Parse** — ask Claude or Gemini to propose durable, evergreen
   additions matching the target category's schema.
3. **Verify** — GET each proposed URL with a short timeout and treat
   2xx/3xx (plus 401/403/429) as reachable; capture the page `<title>`.
4. **Emit** — write a JSON file the cybersecuritylibrary GitHub Actions
   workflow merges into `RESOURCES_DB.js` and opens a PR for review.

```bash
python -m resource_finder.discover \
  --existing-db existing.json \
  --category tools \
  --max 5 \
  --topic "AI security" \
  --out proposed.json
```

No Modal sandbox required — this runs on any vanilla GitHub Actions
runner with an `ANTHROPIC_API_KEY` or `GOOGLE_API_KEY`. See
[`resource_finder/README.md`](resource_finder/README.md) for full
schema and flag reference.

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

## Status/Contribution
This is a super-early, experimental harness. There are a number of improvements to be worked out (i.e. dataset sharing between agents, key management, etc.), literature search, that would make this way more capable. If anyone wants to add these in, feel free!
