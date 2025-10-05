以下是为提供的 `FunctionProcessor` 类编写的 **Markdown 格式技术文档**，适用于项目开发文档或 API 文档场景。

---

# `FunctionProcessor` 技术文档

## 概述

`FunctionProcessor` 是一个基于 `aiohttp` 的异步请求处理器类，继承自 `BaseProcessor`。它用于将 HTTP 请求动态映射到通过 `RegisterFunction` 注册的函数上，并支持路径参数解析和运行时环境注入。该处理器特别适用于实现基于注册函数的路由分发机制。

主要功能包括：
- 解析 URL 路径中的参数
- 调用已注册的同步或异步函数
- 支持运行时命名空间（`run_ns`）注入上下文变量
- 返回 `Response`、`FileResponse` 或普通内容数据

---

## 导入依赖

```python
import inspect
from appPublic.dictObject import DictObject
from appPublic.registerfunction import RegisterFunction
from appPublic.log import info, debug, warning, error, exception, critical
from aiohttp import web
from aiohttp.web_response import Response, StreamResponse
from .baseProcessor import BaseProcessor
```

### 依赖说明

| 模块 | 用途 |
|------|------|
| `inspect` | 判断目标函数是否为协程函数 |
| `DictObject` | 将字典转换为属性可访问的对象 |
| `RegisterFunction` | 获取全局注册的函数 |
| `appPublic.log` | 日志输出 |
| `aiohttp.web` | Web 服务核心组件 |
| `BaseProcessor` | 基础处理器基类 |

---

## 类定义

```python
class FunctionProcessor(BaseProcessor):
```

继承自 `BaseProcessor`，用于处理特定类型的 HTTP 请求并调用注册函数。

---

## 类方法

### `isMe(name)`

```python
@classmethod
def isMe(cls, name):
    return False
```

#### 说明

此方法用于判断当前处理器是否适用于给定名称的资源。在本实现中始终返回 `False`，表示此类不会自动匹配任何资源名 —— 其使用需显式配置。

> ⚠️ 注意：若需启用自动识别，请重写此方法以根据条件返回 `True`。

#### 参数

- `name` (`str`) - 资源名称

#### 返回值

- `bool`: 始终返回 `False`

---

## 实例方法

### `__init__(path, resource, opts)`

构造函数，初始化处理器实例。

```python
def __init__(self, path, resource, opts):
    self.config_opts = opts
    BaseProcessor.__init__(self, path, resource)
```

#### 参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `path` | `str` | 请求路径模板 |
| `resource` | `Any` | 关联资源对象（未具体使用） |
| `opts` | `dict` | 配置选项，必须包含以下键：<br>`leading`: 前缀路径，用于截断<br>`registerfunction`: 注册函数名 |

#### 属性设置

- `self.config_opts`: 存储传入的配置项
- 调用父类初始化逻辑

---

### `path_call(request, params={})`

执行注册函数的核心方法，负责解析路径、获取函数并调用。

```python
async def path_call(self, request, params={}):
```

#### 流程说明

1. 设置运行时环境（通过 `set_run_env`）
2. 提取 `params_kw` 和实际请求路径
3. 截去配置中指定的前缀（`leading`），拆分剩余路径作为位置参数
4. 从 `RegisterFunction` 中获取目标函数
5. 若函数未注册，记录错误日志并返回 `None`
6. 构造调用环境（排除敏感键）
7. 异步或同步调用函数并返回结果

#### 参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `request` | `aiohttp.web.Request` | 当前 HTTP 请求对象 |
| `params` | `dict` | 可选参数字典，可覆盖默认路径等信息 |

#### 返回值

- 函数调用结果（可以是 `Response`, `str`, `dict`, 或其他类型）
- 如果函数未注册，返回 `None`

#### 内部逻辑细节

##### 路径处理

```python
path1 = path[len(self.config_opts['leading']):]
if path1[0] == '/': path1 = path1[1:]
args = path1.split('/')
```

