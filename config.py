import os


def _detect_device():
    try:
        import torch
    except ImportError:
        return "cpu"

    return "cuda" if torch.cuda.is_available() else "cpu"

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
APP_THEME = "soft"
SHARE = os.getenv("GRADIO_SHARE", "false").lower() == "true"
SERVER_NAME = "0.0.0.0"
DEBUG = os.getenv("GRADIO_DEBUG", "false").lower() == "true"
