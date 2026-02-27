/**
 * 通用 Sora API Cloudflare Worker 代理
 *
 * 支持的请求类型:
 * - nf_create: 创建视频生成任务 (POST /nf/create)
 * - nf_create_storyboard: 创建分镜视频任务 (POST /nf/create/storyboard)
 * - video_gen: 生成图片 (POST /video_gen)
 * - uploads: 上传图片 (POST /uploads)
 * - pending: 获取待处理任务 (GET /nf/pending/v2)
 * - me: 获取用户信息 (GET /me)
 * - enhance_prompt: 增强提示词 (POST /editor/enhance_prompt)
 * - post: 发布视频 (POST /project_y/post)
 * - custom: 自定义请求 (任意 method + endpoint)
 * - rt_to_at: Refresh Token 转 Access Token
 * - st_to_at: Session Token 转 Access Token
 * - get_oai_did: 获取 oai-did (访问 chatgpt.com 获取 cookie)
 */

import { sha3_512 } from 'js-sha3';

// iOS Safari UA
const SORA_APP_USER_AGENT = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1";

const POW_MAX_ITERATION = 500000;
const POW_CORES = [8, 16, 24, 32];
const POW_SCRIPTS = [
    "https://cdn.oaistatic.com/_next/static/cXh69klOLzS0Gy2joLDRS/_ssgManifest.js?dpl=453ebaec0d44c2decab71692e1bfe39be35a24b3"
];
const POW_DPL = ["prod-f501fe933b3edf57aea882da888e1a544df99840"];
const POW_NAVIGATOR_KEYS = [
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
];
const POW_DOCUMENT_KEYS = ["_reactListeningo743lnnpvdg", "location"];
const POW_WINDOW_KEYS = [
    "0", "window", "self", "document", "name", "location",
    "navigator", "screen", "innerWidth", "innerHeight",
    "localStorage", "sessionStorage", "crypto", "performance",
    "fetch", "setTimeout", "setInterval", "console",
];

// 需要 sentinel token 的 action 列表
const SENTINEL_REQUIRED_ACTIONS = new Set([
    "nf_create", "nf_create_storyboard", "video_gen", "post"
]);

// action 到 endpoint 的映射
const ACTION_ENDPOINTS = {
    "nf_create": ["POST", "/nf/create"],
    "nf_create_storyboard": ["POST", "/nf/create/storyboard"],
    "video_gen": ["POST", "/video_gen"],
    "uploads": ["POST", "/uploads"],
    "pending": ["GET", "/nf/pending/v2"],
    "me": ["GET", "/me"],
    "enhance_prompt": ["POST", "/editor/enhance_prompt"],
    "post": ["POST", "/project_y/post"],
};

// action 到 flow 的映射
const ACTION_FLOWS = {
    "nf_create": "sora_2_create_task",
    "nf_create_storyboard": "sora_2_create_task",
    "video_gen": "sora_2_create_task",
    "post": "sora_2_create_task",
};

function generateId() {
    return crypto.randomUUID();
}

function generateDeviceId() {
    return crypto.randomUUID();
}

function getPowParseTime() {
    const now = new Date();
    const estTime = new Date(now.toLocaleString('en-US', { timeZone: 'America/New_York' }));
    const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

    const day = days[estTime.getDay()];
    const month = months[estTime.getMonth()];
    const date = estTime.getDate();
    const year = estTime.getFullYear();
    const hours = String(estTime.getHours()).padStart(2, '0');
    const minutes = String(estTime.getMinutes()).padStart(2, '0');
    const seconds = String(estTime.getSeconds()).padStart(2, '0');

    return `${day} ${month} ${date} ${year} ${hours}:${minutes}:${seconds} GMT-0500 (Eastern Standard Time)`;
}

function randomChoice(arr) {
    return arr[Math.floor(Math.random() * arr.length)];
}

