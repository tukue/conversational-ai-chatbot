from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import config


def load_model():
    print(f"Loading model: {config.MODEL_NAME}")
    tokenizer = AutoTokenizer.from_pretrained(config.MODEL_NAME)
    model = AutoModelForCausalLM.from_pretrained(config.MODEL_NAME)
    model.to(config.DEVICE)
    print(f"Model loaded on {config.DEVICE}")
    return tokenizer, model


def generate_response(tokenizer, model, input_text):
    input_ids = tokenizer.encode(
        input_text,
        return_tensors="pt",
        truncation=True,
        max_length=config.MAX_INPUT_LENGTH
    ).to(config.DEVICE)

    output_ids = model.generate(
        input_ids,
        max_new_tokens=config.MAX_NEW_TOKENS,
        do_sample=True,
        top_k=config.TOP_K,
        top_p=config.TOP_P,
        temperature=config.TEMPERATURE,
        pad_token_id=tokenizer.eos_token_id
    )

    response = tokenizer.decode(
        output_ids[:, input_ids.shape[-1]:][0],
        skip_special_tokens=True
    )

    return response
