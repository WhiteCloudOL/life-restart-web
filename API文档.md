# 📚 AI Life Simulator - 后端 API 文档

> 本文档整理了系统（MVP）核心可用接口。系统基于 FastAPI 自动生成符合 OpenAPI 标准的详尽在线文档，强烈建议在服务启动后直接访问接口页面进行测试与调试。

## 🧭 在线接口文档

当后端服务（默认运行在 `http://127.0.0.1:8000`）启动后，您可以访问以下地址查看完整的交互式 API 文档：
- **Swagger UI（推荐测试使用）**: [`/docs`](http://127.0.0.1:8000/docs)
- **ReDoc（推荐阅读使用）**: [`/redoc`](http://127.0.0.1:8000/redoc)

---

## 🔒 基础约定

- **Base URL**: `http://{APP_HOST}:{APP_PORT}`
- **接口前缀**: `/api`
- **鉴权方式**: JWT (JSON Web Token)
  - 在请求头中携带：`Authorization: Bearer <您的 Token>`
- **数据格式**: 请求与响应默认均采用 `application/json` 格式（登录接口除外）。

---

## 👤 认证与用户模块

### 1. 用户注册
- **接口**: `POST /api/auth/register`
- **权限**: 开放
- **请求体**:
  ```json
  {
    "username": "alice_001",
    "password": "StrongPass!123"
  }
  ```
- **响应**: 成功返回 `200 OK`，包含新建用户的基础信息。

### 2. 用户登录
- **接口**: `POST /api/auth/login`
- **权限**: 开放
- **请求格式**: `application/x-www-form-urlencoded` (OAuth2PasswordRequestForm)
- **请求体**:
  ```text
  username=alice_001&password=StrongPass!123
  ```
- **响应**:
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5...",
    "token_type": "bearer"
  }
  ```

### 3. 获取当前登录用户信息
- **接口**: `GET /api/user/me`
- **权限**: 需有效登录 Token
- **说明**: 
  - 返回用户的基本信息、额度使用情况。
  - **安全保障**：对于自定义 API Key，接口仅返回布尔值状态 `has_custom_api_key`，绝对不会回传明文 Key。

### 4. 更新当前用户信息
- **接口**: `PUT /api/user/me`
- **权限**: 需有效登录 Token
- **请求体** (仅需传需修改的字段):
  ```json
  {
    "username": "new_alice",
    "custom_api_key": "sk-your-new-api-key",
    "custom_model_name": "gpt-4o-mini",
    "custom_base_url": "https://api.openai.com/v1"
  }
  ```

### 5. 获取用户游戏历史
- **接口**: `GET /api/user/history`
- **权限**: 需有效登录 Token
- **响应**: 分页返回该用户曾经游玩过的所有游戏会话摘要列表。

---

## 🎮 游戏引擎模块

### 1. 获取可用人生预设
- **接口**: `GET /api/game/presets`
- **权限**: 需有效登录 Token
- **响应示例**:
  ```json
  [
    {
      "id": 1,
      "title": "普通家庭开局",
      "description": "你出生在一个普通家庭，资源有限但关系温暖。"
    },
    {
      "id": 2,
      "title": "天胡富二代开局",
      "description": "含着金汤匙出生，起点即是很多人的终点。"
    }
  ]
  ```

### 2. 开始新游戏
- **接口**: `POST /api/game/start`
- **权限**: 需有效登录 Token
- **请求体**:
  ```json
  {
    "preset_id": 1
  }
  ```
- **响应示例** (包含游戏初始状态及 AI 生成的选项):
  ```json
  {
    "session_id": 1,
    "event": "你顺利进入小学，第一次班会开始了。",
    "current_stats": { 
      "health": 81, 
      "intelligence": 71, 
      "wealth": 40, 
      "happiness": 76 
    },
    "is_ended": false,
    "daily_quota": 20,
    "used_quota_today": 1,
    "next_choices": [
      "认真听讲", 
      "和同桌聊天", 
      "举手发言"
    ]
  }
  ```

### 3. 做出选择并推进人生
- **接口**: `POST /api/game/next`
- **权限**: 需有效登录 Token，且只能操作属于自己的 `session_id` (防 IDOR 越权)
- **请求体**:
  ```json
  {
    "session_id": 1,
    "user_choice": "我选择认真听讲，给老师留下好印象"
  }
  ```
- **响应说明**:
  - 成功时响应结构同 `开始新游戏` 接口。
  - 若触发角色死亡或达成结局，`is_ended` 将变为 `true`，此时 `next_choices` 将返回空数组 `[]`。

---

## ⚙️ 系统管理员模块

> 以下接口必须由拥有管理员标记（`is_admin=true`）的账户调用。

### 1. 分页查询用户列表
- **接口**: `GET /api/admin/users?page=1&size=20`
- **权限**: 管理员专有
- **说明**: 方便管理员监控系统全局用户增长和基本状态。

### 2. 修改指定用户配额
- **接口**: `PUT /api/admin/users/{user_id}/quota`
- **权限**: 管理员专有
- **请求体**:
  ```json
  {
    "daily_quota": 50
  }
  ```
- **说明**: 调整指定用户的每日最大调用次数上限，方便给特定用户发福利或限制滥用行为。

---

## 🛡️ 核心安全与额度规则机制

本系统为商业化标准设计，针对 AI 服务的核心资产进行了以下安全限制：

### 1. 数据权限隔离
- 严密的 IDOR（越权访问）防护机制：例如访问 `/api/game/next` 接口时，系统会严格校验请求携带的 `session_id` 是否归属于当前请求的 Token 所有者。

### 2. 凭据加密策略
- **账户密码**：使用强单向哈希算法 `bcrypt` 存储，数据库绝不保存明文密码。
- **自定义 API Key**：使用 `Fernet` 对称加密算法存储入库。前端永远无法查询到明文，仅由服务端在请求上游大模型 API 时解密使用。

### 3. 服务端模型资产保护
- 系统的兜底/默认模型配置位于 `config/app_config.toml` 的 `[default_model].api_key` 中。
- 绝不提供任何 API 或页面返回该系统级 Key，防止开发者核心资产外泄。

### 4. 额度计费规则
- 若用户使用系统的 **默认模型**：扣除系统派发的每日额度（`daily_quota`），当达到上限时拒绝服务；次日凌晨（00:00）自动重置。
- 若用户配置了 **自定义模型与自定义 API Key（BYOK）**：消耗用户自己的资金，该用户的调用将 **不限额**，不受系统每日额度管控。
