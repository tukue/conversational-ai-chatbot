import re

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
    message_lower = message.lower()

    for pattern in TOXIC_PATTERNS:
        if re.search(pattern, message_lower):
            return False, "I'm here to help with customer support. Please keep our conversation respectful."

    for pattern in PII_PATTERNS:
        if re.search(pattern, message):
            return False, (
                "Please don't share sensitive personal information here. "
                "For security, I'll transfer you to a secure form."
            )

    return True, ""


def check_output(response, message):
    response_lower = response.lower()

    for pattern in PII_PATTERNS:
        if re.search(pattern, response):
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
