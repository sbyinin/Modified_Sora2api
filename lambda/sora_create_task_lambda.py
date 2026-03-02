"""
通用 Sora API Lambda 代理

支持的请求类型:
- nf_create: 创建视频生成任务 (POST /nf/create)
- nf_create_storyboard: 创建分镜视频任务 (POST /nf/create/storyboard)
- video_gen: 生成图片 (POST /video_gen)
- uploads: 上传图片 (POST /uploads)
- pending: 获取待处理任务 (GET /nf/pending/v2)
- me: 获取用户信息 (GET /me)
- enhance_prompt: 增强提示词 (POST /editor/enhance_prompt)
- post: 发布视频 (POST /project_y/post)
- custom: 自定义请求 (任意 method + endpoint)
- rt_to_at: Refresh Token 转 Access Token
- st_to_at: Session Token 转 Access Token
- get_oai_did: 获取 oai-did (访问 chatgpt.com 获取 cookie)
"""
import os
import json
import base64
import random
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone

# iOS Safari UA
SORA_APP_USER_AGENT = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"

POW_MAX_ITERATION = 500000
POW_CORES = [8, 16, 24, 32]
POW_SCRIPTS = [
    "https://cdn.oaistatic.com/_next/static/cXh69klOLzS0Gy2joLDRS/_ssgManifest.js?dpl=453ebaec0d44c2decab71692e1bfe39be35a24b3"
]
POW_DPL = ["prod-f501fe933b3edf57aea882da888e1a544df99840"]
POW_NAVIGATOR_KEYS = [
    "registerProtocolHandler-function registerProtocolHandler() { [native code] }",
    "storage-[object StorageManager]",
    "locks-[object LockManager]",
    "appCodeName-Mozilla",
    "permissions-[object Permissions]",
    "webdriver-false",
    "vendor-Google Inc.",
    "mediaDevices-[object MediaDevices]",
    "cookieEnabled-true",
    "product-Gecko",
    "productSub-20030107",
    "hardwareConcurrency-32",
    "onLine-true",
]
POW_DOCUMENT_KEYS = ["_reactListeningo743lnnpvdg", "location"]
POW_WINDOW_KEYS = [
    "0", "window", "self", "document", "name", "location",
    "navigator", "screen", "innerWidth", "innerHeight",
    "localStorage", "sessionStorage", "crypto", "performance",
    "fetch", "setTimeout", "setInterval", "console",
]

# 需要 sentinel token 的 action 列表
SENTINEL_REQUIRED_ACTIONS = {
    "nf_create", "nf_create_storyboard", "video_gen", "post"
}

# action 到 endpoint 的映射
ACTION_ENDPOINTS = {
    "nf_create": ("POST", "/nf/create"),
    "nf_create_storyboard": ("POST", "/nf/create/storyboard"),
    "video_gen": ("POST", "/video_gen"),
    "uploads": ("POST", "/uploads"),
    "pending": ("GET", "/nf/pending/v2"),
    "me": ("GET", "/me"),
    "enhance_prompt": ("POST", "/editor/enhance_prompt"),
    "post": ("POST", "/project_y/post"),
}

# action 到 flow 的映射
ACTION_FLOWS = {
    "nf_create": "sora_2_create_task",
    "nf_create_storyboard": "sora_2_create_task",
    "video_gen": "sora_2_create_task",
    "post": "sora_2_create_task",
}


def _get_header(headers, name):
    if not headers:
        return None
    for key, value in headers.items():
        if key.lower() == name.lower():
            return value
    return None


def generate_id():
    import uuid
    return str(uuid.uuid4())


def generate_device_id():
    import uuid
    return str(uuid.uuid4())


def get_pow_parse_time():
    now = datetime.now(timezone(timedelta(hours=-5)))
    return now.strftime("%a %b %d %Y %H:%M:%S") + " GMT-0500 (Eastern Standard Time)"


