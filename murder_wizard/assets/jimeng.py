"""即梦 AI 图像生成适配器."""
import os
import time
from typing import Optional


class JimengAdapter:
    """即梦 AI 图像生成"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("JIMENG_API_KEY")
        self.base_url = "https://api.jimeng.jianying.com"

    def generate(self, prompt: str, style: str = "国风") -> str:
        """
        生成图像。

        Returns:
            图片 URL 或本地路径

        Raises:
            RuntimeError: 生成失败时
        """
        if not self.api_key:
            raise RuntimeError("JIMENG_API_KEY not configured")

        # TODO: 实现即梦 API 调用
        # 即梦 API 文档：https://jianying.jimeng.aliyun.com/
        raise NotImplementedError("即梦 API integration pending")


class HaibaoAdapter:
    """海螺 AI 视频生成"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("HAIBO_API_KEY")
        self.base_url = "https://api.haibo.cn"

    def generate(self, prompt: str, duration: int = 5) -> str:
        """
        生成视频。

        Args:
            prompt: 视频描述
            duration: 视频时长（秒）

        Returns:
            视频 URL 或本地路径
        """
        if not self.api_key:
            raise RuntimeError("HAIBO_API_KEY not configured")

        # TODO: 实现海螺 API 调用
        raise NotImplementedError("海螺 API integration pending")