例如：  
若 `request.path = "/api/v1/user/123"`，且 `leading="/api/v1"`，则 `args = ['user', '123']`

##### 函数调用环境构建

```python
env = {k:v for k,v in self.run_ns.items() if k not in ['params_kw', 'request']}
```

过滤掉 `params_kw` 和 `request`，避免重复传参冲突。

##### 协程支持

```python
if inspect.iscoroutinefunction(f):
    return await f(request, params_kw, *args, **env)
return f(request, params_kw, *args, **env)
```

自动识别函数类型，确保正确调用同步或异步函数。

##### 错误处理

```python
if f is None:
    error(f'{rfname=} is not registered, {rf.registKW=}')
    return None
```

若函数未注册，输出调试信息并返回 `None`。

---

### `datahandle(request)`

处理请求并生成响应内容的方法。

```python
async def datahandle(self, request):
    x = await self.path_call(request)
    if isinstance(x, web.FileResponse):
        self.retResponse = x
    elif isinstance(x, Response):
        self.retResponse = x
    else:
        self.content = x
```

#### 功能

调用 `path_call` 执行业务逻辑，并根据返回值类型决定如何封装响应：

| 返回类型 | 处理方式 |
|---------|----------|
| `web.FileResponse` | 直接赋值给 `self.retResponse` |
| `Response`（含子类） | 赋值给 `self.retResponse` |
| 其他类型（如 `str`, `dict` 等） | 赋值给 `self.content`，由后续中间件或父类序列化 |

#### 参数

- `request`: `aiohttp.web.Request` 对象

#### 影响属性

- `self.retResponse`: 成功时保存响应对象
- `self.content`: 成功时保存原始内容数据

---

## 配置要求（`opts`）

`FunctionProcessor` 必须接收如下配置项：

| 键名 | 类型 | 说明 |
|------|------|------|
| `leading` | `str` | 需要从路径中去除的前缀，如 `/api/v1` |
| `registerfunction` | `str` | 在 `RegisterFunction` 中注册的函数名称 |

示例配置：

```python
opts = {
    "leading": "/api/v1",
    "registerfunction": "my_registered_handler"
}
```

---

## 使用示例

### 注册函数示例

```python
from appPublic.registerfunction import RegisterFunction

def my_handler(request, params, *args, **env):
    return web.json_response({"args": args, "env": env})

RegisterFunction().register("my_registered_handler", my_handler)
```

### 创建处理器并处理请求

```python
processor = FunctionProcessor("/api/v1/data/*", None, {
    "leading": "/api/v1/data",
    "registerfunction": "my_registered_handler"
})

# 在 aiohttp 路由中调用
async def handle_request(request):
    await processor.datahandle(request)
    if processor.retResponse:
        return processor.retResponse
    return web.json_response(processor.content)
```

---

## 注意事项与限制

1. **函数注册必需**：目标函数必须提前通过 `RegisterFunction().register(name, func)` 注册。
2. **函数签名要求**：被调用函数应接受 `(request, params_kw, *args, **kwargs)` 形式的参数。
3. **路径前缀必须匹配**：`leading` 必须准确匹配请求路径开头，否则可能导致参数解析异常。
4. **非标准返回值需手动处理**：若返回非 `Response` 类型，需确保上游能正确序列化 `self.content`。

---

## 日志输出

该类使用 `appPublic.log` 模块进行日志记录：

- `error`: 函数未注册时输出详细错误信息
- （其他日志级别暂未使用）

建议开启调试日志以便追踪调用过程。

---

## 总结

`FunctionProcessor` 提供了一种灵活的函数驱动式 Web 接口设计模式，适合微服务、插件化系统或需要动态绑定逻辑的场景。结合 `RegisterFunction` 机制，实现了低耦合、高扩展性的请求处理架构。

--- 

> ✅ 文档版本：1.0  
> 📅 最后更新：2025-04-05