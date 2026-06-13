import re

INTENTS = {
    "greeting": ["hello", "hi", "hey", "good morning", "good evening", "howdy"],
    "closing": ["bye", "goodbye", "see you", "thanks", "thank you", "thank"],
    "order_status": ["where is my order", "track", "tracks", "tracked", "tracking", "order status", "shipping status", "has my order shipped", "order update"],
    "cancel_order": ["cancel order", "cancel my order", "cancelled order", "cancelling order", "stop order"],
    "return_request": ["return", "returns", "returned", "refund", "refunds", "refunded", "send back", "return item", "money back", "return policy"],
    "shipping_info": ["shipping time", "shipping cost", "delivery", "free shipping", "how long", "ship", "ships", "shipped", "shipping"],
    "payment_issue": ["payment declined", "card not working", "payment error", "charge", "charges", "charged", "billing", "transaction", "declined"],
    "payment_method": ["payment methods", "how to pay", "credit card", "paypal", "what payment"],
    "product_inquiry": ["product", "products", "item", "items", "buy", "price", "prices", "cost", "costs", "available", "in stock", "tell me about", "looking for", "do you sell"],
    "damaged_item": ["damaged", "broken", "defective", "arrived damaged", "not working"],
    "exchange": ["exchange", "exchanges", "different size", "wrong size", "swap", "size", "sizes"],
    "lost_package": ["lost package", "missing package", "not delivered", "stolen", "package is lost", "package lost"],
    "change_address": ["change address", "wrong address", "shipping address", "my address"],
    "discount": ["discount", "discounts", "promo code", "promo codes", "coupon", "coupons", "voucher", "vouchers", "sale", "sales"],
    "gift_card": ["gift card", "gift cards", "gift voucher", "gift vouchers", "store credit"],
    "complaint": ["unhappy", "frustrated", "terrible", "awful", "bad service", "angry", "disappointed", "worst", "horrible"],
    "contact_human": ["human", "real person", "agent", "agents", "manager", "managers", "speak to", "talk to a", "representative"],
    "escalate": ["escalate", "escalated", "escalation", "supervisor", "manager"],
}


def _word_boundary_match(keyword, text):
    if not keyword.strip():
        return False
    escaped = re.escape(keyword)
    return bool(re.search(rf"\b{escaped}\b", text, re.IGNORECASE))


def classify_intent(message):
    message_lower = message.lower().strip()

    matched_intents = []
    for intent, keywords in INTENTS.items():
        for kw in keywords:
            if _word_boundary_match(kw, message_lower):
                matched_intents.append(intent)
                break

    if not matched_intents:
        return "general"

    priority = [
        "escalate", "contact_human", "complaint",
        "damaged_item", "lost_package",
        "cancel_order", "return_request", "exchange",
        "payment_issue",
        "order_status", "change_address",
        "shipping_info",
        "product_inquiry", "discount", "gift_card", "payment_method",
        "greeting", "closing",
    ]

    for p in priority:
        if p in matched_intents:
            return p

    return matched_intents[0]
