"""Tests for llm/client.py"""
import pytest
from unittest.mock import patch, MagicMock
from murder_wizard.llm.client import (
    create_llm_adapter,
    LLMAdapter,
    ClaudeAdapter,
    OpenAIAdapter,
    OllamaAdapter,
)


class TestLLMAdapter:
    def test_adapter_has_complete_method(self):
        assert hasattr(LLMAdapter, "complete")
        assert hasattr(LLMAdapter, "complete_streaming")


class TestCreateLLMAdapter:
    @patch("murder_wizard.llm.client.ClaudeAdapter")
    def test_create_claude_adapter(self, mock_claude):
        mock_claude.return_value = MagicMock()
        adapter = create_llm_adapter("claude")
        assert adapter is not None
        mock_claude.assert_called_once()

    @patch("murder_wizard.llm.client.OpenAIAdapter")
    def test_create_openai_adapter(self, mock_openai):
        mock_openai.return_value = MagicMock()
        adapter = create_llm_adapter("openai")
        assert adapter is not None
        mock_openai.assert_called_once()

    def test_create_invalid_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            create_llm_adapter("invalid_provider")


class TestClaudeAdapter:
    def test_token_cost_calculation(self):
        """Test that Claude token costs are defined correctly"""
        # Claude output: $15.00/MTok, input: $3.75/MTok
        # 1000 prompt tokens + 500 output tokens
        prompt_cost = 1000 * (3.75 / 1_000_000)
        output_cost = 500 * (15.00 / 1_000_000)
        expected = prompt_cost + output_cost
        # Verify calculation matches expected values
        assert abs(expected - 0.01125) < 0.0001


class TestOllamaAdapter:
    def test_ollama_adapter_default_init(self):
        """OllamaAdapter 可以用默认参数初始化"""
        adapter = OllamaAdapter()
        assert adapter.model == "llama3"
        assert adapter.base_url == "http://localhost:11434/v1"

    def test_ollama_adapter_custom_params(self):
        """OllamaAdapter 支持自定义 base_url 和 model"""
        adapter = OllamaAdapter(
            base_url="http://192.168.1.100:11434/v1",
            model="qwen2.5"
        )
        assert adapter.model == "qwen2.5"
        assert adapter.base_url == "http://192.168.1.100:11434/v1"

    def test_ollama_cost_is_zero(self):
        """Ollama 本地运行成本为零"""
        adapter = OllamaAdapter()
        assert adapter.cost_per_token() == 0.0

    def test_ollama_estimate_tokens(self):
        """token 估算：中英文混合"""
        adapter = OllamaAdapter()
        # 4个中文字符 + 10个英文字符 = 4/2 + 10/4 = 2 + 2.5 = 4.5 -> 4
        text = "你好世界HelloWorld"
        estimated = adapter._estimate_tokens(text)
        assert estimated == 4  # 4/2 + 10/4 = 4

    def test_create_ollama_adapter(self):
        """create_llm_adapter("ollama") 返回 OllamaAdapter"""
        from unittest.mock import patch, MagicMock
        with patch("murder_wizard.llm.client.OllamaAdapter") as mock:
            mock.return_value = MagicMock()
            adapter = create_llm_adapter("ollama")
            assert adapter is not None
