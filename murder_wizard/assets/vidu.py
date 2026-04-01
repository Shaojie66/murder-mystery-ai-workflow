"""Vidu AI 视频/图像生成适配器.

API文档: https://platform.vidu.cn
支持: text2video, img2video, ref2video, nano-image, tts, voice-clone

环境变量:
    VIDU_API_KEY: Vidu API密钥（从 https://platform.vidu.cn 获取）
"""
import os
import time
import urllib.request
import urllib.error
import json
import ssl
from typing import Optional


class ViduAdapter:
    """Vidu AI 视频/图像生成"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("VIDU_API_KEY")
        # api.vidu.cn for Chinese users, api.vidu.com for others
        self.base_url = "https://api.vidu.cn/ent/v2"
        # SSL context that doesn't verify certificates (for macOS compatibility)
        self._ssl_ctx = ssl.create_default_context()
        self._ssl_ctx.check_hostname = False
        self._ssl_ctx.verify_mode = ssl.CERT_NONE

    def _get_headers(self) -> dict:
        if not self.api_key:
            raise RuntimeError("VIDU_API_KEY not configured")
        return {
            "Content-Type": "application/json",
            "Authorization": f"Token {self.api_key}"
        }

    def _post(self, endpoint: str, data: dict, timeout: int = 60) -> dict:
        """POST请求到Vidu API"""
        if not self.api_key:
            raise RuntimeError("VIDU_API_KEY not configured")

        url = f"{self.base_url}{endpoint}"
        req_data = json.dumps(data).encode('utf-8')
        req = urllib.request.Request(
            url, data=req_data, headers=self._get_headers(), method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout, context=self._ssl_ctx) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            raise RuntimeError(f"Vidu API HTTP {e.code}: {error_body}")
        except Exception as e:
            raise RuntimeError(f"Vidu API request failed: {e}")

    def _get(self, endpoint: str, timeout: int = 30) -> dict:
        """GET请求到Vidu API"""
        if not self.api_key:
            raise RuntimeError("VIDU_API_KEY not configured")

        url = f"{self.base_url}{endpoint}"
        req = urllib.request.Request(
            url, headers=self._get_headers(), method="GET"
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout, context=self._ssl_ctx) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            raise RuntimeError(f"Vidu API HTTP {e.code}: {error_body}")
        except Exception as e:
            raise RuntimeError(f"Vidu API request failed: {e}")

    def _wait_for_completion(self, task_id: str, timeout: int = 300) -> dict:
        """等待任务完成"""
        start = time.time()
        while time.time() - start < timeout:
            result = self._get_task_status(task_id)
            state = result.get("state", "")
            if state == "success":
                return result
            elif state == "failed":
                raise RuntimeError(f"Vidu任务失败: {result.get('error', 'unknown')}")
            time.sleep(5)
        raise TimeoutError(f"Vidu任务超时: {task_id}")

    def _get_task_status(self, task_id: str) -> dict:
        """查询任务状态 - 遍历任务列表找到对应ID"""
        result = self._get("/tasks")
        tasks = result.get('tasks', [])
        for task in tasks:
            if task.get('id') == task_id or task.get('task_id') == task_id:
                return task

        # 如果有分页，继续查找
        next_token = result.get('next_page_token')
        while next_token:
            page_result = self._get(f"/tasks?page_token={next_token}")
            for task in page_result.get('tasks', []):
                if task.get('id') == task_id or task.get('task_id') == task_id:
                    return task
            next_token = page_result.get('next_page_token')

        return {"task_id": task_id, "state": "not_found"}

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
        result = self._post("/text2video", data)
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
        resolution: str = "720p",
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
            "resolution": resolution,
            "image_url": image_url,
            "prompt": prompt,
        }
        result = self._post("/img2video", data)
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
        resolution: str = "720p",
        model: str = "viduq3",
        wait: bool = True,
    ) -> str:
        """
        参考图生视频（多主体）

        Args:
            image_urls: 参考图片URL列表（最多5张）
            prompt: 视频描述
            duration: 视频时长（秒）
            model: 模型，默认viduq3
            wait: 是否等待生成完成

        Returns:
            视频URL或任务ID
        """
        data = {
            "model": model,
            "duration": duration,
            "resolution": resolution,
            "images": image_urls[:5],
            "prompt": prompt,
        }
        result = self._post("/reference2video", data)
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
        wait: bool = True,
    ) -> str:
        """
        文生图像（nano模式）

        Args:
            prompt: 图像描述
            resolution: 分辨率，默认2K
            model: 模型，默认q3-fast
            aspect_ratio: 宽高比，默认16:9
            wait: 是否等待生成完成

        Returns:
            图片URL或任务ID（wait=False时）
        """
        data = {
            "model": model,
            "resolution": resolution,
            "aspect_ratio": aspect_ratio,
            "prompt": prompt,
        }
        result = self._post("/reference2image/nano", data)
        task_id = result.get("task_id") or result.get("id")
        if not task_id:
            creations = result.get("creations", [])
            if creations:
                return creations[0].get("url", "")
            raise RuntimeError(f"Vidu图像生成为空: {result}")

        if wait:
            final = self._wait_for_completion(task_id)
            creations = final.get("creations", [])
            if creations:
                return creations[0].get("url", "")
            raise RuntimeError(f"Vidu图像生成为空: {final}")

        return task_id

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
            "voice_setting_voice_id": voice_id,
        }
        result = self._post("/audio-tts", data)
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
        result = self._post("/audio-clone", data)
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
