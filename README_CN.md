# Repo JSON Generator（仓库 JSON 指令生成器）

[![版本](https://img.shields.io/badge/version-3.2.0-blue.svg)](CHANGELOG.md)
[![Python](https://img.shields.io/badge/python-3.8+-green.svg)](https://www.python.org/)
[![许可证](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

将 Git 仓库代码转换为结构化 JSON 指令，供 AI Agent 和自动化工具使用。

## 📋 概述

**Repo JSON Generator** 从 Git 仓库（GitHub、GitLab、Bitbucket 等）获取代码，并生成**结构化 JSON 指令**，可被任何 AI Agent 或自动化系统消费，以实现准确的代码处理和更新。

**📖 英文版文档：[README.md](README.md)**
**📖 中文使用文档：[USER_GUIDE.md](USER_GUIDE.md)**

### 核心特性

- ✅ **高准确率**：结构化 JSON 准确率达 90-95%（自然语言仅 70-80%）
- ✅ **模块化架构**：清晰、可维护的代码库，模块相互独立
- ✅ **批处理**：大型项目自动拆分（>50 个文件）
- ✅ **文件过滤**：按模式包含/排除文件（`--filter`、`--exclude`）
- ✅ **多命令支持**：`sync` 用于代码同步，`info` 用于查看 commit 信息，`full` 用于完整快照
- ✅ **辅助查询**：`branches` 和 `versions` 用于在执行同步前查询分支和最近版本
- ✅ **跨平台**：支持 Windows、macOS 和 Linux
- ✅ **零依赖**：仅需 Python 3.8+ 和 Git
- ✅ **安全特性**：包含 Token 保护、自动清理和敏感数据脱敏

### 为什么使用结构化 JSON？

| 方面                 | 自然语言     | 结构化 JSON         |
| -------------------- | ------------ | ------------------- |
| **准确率**     | 70-80%       | 90-95%              |
| **文件完整性** | 可能遗漏文件 | JSON 结构保证完整性 |
| **可控性**     | 难以验证     | 处理前易于验证      |
| **批处理**     | 困难         | 内置支持            |

---

## 🚀 快速开始

### 前置要求

- **Python 3.8+**
- **Git**（已安装并添加到 PATH）
- **GitHub Token**（私有仓库需要，可选）

### 安装

无需安装！只需克隆或下载此仓库。

```bash
# 克隆或下载此仓库
cd miaoda-app-chat-sync
```

### 基本使用

#### 1. 获取Commit 信息完整内容（Sync 命令）

```bash
# 基础同步 - 为整个仓库生成 JSON
python3 scripts/generator.py sync \
  --repo https://github.com/username/my-project \
  --branch main \
  --commit abc123def456
```

#### 2. 获取Commit 信息变更内容（Info 命令）

```bash
# 获取详细的 commit 信息及文件内容
python3 scripts/generator.py info \
  --repo https://github.com/username/my-project \
  --branch main \
  --commit abc123def456
```

#### 3. 获取完整仓库快照完整内容（Full 命令）

```bash
# 获取指定 commit 的完整文件内容
python3 scripts/generator.py full \
  --repo https://github.com/username/my-project \
  --branch main \
  --commit abc123def456 \
  --max-files 100
```

#### 4. 查看帮助

```bash
# 查看所有可用命令和选项
python3 scripts/generator.py --help
```

#### 5. 辅助命令（可选）

在执行 `sync` / `info` / `full` 之前，可用以下命令查询分支和最近版本：

```bash
# 列出远程分支
python3 scripts/generator.py branches \
  --repo https://github.com/username/my-project

# 列出分支最近 commit（默认 30 条，最多 100 条）
python3 scripts/generator.py versions \
  --repo https://github.com/username/my-project \
  --branch main \
  --limit 10
```

---

## 📖 命令参考

### `sync` 命令

获取详细的 commit 信息，包括变更文件的完整内容。

#### 必需参数

| 参数         | 说明                            | 示例                              |
| ------------ | ------------------------------- | --------------------------------- |
| `--repo`   | Git 仓库 URL                    | `https://github.com/user/repo`  |
| `--branch` | 分支名称（必需）                | `main`、`master`、`develop` |
| `--commit` | Commit hash（可选，默认为最新） | `abc123def456`                  |

#### 可选参数

| 参数                  | 说明                        | 默认值     |
| --------------------- | --------------------------- | ---------- |
| `--filter`          | 仅包含匹配模式的文件        | 所有文件   |
| `--exclude`         | 排除匹配模式的文件          | 无         |
| `--max-files`       | 最大处理文件数              | 50         |
| `--output`          | 保存输出到文件              | 仅终端显示 |
| `--no-instructions` | 输出纯 JSON（无格式化说明） | 显示说明   |

#### 示例

```bash
# 同步指定文件（Python 和 JavaScript）
python3 scripts/generator.py sync \
  --repo https://github.com/user/repo \
  --branch main \
  --filter "*.py,*.js" \
  --max-files 30 \
  --output sync_output.json

# 排除测试和文档文件
python3 scripts/generator.py sync \
  --repo https://github.com/user/repo \
  --branch main \
  --exclude "*.md,test/*,docs/*" \
  --output sync_output.json
```

---

### `info` 命令

获取详细的 commit 信息，包括变更文件及其变化内容。

#### 必需参数

| 参数         | 说明             | 示例                              |
| ------------ | ---------------- | --------------------------------- |
| `--repo`   | Git 仓库 URL     | `https://github.com/user/repo`  |
| `--branch` | 分支名称（必需） | `main`、`master`、`develop` |

#### 可选参数

| 参数                  | 说明                 | 默认值      |
| --------------------- | -------------------- | ----------- |
| `--commit`          | 指定 commit hash     | 最新 commit |
| `--filter`          | 仅包含匹配模式的文件 | 所有文件    |
| `--exclude`         | 排除匹配模式的文件   | 无          |
| `--output`          | 保存输出到文件       | 仅终端显示  |
| `--no-instructions` | 保存纯 JSON 到文件   | 格式化输出  |

#### 示例

```bash
# 获取包含完整文件内容的 commit 信息
python3 scripts/generator.py info \
  --repo https://github.com/user/repo \
  --branch main \
  --commit abc123def456

# 保存到文件（格式化输出）
python3 scripts/generator.py info \
  --repo https://github.com/user/repo \
  --branch main \
  --commit abc123def456 \
  --output changes.json

# 仅保存纯 JSON
python3 scripts/generator.py info \
  --repo https://github.com/user/repo \
  --branch main \
  --commit abc123def456 \
  --output changes.json \
  --no-instructions

# 过滤特定文件类型
python3 scripts/generator.py info \
  --repo https://github.com/user/repo \
  --branch main \
  --commit abc123def456 \
  --filter "*.ts,*.tsx" \
  --output changes.json
```

#### 输出行为

| 场景                                 | 终端     | 文件                      |
| ------------------------------------ | -------- | ------------------------- |
| 无`--output`                       | 显示摘要 | 不保存                    |
| 有`--output`                       | 显示摘要 | 完整格式化（摘要 + JSON） |
| `--output` + `--no-instructions` | 显示摘要 | 仅纯 JSON                 |

**注意**：在所有场景下，终端**始终**显示摘要信息。

---

### `full` 命令

获取指定 commit 版本的所有文件的完整内容。此命令检索给定 commit 处的完整仓库快照（而非仅变更文件）。

**使用场景：**

- 在特定版本进行完整仓库备份
- 使用完整代码库初始化新项目
- 对比不同版本间的完整代码差异
- 生成全面的文档

#### 必需参数

| 参数         | 说明             | 示例                              |
| ------------ | ---------------- | --------------------------------- |
| `--repo`   | Git 仓库 URL     | `https://github.com/user/repo`  |
| `--branch` | 分支名称（必需） | `main`、`master`、`develop` |

#### 可选参数

| 参数                  | 说明                                     | 默认值      |
| --------------------- | ---------------------------------------- | ----------- |
| `--commit`          | 指定 commit hash                         | 最新 commit |
| `--filter`          | 仅包含匹配模式的文件（如 "*.py,*.js"） | 所有文件    |
| `--exclude`         | 排除匹配模式的文件（如 "*.md,test/*"） | 无          |
| `--max-files`       | 最大处理文件数                           | `50`      |
| `--output`          | 保存输出到文件                           | 仅终端显示  |
| `--no-instructions` | 输出纯 JSON（无格式化说明）              | 格式化输出  |
| `--verbose`         | 启用详细日志                             | 禁用        |

#### 示例

```bash
# 获取指定 commit 的完整仓库内容
python3 scripts/generator.py full \
  --repo https://github.com/user/repo \
  --branch main \
  --commit abc123def456

# 获取完整内容并限制文件数量
python3 scripts/generator.py full \
  --repo https://github.com/user/repo \
  --branch main \
  --commit abc123def456 \
  --max-files 100

# 过滤特定文件类型
python3 scripts/generator.py full \
  --repo https://github.com/user/repo \
  --branch main \
  --filter "*.py,*.js,*.ts" \
  --exclude "test/*,*.md" \
  --output full-snapshot.json

# 保存纯 JSON 到文件
python3 scripts/generator.py full \
  --repo https://github.com/user/repo \
  --branch main \
  --commit abc123def456 \
  --output full-snapshot.json \
  --no-instructions
```

#### 输出格式

`full` 命令输出的 JSON 结构与 `sync` 相同，但包含 commit 中的**所有**文件：

```json
{
  "action": "CREATE_OR_UPDATE_FILES",
  "description": "请根据以下 JSON 数据创建或更新所有文件...",
  "commit_message": "完整仓库快照，commit: abc123",
  "source": {
    "repository": "https://github.com/user/repo",
    "branch": "main",
    "commit": "abc123def456"
  },
  "summary": {
    "total_files_in_commit": 150,
    "files_processed": 100,
    "files": [...]
  },
  "rules": [...],
  "files": [
    {
      "path": "src/main.py",
      "action": "CREATE_OR_OVERWRITE",
      "content": "# 完整文件内容..."
    }
  ]
}
```

---

### 辅助命令（`branches` / `versions`）

这两个命令为**辅助函数**，实现在 `scripts/git/repository.py`（`get_branches()`、`get_branch_versions()`）。它们不生成 JSON 同步指令，仅返回仓库元数据，帮助你在执行核心命令前确认 `--branch` 和 `--commit` 参数。

#### `branches` 命令

无需完整 clone，列出远程分支。

| 参数 | 必需 | 说明 |
|------|------|------|
| `--repo` | ✅ | Git 仓库 URL |
| `--output` | ❌ | 保存 JSON 到文件 |

```bash
python3 scripts/generator.py branches --repo https://github.com/user/repo
```

#### `versions` 命令

获取指定分支最近的 commit 版本列表。

| 参数 | 必需 | 说明 | 默认值 |
|------|------|------|--------|
| `--repo` | ✅ | Git 仓库 URL | — |
| `--branch` | ✅ | 分支名称 | — |
| `--limit` | ❌ | 最近版本数量（1–100） | 30 |
| `--output` | ❌ | 保存 JSON 到文件 | — |

```bash
python3 scripts/generator.py versions \
  --repo https://github.com/user/repo \
  --branch main \
  --limit 10
```

---

## 🏗️ 架构设计（v3.2.0）

### 模块化结构

```
scripts/
├── generator.py              # 主入口点（CLI 路由）
├── core/
│   ├── constants.py          # 共享常量和配置
│   ├── temp_manager.py       # 跨平台临时目录管理
│   ├── circuit_breaker.py    # 熔断器和重试机制
│   ├── security.py           # 敏感信息保护
│   └── prompts.py            # Prompt 配置管理
├── git/
│   └── repository.py         # Git 仓库操作
└── processors/
    ├── file_processor.py     # 文件读取和过滤
    └── instruction_gen.py    # JSON 指令生成
```

### 模块依赖关系

```
core/（无依赖）
  ↓
git/（依赖 core）
  ↓
processors/（依赖 core、git）
  ↓
generator.py（依赖所有模块）
```

### v3.2.0 架构改进

- **移除 streaming.py**：删除未使用的流输出模块
- **简化依赖**：更清晰的模块结构，仅保留活跃使用的组件
- **增强可维护性**：减少约 320 行无用代码，降低代码复杂度

### 优势

- **可维护性**：每个模块可独立更新
- **可测试性**：模块可单独测试
- **可复用性**：核心组件可在其他项目中复用
- **可读性**：更小、更专注的文件更易于理解

---

## 🔄 AI Agent 集成

### 工作流程

```
用户请求
    ↓
"从 Git 仓库生成 JSON"
    ↓
步骤 1：repo-json-generator
    ├─ 从 Git 克隆仓库
    ├─ 读取所有代码文件
    ├─ 生成结构化 JSON 指令
    └─ 输出：包含文件内容的 JSON 数据
    ↓
步骤 2：您的 AI Agent / 系统
    ├─ 接收 JSON 指令
    ├─ 解析文件列表和内容
    ├─ 创建/覆盖每个文件
    └─ 输出：更新后的文件列表供验证
    ↓
完成！代码已由 AI Agent 处理
```

### JSON 模板格式

```json
{
  "action": "CREATE_OR_UPDATE_FILES",
  "description": "请创建或更新所有文件...",
  "commit_message": "初始提交",
  "source": {
    "repository": "https://github.com/username/repo",
    "branch": "main",
    "commit": "abc123def456"
  },
  "summary": {
    "files_changed": 3,
    "total_additions": 131,
    "total_deletions": 98,
    "files": [...]
  },
  "rules": [
    "1. 必须更新 files 数组中的所有文件",
    "2. 必须原样复制内容",
    "3. 必须保留所有空白和格式"
  ],
  "files": [
    {
      "path": "src/file.ts",
      "status": "modified",
      "action": "CREATE_OR_OVERWRITE",
      "content": "// 文件内容..."
    }
  ]
}
```

| 字段               | 类型   | 说明                                 |
| ------------------ | ------ | ------------------------------------ |
| `action`         | 字符串 | 始终为 "CREATE_OR_UPDATE_FILES"      |
| `description`    | 字符串 | 人类可读的指令                       |
| `commit_message` | 字符串 | Git commit 的提交信息（主题 + 正文） |
| `source`         | 对象   | Git 来源信息，用于追溯               |
| `summary`        | 对象   | 变更摘要                             |
| `rules`          | 数组   | AI Agent 的指令                      |
| `files`          | 数组   | 要创建或更新的文件列表               |

### 与 Miaoda 平台集成

此工具与 `miaoda-app-builder` 配合使用，形成两步工作流：

1. **repo-json-generator**：获取代码并生成 JSON 指令
2. **miaoda-app-builder**：接收 JSON 并通过 Chat API 更新代码

详见 [SKILL.md](SKILL.md) 获取详细集成指南。

---

## 📦 批处理

### 自动拆分

当代码库超过阈值时，工具会自动建议批处理：

| 条件         | 操作       |
| ------------ | ---------- |
| 文件数 > 50  | 建议拆分   |
| 总大小 > 5MB | 建议拆分   |
| 混合文件类型 | 按类别拆分 |

### 推荐的批处理策略

```bash
# 批次 1：配置文件
python3 scripts/generator.py sync \
  --repo <repo_url> \
  --branch main \
  --filter "*.json,*.yaml,*.toml" \
  --max-files 20 \
  --output batch1_config.json

# 批次 2：前端代码
python3 scripts/generator.py sync \
  --repo <repo_url> \
  --branch main \
  --filter "src/*.vue,src/*.js,src/*.ts" \
  --max-files 30 \
  --output batch2_frontend.json

# 批次 3：后端代码
python3 scripts/generator.py sync \
  --repo <repo_url> \
  --branch main \
  --filter "api/*.py,models/*.py" \
  --max-files 30 \
  --output batch3_backend.json
```

### 执行顺序

1. 将批次 1 发送给 AI Agent
2. 等待完成并验证文件列表
3. 将批次 2 发送给 AI Agent
4. 重复直到所有批次完成
5. 最终验证 - 检查所有文件是否同步

---

## 🔒 安全与配置

#### 环境变量

| 变量             | 说明                                  | 必需 |
| ---------------- | ------------------------------------- | ---- |
| `GITHUB_TOKEN` | GitHub 个人访问 Token（用于私有仓库） | 可选 |

**⚠️ 安全提示**：此工具在访问私有仓库时需要 GitHub 凭据。请仅使用最小权限的只读 Token，并限定到特定仓库。

### Token 设置

**公共仓库**（无需 Token）：

```bash
python3 scripts/generator.py sync --repo https://github.com/user/public-repo
```

**私有仓库**（需要 Token）：

```bash
# 步骤 1：创建 Token（GitHub → Settings → Developer settings → Personal access tokens）
# 步骤 2：设置环境变量
export GITHUB_TOKEN="ghp_your_token"
# 步骤 3：使用工具
python3 scripts/generator.py sync --repo https://github.com/user/private-repo
```

**Token 要求：**

- 仅需 `repo` 读取权限
- 格式：`ghp_*`、`gho_*`、`ghu_*`、`ghs_*` 或 `ghr_*`

### 安全机制

**1. 自动 Token 检测**

- 公共仓库：无需 Token 直接克隆
- 私有仓库：自动注入 Token
- 非 GitHub 仓库：不应用 Token

**2. 敏感信息脱敏**
所有敏感数据自动检测并屏蔽：

- GitHub Token：`ghp_*` → `<GITHUB_TOKEN>`
- API 密钥、密码、Bearer Token：自动脱敏

**3. URL 凭据移除**
输出中的所有 URL 自动清理：

```
输入：  https://x-access-token:ghp_abc123@github.com/user/repo.git
输出：  https://github.com/user/repo.git
```

**4. 安全的 Git 操作**

- 非交互模式（`GIT_TERMINAL_PROMPT=0`）
- 通过 URL 传递 Token（不在命令行参数中）
- 在进程列表中不可见

**5. 临时文件安全（跨平台）**

- 执行后自动清理
- 磁盘上不留存敏感数据
- 基于 UUID 的唯一目录名

**临时目录位置：**

| 平台        | 位置                      | 示例                                                  |
| ----------- | ------------------------- | ----------------------------------------------------- |
| macOS/Linux | `/tmp/github-<uuid>/`   | `/tmp/github-a1b2c3d4/`                             |
| Windows     | `%TEMP%\github-<uuid>\` | `C:\Users\user\AppData\Local\Temp\github-a1b2c3d4\` |

**清理机制：**

- 上下文管理器（`with temp_directory()`）
- `atexit` 处理器确保清理
- 信号处理器（`SIGTERM`、`SIGINT`）

---

## 📁 临时文件

### 克隆位置（跨平台）

工具使用系统临时目录，并采用基于 UUID 的名称：

| 平台                  | 位置                      | 示例                                                    |
| --------------------- | ------------------------- | ------------------------------------------------------- |
| **macOS/Linux** | `/tmp/github-<uuid>/`   | `/tmp/github-a1b2c3d4/`                               |
| **Windows**     | `%TEMP%\github-<uuid>\` | `C:\Users\<user>\AppData\Local\Temp\github-a1b2c3d4\` |

### 快速说明

- ✅ **自动清理**：脚本执行完毕后所有临时目录都会被删除
- ✅ **唯一名称**：基于 UUID 的目录名防止冲突
- ✅ **安全性**：执行后磁盘上不留存敏感数据
- ✅ **保证清理**：使用上下文管理器、atexit 处理器和信号处理器

---

## ⚠️ 限制与约束

### 当前限制

| 限制         | 上限       | 建议                       |
| ------------ | ---------- | -------------------------- |
| 每批次文件数 | <50 个文件 | 大型项目使用批处理         |
| 单个文件大小 | <100KB     | 拆分超大文件               |
| 二进制文件   | 不支持     | 排除图片、字体、可执行文件 |
| AI 准确率    | ~90-95%    | 同步后务必验证             |

### 最佳实践

✅ **建议做法：**

- 使用结构化 JSON 模板（本工具输出）
- 按文件类型分批大型项目
- 每次同步后验证文件数量
- 使用特定 commit hash 确保可重现性
- 先同步配置文件

❌ **避免做法：**

- 单批次发送超过 50 个文件
- 在同步中包含二进制文件
- 跳过验证步骤
- 使用自然语言进行代码更新（改用 JSON）
- 在发送给 AI Agent 前修改 JSON 内容

---

## ⚠️ 重要安全注意事项

### 生成的 JSON 指令

**使用前审查**：此工具生成的 JSON 输出包含下游 AI Agent 可能解释为权威命令的指令规则。在将生成的 JSON 传递给其他 AI Agent 或自动化系统之前，请务必审查，特别是：

- 文件列表和路径
- Action 字段（`CREATE_OR_UPDATE_FILES` 等）
- Rules 数组内容
- 文件内容（可能包含敏感数据）

### 仓库来源验证

**信任您的来源**：此工具从 Git 仓库获取代码。仅使用可信的仓库 URL，并在需要可重现性时验证 commit hash。

### 下游 Agent 行为

**AI Agent 解释**：当生成的 JSON 被下游 AI Agent 处理时，它们可能会：

- 根据 JSON 指令创建或覆盖文件
- 将规则解释为严格要求
- 处理可能包含提示注入尝试的仓库内容

**最佳实践**：

1. 执行前始终审查生成的 JSON
2. 使用特定 commit hash 确保可重现性
3. 在发送给下游 Agent 前验证文件列表和内容
4. 维护备份或版本控制以便回滚
5. 将仓库内容视为不受信任的数据

---

## 🐛 故障排除

### 常见问题

| 问题               | 原因              | 解决方案                   |
| ------------------ | ----------------- | -------------------------- |
| 同步后文件缺失     | AI 跳过了某些文件 | 使用带严格规则的 JSON 模板 |
| 代码被修改/改变    | AI 尝试"改进"代码 | 在规则中强调"不要修改"     |
| 同步不完整         | 一次处理太多文件  | 使用批处理                 |
| Token 限制超出     | JSON 太大         | 拆分为更小的批次           |
| 私有仓库访问被拒绝 | 缺少 Token        | 提供 GITHUB_TOKEN          |

---

## 📚 文档

- **[SKILL.md](SKILL.md)**：完整的技能文档，包含集成指南
- **[CHANGELOG.md](CHANGELOG.md)**：版本历史和变更
- **CLI 帮助**：运行 `python3 scripts/generator.py --help` 获取命令参考

---

## 📝 许可证

本项目是 Miaoda 生态系统的一部分。有关许可证信息，请参阅项目文档。

---

## 🤝 贡献

欢迎贡献！请遵循以下指南：

1. 阅读 SKILL.md 文档
2. 遵循模块化架构
3. 充分测试您的更改
4. 如需则更新文档
5. 提交 Pull Request

---

**版本**：3.2.0
**最后更新**：2026-04-30
**Python 版本**：3.8+
**依赖**：Python 标准库 + Git
