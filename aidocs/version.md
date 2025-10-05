# 版本信息模块文档

## 概述

本模块定义了当前软件包的版本号，采用语义化版本控制（Semantic Versioning）格式。

## 版本属性

### `__version__`

- **类型**: 字符串 (str)
- **值**: `'0.3.4'`
- **作用**: 存储当前软件包的版本标识

#### 版本号解析
版本号 `0.3.4` 遵循 `主版本号.次版本号.修订号` 的格式：
- **主版本号 (Major)**: `0` - 初始开发阶段，可能包含不兼容的API变更
- **次版本号 (Minor)**: `3` - 向后兼容的功能新增
- **修订号 (Patch)**: `4` - 向后兼容的问题修复

## 使用示例

```python
# 导入版本信息
import your_package

# 获取当前版本
print(f"当前版本: {your_package.__version__}")

# 版本比较示例
current_version = your_package.__version__
if current_version == '0.3.4':
    print("使用的是最新版本")
```

## 版本控制规范

本项目遵循[语义化版本控制 2.0.0](https://semver.org/lang/zh-CN/)规范：

1. **主版本号**：当你做了不兼容的 API 修改
2. **次版本号**：当你做了向下兼容的功能性新增
3. **修订号**：当你做了向下兼容的问题修正

## 相关工具

可以使用以下方式查询版本：

```bash
python -c "import your_package; print(your_package.__version__)"
```

> **注意**：请将 `your_package` 替换为实际的包名称。