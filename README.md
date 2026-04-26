# AI 人生重开模拟器

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-009688.svg?style=flat&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com)
[![Vue3](https://img.shields.io/badge/Vue.js-3.5-4FC08D.svg?style=flat&logo=vuedotjs&logoColor=white)](https://vuejs.org/)
[![Vite](https://img.shields.io/badge/Vite-7-646CFF.svg?style=flat&logo=vite&logoColor=white)](https://vitejs.dev/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3.4-38B2AC.svg?style=flat&logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

> 全栈项目：FastAPI + Vue 3（Vite + Pinia + Tailwind）  
> 目标：构建可商用的 AI 人生重开模拟器（鉴权、权限、额度、管理员能力齐全）  
> 项目使用 Vibe Coding 构建

---

基于 `FastAPI` 和 `Vue 3` 的全栈 AI 人生模拟项目，支持用户鉴权、管理员配额管理、自定义模型接入、Prompt 注入拦截、速率限制与本地一键联调。

## ✨ 核心特性

- **现代全栈架构**
  - **后端**: FastAPI + SQLModel + SQLAlchemy Async + LiteLLM
  - **前端**: Vue 3 + Vite + Pinia + Tailwind CSS
- **工程化与规范**
  - 后端采用应用工厂、路由/服务/仓储分层、异步 SQLite 会话与配置预热。
  - 前端采用组合式 API、页面逻辑拆分为 composables 与无状态组件。
- **极致的开发体验**
  - 本地开发支持 `uv run python main.py` **一键拉起**后端与 Vite。
- **生产级部署支持**
  - 生产环境支持在 FastAPI 中挂载 `frontend/dist` 静态产物，实现单服务一键部署。
  - 支持前后端分离部署（Nginx/CDN）。
- **完善的安全机制**
  - JWT 鉴权、密码 bcrypt 哈希、用户 API Key Fernet 加密。
  - 多级速率限制、HTTPS 强制中间件、Prompt 注入拦截。

---

## 📂 项目结构

```text
.
├── app/                     # FastAPI 后端核心
│   ├── api/                 # 路由入口
│   ├── core/                # 配置、安全、中间件、依赖
│   ├── db/                  # 数据库会话与初始化
│   ├── models/              # 数据模型
│   ├── repositories/        # 数据访问层
│   ├── schemas/             # Pydantic V2 模型
│   └── services/            # 业务服务层
├── config/                  # 业务与游戏预设配置
│   ├── app_config.toml      # 运营配置 (配额、模型等)
│   └── world_config.toml    # 游戏世界与预设配置
├── data/                    # SQLite 数据文件目录
├── frontend/                # Vue 3 前端工程
├── tests/                   # 自动化测试
├── .env.example             # 环境变量模板
├── main.py                  # 本地开发一键联调入口
└── pyproject.toml           # Python 项目依赖清单 (uv)
```

---

## 🚀 快速开始

### 1. 运行环境要求

- Python `3.11+`
- Node.js `20+`
- [uv](https://github.com/astral-sh/uv) (推荐的 Python 包管理器)

### 2. 获取代码与安装依赖

```bash
# 克隆仓库
git clone https://github.com/WhiteCloudOL/life-restart-web.git
cd life-restart-web

# 使用 uv 安装后端依赖 (推荐)
uv sync

# 安装前端依赖
cd frontend
npm install
cd ..
```

### 3. 环境配置

复制环境变量模板并根据需要修改：

```bash
# Linux / macOS
cp .env.example .env

# Windows
Copy-Item .env.example .env
```

*注意：系统启动时会自动依据 `config/*.template.toml` 创建 `app_config.toml` 和 `world_config.toml`。*

### 4. 一键开发启动

```bash
uv run python main.py
```

该命令会：
1. 启动 FastAPI 后端 (`http://127.0.0.1:8100`)
2. 自动启动 Vite 前端开发服务器 (`http://127.0.0.1:8101`)
3. 您可以通过访问前端地址开始调试。

*(或者你可以分别启动：`uv run uvicorn app.main:app --reload` 和 `cd frontend && npm run dev`)*

---

## ⚙️ 核心配置说明

项目配置分为三层：

### 1. `.env` (系统级配置)
主要控制运行环境、网络与密钥。
- `SECRET_KEY`: JWT 密钥 (必填)
- `USER_DATA_ENCRYPTION_SECRET`: API Key 加密密钥 (必填)
- `ENVIRONMENT`: `development` / `production` 等
- `DATABASE_URL`: 数据库连接，默认 SQLite `sqlite:///./data/life_simulator.db`

### 2. `config/app_config.toml` (运营配置)
控制业务逻辑与限制。
- `[default_model]`: 系统默认调用的 AI 模型及提供商。
- `[quota]`: 用户每日额度限制。
- `[rate_limit]`: 接口请求频率限制。

### 3. `config/world_config.toml` (游戏配置)
控制游戏内容。
- `[[startup_presets]]`: 游戏开局选项、预设模板、属性面板。

---

## 📦 生产部署

项目支持两种部署模式，您可以根据服务器资源自由选择。

### 模式一：一体化部署 (推荐小型服务)

利用 FastAPI 直接托管构建好的前端静态资源。

1. **构建前端产物**
   ```bash
   cd frontend
   npm run build
   cd ..
   ```
2. **设置生产环境变量** (`.env`)
   ```env
   ENVIRONMENT=production
   APP_HOST=0.0.0.0
   APP_PORT=8100
   ```
3. **启动服务**
   ```bash
   uv run uvicorn app.main:app --host 0.0.0.0 --port 8100 --workers 4
   ```
   *服务启动后，访问 `http://your-ip:8100` 即可直接看到前端页面。*

### 模式二：前后端分离部署 (推荐配合 Nginx/CDN)

1. **后端单独运行**
   ```bash
   uv run uvicorn app.main:app --host 127.0.0.1 --port 8100
   ```
2. **前端构建并部署到 Nginx**
   将 `frontend/dist` 部署至您的 Web 服务器，并配置反向代理指向后端 `8100` 端口的 API。

*(详细 Nginx 配置与反代说明请参考源码中的注释或独立文档)*

---

## 🧪 测试与校验

```bash
# 后端基础测试
uv run pytest

# 语法检查
uv run ruff check .
```

## 📚 API 文档

在后端服务启动后，您可以访问自动生成的交互式文档：
- **Swagger UI**: `http://127.0.0.1:8100/docs`
- **ReDoc**: `http://127.0.0.1:8100/redoc`

人工维护的业务接口说明请参考仓库内的 [`API文档.md`](./API文档.md)。
