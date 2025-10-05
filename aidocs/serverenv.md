# Server Environment Management Module

本模块提供了一个用于管理服务器运行环境变量的工具，以及客户端类型识别功能。通过单例模式确保全局环境配置的一致性，并支持基于 HTTP 请求头的用户代理（User-Agent）解析来判断客户端设备类型。

---

## 模块依赖

```python
from appPublic.Singleton import SingletonDecorator
from appPublic.dictObject import DictObject
import re
```

- `SingletonDecorator`：来自 `appPublic` 包的单例装饰器，用于保证 `ServerEnv` 类在整个应用中只有一个实例。
- `DictObject`：字典式对象封装类，允许通过属性或键值方式访问数据。
- `re`：Python 正则表达式库，用于匹配 User-Agent 字符串。

---

## 核心类：`ServerEnv`

```python
@SingletonDecorator
class ServerEnv(DictObject):
    pass
```

### 功能说明

`ServerEnv` 是一个继承自 `DictObject` 的类，并使用 `@SingletonDecorator` 装饰为单例类。

- **继承特性**：
  - 继承 `DictObject` 后，该类具备类似字典的操作能力（如 `obj[key] = value`, `obj.get(key)` 等），同时也支持属性式访问（如 `obj.key`）。
- **单例模式**：
  - 使用 `@SingletonDecorator` 确保整个应用程序生命周期中仅存在一个 `ServerEnv` 实例，适合存储和共享全局配置或状态信息。

> ⚠️ 当前实现为空类（`pass`），但其行为完全由父类 `DictObject` 和单例机制驱动。

---

## 全局环境操作函数

### `get_serverenv(name)`

获取指定名称的服务器环境变量值。

#### 参数

| 参数名 | 类型   | 说明         |
|--------|--------|--------------|
| name   | str    | 环境变量名称 |

#### 返回值

- 返回对应键的值；若不存在，则返回 `None`。

#### 示例

```python
db_host = get_serverenv("database_host")
```

#### 实现逻辑

```python
def get_serverenv(name):
    g = ServerEnv()
    return g.get(name)
```

> 自动创建或获取唯一的 `ServerEnv` 实例，并调用其 `get()` 方法。

---

### `set_serverenv(name, value)`

设置服务器环境变量的值。

#### 参数

| 参数名 | 类型   | 说明             |
|--------|--------|------------------|
| name   | str    | 环境变量名称     |
| value  | any    | 要设置的任意值   |

#### 示例

```python
set_serverenv("debug_mode", True)
```

#### 实现逻辑

```python
def set_serverenv(name, value):
    g = ServerEnv()
    g[name] = value
```

> 将键值对存储在单例 `ServerEnv` 实例中，可供后续全局访问。

---

## 客户端类型识别功能

### `clientkeys`

预定义的用户代理关键字与客户端类型的映射表。

```python
clientkeys = {
    "iPhone": "iphone",
    "iPad": "ipad",
    "Android": "androidpad",
    "Windows Phone": "winphone",
    "Windows NT[.]*Win64; x64": "pc",
}
```

| User-Agent 关键词               | 映射类型     |
|-------------------------------|-------------|
| `iPhone`                      | `iphone`    |
| `iPad`                        | `ipad`      |
| `Android`                     | `androidpad`|
| `Windows Phone`               | `winphone`  |
| `Windows NT.*Win64; x64`      | `pc`        |

> 支持正则表达式匹配（例如最后一个条目），可用于更精确地识别桌面 Windows 浏览器。

---

### `getClientType(request)`

根据 HTTP 请求中的 `User-Agent` 头部判断客户端设备类型。

#### 参数

| 参数名   | 类型       | 说明                       |
|----------|------------|----------------------------|
| request  | object     | HTTP 请求对象，需含 headers 属性 |

#### 返回值

| 返回值       | 说明                     |
|-------------|--------------------------|
| `iphone`    | 来自 iPhone 设备         |
| `ipad`      | 来自 iPad 设备           |
| `androidpad`| 来自 Android 平板/手机   |
| `winphone`  | 来自 Windows Phone       |
| `pc`        | 桌面浏览器（默认 fallback）|

#### 实现逻辑

```python
def getClientType(request):
    agent = request.headers.get('user-agent', '')
    for k in clientkeys.keys():
        m = re.findall(k, agent)
        if len(m) > 0:
            return clientkeys[k]
    return 'pc'
```

#### 工作流程

1. 获取请求头中的 `User-Agent` 字符串。
2. 遍历 `clientkeys` 中的每个正则模式。
3. 使用 `re.findall()` 进行匹配，若成功则返回对应的客户端类型。
4. 若无任何匹配项，默认返回 `'pc'`。

#### 示例用法

```python
client_type = getClientType(request)
if client_type == 'iphone':
    # 返回移动端页面
    render_mobile_page()
```

---

## 使用场景建议

- **环境配置管理**：将数据库连接、调试开关、API 密钥等配置存入 `ServerEnv`，通过 `set_serverenv()` 初始化，在各模块中用 `get_serverenv()` 读取。
- **动态行为控制**：根据 `getClientType()` 返回结果调整响应内容格式（如适配移动/PC 页面）。
- **日志与监控**：记录不同客户端的行为差异，辅助分析用户分布。

---

## 注意事项

1. `clientkeys` 中的键是正则表达式，请确保语法正确，避免误匹配。
2. 当前 `getClientType()` 对于大多数现代浏览器未明确覆盖的情况统一归为 `'pc'`，可根据需要扩展规则。
3. `ServerEnv` 单例在进程内有效，分布式部署时需配合外部配置中心使用。

---

## 扩展建议

- 添加清除环境变量的方法（如 `clear_serverenv(name)`）。
- 增加更多设备识别规则（如 macOS Safari、微信内置浏览器等）。
- 提供 `ServerEnv` 初始化加载配置文件的功能。

--- 

✅ **总结**：本模块简洁高效地实现了服务端环境变量管理和基础客户端识别功能，适用于 Web 应用开发中的通用支撑层设计。