def get_pow_config(user_agent):
    import time
    import uuid
    return [
        random.choice([1920 + 1080, 2560 + 1440, 1920 + 1200, 2560 + 1600]),
        get_pow_parse_time(),
        4294705152,
        0,
        user_agent,
        random.choice(POW_SCRIPTS) if POW_SCRIPTS else "",
        random.choice(POW_DPL) if POW_DPL else None,
        "en-US",
        "en-US,es-US,en,es",
        0,
        random.choice(POW_NAVIGATOR_KEYS),
        random.choice(POW_DOCUMENT_KEYS),
        random.choice(POW_WINDOW_KEYS),
        time.perf_counter() * 1000,
        str(uuid.uuid4()),
        "",
        random.choice(POW_CORES),
        time.time() * 1000 - (time.perf_counter() * 1000),
    ]


def solve_pow(seed, difficulty, config):
    import hashlib
    diff_len = len(difficulty) // 2
    seed_encoded = seed.encode()
    target_diff = bytes.fromhex(difficulty)

    static_part1 = (json.dumps(config[:3], separators=(",", ":"), ensure_ascii=False)[:-1] + ",").encode()
    static_part2 = ("," + json.dumps(config[4:9], separators=(",", ":"), ensure_ascii=False)[1:-1] + ",").encode()
    static_part3 = ("," + json.dumps(config[10:], separators=(",", ":"), ensure_ascii=False)[1:]).encode()

    for i in range(POW_MAX_ITERATION):
        dynamic_i = str(i).encode()
        dynamic_j = str(i >> 1).encode()
        final_json = static_part1 + dynamic_i + static_part2 + dynamic_j + static_part3
        b64_encoded = base64.b64encode(final_json)

        hash_value = hashlib.sha3_512(seed_encoded + b64_encoded).digest()
        if hash_value[:diff_len] <= target_diff:
            return b64_encoded.decode(), True

    error_token = "wQ8Lk5FbGpA2NcR9dShT6gYjU7VxZ4D" + base64.b64encode(f"\"{seed}\"".encode()).decode()
    return error_token, False


def get_pow_token(user_agent):
    seed = format(random.random())
    difficulty = "0fffff"
    config = get_pow_config(user_agent)
    solution, _ = solve_pow(seed, difficulty, config)
    return "gAAAAAC" + solution


def build_openai_sentinel_token(flow, resp, pow_token, user_agent):
    final_pow_token = pow_token
    proofofwork = resp.get("proofofwork", {})
    if proofofwork.get("required"):
        seed = proofofwork.get("seed", "")
        difficulty = proofofwork.get("difficulty", "")
        if seed and difficulty:
            config = get_pow_config(user_agent)
            solution, _ = solve_pow(seed, difficulty, config)
            final_pow_token = "gAAAAAB" + solution

    token_payload = {
        "p": final_pow_token,
        "t": resp.get("turnstile", {}).get("dx", ""),
        "c": resp.get("token", ""),
        "id": generate_id(),
        "flow": flow,
    }
    return json.dumps(token_payload, ensure_ascii=False, separators=(",", ":"))


def http_request(url, method="GET", payload=None, headers=None, timeout=20):
    """通用 HTTP 请求函数"""
    import gzip
    
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            resp_headers = dict(resp.headers)
            
            # 检查是否是 gzip 压缩的响应
            content_encoding = resp_headers.get("Content-Encoding", "").lower()
            if content_encoding == "gzip" or (body[:2] == b'\x1f\x8b'):
                try:
                    body = gzip.decompress(body)
                except Exception:
                    pass  # 如果解压失败，使用原始数据
            
            return resp.status, body.decode("utf-8"), resp_headers
    except urllib.error.HTTPError as e:
        body = e.read()
        resp_headers = dict(e.headers) if hasattr(e, 'headers') else {}
        
        # 检查是否是 gzip 压缩的响应
        content_encoding = resp_headers.get("Content-Encoding", "").lower()
        if content_encoding == "gzip" or (body[:2] == b'\x1f\x8b'):
            try:
                body = gzip.decompress(body)
            except Exception:
                pass
        
        return e.code, body.decode("utf-8"), resp_headers


