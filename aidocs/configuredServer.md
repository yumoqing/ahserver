# AHApp 技术文档

## 概述

`AHApp` 是一个基于 `aiohttp.web.Application` 构建的异步 Web 应用框架，专为支持复杂业务逻辑、插件化架构和灵活配置而设计。它集成了数据库连接池、模板引擎、身份认证、文件存储、中间件处理等功能，并通过配置驱动的方式实现高度可定制性。

该应用主要用于构建高性能、模块化的 Python 异步后端服务，适用于企业级 Web 服务或 API 网关场景。

---

## 依赖库说明

### 标准库
| 模块 | 用途 |
|------|------|
| `os`, `sys` | 路径与系统环境操作 |
| `platform` | 判断操作系统平台（用于端口复用） |
| `time` | 时间相关功能（预留扩展） |
| `ssl` | SSL/TLS 支持，用于 HTTPS 服务器启动 |
| `socket` | 套接字基础支持（可能用于网络检测或底层通信） |

### 第三方库
| 模块 | 用途 |
|------|------|
| `aiohttp.web` | 异步 Web 框架核心，提供 HTTP 服务支持 |
| `appPublic.*` 系列模块 | 自定义公共工具组件（路径、日志、配置、字典对象等） |
| `sqlor.dbpools.DBPools` | 数据库连接池管理器，支持多数据源 |

### 本地模块（相对导入）
| 模块 | 用途 |
|------|------|
| `.processorResource.ProcessorResource` | 可编程资源处理器，支持自定义请求处理逻辑 |
| `.auth_api.AuthAPI` | 认证接口抽象类，支持 JWT/OAuth 等机制 |
| `.myTE.setupTemplateEngine` | 初始化模板引擎（如 Jinja2） |
| `.globalEnv.initEnv` | 初始化全局运行环境变量 |
| `.serverenv.ServerEnv` | 全局服务器运行上下文容器 |
| `.filestorage.TmpFileRecord` | 临时文件记录管理器 |
| `.loadplugins.load_plugins` | 插件加载系统，实现功能扩展 |
| `.real_ip.real_ip_middleware` | 中间件：提取真实客户端 IP（支持反向代理） |

---

## 核心类说明

### `AHApp(web.Application)`

继承自 `aiohttp.web.Application` 的增强型应用类，增加了用户数据存储和中间件预置功能。

#### 方法

##### `__init__(*args, **kw)`
初始化应用实例，设置最大请求体大小并插入真实 IP 中间件。

- **参数**：
  - `*args`, `**kw`: 传递给父类的参数
- **行为**：
  - 设置默认 `client_max_size = 1024000000` 字节（约 1GB）
  - 创建 `user_data: DictObject` 存储用户自定义数据
  - 在中间件链首部插入 `real_ip_middleware`

##### `set_data(k, v)`
将键值对存入内部 `user_data` 容器中。

- **参数**：
  - `k` (str): 键名
  - `v`: 任意类型值

##### `get_data(k)`
获取指定键对应的值。

- **参数**：
  - `k` (str): 键名
- **返回**：
  - 值或 `None`（若不存在）

---

### `ConfiguredServer`

主服务器配置类，负责加载配置、初始化组件、注册路由及启动服务。

#### 构造函数 `__init__(auth_klass=AuthAPI, workdir=None)`

- **参数**：
  - `auth_klass`: 认证类，需实现 `setupAuth(app)` 异步方法，默认使用 `AuthAPI`
  - `workdir`: 工作目录路径，用于加载配置文件；若未指定则使用默认查找策略

- **初始化流程**：
  1. 加载配置文件（通过 `getConfig()`）
     - 若提供了 `workdir`，则传入上下文 `{workdir, ProgramPath}`
  2. 若配置中包含 `databases`，初始化 `DBPools`
  3. 调用 `initEnv()` 和 `setupTemplateEngine()` 初始化全局环境与模板引擎
  4. 设置上传文件最大尺寸（默认 10MB，可由配置覆盖）
  5. 实例化 `AHApp` 并注入 `client_max_size`
  6. 加载插件（调用 `load_plugins(workdir)`）
  7. 初始化 `ServerEnv` 全局环境对象并设置工作目录

#### 方法

##### `async build_app()`
构建完整的 Web 应用实例。

- **流程**：
  1. 触发 `'ahapp_built'` 钩子事件（所有注册的协程函数执行）
  2. 实例化认证模块并调用其 `setupAuth(app)` 完成认证配置
  3. 返回最终的 `Application` 实例

> ⚠️ 注意：此方法返回的是 `awaitable`，必须在事件循环中调用。

##### `run(port=None)`
启动 HTTP/HTTPS 服务。

- **参数**：
  - `port`: 监听端口，优先级：传参 > 配置文件 > 默认 8080

