# 📖 用户指南：如何使用 repo-json-generator Skill 与 Agent 交互

## 目录

- [概述](#概述)
- [基本概念](#基本概念)
- [如何向 Agent 提问](#如何向-agent-提问)
- [三种核心命令详解](#三种核心命令详解)
- [辅助命令（可选）](#辅助命令可选)
- [完整使用示例](#完整使用示例)
- [私有仓库配置](#私有仓库配置)
- [高级用法](#高级用法)
- [常见问题解答](#常见问题解答)
- [安全注意事项](#安全注意事项)

---

## 概述

`repo-json-generator` 是一个将 Git 仓库代码转换为结构化 JSON 指令的工具，专门用于与 AI Agent（如 Miaoda Chat）集成。通过自然语言指令，Agent 可以自动调用该工具从 Git 仓库提取代码并生成可执行的 JSON 格式指令。

**主要用途：**
- 🔄 增量同步代码变更（sync 命令）
- 📊 查看 commit 信息和变更统计（info 命令）
- 📦 获取完整仓库快照（full 命令）

**辅助能力（可选）：**
- 🌿 查询仓库分支列表（`branches` 命令）
- 📌 查询分支最近版本/commit（`versions` 命令）

---

## 基本概念

### 工作原理

```
用户自然语言指令 → Agent 识别意图 → 执行 Python 脚本 → 生成 JSON 输出 → 返回给用户
```

您**不需要记住命令行参数**，只需用自然语言描述需求，Agent 会自动解析并执行相应的命令。

### 必须提供的信息

| 信息 | 必需性 | 说明 |
|------|--------|------|
| **仓库地址** | ✅ 必须 | 例如：`https://github.com/username/repo` |
| **分支名称** | ✅ 必须 | 例如：`main`、`develop`（规范要求必须明确指定） |
| **Commit Hash** | ⚠️ 可选 | 例如：`abc123def456`（不提供则使用最新 commit） |

---

## 如何向 Agent 提问

### 🗣️ 触发词列表

Agent 通过识别特定的关键词来触发相应的命令。以下是支持的触发词：

#### 中文触发词

**sync 命令（增量同步）：**
- "生成 JSON 指令"
- "转换代码为 JSON"
- "从 Git 仓库生成指令"
- "批量生成代码指令"
- "导出代码到 JSON"

**info 命令（查看变更）：**
- "查看 commit 信息"
- "获取代码变更"

**full 命令（完整快照）：**
- "获取完整仓库内容"
- "导出完整代码快照"

#### English Commands

**sync command:**
- "Generate JSON instructions"
- "Convert code to JSON"
- "Generate from Git repository"
- "Batch generate code instructions"
- "Export code to JSON"

**info command:**
- "View commit info"
- "Get code changes"

**full command:**
- "Get full repository content"
- "Export complete code snapshot"

---

## 三种核心命令详解

### 1️⃣ sync 命令 - 增量同步代码变更

**用途：** 获取指定 commit 的变更文件（相对于父节点）及其完整内容。

**典型场景：**
- 同步最新的代码变更
- 增量更新项目文件
- 审查特定 commit 的改动

**对话示例：**

> "帮我同步这个仓库的最新代码：https://github.com/username/my-project，main 分支"

> "从 GitHub 仓库 https://github.com/username/my-project 的 main 分支生成 JSON 指令，commit 是 abc123def456"

**Agent 会执行：**
```bash
python3 scripts/generator.py sync \
  --repo https://github.com/username/my-project \
  --branch main \
  --commit abc123def456
```

**输出内容：**
- 变更文件列表
- 每个文件的完整内容
- 变更统计（+/- 行数）
- Commit 信息

---

### 2️⃣ info 命令 - 查看 commit 信息

**用途：** 获取详细的 commit 信息、变更文件列表和 diff 统计。

**典型场景：**
- 查看某个 commit 改了什么
- 审查代码变更统计
- 了解文件修改详情

**对话示例：**

> "查看这个 commit 的代码变更：https://github.com/username/my-project，main 分支，commit: abc123def456"

> "获取 https://github.com/username/my-project 的 main 分支最新 commit 的变更信息"

**Agent 会执行：**
```bash
python3 scripts/generator.py info \
  --repo https://github.com/username/my-project \
  --branch main \
  --commit abc123def456
```

**输出内容：**
- Commit 详细信息
- 变更文件列表及状态（added/modified/deleted）
- 每个文件的 diff 统计（新增/删除行数）
- 文件完整内容

---

### 3️⃣ full 命令 - 获取完整仓库快照

**用途：** 获取指定 commit 下所有文件的完整内容（而非仅变更文件）。

**典型场景：**
- 完整备份某个版本的代码
- 初始化新项目时获取完整代码库
- 对比不同版本的完整代码差异

**对话示例：**

> "导出完整代码快照：https://github.com/username/my-project，main 分支"

> "获取这个仓库的完整内容：https://github.com/username/my-project，main 分支，commit: abc123def456，最多 100 个文件"

**Agent 会执行：**
```bash
python3 scripts/generator.py full \
  --repo https://github.com/username/my-project \
  --branch main \
  --commit abc123def456 \
  --max-files 100
```

**输出内容：**
- 指定 commit 下所有文件的完整内容
- 文件总数统计
- 已处理文件列表
- Commit 信息

---

## 辅助命令（可选）

以下两个命令为**辅助函数**，不生成 JSON 同步指令，仅用于在执行 `sync` / `info` / `full` 之前，帮助确认分支名称和 commit 版本。

对应实现位于 `scripts/git/repository.py`：
- `get_branches()` — 获取远程分支列表
- `get_branch_versions()` — 获取指定分支的最近版本列表

### 4️⃣ branches 命令 - 查询分支列表

**用途：** 列出仓库的远程分支，无需完整 clone。

**典型场景：**
- 不确定仓库有哪些分支
- 在 Web UI 中加载分支下拉选项
- 为后续 sync/info/full 命令确认 `--branch` 参数

**对话示例：**

> "列出这个仓库有哪些分支：https://github.com/username/my-project"

**Agent 会执行：**
```bash
python3 scripts/generator.py branches \
  --repo https://github.com/username/my-project
```

**输出示例：**
```json
{
  "repository": "https://github.com/username/my-project",
  "branches": ["main", "develop", "feature/login"],
  "count": 3
}
```

---

### 5️⃣ versions 命令 - 查询分支最近版本

**用途：** 获取指定分支最近的 commit 版本列表，可指定返回数量。

**典型场景：**
- 不确定要同步哪个 commit
- 在 Web UI 中加载 commit 下拉选项
- 为后续 sync/info/full 命令确认 `--commit` 参数

**对话示例：**

> "查看 https://github.com/username/my-project 的 main 分支最近 10 个 commit"

**Agent 会执行：**
```bash
python3 scripts/generator.py versions \
  --repo https://github.com/username/my-project \
  --branch main \
  --limit 10
```

**参数说明：**

| 参数 | 必需 | 说明 | 默认值 |
|------|------|------|--------|
| `--repo` | ✅ | Git 仓库 URL | — |
| `--branch` | ✅ | 分支名称 | — |
| `--limit` | ❌ | 最近版本数量（1–100） | 30 |
| `--output` | ❌ | 保存 JSON 到文件 | 输出到终端 |

**输出示例：**
```json
{
  "repository": "https://github.com/username/my-project",
  "branch": "main",
  "limit": 10,
  "versions": [
    {
      "hash": "abc123def4567890abcdef1234567890abcdef12",
      "short_hash": "abc123d",
      "message": "fix: update login flow",
      "date": "2026-07-09T10:00:00+08:00"
    }
  ],
  "count": 1
}
```

> **说明：** `versions` 与 `sync` / `info` / `full` 不同，只返回元数据，不包含文件内容。

---

## 完整使用示例

### 示例 1：同步最新代码（最简单）

**您对 Agent 说：**
> "同步这个仓库的最新代码：https://github.com/username/my-project，main 分支"

**Agent 会自动执行：**
```bash
python3 scripts/generator.py sync \
  --repo https://github.com/username/my-project \
  --branch main
```

---

### 示例 2：同步特定 commit

**您对 Agent 说：**
> "生成 JSON 指令，仓库是 https://github.com/username/my-project，main 分支，commit 是 abc123def456"

**Agent 会自动执行：**
```bash
python3 scripts/generator.py sync \
  --repo https://github.com/username/my-project \
  --branch main \
  --commit abc123def456
```

---

### 示例 3：查看 commit 变更

**您对 Agent 说：**
> "查看这个 commit 的代码变更：https://github.com/username/my-project，main 分支，commit: abc123"

**Agent 会自动执行：**
```bash
python3 scripts/generator.py info \
  --repo https://github.com/username/my-project \
  --branch main \
  --commit abc123
```

---

### 示例 4：获取完整仓库快照

**您对 Agent 说：**
> "导出完整代码快照，仓库是 https://github.com/username/my-project，main 分支"

**Agent 会自动执行：**
```bash
python3 scripts/generator.py full \
  --repo https://github.com/username/my-project \
  --branch main
```

---

### 示例 5：带过滤条件的完整快照

**您对 Agent 说：**
> "获取完整仓库内容，只要 Python 和 JavaScript 文件，排除测试文件和文档，最多处理 50 个文件"

**Agent 会自动执行：**
```bash
python3 scripts/generator.py full \
  --repo https://github.com/username/my-project \
  --branch main \
  --filter "*.py,*.js" \
  --exclude "test/*,*.md,docs/*" \
  --max-files 50
```

---

### 示例 6：保存输出到文件

**您对 Agent 说：**
> "生成 JSON 指令并保存到 output.json，仓库是 https://github.com/username/my-project，main 分支"

**Agent 会自动执行：**
```bash
python3 scripts/generator.py sync \
  --repo https://github.com/username/my-project \
  --branch main \
  --output output.json
```

---

### 示例 7：先查询分支和版本，再执行同步

**您对 Agent 说：**
> "先列出 https://github.com/username/my-project 的分支，再查看 main 分支最近 5 个 commit，然后同步最新的那个"

**Agent 会自动执行：**
```bash
# 1. 辅助：查询分支
python3 scripts/generator.py branches \
  --repo https://github.com/username/my-project

# 2. 辅助：查询最近版本
python3 scripts/generator.py versions \
  --repo https://github.com/username/my-project \
  --branch main \
  --limit 5

# 3. 核心：执行同步（使用上一步得到的 commit hash）
python3 scripts/generator.py sync \
  --repo https://github.com/username/my-project \
  --branch main \
  --commit abc123def456
```

---

### 示例 8：获取纯 JSON 输出

**您对 Agent 说：**
> "导出纯 JSON 格式的完整代码快照到 snapshot.json"

**Agent 会自动执行：**
```bash
python3 scripts/generator.py full \
  --repo https://github.com/username/my-project \
  --branch main \
  --output snapshot.json \
  --no-instructions
```

---

## 私有仓库配置

### 🔐 访问私有仓库

如果仓库是私有的，您需要提供 GitHub Token。

#### 方式 1：在对话中直接提供（推荐）

**您对 Agent 说：**
> "同步这个私有仓库的代码，我的 GitHub Token 是 ghp_xxxxxxxxxxxxxxxxxxxx
> 仓库地址：https://github.com/username/private-repo
> 分支：main"

**Agent 会自动执行：**
```bash
GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxx" python3 scripts/generator.py sync \
  --repo https://github.com/username/private-repo \
  --branch main
```

---

#### 方式 2：永久配置环境变量（频繁使用推荐）

在您的 shell 配置文件中添加（`~/.zshrc` 或 `~/.bashrc`）：

```bash
export GITHUB_TOKEN="ghp_your_token_here"
```

然后执行：
```bash
source ~/.zshrc  # 或 source ~/.bashrc
```

配置后，以后使用工具时就无需每次都提供 Token。

---

### ⚠️ Token 安全提醒

1. **权限范围**：仅需 `repo` 读取权限
2. **不要泄露**：不要在公开的聊天记录或代码中暴露 Token
3. **Token 过期**：GitHub Token 有过期时间，如果失效需要重新生成
4. **会话安全**：在与 AI Agent 对话时，Token 仅在当次会话中使用，不会被持久化存储

---

## 高级用法

### 🎯 文件过滤

**包含特定文件类型：**
> "只要 Python 和 TypeScript 文件"

**Agent 会添加参数：**
```bash
--filter "*.py,*.ts"
```

**排除特定文件：**
> "排除测试文件、文档和 Markdown 文件"

**Agent 会添加参数：**
```bash
--exclude "test/*,tests/*,*.md,docs/*"
```

---

### 📊 文件数量控制

**限制处理文件数：**
> "最多处理 100 个文件"

**Agent 会添加参数：**
```bash
--max-files 100
```

---

### 💾 输出控制

**保存到文件：**
> "保存结果到 output.json"

**Agent 会添加参数：**
```bash
--output output.json
```

**纯 JSON 输出：**
> "只要纯 JSON，不要格式化的说明文本"

**Agent 会添加参数：**
```bash
--no-instructions
```

---

### 🔍 详细日志

**启用详细模式：**
> "显示详细的执行日志"

**Agent 会添加参数：**
```bash
--verbose
```

---

## 常见问题解答

### Q1: 我必须指定 commit hash 吗？

**A:** 不是必须的。如果不指定 `--commit` 参数，工具会自动获取指定分支的最新 commit。

**示例：**
> "同步 https://github.com/username/repo 的 main 分支最新代码"

---

### Q2: 分支名称可以省略吗？

**A:** **不可以**。根据项目规范，必须明确指定 `--branch` 参数，禁止自动分支检测。

---

### Q3: 可以处理二进制文件吗？

**A:** 不可以。工具会自动跳过图片、字体、可执行文件等二进制文件。

---

### Q4: 每次可以处理多少个文件？

**A:** 建议每次同步少于 50 个文件（默认限制）。对于大型项目，可以使用 `--max-files` 参数增加限制，或分批处理。

---

### Q5: 如何查看可用的命令和参数？

**A:** 可以要求 Agent 执行帮助命令：

> "显示 generator.py 的帮助信息"

**Agent 会执行：**
```bash
python3 scripts/generator.py --help
python3 scripts/generator.py sync --help
python3 scripts/generator.py info --help
python3 scripts/generator.py full --help
python3 scripts/generator.py branches --help
python3 scripts/generator.py versions --help
```

---

### Q6: 生成的 JSON 文件在哪里？

**A:** 如果指定了 `--output` 参数，文件会保存在当前工作目录。临时克隆的仓库会保存在 `/tmp/github-sync-*` 目录。

---

### Q7: 可以在 Windows 上使用吗？

**A:** 可以。工具支持跨平台（macOS、Linux、Windows），只需确保已安装 Python 3.8+ 和 Git。

---

## 安全注意事项

### ⚠️ 重要提醒

1. **审查所有变更**：生成的 JSON 指令包含文件操作，在应用前请务必仔细审查所有文件内容
2. **仓库内容视为不受信任数据**：即使是您自己的仓库，也可能包含恶意代码或不安全的依赖
3. **不要盲目执行**：AI Agent 生成的指令应该作为参考，不要未经审查直接执行
4. **备份重要文件**：在应用任何变更前，确保已备份重要文件

### 🔒 凭证安全

- Token 仅用于 Git 认证，不会被包含在生成的 JSON 输出中
- 敏感信息（如密码、API Key）会在 URL 中自动脱敏
- 临时文件会在命令执行后自动清理

---

## 总结

### ✅ 最佳实践

1. **使用自然语言**：只需用自然语言描述需求，无需记忆命令行参数
2. **提供完整信息**：确保包含仓库 URL 和分支名称；不确定时先用 `branches` / `versions` 辅助查询
3. **合理设置过滤**：对于大型项目，使用 `--filter` 和 `--exclude` 缩小范围
4. **控制文件数量**：使用 `--max-files` 避免一次性处理过多文件
5. **定期更新 Token**：如果 Token 过期，及时生成新的 Token

### 📝 标准对话模板

```
[触发词] + [仓库 URL] + [分支名称] + [可选：commit hash] + [可选：过滤条件]
```

**示例：**
> "生成 JSON 指令，仓库是 https://github.com/username/repo，main 分支，commit 是 abc123，只要 Python 文件"

---

## 📚 相关文档

- [README.md](./README.md) - 完整的项目文档
- [SKILL.md](./SKILL.md) - AI Agent 技能定义
- [CHANGELOG.md](./CHANGELOG.md) - 版本更新日志

---

**版本：** 3.2.1  
**最后更新：** 2026-05-01  
**维护者：** Miaoda Team