def get_sentinel_token(token, user_agent, flow, sentinel_base):
    """获取 sentinel token"""
    pow_token = get_pow_token(user_agent)
    sentinel_req_payload = {"p": pow_token, "flow": flow, "id": generate_id()}
    sentinel_headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Origin": "https://chatgpt.com",
        "Referer": "https://chatgpt.com/",
        "User-Agent": user_agent,
        "Authorization": f"Bearer {token}",
    }
    sentinel_url = sentinel_base.rstrip("/") + "/backend-api/sentinel/req"
    status, body, _ = http_request(sentinel_url, "POST", sentinel_req_payload, sentinel_headers, timeout=10)
    
    if status != 200:
        return None, status, body
    
    sentinel_resp = json.loads(body)
    sentinel_token = build_openai_sentinel_token(flow, sentinel_resp, pow_token, user_agent)
    return sentinel_token, 200, None


def build_sora_headers(token, user_agent, sentinel_token=None, content_type="application/json", device_id=None):
    """构建 Sora API 请求头
    
    Args:
        token: Access token
        user_agent: User-Agent
        sentinel_token: openai-sentinel-token
        content_type: Content-Type
        device_id: oai-device-id 和 oai-did cookie 的值
    """
    effective_device_id = device_id or generate_device_id()
    
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://sora.chatgpt.com",
        "Referer": "https://sora.chatgpt.com/",
        "User-Agent": user_agent,
        "Authorization": f"Bearer {token}",
        "oai-device-id": effective_device_id,
        "oai-package-name": "com.openai.sora",
        "oai-client-type": "android",
        "Cookie": f"oai-did={effective_device_id}",
    }
    
    if content_type:
        headers["Content-Type"] = content_type
    
    if sentinel_token:
        headers["openai-sentinel-token"] = sentinel_token
    
    return headers


def refresh_token_to_access_token(refresh_token, client_id=None):
    """
    Refresh Token 转 Access Token
    
    Args:
        refresh_token: Refresh Token
        client_id: Client ID (可选)
    
    Returns:
        (status_code, response_body)
    """
    effective_client_id = client_id or "app_WXrF1LSkiTtfYqiL6XtjygvX"
    
    url = "https://auth.openai.com/oauth/token"
    payload = {
        "client_id": effective_client_id,
        "grant_type": "refresh_token",
        "redirect_uri": "com.openai.chat://auth0.openai.com/ios/com.openai.chat/callback",
        "refresh_token": refresh_token.strip()
    }
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    status, body, _ = http_request(url, "POST", payload, headers, timeout=30)
    return status, body


def session_token_to_access_token(session_token):
    """
    Session Token 转 Access Token
    
    Args:
        session_token: Session Token (from cookie)
    
    Returns:
        (status_code, response_body)
    """
    url = "https://sora.chatgpt.com/api/auth/session"
    headers = {
        "Cookie": f"__Secure-next-auth.session-token={session_token.strip()}",
        "Accept": "application/json",
        "Origin": "https://sora.chatgpt.com",
        "Referer": "https://sora.chatgpt.com/"
    }
    
    status, body, _ = http_request(url, "GET", None, headers, timeout=30)
    return status, body


