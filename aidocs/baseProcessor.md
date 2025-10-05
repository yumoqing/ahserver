# 技术文档：处理器框架（Processor Framework）

本文档描述了一个基于 `aiohttp` 的异步 Web 处理器系统，支持多种资源类型（如模板、脚本、Markdown 等）的动态处理。该系统通过继承和多态机制实现不同类型的处理器，并结合运行时环境注入与缓存策略提升性能。

---

## 📦 模块概览

```python
import os
import re
import json
import codecs
import aiofiles
from aiohttp.web_request import Request
from aiohttp.web_response import Response, StreamResponse

from appPublic.jsonConfig import getConfig
from appPublic.dictObject import DictObject
from appPublic.folderUtils import listFile
from appPublic.argsConvert import ArgsConvert
from appPublic.log import info, debug, warning, error, critical, exception

from .utils import unicode_escape
from .serverenv import ServerEnv
from .filetest import current_fileno
```

### 依赖说明

| 包/模块 | 用途 |
|--------|------|
| `aiohttp` | 提供异步请求/响应对象 |
| `appPublic.*` | 自定义公共库：配置读取、字典封装、日志等 |
| `aiofiles` | 异步文件操作 |
| `json`, `re` | 数据序列化与正则替换 |

---

## 🔁 核心组件

### 1. `ObjectCache` 类

用于缓存已加载的对象，避免重复解析或编译开销。

#### 方法

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `__init__()` | - | `ObjectCache` 实例 | 初始化空缓存字典 |
| `store(path, obj)` | `path: str`, `obj: Any` | `None` | 将对象按路径存储，记录其最后修改时间（mtime） |
| `get(path)` | `path: str` | `Any or None` | 若文件未被修改则返回缓存对象，否则返回 `None` |

> ⚠️ 缓存失效判断依据：`os.path.getmtime(path) > cached_mtime`

#### 示例用法

```python
cache = ObjectCache()
cache.store('/path/to/file.py', compiled_code)
obj = cache.get('/path/to/file.py')  # 如果文件未变，返回缓存对象
```

---

### 2. `BaseProcessor` 基类

所有处理器的基类，提供通用处理流程和响应构造能力。

#### 属性

| 属性 | 类型 | 初始值 | 说明 |
|------|------|-------|------|
| `path` | `str` | 构造传入 | 请求对应的虚拟路径 |
| `resource` | `Resource` 对象 | 构造传入 | 资源管理器实例 |
| `retResponse` | `Response or None` | `None` | 可直接返回的自定义响应对象 |
| `headers` | `dict` | 默认头信息 | 响应头字段集合 |
| `content` | `str / dict / bytes / ...` | `''` | 处理后的输出内容 |
| `env_set` | `bool` | `False` | 是否已设置运行环境 |
| `real_path` | `str` | 动态设置 | 映射到本地文件系统的实际路径 |

#### 静态方法

##### `isMe(name: str) -> bool`
- **用途**：判断当前处理器是否匹配给定名称。
- **默认实现**：仅当 `name == 'base'` 时返回 `True`
- 子类需重写此方法以支持识别。

#### 异步方法

##### `be_call(request: Request, params: dict = {}) -> Response`
调用入口，最终返回 HTTP 响应。

```python
return await self.path_call(request, params)
```

##### `set_run_env(request: Request, params: dict = {}) -> None`
初始化运行命名空间（`run_ns`），注入上下文变量。

###### 注入变量包括：
| 变量名 | 来源 | 说明 |
|--------|------|------|
| `request` | 参数 | 当前请求对象 |
| `app` | `request.app` | 应用实例 |
| `params_kw` | 合并参数 | 来自 URL 参数和外部传参 |
| `ref_real_path` | 映射结果 | 文件系统真实路径 |
| `processor` | `self` | 当前处理器引用 |
| 其他全局环境 | `ServerEnv().to_dict()` 和 `resource.y_env` | 服务端环境配置 |

> ✅ 支持 `request2ns()` 扩展函数将请求参数转换为命名空间。

##### `execute(request: Request) -> str`
执行主逻辑链：

