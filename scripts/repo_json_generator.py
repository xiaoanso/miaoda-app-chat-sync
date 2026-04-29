#!/usr/bin/env python3
"""
Repo JSON Generator - Git Repository to Structured JSON Converter

Fetches code from Git repositories and generates structured JSON instructions
for accurate code updates via AI agents and automation tools.

## Features
- Cross-platform temp directory support (Windows/macOS/Linux)
- Circuit breaker mechanism for resilient operations
- Streaming/chunked output for large repositories
- Automatic cleanup of temporary files
- Sensitive information protection (tokens, credentials)

## Temporary Clone Locations

- **sync**: `<system_temp>/github-sync-<repo-name>/` (auto-cleaned after execution)
- **info**: `<system_temp>/github-info-<uuid>/` (auto-deleted)

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
import time
import uuid
import atexit
import signal
import functools
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Iterator, Any
from datetime import datetime
from contextlib import contextmanager
from enum import Enum


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

# Streaming configuration
DEFAULT_CHUNK_SIZE = 100  # Number of files per chunk in streaming mode
MAX_JSON_CHUNK_SIZE = 10 * 1024 * 1024  # 10MB per JSON chunk
MAX_MEMORY_SIZE = 500 * 1024 * 1024  # 500MB total for file storage


# ---------------------------------------------------------------------------
# Cross-Platform Temporary Directory Management
# ---------------------------------------------------------------------------

class TempDirManager:
    """
    Manages temporary directories across Windows/macOS/Linux.
    
    Features:
    - Uses system temp directory via tempfile.gettempdir()
    - Generates unique, collision-free directory names
    - Supports context manager for automatic cleanup
    - Registers with atexit for guaranteed cleanup
    """
    
    _instances: List[str] = []
    _cleanup_registered: bool = False
    
    def __init__(self, prefix: str = 'github-', base_dir: str = None):
        """
        Initialize TempDirManager.
        
        Args:
            prefix: Prefix for temporary directory name
            base_dir: Base directory (defaults to system temp)
        """
        self.prefix = prefix
        self.base_dir = base_dir or tempfile.gettempdir()
        self._path: Optional[str] = None
        self._owns_path: bool = False
    
    @staticmethod
    def _normalize_path(path: str) -> str:
        """Normalize path for cross-platform compatibility."""
        return os.path.normpath(os.path.abspath(path))
    
    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """Sanitize filename for cross-platform compatibility."""
        # Remove or replace unsafe characters
        name = re.sub(r'[<>:"/\\|?*]', '-', name)
        name = re.sub(r'-+', '-', name)
        name = name.strip('.-')
        # Limit length for Windows compatibility (MAX_PATH issues)
        if len(name) > 100:
            name = name[:100]
        return name or 'repo'
    
    def create(self) -> str:
        """
        Create a unique temporary directory.
        
        Returns:
            Path to the created temporary directory
        """
        unique_id = uuid.uuid4().hex[:8]
        sanitized_prefix = self._sanitize_filename(self.prefix)
        dir_name = f"{sanitized_prefix}-{unique_id}"
        self._path = os.path.join(self.base_dir, dir_name)
        self._owns_path = True
        
        # Ensure parent directory exists
        os.makedirs(self.base_dir, exist_ok=True)
        
        # Create directory with restricted permissions (Unix) or standard (Windows)
        os.makedirs(self._path, mode=0o755, exist_ok=True)
        
        # Track for cleanup
        if self._path not in TempDirManager._instances:
            TempDirManager._instances.append(self._path)
        
        # Register cleanup handler once
        if not TempDirManager._cleanup_registered:
            self._register_cleanup()
        
        return self._path
    
    def create_named(self, name: str) -> str:
        """
        Create a named temporary directory (for predictable paths).
        
        Args:
            name: Directory name (will be sanitized)
            
        Returns:
            Path to the created temporary directory
        """
        sanitized_name = self._sanitize_filename(name)
        unique_id = uuid.uuid4().hex[:4]
        dir_name = f"{sanitized_name}-{unique_id}"
        self._path = os.path.join(self.base_dir, dir_name)
        self._owns_path = True
        
        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs(self._path, mode=0o755, exist_ok=True)
        
        if self._path not in TempDirManager._instances:
            TempDirManager._instances.append(self._path)
        
        if not TempDirManager._cleanup_registered:
            self._register_cleanup()
        
        return self._path
    
    @staticmethod
    def _register_cleanup():
        """Register cleanup handlers for exit and signals."""
        TempDirManager._cleanup_registered = True
        
        # Register atexit
        atexit.register(TempDirManager.cleanup_all)
        
        # Register signal handlers (Unix)
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, TempDirManager._signal_handler)
        if hasattr(signal, 'SIGINT'):
            signal.signal(signal.SIGINT, TempDirManager._signal_handler)
    
    @staticmethod
    def _signal_handler(signum, frame):
        """Handle termination signals."""
        TempDirManager.cleanup_all()
        sys.exit(128 + signum)
    
    def cleanup(self) -> bool:
        """
        Remove the temporary directory.
        
        Returns:
            True if cleaned up successfully, False otherwise
        """
        if not self._path or not self._owns_path:
            return False
        
        try:
            if os.path.exists(self._path):
                # On Windows, try multiple times in case of locked files
                for attempt in range(3):
                    try:
                        shutil.rmtree(self._path, ignore_errors=True)
                        break
                    except PermissionError:
                        if attempt < 2:
                            time.sleep(0.1)
                        else:
                            # Last resort: mark for later cleanup
                            pass
                
                # Remove from tracking
                if self._path in TempDirManager._instances:
                    TempDirManager._instances.remove(self._path)
                
                return True
        except Exception:
            pass
        
        return False
    
    @staticmethod
    def cleanup_all():
        """Clean up all tracked temporary directories."""
        instances = TempDirManager._instances.copy()
        for path in instances:
            try:
                if os.path.exists(path):
                    shutil.rmtree(path, ignore_errors=True)
                if path in TempDirManager._instances:
                    TempDirManager._instances.remove(path)
            except Exception:
                pass
        
        TempDirManager._instances.clear()
    
    def __enter__(self) -> 'TempDirManager':
        """Context manager entry."""
        if not self._path:
            self.create()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.cleanup()
    
    @property
    def path(self) -> Optional[str]:
        """Get the current temporary directory path."""
        return self._path


@contextmanager
def temp_directory(prefix: str = 'github-', base_dir: str = None) -> Iterator[str]:
    """
    Context manager for temporary directories.
    
    Usage:
        with temp_directory('github-sync-') as temp_dir:
            # Use temp_dir here
            pass
        # Automatically cleaned up after exiting
    """
    manager = TempDirManager(prefix=prefix, base_dir=base_dir)
    path = manager.create()
    try:
        yield path
    finally:
        manager.cleanup()


# ---------------------------------------------------------------------------
# Circuit Breaker
# ---------------------------------------------------------------------------

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """
    Circuit breaker implementation for resilient operations.
    
    States:
    - CLOSED: Normal operation, requests go through
    - OPEN: Too many failures, reject requests immediately
    - HALF_OPEN: Testing if service recovered
    
    Args:
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds to wait before testing recovery
        expected_exceptions: Tuple of exception types to catch
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exceptions: Tuple = (Exception,)
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exceptions = expected_exceptions
        
        self._failure_count: int = 0
        self._last_failure_time: Optional[float] = None
        self._state: CircuitState = CircuitState.CLOSED
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        if self._state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._state = CircuitState.HALF_OPEN
        return self._state
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self._last_failure_time is None:
            return True
        return (time.time() - self._last_failure_time) >= self.recovery_timeout
    
    def record_success(self):
        """Record a successful operation."""
        self._failure_count = 0
        self._state = CircuitState.CLOSED
    
    def record_failure(self):
        """Record a failed operation."""
        self._failure_count += 1
        self._last_failure_time = time.time()
        
        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
    
    def allow_request(self) -> bool:
        """Check if a request should be allowed."""
        current_state = self.state
        
        if current_state == CircuitState.CLOSED:
            return True
        elif current_state == CircuitState.HALF_OPEN:
            return True
        else:  # OPEN
            return False
    
    def __call__(self, func):
        """Decorator for wrapping functions with circuit breaker."""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not self.allow_request():
                raise CircuitBreakerOpenError(
                    f"Circuit breaker is OPEN. Retry after "
                    f"{self.recovery_timeout} seconds."
                )
            
            try:
                result = func(*args, **kwargs)
                self.record_success()
                return result
            except self.expected_exceptions as e:
                self.record_failure()
                raise
        
        return wrapper
    
    def reset(self):
        """Manually reset the circuit breaker."""
        self._failure_count = 0
        self._last_failure_time = None
        self._state = CircuitState.CLOSED


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


