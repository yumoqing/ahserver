# 技术文档：`DBCrud` REST API 端点实现

> **基于 `aiohttp` 的数据库 CRUD 操作 RESTful 接口封装**

---

## 概述

该模块提供了一个基于 `aiohttp` 的异步 Web 框架的 RESTful 接口抽象类 `DBCrud`，用于对指定数据库表执行标准的增删改查（CRUD）操作。它继承自通用的 `RestEndpoint` 类，并通过 `sqlor` ORM 工具与数据库交互。

主要特性：
- 支持标准 HTTP 方法：`GET`, `POST`, `PUT`, `DELETE`, `OPTIONS`
- 自动路由分发请求到对应方法
- 使用配置化数据库连接池（`DBPools`）
- 统一返回 JSON 格式响应（成功/错误）
- 集成异常处理和日志输出

---

## 依赖说明

### 第三方库
| 包 | 用途 |
|----|------|
| `aiohttp` | 异步 Web 框架，处理 HTTP 请求/响应 |
| `sqlor.dbpools.DBPools` | 数据库连接池管理器及 ORM 上下文支持 |

### 内部模块
| 模块 | 用途 |
|------|------|
| `appPublic.dictObject.multiDict2Dict` | 将 `MultiDictProxy` 转换为普通字典 |
| `appPublic.jsonConfig.getConfig` | （未使用）预留配置加载功能 |
| `.error.Error`, `.error.Success` | 自定义响应结构体：错误与成功封装 |

---

## 核心类定义

### `RestEndpoint`

一个通用的 REST 端点基类，负责方法注册与请求调度。

#### 属性
- `methods (dict)`：存储 HTTP 方法名与其对应处理函数的映射（如 `'GET': self.get`）

#### 常量
```python
DEFAULT_METHODS = ('GET', 'POST', 'PUT', 'DELETE', 'HEAD', 'OPTIONS', 'TRACE')
```

#### 方法

##### `__init__(self)`
初始化时自动扫描子类中是否存在小写命名的方法（如 `get`, `post`），若存在则调用 `register_method` 注册到 `self.methods` 中。

##### `register_method(self, method_name: str, method: callable)`
将给定的方法注册到内部方法字典中，键为大写的 HTTP 方法名。

**参数：**
- `method_name`: HTTP 方法名称，例如 `'GET'`
- `method`: 可调用的异步处理函数

##### `dispatch(self) -> Awaitable[Response]`
根据当前请求的 `request.method` 分发到对应处理方法。

**逻辑流程：**
1. 获取当前请求方法的小写形式
2. 查找已注册的方法
3. 若无匹配方法，抛出 `HTTPMethodNotAllowed`
4. 否则调用并返回对应方法的结果

**返回值：**
- `Response` 对象（通常为 `json_response`）

**异常：**
- `HTTPMethodNotAllowed`：当请求方法未被实现时抛出

---

### `DBCrud(RestEndpoint)`

继承自 `RestEndpoint`，实现针对特定数据库表的 CRUD 操作。

#### 构造函数
```python
def __init__(self, request: Request, dbname: str, tablename: str, id=None)
```

**参数：**
- `request (aiohttp.web_request.Request)`：当前 HTTP 请求对象
- `dbname (str)`：数据库标识名（需在配置中定义）
- `tablename (str)`：目标数据表名
- `id (optional)`：可选资源 ID（当前未实际使用）

**初始化行为：**
- 调用父类构造函数
- 初始化数据库连接池实例 `DBPools()`
- 设置上下文属性以便后续操作使用

---

## 支持的 HTTP 方法

### `OPTIONS` — 获取元信息
```python
async def options(self) -> Response
```
获取指定表的元数据结构（字段、类型等）。

**行为：**
- 使用 `sor.I(tablename)` 获取表结构信息（I 表示 "Inspect"）
- 成功返回元数据
- 失败返回错误码 `'metaerror'`

**返回示例（成功）：**
```json
{
  "ret": "success",
  "data": {
    "fields": [
      {"name": "id", "type": "int"},
      {"name": "name", "type": "varchar"}
    ]
  }
}
```

**错误响应：**
```json
{
  "ret": "error",
  "errno": "metaerror",
  "msg": "get metadata error"
}
```

---

### `GET` — 查询数据
```python
async def get(self) -> Response
```
从表中查询符合条件的数据记录。

**行为：**
- 解析 URL 查询参数（`request.query`）为标准字典
- 调用 `sor.R(tablename, conditions)` 执行读取操作（R 表示 "Read"）
- 返回查询结果列表或单条记录

**输入示例：**
```
GET /api/user?age__gt=18&name__like=john
```

**返回示例：**
```json
{
  "ret": "success",
  "data": [
    {"id": 1, "name": "John", "age": 25}
  ]
}
```

**错误响应：**
```json
{
  "ret": "error",
  "errno": "search error",
  "msg": "search error"
}
```

