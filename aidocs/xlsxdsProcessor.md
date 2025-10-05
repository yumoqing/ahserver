# XLSX 数据源处理器技术文档

```markdown
# `XLSXDataSourceProcessor` 技术文档

## 概述

`XLSXDataSourceProcessor` 是一个基于 `.xlsx` 文件的数据源处理器，继承自 `DataSourceProcessor`。它用于从 Excel 文件中读取结构化数据和字段元信息，并支持分页查询。该类通过配置文件指定 Excel 文件路径及数据布局规则，实现灵活的数据提取。

该处理器适用于需要将 Excel 表格作为数据源的场景，如配置管理、静态数据导入等。

---

## 依赖库

- `openpyxl`: 用于读取 `.xlsx` 文件。
- `codecs`: 编码处理（当前未直接使用，可能为预留或间接依赖）。
- `appPublic.jsonConfig.getConfig`: 获取全局配置对象。
- `.dsProcessor.DataSourceProcessor`: 数据源处理器基类。
- `.xlsxData.XLSXData`: 封装对 Excel 文件的具体操作。

---

## 配置格式（`xlsxds` 格式）

`XLSXDataSourceProcessor` 使用特定 JSON 结构描述 Excel 文件的数据布局：

```json
{
  "xlsxfile": "./data.xlsx",
  "data_from": 7,
  "data_sheet": "Sheet1",
  "label_at": 1,
  "name_at": null,
  "datatype_at": 2,
  "ioattrs": 3,
  "listhide_at": 4,
  "inputhide_at": 5,
  "frozen_at": 6
}
```

### 字段说明

| 字段名         | 类型     | 必填 | 描述 |
|----------------|----------|------|------|
| `xlsxfile`     | string   | 是   | Excel 文件路径（相对或绝对），支持 URL 转换。 |
| `data_from`    | integer  | 是   | 数据起始行号（从 1 开始计数）。 |
| `data_sheet`   | string   | 否   | 工作表名称，默认为 `"Sheet1"`。 |
| `label_at`     | integer  | 是   | 字段标签所在行号。 |
| `name_at`      | integer/null | 否 | 字段名所在行号；若为 `null`，则使用默认命名规则（如 col0, col1...）。 |
| `datatype_at`  | integer  | 是   | 字段类型所在行号。 |
| `ioattrs`      | integer  | 是   | I/O 属性所在行号。 |
| `listhide_at`  | integer  | 是   | 列表中是否隐藏标志所在行号。 |
| `inputhide_at` | integer  | 是   | 输入界面中是否隐藏标志所在行号。 |
| `frozen_at`    | integer  | 是   | 冻结列标志所在行号。 |

> **注意**：所有行号均以 1 为基础编号。

---

## 类定义

```python
class XLSXDataSourceProcessor(DataSourceProcessor)
```

### 继承关系

- 父类：`DataSourceProcessor`
- 子系统接口：符合统一数据源处理规范。

---

## 方法说明

### `isMe(name: str) -> bool`  
**@classmethod**

判断当前处理器是否匹配给定名称。

#### 参数：
- `name` (str): 数据源类型标识符。

#### 返回值：
- `True` 当 `name == 'xlsxds'` 时；
- 否则返回 `False`。

#### 示例：
```python
if XLSXDataSourceProcessor.isMe("xlsxds"):
    processor = XLSXDataSourceProcessor()
```

---

### `getArgumentsDesc(dict_data, ns, request)` → `None`

获取参数描述（当前未实现）。

#### 参数：
- `dict_data`: 配置字典。
- `ns`: 命名空间对象。
- `request`: 请求上下文。

#### 返回值：
- 固定返回 `None`，表示无额外参数描述。

> ⚠️ 当前功能占位，未来可扩展用于生成 API 文档或校验输入参数。

---

### `async getDataDesc(dict_data, ns, request)` → `dict`

异步获取数据结构描述（字段元信息）。

#### 功能：
加载指定 Excel 文件并解析字段基本信息（如标签、类型、属性等）。

#### 参数：
- `dict_data`: 包含 `xlsxds` 配置的字典。
- `ns`: 上下文命名空间。
- `request`: 请求对象，用于构建绝对路径。

#### 流程：
1. 提取 `xlsxfile` 路径；
2. 使用 `absurl` 和 `abspath` 解析为本地绝对路径；
3. 初始化 `XLSXData` 实例；
4. 调用 `.getBaseFieldsInfo(ns)` 获取字段元数据。

#### 返回值：
- 字段信息列表，格式示例：
  ```json
  [
    {
      "name": "id",
      "label": "编号",
      "type": "int",
      "inputhide": false,
      "listhide": true,
      ...
    },
    ...
  ]
  ```

---

### `async getData(dict_data, ns, request)` → `list[dict]`

异步获取全部数据记录。

#### 功能：
读取 Excel 中从 `data_from` 行开始的所有数据行，转换为字典列表。

#### 参数：
同 `getDataDesc`。

#### 流程：
1. 解析文件路径；
2. 创建 `XLSXData` 实例；
3. 调用 `.getData(ns)` 获取完整数据集。

#### 返回值：
- 数据列表，每项为 `{字段名: 值}` 的字典。

---

### `async getPagingData(dict_data, ns, request)` → `dict`

异步获取分页数据。

#### 功能：
支持分页查询，返回当前页数据及总数。

#### 参数：
同上。

#### 返回值：
- 分页结果对象，格式如下：
  ```json
  {
    "page": 1,
    "pageSize": 20,
    "total": 100,
    "data": [...]
  }
  ```
> 实际结构取决于 `XLSXData.getPagingData()` 的实现。

---

## 内部组件协作

### `XLSXData` 类职责
- 封装 Excel 文件的打开与读取；
- 解析元信息行（label, type, hide 等）；
- 提供统一接口获取字段描述和数据；
- 支持分页逻辑。

### 路径处理机制
使用 `self.g.absurl(request, path)` 和 `self.g.abspath(...)` 将相对路径或资源 URL 转换为可访问的本地文件路径。

---

## 使用示例

假设配置文件 `config.json` 内容如下：

```json
{
  "type": "xlsxds",
  "xlsxfile": "./data/users.xlsx",
  "data_from": 2,
  "data_sheet": "Users",
  "label_at": 1,
  "name_at": null,
  "datatype_at": 2,
  "ioattrs": 3,
  "listhide_at": 4,
  "inputhide_at": 5,
  "frozen_at": 6
}
```

在系统中注册后，可通过以下方式调用：

```python
processor = XLSXDataSourceProcessor(g=global_context)
fields = await processor.getDataDesc(config, ns, request)
data = await processor.getData(config, ns, request)
paged = await processor.getPagingData(config, ns, request)
```

---

## 注意事项

1. **性能限制**：大文件可能导致内存占用高，建议控制 Excel 文件大小。
2. **并发安全**：每个请求创建独立的 `XLSXData` 实例，避免状态冲突。
3. **异常处理**：未显式捕获异常，需确保上游有错误兜底机制。
4. **编码兼容性**：Excel 本身不涉及文本编码问题（`openpyxl` 自动处理 UTF-8）。

---

## 扩展建议

- 添加字段映射别名支持；
- 支持写入操作（导出回写）；
- 引入缓存机制提升重复读取效率；
- 增加校验层验证必填字段是否存在。

---
```

> ✅ **文档版本**：1.0  
> 📦 **所属模块**：`app.datasource.xlsxds`  
> © 2025 内部技术文档，禁止外传