function getPowConfig(userAgent) {
    return [
        randomChoice([1920 + 1080, 2560 + 1440, 1920 + 1200, 2560 + 1600]),
        getPowParseTime(),
        4294705152,
        0,
        userAgent,
        POW_SCRIPTS.length > 0 ? randomChoice(POW_SCRIPTS) : "",
        POW_DPL.length > 0 ? randomChoice(POW_DPL) : null,
        "en-US",
        "en-US,es-US,en,es",
        0,
        randomChoice(POW_NAVIGATOR_KEYS),
        randomChoice(POW_DOCUMENT_KEYS),
        randomChoice(POW_WINDOW_KEYS),
        performance.now(),
        crypto.randomUUID(),
        "",
        randomChoice(POW_CORES),
        Date.now() - performance.now(),
    ];
}

function hashSha3512(data) {
    // 使用 js-sha3 库的真正 SHA3-512
    const hash = sha3_512(data);
    // 将十六进制字符串转换为 Uint8Array
    const hashArray = new Uint8Array(hash.length / 2);
    for (let i = 0; i < hash.length; i += 2) {
        hashArray[i / 2] = parseInt(hash.substring(i, i + 2), 16);
    }
    return hashArray;
}

function solvePow(seed, difficulty, config) {
    const diffLen = difficulty.length / 2;
    const targetDiff = new Uint8Array(diffLen);
    for (let i = 0; i < diffLen; i++) {
        targetDiff[i] = parseInt(difficulty.substring(i * 2, i * 2 + 2), 16);
    }

    const staticPart1 = JSON.stringify(config.slice(0, 3)).slice(0, -1) + ",";
    const staticPart2 = "," + JSON.stringify(config.slice(4, 9)).slice(1, -1) + ",";
    const staticPart3 = "," + JSON.stringify(config.slice(10)).slice(1);

    for (let i = 0; i < POW_MAX_ITERATION; i++) {
        const dynamicI = String(i);
        const dynamicJ = String(i >> 1);
        const finalJson = staticPart1 + dynamicI + staticPart2 + dynamicJ + staticPart3;
        const b64Encoded = btoa(finalJson);

        const hashValue = hashSha3512(seed + b64Encoded);

        let match = true;
        for (let j = 0; j < diffLen; j++) {
            if (hashValue[j] > targetDiff[j]) {
                match = false;
                break;
            } else if (hashValue[j] < targetDiff[j]) {
                break;
            }
        }

        if (match) {
            return [b64Encoded, true];
        }
    }

    const errorToken = "wQ8Lk5FbGpA2NcR9dShT6gYjU7VxZ4D" + btoa(JSON.stringify(seed));
    return [errorToken, false];
}

function getPowToken(userAgent) {
    const seed = String(Math.random());
    const difficulty = "0fffff";
    const config = getPowConfig(userAgent);
    const [solution] = solvePow(seed, difficulty, config);
    return "gAAAAAC" + solution;
}

function buildOpenaiSentinelToken(flow, resp, powToken, userAgent) {
    let finalPowToken = powToken;
    const proofofwork = resp.proofofwork || {};

    if (proofofwork.required) {
        const seed = proofofwork.seed || "";
        const difficulty = proofofwork.difficulty || "";
        if (seed && difficulty) {
            const config = getPowConfig(userAgent);
            const [solution] = solvePow(seed, difficulty, config);
            finalPowToken = "gAAAAAB" + solution;
        }
    }

    const tokenPayload = {
        p: finalPowToken,
        t: (resp.turnstile || {}).dx || "",
        c: resp.token || "",
        id: generateId(),
        flow: flow,
    };

    return JSON.stringify(tokenPayload);
}

async function httpRequest(url, method = "GET", payload = null, headers = {}, timeout = 20000) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
        const options = {
            method: method,
            headers: headers,
            signal: controller.signal,
        };

        if (payload !== null) {
            options.body = JSON.stringify(payload);
        }

        const response = await fetch(url, options);
        clearTimeout(timeoutId);

        const body = await response.text();
        const respHeaders = Object.fromEntries(response.headers.entries());

        return {
            status: response.status,
            body: body,
            headers: respHeaders
        };
    } catch (error) {
        clearTimeout(timeoutId);
        throw error;
    }
}

