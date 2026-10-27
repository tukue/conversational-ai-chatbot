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
        "greeting": "I can help with deliveries, couriers, missing items, checkout, and refunds!",
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


def _extract_direct_faq_answer(context_chunks):
    """Extract exact FAQ answer without LLM generation.

    Returns the answer string if a matching FAQ chunk is found,
    or None if no direct answer available (falls back to LLM generation).
    """
    for chunk in context_chunks:
        if chunk.get("type") == "faq":
            content = chunk.get("content", "")
            if "Answer:" in content:
                # Return the exact answer text, stripped
                answer = content.split("Answer:", 1)[1].strip()
                if answer:
                    return answer
    return None


def _build_rag_response(message, context_chunks):
    """Build a response from RAG context chunks.

    Tries direct FAQ answer extraction first (LLM-free).
    Falls back to LLM-mediated response generation if no direct answer.
    """
    if not context_chunks:
        return None

    # Try direct FAQ answer extraction first (no LLM needed)
    direct_answer = _extract_direct_faq_answer(context_chunks)
    if direct_answer:
        return direct_answer

    # Sort by position weight (earlier/chunks with higher weight first)
    sorted_chunks = sorted(context_chunks, key=lambda c: c.get("weight", 1.0), reverse=True)

    for chunk in sorted_chunks:
        if chunk.get("type") == "faq":
            answer = chunk.get("content", "")
            if "Answer:" in answer:
                answer = answer.split("Answer:", 1)[1].strip()
            return answer

    for chunk in sorted_chunks:
        if chunk.get("type") == "product":
            product_id = chunk.get("id", "")
            return (
                f"{chunk.get('content', '')}\nProduct ID: {product_id}"
                if product_id
                else chunk.get("content", "")
            )

    if sorted_chunks:
        return sorted_chunks[0].get("content", "")

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


def _chat(message, history):
    from src.monitoring import record_event

    if config.ENABLE_RATE_LIMITING:
        allowed, retry_after = check_rate_limit(history)
        if not allowed:
            record_event("rate_limited")
            return (
                f"You've sent too many messages. "
                f"Please wait {retry_after} seconds and try again."
            )

    safe, reason = check_input(message)
    if not safe:
        record_event("input_blocked")
        return reason
    record_event("input_allowed")
    message = sanitize_input(message)

    if not is_on_topic(message):
        # Allow delivery platform related queries
        if _is_platform_query(message):
            pass  # Continue processing
        else:
            return (
                "I'm a customer support assistant for our delivery platform. "
                "I can help with orders, returns, shipping, products, and payments. "
                "What can I help you with?"
            )

    intent = classify_intent(message)
    if intent in {"contact_human", "escalate"}:
        record_event("intent_" + intent)
        return get_template(intent)

    from src.delivery import delivery_response
    delivery = delivery_response(message)
    if delivery:
        return delivery

    record_event("intent_" + intent)

    if intent == "order_status":
        order_number = _extract_order_number(message) or _find_order_in_history(history)
        if order_number:
            return (
                f"For order **#{order_number}**, open Orders and select Track delivery. "
                "I cannot access live order status here. Use Help on the order if the delivery is late."
            )
        return get_template("order_status") + " Open Orders and select Track delivery for live updates."

    if intent == "product_inquiry":
        # Retain the sample catalog for compatibility; it is not live inventory.
        context_chunks = [c for c in _rag_retrieve(message) if c.get("type") == "product"]
        rag_response = _build_rag_response(message, context_chunks)
        if rag_response:
            return "Sample catalog (not live availability): " + rag_response
        matches = _get_products().search(message)
        if matches:
            p = matches[0]
            return (
                f"Sample catalog: **{p['name']}** — ${p['price']:.2f}\n"
                f"{p['description']}\nProduct ID: {p['id']}\n"
                "Confirm current price and availability in the platform."
            )
        return get_template(intent)

    if intent != "general":
        return get_template(intent)

    if config.ENABLE_GENERATIVE_FALLBACK:
        record_event("generative_fallback")
        if getattr(config, "USE_LLM_PROXY", False):
            return respond_via_proxy(message, history)
        return respond_with_dialogpt(message, history)
    return get_template("general")


def respond_via_proxy(message, history):
    import httpx

    if not config.PROXY_CLIENT_KEY.strip():
        logger.warning("Proxy client key is not configured")
        return "Support generation is temporarily unavailable. Please use Help on your order."

    # Build messages in proxy format
    messages = []
    for user_msg, bot_msg in _history_pairs(history)[-config.MAX_HISTORY_TURNS:]:
        messages.append({"role": "user", "content": user_msg})
        messages.append({"role": "assistant", "content": bot_msg})

    if config.ENABLE_SANDWICH_DEFENSE:
        message = wrap_with_sandwich_defense(message)
    messages.append({"role": "user", "content": message})

    try:
        response = httpx.post(
            f"{config.PROXY_BASE_URL.rstrip('/')}/v1/chat/completions",
            headers={"Authorization": f"Bearer {config.PROXY_CLIENT_KEY}"},
            json={
                "model": config.PROXY_MODEL,
                "messages": messages,
                "max_tokens": config.MAX_NEW_TOKENS,
            },
            timeout=config.PROXY_TIMEOUT,
            follow_redirects=False,
            trust_env=False,
        )
        if response.status_code == 200:
            data = response.json()
            choices = data.get("choices", [])
            if isinstance(choices, list) and len(choices) == 1:
                result = choices[0].get("message", {})
                content = result.get("content")
                if (result.get("role") == "assistant" and isinstance(content, str)
                        and content.strip() and not result.get("tool_calls")
                        and not result.get("function_call")):
                    return content.strip()
        # On policy denial or errors, don't fallback silently - return safe generic response
        # to avoid bypassing proxy protections
        if response.status_code in (403, 413):
            return (
                "I can't process that request due to a policy restriction. "
                "Could you rephrase it or ask about something else?"
            )
        if response.status_code == 429:
            return "Too many requests. Please wait a moment and try again."
        if response.status_code in (408, 504):
            return "The request timed out. Please try again."
        if response.status_code in (503,):
            return "The service is temporarily busy. Please try again in a moment."
        if response.status_code >= 500:
            return (
                "I'm having trouble connecting right now. "
                "Please try again later."
            )
    except httpx.TimeoutException:
        return "The request timed out. Please try again."
    except Exception as exc:
        logger.warning("Proxy request failed: %s", exc.__class__.__name__)

    return "Support generation is temporarily unavailable. Please use Help on your order."


# Enhanced support for platform queries
def _is_platform_query(message):
    from src.delivery import is_delivery_query
    if is_delivery_query(message):
        return True
    keywords = [
        "delivery platform", "groceries", "pharmacy", "meal",
        "catalog", "cart", "order tracking", "track", "checkout", "swish",
        "klarna", "stripe", "stockholm"
    ]
    msg_lower = message.lower()
    return any(k in msg_lower for k in keywords)


def chat(message, history):
    """Monitor every request and screen the complete response before returning it."""
    from time import perf_counter
    from src.monitoring import record_request, request_outcome

    started = perf_counter()
    token = request_outcome.set("completed")
    outcome = "error"
    response = ""
    try:
        response = _chat(message, history)
        allowed, response = check_output(response, sanitize_input(message))
        outcome = request_outcome.get() if allowed else "output_blocked"
        return response
    finally:
        request_outcome.reset(token)
        record_request(message, response, outcome, (perf_counter() - started) * 1000)
