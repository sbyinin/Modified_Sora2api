"""Load balancing module"""
import asyncio
import random
from datetime import datetime
from typing import List, Optional

from ..core.config import config
from ..core.logger import debug_logger
from ..core.models import Token
from .concurrency_manager import ConcurrencyManager
from .token_lock import TokenLock
from .token_manager import TokenManager


class LoadBalancer:
    """Token load balancer with call-logic-aware selection and image generation lock

    高并发优化：
    - 自动刷新检查移到后台任务，不阻塞请求
    - 减少不必要的日志输出
    - 使用缓存的 Token 列表
    """

    def __init__(self, token_manager: TokenManager, concurrency_manager: Optional[ConcurrencyManager] = None):
        self.token_manager = token_manager
        self.concurrency_manager = concurrency_manager
        self.proxy_manager = token_manager.proxy_manager
        # Use image timeout from config as lock timeout
        self.token_lock = TokenLock(lock_timeout=config.image_timeout)
        # 后台刷新任务
        self._refresh_task: Optional[asyncio.Task] = None
        self._last_refresh_check: Optional[datetime] = None
        self._refresh_check_interval = 300  # 5 分钟检查一次
        self._rr_lock = asyncio.Lock()
        self._rr_indices = {
            "image": 0,
            "video": 0,
            "default": 0,
        }

    async def _select_round_robin(self, tokens: List[Token], key: str) -> Optional[Token]:
        if not tokens:
            return None
        ordered = sorted(tokens, key=lambda t: t.id)
        async with self._rr_lock:
            index = self._rr_indices.get(key, 0)
            if index >= len(ordered):
                index = 0
            token = ordered[index]
            self._rr_indices[key] = (index + 1) % len(ordered)
        return token

    async def _select_by_call_logic(self, tokens: List[Token], key: str) -> Optional[Token]:
        if not tokens:
            return None
        if config.call_logic_mode == "polling":
            return await self._select_round_robin(tokens, key)
        return random.choice(tokens)

    async def _background_refresh_check(self):
        """后台检查并刷新即将过期的 Token"""
        if not config.at_auto_refresh_enabled:
            return

        now = datetime.now()
        # 限制检查频率
        if self._last_refresh_check and (now - self._last_refresh_check).total_seconds() < self._refresh_check_interval:
            return

        self._last_refresh_check = now

        try:
            all_tokens = await self.token_manager.get_all_tokens()
            for token in all_tokens:
                if token.is_active and token.expiry_time:
                    time_until_expiry = token.expiry_time - now
                    hours_until_expiry = time_until_expiry.total_seconds() / 3600
                    if hours_until_expiry <= 24:
                        # 异步刷新，不等待结果
                        asyncio.create_task(self.token_manager.auto_refresh_expiring_token(token.id))
        except Exception as e:
            debug_logger.log_info(f"[LOAD_BALANCER] 后台刷新检查失败: {e}")

    async def select_token(
        self,
        for_image_generation: bool = False,
        for_video_generation: bool = False,
        excluded_token_ids: Optional[set] = None,
        require_pro: bool = False,
    ) -> Optional[Token]:
        """
        Select a token using call-logic-aware load balancing.

        Args:
            for_image_generation: If True, only select tokens that are not locked for image generation and have image_enabled=True
            for_video_generation: If True, filter out tokens with Sora2 quota exhausted (sora2_cooldown_until not expired), tokens that don't support Sora2, and tokens with video_enabled=False
            excluded_token_ids: Set of token IDs to exclude from selection (e.g., dead tokens)
            require_pro: If True, only select tokens with ChatGPT Pro subscription (plan_type="chatgpt_pro")

        Returns:
            Selected token or None if no available tokens
        """
        # 后台触发刷新检查（非阻塞）
        if config.at_auto_refresh_enabled:
            if not self._refresh_task or self._refresh_task.done():
                self._refresh_task = asyncio.create_task(self._background_refresh_check())

        excluded_token_ids = excluded_token_ids or set()
        active_tokens = await self.token_manager.get_active_tokens()

        # Filter out excluded tokens
        if excluded_token_ids:
            active_tokens = [t for t in active_tokens if t.id not in excluded_token_ids]

        # Filter for Pro tokens if required
        if require_pro:
            active_tokens = [t for t in active_tokens if t.plan_type == "chatgpt_pro"]

        if not active_tokens:
            return None

        # If for video generation, filter out tokens with Sora2 quota exhausted and tokens without Sora2 support
        if for_video_generation:
            now = datetime.now()
            available_tokens = []

            for token in active_tokens:
                # Skip tokens that don't have video enabled
                if not token.video_enabled:
                    continue

                # Skip tokens that don't support Sora2
                if not token.sora2_supported:
                    continue

                # Check if Sora2 cooldown has expired - 异步刷新，不阻塞
                if token.sora2_cooldown_until and token.sora2_cooldown_until <= now:
                    asyncio.create_task(
                        self.token_manager.refresh_sora2_remaining_if_cooldown_expired(token.id)
                    )
                    # 暂时跳过这个 token，下次请求时会使用刷新后的数据
                    continue

                # Skip tokens that are in Sora2 cooldown (quota exhausted)
                if token.sora2_cooldown_until and token.sora2_cooldown_until > now:
                    continue

                available_tokens.append(token)

            if not available_tokens:
                return None

            active_tokens = available_tokens

        # If for image generation, filter out locked tokens and tokens without image enabled
        if for_image_generation:
            available_tokens = []
            for token in active_tokens:
                # Skip tokens that don't have image enabled
                if not token.image_enabled:
                    continue

                if not await self.token_lock.is_locked(token.id):
                    # Check concurrency limit if concurrency manager is available
                    if self.concurrency_manager and not await self.concurrency_manager.can_use_image(token.id):
                        continue
                    available_tokens.append(token)

            if not available_tokens:
                return None

            return await self._select_by_call_logic(available_tokens, "image")

        # For video generation, check concurrency limit
        if for_video_generation and self.concurrency_manager:
            available_tokens = []
            for token in active_tokens:
                if await self.concurrency_manager.can_use_video(token.id):
                    available_tokens.append(token)
            if not available_tokens:
                return None
            return await self._select_by_call_logic(available_tokens, "video")

        # For video generation without concurrency manager, no additional filtering
        key = "video" if for_video_generation else "default"
        return await self._select_by_call_logic(active_tokens, key)
