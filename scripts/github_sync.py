#!/usr/bin/env python3
"""
GitHub Code Sync to Miaoda - OpenClaw Skill

Fetches code from GitHub repositories and generates structured JSON instructions
for accurate code updates via Miaoda's chat API.

Usage:
    python github_sync.py sync --repo URL --app-id ID --context-id ID [options]
    python github_sync.py diff --repo URL --from COMMIT --to COMMIT [options]
    python github_sync.py info --repo URL [options]
"""

import argparse
import json
import os
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TEXT_EXTENSIONS = {
    '.py', '.js', '.jsx', '.ts', '.tsx',
    '.html', '.css', '.scss', '.less',
    '.json', '.yaml', '.yml', '.toml',
    '.md', '.txt', '.sh', '.bash',
    '.xml', '.sql', '.env',
    '.vue', '.svelte', '.rst',
}

SKIP_DIRS = {
    '.git', 'node_modules', '__pycache__', 
    '.venv', 'venv', 'dist', 'build',
    '.next', '.nuxt', 'target',
    '.DS_Store', 'thumbs.db',
}

MAX_SINGLE_FILE_SIZE = 100 * 1024 * 1024  # 100MB (prevent memory issues)


# ---------------------------------------------------------------------------
# GitHub Operations
# ---------------------------------------------------------------------------

class GitHubSync:
    """Handles GitHub repository operations"""
    
    def __init__(self, token: str = None):
        self.token = token or os.environ.get('GITHUB_TOKEN')
        
    def clone_repo(self, repo_url: str, target_dir: str, 
                   branch: str = 'main', commit: str = None) -> str:
        """
        Clone repository and optionally checkout specific commit
        
        Args:
            repo_url: GitHub repository URL
            target_dir: Directory to clone into
            branch: Branch name (default: main)
            commit: Specific commit hash (optional)
            
        Returns:
            Actual commit hash that was checked out
        """
        try:
            # Construct URL with token if provided
            if self.token and 'github.com' in repo_url:
                # Insert token into URL
                if repo_url.startswith('https://'):
                    repo_url = repo_url.replace('https://', f'https://{self.token}@')
            
            # Clone repository (shallow clone for speed)
            cmd = ['git', 'clone', '--depth', '1']
            if branch and not commit:
                cmd.extend(['-b', branch])
            cmd.extend([repo_url, target_dir])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                raise Exception(f"Git clone failed: {result.stderr}")
            
            # Checkout specific commit if provided
            actual_commit = commit
            if commit:
                cmd = ['git', '-C', target_dir, 'fetch', '--depth', '1', 'origin', commit]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                if result.returncode != 0:
                    raise Exception(f"Failed to fetch commit {commit}: {result.stderr}")
                
                cmd = ['git', '-C', target_dir, 'checkout', commit]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if result.returncode != 0:
                    raise Exception(f"Failed to checkout commit {commit}: {result.stderr}")
                actual_commit = commit
            
            # Get actual commit hash
            cmd = ['git', '-C', target_dir, 'rev-parse', 'HEAD']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                actual_commit = result.stdout.strip()
            
            return actual_commit
            
        except subprocess.TimeoutExpired:
            raise Exception("Git operation timed out. Check network connection.")
        except Exception as e:
            raise Exception(f"Git operation failed: {str(e)}")
    
    def get_repo_info(self, repo_url: str, branch: str = 'main') -> Dict:
        """Get repository information"""
        temp_dir = tempfile.mkdtemp(prefix='github-info-')
        try:
            self.clone_repo(repo_url, temp_dir, branch)
            
            # Get commit info
            cmd = ['git', '-C', temp_dir, 'log', '-1', '--format=%H%n%h%n%s%n%ai']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                return {
                    'commit_hash': lines[0],
                    'commit_short': lines[1],
                    'message': lines[2],
                    'date': lines[3],
                    'branch': branch
                }
            else:
                return {'error': 'Failed to get repo info'}
                
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def get_commit_diff(self, repo_url: str, from_commit: str, 
                       to_commit: str = 'HEAD') -> List[str]:
        """Get list of changed files between commits"""
        temp_dir = tempfile.mkdtemp(prefix='github-diff-')
        try:
            self.clone_repo(repo_url, temp_dir)
            
            # Fetch both commits
            cmd = ['git', '-C', temp_dir, 'fetch', '--depth', '1', 'origin', from_commit, to_commit]
            subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            # Get diff
            cmd = ['git', '-C', temp_dir, 'diff', '--name-only', f'{from_commit}..{to_commit}']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                return [f for f in result.stdout.strip().split('\n') if f]
            else:
                return []
                
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# File Reading & Processing
# ---------------------------------------------------------------------------

