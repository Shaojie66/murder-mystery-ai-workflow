"""LLM client adapter - supports Claude and OpenAI."""
import os
import time
from abc import ABC, abstractmethod
from typing import Optional, Iterator
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """LLM 响应"""
    content: str
    tokens_used: int
    cost: float
    model: str


class LLMAdapter(ABC):
    """LLM 适配器基类"""

    model: str  # 子类必须定义

    @abstractmethod
    def complete(self, prompt: str, system: str = "") -> LLMResponse:
        """同步完成调用"""
        pass

    @abstractmethod
    def complete_streaming(self, prompt: str, system: str = "") -> Iterator[str]:
        """流式完成调用"""
        pass

    @abstractmethod
    def cost_per_token(self) -> float:
        """每 token 成本"""
        pass


class ClaudeAdapter(LLMAdapter):
    """Anthropic Claude 适配器"""

    def __init__(self, api_key: Optional[str] = None):
        try:
            from anthropic import Anthropic
        except ImportError:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")

        self.client = Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))
        self.model = "claude-3-5-sonnet-20241022"

    def complete(self, prompt: str, system: str = "") -> LLMResponse:
        import anthropic
        max_retries = 3
        base_delay = 2

        for attempt in range(max_retries):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    system=system,
                    messages=[{"role": "user", "content": prompt}]
                )
                content = response.content[0].text
                input_tokens = response.usage.input_tokens
                output_tokens = response.usage.output_tokens
                total_tokens = input_tokens + output_tokens

                # Claude pricing: $3/MTok input, $15/MTok output
                cost = (input_tokens / 1_000_000) * 3 + (output_tokens / 1_000_000) * 15

                return LLMResponse(
                    content=content,
                    tokens_used=total_tokens,
                    cost=cost,
                    model=self.model
                )
            except anthropic.RateLimitError:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    time.sleep(delay)
                else:
                    raise
            except Exception as e:
                raise

    def complete_streaming(self, prompt: str, system: str = "") -> Iterator[str]:
        # 实现流式输出
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            stream=True
        )
        for event in response:
            if event.type == "content_block_delta":
                yield event.delta.text

    def cost_per_token(self) -> float:
        return 0.000015  # Claude 3.5 Sonnet 平均成本


class OpenAIAdapter(LLMAdapter):
    """OpenAI GPT 适配器"""

    def __init__(self, api_key: Optional[str] = None):
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")

        self.client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))
        self.model = "gpt-4o"

    def complete(self, prompt: str, system: str = "") -> LLMResponse:
        from openai import RateLimitError
        max_retries = 3
        base_delay = 2

        for attempt in range(max_retries):
            try:
                messages = []
                if system:
                    messages.append({"role": "system", "content": system})
                messages.append({"role": "user", "content": prompt})

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=4096,
                )
                content = response.choices[0].message.content
                tokens = response.usage.total_tokens
                # GPT-4o: $5/MTok input, $15/MTok output
                cost = (tokens / 1_000_000) * 10  # 平均

                return LLMResponse(
                    content=content,
                    tokens_used=tokens,
                    cost=cost,
                    model=self.model
                )
            except RateLimitError:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    time.sleep(delay)
                else:
                    raise
            except Exception as e:
                raise

    def complete_streaming(self, prompt: str, system: str = "") -> Iterator[str]:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True
        )
        for event in response:
            if event.choices[0].delta.content:
                yield event.choices[0].delta.content

    def cost_per_token(self) -> float:
        return 0.00001  # GPT-4o 平均成本


def create_llm_adapter(provider: str = "claude") -> LLMAdapter:
    """工厂函数：创建 LLM 适配器"""
    if provider == "claude":
        return ClaudeAdapter()
    elif provider == "openai" or provider == "gpt":
        return OpenAIAdapter()
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
