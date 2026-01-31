"""Translation service using OpenAI-compatible API"""
import re
import httpx
from typing import Optional
from ..core.config import config
from ..core.logger import debug_logger

# System prompt for translation with language intent preservation
TRANSLATION_SYSTEM_PROMPT = """You are a translator for AI video generation prompts. Your task is to translate non-English prompts to English while preserving the user's language intent.

Rules:
1. First, detect the primary language of the user's prompt (e.g., Chinese, Japanese, Korean, French, Spanish, etc.).
2. Translate the prompt to English accurately, keeping the same style and meaning.
3. Since the user wrote their prompt in a specific language, they likely want content in that language in the generated video. Analyze the prompt and:
   - If the prompt involves speech, dialogue, text, subtitles, signs, news, teaching, singing, or any language-sensitive content, add the appropriate language directive (e.g., "in Chinese", "in Japanese", "speaking Korean", "with French text") to preserve the user's language intent.
   - If the prompt is purely visual with no language-sensitive elements (e.g., "a cat sleeping", "sunset over mountains"), do NOT add any language directive.
   - If the user explicitly specifies a different language in their prompt, respect their choice.
4. Only output the translated prompt, no explanations.

Examples:
- "一个女孩在说话" (Chinese) → "A girl talking in Chinese"
- "街道上的广告牌" (Chinese) → "Billboards on the street with Chinese text"
- "女の子が歌っている" (Japanese) → "A girl singing in Japanese"
- "東京の看板" (Japanese) → "Signs in Tokyo with Japanese text"
- "소녀가 말하고 있다" (Korean) → "A girl talking in Korean"
- "Une fille parle" (French) → "A girl talking in French"
- "一只猫在睡觉" (Chinese) → "A cat sleeping"
- "美しい夕日" (Japanese) → "A beautiful sunset"
- "一个人在说英语" (Chinese) -> A person speaking English"""


class Translator:
    """Translate Chinese prompts to English using OpenAI-compatible API"""

    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=config.translation_timeout)
        return self._client

    def _needs_translation(self, text: str) -> bool:
        """Check if text contains non-English characters that need translation"""
        # Match various non-English scripts:
        # - CJK Unified Ideographs (Chinese, Japanese Kanji)
        # - Hiragana and Katakana (Japanese)
        # - Hangul (Korean)
        # - Cyrillic (Russian, etc.)
        # - Arabic
        # - Thai
        # - Devanagari (Hindi, etc.)
        # - Hebrew
        return bool(re.search(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af\u0400-\u04ff\u0600-\u06ff\u0e00-\u0e7f\u0900-\u097f\u0590-\u05ff]', text))

    async def translate_to_english(self, text: str) -> str:
        """Translate Chinese text to English, preserving language intent
        
        Args:
            text: Text to translate (may contain Chinese)
            
        Returns:
            Translated English text with appropriate language directives
        """
        if not config.translation_enabled:
            return text

        if not self._needs_translation(text):
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
                            "content": TRANSLATION_SYSTEM_PROMPT
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
                    translated = translated.strip()
                    debug_logger.log_info(f"Translated prompt: '{text}' -> '{translated}'")
                    return translated
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
