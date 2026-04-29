# Repo JSON Generator

> 🚀 Convert Git repository code to structured JSON instructions for AI agents

## 🎯 What This Tool Does

This command-line tool fetches code from Git repositories (GitHub, GitLab, etc.) and generates **structured JSON instructions** that you can send to any AI agent or automation tool for accurate code updates and processing.

**Key Features:**
- ✅ Fetch code from any Git repository (public or private)
- ✅ Support for specific commits and branches
- ✅ Generate JSON structured instructions for maximum AI accuracy
- ✅ File filtering and batching for large projects
- ✅ Platform-agnostic - works with any AI agent or system
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

### 2. Set Git Token (for private repos)

```bash
# For GitHub
export GITHUB_TOKEN="ghp_your_personal_access_token"

# For GitLab
export GITLAB_TOKEN="glpat_your_personal_access_token"
```

### 3. Generate JSON Instructions

```bash
python3 scripts/repo_json_generator.py sync \
  --repo https://github.com/username/my-project \
  --commit abc123def456
```

### 4. Use JSON Output with Your AI Agent

The script will output formatted JSON instructions. Copy the JSON block and send it to your AI agent or automation tool!

---

## 📖 Usage Examples

### Example 1: Generate JSON from Latest Code (Public Repository)

```bash
python3 scripts/repo_json_generator.py sync \
  --repo https://github.com/username/my-project
```

**Output:**
```
📦 Repo JSON Generator - Structured Update Instructions
═══════════════════════════════════════════════════════

📋 Summary:
  Repository: https://github.com/username/my-project
  Branch: main
  Commit: abc123def456
  Files: 45
  Total Size: 2.3 MB
  Generated: 2026-04-28 17:30:00

═══════════════════════════════════════════════════════

📝 Copy the following JSON and send to AI Agent:

```json
{
  "action": "CREATE_OR_UPDATE_FILES",
  "files": [...]
}
```
```

---

### Example 2: Generate JSON from Specific Commit

```bash
python3 scripts/repo_json_generator.py sync \
  --repo https://github.com/username/my-project \
  --commit abc123def456
```

---

### Example 3: Private Repository

```bash
export GITHUB_TOKEN="ghp_your_token"

python3 scripts/repo_json_generator.py sync \
  --repo https://github.com/username/private-repo
```

---

### Example 4: Filter Files

```bash
# Only generate JSON for Python and JavaScript files
python3 scripts/repo_json_generator.py sync \
  --repo https://github.com/username/my-project \
  --filter "*.py,*.js,*.html"
```

---

### Example 5: Large Project (Batch JSON Generation)

```bash
# Batch 1: Configuration files
python3 scripts/repo_json_generator.py sync \
  --repo https://github.com/username/my-project \
  --filter "*.json,*.yaml,*.toml" \
  --max-files 20 \
  --output batch1_config.json

# Batch 2: Frontend code
python3 scripts/repo_json_generator.py sync \
  --repo https://github.com/username/my-project \
  --filter "src/*.vue,src/*.js" \
  --max-files 30 \
  --output batch2_frontend.json

# Batch 3: Backend code
python3 scripts/repo_json_generator.py sync \
  --repo https://github.com/username/my-project \
  --filter "api/*.py" \
  --max-files 30 \
  --output batch3_backend.json
```

Then send each batch JSON to your AI agent separately.

---

### Example 6: Save JSON to File

```bash
python3 scripts/repo_json_generator.py sync \
  --repo https://github.com/username/my-project \
  --output update_instructions.json
```

---

### Example 7: View Repository Info

```bash
# Get latest commit info from default branch
python3 scripts/repo_json_generator.py info \
  --repo https://github.com/username/my-project

# Get specific commit information
python3 scripts/repo_json_generator.py info \
  --repo https://github.com/username/my-project \
  --commit abc123def456

# Get info from specific branch
python3 scripts/repo_json_generator.py info \
  --repo https://github.com/username/my-project \
  --branch develop

# Get full changes of a commit (including file diffs and complete file content)
python3 scripts/repo_json_generator.py info \
  --repo https://github.com/username/my-project \
  --commit dbc95d3f5c708709e83b2ae3bd1a1354fb4d43b1 \
  --output commit_changes.json

# Get full changes in pure JSON format (terminal still shows summary)
python3 scripts/repo_json_generator.py info \
  --repo https://github.com/username/my-project \
  --commit abc123def456 \
  --output changes.json \
  --no-instructions
```

