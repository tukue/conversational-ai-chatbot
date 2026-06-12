import config
from src.intent import classify_intent
from src.templates import get_template
from src.knowledge_base import FAQSearch, ProductSearch
from src.guardrails import check_input, check_output, is_on_topic


tokenizer, model = None, None
faq = FAQSearch()
products = ProductSearch()


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
    # Input guardrails
    safe, reason = check_input(message)
    if not safe:
        return reason

    # Topic confinement — if clearly off-topic, redirect
    if not is_on_topic(message):
        return (
            "I'm a customer support assistant for our online store. "
            "I can help with orders, returns, shipping, products, and payments. "
            "What can I help you with?"
        )

    intent = classify_intent(message)

    # Template-only intents (no model needed)
    known_intents = {
        "greeting", "closing", "cancel_order", "change_address",
        "payment_method", "contact_human", "escalate", "discount", "gift_card",
    }

    if intent in known_intents:
        response = get_template(intent)
        return check_output(response, message)[1]

    # FAQ-backed intents
    if intent in {"return_request", "shipping_info", "damaged_item", "exchange", "lost_package", "complaint"}:
        results = faq.search(message)
        if results:
            safe_out, response = check_output(results[0]["answer"], message)
            return response if safe_out else get_template("escalate")
        response = get_template(intent)
        return check_output(response, message)[1]

    if intent == "order_status":
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
