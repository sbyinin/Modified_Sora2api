"""POW Generator - Playwright-based Sentinel Token Generation

Uses Playwright with route interception and SDK injection.
Reuses browser instance for efficiency.
"""
import asyncio
import re
from typing import Optional

try:
    from playwright.async_api import async_playwright, Playwright, Browser
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

try:
    from curl_cffi.requests import AsyncSession
    CURL_CFFI_AVAILABLE = True
except ImportError:
    CURL_CFFI_AVAILABLE = False


# Simple logger fallback
class _SimpleLogger:
    def debug(self, msg): print(f"[DEBUG] {msg}")
    def info(self, msg): print(f"[INFO] {msg}")
    def warning(self, msg): print(f"[WARN] {msg}")
    def error(self, msg): print(f"[ERROR] {msg}")

def _get_logger():
    try:
        from .logger import get_logger
        return get_logger()
    except ImportError:
        return _SimpleLogger()


# Global state
_cached_sentinel_token: Optional[str] = None
_cached_device_id: Optional[str] = None
_cached_user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

# Browser instance (reused)
_playwright: Optional[Playwright] = None
_browser: Optional[Browser] = None
_current_proxy: Optional[str] = None


def set_user_agent(ua: str):
    """Set the user agent to use for requests"""
    global _cached_user_agent
    _cached_user_agent = ua


async def _get_browser(proxy_url: str = None) -> Browser:
    """Get or create browser instance"""
    global _playwright, _browser, _current_proxy
    
    # If proxy changed, close existing browser
    if _browser and _current_proxy != proxy_url:
        await _browser.close()
        _browser = None
    
    if not _browser:
        if not _playwright:
            _playwright = await async_playwright().start()
        
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
        
        _browser = await _playwright.chromium.launch(**launch_args)
        _current_proxy = proxy_url
    
    return _browser


async def close_browser():
    """Close browser instance"""
    global _browser, _playwright
    if _browser:
        await _browser.close()
        _browser = None
    if _playwright:
        await _playwright.stop()
        _playwright = None


async def _fetch_oai_did(proxy_url: str = None, max_retries: int = 3) -> Optional[str]:
    """Fetch oai-did using curl_cffi"""
    logger = _get_logger()
    
    if not CURL_CFFI_AVAILABLE:
        logger.error("curl_cffi not available")
        return None
    
    logger.info("Fetching oai-did...")
    
    for attempt in range(max_retries):
        try:
            async with AsyncSession(impersonate="chrome120") as session:
                response = await session.get(
                    "https://chatgpt.com/",
                    proxy=proxy_url,
                    timeout=30,
                    allow_redirects=True
                )
                
                if response.status_code == 403:
                    raise Exception("403 Forbidden")
                if response.status_code == 429:
                    raise Exception("429 Too Many Requests")
                
                oai_did = response.cookies.get("oai-did")
                if oai_did:
                    logger.info(f"oai-did: {oai_did}")
                    return oai_did
                
                set_cookie = response.headers.get("set-cookie", "")
                match = re.search(r'oai-did=([a-f0-9-]{36})', set_cookie)
                if match:
                    oai_did = match.group(1)
                    logger.info(f"oai-did: {oai_did}")
                    return oai_did
                    
        except Exception as e:
            error_str = str(e)
            if "403" in error_str or "429" in error_str:
                raise
            logger.debug(f"oai-did fetch failed: {e}")
        
        if attempt < max_retries - 1:
            await asyncio.sleep(2)
    
    return None


async def _generate_sentinel_token_browser(
    proxy_url: str = None,
    device_id: str = None,
    flow: str = "sora_2_create_task"
) -> Optional[str]:
    """Generate sentinel token using Playwright
    
    Uses route interception and SDK injection.
    Reuses browser instance across calls.
    """
    global _cached_device_id
    logger = _get_logger()
    
    if not PLAYWRIGHT_AVAILABLE:
        logger.error("Playwright not available")
        return None
    
    # Get oai-did
    if not device_id:
        device_id = await _fetch_oai_did(proxy_url)
    
    if not device_id:
        logger.error("Failed to get oai-did")
        return None
    
    _cached_device_id = device_id
    
    logger.info("Starting browser...")
    browser = await _get_browser(proxy_url)
    
    context = await browser.new_context(
        viewport={'width': 800, 'height': 600},
        user_agent=_cached_user_agent,
        bypass_csp=True
    )
    
    # Set cookie
    await context.add_cookies([{
        'name': 'oai-did',
        'value': device_id,
        'domain': 'api.sorai2.fun',
        'path': '/'
    }])
    
    page = await context.new_page()
    
    # Route interception - inject SDK
    inject_html = '<!DOCTYPE html><html><head><script src="https://api.sorai2.fun/backend-api/sentinel/sdk.js"></script></head><body></body></html>'
    
    async def handle_route(route):
        url = route.request.url
        if "__sentinel__" in url:
            await route.fulfill(status=200, content_type="text/html", body=inject_html)
        elif "/sentinel/" in url or "sorai2.fun" in url:
            await route.continue_()
        else:
            await route.abort()
    
    await page.route("**/*", handle_route)
    
    logger.info("Loading SDK...")
    
    try:
        # Load SDK via hack page
        await page.goto("https://pow.local/__sentinel__", wait_until="load", timeout=30000)
        
        # Wait for SDK to load
        await page.wait_for_function(
            "typeof SentinelSDK !== 'undefined' && typeof SentinelSDK.token === 'function'",
            timeout=15000
        )
        
        logger.info("Getting token...")
        
        # Call SDK
        token = await page.evaluate(f'''
            async () => {{
                try {{
                    return await SentinelSDK.token('{flow}', '{device_id}');
                }} catch (e) {{
                    return 'ERROR: ' + e.message;
                }}
            }}
        ''')
        
        if token and not str(token).startswith('ERROR'):
            logger.info(f"Token obtained (len={len(token)})")
            return token
        else:
            logger.error(f"Token error: {token}")
            return None
            
    except Exception as e:
        logger.error(f"Error: {e}")
        return None
    finally:
        await context.close()


async def generate_sentinel_token(
    proxy_url: str = None,
    force_refresh: bool = False,
    oai_did: str = None,
    flow: str = "sora_2_create_task",
    headless: bool = True,  # Ignored - always headless
    browser_manager=None,   # Ignored
    **kwargs
) -> Optional[str]:
    """Generate sentinel token using Playwright
    
    Args:
        proxy_url: Optional proxy URL
        force_refresh: Force refresh token
        oai_did: Pre-provided oai-did (optional)
        flow: Flow name (default: sora_2_create_task)
        headless: Ignored (always headless)
        browser_manager: Ignored
        **kwargs: Ignored
        
    Returns:
        Sentinel token string
    """
    global _cached_sentinel_token

    if _cached_sentinel_token and not force_refresh:
        print("[POW] Using cached token")
        return _cached_sentinel_token

    print("[POW] Generating new token (Playwright)...")
    
    token = await _generate_sentinel_token_browser(proxy_url, oai_did, flow)

    if token:
        _cached_sentinel_token = token
        print("[POW] Token generated successfully")

    return token


def invalidate_cache():
    """Invalidate cached sentinel token"""
    global _cached_sentinel_token
    _cached_sentinel_token = None
    print("[POW] Cache invalidated")


def get_cached_token() -> Optional[str]:
    """Get currently cached token without generating new one"""
    return _cached_sentinel_token


def get_cached_device_id() -> Optional[str]:
    """Get cached device id (oai-did)"""
    return _cached_device_id


def get_cached_user_agent() -> Optional[str]:
    """Get cached user agent"""
    return _cached_user_agent
