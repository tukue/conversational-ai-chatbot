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
        # Allow delivery platform related queries
        if _is_platform_query(message):
            pass  # Continue processing
        else:
            return (
                "I'm a customer support assistant for our online store. "
                "I can help with orders, returns, shipping, products, and payments. "
                "What can I help you with?"
            )

    intent = classify_intent(message)

    # Enhanced help for platform queries
    if intent == "greeting" or ("help" in message.lower() and intent == "general"):
        platform_help = _get_comprehensive_help(message)
        if platform_help:
            safe_out, response = check_output(platform_help, message)
            if safe_out:
                tip = _suggestion("greeting")
                return response + ("\n\n" + tip if tip else "")

    if intent in {"return_request", "shipping_info", "damaged_item", "exchange", "lost_package"}:
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

        # Try direct FAQ answer extraction (LLM-free, fastest path)
        direct_answer = _extract_direct_faq_answer(context_chunks)
        if direct_answer:
            # Direct answer from controlled knowledge base - skip LLM guardrails
            # but still apply basic output filtering
            safe_out, response = check_output(direct_answer, message)
            if safe_out:
                tip = _suggestion(intent)
                # Add platform-specific context for shipping issues
                if intent == "lost_package" or "lost" in message.lower():
                    response += f"\n\n🛒 You can report this on Online Shop at {PLATFORM_URL}/orders"
                return response + ("\n\n" + tip if tip else "")
            # If direct answer fails output filter, fall through to normal RAG path

        # Fall back to LLM-mediated RAG response
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
            if intent == "lost_package" or "lost" in message.lower():
                rag_response += f"\n\n🛒 Report lost/missing packages at {PLATFORM_URL}/orders"
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
        platform_help = _get_platform_help(intent, message)
        if platform_help:
            return check_output(platform_help, message)[1]
        response = get_template("order_status")
        return check_output(response, message)[1]

    if intent == "payment_issue":
        response = get_template("payment_issue")
        safe_out, response = check_output(response, message)
        if safe_out:
            response += f"\n\n💳 You can update payment methods at {PLATFORM_URL} during checkout."
        return response if safe_out else get_template("escalate")

    if intent == "product_inquiry":
        # Check for platform help first
        platform_help = _get_comprehensive_help(message)
        if platform_help and ("grocery" in message.lower() or "pharmacy" in message.lower() or "meal" in message.lower()):
            safe_out, response = check_output(platform_help, message)
            if safe_out:
                tip = _suggestion(intent)
                return response + ("\n\n" + tip if tip else "")
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
        if getattr(config, "USE_LLM_PROXY", False):
            response = respond_via_proxy(message, history)
        else:
            response = respond_with_dialogpt(message, history)
    else:
        response = get_template("general")
    return check_output(response, message)[1]


def respond_via_proxy(message, history):
    import httpx

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
            f"{config.PROXY_BASE_URL}/v1/chat/completions",
            headers={"Authorization": f"Bearer {config.PROXY_CLIENT_KEY}"},
            json={
                "model": config.PROXY_MODEL,
                "messages": messages,
                "max_tokens": config.MAX_NEW_TOKENS,
            },
            timeout=config.PROXY_TIMEOUT,
        )
        if response.status_code == 200:
            data = response.json()
            choices = data.get("choices", [])
            if choices and choices[0].get("message", {}).get("content"):
                content = choices[0]["message"]["content"].strip()
                if content:
                    return content
        # On policy denial or errors, don't fallback silently - return safe generic response
        # to avoid bypassing proxy protections
        if response.status_code in (403, 429, 413):
            return (
                "I can't process that request due to a policy restriction. "
                "Could you rephrase it or ask about something else?"
            )
        if response.status_code in (408, 504):
            return "The request timed out. Please try again."
        if response.status_code in (503,):
            return "The service is temporarily busy. Please try again in a moment."
        if response.status_code >= 500:
            return (
                "I'm having trouble connecting right now. "
                "Please try again later."
            )
    except Exception as exc:
        logger.warning("Proxy request failed: %s", exc.__class__.__name__)

    return (
        "I can help with orders, returns, shipping, products, payments, and account questions. "
        "Could you share a few more details about what you need?"
    )


