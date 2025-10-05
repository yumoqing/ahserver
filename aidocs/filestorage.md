# `fileUpload.py` 技术文档

> **文件上传与临时文件管理模块**

---

## 概述

`fileUpload.py` 是一个基于异步 I/O 的文件存储与上传处理模块，主要用于：

- 接收 Base64 编码的文件并保存为本地文件；
- 支持流式下载远程文件；
- 管理临时文件生命周期（自动清理过期文件）；
- 提供安全的文件路径映射与访问控制；
- 支持分片读取大文件以支持 HTTP 范围请求（Range Request），适用于视频/音频流媒体场景。

该模块广泛用于 Web 后端服务中处理用户上传、临时缓存和资源代理等场景。

---

## 依赖说明

### 第三方库
```python
import asyncio
import os
import time
import tempfile
import aiofiles
import json
import base64
```

### 自定义模块（来自 `appPublic` 包）
| 模块 | 功能 |
|------|------|
| `folderUtils._mkdir` | 递归创建目录 |
| `base64_to_file.base64_to_file`, `getFilenameFromBase64` | 将 Base64 字符串转为文件，并提取原始文件名 |
| `jsonConfig.getConfig` | 获取全局配置对象 |
| `Singleton.SingletonDecorator` | 单例装饰器 |
| `log.info`, `debug`, `warning`, `exception`, `critical` | 日志输出工具 |
| `streamhttpclient.StreamHttpClient` | 异步流式 HTTP 客户端 |

---

## 核心类与功能

---

### 1. `TmpFileRecord` 类：临时文件记录器（单例）

#### 说明
使用单例模式管理所有临时文件的创建时间，定期检查并删除超时文件。通过 JSON 文件持久化记录状态。

#### 装饰器
```python
@SingletonDecorator
class TmpFileRecord:
```
确保整个应用中仅存在一个实例。

#### 初始化参数
| 参数 | 默认值 | 说明 |
|------|--------|------|
| `timeout` | `3600` 秒（1小时） | 文件最大存活时间 |
| `time_period` | `10` 秒 | 清理任务执行周期 |

#### 属性
| 属性 | 类型 | 描述 |
|------|------|------|
| `filetime` | `dict[str, float]` | 文件路径 → 创建时间戳（`time.time()`） |
| `changed_flg` | `bool` | 是否有未保存的状态变更 |
| `filename` | `str` | 存储记录的 JSON 文件路径，格式：`{config.filesroot}/tmpfile_rec_{pid}.json` |
| `loop` | `asyncio.EventLoop` | 当前事件循环引用 |

#### 方法

##### `__init__(self, timeout=3600)`
初始化记录器，并在事件循环中调度加载与定时清理任务。

##### `savefilename(self)`
生成用于保存临时文件记录的 JSON 文件路径：
```python
root = config.filesroot or tempfile.gettempdir()
return f"{root}/tmpfile_rec_{os.getpid()}.json"
```

##### `newtmpfile(path: str)`
注册一个新的临时文件路径及其当前时间。
- 设置 `changed_flg = True` 触发后续持久化。

##### `async save()`
将内存中的 `filetime` 字典异步写入 JSON 文件。
- 若无更改则跳过。
- 使用 `aiofiles` 异步写入 UTF-8 编码内容。

##### `async load()`
从磁盘加载已有的文件记录。
- 若文件不存在则忽略。
- 加载后立即调用 `remove()` 执行一次清理。

##### `file_useful(self, fpath)`
标记某个文件仍在使用（即被访问），将其从待清理列表中移除。
- 使用 `try-except` 避免键不存在时报错。

##### `async remove()`
遍历所有记录的文件，删除超过 `timeout` 时间的文件。
- 调用 `rmfile(k)` 删除物理文件；
- 从 `filetime` 中删除条目；
- 异步保存更新后的记录；
- 自动递归调度下一次清理（每 `time_period` 秒执行一次）。

> ⚠️ 注意：此方法由 `loop.call_later()` 循环调用，构成后台守护任务。

##### `rmfile(name: str)`
根据配置根目录拼接完整路径后删除文件。
```python
os.remove(config.fileroot + name)
```
> ❗ 存在潜在错误：应为 `config.filesroot` 而非 `config.fileroot`（代码拼写错误）

