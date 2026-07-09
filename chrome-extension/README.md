# Repo JSON Generator - Chrome 扩展

Chrome 浏览器扩展，作为 [`web-ui/server.py`](../web-ui/server.py) 的便捷前端。你自行启动本地 Python 后端，扩展通过 API 生成结构化 JSON 并支持复制/下载。

## 功能

- **弹窗完整 UI**：点击扩展图标打开弹窗，配置 / 结果 / 设置 三个标签页
- **配置 / 结果 / 设置分栏**：弹窗内切换标签；设置页可配置后端地址、默认命令等
- **自动识别**：浏览 GitHub / GitLab / Bitbucket 时自动预填仓库、分支、commit
- **手动录入**：任意页面可手动输入，分支/commit 支持下拉或键盘输入
- **JSON 导出**：执行后一键复制或下载 `.json` 文件
- **执行历史**：最近 20 条记录，刷新后不丢失

## 安装

### 1. 启动后端（必须）

```bash
# 项目根目录
export GITHUB_TOKEN=your_token   # 私有仓库可选
python3 web-ui/server.py         # 默认 http://localhost:8080
```

### 2. 加载扩展

1. 打开 Chrome，访问 `chrome://extensions/`
2. 开启右上角「开发者模式」
3. 点击「加载已解压的扩展程序」
4. 选择本目录 `chrome-extension/`

### 3. 配置后端地址

点击扩展图标打开弹窗，切换到「**设置**」标签，确认后端地址与 `server.py` 端口一致（默认 `http://localhost:8080`），点击「测试连接」验证后保存。

也可通过扩展详情页的「扩展程序选项」打开独立设置页（与弹窗设置共用同一配置）。

## 使用

1. 浏览 GitHub / GitLab / Bitbucket 仓库页面
2. **点击浏览器工具栏中的扩展图标**，打开弹窗
3. 表单会自动预填当前仓库信息（也可手动修改或点击「从页面填充」）
4. 在「配置」页选择命令类型，点击「执行」
5. 切换到「结果」页查看 JSON，点击 📋 复制或 💾 下载

**快捷键**：`Ctrl+Enter`（Mac: `Cmd+Enter`）执行命令

> 注意：弹窗关闭后正在进行的请求会中断，执行大仓库时请保持弹窗打开直至完成。

## 目录结构

```
chrome-extension/
├── manifest.json
├── background/service-worker.js   # 右键菜单、页面上下文
├── content/git-host.js            # Git 托管页面 URL 解析
├── popup/                         # 弹窗主界面
├── options/                       # 设置页
├── lib/api.js                     # 后端 API 客户端
└── icons/                         # 扩展图标
```

## API 说明

扩展调用与 Web UI 相同的后端接口：

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/status` | GET | 检测在线状态与 Token |
| `/api/branches?repo=` | GET | 分支列表 |
| `/api/commits?repo=&branch=&limit=` | GET | 最近 commit |
| `/api/generate` | POST | 执行 sync/info/full |

## 自动识别规则

| 平台 | 识别内容 |
|------|----------|
| GitHub | `/{owner}/{repo}`、`/tree/{branch}`、`/commit/{sha}` |
| GitLab | `/{ns}/{project}`、`/-/tree/{branch}`、`/-/commit/{sha}` |
| Bitbucket | `/projects/{ws}/repos/{repo}`、`/src/{branch}` |

在非 Git 页面打开弹窗时，会加载上次保存的表单配置，可完全手动输入。

## 与 Web UI 的关系

扩展和 `http://localhost:8080` 的 Web UI 是**同一后端的两个前端**，可同时使用，共用同一个 `server.py` 实例。

## 故障排查

| 问题 | 解决方案 |
|------|----------|
| 显示「后端离线」 | 确认 `python3 web-ui/server.py` 已启动 |
| 私有仓库失败 | 设置 `GITHUB_TOKEN` 环境变量后重启 server |
| 页面未自动填充 | 确认在 GitHub/GitLab/Bitbucket 仓库页，或手动点击「从页面填充」 |
| 端口不一致 | 在扩展设置中修改后端地址，如 `http://localhost:3000` |
