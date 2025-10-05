# DBAdmin 模块技术文档

## 概述

`DBAdmin` 是一个基于 `aiohttp` 的异步 Web 处理类，用于对数据库表进行基础的管理操作（如浏览、添加、更新、过滤等）。该模块通过封装 `CRUD` 类实现与数据库的交互，并提供统一的 JSON 响应格式。支持错误处理和日志记录，适用于构建轻量级的数据库管理接口。

---

## 依赖说明

### 第三方库
- `aiohttp`: 异步 Web 框架，用于处理 HTTP 请求和响应。
- `sqlor.crud.CRUD`: 提供数据库表的增删改查功能。

### 内部模块（来自项目）
- `appPublic.dictObject.multiDict2Dict`: 将多值字典转换为普通字典（通常用于处理表单或查询参数）。
- `appPublic.jsonConfig.getConfig`: 加载配置文件。
- `appPublic.log`: 日志工具，提供 `info`, `debug`, `warning`, `error`, `critical`, `exception` 等日志级别输出。

---

## 核心变量

```python
actions = ["browse", "add", "update", "filter"]
```

定义了系统支持的操作类型列表。任何不在该列表中的操作将返回 `404 Not Found` 错误。

> ⚠️ 注意：目前未实现 `delete` 操作。

---

## 类定义：`DBAdmin`

### 类签名

```python
class DBAdmin:
    def __init__(self, request: Request, dbname: str, tablename: str, action: str):
        ...
```

#### 参数说明

| 参数名 | 类型 | 描述 |
|-------|------|------|
| `request` | `aiohttp.web_request.Request` | 当前 HTTP 请求对象 |
| `dbname` | `str` | 数据库名称 |
| `tablename` | `str` | 表名称 |
| `action` | `str` | 要执行的操作（必须是 `actions` 列表中的一项） |

#### 初始化逻辑

1. 验证 `action` 是否在允许的操作列表中：
   - 若不合法，记录调试日志并抛出 `HTTPNotFound`。
2. 实例化 `CRUD(dbname, tablename)`：
   - 成功则保存为 `self.crud`
   - 失败则捕获异常，打印堆栈，记录错误日志，并抛出 `HTTPNotFound`

> 💡 使用 `CRUD` 类来抽象底层数据库访问，提升可维护性。

---

### 方法：`render() -> Response`

异步方法，根据初始化时指定的动作生成响应内容。

#### 返回值

- 返回一个 `aiohttp.web_response.Response` 对象，通常是 JSON 格式响应。

#### 逻辑流程

```python
async def render(self) -> Response:
    try:
        d = await self.crud.I()  # 获取元数据
        return json_response(Success(d))
    except Exception as e:
        exception('except=%s' % e)
        traceback.print_exc()
        return json_response(Error(errno='metaerror', msg='get metadata error'))
```

#### 当前行为说明

⚠️ **注意：当前 `render()` 方法的行为是固定的 —— 只调用 `self.crud.I()` 获取表的元数据信息（metadata），无论 `action` 是什么！**

这表明代码尚未完成不同操作的分支处理。

##### 正常情况
- 调用 `CRUD.I()` 方法获取表结构或元数据。
- 包装成 `Success(data)` 并以 JSON 形式返回。

##### 异常情况
- 捕获任意异常，记录详细错误日志（含堆栈跟踪）。
- 返回标准错误 JSON：`Error(errno='metaerror', msg='get metadata error')`

---

## 错误处理机制

### 抛出的 HTTP 异常
- `HTTPNotFound`: 
  - 动作无效
  - CRUD 初始化失败
- `HTTPForbidden`, `HTTPMethodNotAllowed`, `HTTPExpectationFailed` 等导入但未使用（可能是预留扩展）

### 自定义响应对象
- `Success(data)`: 成功响应包装器
- `Error(errno, msg)`: 错误响应包装器  
  （来自 `.error` 模块，需确保已正确定义）

---

## 示例请求流程

假设有一个路由匹配如下 URL：

```
/dbadmin/{dbname}/{tablename}/{action}
```

当收到请求 `/dbadmin/mydb/users/browse` 时：

1. 解析路径参数：
   ```python
   dbname = "mydb"
   tablename = "users"
   action = "browse"
   ```
2. 创建 `DBAdmin(request, "mydb", "users", "browse")`
3. 初始化成功后调用 `await dbadmin.render()`
4. 返回类似：
   ```json
   {
     "success": true,
     "data": { ... }  // 元数据信息
   }
   ```

如果 `action="invalid"`，则直接抛出 `HTTPNotFound`。

---

## 已知问题与待改进点

| 问题 | 描述 | 建议 |
|------|------|------|
| ❌ 动作未分发 | 所有动作都执行 `I()` 方法，未真正实现 `add`, `update`, `browse`, `filter` | 应使用条件判断或策略模式分发不同逻辑 |
| ⚠️ 错误码单一 | 所有元数据错误均返回 `metaerror` | 应细化错误类型（如连接失败、权限不足等） |
| 🔒 安全性缺失 | 无身份验证或权限控制 | 建议增加认证中间件或检查逻辑 |
| 📦 日志冗余 | 多处使用 `traceback.print_exc()`，同时有 `exception()` 记录 | 推荐仅使用 `exception()` 即可 |
| 🧩 不完整实现 | `filter`, `add`, `update` 无实际逻辑 | 需补充对应 `CRUD` 方法调用 |

---

## 改进建议示例（伪代码）

```python
async def render(self):
    try:
        if self.action == "browse":
            data = await self.crud.read()
        elif self.action == "add":
            data = await self.crud.create(await self.request.json())
        elif self.action == "update":
            data = await self.crud.update(await self.request.json())
        elif self.action == "filter":
            query = multiDict2Dict(self.request.query)
            data = await self.crud.filter(query)
        else:
            raise HTTPNotFound()

        return json_response(Success(data))

    except HTTPException:
        raise
    except Exception as e:
        exception(f"DBAdmin render error: {e}")
        return json_response(Error(errno="server_error", msg="Internal server error"))
```

---

## 总结

`DBAdmin` 是一个初步搭建的数据库管理处理器框架，具备良好的模块化结构和异常处理能力。当前主要问题是**功能未完整实现**，所有操作均退化为获取元数据。

✅ 优势：
- 清晰的职责划分
- 统一错误响应格式
- 支持异步非阻塞 I/O

🔧 待完善：
- 实现各操作的具体逻辑
- 添加输入校验与安全控制
- 细化错误分类与日志管理

建议后续按 RESTful 风格设计接口，结合 `POST`, `GET`, `PUT`, `DELETE` 方法映射到对应 CRUD 操作。