---

### 2. `FileStorage` 类：文件存储管理器

提供统一接口进行文件的保存、读取、删除及路径转换。

#### 初始化
```python
def __init__(self):
    config = getConfig()
    self.root = os.path.abspath(config.filesroot or tempfile.gettempdir())
    self.tfr = TmpFileRecord()  # 共享单例
```

#### 属性
| 属性 | 类型 | 描述 |
|------|------|------|
| `root` | `str` | 文件系统根目录（绝对路径） |
| `tfr` | `TmpFileRecord` | 临时文件记录器单例 |

---

#### 核心方法

##### `realPath(path)`
将相对或绝对 Web 路径转换为安全的本地文件系统路径。
- 若路径以 `/` 开头，则去除；
- 使用 `os.path.join(self.root, ...)` 拼接；
- 返回规范化后的绝对路径。

> ✅ 安全性：防止路径穿越攻击（如 `../../etc/passwd`）

##### `webpath(path)`
将本地文件路径转换为 Web 可访问路径（相对于 `self.root`）。
- 成功时返回去根前缀的子路径；
- 失败时返回 `None`。

##### `_name2path(name, userid=None)`
根据文件名生成唯一且分布均匀的存储路径，避免单目录下文件过多。

###### 算法逻辑
1. 取当前微秒级时间戳：`int(time.time() * 1000000)`
2. 对四个质数 `[191, 193, 197, 97]` 取模，生成四级子目录；
3. 若指定 `userid`，则加入用户隔离路径 `/userid/...`
4. 最终结构示例：
   ```
   /filesroot/tmp/123/45/67/89/avatar.png
   ```

> ✅ 优点：高并发下分散 IO 压力；天然防重名。

##### `save_base64_file(b64str)`
将 Base64 编码字符串保存为文件。
- 自动提取文件名（`getFilenameFromBase64`）；
- 使用 `_name2path` 生成路径；
- 调用 `base64_to_file` 写入；
- 返回文件系统路径。

##### `remove(path)`
删除指定路径的文件。
- 支持带 `/` 前缀的路径；
- 捕获异常并记录日志；
- 实际路径为 `os.path.join(self.root, path.lstrip('/'))`

##### `async streaming_read(request, webpath, buf_size=8096)`
支持 HTTP Range 请求的大文件流式读取，适用于视频播放等场景。

###### 参数
| 参数 | 类型 | 说明 |
|------|------|------|
| `request` | `HTTPRequest` | 包含 headers 的请求对象 |
| `webpath` | `str` | Web 上下文路径（如 `/uploads/test.mp4`） |
| `buf_size` | `int` | 每次读取缓冲大小，默认 8KB |

###### 功能
- 解析 `Range: bytes=0-1023` 请求头；
- 计算起始和结束位置；
- 使用 `aiofiles.open(..., 'rb')` 异步打开文件；
- 支持 `seek()` 跳转；
- 分块 `yield` 数据，可用于 ASGI 响应体；

###### 日志输出
```python
debug(f'filesize={stats.st_size}, startpos=..., endpos=...')
```

##### `async save(name, read_data, userid=None)`
通用文件保存方法，支持多种输入类型。

###### 参数
| 参数 | 类型 | 说明 |
|------|------|------|
| `name` | `str` | 原始文件名 |
| `read_data` | `str`, `bytes`, 或 `callable async () -> bytes` | 数据源 |
| `userid` | `str` | 用户 ID（用于路径隔离） |

###### 行为
1. 生成唯一路径 `_name2path(...)`
2. 创建父目录（`_mkdir`）
3. 判断数据类型：
   - 若为 `str` 或 `bytes`：直接写入；
   - 否则视为异步生成器函数，循环读取直到返回空；
4. 保存成功后调用 `tfr.newtmpfile(fpath)` 注册为临时文件；
5. 返回 Web 路径（相对于 root）

> ✅ 支持同步数据和异步流两种模式。

---

## 工具函数

---

### `file_realpath(path)`
获取给定路径对应的实际文件系统路径。

```python
fs = FileStorage()
return fs.realPath(path)
```

> 主要用于外部调用快速解析路径。

