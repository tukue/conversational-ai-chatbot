import re
import logging
import config
from src.intent import classify_intent
from src.templates import get_template
from src.guardrails import (
    check_input,
    check_output,
    is_on_topic,
    check_rate_limit,
    wrap_with_sandwich_defense,
    sanitize_input,
    validate_rag_response,
)


tokenizer, model = None, None
_faq = None
_products = None
_rag = None
logger = logging.getLogger(__name__)


def _get_faq():
    global _faq
    if _faq is None:
        from src.knowledge_base import FAQSearch
        _faq = FAQSearch()
    return _faq


def _get_products():
    global _products
    if _products is None:
        from src.knowledge_base import ProductSearch
        _products = ProductSearch()
    return _products


def _get_rag():
    global _rag
    if _rag is None:
        from src.rag import RAGEngine
        _rag = RAGEngine.get_instance()
    return _rag


def _history_pairs(history):
    if not history:
        return []

    if isinstance(history, list) and history and isinstance(history[0], dict):
        pairs = []
        pending_user = None
        for item in history:
            role = item.get("role")
            content = item.get("content", "")
            if role == "user":
                pending_user = content
            elif role == "assistant" and pending_user is not None:
                pairs.append((pending_user, content))
                pending_user = None
        return pairs

    return history


def _extract_order_number(message):
    match = re.search(r'\b(?:order\s*#?\s*)?([A-Z]{0,4}-?\d{5,})\b', message, re.IGNORECASE)
    return match.group(1) if match else None


def _find_order_in_history(history):
    for user_msg, _ in reversed(_history_pairs(history)):
        num = _extract_order_number(user_msg)
        if num:
            return num
    return None


def _suggestion(intent):
    suggestions = {
        "order_status": "You can also track your order anytime in your account under 'My Orders'.",
        "return_request": "Need a prepaid return label? Use the secure returns portal so private details stay protected.",
        "shipping_info": "You can check estimated delivery times on any product page.",
        "product_inquiry": "Would you like me to check stock for a specific item?",
        "cancel_order": "If your order already shipped, you can start a return once it arrives.",
        "payment_issue": "You might also try a different payment method or contact your bank.",
        "greeting": "I can help with orders, returns, shipping, products, and more!",
    }
    return suggestions.get(intent)


def _rag_retrieve(message):
    """Retrieve relevant context using the RAG engine."""
    if not config.ENABLE_RAG:
        return []

    rag = _get_rag()
    if config.RAG_RERANK:
        return rag.search_with_rerank(message, top_k=config.RAG_TOP_K)
    return rag.retrieve(message, top_k=config.RAG_TOP_K)


def _build_rag_response(message, context_chunks):
    """Build a response from RAG context chunks."""
    if not context_chunks:
        return None

    for chunk in context_chunks:
        if chunk.get("type") == "faq":
            answer = chunk.get("content", "")
            if "Answer:" in answer:
                answer = answer.split("Answer:", 1)[1].strip()
            return answer

    for chunk in context_chunks:
        if chunk.get("type") == "product":
            product_id = chunk.get("id", "")
            return (
                f"{chunk.get('content', '')}\nProduct ID: {product_id}"
                if product_id
                else chunk.get("content", "")
            )

    if context_chunks:
        return context_chunks[0].get("content", "")

    return None


def ensure_model_loaded():
    global tokenizer, model
    if tokenizer is None or model is None:
        from src.model import load_model
        tokenizer, model = load_model()


def build_conversation(message, history):
    conversation = ""
    for user_msg, bot_msg in _history_pairs(history)[-config.MAX_HISTORY_TURNS:]:
        conversation += user_msg + tokenizer.eos_token
        conversation += bot_msg + tokenizer.eos_token

    if config.ENABLE_SANDWICH_DEFENSE:
        message = wrap_with_sandwich_defense(message)

    conversation += message + tokenizer.eos_token
    return conversation


def respond_with_dialogpt(message, history):
    try:
        ensure_model_loaded()
        conversation = build_conversation(message, history)

        from src.model import generate_response
        response = generate_response(tokenizer, model, conversation)
        if response.strip():
            return response
    except Exception as exc:
        logger.warning("Fallback model unavailable: %s", exc.__class__.__name__)

    return (
        "I can help with orders, returns, shipping, products, payments, and account questions. "
        "Could you share a few more details about what you need?"
    )


def chat(message, history):
    message = sanitize_input(message)

    if config.ENABLE_RATE_LIMITING:
        allowed, retry_after = check_rate_limit(history)
        if not allowed:
            return (
                f"You've sent too many messages. "
                f"Please wait {retry_after} seconds and try again."
            )

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
        "complaint",
    }

    if intent in known_intents:
        response = get_template(intent)
        safe_out, response = check_output(response, message)
        if not safe_out:
            return response
        tip = _suggestion(intent)
        return response + ("\n\n" + tip if tip else "")

    if intent in {"return_request", "shipping_info", "damaged_item", "exchange", "lost_package"}:
        context_chunks = _rag_retrieve(message)
        expected_source = {
            "damaged_item": "damaged_item",
            "exchange": "size_exchange",
            "lost_package": "lost_package",
        }.get(intent)
        if expected_source:
            matching_chunks = [
                chunk for chunk in context_chunks if chunk.get("id") == expected_source
            ]
            context_chunks = matching_chunks or context_chunks
        rag_response = _build_rag_response(message, context_chunks)

        if rag_response:
            safe_out, rag_response = check_output(rag_response, message)
            if not safe_out:
                return get_template("escalate")

            if config.ENABLE_RAG and context_chunks:
                valid, rag_response = validate_rag_response(rag_response, context_chunks)
                if not valid:
                    return get_template("escalate")

            tip = _suggestion(intent)
            return rag_response + ("\n\n" + tip if tip else "")

        results = _get_faq().search(message)
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
        context_chunks = _rag_retrieve(message)
        rag_response = _build_rag_response(message, context_chunks)

        if rag_response:
            safe_out, rag_response = check_output(rag_response, message)
            if safe_out:
                tip = _suggestion(intent)
                return rag_response + ("\n\n" + tip if tip else "")

        matches = _get_products().search(message)
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

    if config.ENABLE_GENERATIVE_FALLBACK:
        response = respond_with_dialogpt(message, history)
    else:
        response = get_template("general")
    return check_output(response, message)[1]