class FileProcessor:
    """Handles file reading and processing"""
    
    def __init__(self, max_files: int = 50, file_filter: str = None):
        self.max_files = max_files
        self.file_filter = self._parse_filter(file_filter) if file_filter else None
    
    def _parse_filter(self, filter_str: str) -> List[str]:
        """Parse file filter string"""
        return [f.strip() for f in filter_str.split(',')]
    
    def _matches_filter(self, filepath: str) -> bool:
        """Check if file matches the filter"""
        if not self.file_filter:
            return True
        
        filename = os.path.basename(filepath)
        for pattern in self.file_filter:
            if pattern.startswith('*.'):
                # Extension match
                ext = '.' + pattern[2:]
                if filepath.endswith(ext):
                    return True
            elif '*' in pattern:
                # Glob match
                import fnmatch
                if fnmatch.fnmatch(filepath, pattern):
                    return True
            else:
                # Exact match
                if filepath == pattern:
                    return True
        return False
    
    def read_files(self, directory: str) -> Dict[str, str]:
        """
        Read all text files from directory
        
        Args:
            directory: Root directory to scan
            
        Returns:
            Dict mapping relative paths to file contents
        """
        files_content = {}
        skipped_files = []
        
        for root, dirs, files in os.walk(directory):
            # Skip unwanted directories
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            
            for file in sorted(files):  # Sort for consistent ordering
                filepath = os.path.join(root, file)
                relpath = os.path.relpath(filepath, directory)
                
                # Check filter
                if not self._matches_filter(relpath):
                    continue
                
                # Check extension
                ext = os.path.splitext(file)[1].lower()
                if ext not in TEXT_EXTENSIONS:
                    skipped_files.append(relpath)
                    continue
                
                # Check file size
                try:
                    file_size = os.path.getsize(filepath)
                    if file_size > MAX_SINGLE_FILE_SIZE:
                        skipped_files.append(f"{relpath} (too large: {file_size} bytes)")
                        continue
                except:
                    continue
                
                # Read file content
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        files_content[relpath] = content
                        
                        # Check if we've reached max files
                        if len(files_content) >= self.max_files:
                            break
                except Exception as e:
                    skipped_files.append(f"{relpath} (error: {str(e)})")
            
            if len(files_content) >= self.max_files:
                break
        
        return files_content
    
    def get_stats(self, files_content: Dict[str, str]) -> Dict:
        """Get file statistics"""
        total_size = sum(len(content.encode('utf-8')) for content in files_content.values())
        
        # Group by extension
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
        """
        Generate JSON structured instruction
        
        Args:
            files_content: Dict of filepath -> content
            repo_url: GitHub repository URL
            branch: Git branch
            commit: Commit hash
            stats: File statistics
            
        Returns:
            Formatted instruction string ready to copy
        """
        # Sort files by priority (config files first)
        priority_files = [
            'package.json', 'requirements.txt', 'pyproject.toml',
            'index.html', 'main.py', 'app.py'
        ]
        
        sorted_files = sorted(
            files_content.keys(),
            key=lambda x: (0 if x in priority_files else 1, x)
        )
        
        # Build JSON structure
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
                "2. File content must match the content field exactly - do not modify or alter any code",
                "3. Create file if it doesn't exist, completely overwrite if it exists",
                "4. Do not skip any file from the list",
                "5. Preserve the exact file structure and paths",
                "6. After updating, output a complete list of all updated files for verification"
            ],
            "files": []
        }
        
        for filepath in sorted_files:
            instruction_data["files"].append({
                "path": filepath,
                "action": "CREATE_OR_OVERWRITE",
                "content": files_content[filepath]
            })
        
        # Format output
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        output = f"""📦 GitHub Code Sync - Structured Update Instructions
{'═' * 60}

📋 Summary:
  Repository: {repo_url}
  Branch: {branch}
  Commit: {commit[:8] if commit else 'N/A'}
  Files: {stats['file_count']}
  Total Size: {stats['total_size_mb']} MB
  Generated: {timestamp}

{'═' * 60}

📝 Copy the following JSON and send to Miaoda chat:

```json
{json.dumps(instruction_data, ensure_ascii=False, indent=2)}
```

{'═' * 60}
✅ Instructions generated successfully!

💡 Next Steps:
  1. Copy the JSON above
  2. Send to Miaoda chat with your app
  3. Wait for AI to update all files
  4. Verify the updated file list
  5. Preview: https://www.miaoda.cn/projects/YOUR_APP_ID
"""
        
        return output
    
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


# ---------------------------------------------------------------------------
# CLI Commands
# ---------------------------------------------------------------------------

