# AI Life Simulator 后端 API 文档（MVP）

## 1. 基础信息

- Base URL: `http://{APP_HOST}:{APP_PORT}`
- 前缀: `/api`
- 鉴权方式: `Authorization: Bearer <JWT>`
- 文档页面:
  - Swagger UI: `/docs`
  - ReDoc: `/redoc`

## 2. 认证与用户

### 2.1 注册
- `POST /api/auth/register`
- 请求体:
```json
{
  "username": "alice_001",
  "password": "StrongPass!123"
}
```

### 2.2 登录
- `POST /api/auth/login`
- 请求体:
```json
{
  "username": "alice_001",
  "password": "StrongPass!123"
}
```
- 响应体:
```json
{
  "access_token": "jwt-token",
  "token_type": "bearer"
}
```

### 2.3 当前用户信息
- `GET /api/user/me`
- 需要登录
- 响应中不会返回任何明文 API Key（仅返回 `has_custom_api_key`）

### 2.4 更新当前用户
- `PUT /api/user/me`
- 需要登录
- 可更新字段:
```json
{
  "username": "new_name",
  "custom_api_key": "sk-xxx",
  "custom_model_name": "gpt-4o-mini",
  "custom_base_url": "https://api.openai.com/v1"
}
```

### 2.5 游戏历史
- `GET /api/user/history`
- 需要登录

## 3. 管理员接口

### 3.1 分页用户列表
- `GET /api/admin/users?page=1&size=20`
- 需要管理员权限

### 3.2 修改用户每日额度
- `PUT /api/admin/users/{user_id}/quota`
- 需要管理员权限
- 请求体:
```json
{
  "daily_quota": 50
}
```

## 4. 游戏接口

### 4.0 预设列表
- `GET /api/game/presets`
- 需要登录
- 响应体:
```json
[
  {
    "id": 1,
    "title": "普通家庭开局",
    "description": "你出生在一个普通家庭，资源有限但关系温暖。"
  }
]
```

### 4.1 开始游戏
- `POST /api/game/start`
- 需要登录
- 请求体:
```json
{
  "preset_id": 1
}
```
- 响应体新增 `next_choices` 字段:
```json
{
  "session_id": 1,
  "event": "你顺利进入小学，第一次班会开始了。",
  "current_stats": { "health": 81, "intelligence": 71, "wealth": 40, "happiness": 76 },
  "is_ended": false,
  "daily_quota": 20,
  "used_quota_today": 1,
  "next_choices": ["认真听讲", "和同桌聊天", "举手发言"]
}
```

### 4.2 推进下一步
- `POST /api/game/next`
- 需要登录
- 请求体:
```json
{
  "session_id": 1,
  "user_choice": "我选择认真读书"
}
```
- 响应体同样包含 `next_choices`（当 `is_ended=true` 时返回空数组）

## 5. 安全与额度规则

- IDOR 防护：`/api/game/next` 会强制校验 `session_id` 必须属于当前登录用户。
- 密码安全：使用 `bcrypt` 哈希存储，数据库不保存明文密码。
- 服务端默认模型 Key 安全：
  - Key 存在 `config/app_config.toml` 的 `[default_model].api_key`
  - API 不提供任何获取该 Key 的接口
  - 响应中不会回传该 Key
- 配额规则：
  - 使用系统默认模型时，受每日额度限制
  - 用户配置“自定义模型 + 自定义 API Key”后，调用不限额
  - 跨天自动重置当日已用额度
