"""
最轻量 Playwright 方案 - 复用浏览器 + 路由拦截
只加载 SDK，不加载任何其他资源
"""
import asyncio
import json
import re
import sys
from curl_cffi.requests import AsyncSession
from playwright.async_api import async_playwright

# 全局浏览器实例（复用）
_browser = None
_playwright = None
_current_proxy = None


async def get_browser(proxy_url: str = None):
    """获取或创建浏览器实例"""
    global _browser, _playwright, _current_proxy
    
    # 如果代理变化，需要重启浏览器
    if _browser is not None and _current_proxy != proxy_url:
        await _browser.close()
        _browser = None
    
    if _browser is None:
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
    """关闭浏览器"""
    global _browser, _playwright
    if _browser:
        await _browser.close()
        _browser = None
    if _playwright:
        await _playwright.stop()
        _playwright = None


async def fetch_oai_did(proxy_url: str = None, max_retries: int = 3) -> str:
    """使用 curl_cffi 获取 oai-did"""
    print(f"[1] 获取 oai-did...")
    
    for attempt in range(max_retries):
        try:
            async with AsyncSession(impersonate="chrome120") as session:
                response = await session.get(
                    "https://chatgpt.com/",
                    proxy=proxy_url,
                    timeout=30,
                    allow_redirects=True
                )
                
                oai_did = response.cookies.get("oai-did")
                if oai_did:
                    print(f"    ✅ oai-did: {oai_did}")
                    return oai_did
                
                set_cookie = response.headers.get("set-cookie", "")
                match = re.search(r'oai-did=([a-f0-9-]{36})', set_cookie)
                if match:
                    oai_did = match.group(1)
                    print(f"    ✅ oai-did: {oai_did}")
                    return oai_did
                    
        except Exception as e:
            print(f"    ❌ 失败: {e}")
        
        if attempt < max_retries - 1:
            await asyncio.sleep(2)
    
    return None


async def generate_sentinel_token(proxy_url: str = None, device_id: str = None) -> str:
    """使用最轻量 Playwright 生成 token"""
    
    # 获取 oai-did
    if not device_id:
        device_id = await fetch_oai_did(proxy_url)
    
    if not device_id:
        print("[!] 无法获取 oai-did")
        return None
    
    print(f"[2] 启动浏览器...")
    browser = await get_browser(proxy_url)
    
    context = await browser.new_context(
        viewport={'width': 800, 'height': 600},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        bypass_csp=True  # 绕过 CSP
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
            # 允许所有 sentinel 相关请求（包括 chatgpt.com 的 SDK）
            await route.continue_()
        else:
            await route.abort()
    
    await page.route("**/*", handle_route)
    
    print(f"[3] 加载 SDK...")
    
    try:
        # hack 方式加载（必须在 sora.chatgpt.com 域名下）
        await page.goto("https://sora.chatgpt.com/__sentinel__", wait_until="load", timeout=30000)
        
        # 等待 SDK 加载
        await page.wait_for_function("typeof SentinelSDK !== 'undefined' && typeof SentinelSDK.token === 'function'", timeout=15000)
        
        print(f"[4] 获取 token...")
        
        # 调用 SDK
        token = await page.evaluate(f'''
            async () => {{
                try {{
                    return await SentinelSDK.token('sora_2_create_task', '{device_id}');
                }} catch (e) {{
                    return 'ERROR: ' + e.message;
                }}
            }}
        ''')
        
        if token and not token.startswith('ERROR'):
            print(f"    ✅ 成功")
            return token
        else:
            print(f"    ❌ {token}")
            return None
            
    except Exception as e:
        print(f"    ❌ {e}")
        return None
    finally:
        await context.close()


async def main():
    proxy_url = sys.argv[1] if len(sys.argv) > 1 else None
    device_id = sys.argv[2] if len(sys.argv) > 2 else None
    
    print("=" * 60)
    print("最轻量 Playwright 方案")
    print("=" * 60)
    print("用法: python get_sentinel_token.py [proxy_url] [oai-did]")
    if proxy_url:
        print(f"Proxy: {proxy_url}")
    if device_id:
        print(f"oai-did: {device_id}")
    print()
    
    try:
        token = await generate_sentinel_token(proxy_url, device_id)
        
        if token:
            print("\n" + "=" * 60)
            print("openai-sentinel-token")
            print("=" * 60)
            print(token)
            
            # 解析显示字段长度
            try:
                data = json.loads(token)
                print(f"\n字段长度:")
                print(f"  p: {len(str(data.get('p', '')))} chars")
                print(f"  t: {len(str(data.get('t', '')))} chars")
                print(f"  c: {len(str(data.get('c', '')))} chars")
            except:
                pass
        else:
            print("\n获取失败!")
    finally:
        await close_browser()


if __name__ == "__main__":
    asyncio.run(main())
