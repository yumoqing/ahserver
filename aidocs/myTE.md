# 模板引擎技术文档

## 概述

本模块实现了一个基于 Jinja2 的自定义模板引擎系统，支持通过 URL 映射到文件路径的方式加载模板，并集成了异步渲染功能。该系统适用于 Web 服务中动态页面的生成和管理。

主要特性包括：

- 自定义模板加载器（`TmplLoader`），支持多路径查找、继承机制与索引页自动识别。
- 支持配置化的编码格式读取模板文件。
- 异步渲染能力（`render_async`）。
- 与项目中的 `Url2File` 和 `ServerEnv` 组件无缝集成。

---

## 模块依赖

```python
import os
import codecs

from appPublic.Singleton import SingletonDecorator
from appPublic.jsonConfig import getConfig

from jinja2 import Template, Environment, BaseLoader

from .serverenv import ServerEnv
from .url2file import Url2File, TmplUrl2File
```

> **说明**：
> - `appPublic`: 项目公共库，提供单例模式和 JSON 配置读取功能。
> - `jinja2`: 核心模板引擎库。
> - `serverenv`: 服务器运行环境对象，用于全局共享资源。
> - `url2file`: 将 URL 路径转换为本地文件路径的工具类，`TmplUrl2File` 是其针对模板的扩展。

---

## 核心类定义

### `TmplLoader(BaseLoader, TmplUrl2File)`

自定义 Jinja2 模板加载器，结合了 `BaseLoader` 和 `TmplUrl2File` 的功能，支持从多个路径中按规则查找 `.tmpl` 类型的模板文件。

#### 构造函数

```python
def __init__(self, paths, indexes, subffixes=['.tmpl'], inherit=False)
```

| 参数 | 类型 | 描述 |
|------|------|------|
| `paths` | `list[str]` | 模板文件搜索路径列表，按顺序查找。 |
| `indexes` | `list[str]` | 索引页名称（如 `index.tmpl`, `default.tmpl`），用于目录访问时自动匹配默认页。 |
| `subffixes` | `list[str]` | 允许的模板文件后缀，默认为 `['.tmpl']`。可扩展支持其他后缀。 |
| `inherit` | `bool` | 是否启用路径继承机制（由 `TmplUrl2File` 实现）。 |

> ⚠️ 注意：需同时调用父类 `BaseLoader` 和 `TmplUrl2File` 的初始化方法。

#### 方法

##### `get_source(env: Environment, template: str) -> tuple[str, str, callable]`

获取指定模板的源码内容。

**返回值**（符合 Jinja2 加载器规范）：
- `source`: 模板文本内容（字符串）
- `filename`: 实际文件路径
- `uptodate`: 可调用对象，判断文件是否被修改（基于 mtime）

**流程说明**：
1. 读取全局配置中的网站编码（`config.website.coding`）。
2. 使用 `url2file()` 将模板名映射为实际文件路径。
3. 若文件不存在，抛出 `TemplateNotFound` 错误。
4. 以指定编码读取文件内容。
5. 返回 `(source, filepath, is_unchanged_lambda)`。

##### `join_path(name: str, parent: str) -> str`

实现模板中 `{% extends %}` 或 `{% include %}` 时相对路径的解析。

使用 `TmplUrl2File.relatedurl()` 计算相对于父模板的路径。

##### `list_templates() -> list`

当前未实现模板枚举功能，固定返回空列表。

> 后续可扩展为扫描所有路径下的模板并去重返回。

---

### `TemplateEngine(Environment)`

封装 Jinja2 `Environment` 的模板执行环境，提供更便捷的异步渲染接口。

#### 构造函数

```python
def __init__(self, loader=None)
```

| 参数 | 类型 | 描述 |
|------|------|------|
| `loader` | `TmplLoader` | 模板加载器实例，若不传则使用默认加载器。 |

