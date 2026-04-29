#!/usr/bin/env python3
"""
Repo JSON Generator - Git Repository to Structured JSON Converter

Fetches code from Git repositories and generates structured JSON instructions
for accurate code updates via AI agents and automation tools.

## Temporary Clone Locations

- **sync**: `/tmp/github-sync-<repo-name>/` (auto-cleaned after execution)
- **info**: `/tmp/github-info-<random>/` (auto-deleted)
- **diff**: `/tmp/github-diff-<random>/` (auto-deleted)

All directories are automatically removed after script completion.

Usage:
    python3 repo_json_generator.py sync --repo URL --commit COMMIT [options]
    python3 repo_json_generator.py diff --repo URL --from-commit COMMIT --to-commit COMMIT [options]
    python3 repo_json_generator.py info --repo URL [--commit COMMIT] [options]
    
Note:
    App ID is automatically extracted from repository URL if not provided.
    Example: https://github.com/xiaoanso/app-9wublrxntfr5.git -> app-9wublrxntfr5
"""

import argparse
import json
import os
import subprocess
import tempfile
import shutil
import sys
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Supported text file extensions
TEXT_EXTENSIONS = {
    '.py', '.js', '.jsx', '.ts', '.tsx',
    '.html', '.css', '.scss', '.less',
    '.json', '.yaml', '.yml', '.toml',
    '.md', '.txt', '.sh', '.bash',
    '.xml', '.sql', '.env',
    '.vue', '.svelte', '.rst',
}

# Directories to skip during processing
SKIP_DIRS = {
    '.git', 'node_modules', '__pycache__', 
    '.venv', 'venv', 'dist', 'build',
    '.next', '.nuxt', 'target',
    '.DS_Store', 'thumbs.db',
}

MAX_SINGLE_FILE_SIZE = 100 * 1024 * 1024  # 100MB


# ---------------------------------------------------------------------------
# Git Repository Operations
# ---------------------------------------------------------------------------

