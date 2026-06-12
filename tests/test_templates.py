import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.templates import get_template


def test_greeting_template():
    response = get_template("greeting")
    assert "Hello" in response or "Hi" in response


def test_return_template():
    response = get_template("return_request")
    assert "return" in response.lower() or "refund" in response.lower()


def test_general_fallback():
    response = get_template("nonexistent_intent")
    assert "I'm not sure" in response


def test_escalate_template():
    response = get_template("escalate")
    assert "supervisor" in response.lower() or "escalate" in response.lower()


def test_all_intents_return_string():
    intents = [
        "greeting", "closing", "order_status", "cancel_order",
        "return_request", "shipping_info", "payment_issue", "payment_method",
        "product_inquiry", "damaged_item", "exchange", "lost_package",
        "change_address", "discount", "gift_card", "complaint",
        "contact_human", "escalate", "general",
    ]
    for intent in intents:
        response = get_template(intent)
        assert isinstance(response, str)
        assert len(response) > 0
