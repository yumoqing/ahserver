# `ProcessorResource` 技术文档

> 基于 `aiohttp` 的异步 Web 资源处理器，支持多类型文件与动态内容处理的扩展静态资源类。

---

## 概述

`ProcessorResource` 是一个继承自 `aiohttp.web_urldispatcher.StaticResource` 并混合了自定义路径映射功能（`Url2File`）的类。它用于统一处理静态资源请求，并根据文件后缀或 URL 前缀自动选择对应的**处理器（Processor）**来执行动态逻辑，如模板渲染、数据库操作、LLM 接口调用等。

该类增强了标准静态资源服务的能力，使其能够无缝集成：

- 动态页面处理（`.html`, `.py`, `.md` 等）
- 数据源接口（SQL/XLSX）
- LLM 调用
- WebSocket 支持
- RESTful CRUD 操作
- 文件上传/下载
- 用户认证与会话管理
- 国际化（i18n）

---

## 依赖说明

### 第三方库
| 包 | 用途 |
|----|------|
| `aiohttp` | 异步 HTTP 服务器框架 |
| `aiohttp_auth` | 请求认证中间件 |
| `aiohttp_session` | Session 管理 |
| `yarl.URL` | URL 解析工具 |
| `ssl` | HTTPS 安全连接支持 |
| `asyncio`, `aiofiles` | 异步 I/O 操作 |

### 内部模块（`appPublic` 和项目本地模块）
| 模块 | 用途 |
|------|------|
| `appPublic.jsonConfig.getConfig` | 全局配置加载 |
| `appPublic.i18n.getI18N` | 多语言支持 |
| `appPublic.dictObject.DictObject`, `multiDict2Dict` | 字典封装与请求参数解析 |
| `appPublic.timecost.TimeCost` / `timeUtils.timestampstr` | 性能监控与时间处理 |
| `appPublic.log.*` | 日志输出函数 |
| `.baseProcessor.*` | 核心处理器基类及实现 |
| `.xlsxdsProcessor.XLSXDataSourceProcessor` | Excel 数据源处理器 |
| `.llmProcessor.Llm*Processor` | 大模型接口处理器 |
| `.websocketProcessor.WebsocketProcessor` | WebSocket 处理器 |
| `.xtermProcessor.XtermProcessor` | 终端模拟处理器 |
| `.sqldsProcessor.SQLDataSourceProcessor` | SQL 数据源处理器 |
| `.functionProcessor.FunctionProcessor` | 自定义函数处理器 |
| `.proxyProcessor.ProxyProcessor` | 反向代理处理器 |
| `.serverenv.ServerEnv` | 服务端全局环境变量存储 |
| `.url2file.Url2File` | URL 到文件系统路径转换 |
| `.filestorage.FileStorage` | 文件上传持久化 |
| `.restful.DBCrud` | 数据库 RESTful 接口 |
| `.dbadmin.DBAdmin` | 数据库管理后台 |
| `.filedownload.file_download`, `path_decode` | 文件下载与解码 |
| `.auth_api.*` | 登录/登出/用户信息获取接口 |

---

## 函数详解

### `getHeaderLang(request: Request) → str`
从请求头中提取客户端首选语言。

#### 参数
- **request**: `aiohttp.web.Request` 对象

#### 返回值
- `str`: 如 `'zh-CN'` 或默认 `'en'`

#### 示例
```python
lang = getHeaderLang(request)  # 返回 'zh-CN'
```

---

### `i18nDICT(request: Request) → bytes`
返回当前语言环境下的国际化字典 JSON 编码后的字节串。

#### 参数
- **request**: 请求对象

#### 返回值
- `bytes`: JSON 格式的 i18n 字典，使用网站编码（如 UTF-8）

#### 流程
1. 获取 Accept-Language
2. 查找 langMapping 映射（如 `zh-CN → zh`）
3. 加载对应语言词典并序列化为 JSON

---

## 类：`ProcessorResource`

