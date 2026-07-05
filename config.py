import os

import torch

# Model settings
MODEL_NAME = os.getenv("MODEL_NAME", "microsoft/DialoGPT-medium")
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Generation parameters
MAX_NEW_TOKENS = 100
TOP_K = 50
TOP_P = 0.95
TEMPERATURE = 0.7
MAX_HISTORY_TURNS = 5
MAX_INPUT_LENGTH = 1024

# App settings
APP_TITLE = "Customer Support Chatbot"
APP_DESCRIPTION = "AI-powered customer support chatbot using Microsoft's DialoGPT-medium"
APP_THEME = "soft"
SHARE = os.getenv("GRADIO_SHARE", "false").lower() == "true"
SERVER_NAME = os.getenv("GRADIO_SERVER_NAME", "0.0.0.0")
SERVER_PORT = int(os.getenv("PORT", "7860"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
