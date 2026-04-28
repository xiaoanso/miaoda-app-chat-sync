---
name: github-code-sync
description: Sync code from GitHub repository to Miaoda platform. Fetches code from GitHub, generates structured JSON instructions for accurate code updates via chat API. Works together with miaoda-app-builder skill for complete code sync workflow.
metadata: { "openclaw": {"requires": { "bins": ["python3", "git"], "env":["GITHUB_TOKEN"]},"primaryEnv":"GITHUB_TOKEN" } }
---

# GitHub Code Sync Skill

Sync code from GitHub repositories to Miaoda platform projects.

This skill fetches code from GitHub (using provided credentials and commit versions), then generates **structured JSON instructions** that can be sent to **miaoda-app-builder** skill's chat API for accurate code updates.

---

# 🔄 Two-Skill Collaboration Architecture

## Overview

This skill (`miaoda-app-chat-sync`) **works together with** `miaoda-app-builder` in a **two-step workflow**:

```
┌─────────────────────┐         ┌──────────────────────┐
│  miaoda-app-        │  JSON   │  miaoda-app-         │
│  chat-sync          │ ──────> │  builder             │
│                     │  Code   │                      │
│  1. Fetch from      │  Data   │  2. Update Code      │
│     GitHub          │         │     via Chat API     │
│  3. Generate JSON   │         │  3. Create/Overwrite │
│     Instructions    │         │     Files            │
└─────────────────────┘         └──────────────────────┘
```

## Why Two Skills?

| Aspect | Using Only `miaoda-app-builder` | Two-Skill Collaboration |
|--------|--------------------------------|------------------------|
| **Accuracy** | 70-80% (natural language) | 90-95% (structured JSON) |
| **File Completeness** | May miss files | Guaranteed by JSON structure |
| **Control** | Hard to verify | Easy to validate before sync |
| **Batch Processing** | Difficult | Built-in support |
| **Best For** | Small edits, UI tweaks | Full sync, large updates |

## Collaboration Workflow

### Standard Flow

```
User Request
    ↓
"Sync code from GitHub" / "Update with latest code"
    ↓
Step 1: miaoda-app-chat-sync
    ├─ Clone repository from GitHub
    ├─ Read all code files
    ├─ Generate structured JSON instructions
    └─ Output: JSON data with file contents
    ↓
Step 2: miaoda-app-builder
    ├─ Receive JSON instructions via chat
    ├─ Parse file list and contents
    ├─ Create/overwrite each file
    └─ Output: Updated file list for verification
    ↓
Complete! Code synced to Miaoda platform
```

### Trigger Scenarios

**Scenario 1: Direct Sync Command**
```
User says: "用秒哒更新代码" or "Sync code from GitHub"
    ↓
miaoda-app-chat-sync is triggered
    ↓
Generates JSON structured template
    ↓
Pass JSON to miaoda-app-builder for execution
```

**Scenario 2: Large Codebase - Batch Processing**
```
User says: "同步整个项目代码" or "Update entire project"
    ↓
miaoda-app-chat-sync detects large codebase (>50 files)
    ↓
Automatically splits into batches:
    ├─ Batch 1: Configuration files (*.json, *.yaml, *.toml)
    ├─ Batch 2: Frontend code (src/*.vue, src/*.js)
    └─ Batch 3: Backend code (api/*.py, models/*.py)
    ↓
Each batch sent to miaoda-app-builder sequentially
```

**Scenario 3: Incremental Update**
```
User says: "只更新改动的文件" or "Sync only changed files"
    ↓
miaoda-app-chat-sync uses diff command
    ├─ Compare commits to find changed files
    └─ Generate JSON for only modified files
    ↓
Send to miaoda-app-builder
```

---

# Structured JSON Template Format

## Standard Template

When `miaoda-app-chat-sync` processes code from GitHub, it generates the following JSON structure:

```json
{
  "action": "UPDATE_ALL_FILES",
  "description": "Please update all files in the project according to the following JSON data",
  "source": {
    "repository": "https://github.com/username/repo",
    "branch": "main",
    "commit": "abc123def456"
  },
  "rules": [
    "1. You must update every file in the files array",
    "2. File content must match the content field exactly - do not modify or alter any code",
    "3. Create file if it doesn't exist, completely overwrite if it exists",
    "4. Do not skip any file from the list",
    "5. Preserve the exact file structure and paths",
    "6. After updating, output a complete list of all updated files for verification"
  ],
  "files": [
    {
      "path": "package.json",
      "action": "CREATE_OR_OVERWRITE",
      "content": "{\n  \"name\": \"my-app\",\n  ...\n}"
    },
    {
      "path": "src/App.vue",
      "action": "CREATE_OR_OVERWRITE",
      "content": "<template>\n  ...\n</template>"
    }
  ]
}
```

## Template Components

| Field | Type | Description |
|-------|------|-------------|
| `action` | String | Always "UPDATE_ALL_FILES" |
| `description` | String | Human-readable instruction |
| `source` | Object | GitHub source information for traceability |
| `source.repository` | String | Repository URL |
| `source.branch` | String | Git branch name |
| `source.commit` | String | Commit hash (8 chars) |
| `rules` | Array | Execution rules that miaoda-app-builder must follow |
| `files` | Array | List of files to update |
| `files[].path` | String | Relative file path |
| `files[].action` | String | Always "CREATE_OR_OVERWRITE" |
| `files[].content` | String | Complete file content |

## Batch Template Example

For large projects, JSON is split into multiple batches:

**Batch 1: Configuration**
```json
{
  "action": "UPDATE_ALL_FILES",
  "batch": "1/3",
  "description": "Batch 1: Configuration files",
  "files": [
    {"path": "package.json", "action": "CREATE_OR_OVERWRITE", "content": "..."},
    {"path": "tsconfig.json", "action": "CREATE_OR_OVERWRITE", "content": "..."}
  ]
}
```

**Batch 2: Frontend**
```json
{
  "action": "UPDATE_ALL_FILES",
  "batch": "2/3",
  "description": "Batch 2: Frontend source code",
  "files": [
    {"path": "src/App.vue", "action": "CREATE_OR_OVERWRITE", "content": "..."},
    {"path": "src/components/Header.vue", "action": "CREATE_OR_OVERWRITE", "content": "..."}
  ]
}
```

---

# How to Trigger Code Sync

## User Commands

When users say any of the following, trigger `miaoda-app-chat-sync`:

### Chinese Commands
- "用秒哒更新代码"
- "同步 GitHub 代码"
- "从 GitHub 拉取代码"
- "更新项目代码"
- "同步整个项目"
- "只更新改动的文件"
- "批量同步代码"

### English Commands
- "Sync code from GitHub"
- "Update with latest code"
- "Pull code from GitHub"
- "Sync my repository"
- "Update entire project"
- "Sync only changed files"
- "Batch sync code"

## Execution Flow

### Step 1: User Provides Repository URL

```
User: "用秒哒更新代码，仓库地址是 https://github.com/user/repo"
    ↓
miaoda-app-chat-sync extracts:
  - repo_url: https://github.com/user/repo
  - app_id: (from current context)
  - context_id: (from current context)
```

### Step 2: Fetch and Generate JSON

```bash
# Execute sync command
python scripts/github_sync.py sync \
  --repo https://github.com/user/repo \
  --app-id <app_id> \
  --context-id <context_id>
```

Output: Structured JSON template

### Step 3: Send to miaoda-app-builder

```
User/Agent sends to miaoda-app-builder chat:

Please execute the following code update instructions:

```json
{
  "action": "UPDATE_ALL_FILES",
  "files": [...]
}
```

Important rules:
- Update every file in the files array
- Match content exactly as specified in content field
- Do not modify, alter, or skip any code
- Output complete list of all updated files when done
```

### Step 4: miaoda-app-builder Executes

```bash
# miaoda-app-builder processes via chat API
python scripts/miaoda_api.py chat \
  --text "<JSON instructions from Step 3>" \
  --app-id <app_id> \
  --context-id <context_id>
```