**额外属性**：
- `urlpaths`: （预留字段）可用于缓存 URL 到模板的映射。
- `loader`: 保存引用以便内部调用。

#### 方法

##### `join_path(template: str, parent: str) -> str`

代理至 `self.loader.join_path()`，确保路径解析一致性。

##### `async render(___name: str, **globals) -> str`

异步渲染指定模板。

| 参数 | 类型 | 描述 |
|------|------|------|
| `___name` | `str` | 模板名称（URL 风格路径） |
| `**globals` | `dict` | 渲染上下文变量 |

**逻辑步骤**：
1. 调用 `get_template()` 获取模板对象。
2. 执行 `render_async()` 进行异步渲染。
3. 返回渲染后的 HTML 字符串。

> ✅ 支持异步过滤器、协程调用等高级特性。

---

## 初始化函数

### `setupTemplateEngine() -> None`

全局设置函数，用于初始化模板引擎并注入到服务器环境中。

#### 功能流程

1. 读取配置：`getConfig()` 获取全局配置对象。
2. 提取处理器配置中类型为 `'tmpl'` 的后缀列表：
   ```python
   subffixes = [i[0] for i in config.website.processors if i[1] == 'tmpl']
   ```
   示例：若配置为 `[('.html', 'tmpl'), ('.tmpl', 'tmpl')]`，则支持 `.html` 和 `.tmpl` 文件作为模板。
3. 创建 `TmplLoader` 实例，启用继承模式。
4. 初始化 `TemplateEngine` 并绑定加载器。
5. 将引擎挂载到单例 `ServerEnv()` 的 `tmpl_engine` 属性上，供全局使用。

#### 示例配置片段（JSON/YAML）

```json
{
  "website": {
    "coding": "utf-8",
    "paths": [
      "/var/www/templates",
      "/opt/app/default_tmpl"
    ],
    "indexes": ["index.tmpl", "default.tmpl"],
    "processors": [
      [".html", "tmpl"],
      [".tmpl", "tmpl"],
      [".js", "static"]
    ]
  }
}
```

---

## 使用示例

```python
# 初始化模板引擎（通常在应用启动时调用一次）
setupTemplateEngine()

# 获取引擎实例
g = ServerEnv()
engine = g.tmpl_engine

# 异步渲染模板
result = await engine.render('/user/profile.html', name='Alice', age=30)

print(result)  # 输出渲染后的 HTML 内容
```

在模板中也可以使用继承或包含：

```jinja2
{# base.tmpl #}
<html><body>{% block content %}{% endblock %}</body></html>
```

```jinja2
{# profile.tmpl #}
{% extends "base.tmpl" %}
{% block content %}
  <h1>Hello {{ name }}</h1>
{% endblock %}
```

---

## 注意事项

1. **编码问题**：确保 `config.website.coding` 设置正确（通常为 `"utf-8"`），避免中文乱码。
2. **文件权限**：模板所在目录需对运行进程可读。
3. **性能建议**：
   - 生产环境应开启 Jinja2 缓存机制（当前未配置）。
   - 可考虑实现 `list_templates()` 以支持热重载检测。
4. **异常处理**：
   - `TemplateNotFound`: 模板文件未找到。
   - `OSError`: 文件读取失败（权限、磁盘错误等）。

---

## 扩展建议

| 功能 | 建议 |
|------|------|
| 缓存支持 | 添加 `cache_size` 参数并启用 Jinja2 的模板缓存 |
| 自动重载 | 监听文件变化，在开发模式下自动刷新模板 |
| 安全沙箱 | 对不可信模板启用沙箱执行环境 |
| 多租户支持 | 按用户/站点隔离 `paths` 和 `loader` 实例 |

---

## 版权与维护

- **作者**：项目开发团队
- **所属模块**：`app.template_engine`
- **最后更新**：2025年4月5日

> 文档版本：v1.0  
> 适用于代码版本：见 Git 提交记录