def fetch_oai_did():
    """
    获取 oai-did (访问 chatgpt.com)
    
    Returns:
        (status_code, response_body)
        成功时 response_body 为 {"oai_did": "xxx"}
        失败时 response_body 为 {"error": "xxx"}
    """
    import re
    
    url = "https://chatgpt.com/"
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "User-Agent": SORA_APP_USER_AGENT,
    }
    
    try:
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=30) as resp:
            # 从响应头获取 set-cookie
            set_cookie = resp.headers.get("set-cookie", "")
            match = re.search(r'oai-did=([a-f0-9-]{36})', set_cookie)
            if match:
                oai_did = match.group(1)
                return 200, json.dumps({"oai_did": oai_did})
            
            # 尝试从多个 set-cookie 头获取
            cookies = resp.headers.get_all("set-cookie") or []
            for cookie in cookies:
                match = re.search(r'oai-did=([a-f0-9-]{36})', cookie)
                if match:
                    oai_did = match.group(1)
                    return 200, json.dumps({"oai_did": oai_did})
            
            return 404, json.dumps({"error": "oai-did not found in response cookies"})
            
    except urllib.error.HTTPError as e:
        # 403/429 直接返回错误
        if e.code in (403, 429):
            return e.code, json.dumps({"error": f"HTTP {e.code}: IP may be blocked or rate limited"})
        return e.code, json.dumps({"error": f"HTTP {e.code}: {str(e)}"})
    except Exception as e:
        return 500, json.dumps({"error": str(e)})


def make_sora_request(token, method, endpoint, payload=None, user_agent=None, 
                      add_sentinel=False, flow=None, sora_base=None, sentinel_base=None,
                      oai_did=None):
    """
    通用 Sora API 请求函数
    
    Args:
        token: 访问令牌
        method: HTTP 方法 (GET/POST)
        endpoint: API 端点 (如 /nf/create)
        payload: 请求体 (POST 请求)
        user_agent: 自定义 UA
        add_sentinel: 是否添加 sentinel token
        flow: sentinel flow 类型
        sora_base: Sora API 基础 URL
        sentinel_base: Sentinel API 基础 URL
        oai_did: oai-did 值 (如果未提供且需要 sentinel，则自动获取)
    
    Returns:
        (status_code, response_body, response_headers)
    """
    user_agent = user_agent or SORA_APP_USER_AGENT
    sora_base = sora_base or os.environ.get("SORA_BASE_URL", "https://sora.chatgpt.com/backend")
    sentinel_base = sentinel_base or os.environ.get("SENTINEL_BASE_URL", "https://chatgpt.com")
    flow = flow or "sora_2_create_task"
    
    # 如果需要 sentinel token 但没有提供 oai_did，先获取 oai_did
    device_id = oai_did
    if add_sentinel and not device_id:
        status, resp_body = fetch_oai_did()
        if status == 200:
            try:
                device_id = json.loads(resp_body).get("oai_did")
            except:
                pass
        if not device_id:
            # 获取失败时生成随机 ID
            device_id = generate_device_id()
    
    sentinel_token = None
    if add_sentinel:
        sentinel_token, status, error_body = get_sentinel_token(token, user_agent, flow, sentinel_base)
        if sentinel_token is None:
            return status, error_body, {}
    
    headers = build_sora_headers(token, user_agent, sentinel_token, device_id=device_id)
    url = sora_base.rstrip("/") + endpoint
    
    return http_request(url, method, payload, headers, timeout=30)


