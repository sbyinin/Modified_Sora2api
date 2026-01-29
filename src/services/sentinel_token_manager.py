"""
Sentinel Token Manager - 高并发缓存 + Playwright 方式获取

特性:
1. 高并发处理机制（锁 + 缓存 + double-check）
2. 浏览器实例复用
3. Token 缓存（带 TTL）
4. 通过 Lambda 获取 oai-did
5. 通过本地 Playwright + 代理池获取 sentinel token
"""
import asyncio
import json
import time
from typing import Optional, Dict, Tuple
from dataclasses import dataclass

# Playwright 延迟导入
_playwright_module = None
_async_playwright = None


def _lazy_import_playwright():
    """延迟导入 Playwright"""
    global _playwright_module, _async_playwright
    if _playwright_module is None:
        from playwright.async_api import async_playwright
        _playwright_module = True
        _async_playwright = async_playwright
    return _async_playwright


@dataclass
class CachedToken:
    """缓存的 token 数据"""
    token: str
    device_id: str
    created_at: float
    proxy_url: Optional[str] = None


class SentinelTokenManager:
    """Sentinel Token 管理器"""
    
    # Token 缓存 TTL (秒) - 默认 5 分钟
    TOKEN_TTL = 300
    
    def __init__(self):
        # 浏览器实例（复用）
        self._browser = None
        self._playwright = None
        self._current_proxy: Optional[str] = None
        
        # Token 缓存
        self._cached_token: Optional[CachedToken] = None
        
        # 并发控制锁
        self._lock = asyncio.Lock()
        self._browser_lock = asyncio.Lock()
        
        # Lambda manager (lazy loaded)
        self._lambda_manager = None
        
        # Proxy manager (lazy loaded)
        self._proxy_manager = None
    
    async def _get_lambda_manager(self):
        """获取 Lambda manager"""
        if self._lambda_manager is None:
            from .lambda_manager import lambda_manager
            self._lambda_manager = lambda_manager
        return self._lambda_manager
    
    async def _get_proxy_manager(self):
        """获取 Proxy manager"""
        if self._proxy_manager is None:
            from .proxy_manager import proxy_manager
            self._proxy_manager = proxy_manager
        return self._proxy_manager
    
    async def _get_browser(self, proxy_url: Optional[str] = None):
        """获取或创建浏览器实例（复用）"""
        async with self._browser_lock:
            # 如果代理变化，需要重启浏览器
            if self._browser is not None and self._current_proxy != proxy_url:
                await self._close_browser_internal()
            
            if self._browser is None:
                async_playwright = _lazy_import_playwright()
                self._playwright = await async_playwright().start()
                
                launch_args = {
                    'headless': True,
                    'args': [
                        '--no-sandbox',
                        '--disable-gpu',
                        '--disable-dev-shm-usage',
                        '--disable-extensions',
                        '--disable-plugins',
                        '--disable-images',
                        '--disable-default-apps',
                        '--disable-sync',
                        '--disable-translate',
                        '--disable-background-networking',
                        '--disable-software-rasterizer',
                    ]
                }
                
                if proxy_url:
                    launch_args['proxy'] = {'server': proxy_url}
                
                self._browser = await self._playwright.chromium.launch(**launch_args)
                self._current_proxy = proxy_url
                print(f"🌐 [SentinelManager] Browser started (proxy: {proxy_url or 'none'})")
            
            return self._browser
    
    async def _close_browser_internal(self):
        """内部关闭浏览器（不加锁）"""
        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None
        
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None
        
        self._current_proxy = None
    
    async def close_browser(self):
        """关闭浏览器"""
        async with self._browser_lock:
            await self._close_browser_internal()
            print("🌐 [SentinelManager] Browser closed")
    
    def _is_token_valid(self) -> bool:
        """检查缓存的 token 是否有效"""
        if self._cached_token is None:
            return False
        
        # 检查 TTL
        elapsed = time.time() - self._cached_token.created_at
        return elapsed < self.TOKEN_TTL
    
    def clear_cache(self):
        """清除缓存的 token"""
        self._cached_token = None
        print("🗑️ [SentinelManager] Token cache cleared")
    
    async def _fetch_oai_did_local(self, proxy_url: Optional[str] = None) -> str:
        """本地获取 oai-did（备用方案）"""
        import re
        from curl_cffi.requests import AsyncSession
        
        print("[SentinelManager] Fetching oai-did locally...")
        
        for attempt in range(3):
            try:
                async with AsyncSession(impersonate="chrome120") as session:
                    response = await session.get(
                        "https://chatgpt.com/",
                        proxy=proxy_url,
                        timeout=30,
                        allow_redirects=True
                    )
                    
                    # 从 cookies 获取
                    oai_did = response.cookies.get("oai-did")
                    if oai_did:
                        print(f"✅ [SentinelManager] Got oai-did locally: {oai_did}")
                        return oai_did
                    
                    # 从 set-cookie 头获取
                    set_cookie = response.headers.get("set-cookie", "")
                    match = re.search(r'oai-did=([a-f0-9-]{36})', set_cookie)
                    if match:
                        oai_did = match.group(1)
                        print(f"✅ [SentinelManager] Got oai-did locally: {oai_did}")
                        return oai_did
                    
                    # 检查是否被封
                    if response.status_code in (403, 429):
                        raise Exception(f"IP blocked or rate limited (HTTP {response.status_code})")
                        
            except Exception as e:
                print(f"⚠️ [SentinelManager] Local fetch attempt {attempt + 1} failed: {e}")
                if attempt < 2:
                    await asyncio.sleep(2)
        
        raise Exception("Failed to fetch oai-did locally after 3 attempts")

    async def _fetch_oai_did_via_lambda(self) -> str:
        """通过 Lambda 获取 oai-did"""
        lambda_mgr = await self._get_lambda_manager()
        
        if not await lambda_mgr.is_enabled():
            raise Exception("Lambda is not enabled")
        
        configs = await lambda_mgr._get_config()
        endpoints = lambda_mgr._get_endpoints(configs)
        
        if not endpoints:
            raise Exception("No Lambda endpoints configured")
        
        # 尝试每个 endpoint
        last_error = None
        for endpoint in endpoints:
            try:
                import httpx
                
                headers = {
                    "Content-Type": "application/json",
                    "x-lambda-key": endpoint["key"]
                }
                
                request_data = {"action": "get_oai_did"}
                
                async with httpx.AsyncClient(timeout=30) as client:
                    response = await client.post(
                        endpoint["url"],
                        json=request_data,
                        headers=headers
                    )
                
                if response.status_code in (403, 429):
                    raise Exception(f"Lambda IP blocked or rate limited (HTTP {response.status_code})")
                
                if response.status_code != 200:
                    raise Exception(f"Lambda request failed: HTTP {response.status_code}")
                
                data = response.json()
                
                if "error" in data:
                    raise Exception(data["error"])
                
                oai_did = data.get("oai_did")
                if not oai_did:
                    raise Exception("oai-did not found in response")
                
                print(f"✅ [SentinelManager] Got oai-did via Lambda: {oai_did}")
                return oai_did
                
            except Exception as e:
                last_error = e
                print(f"⚠️ [SentinelManager] Lambda endpoint {endpoint['url']} failed: {e}")
                continue
        
        raise Exception(f"All Lambda endpoints failed: {last_error}")
    
    async def _generate_token_via_browser(
        self,
        device_id: str,
        proxy_url: Optional[str] = None,
        flow: str = "sora_2_create_task"
    ) -> str:
        """通过 Playwright 浏览器生成 sentinel token"""
        browser = await self._get_browser(proxy_url)
        
        context = await browser.new_context(
            viewport={'width': 800, 'height': 600},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            bypass_csp=True
        )
        
        # 设置 cookie
        await context.add_cookies([{
            'name': 'oai-did',
            'value': device_id,
            'domain': 'sora.chatgpt.com',
            'path': '/'
        }])
        
        page = await context.new_page()
        
        # 路由拦截 - hack 注入 SDK
        inject_html = '''<!DOCTYPE html><html><head><script src="https://chatgpt.com/backend-api/sentinel/sdk.js"></script></head><body></body></html>'''
        
        async def handle_route(route):
            url = route.request.url
            if "__sentinel__" in url:
                await route.fulfill(status=200, content_type="text/html", body=inject_html)
            elif "/sentinel/" in url or "chatgpt.com" in url:
                await route.continue_()
            else:
                await route.abort()
        
        await page.route("**/*", handle_route)
        
        try:
            # hack 方式加载
            await page.goto("https://sora.chatgpt.com/__sentinel__", wait_until="load", timeout=30000)
            
            # 等待 SDK 加载
            await page.wait_for_function(
                "typeof SentinelSDK !== 'undefined' && typeof SentinelSDK.token === 'function'",
                timeout=15000
            )
            
            # 调用 SDK
            token = await page.evaluate(f'''
                async () => {{
                    try {{
                        return await SentinelSDK.token('{flow}', '{device_id}');
                    }} catch (e) {{
                        return 'ERROR: ' + e.message;
                    }}
                }}
            ''')
            
            if token and not token.startswith('ERROR'):
                print(f"✅ [SentinelManager] Sentinel token generated successfully")
                return token
            else:
                raise Exception(f"SDK error: {token}")
                
        finally:
            await context.close()
    
    async def get_sentinel_token(
        self,
        force_refresh: bool = False,
        flow: str = "sora_2_create_task",
        token_id: Optional[int] = None
    ) -> str:
        """
        获取 sentinel token（高并发安全）
        
        流程:
        1. 快速路径: 有缓存且不强制刷新时直接返回
        2. 加锁排队: 需要刷新时获取锁
        3. Double-check: 获取锁后再次检查缓存
        4. 刷新: 通过 Lambda 获取 oai-did，再通过 Playwright 获取 token
        
        Args:
            force_refresh: 是否强制刷新（忽略缓存）
            flow: sentinel flow 类型
            token_id: Token ID（用于获取对应的代理）
            
        Returns:
            sentinel token 字符串
            
        Raises:
            Exception: 获取失败时抛出异常
        """
        # 快速路径（无锁）
        if not force_refresh and self._is_token_valid():
            print("⚡ [SentinelManager] Using cached token (fast path)")
            return self._cached_token.token
        
        # 加锁排队
        async with self._lock:
            # Double-check: 获取锁后再次检查缓存
            if not force_refresh and self._is_token_valid():
                print("⚡ [SentinelManager] Using cached token (double-check)")
                return self._cached_token.token
            
            print("🔄 [SentinelManager] Refreshing sentinel token...")
            
            # 1. 从代理池获取代理
            proxy_mgr = await self._get_proxy_manager()
            proxy_url = await proxy_mgr.get_proxy_url(token_id)
            
            # 2. 获取 oai-did（先尝试 Lambda，失败后本地获取）
            try:
                device_id = await self._fetch_oai_did_via_lambda()
            except Exception as lambda_err:
                print(f"⚠️ [SentinelManager] Lambda failed, falling back to local: {lambda_err}")
                device_id = await self._fetch_oai_did_local(proxy_url)
            
            # 3. 通过 Playwright 生成 token
            token = await self._generate_token_via_browser(
                device_id=device_id,
                proxy_url=proxy_url,
                flow=flow
            )
            
            # 4. 更新缓存
            self._cached_token = CachedToken(
                token=token,
                device_id=device_id,
                created_at=time.time(),
                proxy_url=proxy_url
            )
            
            print(f"✅ [SentinelManager] Token refreshed and cached (TTL: {self.TOKEN_TTL}s)")
            return token
    
    async def get_sentinel_token_with_retry(
        self,
        max_retries: int = 2,
        flow: str = "sora_2_create_task",
        token_id: Optional[int] = None
    ) -> str:
        """
        获取 sentinel token（带重试）
        
        第一次使用缓存，失败后强制刷新重试
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                force_refresh = attempt > 0  # 第一次不强制刷新，后续强制刷新
                return await self.get_sentinel_token(
                    force_refresh=force_refresh,
                    flow=flow,
                    token_id=token_id
                )
            except Exception as e:
                last_error = e
                print(f"⚠️ [SentinelManager] Attempt {attempt + 1} failed: {e}")
                
                # 清除缓存以便下次重试
                self.clear_cache()
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
        
        raise Exception(f"Failed to get sentinel token after {max_retries} attempts: {last_error}")


# 全局单例
sentinel_token_manager = SentinelTokenManager()
