# AI 人生重开模拟器

基于 `FastAPI + Vue 3 + Vite + Pinia + Tailwind CSS` 的全栈 AI 人生模拟项目，支持用户鉴权、管理员配额管理、自定义模型接入、Prompt 注入拦截、速率限制与本地一键联调。

当前仓库已经完成以下关键能力的工程化改造：

- 后端采用应用工厂、路由/服务/仓储分层、异步 SQLite 会话与配置预热。
- 前端采用组合式 API、页面逻辑拆分为 composables 与无状态组件。
- 本地开发支持 `uv run python main.py` 一键拉起后端与 Vite。
- 生产环境支持在 FastAPI 中挂载 `frontend/dist` 静态产物。
- 已补充基础测试基线、Swagger/OpenAPI 文档与部署说明。

## 1. 技术栈

- 后端：`FastAPI`、`SQLModel`、`SQLAlchemy Async`、`aiosqlite`、`LiteLLM`
- 前端：`Vue 3`、`Vite`、`Pinia`、`Vue Router`、`Tailwind CSS`
- 安全：`PyJWT`、`bcrypt`、`cryptography(Fernet)`、速率限制、HTTPS 强制中间件
- 工具链：`uv`、`pytest`、`pytest-asyncio`、`ruff`

## 2. 项目结构

```text
.
├── app/
│   ├── api/                 # 路由入口
│   ├── core/                # 配置、安全、中间件、依赖
│   ├── db/                  # 数据库会话与初始化
│   ├── models/              # 数据模型
│   ├── repositories/        # 数据访问层
│   ├── schemas/             # Pydantic V2 请求/响应模型
│   └── services/            # 业务服务层
├── config/
│   ├── app_config.template.toml
│   ├── app_config.toml
│   ├── world_config.template.toml
│   └── world_config.toml
├── data/                    # SQLite 数据文件目录
├── frontend/                # Vue 3 前端工程
├── tests/                   # 基础自动化测试
├── .env.example             # 环境变量模板
├── main.py                  # 本地开发联调入口
├── pyproject.toml           # Python 项目清单
└── API文档.md               # 人工维护的业务 API 文档
```

## 3. 运行环境

最低要求：

- Python `3.11+`
- Node.js `20+`
- npm `10+`
- `uv`

建议优先使用 `uv` 管理 Python 环境，不再使用 `requirements.txt` 流程。

## 4. 安装步骤

### 4.1 克隆仓库

```bash
git clone <your-repo-url>
cd life-restart
```

### 4.2 安装后端依赖

```bash
uv sync
```

如需开发与测试依赖：

```bash
uv sync --extra dev
```

### 4.3 安装前端依赖

```bash
cd frontend
npm install
cd ..
```

## 5. 配置说明

项目配置分为 3 层：

1. `.env`
2. `config/app_config.toml`
3. `config/world_config.toml`

其中 `config/*.toml` 会在启动时依据模板自动创建/同步字段结构，但不会替你填安全密钥或真实模型配置。

### 5.1 `.env`

先复制模板：

```bash
cp .env.example .env
```

Windows PowerShell：

```powershell
Copy-Item .env.example .env
```

关键变量如下：

| 变量 | 必填 | 说明 |
| --- | --- | --- |
| `ENVIRONMENT` | 是 | `development` / `testing` / `staging` / `production` |
| `APP_HOST` | 是 | 后端监听地址，开发常用 `127.0.0.1`，部署常用 `0.0.0.0` |
| `APP_PORT` | 是 | 后端端口，当前模板默认 `8100` |
| `DATABASE_URL` | 是 | 当前默认 SQLite：`sqlite:///./data/life_simulator.db` |
| `SECRET_KEY` | 是 | JWT 密钥，至少 32 字符 |
| `USER_DATA_ENCRYPTION_SECRET` | 是 | 用户自定义 API Key 加密密钥，至少 32 字符 |
| `FRONTEND_DEV_ORIGIN` | 开发必填 | Vite 开发地址，默认 `http://127.0.0.1:8101` |
| `FRONTEND_PUBLIC_ORIGIN` | 生产必填 | 生产环境前端公开访问地址 |
| `ALLOWED_ORIGINS` | 建议配置 | 逗号分隔的 CORS 白名单 |
| `ENFORCE_HTTPS` | 生产建议开启 | 开启后只允许 HTTPS 请求访问 API |
| `TRUST_X_FORWARDED_PROTO` | 反代场景建议开启 | 信任代理传入的协议头 |
| `TRUST_X_FORWARDED_FOR` | 按需开启 | 信任代理传入的客户端 IP |
| `START_FRONTEND_WITH_BACKEND` | 开发可选 | `uv run python main.py` 时是否自动拉起前端 |
| `FRONTEND_DEV_COMMAND` | 开发可选 | 默认 `npm run dev` |
| `VITE_API_PROXY_TARGET` | 开发建议配置 | Vite 代理指向的后端地址 |

注意事项：

- `SECRET_KEY` 与 `USER_DATA_ENCRYPTION_SECRET` 不要复用。
- `ENVIRONMENT=production` 时，`FRONTEND_PUBLIC_ORIGIN` 不能为空。
- `ENVIRONMENT=production` 时，`ALLOWED_ORIGINS` 不能包含 `*`。

