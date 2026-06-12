import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.intent import classify_intent


def test_greeting():
    assert classify_intent("Hello") == "greeting"
    assert classify_intent("hi there") == "greeting"


def test_order_status():
    assert classify_intent("Where is my order?") == "order_status"
    assert classify_intent("track my package") == "order_status"


def test_return_request():
    assert classify_intent("I want to return an item") == "return_request"
    assert classify_intent("can I get a refund?") == "return_request"


def test_shipping_info():
    assert classify_intent("How long does shipping take?") == "shipping_info"
    assert classify_intent("shipping cost") == "shipping_info"


def test_product_inquiry():
    assert classify_intent("Do you sell headphones?") == "product_inquiry"
    assert classify_intent("tell me about the water bottle") == "product_inquiry"


def test_payment_issue():
    assert classify_intent("My card was declined") == "payment_issue"
    assert classify_intent("payment error") == "payment_issue"


def test_cancel_order():
    assert classify_intent("I want to cancel my order") == "cancel_order"
    assert classify_intent("cancel order") == "cancel_order"


def test_damaged_item():
    assert classify_intent("My item arrived broken") == "damaged_item"
    assert classify_intent("damaged product") == "damaged_item"


def test_complaint():
    assert classify_intent("I'm very unhappy with this") == "complaint"
    assert classify_intent("terrible service") == "complaint"


def test_contact_human():
    assert classify_intent("talk to a real person") == "contact_human"
    assert classify_intent("speak to a human") == "contact_human"


def test_general():
    assert classify_intent("tell me a joke") == "general"
    assert classify_intent("what is the meaning of life") == "general"