---

# Batch Processing Strategy

## Automatic Splitting

When codebase exceeds thresholds, `miaoda-app-chat-sync` automatically suggests batch processing:

### Split Criteria

| Condition | Action |
|-----------|--------|
| Files > 50 | Recommend splitting |
| Total size > 5MB | Recommend splitting |
| Mixed file types | Split by category |

### Recommended Batch Categories

**Priority 1: Configuration Files** (Must sync first)
```bash
python scripts/github_sync.py sync \
  --repo <repo_url> \
  --filter "*.json,*.yaml,*.yml,*.toml,*.env,package.json,requirements.txt" \
  --max-files 20 \
  --app-id <app_id> \
  --context-id <context_id> \
  --output batch1_config.json
```

**Priority 2: Frontend Code**
```bash
python scripts/github_sync.py sync \
  --repo <repo_url> \
  --filter "src/*.vue,src/*.js,src/*.jsx,src/*.ts,src/*.tsx,src/*.css,src/*.scss,src/*.html" \
  --max-files 30 \
  --app-id <app_id> \
  --context-id <context_id> \
  --output batch2_frontend.json
```

**Priority 3: Backend Code**
```bash
python scripts/github_sync.py sync \
  --repo <repo_url> \
  --filter "api/*.py,models/*.py,controllers/*.py,services/*.py,utils/*.py" \
  --max-files 30 \
  --app-id <app_id> \
  --context-id <context_id> \
  --output batch3_backend.json
```

**Priority 4: Documentation & Others**
```bash
python scripts/github_sync.py sync \
  --repo <repo_url> \
  --filter "*.md,*.txt,README*,docs/*" \
  --max-files 10 \
  --app-id <app_id> \
  --context-id <context_id> \
  --output batch4_docs.json
```

### Batch Execution Order

1. **Send Batch 1** to miaoda-app-builder
2. **Wait for completion** and verify file list
3. **Send Batch 2** to miaoda-app-builder
4. **Repeat** until all batches complete
5. **Final verification** - check all files synced

---

# Workflow Examples

## Example 1: Simple Sync (Public Repository)

```bash
# Step 1: Use miaoda-app-chat-sync to fetch code
export GITHUB_TOKEN="ghp_your_token"
python scripts/github_sync.py sync \
  --repo https://github.com/username/my-project \
  --app-id app-abc123xyz \
  --context-id conv-def456uvw

# Step 2: Copy the JSON output
# [Output contains structured JSON template]

# Step 3: Send JSON to miaoda-app-builder
python ../miaoda-app-builder/scripts/miaoda_api.py chat \
  --text 'Please execute the following code update instructions:

```json
{JSON_OUTPUT_FROM_STEP_1}
```

Rules:
- Update every file exactly as specified
- Do not modify any code
- Output complete list of updated files' \
  --app-id app-abc123xyz \
  --context-id conv-def456uvw
```

---

## Example 2: Large Project with Batches

```bash
# Batch 1: Configuration
python scripts/github_sync.py sync \
  --repo https://github.com/username/large-project \
  --filter "*.json,*.yaml,*.toml,*.env" \
  --max-files 20 \
  --app-id app-abc123xyz \
  --context-id conv-def456uvw \
  --output batch1.json

# Send to miaoda-app-builder
python ../miaoda-app-builder/scripts/miaoda_api.py chat \
  --text "Batch 1/3: Configuration files. $(cat batch1.json)" \
  --app-id app-abc123xyz \
  --context-id conv-def456uvw

# Wait for completion, then Batch 2: Frontend
python scripts/github_sync.py sync \
  --repo https://github.com/username/large-project \
  --filter "src/*.vue,src/*.js,src/*.css" \
  --max-files 30 \
  --app-id app-abc123xyz \
  --context-id conv-def456uvw \
  --output batch2.json

python ../miaoda-app-builder/scripts/miaoda_api.py chat \
  --text "Batch 2/3: Frontend code. $(cat batch2.json)" \
  --app-id app-abc123xyz \
  --context-id conv-def456uvw

# Batch 3: Backend
python scripts/github_sync.py sync \
  --repo https://github.com/username/large-project \
  --filter "api/*.py,models/*.py" \
  --max-files 30 \
  --app-id app-abc123xyz \
  --context-id conv-def456uvw \
  --output batch3.json

python ../miaoda-app-builder/scripts/miaoda_api.py chat \
  --text "Batch 3/3: Backend code. $(cat batch3.json)" \
  --app-id app-abc123xyz \
  --context-id conv-def456uvw
```

