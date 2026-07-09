# Repo JSON Generator - Web UI

图形化 Web 界面，用于从 Git 仓库生成结构化 JSON 指令。

## 快速开始

### 1. 启动服务器

在项目根目录运行：

```bash
python3 web-ui/server.py
```

或者指定端口：

```bash
python3 web-ui/server.py 3000
```

### 2. 打开浏览器

访问 `http://localhost:8080`（或你指定的端口）

### 3. 配置参数并执行

1. 选择命令类型（sync / info / full），下方会显示命令说明
2. 输入仓库 URL（输入后会自动加载分支列表）
3. 选择或手动输入分支（切换分支后自动加载最近版本）
4. （可选）选择或手动输入 Commit Hash（留空则使用最新 commit）
5. （可选）展开高级选项设置过滤条件、最大文件数、版本加载数量
6. 点击「执行」按钮，或按 `Ctrl+Enter`

页头会显示 `GITHUB_TOKEN` 是否已配置，便于排查私有仓库访问问题。

## API 接口

| 端点 | 方法 | 参数 | 说明 |
|------|------|------|------|
| `/api/status` | GET | — | 返回 `{ hasToken: bool }` |
| `/api/branches` | GET | `repo` | 获取远程分支列表 |
| `/api/commits` | GET | `repo`, `branch`, `limit`（可选，默认 30） | 获取分支最近版本 |
| `/api/versions` | GET | 同上 | 与 `/api/commits` 等价 |
| `/api/generate` | POST | JSON body | 执行 sync/info/full，返回结构化 JSON |

### POST /api/generate 请求体

```json
{
  "command": "sync",
  "repo": "https://github.com/user/repo.git",
  "branch": "main",
  "commit": "",
  "filter": "",
  "exclude": "",
  "maxFiles": 50
}
```

### 成功响应

```json
{
  "success": true,
  "data": { "...": "完整 JSON 指令" },
  "meta": {
    "command": "sync",
    "duration": 12.3,
    "repo": "...",
    "branch": "main",
    "commit": "abc123..."
  }
}
```

服务端直接调用 `RepoJSONGenerator` Python API，不再依赖 CLI stdout 解析，保证 JSON 输出稳定可靠。

## 功能特性

- **三种核心命令**
  - `sync` - 生成代码同步 JSON 指令
  - `info` - 获取 Commit 信息和变更文件
  - `full` - 获取完整仓库内容快照

- **辅助查询（自动化）**
  - 输入仓库 URL 后自动加载分支
  - 切换分支后自动加载最近 commit 版本
  - 分支/commit 支持 combobox：既可下拉选择，也可手动输入

- **结果展示**
  - 执行摘要卡片（文件数、增删行、耗时等）
  - JSON 语法高亮
  - 大结果默认折叠 `files[].content`，可展开/折叠
  - 执行日志独立 tab

- **状态持久化**
  - 表单配置自动保存到 localStorage
  - 执行历史（最近 20 条）刷新后不丢失
  - 点击历史项可恢复配置

- **其他**
  - Token 状态指示
  - 仓库 URL 格式校验
  - 快捷键：`Ctrl+Enter` 执行，`Esc` 关闭 loading
  - 深色主题，移动端自适应

## 系统要求

- Python 3.8+
- Git（已安装并配置在 PATH 中）
- 现代浏览器（Chrome / Firefox / Edge / Safari）

## 环境变量（可选）

如果需要访问私有仓库，请设置 GitHub Token：

```bash
export GITHUB_TOKEN=your_token_here
python3 web-ui/server.py
```

## 文件结构

```
web-ui/
├── server.py      # Python HTTP 后端服务
├── index.html     # 前端界面
└── README.md      # 说明文档
```

## 使用说明

详见项目根目录的 [USER_GUIDE.md](../USER_GUIDE.md) 和 [SKILL.md](../SKILL.md)。
