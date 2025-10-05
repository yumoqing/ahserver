# WebSocket 处理模块技术文档

```markdown
# WebSocket 处理模块技术文档

本模块提供基于 `aiohttp` 的异步 WebSocket 服务支持，用于构建实时通信的 Web 应用。通过 `WebsocketProcessor` 类实现 WebSocket 连接的管理、消息分发与脚本执行能力。

---

## 模块依赖

```python
import asyncio
import aiohttp
import aiofiles
import json
import codecs
from aiohttp import web
import aiohttp_cors
from traceback import print_exc

# 第三方/项目内部库
from appPublic.sshx import SSHNode
from appPublic.dictObject import DictObject
from appPublic.log import info, debug, warning, error, exception, critical
from .baseProcessor import BaseProcessor, PythonScriptProcessor
```

> **说明**：
- 使用 `aiohttp` 构建异步 HTTP/WebSocket 服务。
- `aiohttp_cors` 支持跨域请求（CORS）。
- `appPublic` 为项目公共工具包，包含日志、字典对象封装等工具。
- 继承自 `PythonScriptProcessor` 实现动态脚本执行。

---

## 核心函数

### `async def ws_send(ws: web.WebSocketResponse, data)`

向指定 WebSocket 客户端发送 JSON 格式数据。

#### 参数
| 参数 | 类型 | 说明 |
|------|------|------|
| `ws` | `web.WebSocketResponse` | WebSocket 响应对象 |
| `data` | `Any` | 要发送的数据内容（将被 JSON 序列化） |

#### 返回值
- 成功：返回 `await ws.send_str(d)` 的结果（通常为 `None`）
- 失败：捕获异常并记录错误，返回 `False`

#### 数据格式
发送的数据会被包装成如下结构：
```json
{
    "type": 1,
    "data": <原始数据>
}
```
使用 `ensure_ascii=False` 和缩进美化输出。

#### 示例
```python
await ws_send(ws, {"status": "connected", "user": "alice"})
```

---

## 核心类

### `class WsSession`

表示一个用户会话，可关联多个节点（连接实例）。

#### 方法
| 方法 | 描述 |
|------|------|
| `__init__(session)` | 初始化会话对象，传入 session 对象 |
| `join(node)` | 将节点加入当前会话（按 `node.id` 存储） |
| `leave(node)` | 从会话中移除指定节点 |

> ⚠️ 注意：`join` 和 `leave` 是实例方法但未使用 `self`，代码存在错误（缺少 `self` 参数），应修正为：
```python
def join(self, node):
    self.nodes[node.id] = node

def leave(self, node):
    self.nodes = {k:v for k,v in self.nodes.items() if k != node.id}
```

---

### `class WsData`

全局状态管理器，维护所有在线节点和会话。

#### 属性
| 属性 | 类型 | 说明 |
|------|------|------|
| `nodes` | `dict` | 存储所有活动节点 `{id: node}` |
| `sessions` | `dict` | 存储所有会话 `{sessionid: session}` |

#### 方法
| 方法 | 功能 |
|------|------|
| `add_node(node)` | 添加节点 |
| `del_node(node)` | 删除节点 |
| `get_nodes()` | 获取全部节点 |
| `get_node(id)` | 根据 ID 获取节点 |
| `add_session(session)` | 添加会话 |
| `del_session(session)` | 删除会话 |
| `get_session(id)` | 根据 ID 获取会话 |

> 所有操作均基于内存字典，非持久化。

---

### `class WsPool`

WebSocket 连接池管理类，封装单个客户端连接的行为与上下文。

#### 初始化参数
```python
def __init__(self, ws, ip, ws_path, app)
```
| 参数 | 类型 | 说明 |
|------|------|------|
| `ws` | `WebSocketResponse` | 当前连接对象 |
| `ip` | `str` | 客户端 IP 地址 |
| `ws_path` | `str` | WebSocket 请求路径（如 `/ws/chat`） |
| `app` | `Application` | aiohttp 应用实例，用于共享全局状态 |

#### 实例属性
| 属性 | 类型 | 说明 |
|------|------|------|
| `id` | `str` | 用户唯一标识（注册后赋值） |
| `ws`, `ip`, `ws_path`, `app` | - | 初始化传入 |

#### 核心方法

##### `get_data() → WsData`
获取或初始化当前路径下的共享数据对象（存储于 `app` 中）。若不存在则创建新的 `WsData` 并设置。

##### `set_data(data)`
将更新后的 `WsData` 写回应用上下文。

##### `is_online(userid) → bool`
检查某用户是否在线（即其节点是否存在）。

##### `register(id)`
注册用户 ID，创建 `DictObject` 并调用 `add_me()`。

##### `add_me(iddata)`
将当前连接绑定到用户 ID，并保存至 `WsData.nodes`。

##### `delete_id(id)`
从全局数据中删除指定用户节点。

##### `delete_me()`
删除当前连接对应的用户节点。

##### `add_session(session)` / `del_session(session)`
管理会话生命周期。

##### `get_session(sessionid)`
根据 ID 查询会话对象。

##### `async def sendto(data, id=None)`
发送消息：
- 若 `id` 为 `None`：发送给当前连接
- 否则：查找目标用户的 WebSocket 并发送
- 发送失败时自动调用 `delete_id(id)` 清理离线用户

---

### `class WebsocketProcessor(PythonScriptProcessor)`

继承自 `PythonScriptProcessor`，专用于处理 WebSocket 类型请求。

#### 类方法
##### `@classmethod isMe(name) → bool`
判断处理器是否匹配给定名称。
- 返回 `True` 当且仅当 `name == 'ws'`
- 用于路由匹配或插件识别

#### 实例方法
##### `async def path_call(self, request, params={})`

主入口方法，处理 WebSocket 升级请求并维持长连接。

###### 流程说明
1. **提取 Cookie 与用户信息**
   - 读取 `Sec-WebSocket-Protocol` 头部模拟 Cookies（逻辑可能需优化）
   - 获取当前用户 ID（通过 `get_user()` 或上下文）

2. **准备运行环境**
   - 设置请求上下文环境 `run_ns`
   - 合并参数 `params` 到本地命名空间 `lenv`
   - 提取 `userid`（优先从 `params_kw`，否则异步获取）

3. **加载脚本**
   - 异步读取脚本文件内容（路径由 `self.real_path` 指定）

4. **建立 WebSocket 连接**
   ```python
   ws = web.WebSocketResponse()
   await ws.prepare(request)
   ```
   - 准备失败时抛出异常并记录堆栈

5. **初始化连接池**
   ```python
   ws_pool = WsPool(ws, client_ip, path, app)
   ```

6. **消息循环监听**
   ```python
   async for msg in ws:
   ```
   - **TEXT 消息**：
     - 心跳检测：收到 `_#_heartbeat_#_` 回复相同字符串
     - 其他消息：注入 `ws_data` 和 `ws_pool` 至脚本环境，执行脚本中的 `myfunc`
   - **ERROR 消息**：
     - 记录异常并中断循环
   - **其他类型**：
     - 输出调试信息

