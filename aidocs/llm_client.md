# `StreamLlmProxy` 与 LLM 代理类技术文档

本项目提供了一套用于代理调用大语言模型（LLM）API 的异步 Python 类，支持流式和同步请求，并具备参数转换、身份认证、响应处理等功能。该模块适用于构建灵活的 LLM 网关服务。

---

## 模块依赖

```python
import re
import base64
import json
from traceback import format_exc
from aiohttp import web
from appPublic.dictObject import DictObject
from appPublic.log import debug, info, exception, error
from appPublic.httpclient import HttpClient, RESPONSE_TEXT, RESPONSE_JSON, RESPONSE_BIN, RESPONSE_FILE, RESPONSE_STREAM
from appPublic.registerfunction import RegisterFunction
from appPublic.argsConvert import ArgsConvert
```

> **说明**：  
> - 使用 `aiohttp` 实现异步 Web 响应流。
> - `DictObject` 提供字典属性访问语法（如 `obj.key`）。
> - `HttpClient` 是封装的异步 HTTP 客户端。
> - `ArgsConvert` 支持模板字符串替换（类似 `${var}`）。
> - 日志使用 `appPublic.log` 统一输出。

---

## 工具函数

### `encode_imagefile(fn)`

将本地图片文件编码为 Base64 字符串，常用于向 LLM API 发送图像输入。

#### 参数：
- `fn` (str): 图像文件路径。

#### 返回值：
- (str): Base64 编码后的 UTF-8 字符串。

#### 示例：
```python
img_b64 = encode_imagefile("example.jpg")
```

---

## 核心类：`StreamLlmProxy`

一个通用的 LLM 接口代理类，支持流式响应处理。

### 初始化：`__init__(self, processor, desc)`

#### 参数：
- `processor`: 包含运行环境上下文的对象（需有 `run_ns` 属性）。
- `desc` (dict-like): 描述目标 LLM API 的配置对象，必须包含 `.name` 字段。

#### 属性初始化：
| 属性 | 类型 | 说明 |
|------|------|------|
| `name` | str | API 名称 |
| `processor` | object | 上下文处理器 |
| `auth_api` | dict/None | 认证接口定义 |
| `desc` | object | 原始描述对象 |
| `api_name` | str | 同 `name` |
| `data` | DictObject | 存储用户级临时数据（如 token） |
| `ac` | ArgsConvert | 模板参数解析器 |

> ⚠️ 断言 `desc.name` 必须存在。

---

### 方法列表

#### `line_chunk_match(l)`
对流式返回的每一行进行正则匹配提取有效 JSON 内容。

##### 参数：
- `l` (str): 输入文本行。

##### 返回值：
- 匹配到的组或原字符串。

##### 配置来源：
通过 `self.api.chunk_match` 正则表达式控制，例如：
```json
"chunk_match": "data: (.*)"
```

---

#### `write_chunk(ll)`
将单条消息写入 HTTP 流响应体中，支持过滤与字段映射。

##### 参数：
- `ll` (str): 待处理的消息字符串。

##### 功能流程：
1. 跳过 `[DONE]` 标记；
2. 使用 `line_chunk_match` 提取内容；
3. 解析为 `DictObject`；
4. 根据 `api.resp` 映射输出字段；
5. 可选地根据 `chunk_filter` 条件清空某字段；
6. 序列化为 JSON 并写入流。

##### 异常处理：
捕获所有异常并记录堆栈日志。

---

#### `stream_handle(chunk)`
处理来自 `HttpClient` 的原始字节流，按换行分割并逐行调用 `write_chunk`。

##### 参数：
- `chunk` (bytes): 原始响应片段。

##### 特性：
- 自动拼接跨块不完整行（使用 `self.remain_str` 缓存尾部未完成部分）。

---

#### `get_apikey(apiname)`
从运行环境中获取当前用户的 API Key。

##### 参数：
- `apiname` (str): 目标 API 名称。

##### 行为：
调用 `processor.run_ns.get_llm_user_apikey(apiname, user)` 获取密钥。

> 若函数未注册，则抛出异常。

---

#### `get_apidata(parts, params={})`
根据配置动态生成请求参数（headers/data/params），支持模板变量替换与自定义转换器。

##### 参数：
- `parts`: 参数定义列表，每项结构如下：
  ```python
  {
    "name": "field_name",
    "value": "template string with ${user}",
    "convertor": "optional_function_name"
  }
  ```
- `params`: 外部传入参数，优先级高于 `self.data`。

##### 返回值：
- (dict): 构造好的参数字典。

##### 转换机制：
- 使用 `ArgsConvert('${', '}')` 替换 `${key}` 模板；
- 若指定了 `convertor`，通过 `RegisterFunction().exe()` 执行转换逻辑。

---

#### `do_auth(request)`
执行前置认证流程（如获取 access_token），通常用于需要 OAuth 或 JWT 的场景。

##### 流程：
1. 检查是否已认证（避免重复请求）；
2. 调用 `get_apikey()` 获取基础凭证；
3. 构造认证请求（URL、method、headers、data）；
4. 发起请求并解析响应；
5. 将关键字段保存至 `self.data`；
6. 设置 `authed=True` 并持久化存储。

