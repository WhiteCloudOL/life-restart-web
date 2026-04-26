# AI 人生重开模拟器 API 文档

本文档描述的是当前仓库中实际存在的业务接口，不代替 Swagger/OpenAPI 自动文档，但会补充鉴权、典型调用顺序、字段语义与部署时最常见的问题。

自动文档入口：

- Swagger UI：`http://127.0.0.1:8100/docs`
- ReDoc：`http://127.0.0.1:8100/redoc`
- OpenAPI JSON：`http://127.0.0.1:8100/openapi.json`

## 1. 通用约定

### 1.1 基础信息

- Base URL：`/api`
- 认证方式：`Authorization: Bearer <access_token>`
- 编码：`application/json`

### 1.2 常见状态码

| 状态码 | 含义 |
| --- | --- |
| `200` | 请求成功 |
| `201` | 资源创建成功 |
| `400` | 请求参数不合法，或被安全规则拒绝 |
| `401` | 未认证或 Token 无效 |
| `403` | 无权限访问 |
| `404` | 资源不存在 |
| `409` | 资源冲突，例如用户名重复 |
| `429` | 触发接口限流或业务额度限制 |
| `500` | 服务器内部错误 |

### 1.3 通用错误响应

```json
{
  "detail": "错误描述"
}
```

## 2. 认证与限流

### 2.1 认证头

```http
Authorization: Bearer eyJhbGciOi...
```

### 2.2 速率限制分类

当前后端按业务分为四类限流：

| 分类 | 默认窗口 | 默认阈值 | 典型接口 |
| --- | --- | --- | --- |
| auth | 60 秒 | 12 次 | `/auth/register` `/auth/login` |
| gameplay | 60 秒 | 30 次 | `/game/start` `/game/next` `/game/force-exit` |
| profile | 60 秒 | 20 次 | `/user/me` `/user/history` |
| admin | 60 秒 | 60 次 | `/admin/*` |

实际值来源于 `config/app_config.toml -> [rate_limit]`。

## 3. 认证接口

### 3.1 注册

- 方法：`POST`
- 路径：`/api/auth/register`
- 认证：否

请求体：

```json
{
  "username": "alice_01",
  "password": "Strong@Pass123"
}
```

约束：

- 用户名长度 3 到 32，只允许字母、数字、下划线
- 密码至少 10 位，必须同时包含大写、小写、数字、特殊字符

成功响应：

```json
{
  "id": 1,
  "username": "alice_01",
  "nickname": "alice_01",
  "api_mode": "default",
  "has_custom_api_key": false,
  "custom_model_name": null,
  "custom_base_url": null,
  "is_admin": false,
  "world_entry_limit": 20,
  "world_entries_used_today": 0,
  "model_call_limit": 80,
  "model_calls_used_today": 0,
  "last_active_date": "2026-04-26"
}
```

### 3.2 登录

- 方法：`POST`
- 路径：`/api/auth/login`
- 认证：否

请求体：

```json
{
  "username": "alice_01",
  "password": "Strong@Pass123"
}
```

成功响应：

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

## 4. 用户接口

### 4.1 获取当前用户

- 方法：`GET`
- 路径：`/api/user/me`
- 认证：是

成功响应字段：

| 字段 | 说明 |
| --- | --- |
| `id` | 用户 ID |
| `username` | 登录用户名 |
| `nickname` | 展示昵称 |
| `api_mode` | `default` 或 `custom` |
| `has_custom_api_key` | 是否已配置自定义模型密钥 |
| `custom_model_name` | 自定义模型名 |
| `custom_base_url` | 自定义模型 Base URL |
| `is_admin` | 是否管理员 |
| `world_entry_limit` | 每日进入世界配额 |
| `world_entries_used_today` | 今日已使用进入世界次数 |
| `model_call_limit` | 每日模型调用配额 |
| `model_calls_used_today` | 今日已使用模型调用次数 |
| `last_active_date` | 最近活跃日期 |

### 4.2 更新当前用户

- 方法：`PUT`
- 路径：`/api/user/me`
- 认证：是

请求体示例：

```json
{
  "nickname": "白昼旅人",
  "api_mode": "custom",
  "custom_api_key": "sk-xxxx",
  "custom_model_name": "gpt-4.1-mini",
  "custom_base_url": "https://api.openai.com/v1"
}
```

说明：

- 不传的字段不会被修改
- `custom_api_key` 只用于写入，不会以明文形式从接口返回
- 若切换回 `default` 模式，可只更新 `api_mode`

### 4.3 获取我的历史局

- 方法：`GET`
- 路径：`/api/user/history`
- 认证：是

成功响应：

```json
[
  {
    "id": 12,
    "user_id": 1,
    "preset_id": 2,
    "current_stats": {
      "physique": 6,
      "intelligence": 8
    },
    "event_history": [
      {
        "role": "system",
        "content": "进入世界：赛博城贫民区"
      }
    ],
    "is_ended": false
  }
]
```

## 5. 管理员接口

所有 `/api/admin/*` 接口都要求管理员身份。

### 5.1 分页获取用户列表

- 方法：`GET`
- 路径：`/api/admin/users?page=1&size=20`
- 认证：管理员

成功响应：

```json
{
  "page": 1,
  "size": 20,
  "total": 2,
  "items": [
    {
      "id": 1,
      "username": "admin",
      "nickname": "admin",
      "api_mode": "default",
      "is_admin": true,
      "world_entry_limit": 10000,
      "world_entries_used_today": 0,
      "model_call_limit": 20000,
      "model_calls_used_today": 0,
      "last_active_date": "2026-04-26",
      "has_custom_api_key": false
    }
  ],
  "next_page": null
}
```