async function getSentinelToken(token, userAgent, flow, sentinelBase) {
    const powToken = getPowToken(userAgent);
    const sentinelReqPayload = { p: powToken, flow: flow, id: generateId() };
    const sentinelHeaders = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Origin": "https://chatgpt.com",
        "Referer": "https://chatgpt.com/",
        "User-Agent": userAgent,
        "Authorization": `Bearer ${token}`,
    };

    const sentinelUrl = sentinelBase.replace(/\/$/, '') + "/backend-api/sentinel/req";

    try {
        const { status, body } = await httpRequest(sentinelUrl, "POST", sentinelReqPayload, sentinelHeaders, 10000);

        if (status !== 200) {
            return { sentinelToken: null, status, error: body };
        }

        const sentinelResp = JSON.parse(body);
        const sentinelToken = buildOpenaiSentinelToken(flow, sentinelResp, powToken, userAgent);
        return { sentinelToken, status: 200, error: null };
    } catch (error) {
        return { sentinelToken: null, status: 500, error: error.message };
    }
}

function buildSoraHeaders(token, userAgent, sentinelToken = null, contentType = "application/json", deviceId = null) {
    const effectiveDeviceId = deviceId || generateDeviceId();

    const headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://sora.chatgpt.com",
        "Referer": "https://sora.chatgpt.com/",
        "User-Agent": userAgent,
        "Authorization": `Bearer ${token}`,
        "oai-device-id": effectiveDeviceId,
        "oai-package-name": "com.openai.sora",
        "oai-client-type": "android",
        "Cookie": `oai-did=${effectiveDeviceId}`,
    };

    if (contentType) {
        headers["Content-Type"] = contentType;
    }

    if (sentinelToken) {
        headers["openai-sentinel-token"] = sentinelToken;
    }

    return headers;
}

async function refreshTokenToAccessToken(refreshToken, clientId = null) {
    const effectiveClientId = clientId || "app_LlGpXReQgckcGGUo2JrYvtJK";

    const url = "https://auth.openai.com/oauth/token";
    const payload = {
        client_id: effectiveClientId,
        grant_type: "refresh_token",
        redirect_uri: "com.openai.chat://auth0.openai.com/ios/com.openai.chat/callback",
        refresh_token: refreshToken.trim()
    };
    const headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    };

    const { status, body } = await httpRequest(url, "POST", payload, headers, 30000);
    return { status, body };
}

async function sessionTokenToAccessToken(sessionToken) {
    const url = "https://sora.chatgpt.com/api/auth/session";
    const headers = {
        "Cookie": `__Secure-next-auth.session-token=${sessionToken.trim()}`,
        "Accept": "application/json",
        "Origin": "https://sora.chatgpt.com",
        "Referer": "https://sora.chatgpt.com/"
    };

    const { status, body } = await httpRequest(url, "GET", null, headers, 30000);
    return { status, body };
}

async function fetchOaiDid() {
    const url = "https://chatgpt.com/";
    const headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "User-Agent": SORA_APP_USER_AGENT,
    };

    try {
        const response = await fetch(url, { method: "GET", headers });
        const setCookie = response.headers.get("set-cookie") || "";
        const match = setCookie.match(/oai-did=([a-f0-9-]{36})/);

        if (match) {
            return { status: 200, body: JSON.stringify({ oai_did: match[1] }) };
        }

        return { status: 404, body: JSON.stringify({ error: "oai-did not found in response cookies" }) };
    } catch (error) {
        if (error.status === 403 || error.status === 429) {
            return { status: error.status, body: JSON.stringify({ error: `HTTP ${error.status}: IP may be blocked or rate limited` }) };
        }
        return { status: 500, body: JSON.stringify({ error: error.message }) };
    }
}

