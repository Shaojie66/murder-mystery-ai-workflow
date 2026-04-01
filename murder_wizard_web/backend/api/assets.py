"""Vidu AI 图像/视频生成 API."""
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/assets", tags=["assets"])


def get_vidu_adapter():
    """Get ViduAdapter instance."""
    from murder_wizard.assets.vidu import ViduAdapter
    api_key = os.environ.get("VIDU_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="VIDU_API_KEY not configured")
    return ViduAdapter(api_key)


class ImageGenerateRequest(BaseModel):
    prompt: str
    resolution: str = "2K"
    model: str = "q3-fast"
    aspect_ratio: str = "16:9"
    wait: bool = True


class VideoGenerateRequest(BaseModel):
    prompt: str
    duration: int = 5
    resolution: str = "720p"
    aspect_ratio: str = "16:9"
    model: str = "viduq3-pro"
    wait: bool = True


class Img2VideoRequest(BaseModel):
    image_url: str
    prompt: str
    duration: int = 5
    resolution: str = "720p"
    model: str = "viduq3-pro-fast"
    wait: bool = True


@router.post("/image/generate")
async def generate_image(req: ImageGenerateRequest):
    """Generate image from text prompt using Vidu."""
    try:
        adapter = get_vidu_adapter()
        url = adapter.nano_image(
            prompt=req.prompt,
            resolution=req.resolution,
            model=req.model,
            aspect_ratio=req.aspect_ratio,
            wait=req.wait,
        )
        return {"url": url, "status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/video/text2video")
async def generate_text2video(req: VideoGenerateRequest):
    """Generate video from text using Vidu."""
    try:
        adapter = get_vidu_adapter()
        url = adapter.text2video(
            prompt=req.prompt,
            duration=req.duration,
            resolution=req.resolution,
            aspect_ratio=req.aspect_ratio,
            model=req.model,
            wait=req.wait,
        )
        return {"url": url, "status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/video/img2video")
async def generate_img2video(req: Img2VideoRequest):
    """Generate video from image using Vidu."""
    try:
        adapter = get_vidu_adapter()
        url = adapter.img2video(
            image_url=req.image_url,
            prompt=req.prompt,
            duration=req.duration,
            resolution=req.resolution,
            model=req.model,
            wait=req.wait,
        )
        return {"url": url, "status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/task/{task_id}")
async def get_task_status(task_id: str):
    """Get Vidu task status."""
    try:
        adapter = get_vidu_adapter()
        status = adapter.get_status(task_id)
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
