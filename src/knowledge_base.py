import json
import os


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def load_json(filename):
    path = os.path.join(DATA_DIR, filename)
    with open(path, "r") as f:
        return json.load(f)


def _word_overlap(a, b):
    words_a = set(a.lower().split())
    words_b = set(b.lower().split())
    if not words_a or not words_b:
        return 0
    intersection = words_a & words_b
    return len(intersection) / max(len(words_a), len(words_b))


class FAQSearch:
    def __init__(self):
        self.faqs = load_json("faq.json")

    def search(self, query, top_k=3):
        query_lower = query.lower()
        query_words = set(query_lower.split())
        scored = []

        for faq in self.faqs:
            kw_overlap = max(
                (_word_overlap(query_lower, kw) for kw in faq["keywords"]),
                default=0,
            )
            q_overlap = _word_overlap(query_lower, faq["question"])
            score = max(kw_overlap * 1.5, q_overlap)

            # Bonus: exact keyword match
            for kw in faq["keywords"]:
                if kw in query_lower:
                    score = max(score, 1.0)
                    break

            scored.append((score, faq))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for score, item in scored if score > 0][:top_k]


class ProductSearch:
    def __init__(self):
        self.products = load_json("products.json")

    def search(self, query, top_k=3):
        query_lower = query.lower()
        query_words = set(query_lower.split())
        scored = []

        for product in self.products:
            name_overlap = _word_overlap(query_lower, product["name"])
            desc_overlap = _word_overlap(query_lower, product["description"])
            cat_overlap = _word_overlap(query_lower, product["category"])
            score = max(name_overlap * 2, desc_overlap, cat_overlap * 1.2)
            scored.append((score, product))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for score, item in scored if score > 0][:top_k]

    def get_by_id(self, product_id):
        for p in self.products:
            if p["id"] == product_id:
                return p
        return None
