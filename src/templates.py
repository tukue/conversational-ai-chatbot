TEMPLATES = {
    "greeting": [
        "Hello! Welcome to our store. How can I help you today?",
        "Hi there! I'm your customer support assistant. What can I do for you?",
    ],
    "closing": [
        "You're welcome! If you ever need anything else, we're here to help. Have a great day!",
        "Glad I could help! Don't hesitate to reach out if you have more questions.",
    ],
    "order_status": [
        "I'd be happy to check your order status. Could you please provide your order number?",
    ],
    "cancel_order": [
        "I can help with that! Could you please provide your order number so I can check if it's still eligible for cancellation?",
    ],
    "return_request": [
        "I understand you'd like to return an item. Please share only your order number here, and use the secure returns form for private details.",
    ],
    "shipping_info": [
        "I'd be happy to help with shipping questions! Could you tell me what you'd like to know — delivery times, costs, or something else?",
    ],
    "payment_issue": [
        "I'm sorry you're having trouble with payment. Let me help you sort this out. Can you tell me what error message you're seeing?",
    ],
    "payment_method": [
        "We accept Visa, Mastercard, American Express, Discover, PayPal, Apple Pay, Google Pay, and Shop Pay. What would you like to use?",
    ],
    "product_inquiry": [
        "I'd be happy to help you find what you're looking for! What type of product are you interested in?",
    ],
    "damaged_item": [
        "I'm so sorry your item arrived damaged. Please share only your order number here. Use the secure support form to upload photos or private details.",
    ],
    "exchange": [
        "I can help with an exchange! Please share your order number and the size/variant you need instead.",
    ],
    "lost_package": [
        "I understand your package hasn't arrived. Let me look into this for you. Could you provide your order number?",
    ],
    "change_address": [
        "I can help start an address update. Please share only your order number here, then use the secure support form for the new address.",
    ],
    "discount": [
        "Looking for a deal? Please provide the promo code you'd like to use, or check our current promotions on the homepage!",
    ],
    "gift_card": [
        "I can help with gift cards! You can check your balance in your account, or let me know if you need help applying one to an order.",
    ],
    "complaint": [
        "I'm sorry to hear you're unhappy. Let me do my best to make this right. Please tell me what happened so I can help.",
    ],
    "contact_human": [
        "I understand you'd like to speak with a human agent. Let me transfer you. In the meantime, could you briefly describe your issue so I can pass it along?",
    ],
    "escalate": [
        "I'll escalate this to a supervisor right away. Please expect a call or email within 2 hours. Your case ID will be provided shortly.",
    ],
    "general": [
        "I'm not sure I understand. Could you tell me more? I can help with orders, returns, shipping, products, and more.",
    ],
}


def get_template(intent):
    import random
    responses = TEMPLATES.get(intent, TEMPLATES["general"])
    return random.choice(responses)
