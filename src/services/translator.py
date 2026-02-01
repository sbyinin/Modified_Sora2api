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
3. IMPORTANT: Preserve all @username mentions exactly as they are (e.g., @xiaohanhan123). These are character card references and must NOT be translated, removed, or modified. Keep them in their original position in the prompt.
4. Since the user wrote their prompt in a specific language, they likely want content in that language in the generated video. Analyze the prompt and:
   - If the prompt involves speech, dialogue, text, subtitles, signs, news, teaching, singing, or any language-sensitive content, add the appropriate language directive (e.g., "in Chinese", "in Japanese", "speaking Korean", "with French text") to preserve the user's language intent.
   - If the prompt is purely visual with no language-sensitive elements (e.g., "a cat sleeping", "sunset over mountains"), do NOT add any language directive.
   - If the user explicitly specifies a different language in their prompt, respect their choice.
5. Only output the translated prompt, no explanations.

Examples:
- "@xiaohanhan123 猫猫装扮" → "@xiaohanhan123 A cat in a costume"
- "@user123 在说话" → "@user123 talking in Chinese"
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
            # Use longer timeout for translation (default 120s, or config value if larger)
            timeout = max(120, config.translation_timeout)
            self._client = httpx.AsyncClient(timeout=timeout)
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

    def _extract_mentions(self, text: str) -> tuple[list[tuple[int, str]], str]:
        """Extract @username mentions from text with their positions
        
        Args:
            text: Text that may contain @username mentions
            
        Returns:
            Tuple of (list of (position, mention), text with mentions replaced by placeholders)
        """
        # Match @username patterns (alphanumeric and underscores)
        mention_pattern = r'@[\w]+'
        mentions = []
        
        # Find all mentions with their positions
        for i, match in enumerate(re.finditer(mention_pattern, text)):
            mentions.append((i, match.group()))
        
        # Replace mentions with placeholders
        text_with_placeholders = re.sub(mention_pattern, lambda m: f'__MENTION_{len(mentions) - 1}__' if mentions else '', text)
        
        # Actually, let's use a simpler approach - replace each mention with indexed placeholder
        text_with_placeholders = text
        for i, (_, mention) in enumerate(mentions):
            text_with_placeholders = text_with_placeholders.replace(mention, f'__MENTION_{i}__', 1)
        
        return mentions, text_with_placeholders

    def _restore_mentions(self, mentions: list[tuple[int, str]], translated_text: str) -> str:
        """Restore @username mentions in translated text
        
        If placeholders are found, replace them with original mentions.
        If placeholders are missing (LLM removed them), prepend all mentions to the text.
        
        Args:
            mentions: List of (position, mention) tuples
            translated_text: The translated text (may have placeholders or not)
            
        Returns:
            Text with mentions restored
        """
        if not mentions:
            return translated_text
        
        result = translated_text
        missing_mentions = []
        
        # Try to restore each mention from its placeholder
        for i, (_, mention) in enumerate(mentions):
            placeholder = f'__MENTION_{i}__'
            if placeholder in result:
                result = result.replace(placeholder, mention, 1)
            else:
                # Placeholder missing - LLM removed it
                missing_mentions.append(mention)
        
        # If any mentions were lost, prepend them to ensure they're not lost
        if missing_mentions:
            missing_str = ' '.join(missing_mentions)
            result = f"{missing_str} {result}"
        
        return result

    async def translate_to_english(self, text: str) -> str:
        """Translate Chinese text to English, preserving language intent
        
        Args:
            text: Text to translate (may contain Chinese)
            
        Returns:
            Translated English text with appropriate language directives
        """
        print(f"\U0001f310 [Translator] translate_to_english called, enabled={config.translation_enabled}")
        
        if not config.translation_enabled:
            print("\U0001f310 [Translator] Translation disabled, returning original")
            return text

        if not self._needs_translation(text):
            print("\U0001f310 [Translator] No translation needed (no CJK characters)")
            return text

        if not config.translation_api_url or not config.translation_api_key:
            print(f"\U0001f310 [Translator] API not configured: url={config.translation_api_url}, key={'***' if config.translation_api_key else 'None'}")
            debug_logger.log_info("Translation API not configured, skipping translation")
            return text
        
        print(f"\U0001f310 [Translator] Starting translation for: {text[:50]}...")

        # Extract @username mentions before translation to guarantee preservation
        mentions, text_to_translate = self._extract_mentions(text)
        
        # If only mentions, no need to translate
        if not text_to_translate.strip() or not self._needs_translation(text_to_translate):
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
                            "content": text_to_translate
                        }
                    ],
                    "temperature": 0.3,
                    "max_tokens": 16000,
                    "stream": False
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"\u2705 [Translator] API response received")
                
                # Try standard OpenAI format first
                translated = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                # If empty, try alternative response formats
                if not translated:
                    # Some APIs return content directly in choices[0].text
                    translated = result.get("choices", [{}])[0].get("text", "")
                if not translated:
                    # Some APIs return in result.content or result.text
                    translated = result.get("content", "") or result.get("text", "")
                
                if translated:
                    translated = translated.strip()
                    # Restore @username mentions - guaranteed not to lose them
                    translated = self._restore_mentions(mentions, translated)
                    print(f"\u2705 [Translator] SUCCESS: '{text[:30]}...' -> '{translated[:30]}...'")
                    return translated
                else:
                    print(f"\u274c [Translator] Empty content returned. Response structure: {list(result.keys())}")
                    if "choices" in result and result["choices"]:
                        print(f"\u274c [Translator] choices[0] structure: {result['choices'][0]}")
            else:
                print(f"\u274c [Translator] API error: {response.status_code}")

        except Exception as e:
            import traceback
            print(f"\u274c [Translator] Exception: {type(e).__name__}: {e}")
            traceback.print_exc()

        return text

    async def close(self):
        """Close HTTP client"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# Global translator instance
translator = Translator()
