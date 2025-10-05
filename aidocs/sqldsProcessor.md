# SQL 数据源处理器技术文档

## 概述

`SQLDataSourceProcessor` 是一个基于 `DataSourceProcessor` 的子类，用于处理以 `.sqlds` 格式定义的 SQL 数据源。它允许通过配置文件描述 SQL 查询、参数和数据库连接，并动态执行查询获取数据。

该模块主要用于从数据库中提取结构化数据，支持普通查询、分页查询以及自动推导返回字段结构（`datadesc`），并能将推导结果持久化回源文件。

---

## 依赖模块

```python
import codecs
from .dsProcessor import DataSourceProcessor
from appPublic.jsonConfig import getConfig
from sqlor.dbpools import DBPools
import json
```

- `codecs`: 用于安全地读写带编码的文件（如 UTF-8）。
- `DataSourceProcessor`: 抽象基类，定义了数据源处理器的标准接口。
- `getConfig` (from `appPublic.jsonConfig`): 获取全局配置对象。
- `DBPools` (from `sqlor.dbpools`): 提供异步数据库连接池及 SQL 执行装饰器。
- `json`: 用于序列化/反序列化 JSON 数据。

---

## 配置文件格式（`.sqlds`）

`.sqlds` 文件是标准的 JSON 格式，描述了一个 SQL 查询的数据源信息：

```json
{
    "sqldesc": {
        "sql_string": "select * from dbo.stock_daily_hist where stock_num=${stock_num}$ order by trade_date desc",
        "db": "mydb",
        "sortfield": "trade_date"
    },
    "arguments": [
        {
            "name": "stock_num",
            "type": "str",
            "iotype": "text",
            "default": "600804"
        }
    ],
    "datadesc": []
}
```

### 字段说明

| 字段 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `sqldesc.sql_string` | string | 是 | 实际执行的 SQL 查询语句，支持 `${param}$` 形式的参数占位符。 |
| `sqldesc.db` | string | 是 | 数据库连接名称（在 DBPools 中注册过的别名）。 |
| `sqldesc.sortfield` | string | 否 | 排序字段，可用于前端排序或分页逻辑参考。 |
| `arguments` | array | 否 | 定义传入 SQL 的参数列表，每个参数包含：`name`, `type`, `iotype`, `default`。 |
| `datadesc` | array | 否 | 描述查询结果字段结构的数组。若为空，则首次访问时自动推导并写回文件。 |

> ⚠️ 注意：`${param}$` 是模板语法，运行时会被 `ns` 上下文中的对应值替换。

---

## 类定义

```python
class SQLDataSourceProcessor(DataSourceProcessor):
```

继承自 `DataSourceProcessor`，实现针对 `.sqlds` 类型数据源的具体行为。

---

## 方法说明

### `isMe(name) -> bool`

判断当前处理器是否适用于指定类型的数据源。

#### 参数
- `name` (`str`)：数据源类型名。

#### 返回值
- `True` 当且仅当 `name == 'sqlds'`。

#### 示例
```python
if SQLDataSourceProcessor.isMe('sqlds'):
    processor = SQLDataSourceProcessor(...)
```

---

### `getArgumentsDesc(dict_data, ns, request) -> list or None`

获取数据源所需的输入参数描述。

#### 参数
- `dict_data` (`dict`)：解析后的 `.sqlds` 文件内容。
- `ns` (`dict`)：命名空间（通常为请求参数）。
- `request` (`Request`)：HTTP 请求对象（可选用途扩展）。

#### 返回值
- `list`：参数描述数组（来自 `arguments` 字段）。
- `None`：若未定义 `arguments`。

#### 示例返回
```python
[
    {
        "name": "stock_num",
        "type": "str",
        "iotype": "text",
        "default": "600804"
    }
]
```

---

### `async getDataDesc(dict_data, ns, request) -> list`

异步获取查询结果的字段元信息（即 `datadesc`）。如果尚未生成，则自动从数据库中推导并保存到原文件。

#### 参数
- `dict_data` (`dict`)：原始数据源配置。
- `ns` (`dict`)：参数上下文，用于填充 SQL 占位符。
- `request` (`Request`)：请求对象。

#### 行为流程
1. 若 `datadesc` 已存在且非空，直接返回。
2. 否则：
   - 调用 `runSQLResultFields` 获取 SQL 查询的实际返回字段（不含 `_row_id`）。
   - 将推导出的字段结构写入 `dict_data['datadesc']`。
   - 序列化整个 `dict_data` 回源文件（路径为 `self.src_file`），保持缩进与中文不转义。

#### 使用的装饰器
- `@pool.runSQLResultFields`：执行 SQL 并返回字段元信息（列名、类型等）。

