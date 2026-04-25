# AI Life Simulator

> 全栈项目：FastAPI + Vue 3（Vite + Pinia + Tailwind）  
> 目标：构建可商用的 AI 人生重开模拟器（鉴权、权限、额度、管理员能力齐全）

---

## 项目结构

```text
.
├── app/                  # FastAPI 后端
├── config/
│   └── app_config.toml   # 业务配置（模型、管理员、额度、前端入口、玩法）
├── data/                 # SQLite 数据目录
├── frontend/             # Vue 3 前端
├── .env                  # 本地环境变量（不要提交真实密钥）
├── .env.example          # 环境变量模板
├── main.py               # 一键启动入口（可同时启动前后端）
├── pyproject.toml
├── requirements.txt
└── requirements-dev.txt
```

---

## 安全设计（已落地）

### 1) 用户密钥不明文存储

- 用户自定义 `custom_api_key` 在服务端入库前会加密（Fernet 对称加密）。
- 数据库存储格式为密文（带前缀），不再保存明文。
- 启动时会自动迁移历史明文字段为密文（幂等迁移）。

### 2) 用户密钥不对外泄露

- 用户相关接口仅返回 `has_custom_api_key`，不会回传明文 Key。
- 默认模型 Key 与用户自定义 Key 均仅在服务端用于上游模型调用。

### 3) 传输安全可强制

- 新增 `ENFORCE_HTTPS` 配置。
- 生产环境建议设为 `true`，API 将拒绝非 HTTPS 请求。
- 支持 `TRUST_X_FORWARDED_PROTO=true`，适配 Nginx/Traefik 反代场景。

---

## 配置说明

### `.env` / `.env.example`

已经补齐并加注释，重点变量：

- `SECRET_KEY`：JWT 签名密钥（至少 32 字符）
- `USER_DATA_ENCRYPTION_SECRET`：用户密钥加密密钥（至少 32 字符）
- `FRONTEND_DEV_ORIGIN` / `FRONTEND_PUBLIC_ORIGIN`：前端访问路径
- `ALLOWED_ORIGINS`：CORS 白名单（可留空自动合并前端 origin）
- `ENFORCE_HTTPS`：是否强制 HTTPS
- `START_FRONTEND_WITH_BACKEND`：`python main.py` 时是否同时拉起前端
- `FRONTEND_DIR` / `FRONTEND_DEV_COMMAND`：前端启动目录与命令

### `config/app_config.toml`

适合产品/运营配置的业务参数：

- `[default_model]`：系统默认模型参数（包含服务端 API Key）
- `[default_admin]`：默认管理员账号配置（启动时自动创建）
- `[quota]`：默认额度与管理员上限
- `[frontend]`：前端公共入口与路由基路径
- `[gameplay]`：默认可选项与选项数量上限

---

## 安装依赖

### 后端

```bash
pip install -r requirements.txt
```

开发依赖：

```bash
pip install -r requirements-dev.txt
```

### 前端

```bash
cd frontend
npm install
```

---

## 启动方式

## 方式 A：一键启动（推荐开发）

在项目根目录执行：

```bash
python main.py
```

行为：

- 启动 FastAPI（`APP_HOST:APP_PORT`）
- 若 `START_FRONTEND_WITH_BACKEND=true`，会自动启动 `frontend/` 下的前端开发服务

## 方式 B：前后端分开启动

后端：

```bash
uvicorn main:app --reload
```

前端：

```bash
cd frontend
npm run dev
```

---

## 构建与检查

前端生产构建：

```bash
cd frontend
npm run build
```

后端语法检查：

```bash
python -m compileall app
```

---

## 关键接口（摘要）

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/user/me`
- `PUT /api/user/me`
- `GET /api/game/presets`
- `POST /api/game/start`
- `POST /api/game/next`
- `GET /api/admin/users`
- `PUT /api/admin/users/{user_id}/quota`

完整示例见 [API文档.md](https://github.com/WhiteCloudOL/life-restart-web/blob/main/API%E6%96%87%E6%A1%A3.md)。

---

## 运行前必做

1. 复制 `.env.example` 到 `.env`（若你已有 `.env`，请核对新加安全项）。  
2. 替换 `SECRET_KEY` 和 `USER_DATA_ENCRYPTION_SECRET` 为强随机值。  
3. 在 `config/app_config.toml` 中填写 `[default_model].api_key`，并修改 `[default_admin].password`。  
4. 生产部署请启用 HTTPS，并将 `ENFORCE_HTTPS=true`。  
