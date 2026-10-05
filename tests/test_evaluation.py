import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.evaluation import score_response, ResponseScore, _calculate_relevance, _calculate_coherence, _calculate_groundedness, _calculate_safety, _calculate_conciseness


def test_score_response_basic():
    """Test basic response scoring."""
    score = score_response(
        "What is your return policy?",
        "You can return any item within 30 days of delivery for a full refund.",
        [{"content": "You can return any item within 30 days of delivery", "type": "faq", "id": "return_policy"}],
    )
    assert isinstance(score, ResponseScore)
    assert 0.0 <= score.overall <= 1.0
    assert 0.0 <= score.relevance <= 1.0
    assert 0.0 <= score.coherence <= 1.0
    assert 0.0 <= score.groundedness <= 1.0
    assert 0.0 <= score.safety <= 1.0
    assert 0.0 <= score.conciseness <= 1.0


def test_score_response_hallucination_penalty():
    """Test that hallucinated responses get lower groundedness."""
    score = score_response(
        "What is your return policy?",
        "You can return items within 365 days for a full refund and get double money back.",
        [{"content": "You can return any item within 30 days of delivery", "type": "faq", "id": "return_policy"}],
    )
    # Hallucinated response should have lower groundedness
    assert score.groundedness < 0.5, f"Expected low groundedness for hallucination, got {score.groundedness}"
    # Overall should be noticeably lower than a grounded response
    grounded_score = score_response(
        "What is your return policy?",
        "You can return any item within 30 days of delivery for a full refund.",
        [{"content": "You can return any item within 30 days of delivery", "type": "faq", "id": "return_policy"}],
    )
    assert score.overall < grounded_score.overall


def test_calculate_relevance():
    """Test relevance calculation."""
    score = _calculate_relevance(
        "How do I return an item?",
        "You can return items within 30 days",
    )
    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0


def test_calculate_coherence():
    """Test coherence calculation."""
    score = _calculate_coherence("This is a short response.")
    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0


def test_calculate_groundedness():
    """Test groundedness calculation."""
    score = _calculate_groundedness(
        "You can return items within 30 days",
        [{"content": "You can return any item within 30 days of delivery", "type": "faq", "id": "return_policy"}],
    )
    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0


def test_calculate_safety():
    """Test safety calculation."""
    # Safe response
    score = _calculate_safety("You can return items within 30 days", "test message")
    assert score == 1.0  # check_output returns safe=True for this


def test_calculate_conciseness():
    """Test conciseness calculation."""
    # Medium length response
    score = _calculate_conciseness("You can return items within 30 days of delivery for a full refund.")
    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0


def test_score_edge_cases():
    """Test scoring edge cases."""
    # Empty response
    score = score_response("test question", "", None)
    assert score.overall == 0.0
    
    # None context
    score = score_response("test question", "Good response", None)
    assert isinstance(score, ResponseScore)
    assert 0.0 <= score.overall <= 1.0


if __name__ == "__main__":
    test_score_response_basic()
    test_score_response_hallucination_penalty()
    test_calculate_relevance()
    test_calculate_coherence()
    test_calculate_groundedness()
    test_calculate_safety()
    test_calculate_conciseness()
    test_score_edge_cases()
    print("All evaluation tests passed!")