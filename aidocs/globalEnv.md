# 技术文档：Web 应用核心工具模块

```markdown
# Web 核心工具模块技术文档

> **文件编码**：UTF-8  
> **语言**：Python 3.7+（基于 `aiohttp` 异步框架）  
> **用途**：为异步 Web 服务提供通用工具函数、配置管理、安全处理、文件操作及数据库上下文支持。

---

## 模块概览

该模块是 Web 后端系统的核心基础组件，封装了以下功能：

- HTTP 错误响应生成
- 文件读写与下载控制
- 数据导出为 Excel
- 配置读取与动态变量替换
- 密码加解密
- 全局环境初始化
- 数据库连接池集成
- 流式响应支持
- 安全路径校验机制

适用于基于 `aiohttp` 构建的异步 Web 服务架构。

---

## 依赖说明

### 第三方库

| 包名 | 用途 |
|------|------|
| `aiohttp` | 异步 Web 服务框架 |
| `aiohttp-session` | Session 管理 |
| `openpyxl` | Excel 文件生成 |
| `asyncio` | 异步编程支持 |

### 内部模块

| 模块路径 | 功能 |
|--------|------|
| `appPublic.*` | 公共工具类（配置、日志、编码、时间等） |
| `sqlor.*` | 数据库抽象层（ORM/查询构造器） |
| `.xlsxData` | Excel 数据解析器 |
| `.uriop` | URI 操作接口 |
| `.error` | 自定义错误类型封装 |
| `.filetest`, `.filedownload`, `.filestorage` | 文件相关操作 |
| `.serverenv` | 服务器运行环境单例 |

---

## 函数与类详解

### `server_error(errcode)`
根据 HTTP 状态码抛出对应的 `aiohttp.web.HTTPException`。

#### 参数：
- `errcode` (int): HTTP 状态码（如 404, 500）

#### 支持状态码列表：
| 状态码 | 异常类 |
|-------|--------|
| 400 | `HTTPBadRequest` |
| 401 | `HTTPUnauthorized` |
| 403 | `HTTPForbidden` |
| 404 | `HTTPNotFound` |
| 405 | `HTTPMethodNotAllowed` |
| 408 | `HTTPRequestTimeout` |
| 409 | `HTTPConflict` |
| 410 | `HTTPGone` |
| 415 | `HTTPUnsupportedMediaType` |
| 429 | `HTTPTooManyRequests` |
| 500 | `HTTPInternalServerError` |
| 502 | `HTTPBadGateway` |
| 503 | `HTTPServiceUnavailable` |

> 默认返回 `HTTPException`，其他未列状态码也映射为此类。

---

### `basic_auth_headers(user, passwd)`
生成用于 Basic Auth 的请求头。

#### 参数：
- `user` (str): 用户名
- `passwd` (str): 密码

#### 返回值：
```python
{
    "Authorization": "Basic base64encoded"
}
```

---

### `stream_response(request, async_data_generator, content_type='text/html')`
异步流式响应处理器，用于大内容或实时数据传输。

#### 参数：
- `request`: aiohttp 请求对象
- `async_data_generator`: 异步生成器函数（`async def()`），产出 `bytes`, `str` 或 JSON 对象
- `content_type` (str): 响应内容类型，默认 `'text/html'`

#### 行为：
- 自动判断输出类型并编码为 UTF-8
- 出错时记录异常并通过 `write_eof()` 结束流
- 支持 JSON 直接序列化（非 ASCII 不转义）

> ⚠️ 注意：若生成器内部报错会中断流并抛出异常。

---

### `data2xlsx(rows, headers=None)`
将数据行列表导出为临时 `.xlsx` 文件。

#### 参数：
- `rows`: 字典列表，例如 `[{'name': 'Alice', 'age': 30}]`
- `headers`: 列定义列表，每个元素可含 `.name` 和 `.title` 属性

#### 返回值：
- 生成的 `.xlsx` 文件绝对路径（使用 `tempfile.mktemp` 创建）

> 使用 `openpyxl` 写入，自动关闭工作簿。建议后续由调用方清理临时文件。

---

### `save_file(str_or_bytes, filename)`
异步保存字符串或字节到文件存储系统。

#### 参数：
- `str_or_bytes`: 要保存的内容（`str` 或 `bytes`）
- `filename`: 文件名（带扩展名）

#### 返回值：
- 存储结果信息（由 `FileStorage.save()` 定义）

> 封装了异步 IO 操作，适合上传场景。

---

### `webpath(path)` / `realpath(path)`
获取文件在 Web 中的访问路径和实际物理路径。

#### 参数：
- `path` (str): 相对路径

#### 返回值：
- `webpath`: 可通过浏览器访问的 URL 路径
- `realpath`: 服务器上的真实文件系统路径

> 基于 `FileStorage` 实现路径映射。

---

### `FileOutZone(fp)`
自定义异常类，防止越权访问文件系统目录。

#### 触发条件：
当尝试打开的文件不在允许目录范围内时抛出。

#### 属性：
- `openfilename`: 被拒绝访问的文件路径

---

### `get_config_value(kstr)`
从全局配置中按点分键获取嵌套值。

#### 示例：
```python
get_config_value("database.host") 
# => getConfig().get('database').get('host')
```

#### 返回值：
- 成功找到则返回对应值
- 找不到任一级键则返回 `None`

---

### `get_definition(k)`
快捷方式获取配置中的 `definitions.{k}` 节点。

#### 示例：
```python
get_definition("userSchema")
# 等价于 get_config_value("definitions.userSchema")
```

---

### `abspath(path)`
根据配置中的网站根路径查找文件的实际路径。

#### 配置要求：
- `config.website.paths`: 字符串路径列表（相对或绝对）
- 尝试拼接每个根路径 + 输入 path，检查是否存在

#### 返回值：
- 找到存在的文件则返回其完整路径
- 否则返回 `None`

---

### `openfile(url, m)`
安全地打开一个本地文件，具备路径白名单校验。

#### 参数：
- `url` (str): 相对路径（相对于 `website.paths` 或 `allow_folders`）
- `m` (str): 文件打开模式（如 `'r'`, `'rb'`）

#### 安全校验流程：
1. 解析为绝对路径（通过 `abspath`）
2. 获取所有允许的根目录（包括 `website.paths` 和 `allow_folders`）
3. 检查目标路径是否以任意允许目录开头
4. 若不满足，抛出 `FileOutZone`

> 防止路径穿越攻击（如 `../../../etc/passwd`）

---

### `isNone(a)`
辅助函数，判断变量是否为 `None`。

#### 返回值：
- `True` if `a is None`
- `False` otherwise

> 主要用于模板引擎或表达式中避免语法限制。

---

### `appname()`
获取当前应用名称。

#### 来源：
- `config.license.app`
- 失败时返回默认 `"test app"`

---

### `configValue(ks)`
执行类似 `eval('config' + ks)` 的安全配置提取。

#### 示例：
```python
configValue(".database.port") 
# => getConfig().database.port
```

> ⚠️ 警告：存在潜在代码注入风险，请确保输入可信！

---

### `visualcoding()`
获取配置项 `config.website.visualcoding` 的值。

通常用于前端可视化开发开关。

---

### `file_download(request, path, name, coding='utf8')`
【已弃用】同步方式发送文件给客户端（兼容旧版 Twisted 风格 API）

#### 参数：
- `request`: 请求对象（需有 `setHeader`, `write`, `finish` 方法）
- `path`: 文件相对路径
- `name`: 下载显示名称
- `coding`: 名称编码格式（默认 UTF-8）

#### 设置响应头：
- `Content-Disposition: attachment; filename=...`
- 缓存控制、内容长度、二进制传输标识等

> ❌ 不推荐新代码使用，建议改用 `path_download` 或流式方案。

---

### `paramify(data, ns)`
使用模板语法 `${key}$` 替换数据中的占位符。

#### 参数：
- `data`: 包含占位符的字符串或结构化数据（dict/list）
- `ns`: 命名空间（dict），提供替换值

#### 示例：
```python
paramify("Hello ${name}$!", {"name": "World"})
# => "Hello World!"
```

> 支持嵌套结构递归替换。

---

### `password_encode(s)` / `password_decode(c)`
RC4 加密/解密封装。

#### 密钥来源：
- `config.password_key`
- 默认密钥：`QRIVSRHrthhwyjy176556332`

#### 用途：
- 敏感字段加密存储（如密码、token）
- 安全参数传递

---

### `@asynccontextmanager sqlorContext(module)`
异步上下文管理器，获取指定模块关联数据库的 `SqlOR` 实例。

#### 工作流程：
1. 获取 `DBPools` 连接池
2. 查询 `ServerEnv` 中模块对应的数据库名
3. 获取该库的 ORM 上下文（`sor`）

#### 使用示例：
```python
async with sqlorContext('user') as sor:
    users = await sor.select('users', cond={'active': True})