class GitHubSync:
    """Handles Git repository operations (GitHub, GitLab, etc.)
    
    Clone target directory is specified by caller (e.g., /tmp/github-sync-<repo-name>/).
    Caller is responsible for cleanup after use.
    """
    
    def __init__(self, token: str = None):
        self.token = token or os.environ.get('GITHUB_TOKEN')
    
    def _get_git_env(self) -> Dict[str, str]:
        """Get environment variables for git commands with authentication"""
        env = os.environ.copy()
        if self.token:
            env['GIT_ASKPASS'] = 'echo'
            env['GIT_TERMINAL_PROMPT'] = '0'
        return env
    
    def _make_authenticated_url(self, repo_url: str) -> str:
        """Convert repo URL to use authentication if token is provided"""
        if not self.token or 'github.com' not in repo_url:
            return repo_url
        
        # Remove .git suffix for consistency
        repo_url = repo_url.rstrip('/')
        if repo_url.endswith('.git'):
            repo_url = repo_url[:-4]
        
        if '@' in repo_url and '://' in repo_url:
            parts = repo_url.split('://')
            return f"{parts[0]}://{self.token}@{parts[1].split('@')[1]}"
        
        if repo_url.startswith('https://'):
            return repo_url.replace('https://', f'https://{self.token}@')
        elif repo_url.startswith('http://'):
            return repo_url.replace('http://', f'https://{self.token}@')
        return repo_url
    
    def clone_repo(self, repo_url: str, target_dir: str, 
                   branch: str = 'main', commit: str = None) -> str:
        """
        Clone repository and optionally checkout specific commit.
        Uses full history fetch to support any commit checkout.
        """
        try:
            auth_url = self._make_authenticated_url(repo_url)
            env = self._get_git_env()
            
            # Step 1: Initialize git repo
            subprocess.run(['git', 'init'], cwd=target_dir, capture_output=True, timeout=30)
            
            # Step 2: Configure git user (required for operations)
            subprocess.run(['git', 'config', 'user.email', 'sync@github.com'], 
                          cwd=target_dir, capture_output=True, timeout=10)
            subprocess.run(['git', 'config', 'user.name', 'GitHub Sync'], 
                          cwd=target_dir, capture_output=True, timeout=10)
            
            # Step 3: Add remote
            subprocess.run(['git', 'remote', 'add', 'origin', auth_url], 
                          cwd=target_dir, capture_output=True, timeout=30)
            
            # Step 4: Fetch
            if commit:
                # Fetch specific commit - need full history
                print(f"   📥 Fetching commit {commit[:8]}...")
                cmd = ['git', '-C', target_dir, 'fetch', '--tags', 'origin', commit]
                result = subprocess.run(cmd, capture_output=True, text=True, 
                                       timeout=180, env=env)
                if result.returncode != 0:
                    # Try as branch first
                    cmd = ['git', '-C', target_dir, 'fetch', 'origin', commit]
                    result = subprocess.run(cmd, capture_output=True, text=True, 
                                          timeout=180, env=env)
                    if result.returncode != 0:
                        raise Exception(f"Failed to fetch commit {commit}: {result.stderr}")
                
                # Checkout the commit
                cmd = ['git', '-C', target_dir, 'checkout', commit]
                result = subprocess.run(cmd, capture_output=True, text=True, 
                                       timeout=60, env=env)
                if result.returncode != 0:
                    raise Exception(f"Failed to checkout commit {commit}: {result.stderr}")
                
                actual_commit = commit
            else:
                # Fetch branch
                print(f"   📥 Fetching branch {branch}...")
                cmd = ['git', '-C', target_dir, 'fetch', 'origin', branch]
                result = subprocess.run(cmd, capture_output=True, text=True, 
                                       timeout=180, env=env)
                if result.returncode != 0:
                    raise Exception(f"Failed to fetch branch {branch}: {result.stderr}")
                
                # Checkout
                cmd = ['git', '-C', target_dir, 'checkout', '-f', '-B', branch, 
                      f'origin/{branch}']
                result = subprocess.run(cmd, capture_output=True, text=True, 
                                       timeout=60, env=env)
                if result.returncode != 0:
                    raise Exception(f"Failed to checkout branch {branch}: {result.stderr}")
                
                # Get actual commit
                cmd = ['git', '-C', target_dir, 'rev-parse', 'HEAD']
                result = subprocess.run(cmd, capture_output=True, text=True, 
                                       timeout=10, env=env)
                actual_commit = result.stdout.strip() if result.returncode == 0 else None
            
            # Verify the commit
            if actual_commit:
                cmd = ['git', '-C', target_dir, 'cat-file', '-t', actual_commit]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if result.returncode != 0:
                    raise Exception(f"Invalid commit hash: {actual_commit}")
            
            return actual_commit
            
        except subprocess.TimeoutExpired:
            raise Exception("Git operation timed out. Check network connection.")
        except Exception as e:
            raise Exception(f"Git operation failed: {str(e)}")
    
    def get_repo_info(self, repo_url: str, commit: str = None, branch: str = 'main') -> Dict:
        """
        Get detailed commit/repository information.
        
        Returns:
            {
                "action": "COMMIT_INFO",
                "repository": "...",
                "commit": {
                    "hash": "...",
                    "short_hash": "...",
                    "message": {"subject": "...", "body": "..."},
                    "author": {"name": "...", "email": "...", "timestamp": "..."},
                    "committer": {"name": "...", "email": "...", "timestamp": "..."},
                    "parent_commits": [...],
                    "is_merge_commit": bool
                },
                "branch": "..."
            }
        """
        temp_dir = tempfile.mkdtemp(prefix='github-info-')
        try:
            if commit:
                self.clone_repo(repo_url, temp_dir, branch, commit)
                target_ref = commit
            else:
                self.clone_repo(repo_url, temp_dir, branch)
                target_ref = 'HEAD'
            
            env = self._get_git_env()
            
            # Get detailed commit info
            # %H = full hash, %h = short hash, %s = subject, %b = body
            # %an = author name, %ae = author email, %aI = author ISO date
            # %cn = committer name, %ce = committer email, %cI = committer ISO date
            # %P = parent hashes (space separated)
            format_str = '%H||%h||%s||%b||%an||%ae||%aI||%cn||%ce||%cI||%P'
            cmd = ['git', '-C', temp_dir, 'log', '-1', f'--format={format_str}', target_ref]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, env=env)
            
            if result.returncode != 0:
                raise Exception(f"Failed to get commit info: {result.stderr}")
            
            lines = result.stdout.strip().split('||')
            if len(lines) < 11:
                raise Exception("Invalid git log output format")
            
            (commit_hash, short_hash, subject, body, 
             author_name, author_email, author_date,
             committer_name, committer_email, committer_date, 
             parents) = lines
            
            parent_list = parents.split() if parents else []
            
            return {
                'action': 'COMMIT_INFO',
                'repository': repo_url,
                'commit': {
                    'hash': commit_hash,
                    'short_hash': short_hash,
                    'message': {
                        'subject': subject,
                        'body': body or ''
                    },
                    'author': {
                        'name': author_name,
                        'email': author_email,
                        'timestamp': author_date
                    },
                    'committer': {
                        'name': committer_name,
                        'email': committer_email,
                        'timestamp': committer_date
                    },
                    'parent_commits': parent_list,
                    'is_merge_commit': len(parent_list) > 1
                },
                'branch': branch
            }
                
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def get_commit_diff(self, repo_url: str, from_commit: str, 
                       to_commit: str = 'HEAD', file_filter: str = None, 
                       exclude_filter: str = None, max_files: int = 50) -> Dict:
        """
        Get detailed diff between two commits with line numbers and code changes.
        
        Args:
            repo_url: GitHub repository URL
            from_commit: Base commit hash
            to_commit: Target commit (default: HEAD)
            file_filter: File pattern filter to include
            exclude_filter: File pattern filter to exclude
            max_files: Maximum number of files to include
            
        Returns:
            {
                "action": "SHOW_DIFF",
                "repository": "...",
                "base_commit": "...",
                "target_commit": "...",
                "summary": {"files_changed": N, "total_additions": N, "total_deletions": N},
                "files": [
                    {
                        "path": "...",
                        "status": "added|modified|deleted",
                        "additions": N,
                        "deletions": N,
                        "hunks": [
                            {
                                "old_start": N,
                                "old_lines": N,
                                "new_start": N,
                                "new_lines": N,
                                "changes": [
                                    {"type": "context|deletion|addition", "old_line": N, "new_line": N, "content": "..."}
                                ]
                            }
                        ]
                    }
                ]
            }
        """
        temp_dir = tempfile.mkdtemp(prefix='github-diff-')
        try:
            # Clone the repo
            self.clone_repo(repo_url, temp_dir)
            env = self._get_git_env()
            
            print(f"   📥 Fetching commits {from_commit[:8]}..{to_commit[:8]}...")
            
            # Get unified diff
            cmd = ['git', '-C', temp_dir, 'diff', '--unified=3', from_commit, to_commit]
            result = subprocess.run(cmd, capture_output=True, text=True, 
                                   timeout=120, env=env)
            
            raw_diff = result.stdout if result.returncode == 0 else ''
            
            # Parse the diff into structured format
            diff_data = self._parse_diff(raw_diff)
            
            # Apply file filtering if filters are specified
            if file_filter or exclude_filter:
                processor = FileProcessor(max_files=max_files, file_filter=file_filter, exclude_filter=exclude_filter)
                diff_data = self._filter_diff_files(diff_data, processor)
            
            # Get summary statistics
            cmd = ['git', '-C', temp_dir, 'diff', '--stat', '--shortstat', from_commit, to_commit]
            result = subprocess.run(cmd, capture_output=True, text=True, 
                                   timeout=30, env=env)
            
            stats = self._parse_diff_stats(result.stdout)
            
            return {
                'action': 'SHOW_DIFF',
                'repository': repo_url,
                'base_commit': from_commit,
                'base_commit_short': from_commit[:8] if from_commit else None,
                'target_commit': to_commit,
                'target_commit_short': to_commit[:8] if to_commit else None,
                'summary': stats,
                'files': diff_data
            }
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def _filter_diff_files(self, diff_data: List[Dict], processor: FileProcessor) -> List[Dict]:
        """
        Filter diff files based on include/exclude patterns
        
        Args:
            diff_data: List of file diff data
            processor: FileProcessor instance with filter configuration
            
        Returns:
            Filtered list of file diff data
        """
        filtered_files = []
        
        for file_diff in diff_data:
            filepath = file_diff.get('path', '')
            
            # Check if file should be included
            if processor._should_include_file(filepath):
                filtered_files.append(file_diff)
            
            # Check if we've reached the max files limit
            if len(filtered_files) >= processor.max_files:
                break
        
        return filtered_files
    
    def _parse_diff_stats(self, stat_output: str) -> Dict:
        """Parse git diff --stat --shortstat output"""
        stats = {
            'files_changed': 0,
            'total_additions': 0,
            'total_deletions': 0
        }
        
        for line in stat_output.strip().split('\n'):
            # Match "N files changed, X insertions(+), Y deletions(-)"
            match = re.search(r'(\d+) files changed', line)
            if match:
                stats['files_changed'] = int(match.group(1))
            
            match = re.search(r'(\d+) insertions?\(\+\)', line)
            if match:
                stats['total_additions'] = int(match.group(1))
            
            match = re.search(r'(\d+) deletions?\(\-\)', line)
            if match:
                stats['total_deletions'] = int(match.group(1))
        
        return stats
    
    def _parse_diff(self, raw_diff: str) -> List[Dict]:
        """
        Parse unified diff format into structured data.
        
        Format:
        diff --git a/src/main.py b/src/main.py
        index 1234567..89abcdef 100644
        --- a/src/main.py
        +++ b/src/main.py
        @@ -10,7 +10,9 @@ function name
        -old line
        +new line
         context line
        """
        files = []
        current_file = None
        current_hunk = None
        old_line = None
        new_line = None
        
        for line in raw_diff.split('\n'):
            if line.startswith('diff --git'):
                # Save previous file
                if current_file:
                    if current_hunk:
                        current_file['hunks'].append(current_hunk)
                    files.append(current_file)
                
                # Parse new file path
                # Format: diff --git a/path b/path
                parts = line.split(' b/')
                if len(parts) == 2:
                    current_file = {
                        'path': parts[1],
                        'status': 'modified',
                        'additions': 0,
                        'deletions': 0,
                        'hunks': []
                    }
                    current_hunk = None
                    
            elif line.startswith('new file mode'):
                if current_file:
                    current_file['status'] = 'added'
                    
            elif line.startswith('deleted file mode'):
                if current_file:
                    current_file['status'] = 'deleted'
                    
            elif line.startswith('--- '):
                # File deletion indicator
                if current_file and current_file['status'] != 'deleted':
                    # Will be confirmed by status line or final determination
                    pass
                    
            elif line.startswith('+++ '):
                pass
                
            elif line.startswith('@@'):
                # New hunk starts
                # Parse @@ -old_start,old_lines +new_start,new_lines @@
                match = re.search(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', line)
                if match:
                    if current_hunk and current_file:
                        current_file['hunks'].append(current_hunk)
                    
                    old_start = int(match.group(1))
                    old_lines = int(match.group(2)) if match.group(2) else 1
                    new_start = int(match.group(3))
                    new_lines = int(match.group(4)) if match.group(4) else 1
                    
                    current_hunk = {
                        'old_start': old_start,
                        'old_lines': old_lines,
                        'new_start': new_start,
                        'new_lines': new_lines,
                        'changes': []
                    }
                    old_line = old_start
                    new_line = new_start
                    
            elif current_hunk and current_file:
                if line.startswith('+') and not line.startswith('+++'):
                    current_hunk['changes'].append({
                        'type': 'addition',
                        'old_line': None,
                        'new_line': new_line,
                        'content': line[1:]
                    })
                    current_file['additions'] += 1
                    new_line += 1
                    
                elif line.startswith('-') and not line.startswith('---'):
                    current_hunk['changes'].append({
                        'type': 'deletion',
                        'old_line': old_line,
                        'new_line': None,
                        'content': line[1:]
                    })
                    current_file['deletions'] += 1
                    old_line += 1
                    
                elif line.startswith(' ') or line == '':
                    current_hunk['changes'].append({
                        'type': 'context',
                        'old_line': old_line,
                        'new_line': new_line,
                        'content': line[1:] if line else ''
                    })
                    old_line += 1
                    new_line += 1
                    
                elif line.startswith('\\'):
                    # Git diff tell us something (e.g., \ No newline at end of file)
                    if current_hunk['changes']:
                        current_hunk['changes'][-1]['trailing_newline_warning'] = line
        
        # Don't forget the last file/hunk
        if current_hunk and current_file:
            current_file['hunks'].append(current_hunk)
        if current_file:
            files.append(current_file)
        
        return files
    
    def get_commit_changed_files(self, repo_dir: str, commit: str) -> List[Tuple[str, str]]:
        """
        Get list of changed files for a specific commit.
        
        Returns:
            List of tuples (status, filepath) where status is:
            'A' = added, 'M' = modified, 'D' = deleted, 'R' = renamed
        """
        try:
            env = self._get_git_env()
            
            cmd = ['git', '-C', repo_dir, 'show', '--name-status', '--format=', commit]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, env=env)
            
            if result.returncode != 0:
                raise Exception(f"git show failed: {result.stderr}")
            
            changed_files = []
            lines = result.stdout.strip().split('\n')
            
            for line in lines:
                if not line:
                    continue
                parts = line.split('\t')
                if len(parts) == 2:
                    status = parts[0].strip()
                    filepath = parts[1].strip()
                    changed_files.append((status, filepath))
            
            return changed_files
            
        except subprocess.TimeoutExpired:
            raise Exception("git show operation timed out")
        except Exception as e:
            raise Exception(f"Failed to get changed files: {str(e)}")


