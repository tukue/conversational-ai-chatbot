import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.templates import get_template
from src.chatbot import chat


def test_chat_profanity_blocked():
    response = chat("this is fucking terrible", [])
    assert "respectful" in response.lower()


def test_chat_pii_blocked():
    response = chat("My SSN is 123-45-6789", [])
    assert "secure" in response.lower() or "don't share" in response.lower()


def test_chat_off_topic_redirected():
    response = chat("what's the weather today", [])
    assert "customer support" in response.lower() or "store" in response.lower()


def test_chat_greeting():
    response = chat("Hello", [])
    assert "Hello" in response or "Hi" in response


def test_chat_return_policy():
    response = chat("What's your return policy?", [])
    assert "return" in response.lower()
    assert "30 days" in response.lower()


def test_chat_order_status():
    response = chat("Where is my order?", [])
    assert "order number" in response.lower()


def test_chat_product_found():
    response = chat("Do you sell wireless headphones?", [])
    assert "PROD-001" in response
    assert "Wireless Bluetooth Headphones" in response


def test_chat_product_not_found():
    response = chat("Do you sell quantum computers?", [])
    assert "I'd be happy" in response or "What type of product" in response


def test_chat_cancel_order():
    response = chat("I want to cancel my order", [])
    assert "order number" in response.lower()


def test_chat_shipping_info():
    response = chat("How long does shipping take?", [])
    assert "shipping" in response.lower() or "delivery" in response.lower()


def test_chat_damaged_item():
    response = chat("My item arrived broken", [])
    assert "damage" in response.lower() or "order number" in response.lower()


def test_chat_lost_package():
    response = chat("My package is lost", [])
    assert "neighbors" in response.lower() or "package" in response.lower()


def test_chat_complaint():
    response = chat("I'm very unhappy with this product", [])
    assert "sorry" in response.lower() or "unhappy" in response.lower()


def test_chat_contact_human():
    response = chat("talk to a real person", [])
    assert "human" in response.lower() or "agent" in response.lower()


def test_chat_escalate():
    response = chat("I want to escalate this", [])
    assert "supervisor" in response.lower() or "escalate" in response.lower()


def test_chat_payment_method():
    response = chat("What payment methods do you accept?", [])
    assert "Visa" in response


def test_chat_payment_issue():
    response = chat("My card was declined", [])
    assert "error" in response.lower() or "sorry" in response.lower()


def test_chat_exchange():
    response = chat("I need to exchange this for a larger size", [])
    assert "exchange" in response.lower() or "order number" in response.lower()


def test_chat_discount():
    response = chat("Do you have any discount codes?", [])
    assert "promo code" in response.lower() or "discount" in response.lower()


def test_chat_gift_card():
    response = chat("How do I use a gift card?", [])
    assert "gift card" in response.lower() or "balance" in response.lower()


def test_chat_change_address():
    response = chat("I need to change my shipping address", [])
    assert "address" in response.lower()


def test_chat_closing():
    response = chat("thanks for your help", [])
    assert "welcome" in response.lower() or "glad" in response.lower()


def test_chat_with_history():
    history = [
        ("Hello", "Hi there! How can I help you?"),
    ]
    response = chat("Where is my order?", history)
    assert isinstance(response, str) and len(response) > 0


def test_chat_all_intents_return_valid_response():
    intents = [
        "greeting", "closing", "order_status", "cancel_order",
        "return_request", "shipping_info", "payment_issue", "payment_method",
        "product_inquiry", "damaged_item", "exchange", "lost_package",
        "change_address", "discount", "gift_card", "complaint",
        "contact_human", "escalate",
    ]
    for intent in intents:
        template = get_template(intent)
        assert isinstance(template, str) and len(template) > 0
