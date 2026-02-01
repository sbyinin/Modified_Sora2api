#!/usr/bin/env python3
"""
Sentinel Token Generator for Sora API

Generates Proof of Work (PoW) and Sentinel tokens required for Sora API authentication.
Based on reverse-engineered browser token generation process.
"""

import hashlib
import json
import random
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

import pybase64

from curl_cffi.requests import AsyncSession, Session

# Sora Browser UA
SORA_BROWSER_USER_AGENT = "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Mobile Safari/537.36"

# ============ Configuration ============

CORES = [8, 16, 24, 32]

CACHED_SCRIPTS = [
    "https://cdn.oaistatic.com/_next/static/cXh69klOLzS0Gy2joLDRS/_ssgManifest.js?dpl=453ebaec0d44c2decab71692e1bfe39be35a24b3"
]

CACHED_DPL = ["prod-f501fe933b3edf57aea882da888e1a544df99840"]

NAVIGATOR_KEY = [
    "registerProtocolHandler-function registerProtocolHandler() { [native code] }",
    "storage-[object StorageManager]",
    "locks-[object LockManager]",
    "appCodeName-Mozilla",
    "permissions-[object Permissions]",
    "share-function share() { [native code] }",
    "webdriver-false",
    "managed-[object NavigatorManagedData]",
    "canShare-function canShare() { [native code] }",
    "vendor-Google Inc.",
    "mediaDevices-[object MediaDevices]",
    "vibrate-function vibrate() { [native code] }",
    "storageBuckets-[object StorageBucketManager]",
    "mediaCapabilities-[object MediaCapabilities]",
    "getGamepads-function getGamepads() { [native code] }",
    "bluetooth-[object Bluetooth]",
    "cookieEnabled-true",
    "virtualKeyboard-[object VirtualKeyboard]",
    "product-Gecko",
    "xr-[object XRSystem]",
    "clipboard-[object Clipboard]",
    "unregisterProtocolHandler-function unregisterProtocolHandler() { [native code] }",
    "productSub-20030107",
    "login-[object NavigatorLogin]",
    "vendorSub-",
    "getInstalledRelatedApps-function getInstalledRelatedApps() { [native code] }",
    "webkitGetUserMedia-function webkitGetUserMedia() { [native code] }",
    "appName-Netscape",
    "presentation-[object Presentation]",
    "onLine-true",
    "mimeTypes-[object MimeTypeArray]",
    "credentials-[object CredentialsContainer]",
    "serviceWorker-[object ServiceWorkerContainer]",
    "keyboard-[object Keyboard]",
    "gpu-[object GPU]",
    "webkitPersistentStorage-[object DeprecatedStorageQuota]",
    "doNotTrack",
    "clearAppBadge-function clearAppBadge() { [native code] }",
    "serial-[object Serial]",
    "requestMIDIAccess-function requestMIDIAccess() { [native code] }",
    "requestMediaKeySystemAccess-function requestMediaKeySystemAccess() { [native code] }",
    "pdfViewerEnabled-true",
    "language-zh-CN",
    "setAppBadge-function setAppBadge() { [native code] }",
    "geolocation-[object Geolocation]",
    "userAgentData-[object NavigatorUAData]",
    "getUserMedia-function getUserMedia() { [native code] }",
    "sendBeacon-function sendBeacon() { [native code] }",
    "hardwareConcurrency-32",
    "windowControlsOverlay-[object WindowControlsOverlay]",
    "scheduling-[object Scheduling]",
]

DOCUMENT_KEY = ['_reactListeningo743lnnpvdg', 'location']

WINDOW_KEY = [
    "0", "window", "self", "document", "name", "location", "customElements",
    "history", "navigation", "locationbar", "menubar", "personalbar",
    "scrollbars", "statusbar", "toolbar", "status", "closed", "frames",
    "length", "top", "opener", "parent", "frameElement", "navigator",
    "origin", "external", "screen", "innerWidth", "innerHeight", "scrollX",
    "pageXOffset", "scrollY", "pageYOffset", "visualViewport", "screenX",
    "screenY", "outerWidth", "outerHeight", "devicePixelRatio",
    "clientInformation", "screenLeft", "screenTop", "styleMedia", "onsearch",
    "isSecureContext", "trustedTypes", "performance", "onappinstalled",
    "onbeforeinstallprompt", "crypto", "indexedDB", "sessionStorage",
    "localStorage", "onbeforexrselect", "onabort", "onbeforeinput",
    "onbeforematch", "onbeforetoggle", "onblur", "oncancel", "oncanplay",
    "oncanplaythrough", "onchange", "onclick", "onclose",
    "oncontentvisibilityautostatechange", "oncontextlost", "oncontextmenu",
    "oncontextrestored", "oncuechange", "ondblclick", "ondrag", "ondragend",
    "ondragenter", "ondragleave", "ondragover", "ondragstart", "ondrop",
    "ondurationchange", "onemptied", "onended", "onerror", "onfocus",
    "onformdata", "oninput", "oninvalid", "onkeydown", "onkeypress", "onkeyup",
    "onload", "onloadeddata", "onloadedmetadata", "onloadstart", "onmousedown",
    "onmouseenter", "onmouseleave", "onmousemove", "onmouseout", "onmouseover",
    "onmouseup", "onmousewheel", "onpause", "onplay", "onplaying", "onprogress",
    "onratechange", "onreset", "onresize", "onscroll", "onsecuritypolicyviolation",
    "onseeked", "onseeking", "onselect", "onslotchange", "onstalled", "onsubmit",
    "onsuspend", "ontimeupdate", "ontoggle", "onvolumechange", "onwaiting",
    "onwebkitanimationend", "onwebkitanimationiteration", "onwebkitanimationstart",
    "onwebkittransitionend", "onwheel", "onauxclick", "ongotpointercapture",
    "onlostpointercapture", "onpointerdown", "onpointermove", "onpointerrawupdate",
    "onpointerup", "onpointercancel", "onpointerover", "onpointerout",
    "onpointerenter", "onpointerleave", "onselectstart", "onselectionchange",
    "onanimationend", "onanimationiteration", "onanimationstart", "ontransitionrun",
    "ontransitionstart", "ontransitionend", "ontransitioncancel", "onafterprint",
    "onbeforeprint", "onbeforeunload", "onhashchange", "onlanguagechange",
    "onmessage", "onmessageerror", "onoffline", "ononline", "onpagehide",
    "onpageshow", "onpopstate", "onrejectionhandled", "onstorage",
    "onunhandledrejection", "onunload", "crossOriginIsolated", "scheduler",
    "alert", "atob", "blur", "btoa", "cancelAnimationFrame", "cancelIdleCallback",
    "captureEvents", "clearInterval", "clearTimeout", "close", "confirm",
    "createImageBitmap", "fetch", "find", "focus", "getComputedStyle",
    "getSelection", "matchMedia", "moveBy", "moveTo", "open", "postMessage",
    "print", "prompt", "queueMicrotask", "releaseEvents", "reportError",
    "requestAnimationFrame", "requestIdleCallback", "resizeBy", "resizeTo",
    "scroll", "scrollBy", "scrollTo", "setInterval", "setTimeout", "stop",
    "structuredClone", "webkitCancelAnimationFrame", "webkitRequestAnimationFrame",
    "chrome", "caches", "cookieStore", "ondevicemotion", "ondeviceorientation",
    "ondeviceorientationabsolute", "launchQueue", "documentPictureInPicture",
    "getScreenDetails", "queryLocalFonts", "showDirectoryPicker",
    "showOpenFilePicker", "showSaveFilePicker", "originAgentCluster",
    "onpageswap", "onpagereveal", "credentialless", "speechSynthesis",
    "onscrollend", "webkitRequestFileSystem", "webkitResolveLocalFileSystemURL",
]

MAX_ITERATION = 500000
SENTINEL_API_URL = "https://chatgpt.com/backend-api/sentinel/req"

# ============ Mail API Configuration ============

# 临时邮箱 API 配置
MAIL_API_URL = "https://mail.lmmllm.com/api"
MAIL_API_TOKEN = "@67chr8981CHR123"  # 认证 Token

# ============ Sora API Configuration ============

SORA_API_BASE = "https://sora.chatgpt.com/backend"
SORA_SESSION_API = "https://sora.chatgpt.com/api/auth/session"

# ============ Token Storage API Configuration ============

# 活号存储 API (已禁用)
TOKEN_STORAGE_API_URL = "http://64.23.250.221:8000/api/tokens"
TOKEN_STORAGE_ENABLED = False  # 是否启用活号存储
TOKEN_STORAGE_COOKIE = "panel_public_key=LS0tLS1CRUdJTiBQVUJMSUMgS0VZLS0tLS0KTUlJQklqQU5CZ2txaGtpRzl3MEJBUUVGQUFPQ0FROEFNSUlCQ2dLQ0FRRUEzV2pSZUJTSnlrZjNWYXVOLzZDdgpvRDJKUTNLR3Nza3NubXlqRWs4aVpyNnJnU1hrOWszTXlLaGcvSTFHWVNZNE0vNzFVRGNSZFo4RGErQmJsYkdjClB0QzFCMVR1STR5MDBadmRtU3E3VUtCb0FNSUY0eW85cWNEZDJlaXBoRWNGT211Q0VGRCtzN1NaV2gvUVBTSFgKL2lERlQvTWJCeTg4ck1zTVFMRTBtR0xCRGptNjZLbFplSHFmekRvWWFnTDlSMk9wUFVFK3Y2RkJGVkFFSnJiYQpSc1gyWk5PV2tOZDF4dVdvYktFdnByS1kvUkhISmxVQ0kyZHpMTVZiSjZkYVpVUFB0OWFuMW9xOEZHRVRWWDFyCkNaMlp5cEUxZElhOFVWUkNiQU5EMmFncTFIaEcvdVd0QjBnYmNMZUh6clpvMmtubk1PVm11QTVSbWwxQjFjbm0KVXdJREFRQUIKLS0tLS1FTkQgUFVCTElDIEtFWS0tLS0tCg%3D%3D; session=MTc2OTg3ODU4M3xEWDhFQVFMX2dBQUJFQUVRQUFEX2t2LUFBQVVHYzNSeWFXNW5EQVFBQW1sa0EybHVkQVFDQUFJR2MzUnlhVzVuREFvQUNIVnpaWEp1WVcxbEJuTjBjbWx1Wnd3S0FBaG5aVzV2TURFeU53WnpkSEpwYm1jTUJnQUVjbTlzWlFOcGJuUUVBd0RfeUFaemRISnBibWNNQ0FBR2MzUmhkSFZ6QTJsdWRBUUNBQUlHYzNSeWFXNW5EQWNBQldkeWIzVndCbk4wY21sdVp3d0pBQWRrWldaaGRXeDB89xqHYpniYW18Cb3d1Fy7sTlzndp_jDaCYpzcXLnC39Y=; psession=MTc2OTkxNjQ2NnxOd3dBTkZaRldVVkNVRVkzV2xFM1EwazFUbE5TU0VOUFdVRlhWMGhGVlRaWlQwMUtVVmRKV1VReVRUZFZTa3BTVlVkSlJGWkRURkU9fJ8oUUnsEkGmQ8FAKbaPb7KW9GKui8o3m3B0IaTe2UCp"

# 死号检测配置
DEAD_TOKEN_CHECK_CONFIG = {
    "poll_interval": 40,      # 轮询间隔 40 秒
    "zero_progress_timeout": 100,  # 进度卡 0% 超过 100 秒则判定为死号
    "max_poll_count": 3,      # 最大轮询次数
}

# 死号检测用的随机提示词列表
DEAD_CHECK_PROMPTS = [
    "A cat sitting on a windowsill",
    "A dog running in the park",
    "A beautiful sunset over the ocean",
    "A bird flying in the blue sky",
    "A flower blooming in spring",
    "A mountain covered with snow",
    "A river flowing through the forest",
    "A child playing with a ball",
    "A coffee cup on a wooden table",
    "A butterfly landing on a flower",
    "Rain falling on a city street",
    "A boat sailing on calm water",
    "Stars twinkling in the night sky",
    "A campfire in the wilderness",
    "Waves crashing on the beach",
    "A hot air balloon in the sky",
    "Leaves falling in autumn",
    "A rainbow after the rain",
    "A train passing through countryside",
    "Fish swimming in clear water",
]

def get_random_check_prompt() -> str:
    """Get a random prompt for dead token check"""
    return random.choice(DEAD_CHECK_PROMPTS)

# ============ Proof of Work ============


def _get_parse_time() -> str:
    """Get formatted time string in EST timezone"""
    now = datetime.now(timezone(timedelta(hours=-5)))
    return now.strftime("%a %b %d %Y %H:%M:%S") + " GMT-0500 (Eastern Standard Time)"


def _get_config(user_agent: str) -> list:
    """Generate browser fingerprint config"""
    config = [
        random.choice([1920 + 1080, 2560 + 1440, 1920 + 1200, 2560 + 1600]),
        _get_parse_time(),
        4294705152,
        0,
        user_agent,
        random.choice(CACHED_SCRIPTS) if CACHED_SCRIPTS else "",
        random.choice(CACHED_DPL) if CACHED_DPL else "",
        "en-US",
        "en-US,es-US,en,es",
        0,
        random.choice(NAVIGATOR_KEY),
        random.choice(DOCUMENT_KEY),
        random.choice(WINDOW_KEY),
        time.perf_counter() * 1000,
        str(uuid.uuid4()),
        "",
        random.choice(CORES),
        time.time() * 1000 - (time.perf_counter() * 1000),
    ]
    return config


def _generate_answer(seed: str, diff: str, config: list) -> Tuple[str, bool]:
    """Generate PoW answer by solving hash challenge"""
    seed_encoded = seed.encode()
    static_config_part1 = (json.dumps(config[:3], separators=(',', ':'), ensure_ascii=False)[:-1] + ',').encode()
    static_config_part2 = (',' + json.dumps(config[4:9], separators=(',', ':'), ensure_ascii=False)[1:-1] + ',').encode()
    static_config_part3 = (',' + json.dumps(config[10:], separators=(',', ':'), ensure_ascii=False)[1:]).encode()

    target_diff = bytes.fromhex(diff)
    diff_len = len(target_diff)

    for i in range(MAX_ITERATION):
        dynamic_json_i = str(i).encode()
        dynamic_json_j = str(i >> 1).encode()
        final_json_bytes = static_config_part1 + dynamic_json_i + static_config_part2 + dynamic_json_j + static_config_part3
        base_encode = pybase64.b64encode(final_json_bytes)
        hash_value = hashlib.sha3_512(seed_encoded + base_encode).digest()
        if hash_value[:diff_len] <= target_diff:
            return base_encode.decode(), True

    # Fallback if no solution found
    return "wQ8Lk5FbGpA2NcR9dShT6gYjU7VxZ4D" + pybase64.b64encode(f'"{seed}"'.encode()).decode(), False


