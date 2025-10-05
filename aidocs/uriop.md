# `URIOp` 类技术文档

## 概述

`URIOp` 是一个用于处理 URI（统一资源标识符）与文件系统操作的 Python 类，主要用于在指定网站根目录范围内安全地进行文件和目录的读写、创建、重命名、删除等操作。该类通过配置文件获取网站根路径，并确保所有操作均限制在该目录范围内，防止越权访问。

此外，还定义了一个自定义异常 `URIopException`，用于统一抛出与 URI 操作相关的错误。

---

## 依赖模块

```python
import os
import codecs
from appPublic.jsonConfig import getConfig
from appPublic.folderUtils import folderInfo
```

- `os`: 提供操作系统接口，用于路径拼接、目录创建、文件重命名等。
- `codecs`: 以指定编码方式打开和读写文本文件。
- `appPublic.jsonConfig.getConfig`: 获取全局 JSON 配置对象。
- `appPublic.folderUtils.folderInfo`: 获取指定路径下的文件/目录列表信息。

---

## 自定义异常：`URIopException`

### 描述

表示 URI 操作过程中发生的错误，包含错误类型和详细消息。

### 构造函数

```python
def __init__(self, errtype, errmsg)
```

#### 参数：
- `errtype` (str): 错误类型标识，如 `'url scope error'`
- `errmsg` (str): 错误描述或触发错误的 URI

#### 示例：
```python
raise URIopException('url scope error', '/../malicious')
```

### 方法

| 方法 | 说明 |
|------|------|
| `__str__()` | 返回格式化字符串：`errtype=xxx,errmsg=xxx` |

---

## 核心类：`URIOp`

### 描述

封装了基于 URI 的安全文件系统操作，所有操作都会被限制在配置中定义的 `website.root` 目录下。

### 初始化方法

```python
def __init__(self)
```

#### 功能：
- 加载全局配置：`getConfig()`
- 设置 `realPath` 为网站根目录的绝对路径

#### 属性初始化：
- `self.conf`: 配置对象（通常来自 `jsonConfig`）
- `self.realPath`: 网站根目录的绝对路径（`os.path.abspath(conf.website.root)`）

> ⚠️ 要求配置中存在 `website.root` 和 `website.coding` 字段。

---

## 公共方法

---

### `abspath(uri=None)`

将相对 URI 转换为安全的绝对文件系统路径。

#### 参数：
- `uri` (str, 可选): 相对路径，例如 `"images/logo.png"` 或 `"/css/style.css"`

#### 返回值：
- (str) 对应的绝对路径字符串

#### 异常：
- 若路径超出允许范围（即不在 `realPath` 下），抛出 `URIopException('url scope error', uri)`

#### 实现逻辑：
1. 从 `conf.website.root` 开始构建基础路径
2. 如果 `uri` 不为空且以 `/` 开头，则去除开头斜杠
3. 使用 `os.path.join` 将 URI 分段拼接到根路径上
4. 调用 `os.path.abspath()` 规范化路径
5. 检查生成路径是否在 `realPath` 范围内（防止路径穿越攻击）

#### 示例：
```python
op = URIOp()
path = op.abspath("/uploads/file.txt")
# 结果类似：/var/www/uploads/file.txt（前提是根目录为 /var/www）
```

---

### `fileList(uri='')`

列出指定 URI 所指向目录中的所有文件和子目录。

#### 参数：
- `uri` (str): 要列出内容的目录 URI，默认为根目录

#### 返回值：
字典结构：
```python
{
    'total': int,        # 文件总数
    'rows': [            # 文件/目录列表
        {
            'id': str,       # 文件路径 ID（路径分隔符替换为 '_#_'）
            'text': str,     # 显示名称
            'type': 'dir'|'file',
            'mtime': float,  # 修改时间戳
            'size': int,     # 文件大小（目录为 0）
            'state': 'closed' if type=='dir' else None
        },
        ...
    ]
}
```

> 注：此方法依赖 `folderInfo(root_path, sub_uri)` 返回可迭代的文件信息。

#### 特殊处理：
- 所有目录项添加 `'state': 'closed'`
- `id` 中的 `/` 被替换为 `_#_`，便于前端解析使用

#### 示例：
```python
files = op.fileList("/docs")
print(files['total'])  # 输出文件数量
```

---

### `mkdir(at_uri, name)`

在指定 URI 对应的目录下创建新目录。