```

---

### `initEnv()`
初始化全局运行环境（`ServerEnv` 单例），注入大量工具函数与常量。

#### 注入内容分类：

| 类别 | 示例 |
|------|------|
| 工具函数 | `paramify`, `data2xlsx`, `uuid` |
| 时间处理 | `curDateString`, `str2date`, `timestampstr` |
| 数据结构 | `DictObject`, `uObject` |
| 文件操作 | `abspath`, `openfile`, `webpath` |
| 数据库 | `DBPools`, `DBFilter` |
| 错误类 | `Success`, `Error`, `NeedLogin` |
| HTTP 工具 | `HttpClient`, `StreamHttpClient`, `basic_auth_headers` |
| 异步支持 | `async_sleep`, `stream_response` |
| 其他 | `rfexe`（注册函数执行器） |

> 此函数应在应用启动时调用一次。

---

### `set_builtins()`
将 Python 内置函数（如 `print`, `len`, `isinstance`）注入到 `ServerEnv()` 全局命名空间。

#### 实现原理：
- 遍历 `builtins` 模块公开符号
- 使用 `exec()` 动态绑定至 `g[key] = builtin_func`

#### 示例效果：
```python
g = ServerEnv()
g.print("Hello")  # 实际调用内置 print
g.len([1,2,3])    # 调用内置 len
```

> 便于在模板或 DSL 中统一访问内置函数。

---

## 使用建议

### ✅ 推荐实践
- 使用 `initEnv()` 初始化全局环境后，可通过 `ServerEnv()` 统一获取工具集
- 文件下载优先使用 `path_download` 或 `file_download`（新版本）
- 敏感数据加解密务必使用 `password_encode/decode`
- 大数据响应使用 `stream_response` 避免内存溢出

### ⚠️ 注意事项
- `configValue()` 使用 `eval`，请严格验证输入
- `mktemp()` 在高并发下可能有命名冲突风险，建议升级为 `NamedTemporaryFile(delete=False)`
- `file_download` 当前实现依赖非标准接口（`setHeader`），仅适配特定框架

---

## 示例：导出用户数据为 Excel 并下载

```python
async def export_users(request):
    env = ServerEnv()
    
    # 查询数据
    async with env.sqlorContext('user') as sor:
        rows = await sor.select('users', fields=['id', 'name', 'email'])

    # 定义表头
    headers = [
        {'name': 'id', 'title': '编号'},
        {'name': 'name', 'title': '姓名'},
        {'name': 'email', 'title': '邮箱'}
    ]

    # 生成 Excel
    xlsx_path = env.data2xlsx(rows, headers)

    # 返回文件下载
    return await env.path_download(request, xlsx_path, '用户列表.xlsx')