### 5.2 创建用户

- 方法：`POST`
- 路径：`/api/admin/users`
- 认证：管理员

请求体：

```json
{
  "username": "operator_01",
  "password": "Strong@Pass123",
  "nickname": "运营一号",
  "is_admin": false
}
```

### 5.3 更新用户配额

- 方法：`PUT`
- 路径：`/api/admin/users/{user_id}/quota`
- 认证：管理员

请求体：

```json
{
  "world_entry_limit": 50,
  "model_call_limit": 300
}
```

兼容字段别名：

- `daily_quota` 等价于 `world_entry_limit`
- `daily_model_call_limit` 等价于 `model_call_limit`

### 5.4 更新用户资料

- 方法：`PATCH`
- 路径：`/api/admin/users/{user_id}`
- 认证：管理员

请求体示例：

```json
{
  "nickname": "审计员",
  "is_admin": true,
  "world_entry_limit": 100,
  "model_call_limit": 500,
  "model_calls_used_today": 12
}
```

### 5.5 删除用户

- 方法：`DELETE`
- 路径：`/api/admin/users/{user_id}`
- 认证：管理员

成功响应：

```json
{
  "message": "用户已删除"
}
```

实际文案可能因服务层实现略有不同，但响应结构为简单消息体。

## 6. 游戏接口

### 6.1 获取世界预设

- 方法：`GET`
- 路径：`/api/game/presets`
- 认证：是

响应示例：

```json
[
  {
    "id": 1,
    "title": "普通家庭开局",
    "description": "你出生在一个普通家庭，资源有限但关系温暖。",
    "worldview": "近未来都市世界……",
    "character_options": ["务实内向", "外向冒险", "理性规划"],
    "max_attribute_points": 15,
    "is_custom": false,
    "attributes": [
      {
        "key": "looks",
        "label": "颜值",
        "purpose": "影响他人的第一印象……",
        "min_value": 0,
        "max_value": 10,
        "default_value": 0
      }
    ]
  }
]
```

### 6.2 开始新局

- 方法：`POST`
- 路径：`/api/game/start`
- 认证：是

请求体示例：

```json
{
  "preset_id": 1,
  "selected_character_setting": "理性规划",
  "allocated_attributes": {
    "looks": 3,
    "physique": 4,
    "intelligence": 5,
    "wealth": 3
  },
  "custom_prompt": "希望剧情更偏现实主义"
}
```

自定义预设示例：

```json
{
  "preset_id": 9999,
  "custom_worldview": "2077 年的海上浮城社会，能源稀缺，秩序建立在算法信用之上。",
  "custom_character_setting": "记忆受损但异常冷静的机械维修师",
  "allocated_attributes": {
    "looks": 2,
    "physique": 3,
    "intelligence": 6,
    "wealth": 4
  },
  "custom_prompt": "剧情节奏偏慢，注重生存与选择后果"
}
```

成功响应：

```json
{
  "session_id": 32,
  "event": "你出生在一个普通家庭……",
  "event_segments": [
    "你出生在一个普通家庭。",
    "你的父母虽然并不富裕，却愿意为你承担风险。"
  ],
  "current_stats": {
    "looks": 3,
    "physique": 4,
    "intelligence": 5,
    "wealth": 3
  },
  "is_ended": false,
  "world_entry_limit": 20,
  "world_entries_used_today": 1,
  "model_call_limit": 80,
  "model_calls_used_today": 1,
  "next_choices": [
    "[高风险] ...",
    "[中风险] ...",
    "[低风险] ..."
  ],
  "end_reason": null,
  "end_summary": null
}
```

### 6.3 推进下一回合

- 方法：`POST`
- 路径：`/api/game/next`
- 认证：是

请求体：

```json
{
  "session_id": 32,
  "user_choice": "接受高风险创业提议"
}
```

响应结构与 `/api/game/start` 相同。

### 6.4 强制结束当前会话

- 方法：`POST`
- 路径：`/api/game/force-exit`
- 认证：是

请求体：

```json
{
  "session_id": 32
}
```

成功响应：

```json
{
  "success": true,
  "end_reason": "forced_exit",
  "end_summary": "你的人生在此刻被主动按下暂停键……"
}
```

## 7. 推荐调用顺序

正常前端接入顺序：

1. `POST /api/auth/login`
2. `GET /api/user/me`
3. `GET /api/game/presets`
4. `POST /api/game/start`
5. 循环调用 `POST /api/game/next`
6. 需要提前结束时调用 `POST /api/game/force-exit`
7. 在个人页读取 `GET /api/user/history`

## 8. 与部署相关的 API 注意事项

- 前端域名变化后，记得同步 `FRONTEND_PUBLIC_ORIGIN` 与 `ALLOWED_ORIGINS`。
- 若启用反向代理并打开 `ENFORCE_HTTPS=true`，必须保证代理透传 `X-Forwarded-Proto`。
- 若切换到自定义模型模式，`custom_base_url` 必须是合法 URL。
- 当前数据库默认 SQLite，管理员类接口与游戏推进接口不建议在多实例共享写入场景下直接横向扩容。

## 9. 文档维护说明

本文档基于当前代码实现维护。若以下内容发生变化，应同步更新：

- 路由路径与方法
- 请求/响应模型字段
- 限流默认值
- 配置项名称
- 默认开发端口与部署方式

