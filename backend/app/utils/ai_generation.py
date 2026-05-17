from urllib.parse import urljoin

import httpx

from app.config.setting import settings
from app.core.exceptions import CustomException


class AiGenerationClient:
    """轻量大模型文本生成客户端，复用 OpenAI 兼容配置。"""

    @staticmethod
    async def chat(
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.5,
        max_tokens: int = 600,
        timeout: float | None = None,
    ) -> str:
        if not settings.OPENAI_API_KEY or not settings.OPENAI_MODEL or not settings.OPENAI_BASE_URL:
            raise CustomException(msg="AI大模型配置不完整")
        url = urljoin(settings.OPENAI_BASE_URL.rstrip("/") + "/", "chat/completions")
        async with httpx.AsyncClient(timeout=timeout or max(settings.HTTPX_DEFAULT_TIMEOUT, 30.0)) as client:
            response = await client.post(
                url,
                headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": settings.OPENAI_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
        if response.status_code >= 400:
            raise CustomException(msg=f"AI生成失败: HTTP {response.status_code}", data=response.text[:1000])
        payload = response.json()
        choice = (payload.get("choices") or [{}])[0]
        if choice.get("finish_reason") == "length":
            raise CustomException(msg="AI生成结果被截断，等待重试")
        content = ((choice.get("message") or {}).get("content") or "").strip()
        if not content:
            raise CustomException(msg="AI生成结果为空")
        return content