def get_pow_token(user_agent: Optional[str] = None) -> str:
    """Generate Proof of Work token

    Args:
        user_agent: Browser user agent string (default: Chrome on Windows)

    Returns:
        PoW token string prefixed with 'gAAAAAC'
    """
    if user_agent is None:
        user_agent = SORA_BROWSER_USER_AGENT

    config = _get_config(user_agent)
    seed = format(random.random())
    diff = "0fffff"
    solution, found = _generate_answer(seed, diff, config)

    if not found:
        print("[SENTINEL] PoW solution not found within max iterations, using fallback")

    return 'gAAAAAC' + solution


# ============ Sentinel Token ============


def _generate_id() -> str:
    """Generate random UUID"""
    return str(uuid.uuid4())


def _generate_payload(data: dict, flow: str,device_id:str) -> str:
    """Generate JSON payload with id and flow"""
    data['id'] = str(device_id)
    data['flow'] = flow
    return json.dumps(data)


def _recalculate_pow(seed: str, difficulty: str, useragent: str) -> str:
    """Recalculate PoW with given seed and difficulty from API response

    Args:
        seed: The seed string from proofofwork response
        difficulty: The difficulty string from proofofwork response
        useragent: User agent string

    Returns:
        PoW token string prefixed with 'gAAAAAB' (note: B not C for recalculated)
    """
    user_agent = useragent
    config = _get_config(user_agent)
    solution, found = _generate_answer(seed, difficulty, config)

    if not found:
        print("[SENTINEL] Recalculated PoW solution not found within max iterations, using fallback")

    # Note: Recalculated PoW uses 'gAAAAAB' prefix (not 'gAAAAAC')
    return 'gAAAAAB' + solution


async def _fetch_requirements(flow: str, pow_token: str, proxy_url: Optional[str] = None) -> Tuple[Optional[dict], bool]:
    """Fetch sentinel requirements from ChatGPT API

    Returns:
        Tuple of (response_dict, success_bool)
    """
    max_retries = 3
    proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None

    for attempt in range(max_retries):
        session = AsyncSession()
        try:
            kwargs = {
                "headers": {"Content-Type": "application/json"},
                "data": _generate_payload({'p': pow_token}, flow),
                "timeout": 30,
                "impersonate": "chrome"
            }
            if proxies:
                kwargs["proxies"] = proxies

            response = await session.post(SENTINEL_API_URL, **kwargs)

            print(f"[SENTINEL] API response status={response.status_code}, body={response.text[:500]}")

            if response.status_code != 200:
                print(f"[SENTINEL] API returned non-200: {response.status_code}")
                if attempt >= max_retries - 1:
                    return None, False
                continue

            result = response.json()
            print(f"[SENTINEL] Fetch requirements success, result keys={list(result.keys()) if isinstance(result, dict) else 'not_dict'}")
            return result, True
        except Exception as err:
            print(f"[SENTINEL] Fetch requirements attempt {attempt + 1} failed: {err}")
            if attempt >= max_retries - 1:
                return None, False
        finally:
            await session.close()

    return None, False


async def get_sentinel_token(flow: str = "sora_2_create_task", useragent: str = "", proxy_url: Optional[str] = None) -> str:
    """Generate Sentinel token for Sora API

    Args:
        flow: The flow type (default: "sora_2_create_task")
        useragent: User agent string
        proxy_url: Optional proxy URL

    Returns:
        Sentinel token JSON string for OpenAI-Sentinel-Token header
    """
    try:
        # Step 1: Generate initial PoW token
        pow_token = get_pow_token(user_agent=useragent if useragent else None)
        print(f"[SENTINEL] Initial PoW token generated: {pow_token[:50]}...")

        # Step 2: Fetch requirements from ChatGPT API
        response, success = await _fetch_requirements(flow, pow_token, proxy_url)

        if not success or response is None:
            print("[SENTINEL] Failed to fetch requirements")
            return _generate_payload({'e': 'fetch_failed', 'p': pow_token}, flow)

        # Step 3: Check if additional PoW is required
        proofofwork = response.get("proofofwork", {})
        final_pow_token = pow_token

        if proofofwork.get("required", False):
            pow_seed = proofofwork.get("seed", "")
            pow_difficulty = proofofwork.get("difficulty", "")

            print(f"[SENTINEL] PoW recalculation required, seed={pow_seed[:20]}..., difficulty={pow_difficulty}")

            if pow_seed and pow_difficulty:
                final_pow_token = _recalculate_pow(pow_seed, pow_difficulty, useragent if useragent else SORA_BROWSER_USER_AGENT)
                print(f"[SENTINEL] Recalculated PoW token: {final_pow_token[:50]}...")
            else:
                print(f"[SENTINEL] PoW required but seed/difficulty missing: seed={pow_seed}, diff={pow_difficulty}")
        else:
            print("[SENTINEL] No additional PoW required, using initial token")

        # Step 4: Construct final token payload
        turnstile_dx = response.get("turnstile", {}).get('dx', "")
        token_c = response.get('token')

        if not turnstile_dx:
            print(f"[SENTINEL] turnstile.dx is empty, response keys={list(response.keys())}")
        if not token_c:
            print(f"[SENTINEL] token is empty/None, response keys={list(response.keys())}")

        payload = _generate_payload({
            'p': final_pow_token,
            't': turnstile_dx,
            'c': token_c
        }, flow)

        print(f"[SENTINEL] Token generated, has_turnstile={bool(turnstile_dx)}, has_token={bool(token_c)}, pow_recalculated={proofofwork.get('required', False)}")
        print(f"[SENTINEL] Final token (first 300 chars): {payload[:300]}")
        return payload

    except Exception as err:
        print(f"[SENTINEL] Token generation failed: {err}")
        pow_token = get_pow_token()
        return _generate_payload({'e': str(err), 'p': pow_token}, flow)


# ============ Temp Mail Service ============

