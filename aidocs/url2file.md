# `Url2File` 与 `TmplUrl2File` 技术文档

> **模块功能概述**  
该模块提供了将 URL 映射到本地文件系统路径的工具类，主要用于 Web 服务或模板引擎中实现 URL 到文件路径的解析。支持虚拟路径映射、目录索引查找、路径继承（父级回退）以及相关资源定位等功能。

---

## 模块依赖

```python
import os
```

> 注意：`listFile()` 函数在代码中被调用但未定义，可能是外部导入函数，用于递归列出指定后缀的文件。

---

## 类一：`Url2File`

### 功能说明
将符合特定规则的 URL 转换为本地文件系统的绝对路径，并支持自动查找默认索引页、处理相对路径（如 `..` 和 `.`）、查询关联资源等。

### 构造函数：`__init__(path: str, prefix: str, indexes: list, inherit: bool = False)`

#### 参数说明

| 参数 | 类型 | 说明 |
|------|------|------|
| `path` | `str` | 根目录路径，URL 将映射到此路径下的子目录结构。 |
| `prefix` | `str` | URL 前缀，用于标识哪些 URL 应由该实例处理（目前仅存储，未直接使用）。 |
| `indexes` | `list[str]` | 索引文件名列表，例如 `['index.html', 'default.htm']`，当请求的是一个目录时，尝试返回这些文件之一。 |
| `inherit` | `bool` | 是否启用“继承模式”。若为 `True`，当当前路径无匹配文件时，会向上一级 URL 路径回溯查找。 |

#### 示例初始化

```python
u2f = Url2File("/var/www/html", "/static", ["index.html"], inherit=True)
```

---

### 方法列表

#### 1. `realurl(url: str) -> str`

**功能**：规范化 URL，去除 `.` 和 `..` 等逻辑路径片段。

**参数**
- `url` (`str`)：原始 URL 路径部分（不含协议）

**返回值**
- 规范化后的 URL 字符串

**算法说明**
- 分割 `/` 得到路径项
- 移除所有 `.` 项
- 遇到 `..` 时，与其前一项配对删除（模拟上级目录跳转）
- 最终重新拼接为标准路径

**示例**

```python
u2f.realurl("a/b/../c")  # → "a/c"
u2f.realurl("a/./b//c")  # → "a/b//c" （注意双斜杠不会被修复）
```

> ⚠️ 注意：本方法不处理重复斜杠，也不验证是否存在真实路径。

---

#### 2. `url2ospath(url: str) -> str`

**功能**：将完整 URL 转换为本地操作系统的绝对路径。

**参数**
- `url` (`str`)：输入的 URL（可带查询参数）

**返回值**
- 对应的本地文件系统绝对路径（尚未验证文件是否存在）

**处理流程**
1. 去除查询字符串（`?` 后内容）
2. 去除末尾 `/`
3. 若以 `http://`, `https://`, `ws://`, `wss://` 开头，则跳过协议头（前三段：协议 + 主机 + 端口/空）
4. 使用 `os.path.join(self.rootpath, *paths)` 构建路径
5. 返回 `abspath` 绝对路径

**示例**

```python
u2f = Url2File("/var/www", "/app", ["index.html"])
u2f.url2ospath("https://example.com/app/user/profile") 
# → /var/www/user/profile
```

---

#### 3. `url2file(url: str) -> str or None`

**功能**：根据 URL 查找对应的本地文件路径，是核心方法。

**参数**
- `url` (`str`)：请求的 URL

**返回值**
- 匹配的本地文件路径（`str`），否则返回 `None`

**查找逻辑**
1. 先去除查询参数
2. 转换为本地路径 `real_path`
3. 如果 `real_path` 是一个存在的目录：
   - 遍历 `self.indexes` 中的索引文件名
   - 检查 `<dir>/<index_file>` 是否存在文件，第一个存在的即返回