```python
await self.set_run_env()
await self.datahandle()  # 子类实现具体处理
return self.content
```

##### `handle(request: Request) -> Response`
生成最终 HTTP 响应对象，自动处理不同类型的内容输出。

###### 内容类型自动检测与转换：
| 输入类型 | 输出行为 |
|---------|----------|
| `Response` / `StreamResponse` | 直接返回 |
| `dict`, `list`, `tuple`, `DictObject` | JSON 序列化，设置 `Content-Type: application/json` |
| `bytes` | 设置二进制响应体 |
| 字符串且合法 JSON | 视为 JSON 输出 |
| 其他字符串 | 普通文本响应 |

> ✅ 自动添加 CORS 相关头部（暴露 Set-Cookie）

##### `datahandle(request: Request)`
**抽象方法**，子类必须实现具体的业务逻辑。

默认实现打印错误日志并清空内容。

##### `setheaders()`
可选覆写方法，用于在响应前设置额外头部（如 Content-Length）。目前留空。

---

## 🧩 处理器子类

### 1. `TemplateProcessor(BaseProcessor)`

用于渲染 `.tmpl` 模板文件。

#### 特性
- 使用 `tmpl_engine` 渲染模板
- 支持扩展名决定内容类型（`.tmpl.css`, `.tmpl.js`）

#### 关键方法

##### `isMe(name)`  
返回 `True` 当 `name == 'tmpl'`

##### `path_call(request, params)`  
使用模板引擎渲染指定路径模板。

```python
te = self.run_ns['tmpl_engine']
return await te.render(path, **ns)
```

##### `datahandle(request)`  
调用 `path_call` 获取模板渲染结果。

##### `setheaders()`  
根据文件后缀设置正确的 MIME 类型：
- `.tmpl.css` → `text/css`
- `.tmpl.js` → `application/javascript`
- 其他 → `text/html`

---

### 2. `BricksAppProcessor(TemplateProcessor)`

包装应用级模板，嵌入主布局框架。

#### 特性
- 继承模板功能
- 将原始模板内容插入到 `bricksapp.tmpl` 主容器中

#### `datahandle(request)`
1. 先调用父类渲染原始模板 → `txt`
2. 加载 `/bricks/bricksapp.tmpl` 作为外壳
3. 使用 `ArgsConvert("${", "}$")` 替换 `${appdic}` 占位符为 `txt`

```python
ac = ArgsConvert("${", "}$")
self.content = ac.convert(template_wrapper, {'appdic': txt})
```

#### `isMe(name)`
返回 `True` 当 `name == 'app'`

---

### 3. `BricksUIProcessor(TemplateProcessor)`

条件性包裹页面 UI 结构（header + content + footer）

#### 行为逻辑
检查参数 `_webbricks_`：
- 若不存在或等于 `0` → 不包装，直接保留原内容
- 否则 → 包装 header 和 footer 模板

#### `datahandle(request)`
```python
if should_wrap:
    header = await resource.path_call(... '/header.tmpl')
    footer = await resource.path_call(... '/footer.tmpl')
    self.content = f"{header}{original}{footer}"
```

#### `isMe(name)`
返回 `True` 当 `name == 'bui'`

---

### 4. `PythonScriptProcessor(BaseProcessor)`

执行 Python 异步脚本（`.dspy` 文件）

#### 特性
- 将 `.dspy` 文件内容包装成 `async def myfunc(request, **ns): ...`
- 在安全命名空间内 `exec()` 执行
- 调用并返回结果

#### 关键方法

##### `loadScript(path)`  
异步读取脚本内容，每行前加缩进 `\t`，拼接为函数体字符串。

> 💡 注意：`\r\n` 被统一处理为 `\n`

##### `path_call(request, params)`  
1. 准备运行环境 `lenv`（移除 `request` 防止污染）
2. 加载并编译脚本代码
3. `exec()` 注入命名空间
4. 调用 `myfunc(request, **lenv)` 并返回结果

##### `datahandle(request)`  
调用 `path_call` 获取脚本执行结果并赋值给 `content`

