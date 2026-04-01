"""Vidu AI 视频/图像生成适配器.

API文档: https://platform.vidu.cn
支持: text2video, img2video, ref2video, nano-image, tts, voice-clone

环境变量:
    VIDU_API_KEY: Vidu API密钥（从 https://platform.vidu.cn 获取）

注意:
    vda_... 格式是任务ID，不是API密钥。需要在VIDU平台申请真正的API密钥。
"""
import os
import time
import requests
from typing import Optional


class ViduAdapter:
    """Vidu AI 视频/图像生成"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("VIDU_API_KEY")
        # Chinese users -> api.vidu.cn, others -> api.vidu.com
        self.base_url = "https://api.vidu.cn/ent/v2"
        self._session = requests.Session()
        if self.api_key:
            self._session.headers.update({"Authorization": f"Bearer {self.api_key}"})

    def _post(self, endpoint: str, data: dict, timeout: int = 60) -> dict:
        """POST请求到Vidu API"""
        if not self.api_key:
            raise RuntimeError("VIDU_API_KEY not configured")

        url = f"{self.base_url}{endpoint}"
        resp = self._session.post(url, json=data, timeout=timeout)
        resp.raise_for_status()
        return resp.json()

    def _wait_for_completion(self, task_id: str, timeout: int = 300) -> dict:
        """等待任务完成"""
        start = time.time()
        while time.time() - start < timeout:
            result = self._get_task_status(task_id)
            status = result.get("status", "")
            if status == "success":
                return result
            elif status == "failed":
                raise RuntimeError(f"Vidu任务失败: {result.get('error', 'unknown')}")
            time.sleep(5)
        raise TimeoutError(f"Vidu任务超时: {task_id}")

    def _get_task_status(self, task_id: str) -> dict:
        """查询任务状态"""
        url = f"{self.base_url}/creations/{task_id}"
        resp = self._session.get(url, timeout=30)
        resp.raise_for_status()
        return resp.json()

    # ──────────────────────────────────────────────────────────────────
    # 视频生成
    # ──────────────────────────────────────────────────────────────────

    def text2video(
        self,
        prompt: str,
        duration: int = 5,
        resolution: str = "720p",
        aspect_ratio: str = "16:9",
        model: str = "viduq3-pro",
        wait: bool = True,
    ) -> str:
        """
        文生视频

        Args:
            prompt: 视频描述
            duration: 视频时长（秒），默认5秒
            resolution: 分辨率，默认720p
            aspect_ratio: 宽高比，默认16:9
            model: 模型，默认viduq3-pro
            wait: 是否等待生成完成

        Returns:
            视频URL或任务ID（wait=False时）
        """
        data = {
            "model": model,
            "duration": duration,
            "resolution": resolution,
            "aspect_ratio": aspect_ratio,
            "prompt": prompt,
        }
        result = self._post("/video/generate/text2video", data)
        task_id = result.get("task_id") or result.get("id")
        if not task_id:
            raise RuntimeError(f"Vidu返回无效: {result}")

        if wait:
            final = self._wait_for_completion(task_id)
            creations = final.get("creations", [])
            if creations:
                return creations[0].get("url", "")
            raise RuntimeError(f"Vidu生成为空: {final}")

        return task_id

    def img2video(
        self,
        image_url: str,
        prompt: str,
        duration: int = 5,
        model: str = "viduq3-pro-fast",
        wait: bool = True,
    ) -> str:
        """
        图生视频

        Args:
            image_url: 图片URL
            prompt: 视频描述
            duration: 视频时长（秒），默认5秒
            model: 模型，默认viduq3-pro-fast
            wait: 是否等待生成完成

        Returns:
            视频URL或任务ID
        """
        data = {
            "model": model,
            "duration": duration,
            "image_url": image_url,
            "prompt": prompt,
        }
        result = self._post("/video/generate/img2video", data)
        task_id = result.get("task_id") or result.get("id")

        if wait:
            final = self._wait_for_completion(task_id)
            creations = final.get("creations", [])
            if creations:
                return creations[0].get("url", "")
            raise RuntimeError(f"Vidu生成为空: {final}")

        return task_id

    def ref2video(
        self,
        image_urls: list[str],
        prompt: str,
        duration: int = 5,
        model: str = "viduq3-pro",
        wait: bool = True,
    ) -> str:
        """
        参考图生视频

        Args:
            image_urls: 参考图片URL列表（最多5张）
            prompt: 视频描述
            duration: 视频时长（秒）
            model: 模型
            wait: 是否等待生成完成

        Returns:
            视频URL或任务ID
        """
        data = {
            "model": model,
            "duration": duration,
            "images": image_urls[:5],
            "prompt": prompt,
        }
        result = self._post("/video/generate/ref2video", data)
        task_id = result.get("task_id") or result.get("id")

        if wait:
            final = self._wait_for_completion(task_id)
            creations = final.get("creations", [])
            if creations:
                return creations[0].get("url", "")
            raise RuntimeError(f"Vidu生成为空: {final}")

        return task_id

    # ──────────────────────────────────────────────────────────────────
    # 图像生成
    # ──────────────────────────────────────────────────────────────────

    def nano_image(
        self,
        prompt: str,
        resolution: str = "2K",
        model: str = "q3-fast",
        aspect_ratio: str = "16:9",
    ) -> str:
        """
        文生图像（nano模式）

        Args:
            prompt: 图像描述
            resolution: 分辨率，默认2K
            model: 模型，默认q3-fast
            aspect_ratio: 宽高比，默认16:9

        Returns:
            图片URL
        """
        data = {
            "model": model,
            "resolution": resolution,
            "aspect_ratio": aspect_ratio,
            "prompt": prompt,
        }
        result = self._post("/image/generate/nano", data)
        creations = result.get("creations", [])
        if not creations:
            raise RuntimeError(f"Vidu图像生成为空: {result}")
        return creations[0].get("url", "")

    # ──────────────────────────────────────────────────────────────────
    # 语音合成
    # ──────────────────────────────────────────────────────────────────

    def tts(
        self,
        text: str,
        voice_id: str = "female-shaonv",
        wait: bool = True,
    ) -> str:
        """
        文本转语音

        Args:
            text: 要转换的文本
            voice_id: 音色ID，默认female-shaonv
            wait: 是否等待生成完成

        Returns:
            音频URL或任务ID
        """
        data = {
            "text": text,
            "voice_id": voice_id,
        }
        result = self._post("/audio/tts", data)
        task_id = result.get("task_id") or result.get("id")

        if wait:
            final = self._wait_for_completion(task_id)
            creations = final.get("creations", [])
            if creations:
                return creations[0].get("url", "")
            raise RuntimeError(f"Vidu TTS生成为空: {final}")

        return task_id

    def voice_clone(
        self,
        audio_url: str,
        voice_id: str,
        text: str = "",
        wait: bool = True,
    ) -> str:
        """
        声音克隆

        Args:
            audio_url: 参考音频URL
            voice_id: 生成的音色ID
            text: 要转换的文本（可选）
            wait: 是否等待生成完成

        Returns:
            音频URL或任务ID
        """
        data = {
            "audio_url": audio_url,
            "voice_id": voice_id,
        }
        if text:
            data["text"] = text
        result = self._post("/audio/clone", data)
        task_id = result.get("task_id") or result.get("id")

        if wait:
            final = self._wait_for_completion(task_id)
            creations = final.get("creations", [])
            if creations:
                return creations[0].get("url", "")
            raise RuntimeError(f"Vidu声音克隆生成为空: {final}")

        return task_id

    # ──────────────────────────────────────────────────────────────────
    # 状态查询
    # ──────────────────────────────────────────────────────────────────

    def get_status(self, task_id: str) -> dict:
        """查询任务状态"""
        return self._get_task_status(task_id)