async function makeSoraRequest(token, method, endpoint, payload = null, userAgent = null,
                               addSentinel = false, flow = null, soraBase = null,
                               sentinelBase = null, oaiDid = null) {
    console.log('[makeSoraRequest] Called with:', { method, endpoint, addSentinel, flow });

    userAgent = userAgent || SORA_APP_USER_AGENT;
    soraBase = soraBase || "https://sora.chatgpt.com/backend";
    sentinelBase = sentinelBase || "https://chatgpt.com";
    flow = flow || "sora_2_create_task";

    let deviceId = oaiDid;
    if (addSentinel && !deviceId) {
        console.log('[makeSoraRequest] Fetching oai-did...');
        const { status, body } = await fetchOaiDid();
        if (status === 200) {
            try {
                deviceId = JSON.parse(body).oai_did;
                console.log('[makeSoraRequest] Got oai-did:', deviceId);
            } catch (e) {
                console.error('[makeSoraRequest] Failed to parse oai-did:', e);
            }
        }
        if (!deviceId) {
            deviceId = generateDeviceId();
            console.log('[makeSoraRequest] Generated device ID:', deviceId);
        }
    }

    let sentinelToken = null;
    if (addSentinel) {
        console.log('[makeSoraRequest] Getting sentinel token...');
        const result = await getSentinelToken(token, userAgent, flow, sentinelBase);
        if (result.sentinelToken === null) {
            console.error('[makeSoraRequest] Failed to get sentinel token:', result.status, result.error);
            return { status: result.status, body: result.error, headers: {} };
        }
        sentinelToken = result.sentinelToken;
        console.log('[makeSoraRequest] Got sentinel token');
    }

    const headers = buildSoraHeaders(token, userAgent, sentinelToken, "application/json", deviceId);
    const url = soraBase.replace(/\/$/, '') + endpoint;

    console.log('[makeSoraRequest] Making request to:', url);
    console.log('[makeSoraRequest] Request headers:', JSON.stringify(headers, null, 2));
    if (payload) {
        console.log('[makeSoraRequest] Request payload:', JSON.stringify(payload).substring(0, 500));
    }
    const { status, body, headers: respHeaders } = await httpRequest(url, method, payload, headers, 30000);
    console.log('[makeSoraRequest] Response status:', status, 'body length:', body.length);
    if (status >= 400) {
        console.error('[makeSoraRequest] Error response body:', body);
    }
    return { status, body, headers: respHeaders };
}