7. **连接关闭清理**
   - 调用 `ws_pool.delete_me()` 注销当前用户
   - 设置响应对象并关闭连接
   - 返回 `ws` 对象

###### 参数
| 参数 | 类型 | 说明 |
|------|------|------|
| `request` | `Request` | aiohttp 请求对象 |
| `params` | `dict` | 额外传入参数（可选） |

###### 返回值
- `web.WebSocketResponse`：已关闭的 WebSocket 对象

###### 环境变量注入
在执行脚本时，以下变量被注入局部命名空间：
- `ws_data`: 接收到的消息文本
- `ws_pool`: 当前连接池实例，可用于发送消息或查询状态
- `request`, `params_kw`, `get_user` 等来自上下文

> ✅ 脚本要求：必须定义名为 `myfunc(request, **kwargs)` 的异步函数。

---

## 使用示例

假设有一个脚本 `/scripts/ws/hello.py`：
```python
async def myfunc(request, ws_data, ws_pool, **kw):
    data = json.loads(ws_data)
    reply = {
        "echo": data,
        "time": time.time()
    }
    await ws_pool.sendto(reply)
```

配置路由指向该处理器并命名为 `'ws'`，当访问对应路径时即可启用 WebSocket 服务。

---

## 日志等级说明

| 等级 | 用途 |
|------|------|
| `info` | 正常流程、连接建立/断开 |
| `debug` | 调试信息、中间状态打印 |
| `warning` | 可容忍异常 |
| `error` | 错误事件 |
| `exception` | 异常捕获（带堆栈） |
| `critical` | 严重故障 |

---

## 注意事项

1. **安全性**
   - 脚本动态执行存在安全风险，请确保脚本来源可信。
   - 建议对 `exec()` 加沙箱限制。

2. **并发控制**
   - 所有操作均为协程安全，但共享状态无锁保护，避免多任务同时修改。

3. **资源清理**
   - 必须保证 `delete_me()` 在连接关闭时调用，防止内存泄漏。

4. **心跳机制**
   - 客户端需定期发送 `_#_heartbeat_#_` 维持连接。

5. **IP 获取**
   - `request['client_ip']` 需要在中间件中预先设置，原生 `aiohttp` 不直接提供。

---

## 待修复问题

| 问题 | 描述 | 建议 |
|------|------|------|
| `WsSession.join/leave` 缺少 `self` | 方法定义语法错误 | 补全 `self` 参数 |
| `cookie` 处理逻辑可疑 | 将 `Sec-WebSocket-Protocol` 当作 Cookies 不合理 | 应使用正确方式解析认证信息 |
| `get_user()` 未导入 | 函数未在代码中定义或导入 | 需确认其来源并显式引入 |

---

## 版本信息

- Python: >=3.7
- aiohttp: >=3.8
- aiohttp-cors: >=0.7
- appPublic: 自定义工具库（需项目内可用）

---
> 文档生成时间：{{ 自动生成时间 }}  
> 维护者：开发者团队  
```