# ---------------------------------------------------------------------------
# File Reading & Processing
# ---------------------------------------------------------------------------

class FileProcessor:
    """Handles file reading and processing"""
    
    def __init__(self, max_files: int = 50, file_filter: str = None, exclude_filter: str = None):
        self.max_files = max_files
        self.file_filter = self._parse_filter(file_filter) if file_filter else None
        self.exclude_filter = self._parse_filter(exclude_filter) if exclude_filter else None
    
    def _parse_filter(self, filter_str: str) -> List[str]:
        """Parse file filter string"""
        return [f.strip() for f in filter_str.split(',')]
    
    def _matches_filter(self, filepath: str) -> bool:
        """Check if file matches the include filter"""
        if not self.file_filter:
            return True
        
        for pattern in self.file_filter:
            if pattern.startswith('*.'):
                ext = '.' + pattern[2:]
                if filepath.endswith(ext):
                    return True
            elif '*' in pattern:
                import fnmatch
                if fnmatch.fnmatch(filepath, pattern):
                    return True
            else:
                if filepath == pattern:
                    return True
        return False
    
    def _matches_exclude(self, filepath: str) -> bool:
        """Check if file matches the exclude filter"""
        if not self.exclude_filter:
            return False
        
        for pattern in self.exclude_filter:
            if pattern.startswith('*.'):
                ext = '.' + pattern[2:]
                if filepath.endswith(ext):
                    return True
            elif '*' in pattern:
                import fnmatch
                if fnmatch.fnmatch(filepath, pattern):
                    return True
            else:
                if filepath == pattern:
                    return True
        return False
    
    def _should_include_file(self, filepath: str) -> bool:
        """Check if file should be included (matches filter AND not excluded)"""
        # First check if it matches the include filter
        if not self._matches_filter(filepath):
            return False
        
        # Then check if it matches the exclude filter
        if self._matches_exclude(filepath):
            return False
        
        return True
    
    def read_files(self, directory: str) -> Dict[str, str]:
        """Read all text files from directory"""
        files_content = {}
        
        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            
            for file in sorted(files):
                filepath = os.path.join(root, file)
                relpath = os.path.relpath(filepath, directory)
                
                if not self._should_include_file(relpath):
                    continue
                
                ext = os.path.splitext(file)[1].lower()
                if ext not in TEXT_EXTENSIONS:
                    continue
                
                try:
                    file_size = os.path.getsize(filepath)
                    if file_size > MAX_SINGLE_FILE_SIZE:
                        continue
                except:
                    continue
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        files_content[relpath] = f.read()
                        
                    if len(files_content) >= self.max_files:
                        break
                except:
                    continue
            
            if len(files_content) >= self.max_files:
                break
        
        return files_content
    
    def read_changed_files(self, directory: str, 
                           changed_files: List[Tuple[str, str]]) -> Dict[str, str]:
        """Read only the changed files from the repository"""
        files_content = {}
        
        for status, filepath in changed_files:
            # Skip deleted files
            if status == 'D':
                print(f"   ⏭️  Skipping deleted file: {filepath}")
                continue
            
            if not self._should_include_file(filepath):
                continue
            
            ext = os.path.splitext(filepath)[1].lower()
            if ext not in TEXT_EXTENSIONS:
                continue
            
            full_path = os.path.join(directory, filepath)
            if not os.path.exists(full_path):
                print(f"   ⚠️  File not found: {filepath}")
                continue
            
            try:
                file_size = os.path.getsize(full_path)
                if file_size > MAX_SINGLE_FILE_SIZE:
                    continue
            except:
                continue
            
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    files_content[filepath] = f.read()
                status_icon = {'A': '🆕', 'M': '📝', 'D': '🗑️', 'R': '🔄'}.get(status, '❓')
                print(f"   ✅ {status_icon} {filepath}")
            except Exception as e:
                print(f"   ⚠️  Error reading {filepath}: {str(e)}")
        
        return files_content
    
    def get_stats(self, files_content: Dict[str, str]) -> Dict:
        """Get file statistics"""
        total_size = sum(len(content.encode('utf-8')) for content in files_content.values())
        
        by_ext = {}
        for filepath in files_content.keys():
            ext = os.path.splitext(filepath)[1].lower()
            by_ext[ext] = by_ext.get(ext, 0) + 1
        
        return {
            'file_count': len(files_content),
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'by_extension': by_ext
        }


