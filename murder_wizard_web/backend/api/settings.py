"""Settings API endpoints for user configuration."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import json

router = APIRouter(prefix="/api/settings", tags=["settings"])

SETTINGS_PATH = Path.home() / ".murder-wizard" / "settings.json"


class LLMConfig(BaseModel):
    provider: str = "minimax"  # minimax, openai, claude, ollama
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None


class NotionConfig(BaseModel):
    enabled: bool = False
    api_key: Optional[str] = None
    database_id: Optional[str] = None


class ObsidianConfig(BaseModel):
    enabled: bool = False
    vault_path: Optional[str] = None


class Settings(BaseModel):
    llm: LLMConfig = LLMConfig()
    notion: NotionConfig = NotionConfig()
    obsidian: ObsidianConfig = ObsidianConfig()


def _load_settings() -> Settings:
    """Load settings from file."""
    if not SETTINGS_PATH.exists():
        return Settings()

    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        return Settings(**data)
    except Exception:
        return Settings()


def _save_settings(settings: Settings) -> None:
    """Save settings to file."""
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(
        json.dumps(settings.model_dump(), indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


@router.get("", response_model=Settings)
async def get_settings():
    """Get current settings (API keys are masked)."""
    settings = _load_settings()

    # Mask API keys in response
    if settings.llm.api_key:
        settings.llm.api_key = _mask_key(settings.llm.api_key)
    if settings.notion.api_key:
        settings.notion.api_key = _mask_key(settings.notion.api_key)

    return settings


@router.put("", response_model=Settings)
async def update_settings(settings: Settings):
    """Update settings."""
    _save_settings(settings)
    return settings


@router.post("/test-llm")
async def test_llm_connection(settings: Settings):
    """Test LLM connection with provided settings."""
    from murder_wizard.llm.client import create_llm_adapter

    try:
        # Create adapter with provided settings
        if settings.llm.provider == "minimax":
            from murder_wizard.llm.client import MiniMaxAdapter
            adapter = MiniMaxAdapter(api_key=settings.llm.api_key)
        elif settings.llm.provider == "openai":
            from murder_wizard.llm.client import OpenAIAdapter
            adapter = OpenAIAdapter(api_key=settings.llm.api_key)
        elif settings.llm.provider == "claude":
            from murder_wizard.llm.client import ClaudeAdapter
            adapter = ClaudeAdapter(api_key=settings.llm.api_key)
        elif settings.llm.provider == "ollama":
            from murder_wizard.llm.client import OllamaAdapter
            adapter = OllamaAdapter(
                base_url=settings.llm.base_url or "http://localhost:11434/v1",
                model=settings.llm.model or "llama3"
            )
        else:
            raise ValueError(f"Unknown provider: {settings.llm.provider}")

        # Test with a simple prompt
        response = adapter.complete("Say 'hello' in Chinese", system="You are a helpful assistant.")
        return {
            "success": True,
            "model": adapter.model,
            "tokens": response.tokens_used,
            "response_preview": response.content[:100]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Connection failed: {str(e)}")


@router.post("/test-notion")
async def test_notion_connection(notion: NotionConfig):
    """Test Notion connection."""
    if not notion.api_key:
        raise HTTPException(status_code=400, detail="Notion API key is required")

    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.notion.com/v1/users/me",
                headers={
                    "Authorization": f"Bearer {notion.api_key}",
                    "Notion-Version": "2022-06-28"
                }
            )
            if response.status_code == 200:
                return {"success": True, "user": response.json()}
            else:
                raise HTTPException(status_code=400, detail=f"Notion API error: {response.status_code}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Connection failed: {str(e)}")


@router.post("/test-obsidian")
async def test_obsidian_connection(obsidian: ObsidianConfig):
    """Test Obsidian vault connection."""
    if not obsidian.vault_path:
        raise HTTPException(status_code=400, detail="Obsidian vault path is required")

    vault_path = Path(obsidian.vault_path).expanduser()
    if not vault_path.exists():
        raise HTTPException(status_code=400, detail=f"Vault path does not exist: {vault_path}")

    # Check for .obsidian folder
    obsidian_folder = vault_path / ".obsidian"
    if not obsidian_folder.exists():
        raise HTTPException(status_code=400, detail=f"Not an Obsidian vault (missing .obsidian folder)")

    return {"success": True, "vault_path": str(vault_path)}


def _mask_key(key: str) -> str:
    """Mask an API key for display."""
    if len(key) <= 8:
        return "***"
    return key[:4] + "***" + key[-4:]
