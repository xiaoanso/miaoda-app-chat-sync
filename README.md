# GitHub Code Sync Skill for Miaoda

> 🚀 Sync code from GitHub to Miaoda platform with structured JSON instructions

## 🎯 What This Skill Does

This OpenClaw Skill fetches code from GitHub repositories and generates **structured JSON instructions** that you can send to Miaoda's chat API for accurate code updates.

**Key Features:**
- ✅ Fetch code from any GitHub repository (public or private)
- ✅ Support for specific commits and branches
- ✅ Generate JSON structured instructions for maximum AI accuracy
- ✅ File filtering and batching for large projects
- ✅ Independent from miaoda-app-builder - works with any Miaoda setup
- ✅ Automatic cleanup of temporary files

---

## 📋 Prerequisites

1. **Python 3.8+**
2. **Git** (must be installed and in PATH)
3. **GitHub Token** (for private repositories)
4. **Miaoda App ID and Context ID**

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# No Python packages required - only uses standard library
# Just ensure Git is installed:
git --version
```

### 2. Set GitHub Token (for private repos)

```bash
export GITHUB_TOKEN="ghp_your_personal_access_token"
```

### 3. Get Miaoda App Info

```bash
# List your apps
python miaoda-app-builder/scripts/miaoda_api.py list-apps --brief

# Get app detail with context ID
python miaoda-app-builder/scripts/miaoda_api.py app-detail --app-id app-abc123xyz
```

### 4. Sync Code

```bash
python skill/scripts/github_sync.py sync \
  --repo https://github.com/username/my-project \
  --app-id app-abc123xyz \
  --context-id conv-def456uvw
```

### 5. Copy JSON to Miaoda Chat

The script will output formatted JSON instructions. Copy the JSON block and send it to Miaoda chat!

---

## 📖 Usage Examples

### Example 1: Sync Latest Code (Public Repository)

```bash
python skill/scripts/github_sync.py sync \
  --repo https://github.com/username/my-project \
  --app-id app-abc123xyz \
  --context-id conv-def456uvw
```

**Output:**
```
📦 GitHub Code Sync - Structured Update Instructions
═══════════════════════════════════════════════════════

📋 Summary:
  Repository: https://github.com/username/my-project
  Branch: main
  Commit: abc123def456
  Files: 45
  Total Size: 2.3 MB
  Generated: 2026-04-28 17:30:00

═══════════════════════════════════════════════════════

📝 Copy the following JSON and send to Miaoda chat:

```json
{
  "action": "UPDATE_ALL_FILES",
  "files": [...]
}
```
```

---

### Example 2: Sync Specific Commit

```bash
python skill/scripts/github_sync.py sync \
  --repo https://github.com/username/my-project \
  --commit abc123def456 \
  --app-id app-abc123xyz \
  --context-id conv-def456uvw
```

---

### Example 3: Private Repository

```bash
export GITHUB_TOKEN="ghp_your_token"

python skill/scripts/github_sync.py sync \
  --repo https://github.com/username/private-repo \
  --app-id app-abc123xyz \
  --context-id conv-def456uvw
```

---

### Example 4: Filter Files

```bash
# Only sync Python and JavaScript files
python skill/scripts/github_sync.py sync \
  --repo https://github.com/username/my-project \
  --filter "*.py,*.js,*.html" \
  --app-id app-abc123xyz \
  --context-id conv-def456uvw
```

---

### Example 5: Large Project (Batch Sync)

```bash
# Batch 1: Configuration files
python skill/scripts/github_sync.py sync \
  --repo https://github.com/username/my-project \
  --filter "*.json,*.yaml,*.toml" \
  --max-files 20 \
  --app-id app-abc123xyz \
  --context-id conv-def456uvw \
  --output batch1_config.json

# Batch 2: Frontend code
python skill/scripts/github_sync.py sync \
  --repo https://github.com/username/my-project \
  --filter "src/*.vue,src/*.js" \
  --max-files 30 \
  --app-id app-abc123xyz \
  --context-id conv-def456uvw \
  --output batch2_frontend.json

# Batch 3: Backend code
python skill/scripts/github_sync.py sync \
  --repo https://github.com/username/my-project \
  --filter "api/*.py" \
  --max-files 30 \
  --app-id app-abc123xyz \
  --context-id conv-def456uvw \
  --output batch3_backend.json
```

Then send each batch to Miaoda chat separately.

---

### Example 6: Save to File

```bash
python skill/scripts/github_sync.py sync \
  --repo https://github.com/username/my-project \
  --app-id app-abc123xyz \
  --context-id conv-def456uvw \
  --output update_instructions.json
```

---

### Example 7: View Repository Info

```bash
python skill/scripts/github_sync.py info \
  --repo https://github.com/username/my-project \
  --branch main