export default {
    async fetch(request, env, ctx) {
        // CORS headers
        const corsHeaders = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, x-lambda-key',
        };

        // Handle CORS preflight
        if (request.method === 'OPTIONS') {
            return new Response(null, { headers: corsHeaders });
        }

        try {
            console.log('[Worker] Request received:', request.method, request.url);

            // 验证 shared key
            const expectedKey = env.LAMBDA_SHARED_KEY;
            if (expectedKey) {
                const providedKey = request.headers.get("x-lambda-key");
                if (providedKey !== expectedKey) {
                    console.error('[Worker] Invalid lambda key');
                    return new Response(JSON.stringify({ error: "invalid lambda key" }), {
                        status: 401,
                        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
                    });
                }
            }

            // 解析请求体
            let data = {};
            try {
                const text = await request.text();
                console.log('[Worker] Request body length:', text.length);
                if (text) {
                    data = JSON.parse(text);
                    console.log('[Worker] Parsed data, action:', data.action);
                }
            } catch (e) {
                console.error('[Worker] JSON parse error:', e.message);
                return new Response(JSON.stringify({ error: "invalid JSON body", detail: e.message }), {
                    status: 400,
                    headers: { ...corsHeaders, 'Content-Type': 'application/json' }
                });
            }

            // 获取 action
            let action = data.action;
            if (!action) {
                if (data.payload || data.nf_create) {
                    action = "nf_create";
                } else {
                    return new Response(JSON.stringify({ error: "action required" }), {
                        status: 400,
                        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
                    });
                }
            }

            // 处理 rt_to_at
            if (action === "rt_to_at") {
                const refreshToken = data.refresh_token;
                if (!refreshToken) {
                    return new Response(JSON.stringify({ error: "refresh_token required" }), {
                        status: 400,
                        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
                    });
                }

                const clientId = data.client_id;
                const { status, body } = await refreshTokenToAccessToken(refreshToken, clientId);

                return new Response(body, {
                    status: status,
                    headers: { ...corsHeaders, 'Content-Type': 'application/json' }
                });
            }

            // 处理 st_to_at
            if (action === "st_to_at") {
                const sessionToken = data.session_token;
                if (!sessionToken) {
                    return new Response(JSON.stringify({ error: "session_token required" }), {
                        status: 400,
                        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
                    });
                }

                const { status, body } = await sessionTokenToAccessToken(sessionToken);

                return new Response(body, {
                    status: status,
                    headers: { ...corsHeaders, 'Content-Type': 'application/json' }
                });
            }

            // 处理 get_oai_did
            if (action === "get_oai_did") {
                const { status, body } = await fetchOaiDid();

                return new Response(body, {
                    status: status,
                    headers: { ...corsHeaders, 'Content-Type': 'application/json' }
                });
            }

            // 其他 action 需要 token
            const token = data.token;
            if (!token) {
                console.error('[Worker] Token required for action:', action);
                return new Response(JSON.stringify({ error: "token required" }), {
                    status: 400,
                    headers: { ...corsHeaders, 'Content-Type': 'application/json' }
                });
            }

            console.log('[Worker] Processing action:', action, 'with token length:', token.length);

            // 获取可选参数
            const userAgent = data.user_agent || SORA_APP_USER_AGENT;
            const soraBase = env.SORA_BASE_URL || "https://sora.chatgpt.com/backend";
            const sentinelBase = env.SENTINEL_BASE_URL || "https://chatgpt.com";

            // 处理 custom 类型
            if (action === "custom") {
                const method = (data.method || "GET").toUpperCase();
                const endpoint = data.endpoint;
                if (!endpoint) {
                    return new Response(JSON.stringify({ error: "endpoint required for custom action" }), {
                        status: 400,
                        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
                    });
                }

                const payload = data.payload;
                const addSentinel = data.add_sentinel || false;
                const flow = data.flow || "sora_2_create_task";
                const oaiDid = data.oai_did;

                const { status, body } = await makeSoraRequest(
                    token, method, endpoint, payload, userAgent,
                    addSentinel, flow, soraBase, sentinelBase, oaiDid
                );

                return new Response(body, {
                    status: status,
                    headers: { ...corsHeaders, 'Content-Type': 'application/json' }
                });
            }

            // 处理预定义 action
            if (!ACTION_ENDPOINTS[action]) {
                return new Response(JSON.stringify({ error: `unknown action: ${action}` }), {
                    status: 400,
                    headers: { ...corsHeaders, 'Content-Type': 'application/json' }
                });
            }

            const [method, endpoint] = ACTION_ENDPOINTS[action];

            // 获取 payload
            let payload = data.payload || data.nf_create;
            if (method === "POST" && payload === undefined && action !== "pending" && action !== "me") {
                return new Response(JSON.stringify({ error: "payload required for POST action" }), {
                    status: 400,
                    headers: { ...corsHeaders, 'Content-Type': 'application/json' }
                });
            }

            // 判断是否需要 sentinel token
            let addSentinel = data.add_sentinel;
            if (addSentinel === undefined) {
                addSentinel = SENTINEL_REQUIRED_ACTIONS.has(action);
            }

            // 获取 flow
            const flow = data.flow || ACTION_FLOWS[action] || "sora_2_create_task";

            // 获取 oai_did
            const oaiDid = data.oai_did;

            // 发起请求
            const { status, body } = await makeSoraRequest(
                token, method, endpoint, payload, userAgent,
                addSentinel, flow, soraBase, sentinelBase, oaiDid
            );

            return new Response(body, {
                status: status,
                headers: { ...corsHeaders, 'Content-Type': 'application/json' }
            });

        } catch (error) {
            console.error('[Worker] Fatal error:', error);
            console.error('[Worker] Error stack:', error.stack);
            return new Response(JSON.stringify({
                error: error.message,
                stack: error.stack,
                type: error.name
            }), {
                status: 500,
                headers: { ...corsHeaders, 'Content-Type': 'application/json' }
            });
        }
    }
};
