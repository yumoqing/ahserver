---
name: ahserver-repo
version: 1.0.0
description: ahserver
trigger_conditions:
  - 需要理解、修改或排障 ahserver 的代码
  - 在 ahserver 里定位入口、数据表、对外契约或构建方式
---

# ahserver 仓库技能

> 由仓库实际内容生成的骨架（README/目录/模型定义/契约/构建脚本逐项取证）。新增判断与坑位请直接在下面对应小节补充。

## 定位

**ahserver**

ahserver is a http(s) server base on aiohttp asynchronous framework. ahserver capabilities: + 'dspy' file subffix by '.dspy', is process as a python script + 'tmpl' files subffix by '.tmpl', is process as a template + 'md' files subffix by '.md', is process as a markdown file + 'xlsxds' files subffi

- 远端：`https://github.com/yumoqing/ahserver.git`
- 默认分支：`main`（共 190 个提交）
- 最近提交：2026-11-10 `0c4e05a` fix(resource): invalid path 语义裸 Exception -> InvalidPathError(HTTPNotFound)
- 规模：74 个文件；Python 34，Shell 1，JSON 1

## 目录结构

- `ahserver/` — Python 包源码（模块本体）（32 个文件）
- `aidocs/` — AI/开发文档（31 个文件）
- `test/` — 测试（2 个文件）
- `docs/` — 文档（1 个文件）
- 根文件：`.gitignore`、`README.md`、`ah.py`、`build.sh`、`change.log`、`changelog.txt`、`pyproject.toml`、`setup.cfg`

## 注册入口

- `ahserver/loadplugins.py` → `load_plugins()`

## 构建与运行

- `build.sh`（一键部署）
- `pyproject.toml`：`?` v?，依赖 0 项
- Python 包 `ahserver/`：`__init__.py`、`auth_api.py`、`baseProcessor.py`、`configuredServer.py`、`dsProcessor.py`、`error.py`、`filedownload.py`、`filestorage.py`

## README 要点与注意（摘自 `README.md`）

- 章节：python3.12 bug fix、Requirements、Usage、Folder structure、Configuration file content、international、performance、Behind the nginx、environment for processors、Hot Reload、Change logs
- 注意：	aiohttp.web.HTTPForbidden	禁止访问

## 建议阅读顺序

1. `README.md`
2. `docs/`
3. `aidocs/`
4. `build.sh`

