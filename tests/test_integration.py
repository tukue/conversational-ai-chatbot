import sys
import os
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.chatbot import chat
from src.intent import classify_intent
from src.knowledge_base import FAQSearch, ProductSearch
from src.guardrails import check_input, is_on_topic, check_output


faq = FAQSearch()
products = ProductSearch()


def test_full_pipeline_return_policy():
    response = chat("What's your return policy?", [])
    assert isinstance(response, str) and len(response) > 0


def test_full_pipeline_order_status():
    response = chat("Where is my order?", [])
    assert isinstance(response, str) and len(response) > 0


def test_full_pipeline_shipping():
    response = chat("How long does shipping take?", [])
    assert isinstance(response, str) and len(response) > 0


def test_full_pipeline_product_inquiry():
    response = chat("Do you sell wireless headphones?", [])
    assert isinstance(response, str) and len(response) > 0
    assert "PROD-001" in response


def test_full_pipeline_cancel_order():
    response = chat("I want to cancel my order", [])
    assert isinstance(response, str) and len(response) > 0


def test_full_pipeline_greeting():
    response = chat("Hello", [])
    assert isinstance(response, str) and len(response) > 0


def test_full_pipeline_lost_package():
    response = chat("My package is lost", [])
    assert isinstance(response, str) and len(response) > 0


def test_full_pipeline_damaged_item():
    response = chat("My item arrived broken", [])
    assert isinstance(response, str) and len(response) > 0


def test_full_pipeline_exchange():
    response = chat("I need to exchange for a larger size", [])
    assert isinstance(response, str) and len(response) > 0


def test_full_pipeline_complaint():
    response = chat("I'm very unhappy with this", [])
    assert isinstance(response, str) and len(response) > 0


def test_full_pipeline_contact_human():
    response = chat("talk to a real person", [])
    assert isinstance(response, str) and len(response) > 0


def test_full_pipeline_escalate():
    response = chat("I want to escalate this", [])
    assert isinstance(response, str) and len(response) > 0


def test_full_pipeline_profanity_blocked():
    safe, _ = check_input("this is fucking terrible service")
    assert not safe


def test_full_pipeline_off_topic_redirected():
    assert not is_on_topic("what's the weather today")


def test_full_pipeline_general_fallback():
    pytest.importorskip("transformers")
    response = chat("tell me a story", [])
    assert isinstance(response, str) and len(response) > 0


def test_full_pipeline_with_history():
    history = [
        ("Hi", "Hello! Welcome to our store. How can I help you today?"),
    ]
    response = chat("What's your return policy?", history)
    assert isinstance(response, str) and len(response) > 0


def test_full_pipeline_multi_turn_conversation():
    history = [
        ("Hi", "Hello! Welcome! How can I help?"),
        ("I need to return something", "Sure! Please share your order number."),
        ("My order number is 12345", "Thank you! Let me check on that return."),
    ]
    response = chat("What's the return policy for electronics?", history)
    assert isinstance(response, str) and len(response) > 0


def test_full_pipeline_pii_at_input_blocked():
    response = chat("My credit card is 4111111111111111", [])
    assert "secure" in response.lower() or "don't share" in response.lower() or "transfer" in response.lower()


def test_full_pipeline_profanity_at_input_blocked():
    response = chat("this is a shitty product", [])
    assert "respectful" in response.lower()


def test_full_pipeline_guardrail_then_legitimate_question():
    bad_response = chat("fuck this", [])
    assert "respectful" in bad_response.lower()
    good_response = chat("What's your return policy?", [])
    assert "return" in good_response.lower()


def test_intent_classification_coverage():
    test_cases = {
        "hello": "greeting",
        "bye": "closing",
        "track my order": "order_status",
        "I want a refund": "return_request",
        "shipping cost": "shipping_info",
        "do you sell headphones": "product_inquiry",
        "my card was declined": "payment_issue",
        "cancel my order": "cancel_order",
        "item arrived broken": "damaged_item",
        "I'm very unhappy": "complaint",
        "talk to a real person": "contact_human",
        "lost package": "lost_package",
        "my package is lost": "lost_package",
        "change my address": "change_address",
        "discount code": "discount",
        "gift card balance": "gift_card",
        "exchange for larger size": "exchange",
        "what payment methods": "payment_method",
        "escalate to supervisor": "escalate",
    }
    for msg, expected_intent in test_cases.items():
        assert classify_intent(msg) == expected_intent, f"Failed: '{msg}' should be '{expected_intent}' got '{classify_intent(msg)}'"


def test_guardrail_output_check_valid():
    safe, out = check_output("Your 30-day return policy allows you to send items back.", "")
    assert safe
    assert "return policy" in out


def test_guardrail_output_check_pii_blocked():
    safe, _ = check_output("Call me at 123-456-7890", "")
    assert not safe


def test_knowledge_base_faq_coverage():
    queries = [
        ("return policy", "return"),
        ("shipping time", "shipping"),
        ("track order", "order"),
        ("cancel", "cancel"),
        ("damaged", "damaged"),
        ("lost package", "neighbors"),
    ]
    for query, expected_keyword in queries:
        results = faq.search(query)
        assert len(results) > 0, f"FAQ search returned no results for '{query}'"
        answer = results[0]["answer"].lower()
        assert expected_keyword in answer, f"FAQ answer for '{query}' missing '{expected_keyword}'"


def test_product_search_coverage():
    queries = [
        ("headphones", "PROD-001"),
        ("water bottle", "PROD-003"),
        ("yoga mat", "PROD-005"),
        ("running shoes", "PROD-008"),
        ("charging hub", "PROD-006"),
    ]
    for query, expected_id in queries:
        results = products.search(query)
        assert len(results) > 0, f"Product search returned no results for '{query}'"
        ids = [p["id"] for p in results]
        assert expected_id in ids, f"Product search for '{query}' missing '{expected_id}'"


def test_intent_no_false_positive_on_unrelated():
    assert classify_intent("I like programming") == "general"
    assert classify_intent("What is the meaning of life") == "general"
    assert classify_intent("Tell me a joke") == "general"