#### 参数：
- `at_uri` (str): 父目录的 URI，如 `/projects`
- `name` (str): 新目录名称，如 `'new_folder'`

#### 实现步骤：
1. 使用 `abspath(at_uri)` 获取父目录绝对路径
2. 使用 `os.path.join()` 拼接完整路径
3. 调用 `os.mkdir(p)` 创建目录

#### 示例：
```python
op.mkdir("/data", "backup")
# 在 data 目录下创建 backup 子目录
```

---

### `rename(uri, newname)`

重命名文件或目录。

#### 参数：
- `uri` (str): 原始文件/目录的 URI
- `newname` (str): 新的名字（仅名字，不含路径）

#### 注意事项：
- 不支持跨目录移动，只能改名
- 新名称不能包含路径分隔符

#### 实现步骤：
1. 获取原路径绝对地址
2. 获取其所在目录
3. 构造新路径：`os.path.join(dirname, newname)`
4. 调用 `os.rename(old_path, new_path)`

#### 示例：
```python
op.rename("/old_name.txt", "new_name.txt")
```

---

### `delete(uri)`

删除指定 URI 指向的文件。

#### 参数：
- `uri` (str): 要删除的文件 URI

#### 行为：
- 仅支持删除**文件**
- 不支持删除非空目录（若需删除目录，请先清空）

> 如需删除目录，建议扩展功能或使用其他工具。

#### 示例：
```python
op.delete("/temp/unwanted.log")
```

---

### `read(uri)`

读取指定 URI 指向的文本文件内容。

#### 参数：
- `uri` (str): 文件 URI

#### 返回值：
- (str) 文件内容字符串

#### 编码：
- 使用配置项 `conf.website.coding` 指定编码（如 `'utf-8'`）
- 使用 `codecs.open(..., 'r', encoding)` 安全读取

#### 示例：
```python
content = op.read("/config/settings.json")
```

---

### `save(uri, data)`

保存数据到指定 URI 的文件中（覆盖写入）。

#### 参数：
- `uri` (str): 目标文件 URI
- `data` (str): 要写入的字符串内容

#### 行为：
- 若文件已存在则覆盖
- 若路径不存在会引发 OSError（建议提前创建目录）

#### 编码：
- 使用 `conf.website.coding` 进行编码写入

#### 示例：
```python
op.save("/notes.txt", "Hello World!")
```

---

### `write(uri, data)`

功能与 `save(uri, data)` **完全相同**。

> 当前代码中 `write` 是 `save` 的重复实现，建议合并或保留其一以避免冗余。

#### 建议改进：
```python
def save(self, uri, data):
    return self.write(uri, data)

# 或反之
```

---

## 安全性说明

- 所有路径操作都经过 `abspath()` 的边界检查，防止路径穿越（如 `../../../etc/passwd`）
- 使用 `os.path.abspath` 和前缀比对双重验证路径合法性
- 不直接暴露底层文件系统路径给外部调用者

---

## 配置要求

`URIOp` 依赖以下配置项（由 `getConfig()` 提供）：

```json
{
  "website": {
    "root": "/path/to/your/site/root",
    "coding": "utf-8"
  }
}
```

- `root`: 网站资源根目录（推荐使用绝对路径）
- `coding`: 文件读写的默认字符编码

---

## 使用示例

```python
from your_module import URIOp

op = URIOp()

# 列出根目录文件
files = op.fileList("/")
print(files)

# 创建目录
op.mkdir("/", "new_folder")

# 写入文件
op.save("/new_folder/hello.txt", "Hi there!")

# 读取文件
text = op.read("/new_folder/hello.txt")
print(text)

# 重命名
op.rename("/new_folder/hello.txt", "greeting.txt")

# 删除文件
op.delete("/new_folder/greeting.txt")
```

---

## 已知限制与改进建议

| 问题 | 建议 |
|------|------|
| `write` 与 `save` 方法重复 | 合并为单一方法，或让其一作为别名 |
| 不支持递归删除目录 | 可增加 `rmdir(uri, recursive=False)` 方法 |
| `fileList` 返回结构固定，不易扩展 | 可增加参数控制返回字段或排序 |
| 异常缺少 traceback 支持 | 可继承更丰富的异常基类或记录日志 |

---

## 版权与许可

© 2025 Your Organization.  
本模块属于 `appPublic` 工具集的一部分，遵循项目整体开源协议（请参考 LICENSE 文件）。