INTENTS = {
    "greeting": ["hello", "hi", "hey", "good morning", "good evening", "howdy"],
    "closing": ["bye", "goodbye", "see you", "thanks", "thank you"],
    "order_status": ["where is my order", "track", "order status", "shipping status", "has my order shipped", "order update", "tracking"],
    "cancel_order": ["cancel order", "cancel my order", "stop order", "cancel"],
    "return_request": ["return", "refund", "send back", "return item", "money back", "return policy"],
    "shipping_info": ["shipping time", "shipping cost", "delivery", "free shipping", "how long", "ship"],
    "payment_issue": ["payment declined", "card not working", "payment error", "charge", "billing", "transaction", "declined"],
    "payment_method": ["payment methods", "how to pay", "credit card", "paypal", "what payment"],
    "product_inquiry": ["product", "item", "buy", "price", "cost", "available", "in stock", "tell me about", "looking for", "do you sell"],
    "damaged_item": ["damaged", "broken", "defective", "arrived damaged", "not working"],
    "exchange": ["exchange", "different size", "wrong size", "swap", "size"],
    "lost_package": ["lost package", "missing package", "not delivered", "stolen", "package is lost", "package lost"],
    "change_address": ["change address", "wrong address", "shipping address", "my address"],
    "discount": ["discount", "promo code", "coupon", "voucher", "sale"],
    "gift_card": ["gift card", "gift voucher", "store credit"],
    "complaint": ["unhappy", "frustrated", "terrible", "awful", "bad service", "angry", "disappointed", "worst", "horrible"],
    "contact_human": ["human", "real person", "agent", "manager", "speak to", "talk to a", "representative"],
    "escalate": ["escalate", "complaint", "supervisor", "manager"],
}


def classify_intent(message):
    message_lower = message.lower().strip()

    # First check for multi-intent (e.g. "I want to return AND get a refund")
    matched_intents = []
    for intent, keywords in INTENTS.items():
        for kw in keywords:
            if kw in message_lower or message_lower.startswith(kw):
                matched_intents.append(intent)
                break

    if not matched_intents:
        return "general"

    # Priority ordering for routing
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