def with_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: Tuple = (subprocess.TimeoutExpired, Exception)
):
    """
    Decorator for retry with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay between retries (seconds)
        max_delay: Maximum delay between retries (seconds)
        exponential_base: Base for exponential backoff
        exceptions: Tuple of exception types to retry on
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_attempts - 1:
                        # Calculate delay with exponential backoff
                        delay = min(
                            base_delay * (exponential_base ** attempt),
                            max_delay
                        )
                        # Add jitter (±25%)
                        import random
                        jitter = delay * 0.25
                        delay = delay + random.uniform(-jitter, jitter)
                        
                        time.sleep(delay)
                    else:
                        raise
            
            raise last_exception
        
        return wrapper
    return decorator


# ---------------------------------------------------------------------------
# Sensitive Information Handler
# ---------------------------------------------------------------------------

class SensitiveInfoHandler:
    """
    Handles sensitive information (tokens, credentials) securely.
    
    Features:
    - Redacts sensitive data from strings
    - Masks tokens in logs
    - Safe error messages
    """
    
    # Patterns to detect sensitive information
    SENSITIVE_PATTERNS = [
        (r'(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36}', '<GITHUB_TOKEN>'),
        (r'xox[baprs]-[A-Za-z0-9]{10,}', '<SLACK_TOKEN>'),
        (r'AIza[A-Za-z0-9_-]{35}', '<GOOGLE_API_KEY>'),
        (r'SK[A-Za-z0-9_-]{20,}', '<STRIPE_KEY>'),
        (r'Bearer\s+[A-Za-z0-9._-]+', r'Bearer <TOKEN>'),
        (r'password["\']?\s*[:=]\s*["\']?[^\s"\']+', 'password=<REDACTED>'),
    ]
    
    @classmethod
    def redact(cls, text: str) -> str:
        """
        Redact sensitive information from text.
        
        Args:
            text: Text to sanitize
            
        Returns:
            Text with sensitive information redacted
        """
        if not text:
            return text
        
        result = text
        for pattern, replacement in cls.SENSITIVE_PATTERNS:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        
        return result
    
    @classmethod
    def redact_url(cls, url: str) -> str:
        """
        Remove credentials from URL.
        
        Args:
            url: URL potentially containing credentials
            
        Returns:
            URL with credentials removed
        """
        if not url:
            return url
        
        # Remove user:pass@ from URLs
        result = re.sub(r'://[^@]+@', '://', url)
        return result
    
    @classmethod
    def safe_error_message(cls, error: Exception, include_details: bool = False) -> str:
        """
        Create a safe error message that doesn't leak sensitive info.
        
        Args:
            error: The exception
            include_details: Whether to include error details (for debugging)
            
        Returns:
            Safe error message string
        """
        error_str = str(error)
        redacted = cls.redact(error_str)
        
        if include_details:
            return f"Error: {redacted}"
        else:
            # Generic message for production
            return "Operation failed. Please check your configuration and try again."


class SecureLogger:
    """
    Logger that automatically redacts sensitive information.
    """
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
    
    def _safe_print(self, *args, **kwargs):
        """Print with sensitive data redacted."""
        safe_args = tuple(
            SensitiveInfoHandler.redact(str(arg)) if isinstance(arg, str) else arg
            for arg in args
        )
        print(*safe_args, **kwargs)
    
    def info(self, *args, **kwargs):
        self._safe_print(*args, **kwargs)
    
    def warning(self, *args, **kwargs):
        self._safe_print(f"⚠️  ", *args, **kwargs)
    
    def error(self, *args, **kwargs):
        self._safe_print(f"❌ ", *args, **kwargs)
    
    def debug(self, *args, **kwargs):
        if self.verbose:
            self._safe_print(f"🔍 ", *args, **kwargs)


# ---------------------------------------------------------------------------
# Git Repository Operations
# ---------------------------------------------------------------------------

class RepoJSONGenerator:
    """Handles Git repository operations (GitHub, GitLab, etc.)
    
    Features:
    - Circuit breaker for resilient operations
    - Automatic retry with exponential backoff
    - Sensitive information protection
    - Cross-platform support
    
    Clone target directory is specified by caller.
    Caller is responsible for cleanup after use.
    """
    
    def __init__(self, token: str = None, verbose: bool = False):
        self.token = token or os.environ.get('GITHUB_TOKEN')
        self.verbose = verbose
        self.logger = SecureLogger(verbose=verbose)
        
        # Initialize circuit breaker for git operations
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60
        )
    
    def _get_git_env(self) -> Dict[str, str]:
        """Get environment variables for git commands with authentication"""
        env = os.environ.copy()
        if self.token:
            env['GIT_ASKPASS'] = 'echo'
            env['GIT_TERMINAL_PROMPT'] = '0'
            # Don't expose token in environment for subprocess
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
            # Re-add token
            return f"{parts[0]}://x-access-token:{self.token}@{parts[1].split('@')[1]}"
        
        if repo_url.startswith('https://'):
            return repo_url.replace('https://', f'https://x-access-token:{self.token}@')
        elif repo_url.startswith('http://'):
            return repo_url.replace('http://', f'https://x-access-token:{self.token}@')
        return repo_url
    
    def _log_operation(self, operation: str, *args, **kwargs):
        """Log operation with sensitive data redacted."""
        if self.verbose:
            self.logger.debug(f"[Git] {operation}:", *args, **kwargs)
    
    @with_retry(max_attempts=3, base_delay=2.0, max_delay=30.0)
    def _execute_git_command(self, cmd: List[str], cwd: str, timeout: int = 60) -> subprocess.CompletedProcess:
        """
        Execute a git command with retry and circuit breaker protection.
        
        Args:
            cmd: Git command arguments
            cwd: Working directory
            timeout: Command timeout in seconds
            
        Returns:
            CompletedProcess result
        """
        if not self._circuit_breaker.allow_request():
            raise CircuitBreakerOpenError(
                "Git operations circuit breaker is OPEN. Too many recent failures."
            )
        
        try:
            env = self._get_git_env()
            self._log_operation("Executing:", ' '.join(cmd[:3]) + '...', f"cwd={cwd}")
            
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env
            )
            
            if result.returncode == 0:
                self._circuit_breaker.record_success()
            else:
                self._circuit_breaker.record_failure()
                error_msg = SensitiveInfoHandler.redact(result.stderr)
                self._log_operation("Command failed:", error_msg)
            
            return result
            
        except subprocess.TimeoutExpired as e:
            self._circuit_breaker.record_failure()
            raise
        except Exception as e:
            self._circuit_breaker.record_failure()
            raise
    
    def _detect_default_branch(self, repo_url: str) -> str:
        """
        Detect the default branch of a remote repository.
        
        Returns:
            Default branch name (e.g., 'main', 'master', 'develop')
        """
        with temp_directory(prefix='branch-detect-') as temp_dir:
            try:
                auth_url = self._make_authenticated_url(repo_url)
                
                # Initialize bare repo to get remote info
                cmd = ['git', 'ls-remote', '--symref', auth_url, 'HEAD']
                result = self._execute_git_command(cmd, cwd=temp_dir, timeout=30)
                
                if result.returncode == 0:
                    # Parse output like: ref: refs/heads/main	HEAD
                    for line in result.stdout.split('\n'):
                        if line.startswith('ref:'):
                            parts = line.split('\t')
                            if len(parts) >= 1:
                                ref = parts[0]
                                if 'refs/heads/' in ref:
                                    branch = ref.split('refs/heads/')[1]
                                    self._log_operation("Detected branch:", branch)
                                    return branch
                
                # Fallback to common branch names
                for branch in ['main', 'master', 'develop']:
                    cmd = ['git', 'ls-remote', '--heads', auth_url, branch]
                    result = self._execute_git_command(cmd, cwd=temp_dir, timeout=30)
                    if result.returncode == 0 and result.stdout.strip():
                        self._log_operation("Using fallback branch:", branch)
                        return branch
                
                return 'main'
                
            except Exception as e:
                self._log_operation("Branch detection failed:", str(e))
                return 'main'
    
    def clone_repo(self, repo_url: str, target_dir: str, 
                   branch: str = 'main', commit: str = None) -> str:
        """
        Clone repository and optionally checkout specific commit.
        Uses full history fetch to support any commit checkout.
        """
        try:
            auth_url = self._make_authenticated_url(repo_url)
            
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
                result = self._execute_git_command(cmd, cwd=target_dir, timeout=180)
                if result.returncode != 0:
                    # Try as branch first
                    cmd = ['git', '-C', target_dir, 'fetch', 'origin', commit]
                    result = self._execute_git_command(cmd, cwd=target_dir, timeout=180)
                    if result.returncode != 0:
                        raise Exception(f"Failed to fetch commit {commit[:8]}")
                
                # Checkout the commit
                cmd = ['git', '-C', target_dir, 'checkout', commit]
                result = self._execute_git_command(cmd, cwd=target_dir, timeout=60)
                if result.returncode != 0:
                    raise Exception(f"Failed to checkout commit {commit[:8]}")
                
                actual_commit = commit
            else:
                # Fetch branch
                print(f"   📥 Fetching branch {branch}...")
                cmd = ['git', '-C', target_dir, 'fetch', 'origin', branch]
                result = self._execute_git_command(cmd, cwd=target_dir, timeout=180)
                if result.returncode != 0:
                    raise Exception(f"Failed to fetch branch {branch}")
                
                # Checkout
                cmd = ['git', '-C', target_dir, 'checkout', '-f', '-B', branch, 
                      f'origin/{branch}']
                result = self._execute_git_command(cmd, cwd=target_dir, timeout=60)
                if result.returncode != 0:
                    raise Exception(f"Failed to checkout branch {branch}")
                
                # Get actual commit
                cmd = ['git', '-C', target_dir, 'rev-parse', 'HEAD']
                result = self._execute_git_command(cmd, cwd=target_dir, timeout=10)
                actual_commit = result.stdout.strip() if result.returncode == 0 else None
            
            # Verify the commit
            if actual_commit:
                cmd = ['git', '-C', target_dir, 'cat-file', '-t', actual_commit]
                result = self._execute_git_command(cmd, cwd=target_dir, timeout=10)
                if result.returncode != 0:
                    raise Exception(f"Invalid commit hash: {actual_commit[:8]}")
            
            return actual_commit
            
        except CircuitBreakerOpenError:
            raise Exception(
                "Git operations temporarily unavailable due to too many failures. "
                "Please try again in a few minutes."
            )
        except subprocess.TimeoutExpired:
            raise Exception("Git operation timed out. Check network connection.")
        except Exception as e:
            raise Exception(f"Git operation failed: {SensitiveInfoHandler.safe_error_message(e)}")
    
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
        with temp_directory(prefix='github-info-') as temp_dir:
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
                target_ref = actual_branch

            env = self._get_git_env()
            
            # Get detailed commit info
            # %H = full hash, %h = short hash, %s = subject, %b = body
            # %an = author name, %ae = author email, %aI = author ISO date
            # %cn = committer name, %ce = committer email, %cI = committer ISO date
            # %P = parent hashes (space separated)
            format_str = '%H||%h||%s||%b||%an||%ae||%aI||%cn||%ce||%cI||%P'
            cmd = ['git', '-C', temp_dir, 'log', '-1', f'--format={format_str}', target_ref]
            result = self._execute_git_command(cmd, cwd=temp_dir, timeout=30)
            
            if result.returncode != 0:
                raise Exception(f"Failed to get commit info")
            
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
                'repository': SensitiveInfoHandler.redact_url(repo_url),
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
            if (current['type'] == next_change['type'] and 
                abs(current.get('line', 0) - next_change.get('line', 0)) <= 1):
                # Merge content
                current['content'] = current.get('content', '') + '\n' + next_change.get('content', '')
                current['line'] = max(current.get('line', 0), next_change.get('line', 0))
            else:
                merged.append(current)
                current = next_change.copy()
        
        merged.append(current)
        return merged

    def get_commit_full_changes(self, repo_url: str, commit: str, branch: str = 'main', 
                                file_filter: str = None, exclude_filter: str = None) -> Dict:
        """
        Get full changes of a specific commit including file diffs.
        
        Args:
            repo_url: Git repository URL
            commit: Commit hash
            branch: Branch name
            file_filter: Comma-separated file patterns to include
            exclude_filter: Comma-separated file patterns to exclude
        
        Returns:
            Dict containing action, description, source, rules, and files
        """
        with temp_directory(prefix='github-info-') as temp_dir:
            # Clone and checkout the specific commit
            self.clone_repo(repo_url, temp_dir, branch='main', commit=commit)
            env = self._get_git_env()
            
            # Get commit info
            format_str = '%H||%h||%s||%b||%an||%ae||%aI||%cn||%ce||%cI||%P'
            cmd = ['git', '-C', temp_dir, 'log', '-1', f'--format={format_str}', commit]
            result = self._execute_git_command(cmd, cwd=temp_dir, timeout=30)
            
            if result.returncode != 0:
                raise Exception(f"Failed to get commit info")
            
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
            result = self._execute_git_command(cmd, cwd=temp_dir, timeout=120)
            
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
            
            # Apply file filters
            if file_filter or exclude_filter:
                processor = FileProcessor(file_filter=file_filter, exclude_filter=exclude_filter)
                
                filtered_files = {}
                for file_path, file_info in files_dict.items():
                    if processor._should_include_file(file_path):
                        filtered_files[file_path] = file_info
                    else:
                        print(f"   ⏭️  Filtered out: {file_path}")
                files_dict = filtered_files
            
            # Merge consecutive changes and read full file content
            files_list = []
            for file_path, file_info in files_dict.items():
                merged_changes = self._merge_consecutive_changes(file_info['changes'])
                file_info['changes'] = merged_changes
                
                if file_info['status'] != 'deleted':
                    full_file_path = os.path.join(temp_dir, file_path)
                    try:
                        if os.path.exists(full_file_path):
                            with open(full_file_path, 'r', encoding='utf-8') as f:
                                file_info['content'] = f.read()
                        else:
                            file_info['content'] = ''
                    except Exception as e:
                        print(f"   ⚠️  Error reading {file_path}: {str(e)}")
                        file_info['content'] = ''
                else:
                    file_info['content'] = ''
                
                files_list.append(file_info)
            
            return {
                'action': 'CREATE_OR_UPDATE_FILES',
                'description': 'Please create or update all files in the project according to the following JSON data',
                'source': {
                    'repository': SensitiveInfoHandler.redact_url(repo_url),
                    'branch': branch,
                    'commit': commit_hash
                },
                'summary': {
                    'files_changed': len(files_list),
                    'total_additions': sum(f.get('additions', 0) for f in files_list),
                    'total_deletions': sum(f.get('deletions', 0) for f in files_list),
                    'files': [
                        {
                            'path': f['path'],
                            'status': f['status'],
                            'additions': f.get('additions', 0),
                            'deletions': f.get('deletions', 0)
                        }
                        for f in files_list
                    ]
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
    

    def get_commit_changed_files(self, repo_dir: str, commit: str) -> List[Tuple[str, str]]:
        """
        Get list of changed files for a specific commit.
        
        Returns:
            List of tuples (status, filepath)
        """
        try:
            env = self._get_git_env()
            
            cmd = ['git', '-C', repo_dir, 'show', '--name-status', '--format=', commit]
            result = self._execute_git_command(cmd, cwd=repo_dir, timeout=30)
            
            if result.returncode != 0:
                raise Exception("git show failed")
            
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
            raise Exception(f"Failed to get changed files: {SensitiveInfoHandler.safe_error_message(e)}")


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
        """Check if file should be included"""
        if not self._matches_filter(filepath):
            return False
        
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
# Streaming Output Generator
# ---------------------------------------------------------------------------

class StreamingJSONEncoder:
    """
    Streaming JSON encoder for large outputs.
    
    Supports:
    - Chunked output for large file lists
    - Memory-efficient processing
    - Progress callbacks
    """
    
    def __init__(self, chunk_size: int = DEFAULT_CHUNK_SIZE):
        self.chunk_size = chunk_size
    
    def stream_json_chunks(self, data: Dict) -> Iterator[Dict]:
        """
        Generate JSON data in chunks.
        
        Yields:
            Dict chunks with metadata about chunk position
        """
        files = data.get('files', [])
        total_files = len(files)
        
        if total_files == 0:
            yield {'type': 'complete', 'data': data}
            return
        
        # Yield header without files
        header = {k: v for k, v in data.items() if k != 'files'}
        header['files'] = []
        header['chunk_info'] = {
            'total_chunks': (total_files + self.chunk_size - 1) // self.chunk_size,
            'total_files': total_files,
            'current_chunk': 0,
            'chunk_size': self.chunk_size
        }
        
        yield {
            'type': 'header',
            'data': header,
            'chunk_info': header['chunk_info']
        }
        
        # Yield file chunks
        for i in range(0, total_files, self.chunk_size):
            chunk_files = files[i:i + self.chunk_size]
            chunk_data = {
                'type': 'chunk',
                'chunk_index': i // self.chunk_size,
                'files': chunk_files,
                'chunk_info': {
                    'total_chunks': header['chunk_info']['total_chunks'],
                    'total_files': total_files,
                    'current_chunk': i // self.chunk_size + 1,
                    'files_in_chunk': len(chunk_files),
                    'start_index': i,
                    'end_index': min(i + self.chunk_size, total_files)
                }
            }
            yield chunk_data
        
        # Yield completion marker
        yield {
            'type': 'complete',
            'chunk_info': header['chunk_info']
        }
    
    def estimate_size(self, data: Dict) -> int:
        """Estimate total JSON size in bytes."""
        json_str = json.dumps(data, ensure_ascii=False)
        return len(json_str.encode('utf-8'))


class StreamingFileWriter:
    """
    Stream large JSON output to file in chunks.
    
    Features:
    - Write incrementally to avoid memory issues
    - Support for multiple output formats
    - Progress tracking
    """
    
    def __init__(self, chunk_size: int = DEFAULT_CHUNK_SIZE):
        self.chunk_size = chunk_size
        self.encoder = StreamingJSONEncoder(chunk_size=chunk_size)
    
    def write_streaming(self, data: Dict, output_path: str, 
                        progress_callback=None) -> Dict:
        """
        Write JSON data in streaming mode.
        
        Args:
            data: Full data structure
            output_path: Output file path
            progress_callback: Optional callback(percent, message)
            
        Returns:
            Summary of written chunks
        """
        total_files = len(data.get('files', []))
        total_chunks = (total_files + self.chunk_size - 1) // self.chunk_size if total_files > 0 else 1
        chunks_written = 0
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for chunk in self.encoder.stream_json_chunks(data):
                chunk_type = chunk.get('type', 'unknown')
                chunk_info = chunk.get('chunk_info', {})
                
                if chunk_type == 'header':
                    # Write header with first chunk of files
                    header_data = chunk['data']
                    # Get first chunk of files
                    files = data.get('files', [])[:self.chunk_size]
                    header_data['files'] = files
                    
                    json_str = json.dumps(header_data, ensure_ascii=False, indent=2)
                    # Add continuation marker
                    if total_chunks > 1:
                        json_str = json_str[:-2] + ',\n  "_streaming": true,\n  "_chunk_info": ' + \
                                   json.dumps(chunk_info, ensure_ascii=False) + '\n}'
                    
                    f.write(json_str)
                    chunks_written += 1
                    
                    if progress_callback:
                        progress_callback(
                            chunks_written / total_chunks * 100,
                            f"Writing chunk {chunks_written}/{total_chunks}"
                        )
                
                elif chunk_type == 'chunk':
                    # Write subsequent chunks
                    chunk_files = chunk['files']
                    chunk_json = ',\n{\n  "_chunk_index": ' + str(chunk['chunk_index']) + ',\n  "_chunk_info": ' + \
                                json.dumps(chunk_info, ensure_ascii=False) + ',\n  "files": ' + \
                                json.dumps(chunk_files, ensure_ascii=False) + '\n}'
                    f.write(chunk_json)
                    chunks_written += 1
                    
                    if progress_callback:
                        progress_callback(
                            chunks_written / total_chunks * 100,
                            f"Writing chunk {chunks_written}/{total_chunks}"
                        )
                
                elif chunk_type == 'complete':
                    # Close JSON
                    f.write('\n}')
                    
                    if progress_callback:
                        progress_callback(100, "Complete")
        
        return {
            'total_chunks': total_chunks,
            'chunks_written': chunks_written,
            'total_files': total_files
        }


# ---------------------------------------------------------------------------
# JSON Instruction Generator
# ---------------------------------------------------------------------------

class InstructionGenerator:
    """Generates structured JSON instructions for code sync"""
    
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
                "repository": SensitiveInfoHandler.redact_url(repo_url),
                "branch": branch,
                "commit": commit[:8] if commit else 'N/A'
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
  Repository: {SensitiveInfoHandler.redact_url(repo_url)}
  Branch: {branch}
  Commit: {commit[:8] if commit else 'N/A'}
  Files: {stats['file_count']}
  Total Size: {stats['total_size_mb']} MB
  Generated: {timestamp}

{'=' * 60}

📝 Copy the following JSON and send to AI Agent:

```json
{json.dumps(instruction_data, ensure_ascii=False, indent=2)}
{'=' * 60} """