**Parameters:**
- `--repo`: GitHub repository URL (required)
- `--branch`: Branch name (default: main, used when --commit is not specified)
- `--commit`: Specific commit hash (optional, overrides branch)
- `--output`: Save output to file instead of printing to terminal
- `--no-instructions`: Output only pure JSON without formatted instruction text

**Output Behavior:**
- **All scenarios**: Terminal always displays summary (file count, additions, deletions, file list)
- **With `--output`**: Saves full formatted output to file, terminal shows summary
- **With `--output` + `--no-instructions`**: Saves pure JSON to file, terminal shows summary
- **Without `--output`**: Terminal shows summary only, no file saved

---

## 📊 Complete Workflow

```
1. Local Development
   ↓
   git push origin main

2. Generate JSON Instructions
   ↓
   python3 scripts/repo_json_generator.py sync \
     --repo https://github.com/user/repo \
     --commit abc123

3. Copy JSON Output
   ↓
   (Copy the JSON block from output)

4. Send to AI Agent
   ↓
   (Paste JSON as message to your AI agent/automation tool)

5. AI Agent Processes Files
   ↓
   (Wait for completion)

6. Verify Results
   ↓
   Check that all files were updated correctly

7. Deploy/Publish (if ready)
   ↓
   Follow your deployment process
```

---

## 🔧 Command Reference

### sync Command

Fetch code and generate structured JSON instructions.

```bash
python3 scripts/repo_json_generator.py sync [options]
```

**Required:**
- `--repo REPO_URL`: Git repository URL

**Optional:**
- `--branch BRANCH`: Git branch (default: main)
- `--commit COMMIT`: Specific commit hash (overrides branch)
- `--token TOKEN`: Git token (or use GITHUB_TOKEN env)
- `--max-files N`: Max files to sync (default: 50)
- `--filter PATTERN`: File filter (e.g., "*.py,*.js")
- `--output FILE`: Save to file
- `--no-instructions`: Output only JSON

---

### info Command

Get detailed commit information with full file content and changes.

```bash
python3 scripts/repo_json_generator.py info [options]
```

**Required:**
- `--repo REPO_URL`: Git repository URL

**Optional:**
- `--branch BRANCH`: Branch name (default: main, used when --commit is not specified)
- `--commit COMMIT`: Specific commit hash (optional, overrides branch)
- `--output FILE`: Save output to file
- `--no-instructions`: Output only pure JSON without formatted text

**Output Behavior:**
- Terminal always displays summary information (file count, additions, deletions, file list)
- With `--output`: saves full formatted output (summary + JSON) to file
- With `--output` + `--no-instructions`: saves pure JSON to file
- Without `--output`: terminal shows summary only, no file saved

**Examples:**
```bash
# Get latest commit from default branch
python3 scripts/repo_json_generator.py info --repo https://github.com/user/repo

# Get specific commit information
python3 scripts/repo_json_generator.py info --repo https://github.com/user/repo --commit abc123

# Get full changes with complete file content (saves to file)
python3 scripts/repo_json_generator.py info --repo https://github.com/user/repo --commit abc123 --output changes.json

# Get full changes in pure JSON format (terminal still shows summary)
python3 scripts/repo_json_generator.py info --repo https://github.com/user/repo --commit abc123 --output changes.json --no-instructions
```

**JSON Output Structure:**
```json
{
  "action": "CREATE_OR_UPDATE_FILES",
  "description": "...",
  "source": {
    "repository": "...",
    "branch": "...",
    "commit": "..."
  },
  "summary": {
    "files_changed": 3,
    "total_additions": 131,
    "total_deletions": 98,
    "files": [
      {
        "path": "src/file.ts",
        "status": "modified",
        "additions": 10,
        "deletions": 5
      }
    ]
  },
  "rules": [...],
  "files": [
    {
      "path": "src/file.ts",
      "status": "modified",
      "additions": 10,
      "deletions": 5,
      "changes": [
        { "type": "deletion", "line": 10, "content": "..." },
        { "type": "addition", "line": 10, "content": "..." }
      ],
      "content": "// Complete file content..."
    }
  ]
}
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
python3 scripts/repo_json_generator.py sync \
  --repo https://github.com/user/repo \
  --commit abc123 \
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
repo-json-generator/
├── README.md                   # This file
├── SKILL.md                    # Skill description (for OpenClaw)
├── _meta.json                  # Metadata
├── scripts/
│   └── repo_json_generator.py  # Core generation script
├── requirements.txt            # Dependencies (none!)
└── .gitignore                  # Git ignore rules
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

A versatile tool for generating structured code instructions for AI agents and automation systems.

---

**Last Updated**: 2026-04-29  
**Version**: 2.4.0
