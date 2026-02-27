# Sora API Cloudflare Worker

这是 Sora API Lambda 代理的 Cloudflare Worker 版本，支持创建视频任务、token 转换等功能。

## 功能

- **nf_create**: 创建视频生成任务
- **nf_create_storyboard**: 创建分镜视频任务
- **video_gen**: 生成图片
- **uploads**: 上传图片
- **pending**: 获取待处理任务
- **me**: 获取用户信息
- **enhance_prompt**: 增强提示词
- **post**: 发布视频
- **custom**: 自定义请求
- **rt_to_at**: Refresh Token 转 Access Token
- **st_to_at**: Session Token 转 Access Token
- **get_oai_did**: 获取 oai-did

## 部署

### 1. 安装依赖

```bash
npm install
```

### 2. 安装 Wrangler CLI（如果未安装）

```bash
npm install -g wrangler
```

### 3. 登录 Cloudflare

```bash
wrangler login
```

### 4. 设置环境变量（可选）

如果需要设置共享密钥进行认证：

```bash
wrangler secret put LAMBDA_SHARED_KEY
```

### 5. 部署 Worker

```bash
npm run deploy
# 或
wrangler deploy
```

部署完成后，Worker 会运行在 `https://your-worker-name.workers.dev`

### 6. 验证部署

```bash
# 测试 get_oai_did 端点（不需要 token）
curl -X POST https://your-worker-name.workers.dev \
  -H "Content-Type: application/json" \
  -d '{"action": "get_oai_did"}'
```

## 使用示例

### 创建视频任务

```bash
curl -X POST https://your-worker.workers.dev \
  -H "Content-Type: application/json" \
  -H "x-lambda-key: your-shared-key" \
  -d '{
    "action": "nf_create",
    "token": "your-access-token",
    "payload": {
      "prompt": "A beautiful sunset over the ocean"
    }
  }'
```

### Refresh Token 转 Access Token

```bash
curl -X POST https://your-worker.workers.dev \
  -H "Content-Type: application/json" \
  -d '{
    "action": "rt_to_at",
    "refresh_token": "your-refresh-token"
  }'
```

### 获取用户信息

```bash
curl -X POST https://your-worker.workers.dev \
  -H "Content-Type: application/json" \
  -d '{
    "action": "me",
    "token": "your-access-token"
  }'
```

### 自定义请求

```bash
curl -X POST https://your-worker.workers.dev \
  -H "Content-Type: application/json" \
  -d '{
    "action": "custom",
    "token": "your-access-token",
    "method": "POST",
    "endpoint": "/nf/create",
    "payload": {
      "prompt": "Custom prompt"
    },
    "add_sentinel": true
  }'
```

## 请求参数

### 通用参数

- `action` (必填): 操作类型
- `token` (大部分操作必填): Access Token
- `user_agent` (可选): 自定义 User-Agent
- `oai_did` (可选): oai-did 值

### 针对特定 action 的参数

#### nf_create / video_gen / post 等

- `payload`: 请求体内容
- `add_sentinel` (可选): 是否添加 sentinel token，默认自动判断

#### rt_to_at

- `refresh_token` (必填): Refresh Token
- `client_id` (可选): Client ID

#### st_to_at

- `session_token` (必填): Session Token

#### custom

- `method` (可选): HTTP 方法，默认 GET
- `endpoint` (必填): API 端点
- `payload` (可选): 请求体
- `add_sentinel` (可选): 是否添加 sentinel token
- `flow` (可选): Sentinel flow 类型

## 环境变量

在 `wrangler.toml` 或 Cloudflare Dashboard 中配置：

- `LAMBDA_SHARED_KEY`: 共享密钥（用于认证）
- `SORA_BASE_URL`: Sora API 基础 URL（默认: https://sora.chatgpt.com/backend）
- `SENTINEL_BASE_URL`: Sentinel API 基础 URL（默认: https://chatgpt.com）

## 注意事项

1. **SHA3-512**: 本实现使用 `js-sha3` 库提供真正的 SHA3-512 算法支持，与 Python Lambda 版本的 hashlib.sha3_512 完全一致。

2. **CORS**: Worker 已经配置了 CORS 支持，允许跨域请求。

3. **超时**: 请求超时设置为 30 秒。注意 Cloudflare Workers 的 CPU 时间限制（免费版 10ms，付费版 50ms），但网络请求时间不计入 CPU 时间。

## 与 Lambda 版本的差异

1. 使用 JavaScript 代替 Python
2. 使用 Fetch API 代替 urllib
3. 使用 js-sha3 库实现 SHA3-512，与 Python 版本算法一致
4. 添加了 CORS 支持
5. 使用环境变量通过 `env` 对象访问

## 依赖

- `js-sha3`: 提供 SHA3-512 哈希算法支持

## 开发和测试

本地测试：

```bash
wrangler dev
```

这会在本地启动一个开发服务器，默认地址为 http://localhost:8787
