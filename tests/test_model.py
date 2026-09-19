import sys
import os
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest


@pytest.fixture(autouse=True)
def mock_torch():
    mock = MagicMock()
    with patch.dict("sys.modules", {"torch": mock}):
        yield mock


@patch("src.model.AutoTokenizer")
@patch("src.model.AutoModelForCausalLM")
def test_load_model_returns_tokenizer_and_model(mock_model_cls, mock_tokenizer_cls):
    from src.model import load_model

    mock_tokenizer = MagicMock()
    mock_model = MagicMock()
    mock_tokenizer_cls.from_pretrained.return_value = mock_tokenizer
    mock_model_cls.from_pretrained.return_value = mock_model

    tokenizer, model = load_model()

    mock_tokenizer_cls.from_pretrained.assert_called_once()
    mock_model_cls.from_pretrained.assert_called_once()
    assert tokenizer == mock_tokenizer
    assert model == mock_model


@patch("src.model.AutoTokenizer")
@patch("src.model.AutoModelForCausalLM")
def test_generate_response_calls_model_generate(mock_model_cls, mock_tokenizer_cls):
    from src.model import generate_response

    mock_tokenizer = MagicMock()
    mock_model = MagicMock()
    mock_tokenizer.encode.return_value = MagicMock()
    mock_model.generate.return_value = MagicMock()
    mock_tokenizer.decode.return_value = "Test response"

    result = generate_response(mock_tokenizer, mock_model, "Hello")

    mock_tokenizer.encode.assert_called_once()
    mock_model.generate.assert_called_once()
    assert result == "Test response"


@patch("src.model.AutoTokenizer")
@patch("src.model.AutoModelForCausalLM")
def test_generate_response_uses_correct_device(mock_model_cls, mock_tokenizer_cls):
    from src.model import generate_response
    import config

    mock_tokenizer = MagicMock()
    mock_model = MagicMock()
    mock_input = MagicMock()
    mock_tokenizer.encode.return_value = mock_input
    mock_model.generate.return_value = MagicMock()
    mock_tokenizer.decode.return_value = "ok"

    generate_response(mock_tokenizer, mock_model, "Hi")

    mock_input.to.assert_called_once_with(config.DEVICE)


@patch("src.model.AutoTokenizer")
@patch("src.model.AutoModelForCausalLM")
def test_generate_response_truncates_long_input(mock_model_cls, mock_tokenizer_cls):
    from src.model import generate_response

    mock_tokenizer = MagicMock()
    mock_model = MagicMock()
    mock_tokenizer.encode.return_value = MagicMock()
    mock_model.generate.return_value = MagicMock()
    mock_tokenizer.decode.return_value = "ok"

    generate_response(mock_tokenizer, mock_model, "A" * 5000)

    call_kwargs = mock_tokenizer.encode.call_args[1]
    assert call_kwargs.get("truncation") is True
    assert call_kwargs.get("max_length") is not None


@patch("src.model.AutoTokenizer")
@patch("src.model.AutoModelForCausalLM")
def test_generate_response_skips_input_tokens_in_output(mock_model_cls, mock_tokenizer_cls):
    from src.model import generate_response

    mock_tokenizer = MagicMock()
    mock_model = MagicMock()

    mock_input_ids = MagicMock()
    mock_input_ids.shape = [1, 5]
    mock_tokenizer.encode.return_value = mock_input_ids

    mock_output_ids = MagicMock()
    mock_model.generate.return_value = mock_output_ids

    mock_tokenizer.decode.return_value = "bot reply"

    result = generate_response(mock_tokenizer, mock_model, "Hello")

    mock_tokenizer.decode.assert_called_with(
        mock_output_ids[:, 5:][0],
        skip_special_tokens=True
    )
    assert result == "bot reply"
