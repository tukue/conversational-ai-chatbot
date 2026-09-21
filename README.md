---
title: Customer Support AI Chatbot
emoji: 💬
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: 4.44.1
app_file: app.py
python_version: "3.10"
suggested_hardware: cpu-upgrade
models:
  - microsoft/DialoGPT-medium
tags:
  - chatbot
  - gradio
  - transformers
  - customer-support
  - portfolio
short_description: E-commerce support chatbot with intent routing, FAQs, product search, guardrails, and a Transformer fallback.
---

# Customer Support AI Chatbot

[![Deploy to HuggingFace](https://img.shields.io/badge/%F0%9F%A4%97-Deploy%20to%20Spaces-blue)](https://huggingface.co/spaces/new?sdk=gradio)

An e-commerce customer support chatbot built with Gradio and Hugging Face Transformers. It combines rule-based intent routing, FAQ retrieval, product search, safety guardrails, and a DialoGPT fallback model for general conversation.

This project is designed as an AI portfolio project: it shows practical product thinking, deployment readiness, and clean separation between UI, routing, safety, knowledge base, and model code.

## Live Demo

There are two ways to make the chatbot public:

- **Permanent portfolio demo:** deploy this repository to Hugging Face Spaces with the Gradio SDK.
- **Temporary public demo:** run the app locally with Gradio `share=True`, which creates a temporary `https://*.gradio.live` URL.

For recruiters and portfolio links, Hugging Face Spaces is the recommended option because the URL stays available after your local computer shuts down.

## What The Chatbot Can Do

- Answer common support questions about returns, shipping, payments, damaged items, lost packages, exchanges, discounts, and gift cards.
- Search a small product catalog from `data/products.json`.
- Ask for an order number when needed and reuse recent chat history when the user already provided one.
- Block sensitive personal information such as SSNs, card numbers, and phone numbers.
- Redirect off-topic or unsafe prompts back to customer support.
- Use `microsoft/DialoGPT-medium` only as a fallback when a question is not handled by the structured support logic.

## What This Demonstrates

| Capability | Implementation |
|---|---|
| AI application design | Intent routing plus optional generative fallback |
| Retrieval | FAQ and product catalog search over local JSON knowledge sources |
| Responsible AI | Input/output guardrails for PII, profanity, off-topic prompts, and policy violations |
| Backend quality | Modular Python services with focused tests |
| Product thinking | Common customer support workflows: returns, shipping, orders, payments, products, complaints |
| Deployment basics | Dockerfile and environment-driven configuration |
| CI/CD | GitHub Actions for tests, linting, and auto-sync to Hugging Face Spaces |

## Architecture

```text
User message
    |
    v
Input guardrails
    |
    v
Intent classifier (fuzzy matching)
    |
    +--> Template response
    +--> FAQ search (TF-IDF + stemming)
    +--> Product search (TF-IDF + stemming)
    +--> DialoGPT fallback
    |
    v
Output guardrails
    |
    v
Gradio chat response
```

## Repository Structure

```text
.
├── app.py                  # Gradio UI and Hugging Face Space entrypoint
├── config.py               # Model, generation, and app settings
├── runtime.txt             # Python version pinning for HF Spaces
├── requirements.txt        # Runtime dependencies for Hugging Face Spaces
├── requirements-dev.txt    # Dev dependencies (pytest, ruff)
├── README.md               # Project docs and Hugging Face Space metadata
├── .gitignore              # Excludes caches, environments, and model files
├── .github/
│   └── workflows/
│       ├── ci.yml          # CI: tests + lint on push/PR
│       └── sync-to-hf.yml  # Auto-sync to Hugging Face Spaces
├── data/
│   ├── faq.json            # FAQ knowledge base
│   └── products.json       # Demo product catalog
├── src/
│   ├── chatbot.py          # Main routing and chat logic
│   ├── guardrails.py       # Input and output safety checks
│   ├── intent.py           # Intent classifier with fuzzy matching
│   ├── knowledge_base.py   # FAQ and product search helpers
│   ├── model.py            # Transformers model loading and generation
│   └── templates.py        # Support response templates
└── tests/                  # Unit and integration tests
```

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open the local Gradio URL printed in the terminal.

## Development

```bash
pip install -r requirements-dev.txt
python -m pytest tests/ -v
ruff check . --select E,F,W --ignore E501
```

## CI/CD

### Workflows

- **CI** (`.github/workflows/ci.yml`): lint + tests on every push/PR.
- **Deploy** (`.github/workflows/deploy.yml`): validates + auto-deploys to HuggingFace on push to `main`.

### Deploy to HuggingFace (One-Time Setup)

No tokens needed — uses HuggingFace's built-in GitHub integration.

1. Go to https://huggingface.co/new-space
   - **Name**: `customer-support-chatbot`
   - **SDK**: Gradio
   - **Python**: 3.10
   - **License**: choose any

2. Open your Space → **Settings** → **Connect repository**

3. Connect this GitHub repo:
   - **Branch**: `main`
   - **Directory**: `/` (root)

4. Done. Every push to `main` auto-deploys.

### Verify It Works

```bash
# Push a change
git push origin main

# Check your Space
open https://huggingface.co/spaces/YOUR_USERNAME/customer-support-chatbot
```

### Environment Variables

Set these in your Space Settings → Variables and secrets if needed:

| Variable | Default | Purpose |
|---|---|---|
| `ENABLE_GENERATIVE_FALLBACK` | `false` | Enable DialoGPT fallback |
| `ENABLE_RAG` | `true` | Enable RAG retrieval |
| `ENABLE_RATE_LIMITING` | `true` | Enable rate limiting |
| `GRADIO_SHARE` | `false` | Gradio public tunnel |

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `GRADIO_SHARE` | `false` | Enable Gradio public share tunnel |
| `GRADIO_DEBUG` | `false` | Enable Gradio debug mode |
| `CHATBOT_DEVICE` | auto/CPU | Override model device when AI fallback is enabled |
| `ENABLE_GENERATIVE_FALLBACK` | `false` | Enable optional DialoGPT fallback |

## Deploy to Hugging Face Spaces

### Option A — Auto-sync via GitHub Actions (recommended)

This pushes code to your Space automatically on every commit to `main`.

**1. Create the Space**

Go to https://huggingface.co/spaces and click **Create new Space**.

| Field | Value |
|---|---|
| Space name | `conversational-ai-chatbot` (or your choice) |
| License | Choose any |
| SDK | **Gradio** |
| Visibility | Public (for portfolio) |

Click **Create Space**. Note the Space ID shown in the URL: `https://huggingface.co/spaces/YOUR_USERNAME/SPACE_NAME`.

**2. Add the GitHub secret**

Go to your GitHub repo **Settings > Secrets and variables > Actions > New repository secret**:

| Name | Value |
|---|---|
| `HF_SPACE` | `YOUR_USERNAME/SPACE_NAME` (e.g. `tukue/conversational-ai-chatbot`) |

No `HF_TOKEN` is needed. The sync uses `huggingface-cli upload` which works with the Space's public endpoint.

**3. Push to `main`**

```bash
git push origin main
```

The GitHub Action runs automatically and syncs all files to your Space. Check the workflow status at **Actions** tab in your repo.

**4. Set environment variables (optional)**

In your Space, go to **Settings > Variables and secrets > Variables** and add:

| Name | Value | Purpose |
|---|---|---|
| `ENABLE_GENERATIVE_FALLBACK` | `true` | Enable DialoGPT fallback for unmatched questions |
| `MODEL_NAME` | `microsoft/DialoGPT-small` | Use a smaller/faster model (optional) |

**5. Verify**

Your Space URL: `https://huggingface.co/spaces/YOUR_USERNAME/SPACE_NAME`

The Space builds automatically. First build takes 2-3 minutes (installing dependencies). Subsequent pushes sync in ~30 seconds.

---

### Option B — Manual push via Git

If you prefer pushing directly from your terminal:

```bash
# Add the Space as a remote
git remote add space https://huggingface.co/spaces/YOUR_USERNAME/SPACE_NAME

# Push
git push space main
```

For private repos, generate a [HuggingFace Access Token](https://huggingface.co/settings/tokens) with write access and use:

```bash
git remote add space https://YOUR_TOKEN@huggingface.co/spaces/YOUR_USERNAME/SPACE_NAME
git push space main
```

---

### Option C — Upload via CLI

Install the HuggingFace CLI and upload files without git:

```bash
pip install huggingface_hub
huggingface-cli login  # only if repo is private
huggingface-cli upload \
  --repo-type space \
  --include "*.py" "*.txt" "*.json" "*.md" "*.yml" \
  --exclude ".git/*" "__pycache__/*" \
  YOUR_USERNAME/SPACE_NAME .
```

---

### Troubleshooting

| Problem | Fix |
|---|---|
| Space shows "Build failed" | Check **Logs** tab. Usually a missing dependency in `requirements.txt`. |
| App loads but chat doesn't work | Ensure `app_file: app.py` is in the README frontmatter (it is by default). |
| Slow first response | Normal. DialoGPT downloads on first use (~500MB). Subsequent loads are cached. |
| Out of memory on free tier | Set `MODEL_NAME=microsoft/DialoGPT-small` in Space variables, or remove DialoGPT entirely. |
| Sync workflow skipped | Check that `HF_SPACE` secret is set correctly in GitHub repo settings. |
| Port errors | HF Spaces handles ports automatically. Do not set `SERVER_PORT` manually. |

### Deployment Notes

- Do not commit downloaded model files. The model is loaded from the Hugging Face Hub at runtime and cached by the Space.
- The first fallback response can be slower because the model may need to download and load.
- Most customer support responses are handled without the Transformer model, so normal FAQ and product queries are fast.
- `cpu-upgrade` is recommended for a smoother demo. The app can run on CPU, but DialoGPT-medium may be slow on basic hardware.
- For a faster or lighter Space, set `MODEL_NAME=microsoft/DialoGPT-small` in the Space environment variables.
- Use `GRADIO_SHARE=true` only for local temporary public links. Keep it disabled on Hugging Face Spaces.

## Portfolio Talking Points

- Hybrid chatbot design: deterministic support workflows first, generative model fallback second.
- Clear safety controls for PII, toxic language, and unsupported topics.
- Consulting-ready boundaries: simulated business workflows, explicit limitations, and safe handoff to secure forms for private data.
- Deployable Gradio interface with Hugging Face Space metadata.
- CI/CD pipeline with GitHub Actions and auto-sync to Hugging Face Spaces.
- Modular Python code that separates UI, business logic, retrieval, guardrails, and model inference.
- Test coverage for routing, guardrails, knowledge base behavior, templates, and model helper functions.

## Limitations

- The order lookup is simulated. A production app would connect to a secure order management API.
- The FAQ and product search are keyword based. A production app could use embeddings and semantic search.
- DialoGPT is a lightweight conversational fallback, not a modern instruction-tuned support model.
- The guardrails are simple regex and keyword checks. Production systems should add stronger moderation and logging.
