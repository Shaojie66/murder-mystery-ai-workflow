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

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        try:
            from anthropic import Anthropic
        except ImportError:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")

        self.client = Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))
        self.model = model or os.environ.get("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")

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


class MiniMaxAdapter(LLMAdapter):
    """MiniMax 适配器 - 使用 Anthropic SDK 格式"""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: Optional[str] = None):
        try:
            from anthropic import Anthropic
        except ImportError:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")

        base_url = base_url or os.environ.get("MINIMAX_BASE_URL", "https://api.minimax.io/anthropic")
        api_key = api_key or os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("MINIMAX_API_KEY", "")

        self.client = Anthropic(
            api_key=api_key,
            base_url=base_url,
        )
        self.model = model or os.environ.get("MINIMAX_MODEL", "MiniMax-M2.7")

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
                # MiniMax may return thinking blocks before text blocks
                content = ""
                for block in response.content:
                    if block.type == "text":
                        content = block.text
                        break
                input_tokens = response.usage.input_tokens
                output_tokens = response.usage.output_tokens
                total_tokens = input_tokens + output_tokens

                # MiniMax pricing - use estimate similar to Claude
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
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            stream=True
        )
        for event in response:
            if event.type == "content_block_delta":
                # Skip thinking blocks (MiniMax)
                if hasattr(event.delta, 'type') and event.delta.type == 'thinking_delta':
                    continue
                if event.delta.text:
                    yield event.delta.text

    def cost_per_token(self) -> float:
        return 0.000015  # MiniMax estimate


class OpenAIAdapter(LLMAdapter):
    """OpenAI GPT 适配器"""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")

        self.client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))
        self.model = model or os.environ.get("OPENAI_MODEL", "gpt-4o")

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


class OllamaAdapter(LLMAdapter):
    """Ollama 本地 LLM 适配器（OpenAI 兼容 API）。

    使用 Ollama 的 OpenAI 兼容端点 http://localhost:11434/v1/chat/completions。
    支持用户配置自定义 base_url 和 model，不依赖云端 API。
    """

    # 允许的本地 host 名（剧本杀内容不会发往远程）
    LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}

    def __init__(
        self,
        base_url: str = "http://localhost:11434/v1",
        model: str = "llama3",
        api_key: Optional[str] = None,
        extra_headers: Optional[dict] = None,
    ):
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")

        # URL 安全检查：只允许 http/https，不允许空 URL
        if not base_url or not base_url.startswith(("http://", "https://")):
            raise ValueError(
                f"Ollama base_url 必须以 http:// 或 https:// 开头，当前值：{base_url!r}"
            )

        # 检查是否发往远程——非 localhost 则发出警告
        parsed = None
        try:
            from urllib.parse import urlparse
            parsed = urlparse(base_url)
        except Exception:
            pass

        if parsed and parsed.hostname and parsed.hostname not in self.LOCAL_HOSTS:
            import sys
            print(
                f"WARNING: Ollama base_url 指向远程地址 {parsed.hostname}，"
                f"剧本内容将被发送到该服务器。\n"
                f"  如果这不是预期行为，请检查 OLLAMA_BASE_URL 环境变量。\n"
                f"  如需强制使用远程地址，设置环境变量 OLLAMA_NO_URL_WARN=1 跳过此警告。",
                file=sys.stderr,
            )

        self.base_url = base_url
        self.model = model
        self.extra_headers = extra_headers or {}
        self.client = OpenAI(
            api_key=api_key or os.environ.get("OLLAMA_API_KEY") or "ollama",
            base_url=base_url,
            default_headers=self.extra_headers,
        )

    def complete(self, prompt: str, system: str = "") -> LLMResponse:
        """调用 Ollama（OpenAI 兼容端点）"""
        from openai import APIError, RateLimitError
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
                # Ollama 不返回 usage.token_count 时估计
                tokens = getattr(response.usage, "total_tokens", None) or self._estimate_tokens(prompt + content)
                # Ollama 本地运行，成本为零
                cost = 0.0

                return LLMResponse(
                    content=content,
                    tokens_used=tokens,
                    cost=cost,
                    model=self.model
                )
            except (APIError, RateLimitError):
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    time.sleep(delay)
                else:
                    raise
            except Exception as e:
                raise

        raise RuntimeError(f"Ollama 调用失败（已重试 {max_retries} 次）：{e}")

    def complete_streaming(self, prompt: str, system: str = "") -> Iterator[str]:
        """Ollama 流式输出"""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=4096,
            stream=True
        )
        for event in response:
            if event.choices and event.choices[0].delta.content:
                yield event.choices[0].delta.content

    def cost_per_token(self) -> float:
        """本地 Ollama 无 API 成本"""
        return 0.0

    def _estimate_tokens(self, text: str) -> int:
        """粗略估计 token 数（中文约 2 字符/token，英文约 4 字符/token）"""
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        other_chars = len(text) - chinese_chars
        return int(chinese_chars / 2 + other_chars / 4)


def _load_settings_from_file():
    """Load settings from the settings file."""
    from pathlib import Path
    import json

    settings_path = Path.home() / ".murder-wizard" / "settings.json"
    if not settings_path.exists():
        return None

    try:
        return json.loads(settings_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def create_llm_adapter(provider: str = None, settings: dict = None) -> LLMAdapter:
    """工厂函数：创建 LLM 适配器

    Args:
        provider: "claude" / "openai" / "ollama" / "minimax" (optional, reads from settings)
        settings: Settings dict from settings.json (optional)
    """
    # Load from settings file if not provided
    if settings is None:
        settings = _load_settings_from_file()

    # Get provider from settings if not explicitly provided
    if provider is None and settings:
        provider = settings.get("llm", {}).get("provider", "minimax")
    elif provider is None:
        provider = "minimax"  # Default

    llm_config = settings.get("llm", {}) if settings else {}

    if provider == "claude":
        api_key = llm_config.get("api_key") or os.environ.get("ANTHROPIC_API_KEY")
        return ClaudeAdapter(api_key=api_key)
    elif provider == "openai" or provider == "gpt":
        api_key = llm_config.get("api_key") or os.environ.get("OPENAI_API_KEY")
        return OpenAIAdapter(api_key=api_key)
    elif provider == "ollama":
        base_url = llm_config.get("base_url") or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        model = llm_config.get("model") or os.environ.get("OLLAMA_MODEL", "llama3")
        return OllamaAdapter(base_url=base_url, model=model)
    elif provider == "minimax":
        api_key = llm_config.get("api_key") or os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("MINIMAX_API_KEY", "")
        base_url = llm_config.get("base_url") or os.environ.get("MINIMAX_BASE_URL", "https://api.minimax.io/anthropic")
        model = llm_config.get("model") or os.environ.get("MINIMAX_MODEL", "MiniMax-M2.7")
        return MiniMaxAdapter(api_key=api_key, base_url=base_url, model=model)
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
