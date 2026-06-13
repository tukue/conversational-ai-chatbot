import re
import config
from src.intent import classify_intent
from src.templates import get_template
from src.knowledge_base import FAQSearch, ProductSearch
from src.guardrails import check_input, check_output, is_on_topic


tokenizer, model = None, None
faq = FAQSearch()
products = ProductSearch()


def _extract_order_number(message):
    match = re.search(r'\b(\d{5,})\b', message)
    return match.group(1) if match else None


def _find_order_in_history(history):
    if not history:
        return None
    for user_msg, _ in reversed(history):
        num = _extract_order_number(user_msg)
        if num:
            return num
    return None


def _suggestion(intent):
    suggestions = {
        "order_status": "You can also track your order anytime in your account under 'My Orders'.",
        "return_request": "Need a prepaid return label? Just share your email and I'll send one.",
        "shipping_info": "You can check estimated delivery times on any product page.",
        "product_inquiry": "Would you like me to check stock for a specific item?",
        "cancel_order": "If your order already shipped, you can start a return once it arrives.",
        "payment_issue": "You might also try a different payment method or contact your bank.",
        "greeting": "I can help with orders, returns, shipping, products, and more!",
    }
    return suggestions.get(intent)


def ensure_model_loaded():
    global tokenizer, model
    if tokenizer is None or model is None:
        from src.model import load_model
        tokenizer, model = load_model()


def build_conversation(message, history):
    conversation = ""
    if history:
        for user_msg, bot_msg in history[-config.MAX_HISTORY_TURNS:]:
            conversation += user_msg + tokenizer.eos_token
            conversation += bot_msg + tokenizer.eos_token
    conversation += message + tokenizer.eos_token
    return conversation


def respond_with_dialogpt(message, history):
    ensure_model_loaded()
    conversation = build_conversation(message, history)

    from src.model import generate_response
    return generate_response(tokenizer, model, conversation)


def chat(message, history):
    safe, reason = check_input(message)
    if not safe:
        return reason

    if not is_on_topic(message):
        return (
            "I'm a customer support assistant for our online store. "
            "I can help with orders, returns, shipping, products, and payments. "
            "What can I help you with?"
        )

    intent = classify_intent(message)

    known_intents = {
        "greeting", "closing", "cancel_order", "change_address",
        "payment_method", "contact_human", "escalate", "discount", "gift_card",
    }

    if intent in known_intents:
        response = get_template(intent)
        safe_out, response = check_output(response, message)
        if not safe_out:
            return response
        tip = _suggestion(intent)
        return response + ("\n\n" + tip if tip else "")

    if intent in {"return_request", "shipping_info", "damaged_item", "exchange", "lost_package", "complaint"}:
        results = faq.search(message)
        if results:
            safe_out, response = check_output(results[0]["answer"], message)
            return response if safe_out else get_template("escalate")
        response = get_template(intent)
        return check_output(response, message)[1]

    if intent == "order_status":
        order_number = _extract_order_number(message) or _find_order_in_history(history)
        if order_number:
            response = (
                f"Let me check on order **#{order_number}** for you.\n\n"
                f"Your order is currently being processed and is expected to ship within 2 business days. "
                f"You'll receive a tracking number via email once it ships."
            )
            return check_output(response, message)[1]
        response = get_template("order_status")
        return check_output(response, message)[1]

    if intent == "payment_issue":
        response = get_template("payment_issue")
        return check_output(response, message)[1]

    if intent == "product_inquiry":
        matches = products.search(message)
        if matches:
            p = matches[0]
            stock = "In stock" if p["in_stock"] else "Currently out of stock"
            response = (
                f"I found **{p['name']}** — ${p['price']:.2f}\n"
                f"{p['description']}\n"
                f"*{stock}*\n"
                f"Product ID: {p['id']}"
            )
            return check_output(response, message)[1]
        response = get_template("product_inquiry")
        return check_output(response, message)[1]

    response = respond_with_dialogpt(message, history)
    return check_output(response, message)[1]
