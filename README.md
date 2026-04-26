# AI 人生重开模拟器

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-009688.svg?style=flat&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com)
[![Vue3](https://img.shields.io/badge/Vue.js-3.5-4FC08D.svg?style=flat&logo=vuedotjs&logoColor=white)](https://vuejs.org/)
[![Vite](https://img.shields.io/badge/Vite-7-646CFF.svg?style=flat&logo=vite&logoColor=white)](https://vitejs.dev/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3.4-38B2AC.svg?style=flat&logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![python](https://img.shields.io/badge/Python-3.11+-blue.svg?style=flat&logo=python&logoColor=white)](https://www.python.org/)

> 全栈项目：FastAPI + Vue 3（Vite + Pinia + Tailwind）  
> 目标：构建可商用的 AI 人生重开模拟器（鉴权、权限、额度、管理员能力齐全）  
> 项目使用Vibe Coding  

---

## ✨ 核心特性

- 🎮 **沉浸式 AI 模拟**：结合大语言模型，体验完全自由且充满变数的人生抉择。
- 🛡️ **生产级安全设计**：用户 API Key 强加密存储、前端零泄露、支持强制 HTTPS。
- 👥 **完善的账户系统**：支持用户注册、登录、额度限制与个人配额管理。
- 🛠️ **管理员面板**：提供完整的用户管理与系统配置监控视图。
- ⚡ **极致开发体验**：支持前后端一键联动启动，配置项自动同步。

## 🧩 技术栈

- **后端**: FastAPI, SQLModel (SQLite), LiteLLM, PyJWT, Cryptography
- **前端**: Vue 3 (Composition API), Vite, Tailwind CSS, Pinia, Vue Router
- **包管理**: 后端推荐使用现代化工具 [uv](https://github.com/astral-sh/uv) 提供极速依赖安装，前端使用 npm。

## 📂 项目结构

```text
.
├── app/                  # FastAPI 后端核心代码
├── config/               # 配置文件目录
│   ├── app_config.toml   # 业务配置（模型、管理员、额度、前端入口等）
│   └── world_config.toml # 世界观与游戏预设配置
├── data/                 # SQLite 数据库存储目录
├── frontend/             # Vue 3 前端源码
├── .env                  # 本地环境变量（需手动创建，勿提交真实密钥）
├── .env.example          # 环境变量配置模板
├── main.py               # 一键启动入口（可同时拉起前后端服务）
├── pyproject.toml        # 后端项目清单
└── README.md             # 项目说明
```

---

## 🚀 快速开始

### 1. 环境准备

确保您的操作系统中已安装以下组件：
- **Python** >= 3.11
- **Node.js** >= 20
- **[uv](https://docs.astral.sh/uv/getting-started/installation/)**：极速的 Python 包管理器（强烈推荐）

### 2. 获取代码

```bash
git clone https://github.com/WhiteCloudOL/life-restart-web.git
cd life-restart-web
```

### 3. 安装依赖

#### 后端 (使用 `uv`)
```bash
# 创建虚拟环境
uv venv

# 激活虚拟环境
# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate

# 安装生产依赖
uv pip install -r requirements.txt

# (可选) 若需参与开发或运行测试，请安装开发依赖
uv pip install -r requirements-dev.txt
```

#### 前端
```bash
cd frontend
npm install
cd ..
```

---

## ⚙️ 配置说明

在运行项目前，您**必须**完成必要的配置。

### 环境变量 (`.env`)

1. 将环境模板文件拷贝一份并重命名为 `.env`：
   ```bash
   cp .env.example .env
   ```
2. **关键安全项替换**（务必修改为强随机字符串）：
   - `SECRET_KEY`: JWT 签名密钥（至少 32 字符）。
   - `USER_DATA_ENCRYPTION_SECRET`: 用户密钥在数据库中加密所需的密钥（至少 32 字符，且勿与 JWT 密钥相同）。
3. **前端联动设置**：
   - 默认开启 `START_FRONTEND_WITH_BACKEND=true`，通过 `python main.py` 启动时会自动运行 `npm run dev` 拉起前端。

### 业务配置 (`config/app_config.toml`)

若此文件不存在，系统会在首次启动时自动从模板 `config/app_config.template.toml` 创建。
适合产品与运营调整的核心参数包括：
- `[default_model]`: 系统默认模型参数（在此配置全局 API Key 和 Base URL）。
- `[default_admin]`: 默认超级管理员账号配置（系统启动时自动检测创建）。
- `[quota]`: 新注册用户默认每日额度以及管理员可分配的最大上限。
- `[gameplay]`: 模拟器基础参数设置，如最大选项数、属性点分配总值等。

---

## 🏃 启动方式

### 方式 A：一键启动（推荐开发时使用）

在项目根目录（确保已安装uv）：
```bash
uv sync
uv run main.py
```
> **行为表现**: 
> 1. 启动 FastAPI 后端服务（默认 `http://127.0.0.1:8100`）。
> 2. 检测 `.env` 中的 `START_FRONTEND_WITH_BACKEND=true` 后，在新的子进程中自动启动 Vite 前端服务（默认 `http://127.0.0.1:8101`）。

### 方式 B：前后端分开独立部署

**后端**:
```bash
uvicorn main:app --reload
```

**前端**:
```bash
cd frontend
npm run build
```

---

## 🔒 安全设计

1. **用户密钥不明文存储**：
   - 用户自定义填写的 `custom_api_key` 在服务端入库前使用 Fernet 对称加密。
   - 数据库存储格式严格为密文。系统启动时具备向下兼容的历史明文自动加密迁移能力。
2. **敏感信息零泄露**：
   - 任何查询用户信息（如 `/api/user/me`）的接口仅返回脱敏状态值 `has_custom_api_key: true/false`，绝不向前端回传明文 Key。
3. **强制传输加密**：
   - 支持设置 `ENFORCE_HTTPS=true`。
   - 在生产环境下建议开启该选项，系统将严格拒绝任何非 HTTPS 的 API 请求，并支持 `TRUST_X_FORWARDED_PROTO` 适配 Nginx/Traefik 等网关反向代理场景。

---

## 📖 API 文档与关键接口

服务成功启动后，后端自动生成并提供 OpenAPI 标准规范接口文档，方便调试：
- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc UI**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

**常见核心 API 摘要**:
- `POST /api/auth/register`：用户注册
- `POST /api/auth/login`：用户登录获取 Token
- `GET /api/user/me`：获取当前用户信息及配额
- `POST /api/game/start`：应用人生预设并开启新局
- `POST /api/game/next`：选择命运并推进下一回合
- `GET /api/admin/users`：【管理员】分页查询用户列表

详尽的自定义业务说明可参考 [API文档.md](./API文档.md)。

---

## 📦 构建与部署

**前端生产环境构建**：
```bash
cd frontend
npm run build
```
这将在 `frontend/dist/` 下生成用于生产环境部署的静态资源。

**后端语法与编译检查**：
```bash
python -m compileall app
```

---