---

### `POST` — 插入数据
```python
async def post(self) -> Response
```
向表中插入新记录。

**行为：**
- 读取表单格式请求体（`await request.post()`）
- 转换为字典格式
- 调用 `sor.C(tablename, data)` 执行创建操作（C 表示 "Create"）
- 返回插入后的主键或其他信息

**输入示例（Form Data）：**
```
name=John&age=30
```

**返回示例：**
```json
{
  "ret": "success",
  "data": {"id": 123}
}
```

**错误响应：**
```json
{
  "ret": "error",
  "errno": "add error",
  "msg": "add error"
}
```

---

### `PUT` — 更新数据
```python
async def put(self) -> Response
```
更新已有记录。

**行为：**
- 读取表单请求体作为更新字段
- 调用 `sor.U(tablename, data)` 执行更新操作（U 表示 "Update"）
- 成功返回空格字符串（应优化为更合理的内容）

⚠️ **注意：** 当前实现无法指定更新哪条记录（缺少 `WHERE` 条件），可能导致全表更新！

**建议改进：**
- 应结合路径参数或 body 中包含主键进行条件更新

**返回示例：**
```json
{
  "ret": "success",
  "data": " "
}
```

**错误响应：**
```json
{
  "ret": "error",
  "errno": "update error",
  "msg": "update error"
}
```

---

### `DELETE` — 删除数据
```python
async def delete(self, request: Request, instance_id) -> Response
```

> ❗ **存在问题：** 方法签名不一致！  
> 实际被调用时不会传入 `request` 和 `instance_id`，且未重写 `dispatch` 来传递这些参数。此方法目前无法正常工作。

**预期行为：**
- 通过查询参数或路径变量确定删除条件
- 调用 `sor.D(tablename, conditions)` 删除记录（D 表示 "Delete"）

**当前问题：**
- 多余的参数 `request`, `instance_id` 不会被自动传入
- 错误码拼写错误：`erron` → 应为 `errno`
- 删除逻辑仍依赖 `query` 参数，但缺乏安全校验

**修复建议：**
```python
async def delete(self):
    try:
        ns = multiDict2Dict(self.request.query)
        if not ns:
            return json_response(Error(errno='delete_error', msg='no condition provided'))
        with self.db.sqlorContext(self.dbname) as sor:
            d = await sor.D(self.tablename, ns)
        return json_response(Success(d))
    except Exception as e:
        traceback.print_exc()
        return json_response(Error(errno='delete_error', msg='delete failed'))
```

---

## 使用示例

假设你有一个名为 `users` 的表，在 `mydb` 数据库中：

```python
from aiohttp import web
from .dbcrud import DBCrud

async def handle_user_crud(request):
    dbname = "mydb"
    tablename = "users"
    crud = DBCrud(request, dbname, tablename)
    return await crud.dispatch()

# 在路由中注册
app.router.add_route('*', '/api/users', handle_user_crud)
app.router.add_route('*', '/api/users/{id}', handle_user_crud)
```

---

## 异常处理

所有方法均使用 `try...except` 包裹核心逻辑：

- 打印异常信息至控制台
- 输出完整堆栈跟踪（`traceback.print_exc()`）
- 返回统一格式的 JSON 错误响应

> ⚠️ 注意：生产环境中不应暴露详细错误信息给客户端

---

## 已知问题与改进建议

| 问题 | 描述 | 建议修复 |
|------|------|---------|
| `delete()` 方法参数错误 | 多余参数导致无法正确调用 | 移除额外参数，保持无参签名 |
| `errno` 拼写错误 | `erron='delete error'` | 改为 `errno` |
| `PUT` 缺少更新条件 | 易造成误删/误更 | 结合路径 ID 或强制要求 `id` 字段 |
| 成功响应内容不合理 | 如 `Success(' ')` | 改为 `{ "updated": 1 }` 等有意义数据 |
| 日志仅打印未记录 | 使用 `logging` 替代 `print` | 引入 logger 模块 |
| 未验证输入合法性 | 可能引发 SQL 注入风险 | 添加字段白名单或校验机制 |

---

## 总结

`DBCrud` 是一个轻量级的数据库 REST 接口封装，适用于快速构建基于表的 API 接口。其设计简洁、扩展性强，但在健壮性和安全性方面仍有提升空间。

适合场景：
- 快速原型开发
- 内部管理系统后端
- 动态表驱动接口服务

不适合场景：
- 高安全性要求系统
- 复杂业务逻辑接口
- 需要精细权限控制的环境

---

## 版本信息

- **语言**：Python 3.7+
- **框架**：aiohttp >= 3.0
- **作者**：Auto-generated from source code
- **最后更新**：2025-04-05

--- 

📌 *注：本技术文档由代码反向生成，建议结合实际项目需求补充单元测试和接口文档（如 Swagger/OpenAPI）*。