```

---

## 版本信息

- **创建日期**：未知（根据代码风格推测为 2020~2022）
- **维护状态**：活跃使用中
- **作者**：内部团队开发（依赖 `appPublic`, `sqlor` 私有库）

---

## 附录 A：HTTP 状态码映射表

| Code | Meaning | Exception Class |
|------|---------|------------------|
| 400 | Bad Request | HTTPBadRequest |
| 401 | Unauthorized | HTTPUnauthorized |
| 403 | Forbidden | HTTPForbidden |
| 404 | Not Found | HTTPNotFound |
| 405 | Method Not Allowed | HTTPMethodNotAllowed |
| 408 | Timeout | HTTPRequestTimeout |
| 409 | Conflict | HTTPConflict |
| 410 | Gone | HTTPGone |
| 415 | Unsupported Media Type | HTTPUnsupportedMediaType |
| 429 | Too Many Requests | HTTPTooManyRequests |
| 500 | Internal Error | HTTPInternalServerError |
| 502 | Bad Gateway | HTTPBadGateway |
| 503 | Service Unavailable | HTTPServiceUnavailable |

---

## 附录 B：全局环境注入清单（部分）

| 名称 | 类型 | 来源 |
|------|------|------|
| `json` | module | built-in |
| `time` | module | built-in |
| `random` | module | built-in |
| `datetime` | module | built-in |
| `paramify` | function | local |
| `curDateString` | function | timeUtils |
| `getID` | function | uniqueID |
| `Error`, `Success` | class | .error |
| `HttpClient` | class | httpclient |
| `stream_response` | coroutine | local |
| `DBPools` | class | sqlor.dbpools |

> 完整列表见 `initEnv()` 函数体。

---
```

> 📝 文档结束。此文档可用于团队 Wiki、API 手册或项目交接资料。