# Changelog

All notable changes to the `generator` project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [3.2.0] - 2026-04-30

### Added
- **Mandatory `--branch` parameter**: Both `sync` and `info` commands now require explicit branch specification
  - Removed automatic branch detection logic
  - Ensures explicit and predictable branch selection
  - Better clarity in command usage

### Changed
- **Separated `sync` and `info` command behaviors**:
  - **`sync` command**: Retrieves complete file content for changed files (for code synchronization)
    - Uses `get_commit_full_changes()` method
    - Returns full file content with `CREATE_OR_OVERWRITE` action
    - Output includes file size in characters
  - **`info` command**: Retrieves diff statistics for changed files (for change overview)
    - Uses new `get_commit_diff_changes()` method
    - Returns additions/deletions statistics per file
    - Terminal output shows `+additions/-deletions` format
    - Displays file status icons (🆕 for added, 📝 for modified)

### Fixed
- **Info command regression**: Restored original `info` command output format with diff statistics
- **Data structure separation**: Each command now uses appropriate data structure for its purpose

---

## [3.1.0] - 2026-04-29

### Changed
- **Improved `sync` command logic**: Changed from getting all files to getting only changed files with full content
  - Now retrieves complete file content for files **changed in the specific commit** (not all files)
  - Uses `git diff --name-status` to identify changed files, then reads their full content
  - Supports initial commits with `--root` parameter
  - Simplified and more reliable file extraction logic
- **Enhanced binary file handling**: Automatic detection and skipping of binary files
  - Detects binary files by checking for null bytes in file header
  - Gracefully skips non-UTF-8 encoded files
  - Provides clear feedback on skipped files count

### Fixed
- **Initial commit support**: Added `--root` flag for diffing initial commits (no parent commit)
- **Binary file errors**: Eliminated UTF-8 decode errors for image files and other binary assets
- **File scope**: Fixed issue where all repository files were returned instead of only changed files

---

## [3.0.0] - 2026-04-29

### Added
- **Modular architecture**: Restructured codebase from monolithic script into modular components
  - `core/`: Shared constants, temp directory management, circuit breaker, security
  - `git/`: Git repository operations
  - `processors/`: File reading, filtering, and instruction generation
  - `output/`: Streaming/chunked output support
- **Enhanced `info` command**: Now includes complete file content in JSON output
- **File filtering support**: `--filter` (whitelist) and `--exclude` (blacklist) parameters for `info` command
- **Unified `--no-instructions` parameter**: Consistent behavior across all commands
- **Consistent terminal output**: Terminal always shows summary information regardless of output options
- **Flexible file output**: 
  - With `--output`: Saves full formatted output (summary + JSON)
  - With `--output --no-instructions`: Saves pure JSON only

### Changed
- **Improved maintainability**: Each module can be updated and tested independently
- **Better code organization**: Smaller, focused files are easier to understand
- **Enhanced reusability**: Core components can be reused in other projects

---

## [2.0.0] - 2026-04-28

### Added
- **Cross-platform temp directory support**: Works on Windows/macOS/Linux
- **Circuit breaker mechanism**: Resilient operations with retry logic
- **Streaming/chunked output**: Support for large repositories
- **Automatic cleanup**: Temporary files are automatically removed after execution
- **Sensitive information protection**: Tokens and credentials are securely handled
- **App ID auto-extraction**: Automatically extracts App ID from repository URL
  - Example: `https://github.com/xiaoanso/app-9wublrxntfr5.git` → `app-9wublrxntfr5`

### Changed
- **Improved batch processing**: Automatic splitting by file type and size
- **Enhanced error handling**: Better error messages and recovery mechanisms

---

## [1.0.0] - 2026-04-27

### Added
- Initial release of `generator`
- **Core functionality**: Convert Git repository code to structured JSON instructions
- **CLI commands**:
  - `sync`: Generate JSON instructions for code synchronization
  - `info`: Get commit information and changed files
- **File filtering**: Support for `--filter` and `--exclude` patterns
- **Batch processing**: Automatic splitting for large projects (>50 files)
- **Structured JSON output**: AI-agent-friendly format with strict execution rules
- **GitHub integration**: Support for public and private repositories
- **Commit-based sync**: Pin to specific commit for reproducibility
- **Comprehensive documentation**: SKILL.md with integration guides and examples