# ---------------------------------------------------------------------------
# JSON Instruction Generator
# ---------------------------------------------------------------------------

class InstructionGenerator:
    """Generates structured JSON instructions for Miaoda"""
    
    @staticmethod
    def generate(files_content: Dict[str, str], 
                 repo_url: str, branch: str, commit: str,
                 stats: Dict) -> str:
        """Generate JSON structured instruction for file sync"""
        priority_files = [
            'package.json', 'requirements.txt', 'pyproject.toml',
            'index.html', 'main.py', 'app.py'
        ]
        
        sorted_files = sorted(
            files_content.keys(),
            key=lambda x: (0 if x in priority_files else 1, x)
        )
        
        instruction_data = {
            "action": "UPDATE_ALL_FILES",
            "description": "Please update all files in the project according to the following JSON data",
            "source": {
                "repository": repo_url,
                "branch": branch,
                "commit": commit
            },
            "rules": [
                "1. You must update every file in the files array",
                "2. File content must match the content field exactly",
                "3. Create file if it doesn't exist, completely overwrite if it exists",
                "4. Do not skip any file from the list",
                "5. Preserve the exact file structure and paths",
                "6. After updating, output a complete list of all updated files"
            ],
            "files": []
        }
        
        for filepath in sorted_files:
            instruction_data["files"].append({
                "path": filepath,
                "action": "CREATE_OR_OVERWRITE",
                "content": files_content[filepath]
            })
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        return f"""📦 Repo JSON Generator - Structured Update Instructions
{'=' * 60}

📋 Summary:
  Repository: {repo_url}
  Branch: {branch}
  Commit: {commit[:8] if commit else 'N/A'}
  Files: {stats['file_count']}
  Total Size: {stats['total_size_mb']} MB
  Generated: {timestamp}

{'=' * 60}

📝 Copy the following JSON and send to AI Agent:

```json
{json.dumps(instruction_data, ensure_ascii=False, indent=2)}
```

{'=' * 60}
"""

    @staticmethod
    def generate_json_only(files_content: Dict[str, str],
                          repo_url: str, branch: str, commit: str) -> str:
        """Generate only JSON data without formatting"""
        sorted_files = sorted(files_content.keys())
        
        instruction_data = {
            "action": "UPDATE_ALL_FILES",
            "files": []
        }
        
        for filepath in sorted_files:
            instruction_data["files"].append({
                "path": filepath,
                "action": "CREATE_OR_OVERWRITE",
                "content": files_content[filepath]
            })
        
        return json.dumps(instruction_data, ensure_ascii=False, indent=2)

    @staticmethod
    def generate_diff_output(diff_data: Dict) -> str:
        """Generate formatted diff output"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        summary = diff_data['summary']
        
        return f"""🔄 Repo Diff Analysis - Comparison Result
{'=' * 60}

