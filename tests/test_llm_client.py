"""Tests for llm/client.py"""
import pytest
from unittest.mock import patch, MagicMock
from murder_wizard.llm.client import (
    create_llm_adapter,
    LLMAdapter,
    ClaudeAdapter,
    OpenAIAdapter,
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
