import os

import gradio as gr
import config
from src.chatbot import chat

CUSTOM_CSS = """
/* ── Global ── */
:root {
    --primary: #2563eb;
    --primary-dark: #1d4ed8;
    --primary-light: #dbeafe;
    --bg: #f8fafc;
    --surface: #ffffff;
    --text: #1e293b;
    --text-muted: #94a3b8;
    --border: #e2e8f0;
    --shadow: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
    --shadow-lg: 0 10px 25px rgba(0,0,0,0.08);
    --radius: 12px;
    --radius-sm: 8px;
}

body {
    background: var(--bg);
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

/* ── Main Container ── */
.gradio-container {
    max-width: 800px !important;
    margin: 2rem auto !important;
    background: var(--surface) !important;
    border-radius: var(--radius) !important;
    box-shadow: var(--shadow-lg) !important;
    border: 1px solid var(--border) !important;
    padding: 0 !important;
    overflow: hidden;
}

/* ── Header ── */
.app-header {
    background: linear-gradient(135deg, var(--primary), var(--primary-dark));
    padding: 1.75rem 2rem;
    text-align: center;
    border-bottom: none;
}
.app-header h1 {
    color: #fff;
    font-size: 1.5rem;
    font-weight: 700;
    margin: 0 0 0.25rem;
    letter-spacing: -0.02em;
}
.app-header .subtitle {
    color: rgba(255,255,255,0.85);
    font-size: 0.9rem;
    margin: 0;
    font-weight: 400;
}
.app-header .badge {
    display: inline-block;
    background: rgba(255,255,255,0.2);
    color: #fff;
    font-size: 0.7rem;
    font-weight: 600;
    padding: 0.2rem 0.7rem;
    border-radius: 20px;
    margin-top: 0.5rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

/* ── Chat Area ── */
.gr-chatinterface {
    border: none !important;
    border-radius: 0 !important;
}

/* Chat message bubbles */
.gr-chatinterface .bot,
.gr-chatinterface .user {
    border: none !important;
    border-radius: var(--radius-sm) !important;
    padding: 0.75rem 1rem !important;
    font-size: 0.9rem !important;
    line-height: 1.55 !important;
    max-width: 80% !important;
    box-shadow: var(--shadow) !important;
    margin: 0.35rem 0 !important;
}

.gr-chatinterface .user {
    background: var(--primary) !important;
    color: #fff !important;
    border-bottom-right-radius: 2px !important;
    align-self: flex-end !important;
}

.gr-chatinterface .bot {
    background: #f1f5f9 !important;
    color: var(--text) !important;
    border-bottom-left-radius: 2px !important;
    align-self: flex-start !important;
}

/* ── Input Area ── */
.gr-textbox {
    border: 2px solid var(--border) !important;
    border-radius: var(--radius-sm) !important;
    background: var(--surface) !important;
    transition: border-color 0.2s;
}
.gr-textbox:focus-within {
    border-color: var(--primary) !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,0.1) !important;
}
.gr-textbox textarea {
    font-size: 0.9rem !important;
    color: var(--text) !important;
}

/* Submit button */
button.gr-button-primary {
    background: var(--primary) !important;
    border: none !important;
    border-radius: var(--radius-sm) !important;
    color: #fff !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    padding: 0.5rem 1.25rem !important;
    transition: background 0.2s, transform 0.1s !important;
}
button.gr-button-primary:hover {
    background: var(--primary-dark) !important;
    transform: translateY(-1px) !important;
}

/* ── Examples ── */
.gr-examples {
    padding: 0.75rem 1.25rem !important;
    background: #f8fafc !important;
    border-top: 1px solid var(--border) !important;
}
.gr-examples label {
    font-size: 0.75rem !important;
    font-weight: 600 !important;
    color: var(--text-muted) !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
    margin-bottom: 0.5rem !important;
}
.gr-examples button {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 20px !important;
    padding: 0.3rem 0.9rem !important;
    font-size: 0.8rem !important;
    color: var(--text) !important;
    transition: all 0.2s !important;
    cursor: pointer !important;
}
.gr-examples button:hover {
    border-color: var(--primary) !important;
    background: var(--primary-light) !important;
    color: var(--primary) !important;
}

/* ── Footer ── */
.app-footer {
    text-align: center;
    padding: 0.75rem 1rem;
    font-size: 0.72rem;
    color: var(--text-muted);
    border-top: 1px solid var(--border);
    background: #fafafa;
}
.app-footer span {
    display: inline-block;
    margin: 0 0.5rem;
}
.app-footer .dot {
    color: var(--text-muted);
}

/* ── Scrollbar ── */
::-webkit-scrollbar {
    width: 6px;
}
::-webkit-scrollbar-track {
    background: transparent;
}
::-webkit-scrollbar-thumb {
    background: #cbd5e1;
    border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
    background: #94a3b8;
}

/* ── Mobile ── */
@media (max-width: 640px) {
    .gradio-container {
        margin: 0 !important;
        border-radius: 0 !important;
        min-height: 100vh;
    }
    .app-header {
        padding: 1.25rem 1rem;
    }
    .app-header h1 {
        font-size: 1.25rem;
    }
}
"""

EXAMPLES = [
    "What's your return policy?",
    "Where is my order?",
    "How long does shipping take?",
    "Do you sell wireless headphones?",
    "I want to cancel my order",
    "My package is lost",
    "Talk to a human agent",
]

HEADER_HTML = """
<div class="app-header">
    <h1>Customer Support AI</h1>
    <p class="subtitle">Ask about orders, returns, shipping, and products. I'm here 24/7.</p>
    <span class="badge">AI-Powered</span>
</div>
"""

FOOTER_HTML = """
<div class="app-footer">
    <span>Intent routing</span>
    <span class="dot">|</span>
    <span>Knowledge-base retrieval</span>
    <span class="dot">|</span>
    <span>Guardrailed AI support</span>
</div>
"""


def respond(message, history):
    return chat(message, history)


def main():
    with gr.Blocks(
        css=CUSTOM_CSS,
        theme=config.APP_THEME,
        title=config.APP_TITLE,
    ) as demo:
        gr.HTML(HEADER_HTML)

        gr.ChatInterface(
            fn=respond,
            title=None,
            description=None,
            examples=EXAMPLES,
            cache_examples=False,
            type="messages",
        )

        gr.HTML(FOOTER_HTML)

    if os.getenv("SPACE_ID"):
        demo.launch()
    else:
        demo.launch(
            server_name=config.SERVER_NAME,
            server_port=config.SERVER_PORT,
            share=config.SHARE,
            debug=config.DEBUG,
            inline=False,
        )


if __name__ == "__main__":
    main()