📋 Summary:
  Repository: {diff_data['repository']}
  Base Commit: {diff_data['base_commit_short']}
  Target Commit: {diff_data['target_commit_short']}
  Files Changed: {summary['files_changed']}
  Total Additions: +{summary['total_additions']}
  Total Deletions: -{summary['total_deletions']}
  Generated: {timestamp}

{'=' * 60}

📝 Copy the following JSON for AI analysis:

```json
{json.dumps(diff_data, ensure_ascii=False, indent=2)}
```

{'=' * 60}
"""

    @staticmethod
    def generate_info_output(info_data: Dict) -> str:
        """Generate formatted commit info output"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        commit = info_data['commit']
        
        is_merge = "✅ Yes (Merge Commit)" if commit['is_merge_commit'] else "❌ No"
        parents = ', '.join([p[:8] for p in commit['parent_commits']]) if commit['parent_commits'] else 'None'
        
        return f"""ℹ️  Repository Commit Info
{'=' * 60}

📋 Repository:
  URL: {info_data['repository']}
  Branch: {info_data['branch']}

🔗 Commit:
  Hash: {commit['hash']}
  Short: {commit['short_hash']}

📝 Message:
  Subject: {commit['message']['subject']}
  Body: {commit['message']['body'] or '(none)'}

👤 Author:
  Name: {commit['author']['name']}
  Email: {commit['author']['email']}
  Date: {commit['author']['timestamp']}

👤 Committer:
  Name: {commit['committer']['name']}
  Email: {commit['committer']['email']}
  Date: {commit['committer']['timestamp']}

🔀 Merge Commit: {is_merge}
📜 Parents: {parents}

{'=' * 60}

📝 Copy the following JSON for AI analysis:

```json
{json.dumps(info_data, ensure_ascii=False, indent=2)}
```

{'=' * 60}
"""