4. 如果 `real_path` 是一个存在的文件 → 直接返回
5. 如果父目录不存在 → 返回 `None`
6. 如果 `inherit=False` → 不允许继承，返回 `None`
7. 如果允许继承且路径层级 > 2：
   - 删除倒数第二级路径（向上回退一级）
   - 递归调用自身进行重试
8. 所有尝试失败 → 返回 `None`

**示例行为**

```python
# 假设目录结构：
# /www/root/
#   └── a/
#       └── b/
#           └── index.html

u2f = Url2File("/www/root", "/site", ["index.html"], inherit=True)
u2f.url2file("/site/a/b/")        # → /www/root/a/b/index.html
u2f.url2file("/site/a/b")         # → 同上（自动识别为目录）
u2f.url2file("/site/a/c")         # → 尝试 /www/root/a/c → 不存在 → 回退到 /site/c？不准确！

# 实际继承逻辑：删除倒数第二段 → /site/a/c → 删除 a → /site/c
# 即：/a/c 失败 → 尝试 /c
```

> 🔍 继承机制适用于某些扁平化模板 fallback 场景，但需谨慎设计路径结构避免误匹配。

---

#### 4. `relatedurl(url: str, name: str) -> str`

**功能**：获取与当前 URL 相关的另一个资源的逻辑 URL。

**参数**
- `url` (`str`)：当前上下文 URL
- `name` (`str`)：目标资源名称（文件或子路径）

**返回值**
- 新的逻辑 URL（规范化后）

**逻辑**
- 若原 URL 以 `/` 结尾，先去掉末尾 `/`
- 使用 `url2ospath` 获取对应路径并判断是否为文件
- 如果是文件，则将其所在目录作为基准路径（即去掉最后一段）
- 拼接新 `name` 成新路径
- 调用 `realurl()` 进行规范化

**用途举例**

```python
# 当前页面是 /user/profile，想引用同级的 avatar.png
relatedurl("/user/profile", "avatar.png")  # → /user/avatar.png
relatedurl("/user/", "style.css")          # → /user/style.css
```

---

#### 5. `relatedurl2file(url: str, name: str) -> str or None`

**功能**：结合 `relatedurl` 和 `url2file`，查找与某 URL 相关的文件。

**参数**
- `url` (`str`)：当前上下文 URL
- `name` (`str`)：目标文件名

**返回值**
- 目标文件的本地路径（`str`），否则 `None`

**内部流程**
1. 调用 `self.relatedurl(url, name)`
2. 再调用 `self.url2file(...)` 查询该路径对应的文件

**示例**

```python
u2f.relatedurl2file("/user/profile", "config.json")
# → 可能返回 /www/root/user/config.json
```

---

## 类二：`TmplUrl2File`

### 功能说明
管理多个 `Url2File` 实例，支持多路径搜索、模板文件扩展名过滤，常用于模板或静态资源加载器。

### 构造函数：`__init__(paths, indexes, subffixes=['.tmpl','.ui'], inherit=False)`

#### 参数说明

| 参数 | 类型 | 说明 |
|------|------|------|
| `paths` | `List[Tuple[str, str]]` | 元组列表，每个元素为 `(本地根路径, URL前缀)` |
| `indexes` | `list[str]` | 索引文件名列表（传递给每个 `Url2File`） |
| `subffixes` | `list[str]` | 模板文件的扩展名，默认为 `['.tmpl', '.ui']` |
| `inherit` | `bool` | 是否开启继承查找（统一传给所有 `Url2File`） |

> ❗ 注意：虽然 `prefix` 存储于 `Url2File` 中，但在当前实现中并未用于路由匹配，所有 `url2file` 请求都会遍历全部 `u2fs` 实例。

#### 示例初始化

```python
tmpl_u2f = TmplUrl2File(
    paths=[
        ("/opt/templates/custom", "/theme"),
        ("/opt/templates/default", "/")
    ],
    indexes=["index.tmpl"],
    subffixes=[".tmpl", ".html"],
    inherit=True
)
```

