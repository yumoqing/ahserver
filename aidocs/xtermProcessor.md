# `XtermProcessor` 技术文档

## 概述

`XtermProcessor` 是一个基于 WebSocket 的终端处理器类，继承自 `PythonScriptProcessor`。它用于通过 Web 界面提供交互式 SSH 终端服务（类似 xterm.js 的后端支持），允许用户通过浏览器连接到远程服务器并执行命令。

该模块利用 `aiohttp` 提供异步 HTTP 和 WebSocket 通信能力，并结合 `appPublic.sshx.SSHServer` 实现与远程主机的 SSH 连接和终端会话管理。

---

## 模块依赖

```python
from traceback import format_exc
import asyncio
import aiohttp
import aiofiles
import json
import codecs
from aiohttp import web
import aiohttp_cors
from appPublic.sshx import SSHServer
from appPublic.dictObject import DictObject
from appPublic.log import info, debug, warning, error, exception, critical
from .baseProcessor import BaseProcessor, PythonScriptProcessor
```

### 外部依赖说明：

| 包/模块 | 用途 |
|--------|------|
| `aiohttp`, `web`, `aiohttp_cors` | 构建异步 Web 服务及处理 WebSocket 请求 |
| `asyncio` | 异步任务调度 |
| `aiofiles` | 异步文件操作（本代码中未直接使用） |
| `json`, `codecs` | 数据序列化与编码处理 |
| `appPublic.sshx.SSHServer` | 封装了 SSH 客户端功能，用于建立远程连接 |
| `appPublic.dictObject.DictObject` | 字典对象封装，支持属性访问 |
| `appPublic.log.*` | 日志输出接口 |

---

## 自定义异常：`ResizeException`

```python
class ResizeException(Exception):
    def __init__(self, rows, cols):
        self.rows = rows
        self.cols = cols
```

> ⚠️ **注意**：当前代码中定义了 `ResizeException` 类但并未实际抛出或捕获此异常。可能为预留扩展功能。

---

## 核心类：`XtermProcessor`

继承自 `PythonScriptProcessor`，实现了一个基于 WebSocket 的伪终端（PTY）代理，将前端输入转发至 SSH 子进程，并将输出回传给客户端。

### 类方法

#### `isMe(name) -> bool`

判断当前处理器是否匹配指定名称。

```python
@classmethod
def isMe(self, name):
    return name == 'xterm'
```

- **参数**：
  - `name` (str): 要检查的处理器名。
- **返回值**：
  - 若 `name == 'xterm'` 返回 `True`，否则 `False`。
- **用途**：
  - 在路由分发时用于选择合适的处理器。

---

## 实例方法

### `datahandle(request)`

HTTP 请求入口点，调用路径处理逻辑。

```python
async def datahandle(self, request):
    await self.path_call(request)
```

- **参数**：
  - `request`: `aiohttp.web.Request` 对象。
- **说明**：
  - 执行 `path_call()` 方法以启动流程。

---

### `path_call(request, params={})`

主处理入口，准备运行环境、获取登录信息并启动终端会话。

```python
async def path_call(self, request, params={}):
    await self.set_run_env(request, params=params)
    login_info = await super().path_call(request, params=params)
    if login_info is None:
        raise Exception('data error')

    ws = web.WebSocketResponse()
    await ws.prepare(request)
    await self.run_xterm(ws, login_info)
    self.retResponse = ws
    return ws
```

#### 流程说明：

1. 设置运行环境变量（如上下文、参数等）。
2. 调用父类 `PythonScriptProcessor.path_call()` 执行脚本逻辑，预期返回包含 SSH 登录信息的 `DictObject`。
3. 若 `login_info` 为空，则抛出异常。
4. 创建 WebSocket 响应对象并准备握手。
5. 启动 `run_xterm` 处理终端会话。
6. 保存响应对象并返回。

