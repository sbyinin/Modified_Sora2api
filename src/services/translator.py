"""Translation service using OpenAI-compatible API"""
import re
import httpx
from typing import Optional
from ..core.config import config
from ..core.logger import debug_logger


class Translator:
    """Translate Chinese prompts to English using OpenAI-compatible API"""

    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=config.translation_timeout)
        return self._client

    def _contains_chinese(self, text: str) -> bool:
        """Check if text contains Chinese characters"""
        # Match CJK Unified Ideographs
        return bool(re.search(r'[\u4e00-\u9fff]', text))

    async def translate_to_english(self, text: str) -> str:
        """Translate Chinese text to English
        
        Args:
            text: Text to translate (may contain Chinese)
            
        Returns:
            Translated English text, or original text if no Chinese detected
        """
        if not config.translation_enabled:
            return text

        if not self._contains_chinese(text):
            return text

        if not config.translation_api_url or not config.translation_api_key:
            debug_logger.log_info("Translation API not configured, skipping translation")
            return text

        try:
            client = await self._get_client()
            
            response = await client.post(
                config.translation_api_url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {config.translation_api_key}"
                },
                json={
                    "model": config.translation_model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a translator. Translate the user's Chinese text to English. Only output the translation, no explanations. Keep the same style and meaning. If there's mixed Chinese and English, translate only the Chinese parts."
                        },
                        {
                            "role": "user",
                            "content": text
                        }
                    ],
                    "temperature": 0.3,
                    "max_tokens": 1000
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                translated = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                if translated:
                    debug_logger.log_info(f"Translated prompt: '{text}' -> '{translated}'")
                    return translated.strip()
            else:
                debug_logger.log_info(f"Translation API error: {response.status_code} - {response.text}")

        except Exception as e:
            debug_logger.log_info(f"Translation failed: {e}")

        return text

    async def close(self):
        """Close HTTP client"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# Global translator instance
translator = Translator()
