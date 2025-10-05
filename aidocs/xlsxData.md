# `XLSXData` 类技术文档

> **模块**: `xlsxdata.py`  
> **依赖库**: `openpyxl`, `json`

---

## 概述

`XLSXData` 是一个用于从 Excel 文件（`.xlsx`）中读取结构化数据的 Python 类。它通过配置描述文件定义数据表的元信息，从而提取字段信息和实际数据记录。

该类适用于需要将 Excel 表格作为数据源的应用场景，例如后台管理系统中的数据导入、展示与分页查询。

---

## 文件格式说明（`xlsxds` 格式）

`XLSXData` 使用一个 JSON 格式的描述对象来指定 Excel 文件的结构布局。该描述对象包含以下字段：

```json
{
  "xlsxfile": "./data.xlsx",
  "data_from": 7,
  "data_sheet": "Sheet1",
  "label_at": 1,
  "name_at": null,
  "datatype_at": 2,
  "ioattrs_at": 3,
  "listhide_at": 4,
  "inputhide_at": 5,
  "frozen_at": 6
}
```

### 字段解释

| 字段名         | 类型 | 描述 |
|----------------|------|------|
| `xlsxfile`     | str  | Excel 文件路径 |
| `data_from`    | int  | 数据起始行号（默认为 2），表示从哪一行开始读取数据记录 |
| `data_sheet`   | str  | 工作表名称，默认为 `"Sheet1"` |
| `label_at`     | int or null | 标签所在行号（用于显示名称），若为 `null` 则使用默认名 |
| `name_at`      | int or null | 字段英文名所在行号，若为 `null` 则生成为 `f1`, `f2`, ... |
| `datatype_at`  | int or null | 数据类型所在行号（如 `str`, `int`, `float` 等） |
| `ioattrs_at`   | int or null | 输入输出属性（JSON 字符串）所在行号 |
| `listhide_at`  | int or null | 控制列表是否隐藏的标志行（'Y'/'y' 表示隐藏） |
| `inputhide_at` | int or null | 控制输入界面是否隐藏的标志行 |
| `frozen_at`    | int or null | 控制列是否冻结的标志行 |

> ⚠️ 所有 `_at` 后缀字段均为行号（从 1 开始计数），若设为 `null` 或不存在，则对应功能无效或使用默认值。

---

## 类定义：`XLSXData`

```python
class XLSXData:
    def __init__(self, path, desc)
```

### 构造函数：`__init__(path, desc)`

初始化 XLSX 数据读取器。

#### 参数：
- `path` (str): Excel 文件路径。
- `desc` (dict): 符合上述 `xlsxds` 格式的描述字典。

#### 功能：
- 加载 Excel 文件；
- 获取指定工作表；
- 初始化内部状态。

#### 示例：
```python
desc = {
    "xlsxfile": "./data.xlsx",
    "data_sheet": "Sheet1",
    "data_from": 7,
    "label_at": 1,
    "datatype_at": 2,
    ...
}
xls_data = XLSXData("./data.xlsx", desc)
```

---

## 方法列表

---

### `getBaseFieldsInfo() → List[Dict]`

获取所有字段的基本元信息。

#### 返回值：
```python
[
  {
    "name": "字段英文名",
    "label": "显示标签",
    "type": "数据类型",
    "listhide": True/False,
    "inputhide": True/False,
    "frozen": True/False,
    **其他 IO 属性（来自 ioattrs）**
  },
  ...
]
```

#### 内部调用方法：
- `_fieldName(ws, col)` - 获取字段名
- `_fieldLabel(ws, col)` - 获取显示标签
- `_fieldType(ws, col)` - 获取数据类型
- `_fieldIOattrs(ws, col)` - 解析并返回额外属性（JSON）
- `_isListHide(...)`, `_isInputHide(...)`, `_isFrozen(...)` - 判断各类隐藏/冻结状态

#### 示例输出：
```json
[
  {
    "name": "user_id",
    "label": "用户ID",
    "type": "int",
    "listhide": false,
    "inputhide": true,
    "frozen": true,
    "width": 100,
    "editor": "numberbox"
  }
]
```

> 💡 若 `ioattrs_at` 行的内容是合法 JSON 字符串，其键值对会合并到结果中。

---

### `getPeriodData(min_r: int, max_r: int) → List[Dict]`

读取指定行范围内的数据记录。

#### 参数：
- `min_r` (int): 起始行号（含）
- `max_r` (int): 结束行号（不含）

#### 返回值：
- 列表形式的数据记录，每条记录是以字段名为键的字典。

#### 注意事项：
- 自动断言 `min_r >= data_from`
- 若 `max_r > 最大行数`，则自动截断
- 使用 `_fieldName` 获取列名映射

#### 示例：
```python
data = xls_data.getPeriodData(7, 10)
# 返回第7~9行的数据
```

---

### `getData(ns: dict) → List[Dict]`

获取全部数据记录。

#### 参数：
- `ns` (dict): 命名空间参数（未使用）

