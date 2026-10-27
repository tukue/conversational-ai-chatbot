"""Delivery support guidance; no live order access or transaction execution."""
import re

# Specific delivery issues take precedence over broad retail intent keywords.
DELIVERY_TOPICS = {
    "change_address": (r"\b(change|update|wrong)\b.*\baddress\b",
                       "For an address change, open the order and use Help immediately. Changes depend on the order stage. Enter the new address only in the platform's secure form; I cannot update it here."),
    "missing_items": (r"\b(missing (items?|food|groceries)|items? (are |is )?missing|wrong (items?|food|order)|incomplete order)\b",
                      "For missing or wrong items, open Orders, select the delivery, then Help and choose the affected items. Share only your order number here; upload photos through the secure support form. Support will review refund or replacement eligibility; I cannot issue either here."),
    "late_delivery": (r"\b(late|delayed|delay|taking too long|cold food)\b",
                      "For a late delivery, open Orders and select Track delivery to check the latest estimate. If the estimate has passed or food arrived cold, use Help on that order. I cannot see your courier's location or promise an arrival time here."),
    "courier": (r"\b(courier|driver|rider)\b",
                "To contact your courier, open the active order and use the contact option if available. If you cannot reach them, choose Help on the order. Keep phone numbers, addresses, and access codes out of this chat."),
    "delivery_area": (r"\b(delivery area|delivery zone|deliver to|coverage|stockholm)\b",
                      "Check delivery availability by entering your address in the platform's secure checkout. Available stores, delivery fees, and estimates depend on the location; do not post your address here."),
    "checkout": (r"\b(cart|checkout|basket)\b",
                 "Open your cart to review items and quantities, then proceed to checkout. Confirm the delivery details, available time, fees, and payment method there. If checkout fails, share the error message without card details or other personal information."),
    "delivery_fee": (r"\b(delivery (fee|cost)|shipping (fee|cost)|free shipping)\b",
                     "Delivery fees and minimum order amounts are shown at checkout before payment. They can vary by store and location; I cannot confirm a fee from this chat."),
    "delivery_time": (r"\b(delivery time|shipping time|how long|when will it arrive)\b",
                      "Check the delivery estimate at checkout before ordering, or Track delivery in Orders for an existing order. Estimates depend on store preparation and courier availability; I cannot access live estimates here."),
    "refund": (r"\b(refund|return policy|return an item|return item)\b",
               "To request a return or refund, open Orders, select the order, and choose Help. Explain the affected items and the issue. Eligibility depends on the item and store policy, especially for perishable groceries and meals. I cannot approve refunds or promise processing times here."),
    "cancel": (r"\b(cancel (my |an |the )?order|cancellation)\b",
               "To request cancellation, open Orders and select the order. Use Cancel if available, or Help if preparation has started. Eligibility and any charge depend on the order stage. Share only your order number here; I cannot cancel an order directly."),
    "payment_methods": (r"\b(payment methods?|swish|klarna|how to pay)\b",
                        "Available payment methods are shown in secure checkout and may vary by location and store. Select a method there; never share card numbers, verification codes, or banking credentials in this chat."),
    "catalog": (r"\b(grocer(y|ies)|meals?|pharmacy|catalog|browse)\b",
                "Browse the platform catalog for groceries, meals, and essentials available in your delivery area. Availability and prices are confirmed in the platform. For pharmacy or prescription eligibility, contact the licensed pharmacy partner through secure support."),
}


def delivery_response(message):
    for topic, (pattern, response) in DELIVERY_TOPICS.items():
        if re.search(pattern, message, re.I):
            from src.monitoring import record_event
            record_event("route_" + topic)
            return response
    return None


def is_delivery_query(message):
    return any(re.search(pattern, message, re.I) for pattern, _ in DELIVERY_TOPICS.values())
