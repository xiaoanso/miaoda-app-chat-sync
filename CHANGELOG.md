# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.3.0] - 2026-04-29

### Changed
- **BREAKING**: Refactored `info --full` command output format to file-based structure
  - Changed from raw unified diff to structured file-level changes
  - Each file now includes: path, status (added/modified/deleted), additions, deletions, and changes array
  - Changes are organized by type (addition/deletion) with line numbers
  - Consecutive changes of the same type are automatically merged
  - Output format matches `CREATE_OR_UPDATE_FILES` action template
  
**New JSON Structure:**
```json
{
  "action": "CREATE_OR_UPDATE_FILES",
  "description": "...",
  "source": { "repository": "...", "branch": "...", "commit": "..." },
  "rules": [...],
  "files": [
    {
      "path": "src/file.ts",
      "status": "modified",
      "additions": 2,
      "deletions": 1,
      "changes": [
        { "type": "deletion", "line": 10, "content": "..." },
        { "type": "addition", "line": 10, "content": "..." }
      ]
    }
  ]
}
```

## [2.2.0] - 2026-04-29

### Added
- **New**: Added `--full` parameter to `info` command to get complete commit changes including file diffs
  - New method `get_commit_full_changes()` in `RepoJSONGenerator` class
  - New method `generate_commit_full_changes()` in `InstructionGenerator` class
  - Outputs structured JSON with commit info, changed files list, and unified diffs
  - Supports saving to file with `--output` parameter
  - Supports JSON-only output with `--json-only` parameter

**Usage Example:**
```bash
# Get full changes of a specific commit
python3 scripts/repo_json_generator.py info \
  --repo https://github.com/username/repo \
  --commit dbc95d3f5c708709e83b2ae3bd1a1354fb4d43b1 \
  --full \
  --output commit_changes.json
```

## [2.1.0] - 2026-04-29

### Removed
- **BREAKING**: Removed `diff` command and all related functionality
  - Removed `cmd_diff` function from codebase
  - Removed diff-related methods from `RepoJSONGenerator` class (`get_commit_diff`, `_parse_diff`, `_parse_diff_stats`, `_filter_diff_files`)
  - Removed diff-related methods from `InstructionGenerator` class (`generate_diff_output`, `_merge_consecutive_changes`)
  - Removed diff command from CLI parser and help documentation
  - Removed diff command examples from README.md and SKILL.md
  - Updated documentation to reflect removal of diff functionality
  
**Reason**: The diff command was not providing significant value for code synchronization workflows

## [2.0.0] - 2026-04-29

### Changed
- **BREAKING**: Renamed project from "GitHub Code Sync" to "Repo JSON Generator"
- Updated all documentation to reflect platform-agnostic design
- Modified script descriptions to emphasize JSON generation for AI agents
- Removed Miaoda-specific references, now works with any AI agent or automation system
- Updated CLI help text and examples

### Added
- Support for multiple Git platforms (GitHub, GitLab, Bitbucket, etc.)
- Generic AI agent integration patterns
- Platform-independent workflow examples

## [1.1.0] - 2026-04-28

### Added
- Enhanced file filtering capabilities
- Improved batch processing for large repositories
- Structured JSON instruction generation

### Fixed
- Fixed temporary directory cleanup issues
- Improved error handling for private repositories

## [1.0.1] - 2026-04-28

### Fixed
- 修复已知问题，提升系统稳定性

### Changed
- 优化代码同步逻辑
- 改进错误处理机制

## [1.0.0] - 2026-03-17

### Added
- Initial release of GitHub Code Sync Skill
- Support for public and private repositories
- Structured JSON instruction generation
- File filtering and batching capabilities
- Commit and branch selection support
- Repository info and diff commands