### 继承关系
```python
class ProcessorResource(StaticResource, Url2File)
```

提供增强型静态资源服务 + 动态处理器路由机制。

---

### 构造方法：`__init__`

```python
def __init__(
    self,
    prefix: str,
    directory: PathLike,
    *,
    name: Optional[str] = None,
    expect_handler: Optional[_ExpectHandler] = None,
    chunk_size: int = 256 * 1024,
    show_index: bool = False,
    follow_symlinks: bool = False,
    append_version: bool = False,
    indexes: list = [],
    processors: dict = {}
)
```

#### 参数说明

| 参数 | 类型 | 描述 |
|------|------|------|
| `prefix` | `str` | URL 前缀，如 `/static/` |
| `directory` | `PathLike` | 静态文件根目录路径 |
| `name` | `Optional[str]` | 路由名称（可选） |
| `expect_handler` | `_ExpectHandler` | Expect 头处理回调（高级用法） |
| `chunk_size` | `int` | 文件读取分块大小，默认 256KB |
| `show_index` | `bool` | 是否显示目录索引页 |
| `follow_symlinks` | `bool` | 是否允许符号链接 |
| `append_version` | `bool` | 是否附加版本号防止缓存 |
| `indexes` | `list` | 自定义索引文件名列表（如 `['index.html']`） |
| `processors` | `dict` | 文件扩展名 → 处理器名称映射表 |

#### 初始化行为
- 调用父类 `StaticResource.__init__()` 设置静态资源基础属性
- 初始化 `Url2File` 实现 URL 到文件路径映射
- 将所有 HTTP 方法（POST/PUT/OPTIONS 等）指向 GET 路由处理器
- 创建运行时环境容器 `self.y_env`（`DictObject`）

---

### 属性

| 属性 | 类型 | 描述 |
|------|------|------|
| `y_processors` | `dict` | 扩展名 → 处理器名称映射 |
| `y_directory` | `PathLike` | 文件目录 |
| `y_prefix` | `str` | URL 前缀 |
| `y_indexes` | `list` | 索引文件名列表 |
| `y_env` | `DictObject` | 运行时上下文环境，供处理器访问 |

---

### 方法

#### `setProcessors(processors: dict)`
更新处理器映射表。

#### `setIndexes(indexes: list)`
设置索引文件名列表。

---

#### `abspath(request: Request, path: str) → str`
将相对路径转为绝对文件系统路径。

##### 示例
```python
fname = resource.abspath(request, "/js/app.js")
# 输出类似：/var/www/static/js/app.js
```

---

#### `getPostData(request: Request) → DictObject`
异步解析 POST 请求数据，支持：
- 表单 (`application/x-www-form-urlencoded`)
- 多部分表单 (`multipart/form-data`) —— 含文件上传
- JSON 正文 (`application/json`)
- 查询参数合并

##### 返回值
- `DictObject`: 类字典对象，支持点语法访问字段

##### 特性
- 文件上传自动保存到 `FileStorage`，返回存储路径
- 数组字段自动合并（同名多次提交）
- 错误捕获并打印堆栈但不中断流程

---

#### `parse_request(request: Request)`
解析真实客户端请求的协议、主机、端口和前置路径，考虑反向代理头：

- `X-Forwarded-Scheme`
- `X-Forwarded-Host`
- `X-Forwarded-Port`
- `X-Forwarded-Prepath`

结果保存在 `self._scheme`, `self._host`, `self._port`, `self._prepath`, `self._preurl` 中。

> ⚠️ 用于构建完整外部可见 URL。

---

#### `async _handle(request: Request) → StreamResponse`
核心请求处理器，重写了 `StaticResource._handle`。

##### 处理流程

1. **初始化客户端类型检测**
   - 通过 User-Agent 判断设备类型（iPhone/iPad/Android/PC）
   - 存入 `y_env.terminalType`

