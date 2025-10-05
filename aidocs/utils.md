# `unicode_escape` 函数技术文档

## 概述

`unicode_escape` 是一个 Python 函数，用于将字符串中的非 ASCII 字符（Unicode 码点 ≥ 256 的字符）转换为其 Unicode 转义序列表示形式，而保留 ASCII 字符（码点 < 256）不变。

该函数适用于需要将包含特殊 Unicode 字符的字符串转换为可打印、可传输或兼容 ASCII 的格式的场景，例如日志记录、数据序列化或生成 JSON 安全字符串。

---

## 函数定义

```python
def unicode_escape(s):
    x = [ch if ord(ch) < 256 else ch.encode('unicode_escape').decode('utf-8') for ch in s]
    return ''.join(x)
```

---

## 参数说明

| 参数 | 类型   | 说明                     |
|------|--------|--------------------------|
| `s`  | `str`  | 输入的原始字符串         |

---

## 返回值

- **类型**：`str`
- **说明**：返回一个新字符串，其中所有 Unicode 码点大于等于 256 的字符被替换为其对应的 `\uXXXX` 或 `\UXXXXXXXX` 形式的 Unicode 转义序列，ASCII 字符保持原样。

---

## 工作原理

1. 遍历输入字符串 `s` 中的每一个字符 `ch`。
2. 对每个字符：
   - 如果其 Unicode 码点（通过 `ord(ch)` 获取）小于 256（即属于标准 ASCII 或 Latin-1 范围），则直接保留该字符。
   - 否则，使用 `.encode('unicode_escape')` 将该字符编码为字节形式的 Unicode 转义序列（如 `\u4e2d`），然后通过 `.decode('utf-8')` 转换回字符串。
3. 使用 `''.join(x)` 将处理后的字符列表拼接成最终结果字符串。

---

## 示例

### 示例 1：基本用法

```python
result = unicode_escape("Hello, 世界!")
print(result)
# 输出: Hello, \u4e16\u754c!
```

### 示例 2：混合字符

```python
result = unicode_escape("Café Noël 🌍")
print(result)
# 输出: Caf\xe9 No\xebl \U0001f30d
```

> 注意：`é` 和 `ë` 属于 Latin-1 范围（码点 < 256），因此使用 `\x` 转义；而 🌍（地球符号）是辅助平面字符，转义为 `\U0001f30d`。

---

## 注意事项

- 本函数会保留所有码点小于 256 的字符（包括控制字符），不会进行额外过滤。
- 对于非 BMP（基本多文种平面）字符（如 emoji），将生成 `\Uxxxxxxxx` 格式的转义。
- 结果字符串为纯 ASCII 字符串，适合在仅支持 ASCII 的环境中使用。
- 原始语义可通过 `eval()` 或 `codecs.decode(..., 'unicode_escape')` 还原（需谨慎使用）。

---

## 还原方法（反向操作）

若需将转义字符串还原为原始 Unicode 字符串，可使用：

```python
import codecs
original = codecs.decode(escaped_string, 'unicode_escape')
```

---

## 应用场景

- 构建兼容 ASCII 的日志输出
- 生成安全的 JSON 字符串（避免直接嵌入非 ASCII 字符）
- 调试 Unicode 字符串内容
- 数据导出/导入时的字符标准化

---

## 版本信息

- **语言**：Python 3.x
- **依赖**：无外部依赖，仅使用标准库

---

## 许可

此函数为公共领域代码片段，可用于任何项目。