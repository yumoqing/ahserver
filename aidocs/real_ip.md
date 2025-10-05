# `real_ip_middleware` 技术文档

## 概述

`real_ip_middleware` 是一个用于提取客户端真实 IP 地址的 Aiohttp 中间件工厂函数。在使用反向代理（如 Nginx、负载均衡器等）时，直接通过 `request.remote` 获取的可能是代理服务器的 IP，而非最终用户的实际 IP。该中间件通过检查特定的 HTTP 请求头字段，尝试还原客户端的真实 IP 地址，并将其挂载到 `request['client_ip']` 中供后续处理使用。

---

## 安装依赖

确保项目中已安装以下依赖：

```bash
pip install aiohttp aiohttp-middlewares
```

---

## 导入模块

```python
from appPublic.log import exception, debug, error
from aiohttp import web
from aiohttp_middlewares.annotations import DictStrStr, Handler, Middleware
```

> ⚠️ 注意：`appPublic.log` 为自定义日志模块，当前代码中未实际调用日志函数，但保留了导入。

---

## 函数定义

### `real_ip_middleware() -> Middleware`

返回一个 Aiohttp 兼容的中间件处理器，用于设置请求中的客户端真实 IP。

#### 返回值

- **类型**：`Middleware`
- **说明**：符合 Aiohttp 中间件协议的异步处理函数。

---

## 内部中间件逻辑

### `middleware(request: web.Request, handler: Handler) -> web.StreamResponse`

这是一个由 `@web.middleware` 装饰的异步中间件函数，负责处理每个进入的请求。

#### 参数

| 参数      | 类型           | 说明 |
|-----------|----------------|------|
| `request` | `web.Request`  | Aiohttp 请求对象 |
| `handler` | `Handler`      | 下一个处理请求的处理器（视图函数或其他中间件） |

#### 工作流程

1. **初始化客户端 IP**
   ```python
   request['client_ip'] = request.remote
   ```
   - 默认将 `request.remote`（即 TCP 连接对端 IP）作为客户端 IP。

2. **检查关键请求头**
   - 遍历请求头，查找以下任一字段：
     - `X-Forwarded-For`
     - `X-real-ip`
   - 这些头部通常由反向代理添加，包含原始客户端 IP。

3. **解析 IP 地址**
   - 若匹配到上述任一头字段：
     ```python
     v = v.split(',')[-1].strip()
     ```
     - 对多层代理情况，取逗号分隔列表中的最后一个非空 IP（最接近客户端的一跳）。
     - 去除首尾空白字符。
   - 将解析出的 IP 设置为 `request['client_ip']` 的值。
   - 找到后立即 `break`，不再检查其他头字段。

4. **继续处理链**
   ```python
   return await handler(request)
   ```
   - 调用下一个处理器，并返回响应。

---

## 使用方法

在 Aiohttp 应用中注册此中间件：

```python
app = web.Application(middlewares=[real_ip_middleware()])
```

之后在任意处理函数中可通过如下方式获取客户端真实 IP：

```python
async def my_handler(request):
    client_ip = request.get('client_ip', 'unknown')
    print(f"Client IP: {client_ip}")
    return web.json_response({"ip": client_ip})
```

---

## 示例场景

假设请求经过如下代理链：

```
Client (1.2.3.4) 
→ Nginx (adds X-Forwarded-For: "1.2.3.4, 5.6.7.8") 
→ Aiohttp Server
```

- `request.remote` 可能是 `5.6.7.8`（Nginx 出口 IP）
- 经过本中间件处理后：
  - `request['client_ip'] = "1.2.3.4"`

---

## 安全注意事项

- ✅ **推荐做法**：仅在受信任的代理环境下启用此中间件（例如内部网络或已验证代理头的网关）。
- ❌ **风险提示**：如果允许外部用户随意设置 `X-Forwarded-For` 或 `X-real-ip`，可能导致 IP 欺骗。
- 🔐 建议结合白名单机制，在可信代理节点才解析这些头字段。

---

## 扩展建议

可扩展支持更多标准头字段，例如：

- `CF-Connecting-IP` （Cloudflare）
- `True-Client-IP` （某些 CDN）
- `X-Original-Forwarded-For`

也可增加配置参数以灵活指定信任层级和头字段列表。

---

## 版本信息

- **语言**：Python 3.7+
- **框架**：Aiohttp >= 3.0
- **兼容性**：支持 `aiohttp-middlewares` 类型注解

---

## 许可证

请根据项目实际情况填写许可证信息（如 MIT、Apache 2.0 等）。