2. **构建运行时环境 `y_env`**
   提供以下便捷函数给处理器使用：

   | 函数名 | 作用 |
   |--------|------|
   | `redirect(url)` | 302 跳转 |
   | `remember_user(userid, ...)` | 登录用户 |
   | `forget_user()` | 注销用户 |
   | `get_user()` / `get_username()` / `get_userinfo()` | 获取用户信息 |
   | `get_ticket()` / `remember_ticket(ticket)` | 认证票据操作 |
   | `i18n(text)` | 文本国际化翻译 |
   | `i18nDict()` | 获取当前语言词典 JSON |
   | `request2ns()` | 获取解析后的请求参数 |
   | `entire_url(path)` | 生成完整 URL |
   | `websocket_url(path)` | 生成 ws:// 或 wss:// URL |
   | `abspath(path)` | 获取文件绝对路径 |
   | `path_call(path, params)` | 调用其他路径的处理器 |
   | `aiohttp_client` | 原生 aiohttp 客户端实例 |
   | `resource` | 当前资源对象引用 |

3. **特殊路径预处理**

   | 条件 | 动作 |
   |------|------|
   | 路径以 `config.website.dbadm` 开头 | 调用 `DBAdmin` 提供数据库管理界面 |
   | 路径以 `config.website.dbrest` 开头 | 调用 `DBCrud` 实现 RESTful 接口 |
   | 路径以 `config.website.download` 开头 | 触发安全文件下载 |

4. **处理器匹配流程**

   ```text
   url → 文件路径 → 匹配处理器规则 → 执行 handle()
   ```

   - 使用 `url2processor()` 按扩展名或前缀查找处理器
   - 若找到，则执行 `processor.handle(request)`
   - 否则尝试作为 HTML 页面处理（检查是否含 `<html>` 或 `<!DOCTYPE html>`）
   - 最后交由父类当作普通静态文件处理

5. **目录访问控制**
   - 若请求的是目录且 `allowListFolder=False`，抛出 `HTTPNotFound`

---

#### `url2processor(request, url, fpath) → Processor or None`
根据 URL 或文件路径决定应使用的处理器。

##### 匹配优先级
1. **前缀匹配**：遍历 `config.website.startswiths`，若 URL 路径匹配某 leading 前缀，使用 `FunctionProcessor`
2. **后缀匹配**：遍历 `self.y_processors`，若文件路径以特定扩展名结尾，实例化对应处理器

##### 返回值
- 成功：返回处理器实例（如 `TemplateProcessor`, `PythonScriptProcessor` 等）
- 失败：返回 `None`

---

#### `entireUrl(request, url) → str`
将相对或绝对 URL 转换为完整的外部可访问 URL。

##### 支持输入形式
- 绝对 URL：`https://example.com/path` → 不变
- 斜杠开头：`/api/data` → 结合 `X-Forwarded-*` 头拼接成完整地址
- 相对路径：`../img/logo.png` → 相对于当前请求路径计算

##### 协议升级
- 自动将 `http://` → `ws://`
- `https://` → `wss://`（WebSocket 场景）

---

#### `websocketUrl(request, url) → str`
专门用于生成 WebSocket 协议 URL。

##### 示例
```python
ws_url = res.websocketUrl(req, "/ws/chat")
# 结果可能是：wss://example.com/ws/chat （如果原请求是 HTTPS）
```

---

#### `urlWebsocketify(url) → str`
确保 `.ws` 或 `.wss` 结尾的 URL 使用正确的 WebSocket 协议。

---

#### `url2path(url) → str`
从完整 URL 中剥离协议+主机部分，得到路径。

##### 示例
```python
self._preurl = "https://example.com/app"
url2path("https://example.com/app/js/main.js") → "/js/main.js"
```

---

#### `async path_call(request, path, params={}) → Any`
在内部调用另一个路径的处理器，可用于模块化组合逻辑。

##### 参数
- `path`: 目标路径（如 `/api/user/info`）
- `params`: 附加参数字典