def lambda_handler(event, context):
    """Lambda 入口函数"""
    # 验证 Lambda key
    headers = event.get("headers") or {}
    expected_key = os.environ.get("LAMBDA_SHARED_KEY")
    if expected_key:
        provided_key = _get_header(headers, "x-lambda-key")
        if provided_key != expected_key:
            return {"statusCode": 401, "body": json.dumps({"error": "invalid lambda key"})}

    # 解析请求体
    body = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")
    data = json.loads(body) if body else {}

    # 获取 action，兼容旧格式
    action = data.get("action")
    if not action:
        # 兼容旧格式: 如果有 payload 或 nf_create，默认为 nf_create
        if data.get("payload") or data.get("nf_create"):
            action = "nf_create"
        else:
            return {"statusCode": 400, "body": json.dumps({"error": "action required"})}

    # 处理 rt_to_at (Refresh Token 转 Access Token)
    if action == "rt_to_at":
        refresh_token = data.get("refresh_token")
        if not refresh_token:
            return {"statusCode": 400, "body": json.dumps({"error": "refresh_token required"})}
        
        client_id = data.get("client_id")
        status, resp_body = refresh_token_to_access_token(refresh_token, client_id)
        
        return {
            "statusCode": status,
            "headers": {"Content-Type": "application/json"},
            "body": resp_body,
        }

    # 处理 st_to_at (Session Token 转 Access Token)
    if action == "st_to_at":
        session_token = data.get("session_token")
        if not session_token:
            return {"statusCode": 400, "body": json.dumps({"error": "session_token required"})}
        
        status, resp_body = session_token_to_access_token(session_token)
        
        return {
            "statusCode": status,
            "headers": {"Content-Type": "application/json"},
            "body": resp_body,
        }

    # 处理 get_oai_did (获取 oai-did)
    if action == "get_oai_did":
        status, resp_body = fetch_oai_did()
        
        return {
            "statusCode": status,
            "headers": {"Content-Type": "application/json"},
            "body": resp_body,
        }

    # 其他 action 需要 token
    token = data.get("token")
    if not token:
        return {"statusCode": 400, "body": json.dumps({"error": "token required"})}

    # 获取可选参数
    user_agent = data.get("user_agent") or SORA_APP_USER_AGENT
    sora_base = os.environ.get("SORA_BASE_URL", "https://sora.chatgpt.com/backend")
    sentinel_base = os.environ.get("SENTINEL_BASE_URL", "https://chatgpt.com")

    # 处理 custom 类型
    if action == "custom":
        method = data.get("method", "GET").upper()
        endpoint = data.get("endpoint")
        if not endpoint:
            return {"statusCode": 400, "body": json.dumps({"error": "endpoint required for custom action"})}
        
        payload = data.get("payload")
        add_sentinel = data.get("add_sentinel", False)
        flow = data.get("flow", "sora_2_create_task")
        oai_did = data.get("oai_did")  # 从请求中获取 oai_did
        
        status, resp_body, resp_headers = make_sora_request(
            token=token,
            method=method,
            endpoint=endpoint,
            payload=payload,
            user_agent=user_agent,
            add_sentinel=add_sentinel,
            flow=flow,
            sora_base=sora_base,
            sentinel_base=sentinel_base,
            oai_did=oai_did
        )
        
        return {
            "statusCode": status,
            "headers": {"Content-Type": "application/json"},
            "body": resp_body,
        }

    # 处理预定义 action
    if action not in ACTION_ENDPOINTS:
        return {"statusCode": 400, "body": json.dumps({"error": f"unknown action: {action}"})}

    method, endpoint = ACTION_ENDPOINTS[action]
    
    # 获取 payload (兼容旧格式)
    payload = data.get("payload") or data.get("nf_create")
    if method == "POST" and payload is None and action not in ("pending", "me"):
        return {"statusCode": 400, "body": json.dumps({"error": "payload required for POST action"})}

    # 判断是否需要 sentinel token
    add_sentinel = data.get("add_sentinel")
    if add_sentinel is None:
        add_sentinel = action in SENTINEL_REQUIRED_ACTIONS

    # 获取 flow
    flow = data.get("flow") or ACTION_FLOWS.get(action, "sora_2_create_task")

    # 获取 oai_did
    oai_did = data.get("oai_did")
    
    # 发起请求
    status, resp_body, resp_headers = make_sora_request(
        token=token,
        method=method,
        endpoint=endpoint,
        payload=payload,
        user_agent=user_agent,
        add_sentinel=add_sentinel,
        flow=flow,
        sora_base=sora_base,
        sentinel_base=sentinel_base,
        oai_did=oai_did
    )

    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": resp_body,
    }