# ---------------------------------------------------------------------------
# CLI Commands
# ---------------------------------------------------------------------------

def extract_app_id_from_repo(repo_url: str) -> str:
    """Extract app-id from GitHub repository URL"""
    if repo_url.endswith('.git'):
        repo_url = repo_url[:-4]
    repo_name = repo_url.rstrip('/').split('/')[-1]
    return repo_name


def cmd_sync(args):
    """[Req 1] Sync command - Get changed files and full content from a commit
    
    Clones repo to: /tmp/github-sync-<repo-name>/ (auto-cleaned)
    """
    if not args.app_id:
        args.app_id = extract_app_id_from_repo(args.repo)
        print(f"🎯 Auto-extracted App ID: {args.app_id}")
    
    print(f"🚀 Starting Repo JSON Generator...")
    print(f"📦 Repository: {args.repo}")
    print(f"🎯 App ID: {args.app_id}")
    print(f"📌 Commit: {args.commit}")
    
    # Temporary clone directory: /tmp/github-sync-<repo-name>/
    # Auto-cleaned in finally block after execution
    temp_dir = '/tmp/github-sync-' + os.path.basename(args.repo).replace('.git', '')
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        print(f"\n📥 Step 1: Cloning repository...")
        print(f"   📁 Target: {temp_dir}")
        
        gh = GitHubSync(args.token)
        actual_commit = gh.clone_repo(args.repo, temp_dir, args.branch, args.commit)
        
        print(f"   ✅ Cloned successfully")
        print(f"   📌 Checked out commit: {actual_commit[:8] if actual_commit else 'N/A'}")
        
        # Step 2: Get changed files
        target_commit = args.commit
        print(f"\n🔍 Step 2: Getting changed files for commit {target_commit[:8]}...")
        changed_files = gh.get_commit_changed_files(temp_dir, target_commit)
        
        if not changed_files:
            print(f"\n⚠️  No changed files found for commit {target_commit[:8]}")
            print(f"   (This may be a merge commit or initial commit with no file changes)")
            sys.exit(0)
        
        print(f"   ✅ Found {len(changed_files)} changed files")
        
        # Step 3: Read changed files
        print(f"\n📂 Step 3: Reading changed files...")
        processor = FileProcessor(max_files=args.max_files, file_filter=args.filter, exclude_filter=args.exclude)
        files_content = processor.read_changed_files(temp_dir, changed_files)
        stats = processor.get_stats(files_content)
        
        print(f"   ✅ Read {stats['file_count']} text files")
        print(f"   📏 Total size: {stats['total_size_mb']} MB")
        
        # Step 4: Generate output
        print(f"\n📝 Step 4: Generating structured instructions...")
        generator = InstructionGenerator()
        
        if args.no_instructions:
            output = generator.generate_json_only(files_content, args.repo, args.branch, target_commit)
        else:
            output = generator.generate(files_content, args.repo, args.branch, target_commit, stats)
        
        # Step 5: Output
        print(f"\n📤 Step 5: Output instructions...")
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"   ✅ Saved to: {args.output}")
        else:
            print(output)
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}", file=sys.stderr)
        sys.exit(1)
    
    finally:
        # Clean up temporary clone directory (/tmp/github-sync-<repo-name>/)
        print(f"\n🧹 Cleaning up temporary files...")
        print(f"   🗑️  Removing: {temp_dir}")
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
            print(f"   ✅ Cleanup complete")