> ✅ **期望 `login_info` 结构示例**：
```python
{
    "host": "192.168.1.100",
    "port": 22,
    "username": "admin",
    "password": "secret",
    # 或 key_filename / pkey 等字段
}
```

---

### `run_xterm(ws, login_info)`

核心方法：建立 SSH 连接并启动双向数据流。

```python
async def run_xterm(self, ws, login_info):
    self.sshnode = SSHServer(login_info)
    async with self.sshnode.get_connector() as conn:
        self.running = True
        self.p_obj = await conn.create_process(term_type='xterm-256color', term_size=(80, 24))
        r1 = self.ws_2_process(ws)
        r2 = self.process_2_ws(ws)
        await asyncio.gather(r1, r2)
    debug(f'run_xterm() ended')
```

#### 功能详解：

- 使用 `SSHServer(login_info)` 初始化连接器。
- 获取连接上下文（`get_connector()`）进行资源管理。
- 创建带有彩色终端支持的进程（`create_process`），初始尺寸为 80x24。
- 并发运行两个协程：
  - `ws_2_process`: 接收客户端输入并发送到 SSH 子进程 stdin。
  - `process_2_ws`: 读取子进程 stdout 并推送到客户端。
- 使用 `asyncio.gather()` 并行等待两者结束。

---

### `ws_2_process(ws)`

处理来自 WebSocket 的消息，转发至 SSH 子进程。

```python
async def ws_2_process(self, ws):
    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            data = DictObject(**json.loads(msg.data))
            if data.type == 'close':
                debug('accept client close request, close the ws')
                self.running = False
                return
            if data.type == 'input':
                self.p_obj.stdin.write(data.data)
            elif data.type == 'heartbeat':
                await self.ws_send_heartbeat(ws)
            elif data.type == 'resize':
                try:
                    self.p_obj._chan.change_terminal_size(data.cols, data.rows)
                except Exception as e:
                    exception(f'{data=}, {e=}, {format_exc()}')
            elif msg.type == aiohttp.WSMsgType.ERROR:
                debug(f'ws connection closed with exception {ws.exception()}')
                return
        else:
            debug('recv from ws:{msg}+++++++++++')
        await asyncio.sleep(0)
```

#### 支持的消息类型：

| 类型 | 描述 |
|------|------|
| `input` | 将 `data.data` 写入子进程标准输入 |
| `resize` | 调整终端窗口大小为 `(cols, rows)` |
| `heartbeat` | 回复心跳包，保持连接活跃 |
| `close` | 关闭终端会话 |
| 其他文本消息 | 忽略并打印日志 |

> ❗ 注意：`change_terminal_size()` 可能引发异常，已捕获并记录堆栈。

---

### `process_2_ws(ws)`

从 SSH 子进程读取输出，推送至 WebSocket。

```python
async def process_2_ws(self, ws):
    try:
        while self.running:
            x = await self.p_obj.stdout.read(1024)
            await self.ws_send_data(ws, x)
            await asyncio.sleep(0)
    finally:
        self.p_obj.close()
```

- 循环读取最多 1024 字节的数据。
- 调用 `ws_send_data()` 发送数据帧。
- 即使连接断开也会确保 `p_obj.close()` 被调用。

---

### `ws_send_data(ws, d)`

发送数据内容到客户端。

```python
async def ws_send_data(self, ws, d):
    dic = {
        'type': 'data',
        'data': d
    }
    await self.ws_send(ws, dic)
```

---

### `ws_send_heartbeat(ws)`

发送心跳响应。

```python
async def ws_send_heartbeat(self, ws):
    dic = {
        'type': 'heartbeat'
    }
    await self.ws_send(ws, dic)
```

---

### `ws_send(ws: WebSocketResponse, s)`

通用 WebSocket 消息发送函数。

```python
async def ws_send(self, ws: web.WebSocketResponse, s):
    data = {
        "type": 1,
        "data": s
    }
    await ws.send_str(json.dumps(data, indent=4, ensure_ascii=False))
```

