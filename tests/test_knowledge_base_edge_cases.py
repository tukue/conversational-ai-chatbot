import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.knowledge_base import FAQSearch, ProductSearch, load_json


faq = FAQSearch()
products = ProductSearch()


def test_faq_search_empty_string():
    results = faq.search("")
    assert len(results) == 0


def test_faq_search_whitespace():
    results = faq.search("   ")
    assert len(results) == 0


def test_faq_search_special_chars():
    results = faq.search("!@#$%")
    assert len(results) == 0


def test_faq_search_short_query():
    results = faq.search("hi")
    assert len(results) == 0


def test_faq_search_partial_word():
    results = faq.search("returning")
    assert len(results) > 0
    assert "return" in results[0]["answer"].lower()


def test_faq_search_punctuation_normalized():
    results = faq.search("return-policy?")
    assert len(results) > 0
    assert results[0]["id"] == "return_policy"


def test_faq_search_case_insensitive():
    results_lower = faq.search("return policy")
    results_upper = faq.search("RETURN POLICY")
    assert len(results_lower) == len(results_upper)
    assert results_lower[0]["id"] == results_upper[0]["id"]


def test_faq_search_top_k_respected():
    results = faq.search("shipping", top_k=2)
    assert len(results) <= 2


def test_faq_all_entries_have_required_fields():
    for faq_entry in faq.faqs:
        assert "id" in faq_entry
        assert "category" in faq_entry
        assert "keywords" in faq_entry
        assert "question" in faq_entry
        assert "answer" in faq_entry
        assert len(faq_entry["answer"]) > 0


def test_faq_all_categories_covered():
    categories = {faq_entry["category"] for faq_entry in faq.faqs}
    expected = {"returns", "shipping", "orders", "payments", "general"}
    assert expected.issubset(categories), f"Missing categories: {expected - categories}"


def test_product_search_empty_string():
    results = products.search("")
    assert len(results) == 0


def test_product_search_whitespace():
    results = products.search("   ")
    assert len(results) == 0


def test_product_search_special_chars():
    results = products.search("~~~")
    assert len(results) == 0


def test_product_search_partial():
    results = products.search("headphones")
    assert len(results) > 0
    assert "PROD-001" in [p["id"] for p in results]


def test_product_search_plural_normalized():
    results = products.search("candles")
    assert len(results) > 0
    assert "PROD-007" in [p["id"] for p in results]


def test_product_search_case_insensitive():
    lower = products.search("wireless headphones")
    upper = products.search("WIRELESS HEADPHONES")
    assert len(lower) == len(upper)


def test_product_get_by_id_nonexistent():
    assert products.get_by_id("PROD-999") is None


def test_product_get_by_id_empty():
    assert products.get_by_id("") is None


def test_product_all_have_required_fields():
    for p in products.products:
        assert "id" in p
        assert "name" in p
        assert "price" in p
        assert "in_stock" in p


def test_product_price_positive():
    for p in products.products:
        assert p["price"] > 0


def test_load_json_nonexistent():
    try:
        load_json("nonexistent.json")
        assert False, "Should have raised FileNotFoundError"
    except FileNotFoundError:
        pass