##### 流程
1. 转换为完整 URL
2. 解析为本地文件路径
3. 查找对应处理器
4. 调用其 `be_call(request, params)` 方法

> 适用于跨模块调用、API 组合场景。

---

#### `async isHtml(fn) → bool`
判断文件是否为 HTML 文件（基于内容而非扩展名）。

##### 判断依据
- 忽略开头空白字符
- 内容以 `<html>` 或 `<!DOCTYPE html>` 开始（忽略大小写）

---

#### `html_handle(request, filepath) → Response`
手动渲染 HTML 文件响应，设置正确头部。

##### 设置 Headers
```http
Content-Type: text/html; charset=utf-8
Accept-Ranges: bytes
Content-Length: [file size]
```

> ⚠️ 注意：此处 header 中 `utf-8` 应移至 `charset=utf-8` 更规范。

---

#### `gethost(request) → str`
获取请求的真实 Host，优先使用代理头。

顺序：
1. `X-Forwarded-Host`
2. `Host`
3. 从 `request.url` 解析

---

## 配置要求（来自 `getConfig()`）

`ProcessorResource` 依赖如下配置项（通常位于 `config.json`）：

```json
{
  "website": {
    "coding": "utf-8",
    "port": 8080,
    "allowListFolder": false,
    "dbadm": "/_dbadmin/",
    "dbrest": "/_dbrest/",
    "download": "/_download/",
    "startswiths": [
      { "leading": "/_func/" }
    ],
    "langMapping": {
      "zh-CN": "zh",
      "en-US": "en"
    }
  }
}
```

---

## 使用示例

### 注册路由
```python
from aiohttp import web

processors = {
    '.py': 'PythonScript',
    '.md': 'Markdown',
    '.xlsx': 'XLSXDataSource'
}

resource = ProcessorResource('/site/', './static/', processors=processors)
app.router.register_resource(resource)
```

此时：
- `/site/index.html` → 自动识别为 HTML 并返回
- `/site/api.py` → 使用 `PythonScriptProcessor` 执行 Python 脚本
- `/site/data.xlsx` → 使用 `XLSXDataSourceProcessor` 输出表格数据
- `/site/_dbrest/mydb/users` → 提供 users 表的 REST 接口

---

## 设计思想

| 特性 | 实现方式 |
|------|----------|
| **统一入口** | 所有请求都经过 `ProcessorResource` 分发 |
| **插件式处理器** | 通过配置绑定扩展名与处理器类 |
| **透明代理兼容** | 解析 X-Forwarded-* 头保证 URL 正确性 |
| **前后端融合** | 支持 `.py`, `.md`, `.ws` 等非传统静态资源 |
| **安全性** | 文件路径解码、上传隔离、目录禁止遍历 |

---

## 注意事项

1. **性能建议**
   - 生产环境中避免开启 `allowListFolder`
   - 静态资源建议由 Nginx 托管，本类主要用于开发或嵌入式场景

2. **安全警告**
   - `.py` 脚本处理器存在代码执行风险，请仅用于可信环境
   - 文件上传需配合权限校验（已通过 `userid` 传入 `FileStorage`）

3. **编码问题**
   - 所有文本文件推荐使用 UTF-8 编码
   - `i18nDICT()` 使用 `website.coding` 配置进行编码

4. **调试提示**
   - 可启用 `print_exc()` 查看异常堆栈
   - 使用 `info/debug/error` 输出日志辅助排查

---

## 总结

`ProcessorResource` 是一个高度可扩展的异步 Web 资源处理器，集成了：

✅ 静态文件服务  
✅ 动态脚本执行  
✅ 数据接口生成  
✅ 认证会话管理  
✅ 国际化支持  
✅ WebSocket 集成  

适用于快速搭建具有混合动静内容的企业级应用门户或低代码平台前端网关。

--- 

> 📝 文档版本：v1.0  
> 🔗 更新日期：2025年4月5日