- **参数**：
  - `ws`: WebSocket 响应对象。
  - `s`: 要发送的数据（通常为 dict）。
- **格式化规则**：
  - JSON 序列化，保留中文字符（`ensure_ascii=False`），缩进便于调试。
- **结构**：
  ```json
  {
      "type": 1,
      "data": { ... }
  }
  ```

> 🔔 提示：前端需解析 `"type":1` 表示这是一个终端数据帧。

---

## 消息协议规范（WebSocket）

### 客户端 → 服务端

| 字段 | 类型 | 示例 | 说明 |
|------|------|-------|------|
| `type` | string | `"input"` | 消息类型 |
| `data` | string | `"ls -l\\n"` | 输入内容（仅 `input` 类型） |
| `rows`, `cols` | int | `24`, `80` | 窗口尺寸（`resize` 类型） |

示例：
```json
{
  "type": "input",
  "data": "echo hello\\n"
}
```

```json
{
  "type": "resize",
  "rows": 30,
  "cols": 120
}
```

---

### 服务端 → 客户端

统一包装格式：

```json
{
  "type": 1,
  "data": {
    "type": "data" | "heartbeat",
    "data": "output string..."
  }
}
```

| `data.type` | 含义 | 数据格式 |
|------------|------|---------|
| `data` | 终端输出 | 字符串（UTF-8 编码的命令行输出） |
| `heartbeat` | 心跳响应 | 空对象或仅含 type |

---

## 使用场景

适用于构建 Web 版终端应用（如运维平台、在线 IDE、云桌面等），典型架构如下：

```
[Browser] 
   ↓ (WebSocket)
[XtermProcessor]
   ↓ (SSH)
[Remote Server]
```

前端可配合 [xterm.js](https://xtermjs.org/) 使用，接收 `data` 类型消息写入终端，发送键盘输入作为 `input` 消息。

---

## 日志等级说明

| 函数 | 用途 |
|------|------|
| `debug()` | 调试信息（连接状态、消息流转） |
| `exception()` | 记录异常及完整堆栈 |
| `error()/critical()` | 严重错误（当前未显式调用） |

建议开启 DEBUG 日志以便排查问题。

---

## 注意事项与安全建议

1. **认证安全性**：
   - `login_info` 来源于脚本执行结果，必须严格校验来源，防止注入攻击。
   - 不应在 URL 或日志中暴露密码。

2. **资源清理**：
   - 已在 `finally` 块中关闭 `p_obj`，但仍需确保 `SSHServer` 正确释放连接。

3. **输入验证**：
   - `resize` 消息未做边界检查，建议添加行列范围限制（如 10~1000）。

4. **性能优化**：
   - `read(1024)` 可根据负载调整缓冲区大小。
   - `await asyncio.sleep(0)` 用于让出控制权，避免阻塞事件循环。

5. **CORS 配置**：
   - 需通过 `aiohttp_cors` 正确配置跨域策略，允许前端域名访问。

---

## 示例配置（aiohttp 路由集成）

```python
from aiohttp import web
import aiohttp_cors

app = web.Application()
# 添加 CORS 支持
cors = aiohttp_cors.setup(app)

# 注册处理器路由
app.router.add_route('GET', '/xterm/{nodeid}', xterm_processor_instance.datahandle)

# 启用 CORS
resource = cors.add(app.router['xterm'])
resource.add_route("*", xterm_processor_instance.datahandle, web.HTTPAllowedMethodsRule(("GET",)))
```

---

## 总结

`XtermProcessor` 是一个完整的异步 Web Terminal 后端实现，具备以下特点：

✅ 支持动态 SSH 登录配置  
✅ 双向实时通信（WebSocket ↔ SSH PTY）  
✅ 终端大小调整、心跳保活、优雅关闭  
✅ 易于集成至现有 Web 框架  

适合用于开发安全可控的远程终端访问系统。