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

### GitHub Actions

- **CI** (`.github/workflows/ci.yml`): runs tests and linting on every push to `main`/`develop` and on PRs to `main`.
- **Sync to HF** (`.github/workflows/sync-to-hf.yml`): auto-pushes `main` to your Hugging Face Space on every push.

### Setup

1. Create two repository secrets in **Settings > Secrets and variables > Actions**:

| Secret | Value |
|---|---|
| `HF_TOKEN` | Your Hugging Face access token (create at https://huggingface.co/settings/tokens) |
| `HF_SPACE` | Your Space ID, e.g. `username/customer-support-ai-chatbot` |

2. Push to `main`. The CI workflow runs tests. The sync workflow pushes to your Space.

### Manual Sync

```bash
git remote add space https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE_NAME
git push space main
```

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `GRADIO_SHARE` | `false` | Enable Gradio public share tunnel |
| `GRADIO_DEBUG` | `false` | Enable Gradio debug mode |
| `CHATBOT_DEVICE` | auto/CPU | Override model device when AI fallback is enabled |
| `ENABLE_GENERATIVE_FALLBACK` | `false` | Enable optional DialoGPT fallback |

## Deployment Notes

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