---

# Integration with miaoda-app-builder

## Chat Message Format

When sending JSON to miaoda-app-builder, use this format:

```
Please execute the following code update instructions:

```json
{
  "action": "UPDATE_ALL_FILES",
  "files": [...]
}
```

**CRITICAL RULES:**
1. ✅ You must update **every file** in the files array
2. ✅ File content must match the `content` field **exactly**
3. ✅ Do not modify, alter, optimize, or reformat any code
4. ✅ Create file if it doesn't exist, completely overwrite if it exists
5. ✅ Do not skip any file from the list
6. ✅ Preserve the exact file structure and paths
7. ✅ After updating, output a **complete list** of all updated files for verification

**Verification:**
After all files are updated, please output:
- Total number of files updated
- Complete list of all file paths
- Any files that failed to update (if any)
```

## Verification After Sync

After miaoda-app-builder completes:

1. **Check file count**: Compare with original JSON `files.length`
2. **Verify file list**: All paths should match
3. **Preview application**: `https://www.miaoda.cn/projects/{app_id}`
4. **Test functionality**: Run key features
5. **Publish if successful**: `python scripts/miaoda_api.py publish --app-id <id> --wait`

---

# Error Handling & Optimization

## Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| Files missing after sync | AI skipped some files | Use JSON template with strict rules |
| Code modified/altered | AI tried to "improve" code | Emphasize "DO NOT MODIFY" in rules |
| Sync incomplete | Too many files at once | Use batch processing |
| Token limit exceeded | JSON too large | Split into smaller batches |
| Private repo access denied | Missing token | Provide GITHUB_TOKEN |

## Optimization Strategies

### 1. Prioritize Critical Files
```bash
# Sync config files first (affects entire app)
--filter "package.json,requirements.txt,*.yaml,*.toml"
```

### 2. Use Commit Hashes for Reproducibility
```bash
# Pin to specific commit
--commit abc123def456
```

### 3. Exclude Unnecessary Files
```bash
# Only sync source code, skip docs/tests
--filter "src/*,api/*,models/*"
```

### 4. Parallel Batch Processing (Advanced)
For independent batches, you can prepare all JSON files first, then send sequentially:

```bash
# Prepare all batches
python scripts/github_sync.py sync --repo <url> --filter "*.json" --output batch1.json
python scripts/github_sync.py sync --repo <url> --filter "src/*.vue" --output batch2.json
python scripts/github_sync.py sync --repo <url> --filter "api/*.py" --output batch3.json

# Send to miaoda-app-builder one by one
# (Must wait for each to complete before sending next)
```

---

# Limitations & Workarounds

## Current Constraints

1. **File Limit**: Recommended <50 files per batch (AI processing limits)
2. **File Size**: Individual files >100KB may cause issues
3. **Binary Files**: Not supported (images, fonts, executables)
4. **No Direct Upload**: Must go through miaoda-app-builder chat API
5. **AI Accuracy**: ~90-95% with JSON instructions (vs 70-80% with natural language)

## Best Practices

✅ **DO:**
- Use structured JSON templates (this skill's output)
- Batch large projects by file type
- Verify file count after each sync
- Use specific commit hashes for reproducibility
- Sync configuration files first

❌ **DON'T:**
- Send >50 files in one batch
- Include binary files in sync
- Skip verification step
- Use natural language for code updates (use JSON instead)
- Modify JSON content before sending to miaoda-app-builder

---
