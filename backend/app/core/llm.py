import logging
from typing import Any, Dict, List, Optional
from openai import AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Unified LLM Client supporting GLM-4.7 (Zhipu AI BigModel) and OpenAI-compatible endpoints.
    GLM-4.7 uses standard OpenAI-compatible completions API at https://open.bigmodel.cn/api/paas/v4.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        default_model: Optional[str] = None,
    ):
        self.api_key = api_key or settings.GLM_API_KEY or settings.OPENAI_API_KEY
        self.base_url = base_url or settings.GLM_BASE_URL
        self.default_model = default_model or settings.LLM_MODEL
        self._client: Optional[AsyncOpenAI] = None

    def get_client(self) -> Optional[AsyncOpenAI]:
        if not self.api_key:
            return None
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=60.0,
            )
        return self._client

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = 2048,
    ) -> Optional[str]:
        """
        Executes an asynchronous chat completion request using GLM-4.8.
        Returns the message string or None if API key is not configured.
        """
        client = self.get_client()
        if client is None:
            logger.info("GLM_API_KEY not configured. Falling back to local agent heuristics.")
            return None

        target_model = model or self.default_model
        try:
            response = await client.chat.completions.create(
                model=target_model,
                messages=messages,  # type: ignore
                temperature=temperature,
                max_tokens=max_tokens,
            )
            if response.choices and response.choices[0].message.content:
                return response.choices[0].message.content
        except Exception as err:
            logger.warning(f"GLM-4.8 completion failed: {err}. Falling back to deterministic pipeline.")
            return None

        return None


# Global singleton LLM client
llm_client = LLMClient()
