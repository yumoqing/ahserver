# 文件服务模块技术文档

## 概述

本模块提供基于 `aiohttp` 的异步文件上传、下载与安全路径处理功能，支持通过加密路径访问存储文件，并集成 RC4 加密算法对文件路径进行编码/解码。主要用于实现安全的文件资源访问接口。

---

## 依赖说明

### 外部依赖
- `aiohttp`: 异步 Web 服务器框架
- `aiofiles`: 异步文件 I/O 操作
- `os`, `asyncio`: Python 标准库，用于系统交互和异步控制

### 内部依赖
- `appPublic.rc4.RC4`: RC4 流加密算法实现
- `appPublic.registerfunction.RegisterFunction`: 函数注册机制
- `appPublic.log.debug`: 调试日志输出
- `.filestorage.FileStorage`: 文件存储路径管理类

---

## 核心配置

```python
crypto_aim = 'God bless USA and others'
```

> **说明**：该字符串作为 RC4 加密的固定密钥（Key），用于路径的加解密。  
> ⚠️ 注意：硬编码密钥存在安全隐患，建议在生产环境中使用环境变量或配置中心管理。

---

## 工具函数

### `path_encode(path: str) -> str`
对输入路径进行 RC4 编码。

#### 参数
| 参数名 | 类型 | 说明 |
|-------|------|------|
| `path` | `str` | 原始文件路径 |

#### 返回值
- `str`: 经 RC4 加密后的 Base64 编码字符串（具体格式取决于 `RC4.encode` 实现）

#### 示例
```python
encoded = path_encode("/uploads/photo.jpg")
# 输出类似: "aGVsbG8gd29ybGQ="
```

---

### `path_decode(dpath: str) -> str`
对加密路径进行 RC4 解码。

#### 参数
| 参数名 | 类型 | 说明 |
|-------|------|------|
| `dpath` | `str` | 加密后的路径字符串 |

#### 返回值
- `str`: 解密后的真实文件路径

#### 示例
```python
decoded = path_decode("aGVsbG8gd29ybGQ=")
# 输出: "/uploads/photo.jpg"
```

> ✅ 提示：此函数应与 `path_encode` 配合使用，确保加解密一致性。

---

## 请求处理函数

### `file_upload(request: web.Request) -> None`
占位函数，预留文件上传逻辑。

> 🔜 当前为空实现（`pass`），需后续扩展支持 multipart 表单上传、权限校验、存储路径生成等功能。

---

### `file_handle(request: web.Request, filepath: str, download: bool = False) -> web.Response`
通用文件响应处理器，支持在线预览或强制下载。

#### 参数
| 参数名 | 类型 | 说明 |
|--------|------|------|
| `request` | `web.Request` | aiohttp 请求对象 |
| `filepath` | `str` | 系统真实文件路径 |
| `download` | `bool` | 是否以附件形式下载 |

#### 行为说明
- 若 `download=True`，设置响应头 `Content-Disposition: attachment; filename="xxx"`
- 使用 `web.FileResponse` 分块传输（chunk_size=8192字节）
- 自动启用 Gzip 压缩（`.enable_compression()`）

#### 返回值
- `web.FileResponse`: 包含文件流的 HTTP 响应对象

#### 日志输出
调试信息示例：
```
DEBUG: filepath='/data/file.txt', filename='file.txt', download=True
```

---

### `file_download(request: web.Request, filepath: str) -> web.Response`
快捷下载入口，调用 `file_handle` 并强制开启下载模式。

#### 参数
同 `file_handle`

#### 等价于
```python
await file_handle(request, filepath, download=True)
```

---

### `path_download(request: web.Request, params_kw: dict, *params, **kw) -> web.Response`
根据加密路径参数下载文件，是外部暴露的主要接口之一。

#### 参数
| 参数名 | 类型 | 说明 |
|--------|------|------|
| `request` | `web.Request` | 请求对象 |
| `params_kw` | `dict` | 路径参数字典，必须包含 `'path'` 字段 |
| `*params`, `**kw` | 可变参数 | 兼容性扩展参数 |

#### 流程
1. 从 `params_kw['path']` 获取加密路径
2. 判断是否需要下载（`params_kw.get('download')`）
3. 初始化 `FileStorage()` 获取实际文件路径
4. 调用 `file_handle` 返回响应

#### 示例请求数据
```python
params_kw = {
    'path': 'encrypted_path_string',
    'download': True
}
```

#### 日志输出
```log
DEBUG: path_download():download filename=/real/path/to/file.pdf
```

---

## 函数注册机制

使用 `RegisterFunction` 将处理函数绑定到命名路由：

```python
rf = RegisterFunction()
rf.register('idfile', path_download)
rf.register('download', path_download)
```

#### 注册映射表
| 名称 | 绑定函数 | 用途 |
|------|---------|------|
| `idfile` | `path_download` | 通过 ID 或加密路径访问文件 |
| `download` | `path_download` | 下载专用接口 |

> 💡 可结合路由中间件动态解析如 `/api/file/idfile/<encrypted_path>` 这类 URL。

---

## 安全性说明

- **路径隐藏**：通过 `path_encode/decode` 隐藏真实文件结构
- **加密强度**：RC4 已被视为弱加密算法，不推荐用于高敏感场景
- **建议改进**
  - 替换为 AES-GCM 或 ChaCha20-Poly1305
  - 添加时效性 Token 支持
  - 增加访问权限验证（如 JWT 鉴权）

---

## 使用示例（伪代码）

```python
# 生成加密链接
raw_path = "/uploads/report.docx"
encrypted = path_encode(raw_path)
url = f"/api/file/download/?path={encrypted}&download=1"

# 用户访问时自动解密并下载
# --> 调用 path_download → 解密 → 查找真实路径 → 发送文件
```

---

## 待完善事项（TODO）

| 功能 | 状态 | 说明 |
|------|------|------|
| 文件上传支持 | ❌ 未实现 | `file_upload` 函数体为空 |
| 错误处理 | ⚠️ 不足 | 缺少 `HTTPNotFound` 以外的异常捕获 |
| 权限控制 | ❌ 无 | 所有可解密路径均可访问 |
| 密钥管理 | ⚠️ 静态硬编码 | 存在泄露风险 |
| 单元测试 | ❓ 未知 | 未提供测试用例 |

---

## 总结

本模块实现了基于加密路径的安全文件访问机制，适用于需要隐藏真实文件路径的轻量级文件服务场景。具备良好的扩展性，但需加强安全性设计以适应生产环境需求。