### 5.2 `config/app_config.toml`

这是业务运营配置，不建议塞进 `.env`。

主要节：

- `[default_model]`
  - 配置系统默认模型提供商、模型名、Base URL、服务端默认 API Key。
- `[default_admin]`
  - 默认管理员账号，仅首次初始化且用户不存在时创建。
- `[quota]`
  - 用户每日进入世界配额、模型调用配额及管理员允许分配的上限。
- `[rate_limit]`
  - 鉴权、个人资料、管理员、游戏推进四类接口的速率限制阈值。
- `[gameplay]`
  - 默认属性点总量、死亡判定属性、终局关键词、默认候选动作等。
- `[frontend]`
  - 生产前端公开地址与路由基准。

### 5.3 `config/world_config.toml`

这是游戏世界与预设配置。

主要节：

- `[[startup_presets]]`
  - 每个世界开局模板，定义标题、描述、世界观、角色选项、属性面板与年龄步进。
- `[[startup_presets.attributes]]`
  - 单个预设下的属性项定义。
- `[custom_preset]`
  - 是否启用“自定义预设”，以及该模式下允许分配的属性配置。

## 6. 开发启动

### 6.1 一键联调

```bash
uv run python main.py
```

该命令会：

1. 启动 FastAPI 后端
2. 等待后端健康检查通过
3. 按 `.env` 配置自动拉起 Vite 开发服务器

默认本地地址：

- 后端：`http://127.0.0.1:8100`
- 前端：`http://127.0.0.1:8101`
- Swagger：`http://127.0.0.1:8100/docs`
- OpenAPI：`http://127.0.0.1:8100/openapi.json`

如果端口被占用，`main.py` 会在启动前直接报出明确错误，而不是等 Uvicorn 启动失败后才发现。

### 6.2 分开启动

后端：

```bash
uv run uvicorn app.main:app --host 127.0.0.1 --port 8100 --reload
```

前端：

```bash
cd frontend
npm run dev
```

## 7. 测试与验证

前端构建：

```bash
cd frontend
npm run build
```

后端测试：

```bash
uv run --isolated --with pytest --with pytest-asyncio --with pytest-cov pytest
```

后端语法检查：

```bash
uv run python -m compileall app main.py
```

## 8. 生产部署

项目支持两种生产形态：

1. `FastAPI + frontend/dist` 一体部署
2. 前后端分离部署

### 8.1 一体部署

适用于中小规模单机或内网环境。

步骤：

1. 构建前端静态资源

```bash
cd frontend
npm install
npm run build
cd ..
```

2. 配置生产环境变量

至少确认以下值：

```env
ENVIRONMENT=production
APP_HOST=0.0.0.0
APP_PORT=8100
FRONTEND_PUBLIC_ORIGIN=https://your-domain.example
ALLOWED_ORIGINS=https://your-domain.example
ENFORCE_HTTPS=true
TRUST_X_FORWARDED_PROTO=true
```

3. 安装后端依赖

```bash
uv sync
```

4. 启动服务

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8100 --workers 2
```

当 `ENVIRONMENT != development` 且 `frontend/dist` 存在时，FastAPI 会自动挂载静态前端。

### 8.2 前后端分离部署

适用于前端走 CDN / Nginx 静态托管、后端单独服务的场景。

后端：

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8100 --workers 2
```

前端：

```bash
cd frontend
npm run build
```

然后将 `frontend/dist` 发布到 Nginx、对象存储或 CDN。

此时务必保证：

- `FRONTEND_PUBLIC_ORIGIN` 指向真实前端域名
- `ALLOWED_ORIGINS` 包含真实前端域名
- `VITE_API_PROXY_TARGET` 仅用于开发，不用于生产静态托管

### 8.3 Nginx 反向代理示例

```nginx
server {
    listen 80;
    server_name your-domain.example;

    location / {
        proxy_pass http://127.0.0.1:8100;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

如果启用了 `ENFORCE_HTTPS=true`，请保证反向代理正确传递 `X-Forwarded-Proto`。

### 8.4 SQLite 部署注意事项

当前默认数据库为 SQLite，适合：

- 单机部署
- 小规模团队内部使用
- 开发与演示环境

不适合：

- 多实例并发写入
- 高并发生产场景
- 强事务隔离要求场景

后续如果要继续扩展，建议升级到 PostgreSQL，并把轻量迁移逻辑迁入 Alembic。

## 9. 安全说明

- 用户自定义 API Key 使用 Fernet 加密存储，不回传前端明文。
- 游戏自定义输入会经过 Prompt 注入拦截与长度限制。
- 生产环境支持 HTTPS 强制与安全响应头。
- 管理员接口、鉴权接口、游戏推进接口都经过独立速率限制。

## 10. API 文档

自动文档：

- Swagger UI：`/docs`
- ReDoc：`/redoc`
- OpenAPI JSON：`/openapi.json`

人工维护的业务接口说明请见：

- [API文档.md](D:/Coding/Web/life-restart/API文档.md)

## 11. 当前验证结果

本仓库已完成以下实际验证：

- `uv run python main.py` 本地联调可正常启动
- `http://127.0.0.1:8100/healthz`、`/docs`、`/openapi.json` 可访问
- `frontend` 构建通过
- `pytest` 基础测试通过