---

### `async downloadfile(url, headers=None, params=None, data={})`
从指定 URL 异步下载文件并保存到本地。

#### 流程
1. 提取 URL 文件名；
2. 使用 `FileStorage._name2path(..., userid='tmp')` 生成临时路径；
3. 使用 `StreamHttpClient` 发起 GET 请求；
4. 流式接收 chunk 并写入文件；
5. 返回保存后的本地路径；
6. 出错时记录异常并重新抛出。

> ✅ 支持自定义 headers、query 参数、POST 数据。

---

### `async base642file(b64str)`
将 Base64 字符串解码并保存为二进制文件。

#### 特性
- 自动剥离 Data URL 头部（如 `data:image/png;base64,...`）；
- 使用 `base64.b64decode` 解码；
- 保存至 `userid='tmp'` 目录；
- 返回文件路径。

---

## 配置要求

需在全局配置中定义以下字段（通过 `getConfig()` 获取）：

| 配置项 | 类型 | 是否必需 | 说明 |
|--------|------|----------|------|
| `filesroot` | `str` | 否 | 文件存储根目录；若未设置则使用系统临时目录 |
| `fileroot` | `str` | 否（但注意 bug） | ❗ 在 `rmfile()` 中被误用，建议统一为 `filesroot` |

---

## 使用示例

### 示例 1：保存 Base64 图片
```python
b64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhE..."
fpath = await base642file(b64)
print(f"Saved to: {fpath}")
```

### 示例 2：流式下载远程文件
```python
url = "https://example.com/file.zip"
try:
    local_path = await downloadfile(url)
    print("Download complete:", local_path)
except Exception as e:
    print("Failed:", e)
```

### 示例 3：处理上传流（FastAPI 示例）
```python
@app.post("/upload")
async def upload_file(file: UploadFile):
    fs = FileStorage()
    def reader():
        return file.read(8192)
    web_path = await fs.save(file.filename, reader)
    return {"web_path": web_path}
```

### 示例 4：流式响应视频（Starlette/FastAPI）
```python
@app.get("/video/{path}")
async def stream_video(request, path: str):
    fs = FileStorage()
    return StreamingResponse(
        fs.streaming_read(request, f"/{path}"),
        media_type="video/mp4"
    )
```

---

## 注意事项与改进建议

### 🔴 已知问题
1. **变量名拼写错误**：
   ```python
   del self.tiletime[k]  # 应为 self.filetime
   ```
   ➤ 导致 KeyError，无法正确清理过期文件。

2. **属性名不一致**：
   ```python
   self.change_flg = True  # 正确
   self.changed_flg = False  # 初始化时使用了不同名称！
   ```
   ➤ 应统一为 `changed_flg`。

3. **`rmfile()` 中配置项错误**：
   ```python
   os.remove(config.fileroot + name)  # 应为 filesroot
   ```

4. **循环语法错误**：
   ```python
   for k,v in ft:  # ft 是 dict，不能直接迭代 tuple
   ```
   ➤ 应改为：`for k, v in ft.items():`

5. **`webpath()` 缺少返回值**：
   ```python
   if path.startswith(self.root):
       return path[len(self.root):]
   # else 缺失 return
   ```
   ➤ 应补上 `return None` 或默认路径。

---

### ✅ 改进建议
| 项目 | 建议 |
|------|------|
| 错误修复 | 修正上述拼写与逻辑错误 |
| 单元测试 | 添加对路径生成、清理机制、流读写的测试 |
| 配置校验 | 初始化时验证 `filesroot` 是否可写 |
| 更灵活的 TTL | 支持按文件类型设置不同过期时间 |
| 监控指标 | 增加文件数量、总大小、清理统计等 |

---

## 总结

`fileUpload.py` 是一个功能完整、设计合理的异步文件处理模块，具备以下优势：

✅ 异步高性能  
✅ 支持流式操作  
✅ 自动清理临时文件  
✅ 安全路径处理  
✅ 易于集成  

只要修复文中指出的几处关键 Bug，即可稳定运用于生产环境。

--- 

> 📝 文档版本：v1.0  
> 💬 维护者：开发者团队  
> 📅 更新日期：2025年4月5日