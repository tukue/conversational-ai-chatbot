import os
import re

MAX_MESSAGE_CHARS = int(os.getenv("MAX_MESSAGE_CHARS", "1000"))

SAFE_INPUT_MESSAGE = "Please enter a customer support question so I can help."
LONG_INPUT_MESSAGE = (
    f"Please keep your message under {MAX_MESSAGE_CHARS:,} characters so I can handle it safely."
)
PII_INPUT_MESSAGE = (
    "Please don't share sensitive personal information here. "
    "For security, use the secure support form for private details."
)

# Toxic / abusive patterns to block
TOXIC_PATTERNS = [
    r"\b(fuck(ing|ed|er)?|shit(ty)?|asshole|bastard|bitch|dick|cunt)\b",
    r"\b(kill|die|suicide|harm myself)\b",
    r"\b(spam|scam|fraud)\s*(link|website|url)\b",
]

# PII patterns — never echo these back
PII_PATTERNS = [
    r"\b\d{3}-\d{2}-\d{4}\b",              # SSN
    r"\b\d{16}\b",                          # raw credit card
    r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",  # formatted card
    r"\b\d{3}[-]?\d{3}[-]?\d{4}\b",        # phone (US)
    r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",  # email
]

BUSINESS_BLOCKLIST = [
    "refund more than", "refund full amount",
    "refund over", "refund beyond",
    "refund outside", "refund above",
    "change return policy",
    "give me a discount",
    "free product",
    "waive the fee",
    "override",
]

PROMPT_INJECTION_PATTERNS = [
    r"ignore (all )?(previous|prior|above) instructions",
    r"forget (all )?(previous|prior|above) instructions",
    r"reveal (your )?(system|developer) prompt",
    r"show (your )?(system|developer) prompt",
    r"act as (an? )?(unrestricted|uncensored|jailbroken)",
]
SUPPORTED_TOPICS = [
    "order", "return", "refund", "shipping", "delivery", "track",
    "product", "item", "price", "payment", "card", "paypal",
    "account", "login", "password", "address", "cancel",
    "exchange", "size", "damage", "broken", "defective",
    "gift card", "discount", "coupon", "promo",
    "store", "policy", "contact", "support", "help",
    "headphone", "shirt", "bottle", "laptop", "yoga", "candle", "shoe",
]


def check_input(message):
    if message is None:
        return False, SAFE_INPUT_MESSAGE

    message = str(message).strip()
    if not message:
        return False, SAFE_INPUT_MESSAGE

    if len(message) > MAX_MESSAGE_CHARS:
        return False, LONG_INPUT_MESSAGE

    message_lower = message.lower()

    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, message_lower):
            return False, (
                "I can't follow requests to bypass my support role. "
                "I can help with orders, returns, shipping, products, and payments."
            )

    for pattern in TOXIC_PATTERNS:
        if re.search(pattern, message_lower):
            return False, "I'm here to help with customer support. Please keep our conversation respectful."

    for pattern in PII_PATTERNS:
        if re.search(pattern, message, re.IGNORECASE):
            return False, PII_INPUT_MESSAGE

    return True, ""


def check_output(response, message):
    response_lower = response.lower()

    for pattern in PII_PATTERNS:
        if re.search(pattern, response, re.IGNORECASE):
            return False, "I can't share that information. Let me connect you with a human agent."

    for phrase in BUSINESS_BLOCKLIST:
        if phrase in response_lower:
            return False, (
                "I'm not authorized to make policy changes. "
                "Let me connect you with a supervisor who can help."
            )

    return True, response


def is_on_topic(message):
    message_lower = message.lower()

    off_topic_signals = [
        "recipe", "cook", "weather", "news", "politics",
        "religion", "medical", "diagnosis", "legal advice",
        "homework", "math problem", "essay",
    ]

    for signal in off_topic_signals:
        if signal in message_lower:
            return False

    # Default: allow if no off-topic signals detected
    return True