- **功能细节**：
  - 读取配置中的主机地址（默认 `'0.0.0.0'`）
  - 若启用 SSL，则创建 `ssl_context` 并加载证书 (`crtfile`, `keyfile`)
  - 非 Windows 平台启用 `reuse_port=True` 提升性能（允许多进程绑定同一端口）
  - 调用 `web.run_app()` 启动服务

##### `configPath(config)`
根据配置动态注册带有处理器的资源路径。

- **参数**：
  - `config`: 配置对象，预期结构为 `config.website.paths` 是一个 `(path, prefix)` 元组列表

- **行为**：
  - 对每条路径创建 `ProcessorResource` 实例
    - 支持索引页显示（`show_index=True`）
    - 允许符号链接访问（`follow_symlinks=True`）
    - 支持自定义索引文件名列表（`indexes`）
    - 支持请求处理器链（`processors`）
  - 将资源注册到 `app.router`

---

## 配置结构示例（JSON/YAML）

```json
{
  "databases": {
    "default": {
      "driver": "postgresql",
      "host": "localhost",
      "port": 5432,
      "database": "mydb",
      "username": "user",
      "password": "pass"
    }
  },
  "website": {
    "host": "0.0.0.0",
    "port": 8080,
    "client_max_size": 10485760,
    "ssl": {
      "crtfile": "/path/to/cert.pem",
      "keyfile": "/path/to/key.pem"
    },
    "paths": [
      ["/static", "/public"],
      ["/uploads", "/files"]
    ],
    "indexes": ["index.html", "default.html"],
    "processors": {
      ".html": "template_processor",
      ".py": "script_processor"
    }
  }
}
```

> 注：实际配置格式取决于 `jsonConfig.getConfig` 的实现，通常支持 `.json`, `.yaml`, `.toml` 等。

---

## 插件机制

通过 `load_plugins(workdir)` 实现插件自动发现与加载。插件可通过 `RegisterCoroutine` 注册生命周期钩子，例如：

```python
from appPublic.registerfunction import RegisterCoroutine

def on_ahapp_built(app):
    app.router.add_get('/hello', lambda r: web.Response(text="Hello"))

RegisterCoroutine().register('ahapp_built', on_ahapp_built)
```

常见钩子事件包括：
- `ahapp_built`: 应用构建完成时触发
- `before_start`: 服务启动前
- `on_shutdown`: 关闭时清理资源

---

## 中间件

### `real_ip_middleware`

自动从请求头（如 `X-Forwarded-For`, `X-Real-IP`）提取真实客户端 IP 地址，防止因反向代理导致 IP 获取错误。

使用方式已在 `AHApp.__init__` 中自动注册。

---

## 使用示例

### 启动最简服务

```python
from your_module import ConfiguredServer

if __name__ == '__main__':
    server = ConfiguredServer(workdir='./config')
    server.run()  # 默认端口 8080
```

### 自定义认证类

```python
class MyAuth(AuthAPI):
    async def setupAuth(self, app):
        # 添加 JWT 中间件或其他认证逻辑
        pass

server = ConfiguredServer(auth_klass=MyAuth, workdir='./config')
server.run(port=9000)
```

---

## 运行环境要求

- Python >= 3.7
- 依赖包：
  ```txt
  aiohttp
  psycopg2-binary (PostgreSQL)
  oracledb / pymysql 等（根据数据库类型）
  pyyaml (可选，用于 YAML 配置)
  jinja2 (模板引擎)
  ```

---

## 安全建议

1. **生产环境务必启用 SSL**
   ```json
   "ssl": {
     "crtfile": "/etc/letsencrypt/live/domain.com/fullchain.pem",
     "keyfile": "/etc/letsencrypt/live/domain.com/privkey.pem"
   }
   ```
2. 设置合理的 `client_max_size` 防止 DoS 攻击
3. 不要暴露调试信息，关闭详细异常回显
4. 使用 WAF 或 Nginx 做前置防护

---

## 日志系统

使用 `appPublic.log` 提供的日志接口：

```python
info("Application started")
debug("Detailed debug info")
warning("Something may go wrong")
error("An error occurred")
critical("Critical failure")
exception("Exception with traceback")
```

日志输出位置由配置决定，通常写入文件或标准输出。

---

## 总结

`AHApp` 和 `ConfiguredServer` 构成了一个完整、可扩展的异步 Web 服务骨架，具备以下特点：

✅ 模块化设计  
✅ 插件热加载支持  
✅ 多数据库连接池  
✅ 安全认证集成  
✅ 反向代理兼容  
✅ HTTPS 支持  
✅ 高性能异步处理  

适合用于开发中大型 Python Web 后端项目。

--- 

> 📚 更多信息请参考配套模块文档：`appPublic`, `sqlor`, `processorResource` 等。