---

### 方法列表

#### 1. `url2file(url) -> str or None`

**功能**：依次尝试各个 `Url2File` 实例来查找文件。

**逻辑**
- 遍历 `self.u2fs`
- 调用每个实例的 `url2file(url)`
- 返回第一个成功结果
- 全部失败 → 返回 `None`

**用途**
- 实现“自定义模板覆盖默认模板”的优先级查找机制

---

#### 2. `relatedurl(url: str, name: str) -> str or None`

**功能**：查找第一个能生成有效相关 URL 的 `Url2File` 实例。

> ⚠️ 当前实现存在问题：即使某个 `relatedurl` 返回非空字符串，也可能不是合法路径或无法访问文件。

**建议改进**：应结合 `relatedurl2file` 思路，确保结果有意义。

---

#### 3. `list_tmpl() -> List[str]`

**功能**：列出所有配置路径下、符合指定后缀的模板文件（绝对路径）。

**返回值**
- 排序后的文件路径列表（`List[str]`）

**实现细节**
- 遍历 `self.paths` 中的每个根路径 `rp`
- 转为绝对路径
- 调用 `listFile(p, suffixs=self.subffixes, recursive=True)` 递归查找匹配文件
- 收集进 `ret` 列表
- 最终排序返回

> 📌 依赖外部函数 `listFile(dir, suffixs=[], recursive=False)`，其功能推测如下：
>
> ```python
> def listFile(directory, suffixs=None, recursive=False):
>     matches = []
>     for root, dirs, files in os.walk(directory):
>         for f in files:
>             if any(f.endswith(suf) for suf in suffixs):
>                 matches.append(os.path.join(root, f))
>         if not recursive:
>             break
>     return matches
> ```

**典型输出示例**

```python
[
  '/opt/templates/default/home.tmpl',
  '/opt/templates/default/layout.ui',
  '/opt/templates/custom/theme.dark.tmpl'
]
```

---

## 使用场景示例

### 场景 1：Web 模板引擎路径映射

```python
loader = TmplUrl2File(
    paths=[("/web/tmpl/custom", "/"), ("/web/tmpl/base", "/")],
    indexes=["page.tmpl"],
    subffixes=[".tmpl"],
    inherit=True
)

# 用户请求 /user/list
template_path = loader.url2file("/user/list")
# → 先查 custom/user/list → 存在则返回
# → 不存在则查 base/user/list → 或继续回退至 /list（如果 inherit=True）
```

### 场景 2：静态资源 fallback

```python
static = Url2File("/public", "/static", ["index.html"], inherit=True)
static.url2file("/static/js/app.js")       # → /public/js/app.js
static.url2file("/static/missing.jpg")     # → 查不到 → 回退到 /static → 仍失败 → None
```

---

## 注意事项与改进建议

| 问题 | 描述 | 建议 |
|------|------|------|
| `prefix` 未实际参与路由 | `Url2File.prefix` 仅保存未使用，可能导致误解 | 可增加前缀匹配逻辑，或移除该字段 |
| `realurl` 不处理重复斜杠 | `"a//b"` 不会被标准化为 `"a/b"` | 可添加正则替换 `re.sub(r'/+', '/', ...)` |
| `listFile` 未定义 | 导致模块不可独立运行 | 应补充定义或明确声明依赖 |
| `relatedurl` 返回可能无效 | 仅生成 URL 字符串，不保证路径存在 | 改为返回 `(url, filepath)` 或集成存在性检查 |
| 多路径查找顺序敏感 | `paths` 顺序决定优先级 | 文档中应强调顺序重要性 |

---

## 版权与许可

© 2025 项目作者。可用于内部系统或 Web 框架中的资源映射层。请确保遵守操作系统权限与安全规范。

--- 

✅ **推荐用途**：轻量级模板/静态文件路由映射、开发服务器路径解析、MVC 架构视图定位组件。