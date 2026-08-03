import config


AutoTokenizer = None
AutoModelForCausalLM = None


def load_model():
    global AutoTokenizer, AutoModelForCausalLM
    if AutoTokenizer is None or AutoModelForCausalLM is None:
        try:
            from transformers import AutoTokenizer as TransformersAutoTokenizer
            from transformers import AutoModelForCausalLM as TransformersAutoModelForCausalLM
        except ImportError as exc:
            raise RuntimeError(
                "Model dependencies are not installed. Install requirements.txt to enable DialoGPT responses."
            ) from exc

        AutoTokenizer = TransformersAutoTokenizer
        AutoModelForCausalLM = TransformersAutoModelForCausalLM

    print(f"Loading model: {config.MODEL_NAME}")
    tokenizer = AutoTokenizer.from_pretrained(config.MODEL_NAME)
    model_kwargs = {"low_cpu_mem_usage": True}
    if config.DEVICE == "cuda":
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

    with torch.no_grad():
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