@staticmethod
def generate_json_only(files_content: Dict[str, str],
                      repo_url: str, branch: str, commit: str) -> str:
    """Generate only JSON data without formatting"""
    sorted_files = sorted(files_content.keys())
    
    instruction_data = {
        "action": "CREATE_OR_UPDATE_FILES",
        "source": {
            "repository": SensitiveInfoHandler.redact_url(repo_url),
            "branch": branch,
            "commit": commit[:8] if commit else 'N/A'
        },
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
    
    total_files = len(files)
    total_additions = sum(f.get('additions', 0) for f in files)
    total_deletions = sum(f.get('deletions', 0) for f in files)
    
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

🔗 Source: Repository: {source.get('repository', 'N/A')} Branch: {source.get('branch', 'N/A')} Commit: {source.get('commit', 'N/A')[:8] if source.get('commit') else 'N/A'}

📊 Statistics: Files Changed: {total_files} Total Additions: +{total_additions} Total Deletions: -{total_deletions}

📁 Changed Files ({total_files}): {chr(10).join(files_summary)}

{'=' * 60}

📝 Copy the following JSON for complete changes:

json

{json.dumps(info_data, ensure_ascii=False, indent=2)}
{'=' * 60} """

@staticmethod
def generate_info_output(info_data: Dict) -> str:
    """Generate formatted commit info output"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    commit = info_data['commit']
    
    is_merge = "✅ Yes (Merge Commit)" if commit['is_merge_commit'] else "❌ No"
    parents = ', '.join([p[:8] for p in commit['parent_commits']]) if commit['parent_commits'] else 'None'
    
    return f"""ℹ️  Repository Commit Info
{'=' * 60}

📋 Repository: URL: {info_data['repository']} Branch: {info_data['branch']}

🔗 Commit: Hash: {commit['hash']} Short: {commit['short_hash']}

📝 Message: Subject: {commit['message']['subject']} Body: {commit['message']['body'] or '(none)'}

👤 Author: Name: {commit['author']['name']} Email: {commit['author']['email']} Date: {commit['author']['timestamp']}

👤 Committer: Name: {commit['committer']['name']} Email: {commit['committer']['email']} Date: {commit['committer']['timestamp']}

🔀 Merge Commit: {is_merge} 📜 Parents: {parents}

{'=' * 60}

📝 Copy the following JSON for AI analysis:

json

{json.dumps(info_data, ensure_ascii=False, indent=2)}
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

    Uses system temp directory with automatic cleanup.
    """
    if not args.app_id:
        args.app_id = extract_app_id_from_repo(args.repo)
        print(f"🎯 Auto-extracted App ID: {args.app_id}")

    print(f"🚀 Starting Repo JSON Generator...")
    print(f"📦 Repository: {SensitiveInfoHandler.redact_url(args.repo)}")
    print(f"🎯 App ID: {args.app_id}")
    print(f"📌 Commit: {args.commit}")

    # Determine temp directory base (cross-platform)
    temp_base = tempfile.gettempdir()
    sanitized_name = TempDirManager._sanitize_filename(
        os.path.basename(args.repo).replace('.git', '')
    )
    temp_dir = os.path.join(temp_base, f"github-sync-{sanitized_name}")

    # Clean up any existing temp directory
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)

    os.makedirs(temp_dir, exist_ok=True)

    # Track for cleanup
    if temp_dir not in TempDirManager._instances:
        TempDirManager._instances.append(temp_dir)

    try:
        print(f"\n📥 Step 1: Cloning repository...")
        print(f"   📁 Target: {temp_dir}")
        
        gh = RepoJSONGenerator(args.token, verbose=args.verbose)
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
    
        print(f"   ✅ Read {stats['file_count']} text files")
        print(f"   📏 Total size: {stats['total_size_mb']} MB")
        
        # Check if streaming is recommended
        estimated_size = sum(len(json.dumps(f).encode('utf-8')) for f in files_content.values())
        should_stream = estimated_size > MAX_JSON_CHUNK_SIZE or len(files_content) > 500
        
        # Step 4: Generate output
        print(f"\n📝 Step 4: Generating structured instructions...")
        generator = InstructionGenerator()
        
        if args.streaming and (args.output or should_stream):
            # Use streaming output for large results
            print(f"   📡 Using streaming mode (large output detected)")
            _write_streaming_output(args, files_content, stats, generator, gh, target_commit)
        elif args.no_instructions:
            output = generator.generate_json_only(files_content, args.repo, args.branch, target_commit)
            _write_output(args, output)
        else:
            output = generator.generate(files_content, args.repo, args.branch, target_commit, stats)
            _write_output(args, output)
        
    except CircuitBreakerOpenError as e:
        print(f"\n❌ {SensitiveInfoHandler.safe_error_message(e)}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {SensitiveInfoHandler.safe_error_message(e)}", file=sys.stderr)
        sys.exit(1)
    finally:
        # Clean up temporary clone directory
        print(f"\n🧹 Cleaning up temporary files...")
        print(f"   🗑️  Removing: {temp_dir}")
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
            print(f"   ✅ Cleanup complete")


