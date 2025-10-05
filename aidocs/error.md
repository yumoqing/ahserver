# API 响应工具函数技术文档

本文档描述了一组用于生成标准化 API 响应的 Python 函数。这些函数旨在统一后端接口返回的数据格式，提升前后端交互的一致性和可维护性。

---

## 目录

- [简介](#简介)
- [函数说明](#函数说明)
  - [`Error(errno, msg)`](#errorerrno-msg)
  - [`Success(data)`](#successdata)
  - [`NeedLogin(path)`](#needloginpath)
  - [`NoPermission(path)`](#nopermissionpath)
- [响应结构规范](#响应结构规范)
- [使用示例](#使用示例)

---

## 简介

该模块提供四个辅助函数，用于快速构造具有统一结构的 JSON 响应对象。适用于 Web API 开发中常见的成功、错误、登录验证和权限控制场景。

所有函数返回标准字典结构，可直接序列化为 JSON 并返回给客户端。

---

## 函数说明

### `Error(errno, msg)`

生成表示错误响应的标准结构。

#### 参数
| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `errno` | `str` | `'undefined error'` | 错误代码或标识符，用于区分不同类型的错误 |
| `msg`   | `str` | `'Error'` | 用户可读的错误消息 |

#### 返回值
```json
{
  "status": "Error",
  "data": {
    "message": "错误信息",
    "errno": "错误编号"
  }
}
```

#### 示例
```python
Error("404", "资源未找到")
# 返回：
# {
#   "status": "Error",
#   "data": {
#     "message": "资源未找到",
#     "errno": "404"
#   }
# }
```

---

### `Success(data)`

生成表示操作成功的响应。

#### 参数
| 参数名 | 类型 | 说明 |
|--------|------|------|
| `data` | `any` | 实际返回的数据内容（可以是字典、列表、字符串等） |

#### 返回值
```json
{
  "status": "OK",
  "data": "传入的数据"
}
```

> **注意**：`data` 字段的内容由调用者决定，保持灵活性。

#### 示例
```python
Success({"id": 1, "name": "张三"})
# 返回：
# {
#   "status": "OK",
#   "data": {
#     "id": 1,
#     "name": "张三"
#   }
# }
```

---

### `NeedLogin(path)`

指示客户端当前请求需要用户登录，并可指定跳转路径。

#### 参数
| 参数名 | 类型 | 说明 |
|--------|------|------|
| `path` | `str` | 登录成功后建议跳转的路径（如 `/login`） |

#### 返回值
```json
{
  "status": "need_login",
  "data": "/login"
}
```

#### 示例
```python
NeedLogin("/login")
# 返回：
# {
#   "status": "need_login",
#   "data": "/login"
# }
```

前端可根据此状态重定向至登录页。

---

### `NoPermission(path)`

表示用户没有访问该资源的权限，可附带引导路径。

#### 参数
| 参数名 | 类型 | 说明 |
|--------|------|------|
| `path` | `str` | 权限不足时建议跳转的页面路径（如 `/forbidden` 或 `/home`） |

#### 返回值
```json
{
  "status": "no_permission",
  "data": "/forbidden"
}
```

#### 示例
```python
NoPermission("/home")
# 返回：
# {
#   "status": "no_permission",
#   "data": "/home"
# }
```

可用于前端展示权限提示或跳转到安全页面。

---

## 响应结构规范

| 字段 | 类型 | 说明 |
|------|------|------|
| `status` | `string` | 响应状态码，取值包括：<br>`"OK"`：成功<br>`"Error"`：通用错误<br>`"need_login"`：需要登录<br>`"no_permission"`：无权限 |
| `data` | `any` | 具体数据内容，结构根据 `status` 而变化 |

推荐前端通过判断 `status` 字段进行相应处理。

---

## 使用示例

```python
# 成功返回用户信息
return Success({
    "user_id": 123,
    "username": "alice",
    "email": "alice@example.com"
})

# 参数校验失败
return Error("VALIDATION_FAILED", "邮箱格式不正确")

# 未登录访问受保护接口
return NeedLogin("/login")

# 用户无权访问管理员功能
return NoPermission("/dashboard")
```

---

## 总结

这组函数简化了 API 响应的构建过程，确保前后端通信格式统一、语义清晰。建议在项目中全局使用，避免手动拼接响应结构带来的不一致性。