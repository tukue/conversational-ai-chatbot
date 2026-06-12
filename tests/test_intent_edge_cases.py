import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.intent import classify_intent


def test_empty_message():
    assert classify_intent("") == "general"


def test_whitespace_only():
    assert classify_intent("   ") == "general"


def test_special_characters():
    assert classify_intent("!@#$%^") == "general"


def test_mixed_case():
    assert classify_intent("WHERE IS MY ORDER") == "order_status"


def test_partial_word_match_does_not_false_positive():
    assert classify_intent("I fixed the problem myself") == "general"


def test_multi_intent_prefers_higher_priority():
    result = classify_intent("I want to return my order and cancel it")
    assert result in ("return_request", "cancel_order")


def test_multi_intent_complaint_and_return():
    result = classify_intent("I'm very unhappy and I want a refund")
    assert result == "complaint"


def test_intent_with_numbers():
    assert classify_intent("track order 12345") == "order_status"


def test_intent_with_punctuation():
    assert classify_intent("Hello!") == "greeting"
    assert classify_intent("Bye...") == "closing"


def test_greeting_variations():
    for msg in ["hey", "howdy", "good morning", "hi"]:
        assert classify_intent(msg) == "greeting"


def test_closing_variations():
    for msg in ["thanks", "bye", "goodbye", "see you", "thank you"]:
        assert classify_intent(msg) == "closing"


def test_return_variations():
    for msg in ["refund please", "send back my item", "return policy"]:
        assert classify_intent(msg) == "return_request"


def test_product_variations():
    for msg in ["do you sell water bottles", "tell me about the laptop sleeve", "price of headphones"]:
        assert classify_intent(msg) == "product_inquiry"


def test_contact_human_variations():
    for msg in ["talk to a human", "real person please", "agent"]:
        assert classify_intent(msg) == "contact_human", f"Failed for '{msg}': got '{classify_intent(msg)}'"


def test_escalate_over_complaint():
    result = classify_intent("I want to escalate this terrible situation")
    assert result == "escalate"