# Enhanced support for platform queries
def _is_platform_query(message):
    keywords = [
        "online shop", "groceries", "pharmacy", "meal",
        "catalog", "cart", "order tracking", "track", "checkout", "swish",
        "klarna", "stripe", "stockholm"
    ]
    msg_lower = message.lower()
    return any(k in msg_lower for k in keywords)


def _get_platform_context(message):
    return (
        "You are a support agent for an online shop, "
        "a delivery service for groceries, meals, pharmacy items, and essentials. "
        "You can help with: browsing catalog, placing orders, tracking orders, cart management, "
        "payments (Visa, Mastercard, Amex, PayPal, Apple Pay, Google Pay, Swish, Klarna), "
        "returns/refunds, delivery times, and account issues. "
        "Always be helpful and guide users to the right pages on the platform."
    )


def _get_platform_help(intent, message):
    """Get helpful responses specific to the online shop platform."""
    if "track" in message.lower() or intent == "order_status":
        return (
            "You can track your order on the online shop at https://delivery-platform.example.com/orders. "
            "Log in to your account to see real-time updates on your delivery status."
        )
    if "catalog" in message.lower() or "browse" in message.lower():
        return (
            "Browse products at https://delivery-platform.example.com/catalog. "
            "We have Groceries, Quick Meals, Pharmacy, and Home Essentials available for delivery in Stockholm."
        )
    if "cart" in message.lower():
        return (
            "View and manage your cart at https://delivery-platform.example.com/cart. "
            "You can add items, update quantities, and proceed to checkout from there."
        )
    return None


# Enhanced support for the online shop
PLATFORM_URL = "https://delivery-platform.example.com"
PLATFORM_NAME = "Online Shop"

def _get_comprehensive_help(message):
    """Provide comprehensive, supportive help for the online shop."""
    msg_lower = message.lower()
    if any(word in msg_lower for word in ["swish", "klarna", "pay"]):
        return (
            "💳 **Payment Options on the Online Shop:**\n\n"
            "We accept Visa, Mastercard, American Express, Discover, PayPal, Apple Pay, Google Pay, and Shop Pay. "
            "The platform also supports local Swedish payment methods like Swish and Klarna where available.\n\n"
            "🔒 All payments are securely processed. If your payment is declined:\n"
            "1. Check card details and available funds\n"
            "2. Try a different payment method\n"
            "3. Contact your bank if the issue persists\n\n"
            "Shop securely at " + PLATFORM_URL
        )
    if any(word in msg_lower for word in ["pharmacy", "medicine", "prescription"]):
        return (
            "💊 **Pharmacy & Health Essentials:**\n\n"
            "The Online Shop offers pharmacy items and health & wellness products in the Pharmacy category. "
            "Browse at " + PLATFORM_URL + "/catalog and look for the 'Pharmacy' section.\n\n"
            "For prescription medications, please check the product details or contact the pharmacy partner directly through the platform."
        )
    if any(word in msg_lower for word in ["grocery", "groceries", "food", "meal"]):
        return (
            "🛒 **Groceries & Meals:**\n\n"
            "Find fresh groceries, pantry staples, ready meals, and more at " + PLATFORM_URL + "/catalog.\n\n"
            "Browse by category: Groceries, Quick Meals, Pharmacy, and Home Essentials. "
            "Add items to your cart and checkout for fast delivery across Stockholm!"
        )
    if any(word in msg_lower for word in ["stockholm", "delivery area", "zone"]):
        return (
            "📍 **Delivery in Stockholm:**\n\n"
            "The Online Shop delivers across Stockholm with fast, reliable service. "
            "Delivery times depend on your location and order time. Check availability at checkout.\n\n"
            "Track your order at " + PLATFORM_URL + "/orders for real-time updates."
        )
    if any(word in msg_lower for word in ["help", "support", "contact"]):
        return (
            "🤝 **How I Can Help You:**\n\n"
            "I'm your AI support agent for the Online Shop. I can help with:\n"
            "- 📦 Order tracking & status\n"
            "- 🛍️ Finding products in the catalog\n"
            "- 🛒 Cart & checkout guidance\n"
            "- 💳 Payment issues & methods\n"
            "- ↩️ Returns, refunds & exchanges\n"
            "- 🚚 Delivery times & tracking\n"
            "- 💊 Pharmacy & grocery questions\n\n"
            "Start shopping at " + PLATFORM_URL + " or ask me anything specific!"
        )
    return None