#### 返回值
- `list`：字段描述列表，每项为字段元数据字典（如 `{ "name": "trade_date", "type": "datetime" }`）。

#### 示例输出
```python
[
    {"name": "stock_num", "type": "string"},
    {"name": "trade_date", "type": "date"},
    {"name": "close_price", "type": "float"}
]
```

> ✅ 自动持久化：一旦推导完成，会更新 `.sqlds` 文件以避免重复分析。

---

### `async getData(dict_data, ns, request) -> list`

执行完整 SQL 查询并返回所有结果记录。

#### 参数
- `dict_data` (`dict`)：数据源定义。
- `ns` (`dict`)：参数上下文。
- `request` (`Request`)：请求对象。

#### 行为
- 使用 `@pool.runSQL` 执行 `sqldesc.sql_string`。
- 替换 `${}` 中的参数。
- 返回所有行组成的列表。

#### 使用的装饰器
- `@pool.runSQL`：执行查询并返回异步迭代器，转换为列表。

#### 返回值
- `list[dict]`：每条记录为一个字典。

#### 示例返回
```python
[
    {"stock_num": "600804", "trade_date": "2023-09-01", "close_price": 12.5},
    {"stock_num": "600804", "trade_date": "2023-08-31", "close_price": 12.3}
]
```

---

### `async getPagingData(dict_data, ns, request) -> dict`

执行分页查询，返回带分页信息的结果集。

#### 参数
- `dict_data` (`dict`)
- `ns` (`dict`)：必须包含分页参数，如 `page`, `pageSize` 或等效字段。
- `request` (`Request`)

#### 行为
- 使用 `@pool.runSQLPaging` 执行分页 SQL。
- 自动处理偏移量和限制数量。
- 返回结构化分页响应。

#### 使用的装饰器
- `@pool.runSQLPaging`：支持分页的 SQL 执行器，返回包含 `data`, `total`, `page`, `pageSize` 的对象。

#### 返回值（示例）
```json
{
    "data": [...],
    "total": 100,
    "page": 1,
    "pageSize": 10
}
```

---

## 内部机制说明

### SQL 模板替换

使用 `${param}$` 语法进行变量注入，例如：

```sql
select * from table where id = ${user_id}$
```

运行时由 `DBPools` 的装饰器根据 `ns` 字典替换为实际值。

### 自动字段推导与缓存

首次访问 `getDataDesc` 时，若 `datadesc` 为空，系统将：
1. 执行 SQL 获取字段结构；
2. 过滤掉内部字段 `_row_id`；
3. 写入本地 `.sqlds` 文件以供后续使用。

这提高了性能并减少了对数据库元数据的频繁访问。

### 编码与文件写入

使用 `codecs.open(..., encoding=config.website.coding)` 确保文件按项目设定编码保存（通常是 UTF-8），并通过 `ensure_ascii=False` 保留中文字符。

---

## 使用场景

适合以下情况：
- 需要灵活配置 SQL 查询作为 API 输出。
- 前端需要知道返回字段结构（用于表格渲染）。
- 支持参数化查询和分页。
- 开发阶段快速原型设计，无需编写后端代码。

---

## 示例 `.sqlds` 文件应用

假设文件名为 `stock_history.sqlds`，配置如下：

```json
{
    "sqldesc": {
        "sql_string": "SELECT stock_num, trade_date, open, high, low, close FROM stock_daily WHERE stock_num = ${code}$ ORDER BY trade_date DESC",
        "db": "financial_db",
        "sortfield": "trade_date"
    },
    "arguments": [
        {
            "name": "code",
            "type": "str",
            "iotype": "text",
            "default": "600804"
        }
    ],
    "datadesc": []
}
```

调用 `getDataDesc()` 后，`datadesc` 将被自动填充为：

```json
[
    {"name": "stock_num", "type": "string"},
    {"name": "trade_date", "type": "date"},
    {"name": "open", "type": "float"},
    {"name": "high", "type": "float"},
    {"name": "low", "type": "float"},
    {"name": "close", "type": "float"}
]
```

---

## 注意事项

1. **安全性**：确保 `${}` 参数经过验证，防止 SQL 注入（建议配合白名单或类型校验）。
2. **性能**：大数据集应优先使用 `getPagingData`。
3. **文件权限**：写回 `.sqlds` 文件时需保证进程有写权限。
4. **缓存失效**：修改 SQL 后建议手动清除 `datadesc` 以触发重新推导。

---

## 总结

`SQLDataSourceProcessor` 提供了一种声明式的方式来定义基于 SQL 的数据接口，结合配置文件与异步数据库访问，实现了高效、可维护的数据服务层组件。特别适用于报表、配置化页面、低代码平台等场景。