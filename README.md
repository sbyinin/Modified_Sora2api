# 本项目二次开发基于 [sora2api](https://github.com/TheSmallHanCat/sora2api)

##### 原作者: [TheSmallHanCat](https://github.com/TheSmallHanCat)

# 该项目是二开的项目请谨慎使用

---

## 项目介绍

Sora2API 是一个 OpenAI 兼容的 Sora API 服务，支持文生图、文生视频、图生视频、视频 Remix、角色创建等功能，提供流式进度与任务状态查询。

**✅ 已兼容 [new-api](https://github.com/Calcium-Ion/new-api) sora2 渠道对接格式**

### 主要功能

- 文生图片 / 图生图片
- 文生视频 / 图生视频
- 视频 Remix（基于已有视频二次创作）
- 视频分镜（Storyboard）
- 角色卡创建与引用
- 图生角色卡（图 -> 角色卡，内部走图生视频 + generation_id）
- OpenAI `/v1/chat/completions` 兼容（SSE 流式输出）
- 任务进度查询（pending/v2 + task_id）
- Token 池管理与自动轮询
- 代理配置（支持单代理和代理池轮询）
- 代理池检测（自动检测并移除无效代理）
- 无水印模式
- 任务日志与进度追踪（管理后台可查看）
- 管理后台

### 批量操作功能

- 批量添加 Token（支持重复检测）
- 批量测试 Token（自动启用/禁用）
- 批量激活 Sora2（使用邀请码）
- 批量启用/禁用 Token
- 批量删除禁用 Token

### 性能优化

- 自适应轮询机制（根据进度动态调整间隔）
- 停滞检测（避免无效请求）
- 并发控制（token 级别图片/视频并发限制）
- Token 缓存（减少数据库查询）
- Token 轮询（按可用账号顺序轮询，不随机）
- 任务进度写入数据库（日志可实时展示）

---

## new-api 对接说明

本项目的 `/v1/videos` 接口已完全兼容 new-api 的 sora2 渠道格式。

### 配置方式

在 new-api 中添加渠道：
- **类型**: Sora
- **Base URL**: `http://your-sora2api-server:8000`
- **密钥**: 你的 API Key（默认 `han1234`）
- **模型**: `sora-2`, `sora-2-pro`

### 支持的接口

| 接口 | 描述 |
|------|------|
| `POST /v1/videos` | 创建视频生成任务 |
| `GET /v1/videos/{id}` | 获取任务状态 |
| `GET /v1/videos/{id}/content` | 获取视频直链（302 重定向） |
| `POST /v1/videos/{id}/remix` | 视频 Remix |

### 响应格式

```json
{
  "id": "sora-2-abc123def456",
  "object": "video",
  "model": "sora-2",
  "status": "in_progress",
  "progress": 50,
  "created_at": 1702388400,
  "completed_at": 1702388500,
  "seconds": "10",
  "size": "1280x720",
  "error": null
}
```

### 状态值

| 状态 | 描述 |
|------|------|
| `queued` | 排队中 |
| `in_progress` | 处理中 |
| `completed` | 成功 |
| `failed` | 失败 |
| `cancelled` | Client disconnected |

Note: `cancelled` indicates the client disconnected before completion. `request_logs.status_code` is set to 499.

---

## 快速开始

```bash
# Docker 部署
docker-compose up -d

# 本地部署
pip install -r requirements.txt
python main.py
```

**管理后台**: http://localhost:8000/login (默认账号: admin/admin)

**默认 API Key**: `han1234`

---

## Token 轮询策略

生成请求会按**可用 Token 列表**进行轮询（Round-Robin），每个可用账号都使用一次后再从头开始。

- 轮询顺序：按 `token.id` 排序
- 过滤规则：未启用、冷却中、并发/锁不可用的 Token 会被跳过
- 被跳过的 Token 在恢复可用后会自动加入下一轮

---

## 并发与连接池调优（避免 Too many open files）

在 `config/setting.toml` 中可以限制并发与连接池规模，避免高并发下句柄耗尽：

```toml
[lambda]
enabled = false
api_url = ""
api_key = ""
max_concurrency = 5
max_connections = 20
max_keepalive_connections = 10
keepalive_expiry = 20
timeout = 30

[cache]
enabled = false
timeout = 600
base_url = "http://127.0.0.1:8000"
max_concurrency = 3

[watermark_free]
watermark_free_enabled = true
parse_method = "builtin"
custom_parse_url = ""
custom_parse_token = ""
max_concurrency = 2
```

### 参数说明

**[lambda]**
- `enabled`: 是否启用 Lambda 代理。`false` 时以下参数不生效。
- `api_url`/`api_key`: 你的 Lambda 端点与密钥（启用时必填）。
- `max_concurrency`: Lambda 代理请求的**全局并发上限**（每个进程）。越小越稳，越大吞吐越高但更易耗尽 FD。
- `max_connections`: httpx 连接池**最大连接数上限**。建议 ≥ `max_concurrency`。
- `max_keepalive_connections`: 连接池**保留的空闲连接上限**。建议 ≤ `max_connections`。
- `keepalive_expiry`: 空闲连接保活时间（秒）。适当增大可减少频繁建连。
- `timeout`: 单次 Lambda 请求超时时间（秒）。

**[cache]**
- `max_concurrency`: 缓存下载并发上限（单位：并发下载数）。限制下载阶段占用的 socket/句柄。

**[watermark_free]**
- `max_concurrency`: 去水印“解析阶段”的并发上限（单位：并发解析数）。仅限制解析/查询，不影响生成任务本身。

### 200 并发示例（仅针对 Lambda 代理请求）

如果你确实走 Lambda 且要让 200 个请求同时发起，可这样设置（**每个进程**）：

```toml
[lambda]
enabled = true
api_url = "https://your-lambda-endpoint"
api_key = "your-key"
max_concurrency = 200
max_connections = 220
max_keepalive_connections = 100
keepalive_expiry = 20
timeout = 30
```

注意：若 `enabled = false`，这些参数不影响直连 Sora 的请求并发。

建议：
1. 多 worker 部署时，按 worker 数量等比例下调并发参数。
2. 压测时优先调小 `max_concurrency`，再逐步增大。

补充说明：
- 实际可同时处理的视频任务数 ≈ 可用 Token 数 × 每个 Token 的 `video_concurrency`（默认 `-1` 表示不限制）。
- 即使 Token 足够，仍受单进程 FD/CPU/内存约束；建议先设每 token 并发为 `1`，再逐步加大。

### 常见问题：能否同时提交 200 个视频任务？

- 可以提交 200 个请求，但是否能**同时在跑**取决于可用 Token 数量与每个 Token 的 `video_concurrency`。
- 如果你有 200 个可用 Token 且每个 Token 的 `video_concurrency >= 1`，理论上可以同时跑 200 个任务（仍受机器资源限制）。
- 若可用 Token 不足或并发限制更低，超出的请求会返回 “No available tokens...” 而不是自动排队。
- 当 `[lambda].enabled = false` 时，`max_concurrency/max_connections/...` **不生效**；直连 Sora 的并发由 Token 和机器资源决定。

---

## 从视频生成到角色卡（粘性 token）

流程:
1. 调用 `/v1/videos` 创建视频任务。
2. 任务完成后，从 `GET /v1/videos/{id}` 的 `metadata.generation_id` 获取 `gen_xxx`。
3. 调用 `/v1/characters/from-generation` 创建角色卡（可选传 `timestamps`、`username` 等）。

说明:
- 该流程使用 **粘性 token**：角色卡创建会绑定到创建该 `generation_id` 的同一账号。
- `timestamps` 支持 `"0,4"` 或 `[0,4]`。

---

## 从图片生成到角色卡（粘性 token）

方式 1（直接接口）:
1. 调用 `/v1/characters` 并传 `input_reference` 或 `input_image`。
2. 服务端会先进行图生视频，拿到 `generation_id` 后再创建角色卡。

方式 2（Chat）:
1. 调用 `/v1/chat/completions`，传 `image` + `character_options`。
2. 返回格式保持标准 Chat（SSE 流式），最终输出角色卡结果。

说明:
- 该流程同样使用 **粘性 token**（图生视频与角色卡创建使用同一账号）。

---

## 项目结构

```
├── config/                 # 配置文件
│   ├── setting.toml       # 主配置文件
│   └── setting_warp.toml  # Warp 配置
├── data/                   # 数据目录
│   ├── hancat.db          # SQLite 数据库
│   └── proxy.txt          # 代理池配置（每行一个代理地址）
├── docs/                   # API 文档
│   └── API_V1_DOCUMENTATION.md # v1 API 文档
├── src/                    # 源代码
│   ├── api/               # API 路由
│   │   ├── admin.py       # 管理接口
│   │   ├── openai_compat.py # OpenAI 兼容接口
│   │   ├── public.py      # 公共接口
│   │   ├── routes.py      # 路由注册
│   │   └── sora_compat.py # Sora 兼容接口
│   ├── core/              # 核心模块
│   │   ├── auth.py        # 认证
│   │   ├── config.py      # 配置管理
│   │   ├── database.py    # 数据库
│   │   ├── logger.py      # 日志
│   │   └── models.py      # 数据模型
│   └── services/          # 业务服务
│       ├── generation_handler.py # 生成处理
│       ├── concurrency_manager.py # 并发控制
│       ├── load_balancer.py      # 负载均衡/令牌选择
│       ├── file_cache.py         # 文件缓存
│       ├── cloudflare_solver.py  # CF Solver 支持
│       ├── proxy_manager.py      # 代理管理
│       ├── sora_client.py        # Sora 客户端
│       ├── token_cache.py        # Token 缓存
│       ├── token_lock.py         # Token 锁
│       └── token_manager.py      # Token 管理
├── static/                 # 静态文件
│   ├── login.html         # 登录页面
│   └── manage.html        # 管理后台
├── tests/                  # 测试脚本
├── docker-compose.yml      # Docker 配置
├── Dockerfile             # Docker 镜像
├── main.py                # 入口文件
└── requirements.txt       # 依赖
```

---

## 代理池配置

在 `data/proxy.txt` 中配置代理列表，每行一个：

```
# 支持格式
http://ip:port
http://user:pass@ip:port
socks5://ip:port
ip:port
ip:port:user:pass
```

**使用逻辑：**
1. 在管理后台启用 `代理` 和 `代理池` 开关
2. 每次请求 Sora API 时，自动轮询使用下一个代理
3. 代理池为空时，回退到单代理配置
4. 修改 `proxy.txt` 后，在管理后台点击"重载代理池"生效

---

## API 文档

详细 API 文档请参考：
- [v1 接口文档](docs/API_V1_DOCUMENTATION.md) - 完整的 v1 API 接口文档（new-api 兼容）

### 主要接口

| 接口 | 方法 | 描述 |
|------|------|------|
| `/v1/models` | GET | 获取可用模型列表 |
| `/v1/chat/completions` | POST | 统一聊天补全接口（支持流式） |
| `/v1/videos` | POST | 创建视频生成任务（new-api 兼容） |
| `/v1/videos/{id}` | GET | 获取视频任务状态（new-api 兼容） |
| `/v1/videos/{id}/content` | GET | 获取视频直链（302 重定向） |
| `/v1/videos/{id}/remix` | POST | 视频 Remix（new-api 兼容） |
| `/v1/images/generations` | POST | 图片生成 |
| `/v1/characters` | POST | 角色创建 |
| `/v1/characters/from-generation` | POST | 从 generation_id 创建角色 |
| `/v1/enhance_prompt` | POST | 提示词增强 |
| `/v1/tokens/{token_id}/pending-tasks` | GET | 任务列表（v1） |
| `/v1/tokens/{token_id}/pending-tasks-v2` | GET | 任务列表（v2，含进度） |
| `/v1/tokens/{token_id}/tasks/{task_id}` | GET | 任务进度查询 |
| `/v1/stats` | GET | 系统统计 |
| `/v1/feed` | GET | 公共 Feed |
| `/api/tokens` | GET/POST | Token 管理 |
| `/api/login` | POST | 管理员登录 |
| `/api/logs` | GET | 请求日志（含任务状态/进度） |
| `/api/proxy/config` | GET/POST | 代理配置 |
| `/api/watermark-free/config` | GET/POST | 无水印配置 |
| `/api/cache/config` | GET/POST | 缓存配置 |
| `/api/cloudflare/config` | GET/POST | Cloudflare Solver 配置 |

---

## 许可证

MIT License
