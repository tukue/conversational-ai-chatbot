import re


INTENTS = {
    "greeting": [
        "hello", "hi", "hey", "good morning", "good evening", "howdy",
        "greetings", "sup", "yo", "what's up",
    ],
    "closing": [
        "bye", "goodbye", "see you", "thanks", "thank you", "thank",
        "appreciate", "cheers", "nice", "great",
    ],
    "order_status": [
        "where is my order", "track", "tracks", "tracked", "tracking",
        "order status", "shipping status", "has my order shipped",
        "order update", "where's my stuff", "where is my stuff",
        "when will it arrive", "when will it get here",
        "where is it", "where'd it go",
    ],
    "cancel_order": [
        "cancel order", "cancel my order", "cancelled order",
        "cancelling order", "stop order", "abort order",
    ],
    "return_request": [
        "return", "returns", "returned", "refund", "refunds", "refunded",
        "send back", "return item", "money back", "return policy",
        "send it back", "get my money",
    ],
    "shipping_info": [
        "shipping time", "shipping cost", "delivery", "free shipping",
        "how long", "ship", "ships", "shipped", "shipping",
        "how many days", "delivery time", "deliver",
    ],
    "payment_issue": [
        "payment declined", "card not working", "payment error",
        "charge", "charges", "charged", "billing", "transaction",
        "declined", "won't go through",
    ],
    "payment_method": [
        "payment methods", "how to pay", "credit card", "paypal",
        "what payment", "do you take", "do you accept",
    ],
    "product_inquiry": [
        "product", "products", "item", "items", "buy", "price",
        "prices", "cost", "costs", "available", "in stock",
        "tell me about", "looking for", "do you sell",
        "what do you have", "what do you sell",
    ],
    "damaged_item": [
        "damaged", "broken", "defective", "arrived damaged",
        "not working", "cracked", "shattered",
    ],
    "exchange": [
        "exchange", "exchanges", "different size", "wrong size",
        "swap", "size", "sizes", "too big", "too small",
    ],
    "lost_package": [
        "lost package", "missing package", "not delivered", "stolen",
        "package is lost", "package lost", "never arrived",
        "never got it",
    ],
    "change_address": [
        "change address", "wrong address", "shipping address",
        "my address", "update address", "new address",
    ],
    "discount": [
        "discount", "discounts", "promo code", "promo codes",
        "coupon", "coupons", "voucher", "vouchers", "sale", "sales",
        "deal", "deals",
    ],
    "gift_card": [
        "gift card", "gift cards", "gift voucher", "gift vouchers",
        "store credit",
    ],
    "complaint": [
        "unhappy", "frustrated", "terrible", "awful", "bad service",
        "angry", "disappointed", "worst", "horrible", "rip off",
        "scam", "unacceptable", "ridiculous",
    ],
    "contact_human": [
        "human", "real person", "agent", "agents", "manager",
        "managers", "speak to", "talk to a", "representative",
        "live person", "real human", "speak with", "talk with",
    ],
    "escalate": [
        "escalate", "escalated", "escalation", "supervisor",
        "manager", "higher up", "report",
    ],
}


def _word_boundary_match(keyword, text):
    if not keyword.strip():
        return False
    escaped = re.escape(keyword)
    return bool(re.search(rf"\b{escaped}\b", text, re.IGNORECASE))


def _levenshtein(a, b):
    if len(a) < len(b):
        return _levenshtein(b, a)
    if not b:
        return len(a)
    prev = range(len(b) + 1)
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            curr.append(
                min(prev[j + 1] + 1, curr[j] + 1, prev[j] + (ca != cb))
            )
        prev = curr
    return prev[-1]


def _fuzzy_match(keyword, text, threshold=0.7):
    words = text.split()
    kw_len = len(keyword.split())
    for i in range(len(words) - kw_len + 1):
        candidate = " ".join(words[i : i + kw_len])
        k, c = len(keyword), len(candidate)
        if k == 0 or c == 0:
            continue
        dist = _levenshtein(keyword, candidate)
        if 1 - dist / max(k, c) >= threshold:
            return True
    return False


def classify_intent(message):
    message_lower = message.lower().strip()

    if not message_lower:
        return "general"

    matched_intents = []
    for intent, keywords in INTENTS.items():
        for kw in keywords:
            if _word_boundary_match(kw, message_lower):
                matched_intents.append(intent)
                break

        if intent not in matched_intents:
            for kw in keywords:
                if len(kw) > 5 and _fuzzy_match(kw, message_lower, threshold=0.85):
                    matched_intents.append(intent)
                    break

    if not matched_intents:
        return "general"

    priority = [
        "escalate", "contact_human", "complaint",
        "damaged_item", "lost_package",
        "cancel_order", "return_request", "exchange",
        "payment_issue",
        "shipping_info", "change_address", "order_status",
        "product_inquiry", "discount", "gift_card", "payment_method",
        "greeting", "closing",
    ]

    for p in priority:
        if p in matched_intents:
            return p

    return matched_intents[0]