#### 返回值：
- 从 `data_from` 行到末尾的所有数据。

#### 相当于：
```python
self.getPeriodData(data_from, ws.max_row + 1)
```

---

### `getPagingData(ns: dict) → Dict`

实现分页数据查询。

#### 参数：
- `ns` (dict): 分页参数
  - `page` (int): 当前页码（从 1 开始），默认为 1
  - `rows` (int): 每页行数，默认为 50

#### 返回值：
```json
{
  "total": 100,
  "rows": [
    { "col1": "val1", "col2": "val2" },
    ...
  ]
}
```

#### 计算逻辑：
- 起始行：`(page - 1) * rows + data_from`
- 结束行：`page * rows + data_from + 1`

#### 示例请求参数：
```python
ns = {'page': 2, 'rows': 20}
result = xls_data.getPagingData(ns)
```

---

### `getArgumentsDesc(ns, request) → None`

预留方法，用于获取参数描述（当前未实现）。

> ✅ 当前返回 `None`，可用于扩展接口文档生成功能。

---

## 私有方法详解

这些方法仅供内部使用，负责解析某一列的特定属性。

| 方法 | 说明 |
|------|------|
| `_fieldName(ws, i)` | 若 `name_at` 存在，取该行第 i 列值；否则返回 `'f'+i` |
| `_fieldLabel(ws, i)` | 取 `label_at` 行值，若无则同上 |
| `_fieldType(ws, i)` | 取 `datatype_at` 行值，缺省为 `'str'` |
| `_fieldIOattrs(ws, i)` | 读取 `ioattrs_at` 行内容，并尝试 `json.loads` 解析，失败时打印错误并返回 `{}` |
| `_isListHide(ws, i)` | 检查 `listhide_at` 是否为 'Y'/'y' |
| `_isInputHide(ws, i)` | 检查 `inputhide_at` 是否为 'Y'/'y' |
| `_isFrozen(ws, i)` | 检查 `frozen_at` 是否为 'Y'/'y' |

> 🔴 **Bug 提示**：在 `_isFrozen()` 方法中存在变量错误！应为 `ws.cell(x, i).value` 而不是 `ws.cell(x, y).value`！

#### 修复建议：
```python
def _isFrozen(self, ws, i):
    x = self.desc.get('frozen_at')
    if x is not None:
        t = ws.cell(x, i).value  # 原代码误写成 y
        if t == 'Y' or t == 'y':
            return True
    return False
```

---

## 使用示例

```python
from xlsxdata import XLSXData

desc = {
    "xlsxfile": "./employees.xlsx",
    "data_sheet": "Staff",
    "data_from": 2,
    "label_at": 1,
    "name_at": None,
    "datatype_at": None,
    "ioattrs_at": 3,
    "listhide_at": 4,
    "inputhide_at": 5,
    "frozen_at": 6
}

xls = XLSXData("./employees.xlsx", desc)

# 获取字段信息
fields = xls.getBaseFieldsInfo()
print(json.dumps(fields, ensure_ascii=False, indent=2))

# 获取全部数据
all_data = xls.getData({})
print(f"共加载 {len(all_data)} 条记录")

# 分页获取（第2页，每页10条）
paged = xls.getPagingData({'page': 2, 'rows': 10})
print(f"当前页数据条数: {len(paged['rows'])}, 总计: {paged['total']}")
```

---

## 异常处理与注意事项

- 若 `ioattrs` 内容非合法 JSON，会捕获异常并打印错误日志，不影响主流程。
- 所有行索引基于 1（与 Excel 一致），程序内部无需转换。
- 不支持多 sheet 联合分析。
- 不修改原始 Excel 文件（只读模式）。

---

## 已知问题（Bug）

⚠️ 在方法 `_isFrozen` 中存在 **严重 Bug**：

```python
t = ws.cell(x,y).value  # ❌ 变量 y 未定义！应为 i
```

这会导致运行时报错 `NameError: name 'y' is not defined`。

✅ **必须修复为**：
```python
t = ws.cell(x, i).value
```

---

## 总结

| 特性 | 支持情况 |
|------|----------|
| 读取 Excel 数据 | ✅ |
| 元数据驱动配置 | ✅ |
| 字段级属性控制 | ✅（隐藏、冻结、编辑属性等） |
| 分页支持 | ✅ |
| JSON 属性嵌入 | ✅ |
| 错误容忍机制 | ✅（部分） |
| 安全性 | ⚠️ 需注意 JSON 解析风险 |
| 可维护性 | ⚠️ 存在一个关键 bug |

---

## 建议改进方向

1. 🛠 修复 `_isFrozen` 中的变量引用错误；
2. 🔒 添加 `read_only=True` 提升性能（如无需写操作）；
3. 📦 将 `desc` 验证封装成独立方法；
4. 🧪 增加单元测试覆盖核心方法；
5. 📄 支持 `.xls` 或其他格式可通过抽象接口扩展。

--- 

📝 文档版本：v1.0  
📅 更新时间：2025-04-05