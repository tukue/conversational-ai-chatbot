import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.guardrails import check_input, check_output, is_on_topic


def test_empty_input():
    safe, _ = check_input("")
    assert not safe


def test_whitespace_input():
    safe, _ = check_input("   ")
    assert not safe


def test_polite_profanity_not_blocked():
    safe, _ = check_input("This product is not working")
    assert safe


def test_profanity_variations():
    assert not check_input("fuck this")[0]
    assert not check_input("fucking terrible")[0]
    assert not check_input("fucked up")[0]


def test_multiple_pii_patterns():
    assert not check_input("SSN: 123-45-6789, Card: 4111111111111111")[0]


def test_credit_card_with_spaces():
    safe, _ = check_input("My card number is 4111 1111 1111 1111")
    assert not safe


def test_credit_card_with_dashes():
    safe, _ = check_input("Card: 4111-1111-1111-1111")
    assert not safe


def test_phone_number():
    safe, _ = check_input("Call me at 123-456-7890")
    assert not safe


def test_safe_input_long():
    safe, _ = check_input("I want to return a pair of shoes I bought last week. They don't fit properly.")
    assert safe


def test_too_long_input_blocked():
    safe, reason = check_input("x" * 1001)
    assert not safe
    assert "under 1,000 characters" in reason


def test_check_output_empty():
    safe, out = check_output("", "")
    assert safe
    assert out == ""


def test_check_output_safe_response():
    safe, out = check_output("Your order has shipped and will arrive in 3 days.", "")
    assert safe
    assert "shipped" in out


def test_check_output_no_harmful_content():
    safe, _ = check_output("I hate this product it is garbage", "why is this bad")
    assert safe


def test_is_on_topic_empty():
    assert is_on_topic("")


def test_is_on_topic_whitespace():
    assert is_on_topic("   ")


def test_is_on_topic_mixed():
    assert not is_on_topic("weather today and politics news")


def test_is_on_topic_product_questions():
    assert is_on_topic("What is the price of this item?")
    assert is_on_topic("How do I reset my password?")
    assert is_on_topic("I need help with my account")


def test_is_on_topic_boundary():
    assert is_on_topic("I have a problem")
    assert is_on_topic("can you help me")
