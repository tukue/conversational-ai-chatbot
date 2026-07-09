---
title: Customer Support AI Chatbot
emoji: 💬
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: 4.44.1
app_file: app.py
python_version: 3.10
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

## Architecture

```text
User message
    |
    v
Input guardrails
    |
    v
Intent classifier
    |
    +--> Template response
    +--> FAQ search
    +--> Product search
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
├── requirements.txt        # Runtime dependencies for Hugging Face Spaces
├── README.md               # Project docs and Hugging Face Space metadata
├── .gitignore              # Excludes caches, environments, and model files
├── data/
│   ├── faq.json            # FAQ knowledge base
│   └── products.json       # Demo product catalog
├── src/
│   ├── chatbot.py          # Main routing and chat logic
│   ├── guardrails.py       # Input and output safety checks
│   ├── intent.py           # Keyword-based intent classifier
│   ├── knowledge_base.py   # FAQ and product search helpers
│   ├── model.py            # Transformers model loading and generation
│   └── templates.py        # Support response templates
└── tests/                  # Unit and integration tests
```

## Local Setup

Use Python 3.10 or newer.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

On macOS/Linux, activate the environment with:

```bash
source .venv/bin/activate
```

Open the local URL printed by Gradio, usually:

```text
http://127.0.0.1:7860
```

## Temporary Public URL With Gradio Share

If you want to quickly share the chatbot from your local machine, enable Gradio sharing:

```powershell
$env:GRADIO_SHARE="true"
python app.py
```

Gradio will print a temporary public URL that looks like this:

```text
https://your-random-name.gradio.live
```

Use this option for quick testing, demos, or sending the app to someone before deploying to Hugging Face Spaces.

Important notes:

- The public Gradio share URL is temporary.
- The URL stops working when your local app stops running.
- Do not use Gradio share for a permanent portfolio link.
- For a permanent public deployment, use Hugging Face Spaces.

On macOS/Linux, use:

```bash
GRADIO_SHARE=true python app.py
```

## Configuration

The app works without secrets. These optional environment variables are supported:

```bash
MODEL_NAME=microsoft/DialoGPT-medium
PORT=7860
GRADIO_SERVER_NAME=0.0.0.0
GRADIO_SHARE=false
DEBUG=false
MAX_MESSAGE_CHARS=1000
```

For Hugging Face Spaces, keep `GRADIO_SHARE=false`. Spaces already gives the app a public URL, so a Gradio share tunnel is not needed.

For a temporary local public URL, set `GRADIO_SHARE=true` before running `python app.py`.

## Security And Safety Design

This project is intentionally scoped like a consulting AI proof of concept: it demonstrates useful automation while keeping clear boundaries around sensitive workflows.

- Empty and very long messages are rejected before routing.
- SSNs, credit card numbers, phone numbers, and email addresses are blocked at input and output.
- Prompt-injection attempts such as requests to ignore instructions or reveal hidden prompts are refused.
- The chatbot avoids collecting private customer details directly in chat and points users to secure forms for addresses, photos, labels, and account-specific information.
- Gradio analytics are disabled in `app.py`.
- The app uses deterministic support flows first and only calls the Transformer model as a fallback.
- Model weights are downloaded from Hugging Face at runtime and should not be committed to the repository.

For a production client project, the next security upgrades would be authentication, secure backend APIs for order lookup, audit logging without raw PII, rate limiting, and a stronger moderation layer.

## Run Tests

```bash
python -m pytest tests -v
```

`pytest` is not included in the deployment requirements because Hugging Face Spaces only needs runtime packages. Install it locally if you want to run the tests:

```bash
pip install pytest
```

## Hugging Face Spaces Deployment

1. Push this repository to GitHub.
2. Go to https://huggingface.co/spaces.
3. Click **Create new Space**.
4. Choose **Gradio** as the SDK.
5. Name the Space, for example `customer-support-ai-chatbot`.
6. Choose public visibility for a portfolio demo.
7. After the Space is created, copy its Git URL.
8. Add the Space as a remote:

```bash
git remote add space https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE_NAME
```

9. Push to the Space:

```bash
git push space main
```

If your local branch has a different name, use:

```bash
git push space HEAD:main
```

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
- Modular Python code that separates UI, business logic, retrieval, guardrails, and model inference.
- Test coverage for routing, guardrails, knowledge base behavior, templates, and model helper functions.

## Limitations

- The order lookup is simulated. A production app would connect to a secure order management API.
- The FAQ and product search are keyword based. A production app could use embeddings and semantic search.
- DialoGPT is a lightweight conversational fallback, not a modern instruction-tuned support model.
- The guardrails are simple regex and keyword checks. Production systems should add stronger moderation and logging.

## Final Checklist Before Deployment

- `app.py` exists at the repository root.
- `requirements.txt` contains only runtime dependencies.
- `README.md` has Hugging Face Space YAML metadata.
- `.gitignore` excludes virtual environments, caches, and model weights.
- No `.env`, API keys, private customer data, or downloaded model files are committed.
- The app starts locally with `python app.py`.
- Optional local public sharing works with `GRADIO_SHARE=true python app.py`.
- The Space is created with the Gradio SDK.
- The Space build logs show successful dependency installation.
- The Space UI loads and responds to example prompts.