##### `isMe(name)`
返回 `True` 当 `name == 'dspy'`

---

### 5. `MarkdownProcessor(BaseProcessor)`

渲染 Markdown 文件，并自动重写链接为完整 URL。

#### 特性
- 支持内联 `[text](url)` 链接自动补全域名
- 使用 `resource.entireUrl()` 解析相对路径

#### 方法

##### `datahandle(request)`
异步读取 `.md` 文件内容，调用 `urlreplace()` 处理链接。

##### `urlreplace(mdtxt, request)`  
使用正则替换所有 Markdown 链接：

```regex
\[(.*)\]\((.*)\)
```

替换为：

```text
[显示文本](完整URL)
```

示例：
```md
[首页](/home) → [首页](https://example.com/home)
```

##### `isMe(name)`
返回 `True` 当 `name == 'md'`

---

## 🔄 工厂函数：处理器查找

### `getProcessor(name: str) -> Type[BaseProcessor] or None`

根据名称递归查找匹配的处理器类。

#### 实现逻辑

```python
def getProcessor(name):
    return _getProcessor(BaseProcessor, name)

def _getProcessor(kclass, name):
    for subclass in kclass.__subclasses__():
        if hasattr(subclass, 'isMe') and subclass.isMe(name):
            return subclass
        # 递归搜索子类
        found = _getProcessor(subclass, name)
        if found:
            return found
    return None
```

#### 示例

```python
cls = getProcessor('tmpl')     # → TemplateProcessor
cls = getProcessor('dspy')     # → PythonScriptProcessor
cls = getProcessor('unknown')  # → None
```

> ✅ 支持深度继承结构下的处理器发现

---

## 🛠️ 设计亮点

| 特性 | 描述 |
|------|------|
| **插件式架构** | 通过 `isMe()` + 继承实现处理器注册与发现 |
| **运行环境隔离** | 每个请求独立 `run_ns`，防止状态污染 |
| **异步友好** | 全面使用 `async/await`，适配 `aiohttp` 生态 |
| **内容类型智能推导** | 自动判断输出类型并设置正确 `Content-Type` |
| **CORS 支持** | 默认暴露 `Set-Cookie` 头部 |
| **模板嵌套机制** | 支持布局包装（BricksApp/UI） |
| **动态脚本执行** | 安全沙箱模式执行用户脚本（谨慎使用） |

---

## ⚠️ 安全建议

1. **慎用 `PythonScriptProcessor`**
   - `exec()` 存在严重安全风险
   - 建议限制 `.dspy` 文件访问权限或禁用生产环境使用

2. **输入验证**
   - 所有来自客户端的参数应进行严格校验
   - 防止路径遍历攻击（如 `../../etc/passwd`）

3. **CORS 策略**
   - 当前只暴露 `Set-Cookie`，但未启用 `Allow-Credentials` 和 `Allow-Origin`
   - 如需跨域，请在 `set_response_headers` 中补充策略

---

## 📎 总结

本模块构建了一个灵活、可扩展的异步 Web 资源处理框架，适用于：

- 模板渲染服务
- 动态 Markdown 页面
- 内嵌脚本执行（开发调试场景）
- 布局嵌套系统（Bricks 架构）

通过简单的继承与注册机制，开发者可以轻松扩展新的处理器类型，满足多样化的前端集成需求。

---

> 📁 **建议目录结构参考**

```
/templates/
  home.tmpl
  bricks/
    bricksapp.tmpl
    header.tmpl
    footer.tmpl
/scripts/
  api.dspy
/pages/
  about.md
/static/
  ...
```

> 📄 **路由映射示意**

| URL Path | Processor | Name Hint |
|---------|-----------|----------|
| `/app/home` | BricksAppProcessor | `app` |
| `/bui/dashboard` | BricksUIProcessor | `bui` |
| `/api/data.dspy` | PythonScriptProcessor | `dspy` |
| `/doc/intro.md` | MarkdownProcessor | `md` |
| `/view/page.tmpl` | TemplateProcessor | `tmpl` |

--- 

📝 *文档版本：v1.0*  
📅 *最后更新：2025-04-05*