def cmd_diff(args):
    """[Req 2] Diff command - Compare two commits with detailed diff"""
    print(f"🔍 Getting commit diff...")
    print(f"📦 Repository: {args.repo}")
    print(f"📌 From Commit: {args.from_commit}")
    print(f"📌 To Commit: {args.to_commit}")
    
    if args.filter:
        print(f"📋 Include Filter: {args.filter}")
    if args.exclude:
        print(f"🚫 Exclude Filter: {args.exclude}")
    if args.max_files:
        print(f"📊 Max Files: {args.max_files}")
    
    try:
        gh = GitHubSync(args.token)
        diff_data = gh.get_commit_diff(
            args.repo, 
            args.from_commit, 
            args.to_commit,
            file_filter=args.filter,
            exclude_filter=args.exclude,
            max_files=args.max_files
        )
        
        generator = InstructionGenerator()
        
        if args.json_only:
            output = json.dumps(diff_data, ensure_ascii=False, indent=2)
        else:
            output = generator.generate_diff_output(diff_data)
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"\n   ✅ Diff saved to: {args.output}")
        else:
            print(output)
        
        print(f"\n📊 Summary:")
        print(f"   Files changed: {len(diff_data['files'])}")
        print(f"   Additions: +{diff_data['summary']['total_additions']}")
        print(f"   Deletions: -{diff_data['summary']['total_deletions']}")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


def cmd_info(args):
    """[Req 3] Info command - Get detailed commit information"""
    print(f"ℹ️  Getting repository/commit info...")
    print(f"📦 Repository: {args.repo}")
    if args.commit:
        print(f"📌 Commit: {args.commit}")
    else:
        print(f"📌 Branch: {args.branch} (HEAD)")
    
    try:
        gh = GitHubSync(args.token)
        info_data = gh.get_repo_info(args.repo, commit=args.commit, branch=args.branch)
        
        generator = InstructionGenerator()
        
        if args.json_only:
            output = json.dumps(info_data, ensure_ascii=False, indent=2)
        else:
            output = generator.generate_info_output(info_data)
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"\n   ✅ Info saved to: {args.output}")
        else:
            print(output)
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# CLI Parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Repo JSON Generator - Convert Git repository code to structured JSON instructions for AI agents',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:

================================================================
Requirement 1: Get changed files and code content from a specific commit
================================================================
python3 repo_json_generator.py sync --repo https://github.com/user/app.git --commit abc123
python3 repo_json_generator.py sync --repo URL --commit abc123 --filter "*.py,*.js"
python3 repo_json_generator.py sync --repo URL --commit abc123 --exclude "*.md,*.txt"
python3 repo_json_generator.py sync --repo URL --commit abc123 --filter "*.py,*.md" --exclude "*.test.py"
python3 repo_json_generator.py sync --repo URL --commit abc123 --max-files 30
python3 repo_json_generator.py sync --repo URL --commit abc123 --output update.json --no-instructions

Parameter Description:
  --max-files    Limit the maximum number of files to sync (default: 50). Used for batch processing large projects to avoid exceeding AI processing limits
  --filter       Specify file patterns to include (whitelist), supports: *.py,*.md or src/*.py etc.
  --exclude      Specify file patterns to exclude (blacklist), supports: *.md,*.txt etc.
  --output       Save output to file instead of printing to terminal
  --no-instructions  Output only pure JSON without formatted instruction text

================================================================
Requirement 2: Compare differences between two commits (including line numbers and code)
================================================================
python3 repo_json_generator.py diff --repo URL --from-commit abc123 --to-commit def456
python3 repo_json_generator.py diff --repo URL --from-commit abc123 --to-commit def456 --filter "*.py,*.js"
python3 repo_json_generator.py diff --repo URL --from-commit abc123 --to-commit def456 --exclude "*.md,*.txt"
python3 repo_json_generator.py diff --repo URL --from-commit abc123 --to-commit def456 --max-files 30
python3 repo_json_generator.py diff --repo URL --from-commit abc123 --to-commit def456 --json-only

Parameter Description:
  --max-files    Limit the maximum number of files in diff output (default: 50). Used for batch processing large diffs
  --filter       Specify file patterns to include (whitelist), supports: *.py,*.md or src/*.py etc.
  --exclude      Specify file patterns to exclude (blacklist), supports: *.md,*.txt etc.
  --output       Save output to file instead of printing to terminal
  --json-only    Output only pure JSON without formatted instruction text

================================================================
Requirement 3: Get detailed commit information
================================================================
python3 repo_json_generator.py info --repo URL --commit abc123
python3 repo_json_generator.py info --repo URL --branch main
python3 repo_json_generator.py info --repo URL --commit abc123 --json-only
"""
    )
    
    parser.add_argument('--token', 
                       default=os.environ.get('GITHUB_TOKEN'),
                       help='GitHub access token (or set GITHUB_TOKEN env var)')
    
    subparsers = parser.add_subparsers(dest='command', required=True)
    
    # sync command
    p = subparsers.add_parser('sync', 
                              help='[Req 1] Get changed files and full code content from a specific commit')
    p.add_argument('--repo', required=True, help='GitHub repository URL')
    p.add_argument('--branch', default='main', help='Git branch (default: main)')
    p.add_argument('--commit', required=True, help='Specific commit hash')
    p.add_argument('--app-id', help='Miaoda application ID (auto-extracted from repo URL if not provided)')
    p.add_argument('--max-files', type=int, default=50, help='Max files to sync (default: 50)')
    p.add_argument('--filter', help='File pattern filter to include (e.g., "*.py,*.js")')
    p.add_argument('--exclude', help='File pattern filter to exclude (e.g., "*.md,*.txt")')
    p.add_argument('--output', help='Output to file instead of stdout')
    p.add_argument('--no-instructions', action='store_true', help='Output only JSON')
    p.set_defaults(func=cmd_sync)
    
    # diff command
    p = subparsers.add_parser('diff', 
                              help='[Req 2] Get detailed differences between two commits (with line numbers and code)')
    p.add_argument('--repo', required=True, help='GitHub repository URL')
    p.add_argument('--from-commit', required=True, help='Base commit hash')
    p.add_argument('--to-commit', default='HEAD', help='Target commit (default: HEAD)')
    p.add_argument('--max-files', type=int, default=50, help='Max files to include in diff (default: 50)')
    p.add_argument('--filter', help='File pattern filter to include (e.g., "*.py,*.js")')
    p.add_argument('--exclude', help='File pattern filter to exclude (e.g., "*.md,*.txt")')
    p.add_argument('--output', help='Output to file instead of stdout')
    p.add_argument('--json-only', action='store_true', help='Output only JSON')
    p.set_defaults(func=cmd_diff)
    
    # info command
    p = subparsers.add_parser('info', 
                              help='[Req 3] Get detailed commit information')
    p.add_argument('--repo', required=True, help='GitHub repository URL')
    p.add_argument('--branch', default='main', help='Branch name (default: main)')
    p.add_argument('--commit', help='Specific commit hash (optional)')
    p.add_argument('--output', help='Output to file instead of stdout')
    p.add_argument('--json-only', action='store_true', help='Output only JSON')
    p.set_defaults(func=cmd_info)
    
    return parser


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