##### 数据持久化：
通过 `set_data(key, value)` 存储于应用全局状态。

---

#### `data_key(apiname)`
生成基于用户的身份数据键名。

##### 规则：
```
{apiname}_a_{username}
```
若用户为空，默认为 `'anonymous'`。

---

#### `set_data(apiname, data)` / `get_data(apiname)`
封装了应用级别的数据读写操作，基于 `aiohttp.web.Application` 的共享状态。

> 利用 `request.app` 实现跨请求的数据缓存（如 access_token 缓存）。

---

#### `__call__(request, params)`
主入口方法，处理客户端请求并转发至后端 LLM 接口。

##### 参数：
- `request`: aiohttp 请求对象；
- `params`: 用户请求参数（DictObject）；

##### 关键行为：
- 支持流式 (`stream=True`) 和非流模式；
- 准备 `StreamResponse`；
- 解析 URL、method、headers、data、params；
- 使用 `HttpClient` 发起异步请求；
- 注册 `stream_func=self.stream_handle` 处理流数据；
- 最终返回 `web.StreamResponse` 对象。

##### 日志调试：
打印完整的请求信息（URL、参数等）便于排查问题。

---

#### `datalize(dic, data={})`
模板变量填充工具函数。

##### 参数：
- `dic`: 包含 `${...}` 模板的字典或字符串；
- `data`: 补充变量源。

##### 优先级：
`data` > `self.data`

##### 返回值：
替换后的结果。

---

## 派生类

### `SyncLlmProxy(StreamLlmProxy)`

同步版本代理，直接返回完整 JSON 响应。

#### 差异点：
- 不使用流式响应；
- `response_type=RESPONSE_JSON`；
- 返回普通字典而非 `StreamResponse`；
- 结果通过 `convert_resp(resp)` 进行字段映射。

#### `convert_resp(resp)`
将原始响应按 `api.resp` 配置投影成标准格式。

##### 示例配置：
```json
"resp": [
  {"name": "content", "value": "choices.0.message.content"},
  {"name": "finish_reason", "value": "choices.0.finish_reason"}
]
```

---

### `AsyncLlmProxy(StreamLlmProxy)`

异步但非流式代理，等待完整响应后再返回。

#### 特性：
- 仍准备 `StreamResponse`；
- 实际以 `RESPONSE_JSON` 获取完整数据；
- 再次尝试写入残留字符串（`remain_str`）；
- 返回 `StreamResponse`（可能无实际流内容）；

> ❗ 注意：此设计可能存在语义歧义，建议明确区分“异步获取”与“流式传输”。

---

## 配置结构示例（JSON Schema）

```json
{
  "name": "openai_gpt4",
  "auth": {
    "url": "https://api.openai.com/v1/token",
    "method": "POST",
    "headers": [
      {"name": "Authorization", "value": "Bearer ${api_key}"}
    ],
    "data": {},
    "set_data": [
      {"name": "access_token", "field": "token"}
    ]
  },
  "chat": {
    "url": "https://api.openai.com/v1/chat/completions",
    "method": "POST",
    "need_auth": true,
    "headers": [
      {"name": "Authorization", "value": "Bearer ${access_token}"},
      {"name": "Content-Type", "value": "application/json"}
    ],
    "data": [
      {"name": "model", "value": "${model}"},
      {"name": "messages", "value": "${messages}"},
      {"name": "stream", "value": "${stream}"}
    ],
    "resp": [
      {"name": "text", "value": "choices.0.delta.content"},
      {"name": "done", "value": "choices.0.finish_reason"}
    ],
    "chunk_match": "data: (.*)",
    "chunk_filter": {
      "name": "choices.0.delta.role",
      "value": "system",
      "op": "!=",
      "field": "text"
    }
  }
}
```

---

## 使用场景

| 场景 | 推荐类 |
|------|--------|
| 实时聊天界面（SSE） | `StreamLlmProxy` |
| 获取完整回复（CLI 工具） | `SyncLlmProxy` |
| 异步任务调度 | `AsyncLlmProxy` |

---

## 日志级别说明

| 级别 | 用途 |
|------|------|
| `debug()` | 请求详情、内部变量 |
| `info()` | 正常流程提示 |
| `exception()` | 异常 + 堆栈 |
| `error()` | 严重错误 |

---

## 注意事项

1. **安全性**：敏感信息（如 API Key）应在 `get_llm_user_apikey` 中安全获取，不应硬编码。
2. **性能**：`stream_handle` 中避免阻塞操作，确保高吞吐。
3. **兼容性**：不同 LLM 提供商的流格式差异较大，需正确设置 `chunk_match`。
4. **缓存策略**：`set_data/get_data` 基于内存，重启丢失，可扩展至 Redis。

---

## 总结

该组件实现了高度可配置化的 LLM API 代理层，支持：

✅ 多种调用模式（流式/同步）  
✅ 动态参数注入（模板引擎）  
✅ 自定义响应映射  
✅ 认证流程自动化  
✅ 插件式转换函数  

适合集成进企业级 AI 网关系统，作为统一接入点。