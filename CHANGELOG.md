# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