```

---

### Example 8: Compare Commits

```bash
python skill/scripts/github_sync.py diff \
  --repo https://github.com/username/my-project \
  --from abc123 \
  --to def456
```

---

## 📊 Complete Workflow

```
1. Local Development
   ↓
   git push origin main

2. Generate Sync Instructions
   ↓
   python skill/scripts/github_sync.py sync \
     --repo https://github.com/user/repo \
     --app-id xxx --context-id yyy

3. Copy JSON Output
   ↓
   (Copy the JSON block from output)

4. Send to Miaoda Chat
   ↓
   (Paste JSON as message)

5. AI Updates Files
   ↓
   (Wait for completion)

6. Verify & Preview
   ↓
   https://www.miaoda.cn/projects/{app_id}

7. Publish (if ready)
   ↓
   python miaoda-app-builder/scripts/miaoda_api.py publish --app-id xxx --wait
```

---

## 🔧 Command Reference

### sync Command

Fetch code and generate structured instructions.

```bash
python skill/scripts/github_sync.py sync [options]
```

**Required:**
- `--repo REPO_URL`: GitHub repository URL
- `--app-id APP_ID`: Miaoda application ID
- `--context-id CONTEXT_ID`: Miaoda conversation ID

**Optional:**
- `--branch BRANCH`: Git branch (default: main)
- `--commit COMMIT`: Specific commit hash (overrides branch)
- `--token TOKEN`: GitHub token (or use GITHUB_TOKEN env)
- `--max-files N`: Max files to sync (default: 50)
- `--filter PATTERN`: File filter (e.g., "*.py,*.js")
- `--output FILE`: Save to file
- `--no-instructions`: Output only JSON

---

### diff Command

Show changed files between commits.

```bash
python skill/scripts/github_sync.py diff \
  --repo REPO_URL \
  --from COMMIT1 \
  --to COMMIT2
```

---

### info Command

Get repository information.

```bash
python skill/scripts/github_sync.py info \
  --repo REPO_URL \
  --branch BRANCH
```

---

## 📁 File Handling

### Automatically Included:
- ✅ Python (.py)
- ✅ JavaScript/TypeScript (.js, .jsx, .ts, .tsx)
- ✅ HTML/CSS (.html, .css, .scss, .less)
- ✅ Config (.json, .yaml, .yml, .toml, .env)
- ✅ Documentation (.md, .txt)
- ✅ Other text files (.vue, .svelte, .xml, .sql)

### Automatically Excluded:
- ❌ Binary files (images, fonts, executables)
- ❌ .git directory
- ❌ Dependencies (node_modules, __pycache__, venv)
- ❌ Build artifacts (dist, build, .next)
- ❌ System files (.DS_Store, Thumbs.db)

---

## 🎯 Best Practices

### 1. Use Specific Commits

```bash
# ✅ Reproducible
--commit abc123def456

# ⚠️ May change
--branch main
```

### 2. Batch Large Projects

- Split into batches of <50 files
- Sync config files first
- Then frontend, then backend

### 3. Verify After Sync

1. Check updated file list
2. Preview project
3. Test functionality
4. Publish if ready

### 4. Keep Records

```bash
python skill/scripts/github_sync.py sync \
  --repo https://github.com/user/repo \
  --commit abc123 \
  --app-id xxx --context-id yyy \
  --output sync_$(date +%Y%m%d_%H%M%S).json
```

---

## ⚠️ Limitations

1. **File Limit**: Recommended <50 files per sync
2. **File Size**: Individual files >100KB may cause issues
3. **Binary Files**: Not supported
4. **AI Accuracy**: ~90-95% with JSON instructions
5. **No Direct Upload**: Must use Miaoda chat

---

## ❓ Troubleshooting

### "Repository not found"
- Check URL is correct
- For private repos, provide token: `--token ghp_xxx`

### "Too many files"
- Use filter: `--filter "*.py,*.js"`
- Reduce max: `--max-files 30`

### "Access denied"
- Verify token has repo access
- Token needs at least `repo` scope

### "JSON output too large"
- Split into batches
- Use `--filter` to select specific files

---

## 📦 Project Structure

```
skill/
├── SKILL.md                    # Skill description
├── _meta.json                  # Metadata
├── scripts/
│   └── github_sync.py          # Core sync script
├── requirements.txt            # Dependencies (none!)
└── README.md                   # This file
```

---

## 🔒 Security

- **Token**: Passed via env var or parameter, never stored
- **Temp Files**: Automatically cleaned up
- **No Data Retention**: Only outputs JSON instructions
- **Minimal Permissions**: Token only needs read access

---

## 📝 License

MIT

---

## 🙏 Credits

Built for use with [Miaoda Platform](https://www.miaoda.cn)

---

**Last Updated**: 2026-04-28  
**Version**: 1.0.0
