from transformers import AutoTokenizer, AutoModelForCausalLM
try:
    import torch
except ImportError:
    torch = None
import config


def load_model():
    print(f"Loading model: {config.MODEL_NAME}")
    tokenizer = AutoTokenizer.from_pretrained(config.MODEL_NAME)
    model_kwargs = {"low_cpu_mem_usage": True}
    if torch is not None and config.DEVICE == "cuda":
        model_kwargs["torch_dtype"] = torch.float16

    model = AutoModelForCausalLM.from_pretrained(config.MODEL_NAME, **model_kwargs)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model.to(config.DEVICE)
    model.eval()
    print(f"Model loaded on {config.DEVICE}")
    return tokenizer, model


def generate_response(tokenizer, model, input_text):
    input_ids = tokenizer.encode(
        input_text,
        return_tensors="pt",
        truncation=True,
        max_length=config.MAX_INPUT_LENGTH
    ).to(config.DEVICE)

    no_grad = torch.no_grad() if torch is not None else _NullContext()
    with no_grad:
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


class _NullContext:
    def __enter__(self):
        return None

    def __exit__(self, exc_type, exc, tb):
        return False
