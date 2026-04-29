#!/usr/bin/env python3
"""
Repo JSON Generator - Git Repository to Structured JSON Converter

Fetches code from Git repositories and generates structured JSON instructions
for accurate code updates via AI agents and automation tools.

## Temporary Clone Locations

- **sync**: `/tmp/github-sync-<repo-name>/` (auto-cleaned after execution)
- **info**: `/tmp/github-info-<random>/` (auto-deleted)

All directories are automatically removed after script completion.

Usage:
    python3 repo_json_generator.py sync --repo URL --commit COMMIT [options]
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

class RepoJSONGenerator:
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
    
    def _detect_default_branch(self, repo_url: str) -> str:
        """
        Detect the default branch of a remote repository.
        
        Returns:
            Default branch name (e.g., 'main', 'master', 'develop')
        """
        try:
            auth_url = self._make_authenticated_url(repo_url)
            env = self._get_git_env()
            
            # Create a temporary directory for detection
            temp_dir = tempfile.mkdtemp(prefix='branch-detect-')
            
            try:
                # Initialize bare repo to get remote info
                cmd = ['git', 'ls-remote', '--symref', auth_url, 'HEAD']
                result = subprocess.run(cmd, capture_output=True, text=True, 
                                       timeout=30, env=env)
                
                if result.returncode == 0:
                    # Parse output like: ref: refs/heads/main	HEAD
                    for line in result.stdout.split('\n'):
                        if line.startswith('ref:'):
                            parts = line.split('\t')
                            if len(parts) >= 1:
                                ref = parts[0]
                                if 'refs/heads/' in ref:
                                    branch = ref.split('refs/heads/')[1]
                                    print(f"   🎯 Detected default branch: {branch}")
                                    return branch
                
                # Fallback to common branch names
                for branch in ['main', 'master', 'develop']:
                    cmd = ['git', 'ls-remote', '--heads', auth_url, branch]
                    result = subprocess.run(cmd, capture_output=True, text=True, 
                                           timeout=30, env=env)
                    if result.returncode == 0 and result.stdout.strip():
                        print(f"   🎯 Using fallback branch: {branch}")
                        return branch
                
                print(f"   ⚠️  Could not detect default branch, using 'main'")
                return 'main'
                
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)
                
        except Exception as e:
            print(f"   ⚠️  Branch detection failed: {str(e)}, using 'main'")
            return 'main'
    
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
            # Auto-detect branch if not specified or using default 'main'
            if commit:
                # When commit is specified, we can use any branch for initial clone
                # since we'll checkout the specific commit anyway
                self.clone_repo(repo_url, temp_dir, branch='main', commit=commit)
                target_ref = commit
            else:
                # Auto-detect default branch
                actual_branch = self._detect_default_branch(repo_url)
                self.clone_repo(repo_url, temp_dir, branch=actual_branch)

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
    
    def _merge_consecutive_changes(self, changes: List[Dict]) -> List[Dict]:
        """
        Merge consecutive changes of the same type.
        
        Args:
            changes: List of change dictionaries
            
        Returns:
            Merged list of changes
        """
        if not changes:
            return []
        
        merged = []
        current = changes[0].copy()
        
        for i in range(1, len(changes)):
            next_change = changes[i]
            
            # Check if we can merge (same type and consecutive lines)
            # Note: For additions, line numbers in new file are consecutive.
            # For deletions, line numbers in old file are consecutive.
            if (current['type'] == next_change['type'] and 
                abs(current.get('line', 0) - next_change.get('line', 0)) <= 1):
                # Merge content
                current['content'] = current.get('content', '') + '\n' + next_change.get('content', '')
                # Update line to the later one (or keep start, depending on preference. 
                # Here we update to max to represent the end of the block or just keep tracking)
                # Actually for a block, keeping the start line is usually more useful for insertion point.
                # But following the reference logic:
                current['line'] = max(current.get('line', 0), next_change.get('line', 0))
            else:
                merged.append(current)
                current = next_change.copy()
        
        merged.append(current)
        return merged

    def get_commit_full_changes(self, repo_url: str, commit: str, branch: str = 'main') -> Dict:
        """
        Get full changes of a specific commit including file diffs.
        
        Returns:
            {
                "action": "CREATE_OR_UPDATE_FILES",
                "description": "...",
                "source": {...},
                "rules": [...],
                "files": [
                    {
                        "path": "...",
                        "status": "added|modified|deleted",
                        "additions": N,
                        "deletions": N,
                        "changes": [
                            {
                                "type": "addition|deletion|replacement",
                                "line": N,
                                "content": "..."
                            }
                        ]
                    }
                ]
            }
        """
        temp_dir = tempfile.mkdtemp(prefix='github-info-')
        try:
            # Clone and checkout the specific commit
            self.clone_repo(repo_url, temp_dir, branch='main', commit=commit)
            env = self._get_git_env()
            
            # Get commit info
            format_str = '%H||%h||%s||%b||%an||%ae||%aI||%cn||%ce||%cI||%P'
            cmd = ['git', '-C', temp_dir, 'log', '-1', f'--format={format_str}', commit]
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
            
            # Get full diff
            if parent_list:
                parent_commit = parent_list[0]
            else:
                # Initial commit has no parent, cannot diff
                raise Exception("Cannot get changes for initial commit (no parent commit found)")
            
            # Get unified diff with 0 context lines for precise change location
            cmd = ['git', '-C', temp_dir, 'diff', '--unified=0', parent_commit, commit]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=env)
            
            full_diff = result.stdout if result.returncode == 0 else ''
            
            # Parse diff into file-based structure
            files_dict = {}
            current_file = None
            new_start = 0
            
            for line in full_diff.split('\n'):
                if line.startswith('diff --git'):
                    # Parse file path
                    parts = line.split(' b/')
                    if len(parts) == 2:
                        file_path = parts[1]
                        current_file = {
                            'path': file_path,
                            'status': 'modified',
                            'additions': 0,
                            'deletions': 0,
                            'changes': []
                        }
                        files_dict[file_path] = current_file
                    
                elif line.startswith('new file mode'):
                    if current_file:
                        current_file['status'] = 'added'
                        
                elif line.startswith('deleted file mode'):
                    if current_file:
                        current_file['status'] = 'deleted'
                        
                elif line.startswith('@@'):
                    # Parse hunk header: @@ -old_start,old_count +new_start,new_count @@
                    match = re.search(r'\+(\d+)(?:,(\d+))?', line)
                    if match and current_file:
                        new_start = int(match.group(1))
                        # new_count = int(match.group(2)) if match.group(2) else 1
                        
                elif line.startswith('+') and not line.startswith('+++') and current_file:
                    current_file['additions'] += 1
                    current_file['changes'].append({
                        'type': 'addition',
                        'line': new_start,
                        'content': line[1:]
                    })
                    new_start += 1
                    
                elif line.startswith('-') and not line.startswith('---') and current_file:
                    current_file['deletions'] += 1
                    current_file['changes'].append({
                        'type': 'deletion',
                        'line': new_start if 'new_start' in dir() else 0,
                        'content': line[1:]
                    })
                    # Deletions don't increment new_start in the new file context, 
                    # but logically we might want to track old line numbers if needed.
                    # The reference implementation uses new_start which might be slightly off for deletions 
                    # relative to the NEW file state, but typically deletions are identified by what's missing.
                    # However, strictly following the provided reference logic:
            
            # Merge consecutive changes of the same type
            files_list = []
            for file_path, file_info in files_dict.items():
                merged_changes = self._merge_consecutive_changes(file_info['changes'])
                file_info['changes'] = merged_changes
                files_list.append(file_info)
            
            # Build output
            return {
                'action': 'CREATE_OR_UPDATE_FILES',
                'description': 'Please create or update all files in the project according to the following JSON data',
                'source': {
                    'repository': repo_url,
                    'branch': branch,
                    'commit': commit_hash
                },
                'rules': [
                    '1. MUST update ALL files in the files array - no exceptions',
                    '2. MUST copy content EXACTLY as-is - no modifications, no reformatting, no \'improvements\'',
                    '3. MUST preserve ALL whitespace, newlines, indentation, and comments exactly',
                    '4. MUST use EXACT file paths from path field - no path transformation',
                    '5. If file exists: overwrite completely (NOT merge)',
                    '6. If file does not exist: create it',
                    '7. After updating: output complete list of all updated files (format: 1. /path/to/file)',
                    '8. DO NOT ask for confirmation - just execute',
                    '9. DO NOT use Git commands - file operations only',
                    '10. DO NOT skip any file for any reason'
                ],
                'files': files_list
            }
                
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    

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
            "action": "CREATE_OR_UPDATE_FILES",
            "description": "Please create or update all files in the project according to the following JSON data",
            "source": {
                "repository": repo_url,
                "branch": branch,
                "commit": commit
            },
            "rules": [
                "1. MUST update ALL files in the files array - no exceptions",
                "2. MUST copy content EXACTLY as-is - no modifications, no reformatting, no 'improvements'",
                "3. MUST preserve ALL whitespace, newlines, indentation, and comments exactly",
                "4. MUST use EXACT file paths from path field - no path transformation",
                "5. If file exists: overwrite completely (NOT merge)",
                "6. If file does not exist: create it",
                "7. After updating: output complete list of all updated files (format: 1. /path/to/file)",
                "8. DO NOT ask for confirmation - just execute",
                "9. DO NOT use Git commands - file operations only",
                "10. DO NOT skip any file for any reason"
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
            "action": "CREATE_OR_UPDATE_FILES",
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
    def generate_commit_full_changes(info_data: Dict) -> str:
        """Generate formatted output for commit full changes"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        source = info_data.get('source', {})
        files = info_data.get('files', [])
        
        # Calculate statistics
        total_files = len(files)
        total_additions = sum(f.get('additions', 0) for f in files)
        total_deletions = sum(f.get('deletions', 0) for f in files)
        
        # Build files summary
        files_summary = []
        for file_info in files:
            status = file_info.get('status', 'modified')
            status_icon = {'added': '🆕 Added', 'deleted': '🗑️ Deleted', 'modified': '📝 Modified'}.get(status, '❓')
            additions = file_info.get('additions', 0)
            deletions = file_info.get('deletions', 0)
            stats_str = f"+{additions}/-{deletions}" if additions or deletions else ""
            files_summary.append(f"  {status_icon}: {file_info['path']} ({stats_str})")
        
        return f"""📋 Commit Full Changes
{'=' * 60}

🔗 Source:
  Repository: {source.get('repository', 'N/A')}
  Branch: {source.get('branch', 'N/A')}
  Commit: {source.get('commit', 'N/A')[:8] if source.get('commit') else 'N/A'}

📊 Statistics:
  Files Changed: {total_files}
  Total Additions: +{total_additions}
  Total Deletions: -{total_deletions}

📁 Changed Files ({total_files}):
{chr(10).join(files_summary)}

{'=' * 60}

📝 Copy the following JSON for complete changes:

```json
{json.dumps(info_data, ensure_ascii=False, indent=2)}
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
        
        gh = RepoJSONGenerator(args.token)
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


def cmd_info(args):
    """[Req 2] Info command - Get detailed commit information"""
    print(f"ℹ️  Getting repository/commit info...")
    print(f"📦 Repository: {args.repo}")
    if args.commit:
        print(f"📌 Commit: {args.commit}")
    else:
        print(f"📌 Branch: {args.branch} (HEAD)")
    
    if args.full:
        print(f"📋 Mode: Full changes (including diffs)")
    
    try:
        gh = RepoJSONGenerator(args.token)
        
        if args.full:
            if not args.commit:
                print(f"\n❌ Error: --full mode requires --commit parameter", file=sys.stderr)
                sys.exit(1)
            
            print(f"\n📥 Fetching full changes for commit {args.commit[:8]}...")
            info_data = gh.get_commit_full_changes(args.repo, commit=args.commit, branch=args.branch)
        else:
            info_data = gh.get_repo_info(args.repo, commit=args.commit, branch=args.branch)
        
        generator = InstructionGenerator()
        
        if args.full:
            if args.json_only:
                output = json.dumps(info_data, ensure_ascii=False, indent=2)
            else:
                output = generator.generate_commit_full_changes(info_data)
        else:
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
Requirement 2: Get detailed commit information
================================================================
python3 repo_json_generator.py info --repo URL --commit abc123
python3 repo_json_generator.py info --repo URL --branch main
python3 repo_json_generator.py info --repo URL --commit abc123 --json-only
python3 repo_json_generator.py info --repo URL --branch main --output info.json

Parameter Description:
  --repo         GitHub repository URL (required)
  --branch       Branch name (default: main, used when --commit is not specified)
  --commit       Specific commit hash (optional, overrides branch)
  --full         Get full changes including file diffs (requires --commit)
  --output       Save output to file instead of printing to terminal
  --json-only    Output only pure JSON without formatted instruction text
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
    
    # info command
    p = subparsers.add_parser('info', 
                              help='[Req 2] Get detailed commit information')
    p.add_argument('--repo', required=True, help='GitHub repository URL')
    p.add_argument('--branch', default='main', help='Branch name (default: main)')
    p.add_argument('--commit', help='Specific commit hash (optional)')
    p.add_argument('--full', action='store_true', help='Get full changes including file diffs (requires --commit)')
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
