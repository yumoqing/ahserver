# Web 应用启动框架技术文档

本项目提供一个基于 `ahserver` 的轻量级 Web 服务启动框架，支持通过命令行参数配置工作目录和端口，并自动加载 JSON 配置文件以初始化服务器环境。该模块适用于快速搭建可配置的 Python Web 服务。

---

## 目录

- [功能概述](#功能概述)
- [依赖说明](#依赖说明)
- [核心函数](#核心函数)
  - [`webapp(init_func)`](#webappinit_func)
  - [`webserver(init_func, workdir, port=None)`](#webserverinit_func-workdir-portnone)
- [配置系统](#配置系统)
- [命令行参数](#命令行参数)
- [使用示例](#使用示例)
- [日志系统](#日志系统)
- [入口点（main）](#入口点main)

---

## 功能概述

该脚本实现了以下功能：

- 解析命令行参数（工作目录、端口）
- 加载指定路径下的 JSON 配置文件
- 初始化日志系统
- 调用用户自定义初始化函数
- 启动基于 `ConfiguredServer` 的 Web 服务器

主要用于快速部署基于 `ahserver` 框架的 Web 应用。

---

## 依赖说明

| 模块 | 来源 | 用途 |
|------|------|------|
| `os`, `sys` | Python 内置 | 系统路径与环境操作 |
| `argparse` | Python 内置 | 命令行参数解析 |
| `MyLogger`, `info`, `debug`, `warning` | `appPublic.log` | 日志记录工具 |
| `ProgramPath` | `appPublic.folderUtils` | 获取程序运行路径 |
| `getConfig` | `appPublic.jsonConfig` | 加载并渲染 JSON 配置文件 |
| `ConfiguredServer` | `ahserver.configuredServer` | 可配置的 Web 服务器主类 |
| `ServerEnv` | `ahserver.serverenv` | 全局服务器运行环境 |

> ⚠️ 注意：两次导入 `getConfig` 属于冗余，建议优化为一次导入。

---

## 核心函数

### `webapp(init_func)`

启动 Web 应用的顶层入口函数，负责解析命令行参数并调用底层服务启动逻辑。

#### 参数

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `init_func` | `callable` | 在服务器启动前执行的初始化回调函数（如注册路由、数据库连接等） |

#### 命令行选项

| 选项 | 简写 | 说明 |
|------|------|------|
| `--workdir` | `-w` | 指定应用的工作目录，默认为当前目录 |
| `--port` | `-p` | 指定监听端口号（可选），若未设置则从配置文件或默认值获取 |

#### 流程说明

1. 创建 `ArgumentParser` 实例
2. 解析 `-w/--workdir` 和 `-p/--port`
3. 设置 `workdir`（优先使用参数，否则为 `os.getcwd()`）
4. 调用 `webserver(init_func, workdir, port)` 启动服务

---

### `webserver(init_func, workdir, port=None)`

实际启动 Web 服务器的核心函数。

#### 参数

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `init_func` | `callable` | 初始化函数，在服务器启动前调用 |
| `workdir` | `str` | 应用根目录，用于查找配置文件 |
| `port` | `int or None` | 指定监听端口，优先级低于命令行但高于配置文件 |

#### 执行流程

1. **获取程序路径**  
   使用 `ProgramPath()` 获取可执行文件所在路径。

2. **加载配置文件**  
   ```python
   config = getConfig(workdir, NS={'workdir': workdir, 'ProgramPath': p})
   ```
   - 从 `workdir` 目录加载 `config.json` 或 `.conf` 文件
   - 支持模板变量替换：`{workdir}`, `{ProgramPath}`

3. **初始化日志系统**
   - 若配置中包含 `logger` 字段，则按配置创建 `MyLogger`
   - 否则使用默认配置：
     - 名称：`webapp`
     - 级别：`info`
     - 不写入文件

4. **执行用户初始化函数**  
   调用传入的 `init_func()`，可用于注册中间件、路由、数据库等。

5. **设置服务器环境**
   - 创建 `ServerEnv()` 单例，设置 `workdir` 和 `port`

6. **启动服务器**
   - 实例化 `ConfiguredServer(workdir=workdir)`
   - 确定最终端口顺序：
     1. 函数参数 `port`
     2. 配置文件中的 `website.port`
     3. 默认值 `8080`
   - 调用 `server.run(port=port)` 启动 HTTP 服务

---

## 配置系统

配置通过 `appPublic.jsonConfig.getConfig()` 加载，支持如下结构（示例 `config.json`）：

```json
{
  "logger": {
    "name": "myweb",
    "levelname": "debug",
    "logfile": "{workdir}/logs/app.log"
  },
  "website": {
    "port": 8000
  }
}
```

> ✅ 支持变量插值：`{workdir}`, `{ProgramPath}` 将被自动替换为对应值。

---

## 命令行参数

可通过命令行控制运行参数：

```bash
python app.py -w /path/to/project -p 9000
```

等价于：

```bash
python app.py --workdir=/path/to/project --port=9000
```

如果不指定：

- `workdir` → 当前目录
- `port` → 依次取值：`None` → `config.website.port` → `8080`

---

## 日志系统

日志由 `MyLogger` 提供，行为如下：

| 配置项 | 是否必需 | 默认值 | 说明 |
|--------|----------|--------|------|
| `logger.name` | 否 | `'webapp'` | 日志器名称 |
| `logger.levelname` | 否 | `'info'` | 日志级别（支持 debug/info/warning/error） |
| `logger.logfile` | 否 | `None` | 日志输出文件路径，`None` 表示仅输出到控制台 |

> 示例输出：
> ```
> [INFO] 2025-04-05 10:00:00 webapp: Starting server on port 8080...
> ```

---

## 入口点（main）

当直接运行此脚本时，会执行以下代码：

```python
if __name__ == '__main__':
    from main import main
    webapp(main)
```

要求项目根目录下存在 `main.py` 并定义 `main()` 函数作为初始化入口。

### 示例 `main.py`

```python
def main():
    print("Initializing application...")
    # 注册路由、加载插件、连接数据库等
```

---

## 使用示例

### 项目结构

```
/myproject/
├── app.py                  # 本启动脚本
├── main.py                 # 初始化逻辑
└── config.json             # 配置文件
```

### 启动方式

```bash
# 使用默认配置（当前目录 + 8080端口）
python app.py

# 自定义工作目录和端口
python app.py -w /myproject -p 3000
```

---

## 注意事项

1. **重复导入问题**  
   当前有两行：
   ```python
   from appPublic.jsonConfig import getConfig
   ```
   应合并为一行，避免冗余。

2. **异常处理缺失**  
   当前代码没有捕获配置加载失败、端口占用等异常，建议增加 try-except 包裹。

3. **端口类型转换**  
   `port = int(port)` 是安全的，但应确保输入为数字字符串或整数。

4. **ServerEnv 的作用**  
   `se = ServerEnv()` 被创建但仅设置了 `workdir` 和 `port`，需确认是否在其他地方被使用。

---

## 总结

该模块是一个简洁高效的 Web 服务启动器，适合中小型项目快速集成。其特点包括：

- ✅ 配置驱动
- ✅ 支持命令行覆盖
- ✅ 灵活的日志配置
- ✅ 易于扩展（通过 `init_func`）

推荐配合 `ahserver` 生态使用，实现模块化 Web 开发。