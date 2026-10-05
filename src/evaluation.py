"""Response quality evaluation and scoring for the chatbot.

Provides metrics for measuring response quality, relevance, coherence,
and halluncination risk. These scores can be used for:
- A/B testing different response strategies
- Monitoring quality over time
- Human-in-the-loop review of borderline cases
- Training data validation
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class ResponseScore:
    """Container for response quality scores."""
    
    def __init__(
        self,
        relevance: float,       # 0.0 - how well the response addresses the user's query
        coherence: float,       # 0.0 - how coherent/readable the response is
        groundedness: float,    # 0.0 - how much the response is grounded in retrieved context
        safety: float,          # 0.0 - how safe the response is (higher = safer)
        conciseness: float,     # 0.0 - how concise the response is (higher = more concise)
        overall: float,         # 0.0 - overall quality score
    ):
        self.relevance = relevance
        self.coherence = coherence
        self.groundedness = groundedness
        self.safety = safety
        self.conciseness = conciseness
        self.overall = overall
    
    def to_dict(self) -> Dict[str, float]:
        return {
            "relevance": self.relevance,
            "coherence": self.coherence,
            "groundedness": self.groundedness,
            "safety": self.safety,
            "conciseness": self.conciseness,
            "overall": self.overall,
        }
    
    def __str__(self) -> str:
        return (
            f"ResponseScore(relevance={self.relevance:.2f}, "
            f"coherence={self.coherence:.2f}, "
            f"groundedness={self.groundedness:.2f}, "
            f"safety={self.safety:.2f}, "
            f"conciseness={self.conciseness:.2f}, "
            f"overall={self.overall:.2f})"
        )


def _calculate_relevance(user_message: str, response: str) -> float:
    """Calculate how well the response addresses the user's query.
    
    Uses overlap of important content words between user message and response.
    """
    if not user_message or not response:
        return 0.0
    
    user_tokens = _tokenize_for_matching(user_message.lower())
    response_tokens = _tokenize_for_matching(response.lower())
    
    if not user_tokens or not response_tokens:
        return 0.0
    
    user_set = set(user_tokens)
    response_set = set(response_tokens)
    
    intersection = user_set & response_set
    denominator = max(len(user_set), 1)
    
    base_score = len(intersection) / denominator if denominator else 0.0
    
    # Bonus for question-answer patterns
    if _has_question_pattern(user_message) and _has_answer_pattern(response):
        base_score = min(base_score + 0.1, 1.0)
    
    return round(base_score, 3)


def _calculate_coherence(response: str) -> float:
    """Calculate how coherent and readable the response is.
    
    Checks sentence structure, word diversity, and readability.
    """
    if not response or not response.strip():
        return 0.0
    
    sentences = [s.strip() for s in re.split(r"[.!?]+", response) if s.strip()]
    if not sentences:
        return 0.0
    
    # Average sentence length (optimal ~10-20 words)
    words_per_sentence = []
    for sentence in sentences:
        words = sentence.split()
        words_per_sentence.append(len(words))
    
    if not words_per_sentence:
        return 0.0
    
    avg_len = sum(words_per_sentence) / len(words_per_sentence)
    
    # Optimal range is 8-20 words per sentence
    if 8 <= avg_len <= 20:
        score = 1.0
    elif avg_len < 8:
        score = avg_len / 8  # penalize too short
    else:
        score = 20 / avg_len  # penalize too long
    
    return round(min(score, 1.0), 3)


def _calculate_groundedness(response: str, context_chunks: List[Dict]) -> float:
    """Calculate how grounded the response is in the provided context.
    
    Measures the proportion of meaningful content words in the response
    that also appear in the context chunks.
    """
    if not context_chunks:
        # If no context, score based on internal coherence only
        return _calculate_coherence(response)
    
    context_text = " ".join(
        chunk.get("content", "") for chunk in context_chunks
    ).lower()
    
    if not context_text:
        return _calculate_coherence(response)
    
    # Extract meaningful phrases from response
    sentences = [s.strip().lower() for s in re.split(r"[.!?]+", response) if s.strip()]
    
    total_coverage = 0.0
    count = 0
    
    for sentence in sentences:
        words = [w for w in sentence.split() if len(w) > 3]
        if not words:
            continue
        
        found = sum(1 for w in words if w in context_text)
        total_coverage += found / len(words) if words else 0.0
        count += 1
    
    if count == 0:
        return 0.5  # neutral score when no sentences analyzed
    
    avg_coverage = total_coverage / count
    return round(avg_coverage, 3)


def _calculate_safety(response: str, message: str) -> float:
    """Calculate safety score (0.0 = unsafe, 1.0 = safe).
    
    Checks for PII, toxic content, business blocklist items,
    and internal instruction leakage.
    """
    from src.guardrails import check_output
    
    safe, _ = check_output(response, message)
    return 1.0 if safe else 0.0


def _calculate_conciseness(response: str, max_acceptable: int = 300) -> float:
    """Calculate conciseness score (0.0 = too verbose, 1.0 = optimally concise).
    
    Longer responses get penalized, but very short responses also
    get penalized if they lack substance.
    """
    if not response or not response.strip():
        return 0.0
    
    length = len(response)
    
    if length <= 50:
        # Very short - might be too terse
        return round(length / 50, 3)
    elif length <= max_acceptable:
        # Good range - penalize slightly for not being shorter
        # Optimal around 100-200 characters
        optimal = 150
        score = 1.0 - abs(length - optimal) / (2 * max_acceptable)
        return round(max(score, 0.0), 3)
    else:
        # Too long
        return round(max_acceptable / length, 3)


def _tokenize_for_matching(text: str) -> List[str]:
    """Tokenize text for matching/relevance calculation."""
    # Keep alphanumeric tokens, remove stop words for matching
    stop_words = {
        "the", "and", "that", "this", "with", "from", "have", "are", "was",
        "for", "not", "but", "can", "will", "your", "our", "you", "i", "me",
        "my", "it", "he", "she", "we", "they", "them", "his", "her"
    }
    tokens = re.findall(r"[a-z0-9]+", text)
    return [t for t in tokens if t not in stop_words and len(t) > 2]


def _has_question_pattern(text: str) -> bool:
    """Check if text has a question pattern."""
    question_patterns = [
        r"\?", r"\b(what|how|why|when|where|which)\b",
        r"\b(can you|do you|would you|should you)\b",
    ]
    return any(re.search(pattern, text) for pattern in question_patterns)


def _has_answer_pattern(text: str) -> bool:
    """Check if text has answer-like patterns."""
    answer_markers = [
        r"\b(can|is|are|does|do|did)\b", 
        r"\b(you can|you can|the way to|the answer is)\b",
    ]
    return any(re.search(pattern, text) for pattern in answer_markers)


def score_response(
    user_message: str,
    response: str,
    context_chunks: Optional[List[Dict]] = None,
) -> ResponseScore:
    """Score a chatbot response across multiple quality dimensions.
    
    Args:
        user_message: The original user message
        response: The bot's response
        context_chunks: Optional RAG context chunks for groundedness evaluation
    
    Returns:
        ResponseScore object with all dimension scores
    """
    relevance = _calculate_relevance(user_message, response)
    coherence = _calculate_coherence(response)
    groundedness = _calculate_groundedness(response, context_chunks or [])
    safety = _calculate_safety(response, user_message)
    conciseness = _calculate_conciseness(response)
    
    # Weighted overall score
    # relevance: 30%, coherence: 25%, groundedness: 25%, safety: 15%, conciseness: 5%
    overall = round(
        0.30 * relevance +
        0.25 * coherence +
        0.25 * groundedness +
        0.15 * safety +
        0.05 * conciseness,
        3
    )
    
    return ResponseScore(
        relevance=relevance,
        coherence=coherence,
        groundedness=groundedness,
        safety=safety,
        conciseness=conciseness,
        overall=overall,
    )


def evaluate_batch(
    test_cases: List[Tuple[str, str, Optional[List[Dict]]]],
    model_response_fn,
) -> List[ResponseScore]:
    """Evaluate a batch of test cases and return scores.
    
    Args:
        test_cases: List of (user_message, expected_intent, context_chunks) tuples
        model_response_fn: Function that takes user_message and returns a response
    
    Returns:
        List of ResponseScore objects
    """
    results = []
    for user_message, expected_intent, context_chunks in test_cases:
        response = model_response_fn(user_message)
        score = score_response(user_message, response, context_chunks)
        results.append(score)
        logger.info(f"Score for '{user_message[:50]}...': {score}")
    
    return results