def cmd_sync(args):
    """Sync command handler"""
    print(f"🚀 Starting GitHub Code Sync...")
    print(f"📦 Repository: {args.repo}")
    print(f"🎯 App ID: {args.app_id}")
    
    # Create temp directory
    temp_dir = tempfile.mkdtemp(prefix='github-sync-')
    
    try:
        # Step 1: Clone repository
        print(f"\n📥 Step 1: Cloning repository...")
        gh = GitHubSync(args.token)
        commit = gh.clone_repo(
            args.repo, 
            temp_dir, 
            args.branch, 
            args.commit
        )
        print(f"   ✅ Cloned successfully")
        print(f"   📌 Commit: {commit[:8]}")
        
        # Step 2: Read files
        print(f"\n📂 Step 2: Reading files...")
        processor = FileProcessor(
            max_files=args.max_files,
            file_filter=args.filter
        )
        files_content = processor.read_files(temp_dir)
        stats = processor.get_stats(files_content)
        print(f"   ✅ Read {stats['file_count']} files")
        print(f"   📏 Total size: {stats['total_size_mb']} MB")
        
        # Step 3: Generate instructions
        print(f"\n📝 Step 3: Generating structured instructions...")
        generator = InstructionGenerator()
        
        if args.no_instructions:
            output = generator.generate_json_only(
                files_content, args.repo, args.branch, commit
            )
        else:
            output = generator.generate(
                files_content, args.repo, args.branch, commit, stats
            )
        
        # Step 4: Output
        print(f"\n📤 Step 4: Output instructions...")
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
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)
        print(f"\n🧹 Cleaned up temporary files")


def cmd_diff(args):
    """Diff command handler"""
    print(f"🔍 Getting commit diff...")
    
    try:
        gh = GitHubSync(args.token)
        changed_files = gh.get_commit_diff(
            args.repo, 
            args.from_commit, 
            args.to_commit
        )
        
        print(f"\n📋 Changed files ({len(changed_files)}):")
        for filepath in changed_files:
            ext = os.path.splitext(filepath)[1].lower()
            if ext in TEXT_EXTENSIONS:
                print(f"  ✅ {filepath}")
            else:
                print(f"  ⚠️  {filepath} (binary)")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


def cmd_info(args):
    """Info command handler"""
    print(f"ℹ️  Getting repository info...")
    
    try:
        gh = GitHubSync(args.token)
        info = gh.get_repo_info(args.repo, args.branch)
        
        if 'error' in info:
            print(f"\n❌ Error: {info['error']}")
            sys.exit(1)
        
        print(f"\n📋 Repository Info:")
        print(f"  Branch: {info['branch']}")
        print(f"  Commit: {info['commit_hash'][:8]}")
        print(f"  Short: {info['commit_short']}")
        print(f"  Message: {info['message']}")
        print(f"  Date: {info['date']}")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# CLI Parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='GitHub Code Sync to Miaoda - Generate structured code update instructions',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Sync latest code from public repo
  python github_sync.py sync --repo https://github.com/user/repo --app-id xxx --context-id yyy

  # Sync specific commit
  python github_sync.py sync --repo https://github.com/user/repo --commit abc123 --app-id xxx --context-id yyy

  # Sync only Python files
  python github_sync.py sync --repo https://github.com/user/repo --filter "*.py" --app-id xxx --context-id yyy

  # Save output to file
  python github_sync.py sync --repo https://github.com/user/repo --app-id xxx --context-id yyy --output update.json
        """
    )
    
    # Global options
    parser.add_argument('--token', 
                       default=os.environ.get('GITHUB_TOKEN'),
                       help='GitHub access token (or set GITHUB_TOKEN env var)')
    
    subparsers = parser.add_subparsers(dest='command', required=True)
    
    # sync command
    p = subparsers.add_parser('sync', help='Sync code from GitHub')
    p.add_argument('--repo', required=True, help='GitHub repository URL')
    p.add_argument('--branch', default='main', help='Git branch (default: main)')
    p.add_argument('--commit', help='Specific commit hash (overrides branch)')
    p.add_argument('--app-id', required=True, help='Miaoda application ID')
    p.add_argument('--context-id', required=True, help='Miaoda conversation ID')
    p.add_argument('--max-files', type=int, default=50, help='Max files to sync (default: 50)')
    p.add_argument('--filter', help='File pattern filter (e.g., "*.py,*.js")')
    p.add_argument('--output', help='Output to file instead of stdout')
    p.add_argument('--no-instructions', action='store_true', 
                   help='Output only JSON, without instructions')
    p.set_defaults(func=cmd_sync)
    
    # diff command
    p = subparsers.add_parser('diff', help='Show diff between commits')
    p.add_argument('--repo', required=True, help='GitHub repository URL')
    p.add_argument('--from', dest='from_commit', required=True, help='Base commit hash')
    p.add_argument('--to', dest='to_commit', default='HEAD', help='Target commit (default: HEAD)')
    p.set_defaults(func=cmd_diff)
    
    # info command
    p = subparsers.add_parser('info', help='Get repository info')
    p.add_argument('--repo', required=True, help='GitHub repository URL')
    p.add_argument('--branch', default='main', help='Branch name (default: main)')
    p.set_defaults(func=cmd_info)
    
    return parser


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

import sys

def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
