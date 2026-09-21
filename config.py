import os


def _detect_device():
    try:
        import torch
    except ImportError:
        return "cpu"

    return "cuda" if torch.cuda.is_available() else "cpu"


def _get_theme():
    try:
        from gradio.themes import Soft
        return Soft()
    except ImportError:
        return "soft"


# Model settings
MODEL_NAME = "microsoft/DialoGPT-medium"
DEVICE = os.getenv("CHATBOT_DEVICE") or _detect_device()

# Generation parameters
MAX_NEW_TOKENS = 100
TOP_K = 50
TOP_P = 0.95
TEMPERATURE = 0.7
MAX_HISTORY_TURNS = 5
MAX_INPUT_LENGTH = 1024
ENABLE_GENERATIVE_FALLBACK = os.getenv("ENABLE_GENERATIVE_FALLBACK", "false").lower() == "true"

# App settings
APP_TITLE = "Customer Support Chatbot"
APP_DESCRIPTION = "AI-powered customer support chatbot using Microsoft's DialoGPT-medium"
APP_THEME = _get_theme()
SHARE = os.getenv("GRADIO_SHARE", "false").lower() == "true"
SERVER_NAME = os.getenv("GRADIO_SERVER_NAME", "0.0.0.0")
SERVER_PORT = int(os.getenv("PORT", "7860"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# RAG settings
ENABLE_RAG = os.getenv("ENABLE_RAG", "true").lower() == "true"
RAG_EMBEDDING_MODEL = os.getenv(
    "RAG_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
)
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))
RAG_SIMILARITY_THRESHOLD = float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.3"))
RAG_RRF_K = int(os.getenv("RAG_RRF_K", "60"))
RAG_RERANK = os.getenv("RAG_RERANK", "true").lower() == "true"

# Security settings
MAX_MESSAGE_CHARS = int(os.getenv("MAX_MESSAGE_CHARS", "1000"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))
RATE_LIMIT_MAX = int(os.getenv("RATE_LIMIT_MAX", "20"))
INJECTION_SCORE_THRESHOLD = int(os.getenv("INJECTION_SCORE_THRESHOLD", "2"))
ENABLE_SANDWICH_DEFENSE = os.getenv("ENABLE_SANDWICH_DEFENSE", "true").lower() == "true"
ENABLE_ENCODING_DEFENSE = os.getenv("ENABLE_ENCODING_DEFENSE", "true").lower() == "true"
ENABLE_RATE_LIMITING = os.getenv("ENABLE_RATE_LIMITING", "true").lower() == "true"