def _write_output(args, output: str):
    """Write output to file or stdout."""
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output)
        print(f" ✅ Saved to: {args.output}")
    else:
        print(output)


def _write_streaming_output(args, files_content: Dict, stats: Dict, generator: InstructionGenerator, gh: RepoJSONGenerator, target_commit: str):
    """Write output using streaming for large datasets."""
    instruction_data = {
        "action": "CREATE_OR_UPDATE_FILES",
        "description": "Please create or update all files in the project according to the following JSON data",
        "source": {
            "repository": SensitiveInfoHandler.redact_url(args.repo),
            "branch": args.branch,
            "commit": target_commit[:8] if target_commit else 'N/A'
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

    for filepath in sorted(files_content.keys()):
        instruction_data["files"].append({
            "path": filepath,
            "action": "CREATE_OR_OVERWRITE",
            "content": files_content[filepath]
        })

    writer = StreamingFileWriter(chunk_size=args.chunk_size)

    def progress(percent, message):
        print(f"   📊 {message} ({percent:.1f}%)")

    if args.output:
        result = writer.write_streaming(instruction_data, args.output, progress)
        print(f"   ✅ Streaming write complete: {result['chunks_written']} chunks, {result['total_files']} files")
    else:
        # For stdout, still show progress but write complete JSON
        print(f"   📡 Large output ({stats['total_size_mb']} MB) - consider using --output for better performance")
        json_output = json.dumps(instruction_data, ensure_ascii=False, indent=2)
        print(json_output)


def cmd_info(args):
    """[Req 2] Info command - Get detailed commit information"""
    print(f"ℹ️  Getting repository/commit info...")
    print(f"📦 Repository: {SensitiveInfoHandler.redact_url(args.repo)}")
    print(f"📌 Commit: {args.commit}")
    print(f"📋 Mode: Full changes (including diffs)")

    if args.filter:
        print(f"📥 Filter: {args.filter}")
    if args.exclude:
        print(f"🚫 Exclude: {args.exclude}")

    try:
        gh = RepoJSONGenerator(args.token, verbose=args.verbose)
        
        print(f"\n📥 Fetching full changes for commit {args.commit[:8]}...")
        info_data = gh.get_commit_full_changes(
            args.repo, 
            commit=args.commit, 
            branch=args.branch,
            file_filter=args.filter,
            exclude_filter=args.exclude
        )
        
        generator = InstructionGenerator()
        
        # Always display summary in terminal
        summary = info_data.get('summary', {})
        files = info_data.get('files', [])
        
        if summary:
            total_files = summary.get('files_changed', len(files))
            total_additions = summary.get('total_additions', 0)
            total_deletions = summary.get('total_deletions', 0)
            files_list = summary.get('files', files)
        else:
            total_files = len(files)
            total_additions = sum(f.get('additions', 0) for f in files)
            total_deletions = sum(f.get('deletions', 0) for f in files)
            files_list = files
        
        print(f"\n📊 Summary:")
        print(f"  Files Changed: {total_files}")
        print(f"  Total Additions: +{total_additions}")
        print(f"  Total Deletions: -{total_deletions}")
        
        print(f"\n📁 Changed Files ({total_files}):")
        for file_info in files_list[:50]:  # Limit display
            status = file_info.get('status', 'modified')
            status_icon = {'added': '🆕 Added', 'deleted': '🗑️ Deleted', 'modified': '📝 Modified'}.get(status, '❓')
            additions = file_info.get('additions', 0)
            deletions = file_info.get('deletions', 0)
            stats_str = f"+{additions}/-{deletions}" if additions or deletions else ""
            print(f"  {status_icon}: {file_info['path']} ({stats_str})")
        
        if total_files > 50:
            print(f"  ... and {total_files - 50} more files")
        
        # Handle file output
        if args.output:
            if args.no_instructions:
                json_output = json.dumps(info_data, ensure_ascii=False, indent=2)
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(json_output)
                print(f"\n   ✅ Pure JSON saved to: {args.output}")
            else:
                full_output = generate_commit_full_changes(info_data)
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(full_output)
                print(f"\n   ✅ Full changes saved to: {args.output}")
        
    except CircuitBreakerOpenError as e:
        print(f"\n❌ {SensitiveInfoHandler.safe_error_message(e)}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        import traceback
        print(f"\n❌ Error: {SensitiveInfoHandler.safe_error_message(e)}", file=sys.stderr)
        print(f"\n🔍 Detailed traceback:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
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

Streaming output for large repositories:
python3 repo_json_generator.py sync --repo URL --commit abc123 --streaming --chunk-size 100 --output large_update.json

================================================================
Requirement 2: Get detailed commit information
================================================================
python3 repo_json_generator.py info --repo URL --commit abc123
python3 repo_json_generator.py info --repo URL --commit abc123 --no-instructions
python3 repo_json_generator.py info --repo URL --commit abc123 --output info.json
python3 repo_json_generator.py info --repo URL --commit abc123 --filter "*.py,*.js"

================================================================
Advanced Options
================================================================
--verbose      Enable verbose logging
--streaming    Force streaming mode for large outputs
--chunk-size   Number of files per chunk in streaming mode (default: 100)

================================================================
Feature Highlights
================================================================
• Circuit breaker: Automatically retries failed git operations
• Cross-platform: Works on Windows, macOS, Linux
• Secure: Tokens and credentials are automatically redacted
• Auto-cleanup: Temporary directories are cleaned up on exit
"""
    )

    parser.add_argument('--token', 
                       default=os.environ.get('GITHUB_TOKEN'),
                       help='GitHub access token (or set GITHUB_TOKEN env var)')
    parser.add_argument('--verbose', '-v',
                       action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--streaming',
                       action='store_true',
                       help='Force streaming output mode for large repositories')
    parser.add_argument('--chunk-size',
                       type=int,
                       default=DEFAULT_CHUNK_SIZE,
                       help=f'Number of files per chunk in streaming mode (default: {DEFAULT_CHUNK_SIZE})')

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
    p.add_argument('--commit', required=True, help='Specific commit hash (required)')
    p.add_argument('--filter', help='File pattern filter to include (e.g., "*.py,*.js")')
    p.add_argument('--exclude', help='File pattern filter to exclude (e.g., "*.md,*.txt")')
    p.add_argument('--output', help='Save output to file instead of printing to terminal')
    p.add_argument('--no-instructions', action='store_true', help='Output only pure JSON without formatted instruction text')
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