class TempMailService:
    """
    临时邮箱服务 - 使用自定义 API
    
    API 接口:
    - GET /api/domains - 获取可用域名列表
    - GET /api/generate - 生成新的临时邮箱
    - GET /api/emails?mailbox=email@domain.com - 获取邮件列表
    """
    
    def __init__(self, api_url: str = None, api_token: str = None, proxy_url: str = None):
        self.api_url = api_url or MAIL_API_URL
        self.api_token = api_token or MAIL_API_TOKEN
        self.proxy_url = proxy_url
        self.email = None
        self.available_domains = []
    
    def _get_headers(self) -> dict:
        """Get API request headers with authentication"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        return headers
    
    def _request(self, endpoint: str, method: str = "GET") -> dict:
        """Make API request"""
        url = f"{self.api_url.rstrip('/')}{endpoint}"
        proxies = {"http": self.proxy_url, "https": self.proxy_url} if self.proxy_url else None
        
        try:
            session = Session()
            kwargs = {
                "headers": self._get_headers(),
                "timeout": 15,
                "impersonate": "chrome"
            }
            if proxies:
                kwargs["proxies"] = proxies
            
            if method.upper() == "GET":
                response = session.get(url, **kwargs)
            else:
                response = session.post(url, **kwargs)
            
            session.close()
            return response.json()
        except Exception as e:
            print(f"[MAIL_API] Request failed: {e}")
            return {"error": str(e)}
    
    def get_domains(self) -> list:
        """获取可用域名列表"""
        print("[MAIL_API] Getting available domains...")
        data = self._request("/domains")
        
        if isinstance(data, list):
            self.available_domains = data
        elif isinstance(data, dict):
            if "domains" in data:
                self.available_domains = data["domains"]
            elif "data" in data and isinstance(data["data"], list):
                self.available_domains = data["data"]
        
        if self.available_domains:
            print(f"[MAIL_API] Available domains: {len(self.available_domains)} ({', '.join(self.available_domains[:3])}...)")
        else:
            print("[MAIL_API] No domains available")
        
        return self.available_domains
    
    def generate_email(self, max_retries: int = 3) -> Optional[str]:
        """生成新的临时邮箱"""
        print("[MAIL_API] Generating temp email...")
        
        for attempt in range(max_retries):
            data = self._request("/generate")
            
            # 支持多种返回格式
            email = None
            if isinstance(data, dict):
                email = data.get("email") or data.get("address")
                if not email and "data" in data:
                    email = data["data"].get("email") or data["data"].get("address")
            
            if email:
                self.email = email
                print(f"[MAIL_API] ✅ Generated email: {self.email}")
                return self.email
            
            print(f"[MAIL_API] Generate failed (attempt {attempt + 1}/{max_retries}): {data}")
            if attempt < max_retries - 1:
                time.sleep(2)
        
        print("[MAIL_API] ❌ Failed to generate email after retries")
        return None
    
    def get_emails(self) -> list:
        """获取邮件列表"""
        if not self.email:
            return []
        
        data = self._request(f"/emails?mailbox={self.email}")
        
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            if "emails" in data:
                return data["emails"]
            elif "data" in data:
                if isinstance(data["data"], list):
                    return data["data"]
                elif isinstance(data["data"], dict) and "emails" in data["data"]:
                    return data["data"]["emails"]
        
        return []
    
    def _extract_code_from_content(self, content: str) -> Optional[str]:
        """从邮件内容中提取验证码"""
        if not content:
            return None
        
        import re
        patterns = [
            r'code is (\d{6})',
            r'code[:\s]+(\d{6})',
            r'verification code[:\s]+(\d{6})',
            r'verify[:\s]+(\d{6})',
            r'验证码[:\s]*(\d{6})',
            r'Your code is[:\s]*(\d{6})',
            r'Enter this code[:\s]*(\d{6})',
            r'>\s*(\d{6})\s*<',
            r'\b(\d{6})\b',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def wait_for_verification_code(self, timeout: int = 120, poll_interval: int = 5) -> Optional[str]:
        """
        等待并获取验证码
        
        Args:
            timeout: 超时时间(秒)
            poll_interval: 轮询间隔(秒)
        
        Returns:
            验证码或 None
        """
        if not self.email:
            print("[MAIL_API] No email address set")
            return None
        
        print(f"[MAIL_API] Waiting for verification code (timeout: {timeout}s)...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            emails = self.get_emails()
            
            for email in emails:
                # 获取发件人和主题
                from_addr = (email.get("from_address") or email.get("from") or email.get("sender") or "").lower()
                subject = (email.get("subject") or "").lower()
                
                # 检查是否是 OpenAI 相关邮件
                is_openai = (
                    "openai" in from_addr or
                    "openai" in subject or
                    "verify" in subject or
                    "code" in subject or
                    "sora" in subject
                )
                
                if is_openai:
                    print(f"[MAIL_API] Found email: {email.get('subject', 'No subject')}")
                    
                    # 从邮件内容提取验证码
                    content = email.get("content") or email.get("body") or email.get("text") or ""
                    html_content = email.get("html_content") or email.get("html") or ""
                    
                    code = (
                        self._extract_code_from_content(content) or
                        self._extract_code_from_content(html_content) or
                        self._extract_code_from_content(email.get("subject", ""))
                    )
                    
                    if code:
                        print(f"[MAIL_API] ✅ Got verification code: {code}")
                        return code
            
            elapsed = int(time.time() - start_time)
            print(f"[MAIL_API] No code yet, waited {elapsed}s, checking again in {poll_interval}s...")
            time.sleep(poll_interval)
        
        print(f"[MAIL_API] ❌ Timeout waiting for verification code")
        return None
    
    def get_email_address(self) -> Optional[str]:
        """Get current email address"""
        return self.email
    
    def set_email_address(self, email: str):
        """Set email address manually"""
        self.email = email
        print(f"[MAIL_API] Using email: {self.email}")


# Synchronous version for compatibility
def get_sentinel_token_sync(flow: str = "sora_2_create_task", user_agent:str = "",proxy_url: Optional[str] = None,device_id:str = "") -> str:
    """Synchronous version of get_sentinel_token

    Note: This makes a synchronous HTTP request. Use async version when possible.
    """
    try:
        pow_token = get_pow_token(user_agent=user_agent)
        print(f"[SENTINEL] Sync: Initial PoW token generated: {pow_token[:50]}...")

        proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None

        max_retries = 3
        response_data = None

        for attempt in range(max_retries):
            session = Session()
            try:
                kwargs = {
                    "headers": {"Content-Type": "application/json"},
                    "data": _generate_payload({'p': pow_token}, flow,device_id),
                    "timeout": 30,
                    "impersonate": "chrome"
                }
                if proxies:
                    kwargs["proxies"] = proxies

                response = session.post(SENTINEL_API_URL, **kwargs)
                response_data = response.json()
                break
            except Exception as err:
                print(f"[SENTINEL] Sync fetch attempt {attempt + 1} failed: {err}")
                if attempt >= max_retries - 1:
                    return _generate_payload({'e': str(err), 'p': pow_token}, flow)
            finally:
                session.close()

        if response_data is None:
            return _generate_payload({'e': 'fetch_failed', 'p': pow_token}, flow)

        # Check if additional PoW is required
        proofofwork = response_data.get("proofofwork", {})
        final_pow_token = pow_token

        if proofofwork.get("required", False):
            pow_seed = proofofwork.get("seed", "")
            pow_difficulty = proofofwork.get("difficulty", "")

            print(f"[SENTINEL] Sync: PoW recalculation required, seed={pow_seed[:20] if pow_seed else 'empty'}..., difficulty={pow_difficulty}")

            if pow_seed and pow_difficulty:
                final_pow_token = _recalculate_pow(pow_seed, pow_difficulty, SORA_BROWSER_USER_AGENT)
                print(f"[SENTINEL] Sync: Recalculated PoW token: {final_pow_token[:50]}...")
            else:
                print(f"[SENTINEL] Sync: PoW required but seed/difficulty missing")
        else:
            print("[SENTINEL] Sync: No additional PoW required, using initial token")

        turnstile_dx = response_data.get("turnstile", {}).get('dx', "")
        token_c = response_data.get('token')

        if not turnstile_dx:
            print(f"[SENTINEL] Sync: turnstile.dx is empty, response keys={list(response_data.keys())}")
        if not token_c:
            print(f"[SENTINEL] Sync: token is empty/None, response keys={list(response_data.keys())}")

        payload = _generate_payload({
            'p': final_pow_token,
            't': turnstile_dx,
            'c': token_c
        }, flow,device_id=device_id)

        print(f"[SENTINEL] Sync: Token generated, has_turnstile={bool(turnstile_dx)}, has_token={bool(token_c)}, pow_recalculated={proofofwork.get('required', False)}")
        return payload

    except Exception as err:
        print(f"[SENTINEL] Sync token generation failed: {err}")
        pow_token = get_pow_token()
        return _generate_payload({'e': str(err), 'p': pow_token}, flow)


# ============ Sora API Functions (Activation & Dead Token Detection) ============

# 视频创建请求是否使用随机 Sentinel Token（不调用外部服务）
USE_RANDOM_SENTINEL_FOR_VIDEO = True


def _generate_random_sentinel_token(device_id: str, flow: str = "sora_2_create_task") -> str:
    """
    生成随机 Sentinel Token（用于视频创建请求）
    不调用任何外部服务，直接生成随机 token
    
    与项目 sentinel_token_manager.py 保持一致的格式
    
    Args:
        device_id: Device ID (oai-did)
        flow: Flow type
    
    Returns:
        Random sentinel token string (base64 encoded)
    """
    import secrets
    import base64
    
    # 生成随机字节并编码为 urlsafe base64（与项目一致）
    random_bytes = secrets.token_bytes(64)
    token = base64.urlsafe_b64encode(random_bytes).decode('utf-8').rstrip('=')
    
    print(f"🎲 [SENTINEL] Generated random token for video creation: {token[:30]}...")
    return token


def _sora_api_request(endpoint: str, method: str = "GET", access_token: str = "",
                      payload: dict = None, proxy_url: str = None,
                      add_sentinel: bool = False, device_id: str = "",
                      debug: bool = True, use_random_sentinel: bool = None) -> Tuple[int, dict]:
    """
    Make a request to Sora API.
    
    Args:
        endpoint: API endpoint (e.g., "/me", "/nf/create")
        method: HTTP method (GET/POST)
        access_token: Access token for authorization
        payload: Request body for POST requests
        proxy_url: Optional proxy URL
        add_sentinel: Whether to add sentinel token header
        device_id: Device ID for headers
        debug: Whether to print debug info
        use_random_sentinel: Force use random sentinel token (None = auto based on endpoint)
    
    Returns:
        Tuple of (status_code, response_dict)
    """
    url = SORA_API_BASE.rstrip("/") + endpoint
    
    # 生成 device_id
    final_device_id = device_id or str(uuid.uuid4())
    
    headers = {
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Authorization": f"Bearer {access_token}",
        "Origin": "https://sora.chatgpt.com",
        "Referer": "https://sora.chatgpt.com/",
        "User-Agent": SORA_BROWSER_USER_AGENT,
        "oai-device-id": final_device_id,
        "oai-package-name": "com.openai.sora",
    }
    
    if add_sentinel:
        # 判断是否使用随机 sentinel token
        # 视频创建请求 (/nf/create) 在 USE_RANDOM_SENTINEL_FOR_VIDEO=True 时使用随机 token
        should_use_random = use_random_sentinel
        if should_use_random is None:
            # Auto: 只有视频创建请求才使用随机 token
            should_use_random = USE_RANDOM_SENTINEL_FOR_VIDEO and endpoint == "/nf/create"
        
        if should_use_random:
            sentinel_token = _generate_random_sentinel_token(
                device_id=final_device_id,
                flow="sora_2_create_task"
            )
        else:
            sentinel_token = get_sentinel_token_sync(
                flow="sora_2_create_task",
                user_agent=SORA_BROWSER_USER_AGENT,
                proxy_url=proxy_url,
                device_id=final_device_id
            )
        headers["openai-sentinel-token"] = sentinel_token
    
    if payload:
        headers["Content-Type"] = "application/json"
    
    proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None
    
    # 详细日志
    if debug:
        print(f"\n[SORA_API] ====== REQUEST ======")
        print(f"[SORA_API] URL: {method} {url}")
        print(f"[SORA_API] Headers:")
        for k, v in headers.items():
            if k == "Authorization":
                print(f"  {k}: Bearer {access_token[:30]}...")
            elif k == "openai-sentinel-token":
                print(f"  {k}: {v[:50]}...")
            else:
                print(f"  {k}: {v}")
        if payload:
            print(f"[SORA_API] Body: {json.dumps(payload, indent=2)}")
        print(f"[SORA_API] Proxy: {proxy_url or 'None'}")
    
    try:
        session = Session()
        kwargs = {
            "headers": headers,
            "timeout": 30,
            "impersonate": "chrome"
        }
        if proxies:
            kwargs["proxies"] = proxies
        
        if method.upper() == "POST":
            kwargs["data"] = json.dumps(payload) if payload else None
            response = session.post(url, **kwargs)
        else:
            response = session.get(url, **kwargs)
        
        session.close()
        
        try:
            result = response.json()
        except:
            result = {"raw": response.text[:500]}
        
        if debug:
            print(f"[SORA_API] ====== RESPONSE ======")
            print(f"[SORA_API] Status: {response.status_code}")
            print(f"[SORA_API] Body: {json.dumps(result, indent=2) if isinstance(result, dict) else result}")
            print(f"[SORA_API] ========================\n")
        
        return response.status_code, result
    except Exception as e:
        print(f"[SORA_API] Request failed: {e}")
        return 500, {"error": str(e)}


def session_token_to_access_token(session_token: str, proxy_url: str = None) -> Optional[str]:
    """
    Convert Session Token (ST) to Access Token (AT).
    
    Args:
        session_token: The session token from cookie
        proxy_url: Optional proxy URL
    
    Returns:
        Access token string or None if failed
    """
    print("[ACTIVATION] Converting ST to AT...")
    
    headers = {
        "Accept": "application/json",
        "Cookie": f"__Secure-next-auth.session-token={session_token.strip()}",
        "Origin": "https://sora.chatgpt.com",
        "Referer": "https://sora.chatgpt.com/",
        "User-Agent": SORA_BROWSER_USER_AGENT,
    }
    
    proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None
    
    try:
        session = Session()
        kwargs = {
            "headers": headers,
            "timeout": 30,
            "impersonate": "chrome"
        }
        if proxies:
            kwargs["proxies"] = proxies
        
        response = session.get(SORA_SESSION_API, **kwargs)
        session.close()
        
        if response.status_code != 200:
            print(f"[ACTIVATION] ST to AT failed: HTTP {response.status_code}")
            return None
        
        data = response.json()
        access_token = data.get("accessToken")
        
        if access_token:
            print(f"[ACTIVATION] ST to AT success, user: {data.get('user', {}).get('email', 'unknown')}")
            return access_token
        else:
            print(f"[ACTIVATION] ST to AT failed: no accessToken in response")
            return None
    except Exception as e:
        print(f"[ACTIVATION] ST to AT error: {e}")
        return None


def activate_sora2(access_token: str, proxy_url: str = None, device_id: str = "", max_retries: int = 3) -> bool:
    """
    Activate Sora2 by calling bootstrap endpoint with retry.
    
    Args:
        access_token: Access token
        proxy_url: Optional proxy URL
        device_id: Device ID
        max_retries: Maximum retry attempts
    
    Returns:
        True if activation successful, False otherwise
    """
    for attempt in range(max_retries):
        print(f"[ACTIVATION] Activating Sora2 (bootstrap)... (attempt {attempt + 1}/{max_retries})")
        
        status, result = _sora_api_request(
            endpoint="/m/bootstrap",
            method="GET",
            access_token=access_token,
            proxy_url=proxy_url,
            device_id=device_id
        )
        
        if status == 200 and not result.get("error"):
            print("[ACTIVATION] ✅ Sora2 activated successfully")
            return True
        
        if attempt < max_retries - 1:
            print(f"[ACTIVATION] Bootstrap failed: {result}, retrying...")
            time.sleep(1)
    
    print(f"[ACTIVATION] ❌ Sora2 activation failed after {max_retries} attempts")
    return False


def get_user_info(access_token: str, proxy_url: str = None, device_id: str = "", max_retries: int = 3) -> Optional[dict]:
    """
    Get user information from Sora API with retry.
    
    Args:
        access_token: Access token
        proxy_url: Optional proxy URL
        device_id: Device ID
        max_retries: Maximum retry attempts
    
    Returns:
        User info dict or None if failed
    """
    for attempt in range(max_retries):
        print(f"[ACTIVATION] Getting user info... (attempt {attempt + 1}/{max_retries})")
        
        status, result = _sora_api_request(
            endpoint="/me",
            method="GET",
            access_token=access_token,
            proxy_url=proxy_url,
            device_id=device_id
        )
        
        if status == 200 and not result.get("error"):
            print(f"[ACTIVATION] ✅ User info: email={result.get('email')}, username={result.get('username')}")
            return result
        
        if attempt < max_retries - 1:
            print(f"[ACTIVATION] Get user info failed: {result}, retrying...")
            time.sleep(1)
    
    print(f"[ACTIVATION] ❌ Get user info failed after {max_retries} attempts")
    return None


def check_username_available(access_token: str, username: str, proxy_url: str = None, device_id: str = "", max_retries: int = 3) -> bool:
    """
    Check if a username is available with retry.
    
    Args:
        access_token: Access token
        username: Username to check
        proxy_url: Optional proxy URL
        device_id: Device ID
        max_retries: Maximum retry attempts
    
    Returns:
        True if available, False otherwise
    """
    for attempt in range(max_retries):
        status, result = _sora_api_request(
            endpoint="/project_y/profile/username/check",
            method="POST",
            access_token=access_token,
            payload={"username": username},
            proxy_url=proxy_url,
            device_id=device_id
        )
        
        if status == 200 and result.get("available") == True:
            return True
        elif status == 200:
            # API responded but username not available
            return False
        
        # Network error, retry
        if attempt < max_retries - 1:
            print(f"[ACTIVATION] Username check failed (attempt {attempt + 1}), retrying...")
            time.sleep(1)
    
    return False


def set_username(access_token: str, username: str, proxy_url: str = None, device_id: str = "", max_retries: int = 3) -> bool:
    """
    Set username for Sora account with retry.
    
    Args:
        access_token: Access token
        username: Username to set
        proxy_url: Optional proxy URL
        device_id: Device ID
        max_retries: Maximum retry attempts
    
    Returns:
        True if successful, False otherwise
    """
    for attempt in range(max_retries):
        print(f"[ACTIVATION] Setting username: {username} (attempt {attempt + 1}/{max_retries})")
        
        status, result = _sora_api_request(
            endpoint="/project_y/profile/username/set",
            method="POST",
            access_token=access_token,
            payload={"username": username},
            proxy_url=proxy_url,
            device_id=device_id
        )
        
        print(f"[ACTIVATION] Set username response: status={status}, result={result}")
        
        # 成功时返回完整用户信息，包含 username 字段
        if status == 200 and result.get("username"):
            print(f"[ACTIVATION] ✅ Username set successfully: {result.get('username')}")
            return True
        
        # Network error, retry
        if attempt < max_retries - 1:
            print(f"[ACTIVATION] Set username failed, retrying...")
            time.sleep(1)
    
    print(f"[ACTIVATION] ❌ Set username failed after {max_retries} attempts")
    return False


def ensure_username(access_token: str, proxy_url: str = None, device_id: str = "") -> bool:
    """
    Ensure user has a username set, create one if not.
    先检查用户名可用性，再设置用户名，最后验证是否设置成功。
    
    Args:
        access_token: Access token
        proxy_url: Optional proxy URL
        device_id: Device ID
    
    Returns:
        True if username exists or was set, False otherwise
    """
    user_info = get_user_info(access_token, proxy_url, device_id)
    if not user_info:
        return False
    
    if user_info.get("username"):
        print(f"[ACTIVATION] ✅ Username already set: {user_info.get('username')}")
        return True
    
    # Generate random username
    adjectives = ['happy', 'lucky', 'sunny', 'cool', 'smart', 'swift', 'bright', 'calm']
    nouns = ['cat', 'dog', 'bird', 'fish', 'star', 'moon', 'sun', 'sky']
    
    print("[ACTIVATION] Username not set, generating random username...")
    
    for attempt in range(10):  # 增加尝试次数
        adj = random.choice(adjectives)
        noun = random.choice(nouns)
        num = random.randint(1000, 9999)
        username = f"{adj}{noun}{num}"
        
        # 先检查用户名是否可用
        print(f"[ACTIVATION] Checking username availability: {username}")
        if check_username_available(access_token, username, proxy_url, device_id):
            print(f"[ACTIVATION] Username '{username}' is available, setting...")
            # 用户名可用，尝试设置
            if set_username(access_token, username, proxy_url, device_id):
                # 验证是否真的设置成功
                print("[ACTIVATION] Verifying username was set...")
                time.sleep(0.5)
                verify_info = get_user_info(access_token, proxy_url, device_id)
                if verify_info and verify_info.get("username"):
                    print(f"[ACTIVATION] ✅ Username verified: {verify_info.get('username')}")
                    return True
                else:
                    print("[ACTIVATION] ⚠️ Username set API returned success but verification failed, retrying...")
        else:
            print(f"[ACTIVATION] Username '{username}' not available, trying another...")
        
        time.sleep(0.5)
    
    print("[ACTIVATION] ❌ Failed to set username after 10 attempts")
    return False


def get_remaining_count(access_token: str, proxy_url: str = None, device_id: str = "", max_retries: int = 3) -> Optional[dict]:
    """
    Get remaining video generation count with retry.
    
    Args:
        access_token: Access token
        proxy_url: Optional proxy URL
        device_id: Device ID
        max_retries: Maximum retry attempts
    
    Returns:
        Dict with remaining_count and rate_limit_reached, or None if failed
    """
    for attempt in range(max_retries):
        print(f"[ACTIVATION] Getting remaining count... (attempt {attempt + 1}/{max_retries})")
        
        status, result = _sora_api_request(
            endpoint="/nf/check",
            method="GET",
            access_token=access_token,
            proxy_url=proxy_url,
            device_id=device_id
        )
        
        if status == 200 and result.get("rate_limit_and_credit_balance"):
            info = result["rate_limit_and_credit_balance"]
            remaining = info.get("estimated_num_videos_remaining", 0)
            print(f"[ACTIVATION] ✅ Remaining count: {remaining}")
            return {
                "remaining_count": remaining,
                "rate_limit_reached": info.get("rate_limit_reached", False)
            }
        
        if attempt < max_retries - 1:
            print(f"[ACTIVATION] Get remaining count failed: {result}, retrying...")
            time.sleep(1)
    
    print(f"[ACTIVATION] ❌ Get remaining count failed after {max_retries} attempts")
    return None


def create_video_task(access_token: str, prompt: str = None, proxy_url: str = None, device_id: str = "", max_retries: int = 3) -> Optional[str]:
    """
    Create a video generation task with retry.
    
    Args:
        access_token: Access token
        prompt: Video prompt (default: random from list)
        proxy_url: Optional proxy URL
        device_id: Device ID
        max_retries: Maximum retry attempts
    
    Returns:
        Task ID string or None if failed
    """
    prompt = prompt or get_random_check_prompt()
    print(f"[DEAD_CHECK] Using prompt: {prompt}")
    
    payload = {
        "kind": "video",
        "prompt": prompt,
        "title": None,
        "orientation": "landscape",
        "size": "small",
        "n_frames": 150,  # 5 seconds
        "inpaint_items": [],
        "remix_target_id": None,
        "project_id": None,
        "metadata": None,
        "cameo_ids": None,
        "cameo_replacements": None,
        "model": "sy_8_20251208",
        "style_id": None,
        "audio_caption": None,
        "audio_transcript": None,
        "video_caption": None,
        "storyboard_id": None,
    }
    
    for attempt in range(max_retries):
        print(f"[DEAD_CHECK] Creating video task... (attempt {attempt + 1}/{max_retries})")
        
        status, result = _sora_api_request(
            endpoint="/nf/create",
            method="POST",
            access_token=access_token,
            payload=payload,
            proxy_url=proxy_url,
            add_sentinel=True,
            device_id=device_id
        )
        
        if status == 200 and result.get("id"):
            task_id = result["id"]
            print(f"[DEAD_CHECK] ✅ Video task created: {task_id}")
            return task_id
        
        if attempt < max_retries - 1:
            print(f"[DEAD_CHECK] Create video task failed: {result}, retrying...")
            time.sleep(1)
    
    print(f"[DEAD_CHECK] ❌ Create video task failed after {max_retries} attempts")
    return None


def get_pending_tasks(access_token: str, proxy_url: str = None, device_id: str = "") -> Optional[list]:
    """
    Get pending video tasks.
    
    Args:
        access_token: Access token
        proxy_url: Optional proxy URL
        device_id: Device ID
    
    Returns:
        List of pending tasks or None if failed
    """
    print("[DEAD_CHECK] Getting pending tasks...")
    
    status, result = _sora_api_request(
        endpoint="/nf/pending/v2",
        method="GET",
        access_token=access_token,
        proxy_url=proxy_url,
        device_id=device_id
    )
    
    if status == 200 and isinstance(result, list):
        print(f"[DEAD_CHECK] Found {len(result)} pending tasks")
        return result
    else:
        print(f"[DEAD_CHECK] Get pending tasks failed: {result}")
        return None


def check_token_alive(session_token: str, proxy_url: str = None, device_id: str = "") -> Tuple[bool, str, Optional[str]]:
    """
    Check if a token is alive (not a dead token).
    
    Detection flow:
    1. ST to AT
    2. Activate Sora2 (bootstrap)
    3. Ensure username is set
    4. Get remaining count
    5. Create video task
    6. Poll for progress
    7. If progress > 0%, token is alive; if stuck at 0%, it's dead
    
    Args:
        session_token: Session token to check
        proxy_url: Optional proxy URL
        device_id: Device ID
    
    Returns:
        Tuple of (is_alive: bool, reason: str, access_token: str or None)
    """
    if not session_token:
        return False, "Empty session token", None
    
    print("\n" + "="*60)
    print("[DEAD_CHECK] Starting dead token detection...")
    print("="*60)
    
    # Step 1: ST to AT
    access_token = session_token_to_access_token(session_token, proxy_url)
    if not access_token:
        return False, "Failed to convert ST to AT", None
    
    # Step 2: Activate Sora2
    activated = activate_sora2(access_token, proxy_url, device_id)
    if not activated:
        print("[DEAD_CHECK] Sora2 activation failed, continuing anyway...")
    
    # Step 3: Ensure username
    username_ok = ensure_username(access_token, proxy_url, device_id)
    if not username_ok:
        return False, "Failed to set username", None
    
    # Step 4: Get remaining count
    quota_info = get_remaining_count(access_token, proxy_url, device_id)
    if not quota_info:
        return False, "Failed to get remaining count", None
    
    remaining = quota_info.get("remaining_count")
    if remaining is None or remaining <= 0:
        return False, f"No remaining quota: {remaining}", None
    
    print(f"[DEAD_CHECK] Remaining count: {quota_info['remaining_count']}, starting video task...")
    
    # Step 5: Create video task
    task_id = create_video_task(access_token, None, proxy_url, device_id)  # None = use random prompt
    if not task_id:
        return False, "Failed to create video task", None
    
    # Step 6: Poll for progress
    print(f"[DEAD_CHECK] Task created ({task_id}), polling for progress...")
    
    start_time = time.time()
    poll_count = 0
    last_progress = 0
    
    while poll_count < DEAD_TOKEN_CHECK_CONFIG["max_poll_count"]:
        # Wait for poll interval
        time.sleep(DEAD_TOKEN_CHECK_CONFIG["poll_interval"])
        poll_count += 1
        
        print(f"[DEAD_CHECK] Poll #{poll_count}...")
        
        pending_tasks = get_pending_tasks(access_token, proxy_url, device_id)
        if pending_tasks is None:
            print("[DEAD_CHECK] Failed to get pending tasks, continuing...")
            continue
        
        # Find our task
        our_task = next((t for t in pending_tasks if t.get("id") == task_id), None)
        
        if not our_task:
            # Task not in pending list, might be completed
            print("[DEAD_CHECK] Task not in pending list, might be completed")
            if last_progress > 0:
                return True, "Task completed with progress", access_token
            # Task disappeared without progress - might be content issue, consider alive
            return True, "Task completed (possibly content filtered)", access_token
        
        # Get progress
        progress = our_task.get("progress_pct", 0)
        # Handle None or non-numeric progress
        if progress is None:
            progress = 0
        # Handle decimal format (0.xx -> xx%)
        if isinstance(progress, (int, float)) and progress <= 1:
            progress = int(progress * 100)
        
        print(f"[DEAD_CHECK] Task progress: {progress}%")
        
        # If progress > 0%, token is alive
        if progress and progress > 0:
            print(f"[DEAD_CHECK] ✅ Token is ALIVE! Progress: {progress}%")
            return True, f"Task progressing: {progress}%", access_token
        
        last_progress = progress
        
        # Check timeout (stuck at 0%)
        elapsed = time.time() - start_time
        if elapsed >= DEAD_TOKEN_CHECK_CONFIG["zero_progress_timeout"]:
            print(f"[DEAD_CHECK] ❌ Progress stuck at 0% for {elapsed:.0f}s, token is DEAD")
            return False, f"Progress stuck at 0% for {elapsed:.0f} seconds", None
    
    # Max polls reached, still at 0%
    print(f"[DEAD_CHECK] ❌ Max polls ({poll_count}) reached, still at 0%, token is DEAD")
    return False, f"Progress still 0% after {poll_count} polls", None


def store_alive_token(access_token: str, session_token: str, proxy_url: str = None) -> bool:
    """
    将活号存储到远程 API。
    
    Args:
        access_token: Access Token (AT)
        session_token: Session Token (ST)
        proxy_url: 代理 URL
    
    Returns:
        True if successful, False otherwise
    """
    if not TOKEN_STORAGE_ENABLED:
        print("[STORAGE] Token storage is disabled")
        return False
    
    if not access_token or not session_token:
        print("[STORAGE] Missing access_token or session_token")
        return False
    
    print(f"[STORAGE] Storing alive token to API...")
    
    payload = {
        "token": access_token,
        "st": session_token,
        "rt": None,
        "client_id": None,
        "proxy_url": proxy_url,
        "remark": None,
        "image_enabled": True,
        "video_enabled": True,
        "image_concurrency": -1,
        "video_concurrency": -1
    }
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Cookie": TOKEN_STORAGE_COOKIE
    }
    
    try:
        session = Session()
        response = session.post(
            TOKEN_STORAGE_API_URL,
            headers=headers,
            data=json.dumps(payload),
            timeout=30,
            impersonate="chrome"
        )
        session.close()
        
        if response.status_code == 200 or response.status_code == 201:
            print(f"[STORAGE] ✅ Token stored successfully")
            return True
        else:
            print(f"[STORAGE] ❌ Failed to store token: HTTP {response.status_code}")
            print(f"[STORAGE] Response: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"[STORAGE] ❌ Error storing token: {e}")
        return False


def get_date_filename(prefix: str = "st", ext: str = "txt") -> str:
    """
    Get filename with current date.
    Format: prefix_YYYY-MM-DD.ext
    """
    date_str = datetime.now().strftime("%Y-%m-%d")
    return f"{prefix}_{date_str}.{ext}"


def save_session_token(email: str, password: str, session_token: str, 
                       save_full: bool = True, save_st_only: bool = True):
    """
    Save session token to files.
    
    Args:
        email: Email address
        password: Password
        session_token: Session token
        save_full: Save full format (email----password----st) to st_日期.txt
        save_st_only: Save only ST (one per line) to stst_日期.txt
    """
    if save_full:
        # Save full format: email----password----st
        full_filename = get_date_filename("st", "txt")
        line = f"{email}----{password}----{session_token}\n"
        try:
            with open(full_filename, 'a', encoding='utf-8') as f:
                f.write(line)
            print(f"[SAVE] Saved to {full_filename}")
        except Exception as e:
            print(f"[SAVE] Failed to save to {full_filename}: {e}")
    
    if save_st_only:
        # Save ST only (one per line)
        st_filename = get_date_filename("stst", "txt")
        try:
            with open(st_filename, 'a', encoding='utf-8') as f:
                f.write(session_token + "\n")
            print(f"[SAVE] ST saved to {st_filename}")
        except Exception as e:
            print(f"[SAVE] Failed to save ST to {st_filename}: {e}")


# ============ Proxy Configuration ============

# 代理列表 - 从文件加载
PROXY_LIST = []
PROXY_FILE = "daili.txt"

def load_proxies(file_path: str = None) -> list:
    """从文件加载代理列表"""
    global PROXY_LIST
    file_path = file_path or PROXY_FILE
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        proxies = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                # 确保代理有 http:// 或 https:// 前缀
                if not line.startswith('http://') and not line.startswith('https://'):
                    line = 'http://' + line
                proxies.append(line)
        
        PROXY_LIST = proxies
        print(f"[PROXY] Loaded {len(proxies)} proxies from {file_path}")
        return proxies
    except FileNotFoundError:
        print(f"[PROXY] ⚠️ Proxy file not found: {file_path}")
        return []
    except Exception as e:
        print(f"[PROXY] ⚠️ Failed to load proxies: {e}")
        return []

def get_random_proxy() -> str:
    """获取随机代理"""
    global PROXY_LIST
    
    # 如果代理列表为空，尝试加载
    if not PROXY_LIST:
        load_proxies()
    
    if PROXY_LIST:
        proxy = random.choice(PROXY_LIST)
        return proxy
    else:
        print("[PROXY] ⚠️ No proxies available, using None")
        return None


# ============ Main Registration Function ============


def register_openai_account(email: str, email_password: str, openai_password: str,
                           username: str, birthdate: str,
                           proxy_url: Optional[str] = None, save_to_file: bool = True,
                           force_email_type: Optional[str] = None,
                           use_emailnator: bool = False,
                           use_kuku: bool = False,
                           verification_email: Optional[str] = None,
                           skip_dead_check: bool = False,
                           _mail_service: Optional[TempMailService] = None) -> dict:
    """
    Register an OpenAI account with provided credentials.

    Args:
        email: Email address for registration (use "AUTO_CREATE" for Emailnator mode)
        email_password: Password for email account (ignored if use_emailnator=True)
        openai_password: Password for OpenAI account registration
        username: Username for the account
        birthdate: Birthdate in format "YYYY-MM-DD"
        proxy_url: Optional proxy URL (will generate random if not provided)
        save_to_file: Whether to save result to file (default: True)
        force_email_type: Force email type ('gmail' or 'custom' or 'emailnator' or 'kuku'), None for auto-detect
        use_emailnator: Use Emailnator temporary email service (auto-create email)
        use_kuku: Use Kuku.lu temporary email service (auto-create email)
        verification_email: Email for receiving verification code (for Gmail alias, use base email)
        skip_dead_check: Skip dead token detection (faster but won't verify account is alive)

    Returns:
        dict: Registration result with status, message, and account data
            {
                "status": "success" | "failed",
                "message": str,
                "data": {
                    "email": str,
                    "email_password": str,
                    "openai_password": str,
                    "username": str,
                    "session_token": str | None,
                    "device_id": str,
                    "timestamp": str,
                    "is_alive": bool | None,
                    "alive_reason": str | None
                },
                "error": str | None
            }
    """
    from curl_cffi import requests

    # 检测是否使用 Emailnator 模式
    if use_emailnator or email == "AUTO_CREATE" or force_email_type == "emailnator":
        use_emailnator = True
        print("[REGISTER] Using Emailnator mode (will create temporary email)")

    # 检测是否使用 Kuku 模式
    if use_kuku or force_email_type == "kuku":
        use_kuku = True
        use_emailnator = False  # Kuku 优先级更高
        print("[REGISTER] Using Kuku.lu mode (will create temporary email)")

    # Emailnator 客户端（如果需要）
    emailnator_client = None
    if use_emailnator and _mail_service is None:
        try:
            from web.utils.emailnator_utils import EmailnatorClient
            emailnator_client = EmailnatorClient()
        except ImportError:
            try:
                from utils.emailnator_utils import EmailnatorClient
                emailnator_client = EmailnatorClient()
            except ImportError:
                print("[REGISTER] ⚠️ Emailnator module not found, skipping")
                use_emailnator = False

    # Kuku 客户端（如果需要）
    kuku_client = None
    if use_kuku and _mail_service is None:
        try:
            from web.utils.kuku_utils import KukuClient
            kuku_client = KukuClient()
        except ImportError:
            try:
                from utils.kuku_utils import KukuClient
                kuku_client = KukuClient()
            except ImportError:
                print("[REGISTER] ⚠️ Kuku module not found, skipping")
                use_kuku = False

    result = {
        "status": "failed",
        "message": "",
        "data": {
            "email": email if not use_emailnator else "AUTO_CREATE",
            "email_password": email_password,
            "openai_password": openai_password,
            "username": username,
            "session_token": None,
            "device_id": None,
            "timestamp": datetime.now().isoformat()
        },
        "error": None
    }

    try:
        # Setup proxy
        if proxy_url is None:
            proxy_url = get_random_proxy()

        proxies = {
            "http": proxy_url,
            "https": proxy_url
        }

        # 确定用于接收验证码的邮箱
        # 如果指定了 verification_email，用它来接收验证码；否则用注册邮箱
        email_for_verification = verification_email if verification_email else email

        # Emailnator: 创建临时邮箱
        if use_emailnator and emailnator_client:
            print("[REGISTER] Creating temporary email with Emailnator...")
            email = emailnator_client.create_email(email_type='plusGmail')
            if not email:
                raise ValueError("Failed to create temporary email")
            print(f"[REGISTER] ✅ Temporary email created: {email}")
            result["data"]["email"] = email
            # Emailnator 不需要密码
            email_password = None
            # Emailnator 模式下，验证邮箱就是创建的邮箱
            email_for_verification = email

        # Kuku: 创建临时邮箱
        if use_kuku and kuku_client:
            print("[REGISTER] Creating temporary email with Kuku.lu...")
            email = kuku_client.create_email()
            if not email:
                raise ValueError("Failed to create temporary email with Kuku")
            print(f"[REGISTER] ✅ Temporary email created: {email}")
            result["data"]["email"] = email
            # Kuku 不需要密码
            email_password = None
            # Kuku 模式下，验证邮箱就是创建的邮箱
            email_for_verification = email

        print(f"[REGISTER] Starting registration for {email}")
        if verification_email and verification_email != email:
            print(f"[REGISTER] Verification code will be sent to: {email_for_verification}")
        print(f"[REGISTER] Using proxy: {proxy_url}")

        # Initialize session
        headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "zh-CN,zh;q=0.9",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "priority": "u=0, i",
            "referer": "https://chatgpt.com/",
            "sec-ch-ua": "\"Google Chrome\";v=\"143\", \"Chromium\";v=\"143\", \"Not A(Brand\";v=\"24\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"macOS\"",
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "cross-site",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
        }
        session = requests.Session(headers=headers, impersonate="chrome")

        # Step 1: Get CSRF token with retry
        print("[REGISTER] Step 1: Getting CSRF token...")
        url = "https://chatgpt.com/api/auth/csrf"
        csrf_token = None

        for csrf_attempt in range(3):
            try:
                print(f"[REGISTER] CSRF token attempt {csrf_attempt + 1}/3...")
                response = session.get(url, proxies=proxies, impersonate="chrome142")
                print(f"[REGISTER] CSRF response status: {response.status_code}")
                print(f"[REGISTER] CSRF response content-type: {response.headers.get('content-type', 'N/A')}")

                if response.status_code != 200:
                    print(f"[REGISTER] CSRF response text: {response.text[:500]}")
                    if csrf_attempt < 2:
                        time.sleep(2)
                        continue
                    else:
                        raise ValueError(f"CSRF request failed with status {response.status_code}")

                csrf_data = response.json()
                csrf_token = csrf_data['csrfToken']
                print(f"[REGISTER] CSRF token obtained: {csrf_token[:20]}...")
                break

            except json.JSONDecodeError as e:
                print(f"[REGISTER] ⚠️ CSRF response is not valid JSON: {e}")
                print(f"[REGISTER] Response text (first 500 chars): {response.text[:500]}")
                if csrf_attempt < 2:
                    print("[REGISTER] Retrying after 2 seconds...")
                    time.sleep(2)
                    continue
                else:
                    raise ValueError("Failed to get CSRF token after 3 attempts: Invalid JSON response")

            except Exception as e:
                print(f"[REGISTER] ⚠️ CSRF request failed: {e}")
                if csrf_attempt < 2:
                    print("[REGISTER] Retrying after 2 seconds...")
                    time.sleep(2)
                    continue
                else:
                    raise ValueError(f"Failed to get CSRF token after 3 attempts: {e}")

        if not csrf_token:
            raise ValueError("Failed to get CSRF token: No token obtained")

        # Step 2: Initialize sign-in with retry
        device_id = uuid.uuid4()
        loggin_id = uuid.uuid4()
        result["data"]["device_id"] = str(device_id)

        print("[REGISTER] Step 2: Initializing sign-in...")
        url = f"https://chatgpt.com/api/auth/signin/openai?prompt=login&screen_hint=login_or_signup&ext-oai-did={device_id}&auth_session_logging_id={loggin_id}"

        payload = {
            'callbackUrl': "/sora/",
            'csrfToken': csrf_token,
            'json': "true"
        }

        redirect_url = None
        for signin_attempt in range(3):
            try:
                print(f"[REGISTER] Sign-in attempt {signin_attempt + 1}/3...")
                response = session.post(url, data=payload, proxies=proxies, impersonate="chrome142")
                print(f"[REGISTER] Sign-in response status: {response.status_code}")

                if response.status_code != 200:
                    print(f"[REGISTER] Sign-in response text: {response.text[:500]}")
                    if signin_attempt < 2:
                        time.sleep(2)
                        continue
                    else:
                        raise ValueError(f"Sign-in request failed with status {response.status_code}")

                signin_data = response.json()
                redirect_url = signin_data['url']
                print(f"[REGISTER] Redirect URL obtained: {redirect_url[:100]}...")
                break

            except json.JSONDecodeError as e:
                print(f"[REGISTER] ⚠️ Sign-in response is not valid JSON: {e}")
                print(f"[REGISTER] Response text (first 500 chars): {response.text[:500]}")
                if signin_attempt < 2:
                    print("[REGISTER] Retrying after 2 seconds...")
                    time.sleep(2)
                    continue
                else:
                    raise ValueError("Failed to initialize sign-in after 3 attempts: Invalid JSON response")

            except Exception as e:
                print(f"[REGISTER] ⚠️ Sign-in request failed: {e}")
                if signin_attempt < 2:
                    print("[REGISTER] Retrying after 2 seconds...")
                    time.sleep(2)
                    continue
                else:
                    raise ValueError(f"Failed to initialize sign-in after 3 attempts: {e}")

        if not redirect_url:
            raise ValueError("Failed to initialize sign-in: No redirect URL obtained")

        session.get(redirect_url, proxies=proxies, impersonate="chrome142")
        print("[REGISTER] Sign-in initialized")

        # Step 3: Get continue token
        print("[REGISTER] Step 3: Getting continue token...")
        continue_token = get_sentinel_token_sync(
            flow="authorize_continue",
            user_agent=headers['user-agent'],
            proxy_url=proxy_url,
            device_id=device_id
        )

        # Step 4: Authorize continue
        print("[REGISTER] Step 4: Authorizing continue...")
        headers = {
            "accept": "application/json",
            "accept-language": "zh-CN,zh;q=0.9",
            "cache-control": "no-cache",
            "content-type": "application/json",
            "openai-sentinel-token": continue_token,
            "origin": "https://auth.openai.com",
            "pragma": "no-cache",
            "priority": "u=1, i",
            "referer": "https://auth.openai.com/log-in-or-create-account",
            "sec-ch-ua": "\"Google Chrome\";v=\"143\", \"Chromium\";v=\"143\", \"Not A(Brand\";v=\"24\"",
            "sec-ch-ua-arch": "\"arm\"",
            "sec-ch-ua-bitness": "\"64\"",
            "sec-ch-ua-full-version": "\"143.0.7499.193\"",
            "sec-ch-ua-full-version-list": "\"Google Chrome\";v=\"143.0.7499.193\", \"Chromium\";v=\"143.0.7499.193\", \"Not A(Brand\";v=\"24.0.0.0\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-model": "\"\"",
            "sec-ch-ua-platform": "\"macOS\"",
            "sec-ch-ua-platform-version": "\"14.6.0\"",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "traceparent": "00-0000000000000000a3aae9d11cebdb1e-12e64b24824cb6b7-01",
            "tracestate": "dd=s:1;o:rum",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
            "x-datadog-origin": "rum",
            "x-datadog-parent-id": "1361858557503125175",
            "x-datadog-sampling-priority": "1",
            "x-datadog-trace-id": "11793495658565720862"
        }

        url = "https://auth.openai.com/api/accounts/authorize/continue"
        data = {
            "username": {
                "value": email,
                "kind": "email"
            },
            "screen_hint": "login_or_signup"
        }
        data = json.dumps(data, separators=(',', ':'))
        response = session.post(url, headers=headers, data=data, impersonate="chrome142", proxies=proxies)
        print(f"[REGISTER] Authorize response: {response.text[:200]}...")

        # Step 5: Register user if needed
        if not response.json()['page']['type'] == "email_otp_verification":
            print("[REGISTER] Step 5: Registering new user...")
            create_token = get_sentinel_token_sync(
                flow="username_password_create",
                user_agent=headers['user-agent'],
                proxy_url=proxy_url,
                device_id=device_id
            )

            headers = {
                "accept": "application/json",
                "accept-language": "zh-CN,zh;q=0.9",
                "cache-control": "no-cache",
                "content-type": "application/json",
                "openai-sentinel-token": create_token,
                "origin": "https://auth.openai.com",
                "pragma": "no-cache",
                "priority": "u=1, i",
                "referer": "https://auth.openai.com/create-account/password",
                "sec-ch-ua": "\"Google Chrome\";v=\"143\", \"Chromium\";v=\"143\", \"Not A(Brand\";v=\"24\"",
                "sec-ch-ua-arch": "\"arm\"",
                "sec-ch-ua-bitness": "\"64\"",
                "sec-ch-ua-full-version": "\"143.0.7499.193\"",
                "sec-ch-ua-full-version-list": "\"Google Chrome\";v=\"143.0.7499.193\", \"Chromium\";v=\"143.0.7499.193\", \"Not A(Brand\";v=\"24.0.0.0\"",
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-model": "\"\"",
                "sec-ch-ua-platform": "\"macOS\"",
                "sec-ch-ua-platform-version": "\"14.6.0\"",
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
                "traceparent": "00-0000000000000000184d09f13a2a5085-509c273deee5c171-01",
                "tracestate": "dd=s:1;o:rum",
                "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
                "x-datadog-origin": "rum",
                "x-datadog-parent-id": "5808560766355620209",
                "x-datadog-sampling-priority": "1",
                "x-datadog-trace-id": "1751066761784610949"
            }
            cookies = session.cookies
            url = "https://auth.openai.com/api/accounts/user/register"
            data = {
                "password": openai_password,
                "username": email
            }
            data = json.dumps(data, separators=(',', ':'))
            response = session.post(url, headers=headers, cookies=cookies, data=data, proxies=proxies, impersonate="chrome142")
            print(f"[REGISTER] User registration response: {response.text[:200]}...")

        # Step 5.5: Check if we need to trigger email send
        try:
            page_type = response.json().get('page', {}).get('type', '')
            print(f"[REGISTER] Current page type: {page_type}")

            if page_type == 'email_otp_send':
                print("[REGISTER] Step 5.5: Triggering email verification code send...")
                send_url = "https://auth.openai.com/api/accounts/email-otp/send"
                send_headers = {
                    "accept": "*/*",
                    "accept-language": "zh-CN,zh;q=0.9",
                    "content-length": "0",
                    "origin": "https://auth.openai.com",
                    "priority": "u=1, i",
                    "referer": "https://auth.openai.com/email-verification",
                    "sec-ch-ua": "\"Google Chrome\";v=\"143\", \"Chromium\";v=\"143\", \"Not A(Brand\";v=\"24\"",
                    "sec-ch-ua-mobile": "?0",
                    "sec-ch-ua-platform": "\"macOS\"",
                    "sec-fetch-dest": "empty",
                    "sec-fetch-mode": "cors",
                    "sec-fetch-site": "same-origin",
                    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
                }
                send_resp = session.post(
                    send_url,
                    headers=send_headers,
                    cookies=session.cookies,
                    proxies=proxies,
                    impersonate="chrome142"
                )
                print(f"[REGISTER] Email send status: {send_resp.status_code}")
                print(f"[REGISTER] Email send response: {send_resp.text[:200]}")

                if send_resp.status_code != 200:
                    raise ValueError(f"Failed to trigger email send: {send_resp.status_code}")
                print("[REGISTER] ✅ Email verification code sent successfully")
            else:
                print(f"[REGISTER] Email already sent (page type: {page_type}), skipping send step")
        except Exception as e:
            print(f"[REGISTER] ⚠️ Error checking/triggering email send: {e}")
            # Continue anyway, as email might already be sent

        # Step 6: Email verification
        print("[REGISTER] Step 6: Email verification...")

        # 统一的 email verification headers（用于 resend 和 validate）
        email_verification_headers = {
            "accept": "application/json",
            "accept-language": "zh-CN,zh;q=0.9",
            "cache-control": "no-cache",
            "content-type": "application/json",
            "origin": "https://auth.openai.com",
            "pragma": "no-cache",
            "priority": "u=1, i",
            "referer": "https://auth.openai.com/email-verification",
            "sec-ch-ua": "\"Google Chrome\";v=\"143\", \"Chromium\";v=\"143\", \"Not A(Brand\";v=\"24\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"macOS\"",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "traceparent": "00-0000000000000000291bd778a7e42d63-438472980c5f2117-01",
            "tracestate": "dd=s:1;o:rum",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
            "x-datadog-origin": "rum",
            "x-datadog-parent-id": "4865139494835134743",
            "x-datadog-sampling-priority": "1",
            "x-datadog-trace-id": "2962198093139029347"
        }

        code = None

        # 不主动触发 resend，等待自然超时后再触发
        for i in range(3):
            print(f"[REGISTER] Fetching verification code (attempt {i+1}/3)...")

            # 第一次尝试：使用较长的timeout等待邮件到达
            # 后续尝试：在 resend 成功后使用较短timeout
            if i == 0:
                timeout = 60  # 第一次等待60秒
                print(f"[REGISTER] Waiting up to {timeout} seconds for email to arrive...")
            else:
                timeout = 30  # resend 后等待30秒
                print(f"[REGISTER] Waiting up to {timeout} seconds for resent email...")

            # 根据模式选择获取验证码的方式
            # 优先使用传入的 TempMailService
            if _mail_service is not None:
                # 使用 TempMailService 获取验证码
                print("[REGISTER] Using TempMailService to get verification code...")
                code = _mail_service.wait_for_verification_code(timeout=timeout, poll_interval=5)
            elif force_email_type == "tempmail":
                # 使用全局 TempMailService
                print("[REGISTER] Using global TempMailService...")
                temp_mail = TempMailService(proxy_url=proxy_url)
                temp_mail.set_email_address(email)
                code = temp_mail.wait_for_verification_code(timeout=timeout, poll_interval=5)
            elif use_emailnator and emailnator_client:
                # Emailnator 模式：从邮件列表提取验证码
                from utils.emailnator_utils import extract_code_from_subject
                code = None
                poll_start = time.time()
                while time.time() - poll_start < timeout:
                    messages = emailnator_client.get_message_list(email_for_verification)
                    for msg in messages:
                        subject = msg.get('subject', '')
                        from_field = msg.get('from', '')

                        # 跳过广告
                        if msg.get('messageID') == 'ADSVPN':
                            continue

                        # 过滤 OpenAI 邮件
                        if 'openai' not in from_field.lower():
                            continue

                        print(f"[REGISTER] Found email: {subject}")
                        code = extract_code_from_subject(subject)
                        if code:
                            break

                    if code:
                        break

                    elapsed = int(time.time() - poll_start)
                    print(f"[REGISTER] Waiting for verification code... ({elapsed}s)")
                    time.sleep(5)
            elif use_kuku and kuku_client:
                # Kuku 模式：从邮件列表提取验证码
                from utils.kuku_utils import extract_code_from_subject
                code = None
                poll_start = time.time()
                while time.time() - poll_start < timeout:
                    mails = kuku_client.get_mail_list(email_for_verification)
                    for mail in mails:
                        subject = mail.get('subject', '')
                        from_field = mail.get('from', '')

                        # 过滤 OpenAI 邮件
                        if 'openai' not in from_field.lower():
                            continue

                        print(f"[REGISTER] Found email: {subject}")
                        code = extract_code_from_subject(subject)
                        if code:
                            break

                    if code:
                        break

                    elapsed = int(time.time() - poll_start)
                    print(f"[REGISTER] Waiting for verification code... ({elapsed}s)")
                    time.sleep(5)
            else:
                # 传统 IMAP 模式
                try:
                    from utils.email_selector import get_verification_code
                    # 使用 email_for_verification 接收验证码
                    code = get_verification_code(
                        email=email_for_verification,  # 使用验证邮箱接收
                        password=email_password,
                        timeout=timeout,
                        sender_filter=None,  # 不过滤发件人，依赖时间窗口和验证码模式
                        pattern_type='generic',  # 使用通用验证码模式（6位数字）
                        force_type=force_email_type  # 强制指定邮箱类型
                    )
                except ImportError:
                    print("[REGISTER] ⚠️ IMAP module not available, cannot get code")
                    code = None
            if code:
                print(f"[REGISTER] ✅ Verification code received: {code}")
                break
            else:
                print(f"[REGISTER] ⚠️ Code not received on attempt {i+1}/3 (timeout after {timeout}s)")

                # 如果不是最后一次，触发 resend
                if i < 2:
                    print(f"[REGISTER] Email timeout detected, triggering resend...")
                    try:
                        resend_url = "https://auth.openai.com/api/accounts/email-otp/resend"
                        resend_resp = session.post(
                            resend_url,
                            headers=email_verification_headers,
                            cookies=session.cookies,
                            proxies=proxies,
                            impersonate="chrome142"
                        )

                        print(f"[REGISTER] Resend status: {resend_resp.status_code}")
                        print(f"[REGISTER] Resend response: {resend_resp.text[:200]}")

                        # Check for session timeout (409 invalid_state)
                        if resend_resp.status_code == 409:
                            try:
                                error_json = resend_resp.json()
                                error_code = error_json.get('error', {}).get('code', '')
                                if error_code == 'invalid_state':
                                    print("[REGISTER] ❌ Session timeout detected (invalid_state)")
                                    raise ValueError("Session timeout - Invalid session state")
                            except ValueError:
                                raise
                            except:
                                pass

                        # Resend 必须成功，否则直接失败
                        if resend_resp.status_code == 200:
                            print("[REGISTER] ✅ Resend successful")
                            # 不需要额外等待，下一轮循环会用timeout等待
                        else:
                            print(f"[REGISTER] ❌ Resend failed with status {resend_resp.status_code}")
                            raise ValueError(f"Resend failed with status {resend_resp.status_code}")

                    except ValueError:
                        raise
                    except Exception as e:
                        print(f"[REGISTER] ❌ Resend request failed: {e}")
                        raise ValueError(f"Resend request failed: {e}")

        if not code:
            raise ValueError("Failed to get verification code after 3 attempts")

        # Step 6.5: Validate email OTP with retry
        print("[REGISTER] Validating email OTP...")
        otp_validated = False
        continue_url_from_otp = None  # Store continue_url if returned directly from OTP
        max_otp_attempts = 3

        for otp_attempt in range(max_otp_attempts):
            print(f"[REGISTER] OTP validation attempt {otp_attempt + 1}/{max_otp_attempts}...")

            url = "https://auth.openai.com/api/accounts/email-otp/validate"
            data = {
                "code": f"{code}"
            }
            data = json.dumps(data, separators=(',', ':'))
            response = session.post(url, headers=email_verification_headers, data=data, proxies=proxies, impersonate="chrome142")

            print(f"[REGISTER] OTP validation response status: {response.status_code}")
            print(f"[REGISTER] OTP validation response (first 500 chars): {response.text[:500]}...")
            print(f"[REGISTER] Using proxy: {proxy_url}")
            print(f"[REGISTER] Request headers: user-agent={email_verification_headers.get('user-agent', 'N/A')}")

            try:
                response_json = response.json()

                # Check page type first
                page_type = response_json.get('page', {}).get('type', '')

                # Case 1: about_you page - need to fill in profile info
                if page_type == "about_you":
                    print("[REGISTER] ✅ OTP validation successful - need to create account (about_you)")
                    otp_validated = True
                    # Don't set continue_url_from_otp, will create account in Step 7
                    break

                # Case 2: has continue_url but not about_you - direct login (already registered)
                if 'continue_url' in response_json and page_type != "about_you":
                    print("[REGISTER] ✅ OTP validation successful - direct login (already registered)")
                    print(f"[REGISTER] Continue URL (direct): {response_json['continue_url'][:100]}...")
                    print(f"[REGISTER] Response keys: {list(response_json.keys())}")
                    continue_url_from_otp = response_json['continue_url']
                    otp_validated = True
                    break

                # Check if code is wrong
                if 'error' in response_json:
                    error_code = response_json['error'].get('code', '')
                    error_msg = response_json['error'].get('message', '')

                    if error_code == "wrong_email_otp_code":
                        print(f"[REGISTER] ❌ Wrong OTP code: {error_msg}")

                        if otp_attempt < max_otp_attempts - 1:
                            print("[REGISTER] Requesting new verification code...")

                            # Resend OTP
                            resend_url = "https://auth.openai.com/api/accounts/email-otp/resend"
                            try:
                                resend_response = session.post(
                                    resend_url,
                                    headers=email_verification_headers,  # 使用统一的 headers
                                    cookies=session.cookies,
                                    proxies=proxies,
                                    impersonate="chrome142"
                                )
                                print(f"[REGISTER] Resend response: {resend_response.status_code}")
                                print(f"[REGISTER] Resend response text: {resend_response.text[:500]}")

                                # Check for session timeout (409 invalid_state)
                                if resend_response.status_code == 409:
                                    try:
                                        error_json = resend_response.json()
                                        error_code = error_json.get('error', {}).get('code', '')
                                        if error_code == 'invalid_state':
                                            print("[REGISTER] ❌ Session timeout detected during OTP retry (invalid_state)")
                                            raise ValueError("Session timeout - Invalid session. Please start over.")
                                    except ValueError:
                                        raise  # Re-raise ValueError
                                    except:
                                        pass  # Ignore JSON parse errors for 409

                            except ValueError as ve:
                                # Session timeout - propagate up
                                raise
                            except Exception as e:
                                print(f"[REGISTER] ⚠️ Resend failed: {e}")

                            # Wait and fetch new code
                            print("[REGISTER] Waiting 20 seconds for new email...")
                            time.sleep(20)

                            # 根据模式获取新验证码
                            new_code = None
                            if _mail_service is not None:
                                # TempMailService 模式
                                new_code = _mail_service.wait_for_verification_code(timeout=60, poll_interval=5)
                            elif use_emailnator and emailnator_client:
                                # Emailnator 模式
                                from utils.emailnator_utils import extract_code_from_subject
                                messages = emailnator_client.get_message_list(email_for_verification)
                                for msg in messages:
                                    if msg.get('messageID') == 'ADSVPN':
                                        continue
                                    subject = msg.get('subject', '')
                                    from_field = msg.get('from', '')
                                    if 'openai' in from_field.lower():
                                        new_code = extract_code_from_subject(subject)
                                        if new_code:
                                            break
                            elif use_kuku and kuku_client:
                                # Kuku 模式
                                from utils.kuku_utils import extract_code_from_subject
                                mails = kuku_client.get_mail_list(email_for_verification)
                                for mail in mails:
                                    subject = mail.get('subject', '')
                                    from_field = mail.get('from', '')
                                    if 'openai' in from_field.lower():
                                        new_code = extract_code_from_subject(subject)
                                        if new_code:
                                            break
                            else:
                                # 传统 IMAP 模式
                                try:
                                    from utils.email_selector import get_verification_code
                                    new_code = get_verification_code(
                                        email=email_for_verification,
                                        password=email_password,
                                        timeout=60,
                                        sender_filter=None,
                                        pattern_type='generic',
                                        force_type=force_email_type
                                    )
                                except ImportError:
                                    print("[REGISTER] ⚠️ IMAP module not available")
                                    new_code = None
                            if new_code:
                                print(f"[REGISTER] New verification code received: {new_code}")
                                code = new_code
                                continue
                            else:
                                print("[REGISTER] Failed to get new verification code")
                                break
                        else:
                            print("[REGISTER] Max OTP attempts reached")
                            break
                    else:
                        print(f"[REGISTER] Unexpected error: {error_code} - {error_msg}")
                        break
                else:
                    print(f"[REGISTER] Unexpected response format: {list(response_json.keys())}")
                    break

            except Exception as e:
                print(f"[REGISTER] Failed to parse OTP validation response: {e}")
                break

        if not otp_validated:
            raise ValueError("OTP validation failed after multiple attempts")

        # Step 7: Get continue URL (either from OTP or create account)
        second_url = None

        if continue_url_from_otp:
            # Already have continue_url from OTP validation (direct login)
            print("[REGISTER] Step 7: Using continue_url from OTP validation")
            second_url = continue_url_from_otp
        else:
            # Need to create account first
            print("[REGISTER] Step 7: Creating account with profile info...")
            account_token = get_sentinel_token_sync(
                flow="oauth_create_account",
                user_agent=headers['user-agent'],
                proxy_url=proxy_url,
                device_id=device_id
            )

            headers = {
                "accept": "application/json",
                "accept-language": "zh-CN,zh;q=0.9",
                "cache-control": "no-cache",
                "content-type": "application/json",
                "openai-sentinel-token": account_token,
                "origin": "https://auth.openai.com",
                "pragma": "no-cache",
                "priority": "u=1, i",
                "referer": "https://auth.openai.com/about-you",
                "sec-ch-ua": "\"Google Chrome\";v=\"143\", \"Chromium\";v=\"143\", \"Not A(Brand\";v=\"24\"",
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": "\"macOS\"",
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
                "traceparent": "00-0000000000000000e383c36f3e505d1b-01db14224a5db0c9-01",
                "tracestate": "dd=s:1;o:rum",
                "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
                "x-datadog-origin": "rum",
                "x-datadog-parent-id": "133722751446659273",
                "x-datadog-sampling-priority": "1",
                "x-datadog-trace-id": "16394161951112977691"
            }

            url = "https://auth.openai.com/api/accounts/create_account"
            data = {
                "name": username,
                "birthdate": birthdate
            }
            data = json.dumps(data, separators=(',', ':'))

            for i in range(1, 3):
                try:
                    response = session.post(url, headers=headers, data=data, proxies=proxies, impersonate="chrome142")
                    print(response.text)
                    second_url = response.json()['continue_url']
                    if second_url:
                        print(f"[REGISTER] Account created, continue URL: {second_url}")
                        break
                except Exception as e:
                    print(f"[REGISTER] Create account attempt {i} failed: {e}")
                    continue

        if not second_url:
            raise ValueError("Failed to get continue URL")

        # Step 8: Get session token from continue URL
        print(f"[REGISTER] Step 8: Getting session token from continue URL")
        print(f"[REGISTER] Continue URL: {second_url[:100]}...")
        print(f"[REGISTER] Using proxy: {proxy_url}")
        print(f"[REGISTER] Using session: {session}")

        session_token = None
        for i in range(1, 3):
            try:
                print(f"[REGISTER] Session token attempt {i}/2...")
                cookies_resp = session.get(
                    second_url,
                    proxies=proxies,
                    impersonate="chrome142",
                    allow_redirects=True
                )

                print(f"[REGISTER] Response status: {cookies_resp.status_code}")
                print(f"[REGISTER] Response URL: {cookies_resp.url}")
                print(f"[REGISTER] Response headers: {dict(cookies_resp.headers)}")
                print(f"[REGISTER] Response cookies: {cookies_resp.cookies.get_dict()}")

                session_token = cookies_resp.cookies.get_dict().get('__Secure-next-auth.session-token')
                if session_token:
                    print(f"[REGISTER] ✅ Session token obtained: {session_token[:20]}...")
                    break
                else:
                    print(f"[REGISTER] ⚠️ No session token in cookies")
                    print(f"[REGISTER] Available cookies: {list(cookies_resp.cookies.get_dict().keys())}")
            except Exception as e:
                print(f"[REGISTER] Get session token attempt {i} failed: {e}")
                import traceback
                traceback.print_exc()
                continue

        if session_token:
            print(f"[REGISTER] ✅ Session token obtained: {session_token[:50]}...")
            
            if skip_dead_check:
                # Skip dead token check - but still activate account
                print("[REGISTER] Step 9: Skipping dead token check, but activating account...")
                
                # 即使跳过死号检测，也要激活账号
                activation_ok = False
                try:
                    # 获取 Access Token
                    access_token = session_token_to_access_token(session_token, proxy_url)
                    if access_token:
                        # 激活 Sora2 (bootstrap)
                        activate_sora2(access_token, proxy_url, str(device_id))
                        # 设置用户名
                        ensure_username(access_token, proxy_url, str(device_id))
                        activation_ok = True
                        print(f"[REGISTER] ✅ Account activated successfully")
                    else:
                        print(f"[REGISTER] ⚠️ Failed to get access token for activation")
                except Exception as e:
                    print(f"[REGISTER] ⚠️ Activation error: {e}")
                
                result["status"] = "success"
                result["message"] = "Account registered" + (" and activated" if activation_ok else " (activation failed)")
                result["data"]["session_token"] = session_token
                result["data"]["is_alive"] = None  # Unknown - not checked
                result["data"]["alive_reason"] = "Not checked (skipped)"
                result["data"]["activated"] = activation_ok
                print(f"[REGISTER] ✅ Registration successful for {email}")
                
                # Save to files (both full format and ST only)
                if save_to_file:
                    save_session_token(
                        email=email,
                        password=openai_password,
                        session_token=session_token,
                        save_full=True,
                        save_st_only=True
                    )
            else:
                # Step 9: Activate account and check if alive
                print("[REGISTER] Step 9: Activating account and checking if alive...")
                
                is_alive, reason, access_token = check_token_alive(
                    session_token=session_token,
                    proxy_url=proxy_url,
                    device_id=str(device_id)
                )
                
                if is_alive:
                    result["status"] = "success"
                    result["message"] = f"Account registered and verified: {reason}"
                    result["data"]["session_token"] = session_token
                    result["data"]["access_token"] = access_token
                    result["data"]["is_alive"] = True
                    result["data"]["alive_reason"] = reason
                    print(f"[REGISTER] ✅ Registration successful for {email}")
                    print(f"[REGISTER] ✅ Account is ALIVE: {reason}")
                    
                    # 存储活号到远程 API
                    if access_token:
                        store_alive_token(access_token, session_token, proxy_url)
                    
                    # Save to files (both full format and ST only)
                    if save_to_file:
                        save_session_token(
                            email=email,
                            password=openai_password,
                            session_token=session_token,
                            save_full=True,
                            save_st_only=True
                        )
                else:
                    # 注册成功但检测为死号 - 不保存
                    result["status"] = "failed"
                    result["message"] = f"Account registered but detected as DEAD: {reason}"
                    result["data"]["session_token"] = session_token
                    result["data"]["is_alive"] = False
                    result["data"]["dead_reason"] = reason
                    result["error"] = f"Dead token: {reason}"
                    print(f"[REGISTER] ❌ Account {email} registered but is DEAD: {reason}")
        else:
            raise ValueError("Failed to get session token")

    except Exception as e:
        result["status"] = "failed"
        result["message"] = f"Registration failed: {str(e)}"
        result["error"] = str(e)
        print(f"[REGISTER] ❌ Registration failed for {email}: {e}")

    finally:
        pass

    return result


# ============ Batch Registration ============

def batch_register_accounts(accounts_file: str, results_dir: str, max_accounts: Optional[int] = None, max_workers: int = 10):
    """
    Batch register OpenAI accounts from JSON file using thread pool for parallel processing.

    Args:
        accounts_file: Path to accounts_ready.json
        results_dir: Directory to save results (will be created with date prefix)
        max_accounts: Maximum number of accounts to register (None for all)
        max_workers: Number of concurrent threads (default: 10)

    Returns:
        dict: Summary of registration results
    """
    import os
    import threading
    from pathlib import Path
    from concurrent.futures import ThreadPoolExecutor, as_completed

    # Thread-safe locks
    file_lock = threading.Lock()
    stats_lock = threading.Lock()

    # Load accounts
    print(f"[BATCH] Loading accounts from: {accounts_file}")
    with open(accounts_file, 'r', encoding='utf-8') as f:
        accounts = json.load(f)

    total = len(accounts)
    print(f"[BATCH] Found {total} accounts")

    # Filter pending accounts
    pending_accounts = [acc for acc in accounts if acc.get('status') == 'pending']
    print(f"[BATCH] Pending accounts: {len(pending_accounts)}")

    if not pending_accounts:
        print("[BATCH] No pending accounts to process")
        return {
            "total": total,
            "pending": 0,
            "processed": 0,
            "success": 0,
            "failed": 0
        }

    # Limit number if specified
    if max_accounts:
        pending_accounts = pending_accounts[:max_accounts]
        print(f"[BATCH] Processing first {len(pending_accounts)} accounts")

    # Create date-based directory (format: YYYYMMDD_account)
    today_str = datetime.now().strftime("%Y%m%d")
    dated_results_dir = os.path.join(results_dir, f"{today_str}_account")
    Path(dated_results_dir).mkdir(parents=True, exist_ok=True)
    print(f"[BATCH] Results will be saved to: {dated_results_dir}")

    # Results file paths
    success_results_file = os.path.join(dated_results_dir, "results.json")
    failure_results_file = os.path.join(dated_results_dir, "failures.json")

    # Load existing results if files exist
    success_results = []
    if os.path.exists(success_results_file):
        try:
            with open(success_results_file, 'r', encoding='utf-8') as f:
                success_results = json.load(f)
            print(f"[BATCH] Loaded {len(success_results)} existing success results")
        except Exception as e:
            print(f"[BATCH] Failed to load existing success results: {e}")
            success_results = []

    failure_results = []
    if os.path.exists(failure_results_file):
        try:
            with open(failure_results_file, 'r', encoding='utf-8') as f:
                failure_results = json.load(f)
            print(f"[BATCH] Loaded {len(failure_results)} existing failure results")
        except Exception as e:
            print(f"[BATCH] Failed to load existing failure results: {e}")
            failure_results = []

    # Statistics
    stats = {
        "total": total,
        "pending": len(pending_accounts),
        "processed": 0,
        "success": 0,
        "failed": 0,
        "start_time": datetime.now().isoformat()
    }

    # Worker function for thread pool
    def process_single_account(account, idx, total_count):
        """Process a single account registration"""
        email = account['email']
        print(f"\n{'='*60}")
        print(f"[THREAD-{threading.current_thread().name}] Processing {idx}/{total_count}: {email}")
        print(f"{'='*60}")

        # Update status to processing
        account['status'] = 'processing'

        try:
            # Call registration function
            result = register_openai_account(
                email=email,
                email_password=account['email_password'],
                openai_password=account['openai_password'],
                username=account['username'],
                birthdate=account['birthdate'],
                proxy_url=None,
                save_to_file=False
            )

            # Update account with result
            if result['status'] == 'success':
                account['status'] = 'success'
                account['session_token'] = result['data']['session_token']
                account['device_id'] = result['data']['device_id']
                account['registered_at'] = datetime.now().isoformat()
                account['error'] = None

                # Thread-safe success result update
                with stats_lock:
                    stats['success'] += 1

                print(f"[THREAD-{threading.current_thread().name}] ✅ Success: {email}")

                # Success record
                success_record = {
                    "email": email,
                    "email_password": account['email_password'],
                    "openai_password": account['openai_password'],
                    "username": account['username'],
                    "birthdate": account['birthdate'],
                    "session_token": result['data']['session_token'],
                    "device_id": result['data']['device_id'],
                    "registered_at": datetime.now().isoformat()
                }

                # Thread-safe file write
                with file_lock:
                    success_results.append(success_record)
                    with open(success_results_file, 'w', encoding='utf-8') as f:
                        json.dump(success_results, f, indent=2, ensure_ascii=False)
                print(f"[THREAD-{threading.current_thread().name}] Success saved to: {success_results_file}")

            else:
                account['status'] = 'failed'
                account['error'] = result['error']
                account['registered_at'] = datetime.now().isoformat()

                # Thread-safe failure stats update
                with stats_lock:
                    stats['failed'] += 1

                print(f"[THREAD-{threading.current_thread().name}] ❌ Failed: {email} - {result['message']}")

                # Failure record
                failure_record = {
                    "email": email,
                    "email_password": account['email_password'],
                    "openai_password": account['openai_password'],
                    "username": account['username'],
                    "birthdate": account['birthdate'],
                    "error": result['error'],
                    "error_message": result['message'],
                    "failed_at": datetime.now().isoformat()
                }

                # Thread-safe file write
                with file_lock:
                    failure_results.append(failure_record)
                    with open(failure_results_file, 'w', encoding='utf-8') as f:
                        json.dump(failure_results, f, indent=2, ensure_ascii=False)
                print(f"[THREAD-{threading.current_thread().name}] Failure saved to: {failure_results_file}")

        except Exception as e:
            account['status'] = 'failed'
            account['error'] = str(e)
            account['registered_at'] = datetime.now().isoformat()

            with stats_lock:
                stats['failed'] += 1

            print(f"[THREAD-{threading.current_thread().name}] ❌ Exception: {email} - {e}")

        # Thread-safe progress update
        with stats_lock:
            stats['processed'] += 1
            current_processed = stats['processed']
            current_success = stats['success']
            current_failed = stats['failed']

        # Save progress after each account (thread-safe)
        with file_lock:
            with open(accounts_file, 'w', encoding='utf-8') as f:
                json.dump(accounts, f, indent=2, ensure_ascii=False)

        print(f"[THREAD-{threading.current_thread().name}] Progress: {current_processed}/{total_count} "
              f"(Success: {current_success}, Failed: {current_failed})")

        return account

    # Process accounts using thread pool
    print(f"\n[BATCH] Starting thread pool with {max_workers} workers...")
    print(f"[BATCH] Processing {len(pending_accounts)} accounts in parallel\n")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_account = {
            executor.submit(process_single_account, account, idx, len(pending_accounts)): account
            for idx, account in enumerate(pending_accounts, 1)
        }

        # Wait for all tasks to complete
        for future in as_completed(future_to_account):
            account = future_to_account[future]
            try:
                future.result()
            except Exception as e:
                print(f"[BATCH] ⚠️ Thread exception for {account['email']}: {e}")

    # Final summary
    stats['end_time'] = datetime.now().isoformat()
    stats['success_results_file'] = success_results_file
    stats['failure_results_file'] = failure_results_file

    print(f"\n{'='*60}")
    print("BATCH REGISTRATION SUMMARY")
    print(f"{'='*60}")
    print(f"Total accounts: {stats['total']}")
    print(f"Processed: {stats['processed']}")
    print(f"Success: {stats['success']} ✅")
    print(f"Failed: {stats['failed']} ❌")
    print(f"Success rate: {stats['success']/stats['processed']*100:.1f}%" if stats['processed'] > 0 else "N/A")
    print(f"\nResults directory: {dated_results_dir}")
    print(f"  - Success accounts: results.json ({len(success_results)} accounts)")
    print(f"  - Failed accounts: failures.json ({len(failure_results)} accounts)")
    print(f"  - Summary: summary.json")
    print(f"  - Source tracking: {ACCOUNTS_FILE}")
    print(f"{'='*60}\n")

    # Save summary
    summary_file = os.path.join(dated_results_dir, "summary.json")
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    print(f"[BATCH] Summary saved to: {summary_file}")

    return stats


# ============ Auto Registration with TempMail ============

def generate_random_password(length: int = 14) -> str:
    """生成随机密码"""
    import string
    upper = 'ABCDEFGHJKLMNPQRSTUVWXYZ'
    lower = 'abcdefghjkmnpqrstuvwxyz'
    digits = '23456789'
    specials = '!@#$%^&*'
    all_chars = upper + lower + digits
    
    # 确保包含各类字符
    password = [
        random.choice(upper),
        random.choice(lower),
        random.choice(digits),
        random.choice(specials),
    ]
    
    # 填充剩余字符
    for _ in range(length - 4):
        password.append(random.choice(all_chars))
    
    # 打乱顺序
    random.shuffle(password)
    return ''.join(password)


def generate_random_birthdate() -> str:
    """生成随机生日 (18-40岁)"""
    current_year = datetime.now().year
    year = current_year - random.randint(18, 40)
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    return f"{year}-{month:02d}-{day:02d}"


def generate_random_username() -> str:
    """生成随机用户名 - OpenAI 要求只能包含字母和空格"""
    import string
    
    def random_name(min_len: int = 4, max_len: int = 8) -> str:
        """Generate a random name-like string"""
        length = random.randint(min_len, max_len)
        # First letter uppercase, rest lowercase
        first = random.choice(string.ascii_uppercase)
        rest = ''.join(random.choice(string.ascii_lowercase) for _ in range(length - 1))
        return first + rest
    
    first_name = random_name(4, 8)
    last_name = random_name(4, 10)
    return f"{first_name} {last_name}"


def auto_register_one(proxy_url: str = None, skip_dead_check: bool = False,
                      mail_api_url: str = None, mail_api_token: str = None) -> dict:
    """
    自动注册一个账号 - 使用临时邮箱自动生成
    
    Args:
        proxy_url: 代理 URL
        skip_dead_check: 是否跳过死号检测
        mail_api_url: 邮箱 API URL (默认使用全局配置)
        mail_api_token: 邮箱 API Token
    
    Returns:
        dict: 注册结果
    """
    print("\n" + "="*60)
    print("[AUTO_REGISTER] Starting auto registration...")
    print("="*60)
    
    # 初始化临时邮箱服务
    mail_service = TempMailService(
        api_url=mail_api_url,
        api_token=mail_api_token,
        proxy_url=proxy_url
    )
    
    # 获取可用域名
    mail_service.get_domains()
    
    # 生成临时邮箱
    email = mail_service.generate_email()
    if not email:
        return {
            "status": "failed",
            "message": "Failed to generate temp email",
            "error": "Email generation failed"
        }
    
    # 生成随机密码、用户名、生日
    password = generate_random_password()
    username = generate_random_username()
    birthdate = generate_random_birthdate()
    
    print(f"[AUTO_REGISTER] Email: {email}")
    print(f"[AUTO_REGISTER] Password: {password}")
    print(f"[AUTO_REGISTER] Username: {username}")
    print(f"[AUTO_REGISTER] Birthdate: {birthdate}")
    
    # 调用注册函数 - 使用临时邮箱服务获取验证码
    result = register_openai_account(
        email=email,
        email_password="",  # 临时邮箱不需要密码
        openai_password=password,
        username=username,
        birthdate=birthdate,
        proxy_url=proxy_url,
        save_to_file=True,
        force_email_type="tempmail",  # 标记使用临时邮箱
        skip_dead_check=skip_dead_check,
        # 传递邮箱服务用于获取验证码
        _mail_service=mail_service
    )
    
    return result


# 用于取消任务的全局标志
_cancel_flag = False

def auto_register_batch(count: int = 10, proxy_url: str = None, 
                        skip_dead_check: bool = False,
                        max_workers: int = 1,
                        mail_api_url: str = None, mail_api_token: str = None,
                        max_attempts: int = None) -> dict:
    """
    批量自动注册 - 使用临时邮箱自动生成
    
    Args:
        count: 目标成功数量（活号数量）
        proxy_url: 代理 URL
        skip_dead_check: 是否跳过死号检测
        max_workers: 并发数 (1 = 串行)
        mail_api_url: 邮箱 API URL
        mail_api_token: 邮箱 API Token
        max_attempts: 最大尝试次数 (默认 count * 3，防止无限循环)
    
    Returns:
        dict: 批量注册结果统计
    """
    import threading
    import signal
    from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED
    
    global _cancel_flag
    _cancel_flag = False
    
    # 设置最大尝试次数，防止无限循环
    if max_attempts is None:
        max_attempts = count * 3
    
    print(f"\n{'='*60}")
    print(f"[BATCH_AUTO] Starting batch auto registration")
    print(f"[BATCH_AUTO] Target: {count} successful accounts")
    print(f"[BATCH_AUTO] Max attempts: {max_attempts}")
    print(f"[BATCH_AUTO] Concurrency: {max_workers}")
    print(f"[BATCH_AUTO] Skip dead check: {skip_dead_check}")
    print(f"[BATCH_AUTO] Mail API: {mail_api_url or MAIL_API_URL}")
    print(f"[BATCH_AUTO] Press Ctrl+C to cancel...")
    print(f"{'='*60}\n")
    
    # Thread-safe locks
    stats_lock = threading.Lock()
    
    stats = {
        "target": count,
        "success": 0,
        "failed": 0,
        "dead": 0,
        "attempts": 0,
        "cancelled": 0,
        "results": []
    }
    
    def register_task():
        """Single registration task"""
        global _cancel_flag
        
        if _cancel_flag:
            return {"status": "cancelled", "error": "User cancelled"}
        
        # 检查是否已达到目标
        with stats_lock:
            if stats["success"] >= count:
                return {"status": "skipped", "error": "Target reached"}
            if stats["attempts"] >= max_attempts:
                return {"status": "skipped", "error": "Max attempts reached"}
            stats["attempts"] += 1
            current_attempt = stats["attempts"]
        
        thread_name = threading.current_thread().name
        print(f"\n[{thread_name}] === Attempt {current_attempt} (Target: {stats['success']}/{count}) ===")
        
        try:
            result = auto_register_one(
                proxy_url=proxy_url,
                skip_dead_check=skip_dead_check,
                mail_api_url=mail_api_url,
                mail_api_token=mail_api_token
            )
            
            with stats_lock:
                if _cancel_flag:
                    stats["cancelled"] += 1
                elif result.get("status") == "success":
                    # 检查是否是活号
                    is_alive = result.get("data", {}).get("is_alive")
                    if is_alive is False:
                        # 死号不计入成功
                        stats["dead"] += 1
                        print(f"[{thread_name}] ⚠️ DEAD TOKEN (not counted)")
                    else:
                        # 活号或跳过检测
                        stats["success"] += 1
                        print(f"[{thread_name}] ✅ SUCCESS ({stats['success']}/{count})")
                else:
                    stats["failed"] += 1
                    print(f"[{thread_name}] ❌ FAILED: {result.get('error', 'Unknown')}")
                stats["results"].append(result)
                
                # Print progress
                print(f"[PROGRESS] Success: {stats['success']}/{count} | Failed: {stats['failed']} | Dead: {stats['dead']} | Attempts: {stats['attempts']}/{max_attempts}")
            
            return result
            
        except Exception as e:
            with stats_lock:
                stats["failed"] += 1
                stats["results"].append({
                    "status": "failed",
                    "error": str(e)
                })
            print(f"[{thread_name}] ❌ EXCEPTION: {e}")
            return {"status": "failed", "error": str(e)}
    
    # Execute with thread pool
    executor = None
    futures = []
    
    def check_should_stop():
        """Check if we should stop submitting new tasks"""
        with stats_lock:
            return stats["success"] >= count or stats["attempts"] >= max_attempts or _cancel_flag
    
    try:
        if max_workers > 1:
            # Concurrent execution
            executor = ThreadPoolExecutor(max_workers=max_workers)
            
            # Submit initial batch of tasks
            for _ in range(min(max_workers, max_attempts)):
                if check_should_stop():
                    break
                futures.append(executor.submit(register_task))
            
            # Process completed futures and submit new ones
            while futures:
                if check_should_stop():
                    # Cancel remaining futures
                    for f in futures:
                        f.cancel()
                    break
                
                # Wait for any future to complete
                done_futures = []
                for f in futures:
                    if f.done():
                        done_futures.append(f)
                
                if not done_futures:
                    time.sleep(0.5)
                    continue
                
                # Remove completed futures
                for f in done_futures:
                    futures.remove(f)
                    try:
                        f.result()
                    except Exception as e:
                        if not _cancel_flag:
                            print(f"[BATCH_AUTO] Thread exception: {e}")
                    
                    # Submit a new task if not reached target
                    if not check_should_stop():
                        futures.append(executor.submit(register_task))
            
            # Final status
            with stats_lock:
                if stats["success"] >= count:
                    print(f"\n[BATCH_AUTO] ✅ Target reached: {stats['success']}/{count}")
                elif stats["attempts"] >= max_attempts:
                    print(f"\n[BATCH_AUTO] ⚠️ Max attempts reached: {stats['attempts']}/{max_attempts}")
        else:
            # Sequential execution
            while True:
                if check_should_stop():
                    with stats_lock:
                        if stats["success"] >= count:
                            print(f"\n[BATCH_AUTO] ✅ Target reached: {stats['success']}/{count}")
                        elif stats["attempts"] >= max_attempts:
                            print(f"\n[BATCH_AUTO] ⚠️ Max attempts reached: {stats['attempts']}/{max_attempts}")
                    break
                
                register_task()
                time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n\n[BATCH_AUTO] ⚠️ Ctrl+C detected, cancelling...")
        _cancel_flag = True
        # Cancel all pending futures
        for f in futures:
            f.cancel()
    
    finally:
        if executor:
            executor.shutdown(wait=False, cancel_futures=True)
    
    # 打印统计
    print(f"\n{'='*60}")
    print("BATCH AUTO REGISTRATION SUMMARY")
    print(f"{'='*60}")
    print(f"Target: {stats['target']}")
    print(f"Attempts: {stats['attempts']}")
    print(f"Success (alive): {stats['success']} ✅")
    print(f"Dead tokens: {stats['dead']} ⚠️")
    print(f"Failed: {stats['failed']} ❌")
    print(f"Success rate: {stats['success']/stats['attempts']*100:.1f}%" if stats['attempts'] > 0 else "N/A")
    print(f"\nResults saved to:")
    print(f"  - st_{datetime.now().strftime('%Y-%m-%d')}.txt (email----password----st)")
    print(f"  - stst_{datetime.now().strftime('%Y-%m-%d')}.txt (st only)")
    print(f"{'='*60}\n")
    
    return stats


# ============ Activate Account Function ============

def activate_account(session_token: str, proxy_url: str = None) -> dict:
    """
    单独激活一个账号（不创建视频任务）。
    用于测试激活流程是否正常工作。
    
    Args:
        session_token: Session Token
        proxy_url: 代理 URL
    
    Returns:
        dict: 激活结果
    """
    result = {
        "st_to_at": False,
        "bootstrap": False,
        "user_info": None,
        "username_set": False,
        "access_token": None,
        "error": None
    }
    
    device_id = str(uuid.uuid4())
    
    print(f"\n{'='*60}")
    print("[ACTIVATE] Starting account activation...")
    print(f"[ACTIVATE] ST: {session_token[:50]}...")
    print(f"[ACTIVATE] Proxy: {proxy_url or 'None'}")
    print(f"{'='*60}\n")
    
    try:
        # Step 1: ST to AT
        print("[ACTIVATE] Step 1: Converting ST to AT...")
        access_token = session_token_to_access_token(session_token, proxy_url)
        if not access_token:
            result["error"] = "Failed to convert ST to AT"
            print(f"[ACTIVATE] ❌ {result['error']}")
            return result
        result["st_to_at"] = True
        result["access_token"] = access_token[:50] + "..."
        print(f"[ACTIVATE] ✅ ST to AT success")
        
        # Step 2: Bootstrap (activate Sora2)
        print("\n[ACTIVATE] Step 2: Calling bootstrap (activate Sora2)...")
        bootstrap_ok = activate_sora2(access_token, proxy_url, device_id)
        result["bootstrap"] = bootstrap_ok
        if bootstrap_ok:
            print(f"[ACTIVATE] ✅ Bootstrap success")
        else:
            print(f"[ACTIVATE] ⚠️ Bootstrap failed (continuing anyway)")
        
        # Step 3: Get user info
        print("\n[ACTIVATE] Step 3: Getting user info...")
        user_info = get_user_info(access_token, proxy_url, device_id)
        if user_info:
            result["user_info"] = {
                "email": user_info.get("email"),
                "username": user_info.get("username"),
                "name": user_info.get("name")
            }
            print(f"[ACTIVATE] ✅ User info: email={user_info.get('email')}, username={user_info.get('username')}")
        else:
            print(f"[ACTIVATE] ⚠️ Failed to get user info")
        
        # Step 4: Set username if not set
        print("\n[ACTIVATE] Step 4: Ensuring username is set...")
        username_ok = ensure_username(access_token, proxy_url, device_id)
        result["username_set"] = username_ok
        if username_ok:
            print(f"[ACTIVATE] ✅ Username is set")
        else:
            print(f"[ACTIVATE] ❌ Failed to set username")
        
        # Final summary
        print(f"\n{'='*60}")
        print("[ACTIVATE] ACTIVATION SUMMARY")
        print(f"{'='*60}")
        print(f"  ST to AT:    {'✅' if result['st_to_at'] else '❌'}")
        print(f"  Bootstrap:   {'✅' if result['bootstrap'] else '❌'}")
        print(f"  User Info:   {'✅' if result['user_info'] else '❌'}")
        print(f"  Username:    {'✅' if result['username_set'] else '❌'}")
        
        if result["user_info"]:
            print(f"\n  Email:    {result['user_info'].get('email')}")
            print(f"  Username: {result['user_info'].get('username')}")
        
        success = result["st_to_at"] and result["username_set"]
        print(f"\n  Overall:  {'✅ ACTIVATED' if success else '❌ FAILED'}")
        print(f"{'='*60}\n")
        
        return result
        
    except Exception as e:
        result["error"] = str(e)
        print(f"[ACTIVATE] ❌ Exception: {e}")
        return result


# ============ Main Entry Point ============
if __name__ == "__main__":
    import sys
    
    # 加载代理
    load_proxies()
    proxy_count = len(PROXY_LIST)
    
    print(f"""
╭──────────────────────────────────────────────────────╮
│       Sora Auto Registration Tool v2.0               │
├──────────────────────────────────────────────────────┤
│  邮箱 API: {MAIL_API_URL:<40} │
│  代理数量: {proxy_count:<42} │
│  支持功能: 自动注册 + 激活 + 死号检测                │
├──────────────────────────────────────────────────────┤
│  模式:                                               │
│  1. 自动注册单个账号 (临时邮箱)                      │
│  2. 批量自动注册 (指定数量+并发)                     │
│  3. 从 JSON 文件批量注册                             │
│  4. 测试激活单个 ST (调试用)                         │
╰──────────────────────────────────────────────────────╯
    """)
    
    if proxy_count == 0:
        print("⚠️  警告: 未加载到代理，请确保 daili.txt 文件存在\n")
    
    # 选择模式
    print("请选择运行模式:")
    print("1. 自动注册单个账号")
    print("2. 批量自动注册 (指定数量+并发)")
    print("3. 从 JSON 文件批量注册")
    print("4. 测试激活单个 ST (调试用)")
    print("")
    
    choice = input("请输入 1/2/3 [默认 2]: ").strip() or "2"
    
    # 是否跳过死号检测
    skip_check = input("是否跳过死号检测? (y/n) [默认 y]: ").strip().lower() or "y"
    skip_dead_check = skip_check == 'y'
    
    if choice == "1":
        # 单个自动注册
        result = auto_register_one(skip_dead_check=skip_dead_check)
        print(f"\n注册结果: {result.get('status')}")
        if result.get('data', {}).get('session_token'):
            print(f"Session Token: {result['data']['session_token'][:50]}...")
    
    elif choice == "2":
        # 批量自动注册
        print("\n--- 批量自动注册配置 ---")
        count_str = input("请输入注册数量: ").strip()
        while not count_str or not count_str.isdigit() or int(count_str) < 1:
            count_str = input("请输入有效的注册数量 (>=1): ").strip()
        count = int(count_str)
        
        workers_str = input(f"请输入并发数 [默认 1, 最大 {min(count, 10)}]: ").strip() or "1"
        max_workers = min(int(workers_str), count, 10)  # 限制最大并发10
        
        print(f"\n配置确认:")
        print(f"  注册数量: {count}")
        print(f"  并发数: {max_workers}")
        print(f"  跳过死号检测: {'是' if skip_dead_check else '否'}")
        print(f"  邮箱 API: {MAIL_API_URL}")
        print(f"  代理数量: {len(PROXY_LIST)}")
        
        confirm = input("\n确认开始? (y/n) [默认 y]: ").strip().lower() or "y"
        if confirm == 'y':
            auto_register_batch(
                count=count,
                skip_dead_check=skip_dead_check,
                max_workers=max_workers
            )
        else:
            print("已取消")
    
    elif choice == "3":
        # 从 JSON 文件批量注册
        accounts_file = input("请输入账号 JSON 文件路径: ").strip()
        results_dir = input("请输入结果保存目录 [默认 ./data]: ").strip() or "./data"
        
        max_accounts_str = input("最大注册数量 [默认全部]: ").strip()
        max_accounts = int(max_accounts_str) if max_accounts_str else None
        
        workers_str = input("并发线程数 [默认 5]: ").strip() or "5"
        max_workers = int(workers_str)
        
        batch_register_accounts(
            accounts_file=accounts_file,
            results_dir=results_dir,
            max_accounts=max_accounts,
            max_workers=max_workers
        )
    
    else:
        print("无效选择")
    
