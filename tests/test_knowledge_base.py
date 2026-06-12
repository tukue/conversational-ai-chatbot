import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.knowledge_base import FAQSearch, ProductSearch


faq = FAQSearch()
products = ProductSearch()


def test_faq_search_returns_policy():
    results = faq.search("What's your return policy?")
    assert len(results) >= 1
    assert "return" in results[0]["answer"].lower()


def test_faq_search_shipping():
    results = faq.search("How long does delivery take?")
    assert len(results) >= 1
    assert "shipping" in results[0]["answer"].lower() or "delivery" in results[0]["answer"].lower()


def test_faq_search_lost_package():
    results = faq.search("My package is lost")
    assert len(results) >= 1
    answer = results[0]["answer"].lower()
    assert any(word in answer for word in ["lost", "missing", "delivered", "carrier", "package"])


def test_faq_search_empty():
    results = faq.search("quantum flux capacitor")
    assert len(results) == 0


def test_product_search_headphones():
    results = products.search("wireless headphones")
    assert len(results) >= 1
    assert "PROD-001" in [p["id"] for p in results]


def test_product_search_by_id():
    p = products.get_by_id("PROD-003")
    assert p is not None
    assert p["name"] == "Stainless Steel Water Bottle"


def test_product_search_returns_empty():
    results = products.search("xyzzy plover")
    assert len(results) == 0


def test_product_out_of_stock():
    p = products.get_by_id("PROD-004")
    assert p is not None
    assert p["in_stock"] is False
