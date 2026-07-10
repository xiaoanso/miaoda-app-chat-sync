#!/usr/bin/env python3
"""
Repo JSON Generator - Web UI Server

A lightweight HTTP server that bridges the web interface with the generator API.
Provides API endpoints to execute generator commands and return results.

Usage:
    python3 web-ui/server.py [port]
"""

import json
import mimetypes
import os
import sys
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from git.repository import RepoJSONGenerator


class GeneratorHandler(BaseHTTPRequestHandler):
    """HTTP request handler for Generator API"""

    def do_OPTIONS(self):
        """Handle CORS preflight for extension requests."""
        parsed_path = urlparse(self.path)
        if parsed_path.path.startswith('/api/'):
            self.send_response(204)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-GitHub-Token, X-GitLab-Token, X-Bitbucket-Token')
            self.end_headers()
        else:
            self.send_error(404)

    def do_GET(self):
        """Handle GET requests - serve the web interface and API"""
        parsed_path = urlparse(self.path)

        if parsed_path.path == '/' or parsed_path.path == '/index.html':
            self._serve_static_file('index.html', 'text/html; charset=utf-8')

        elif parsed_path.path == '/favicon.ico':
            self._serve_static_file('favicon.png', 'image/png')

        elif parsed_path.path in ('/app.js', '/styles.css', '/favicon.png') or parsed_path.path.startswith('/lib/'):
            rel_path = parsed_path.path.lstrip('/')
            self._serve_static_file(rel_path)

        elif parsed_path.path == '/api/status':
            client_tokens = self._client_tokens_from_headers()
            server_tokens = {
                'github': bool(os.environ.get('GITHUB_TOKEN')),
                'gitlab': bool(os.environ.get('GITLAB_TOKEN')),
                'bitbucket': bool(os.environ.get('BITBUCKET_TOKEN')),
            }
            self._send_json_response(200, {
                'success': True,
                'hasToken': any(client_tokens.values()) or any(server_tokens.values()),
                'publicMode': not any(server_tokens.values()),
                'serverTokens': server_tokens,
                'clientTokens': client_tokens,
                # Backward compatibility for older clients
                'tokens': {
                    'github': client_tokens['github'] or server_tokens['github'],
                    'gitlab': client_tokens['gitlab'] or server_tokens['gitlab'],
                    'bitbucket': client_tokens['bitbucket'] or server_tokens['bitbucket'],
                },
            })

        elif parsed_path.path == '/api/branches':
            query_params = parse_qs(parsed_path.query)
            repo = query_params.get('repo', [''])[0]

            if not repo:
                self._send_json_response(400, {'success': False, 'error': 'Repository URL is required'})
                return

            try:
                result = self._get_generator().get_branches(repo)
                self._send_json_response(200, {
                    'success': True,
                    'branches': result['branches'],
                    'count': result['count'],
                    'repository': result['repository'],
                })
            except Exception as e:
                self._send_json_response(500, {'success': False, 'error': str(e)})

        elif parsed_path.path in ('/api/commits', '/api/versions'):
            query_params = parse_qs(parsed_path.query)
            repo = query_params.get('repo', [''])[0]
            branch = query_params.get('branch', [''])[0]
            limit = query_params.get('limit', ['30'])[0]

            if not repo or not branch:
                self._send_json_response(400, {
                    'success': False,
                    'error': 'Repository URL and branch are required',
                })
                return

            try:
                limit_value = int(limit)
            except ValueError:
                self._send_json_response(400, {'success': False, 'error': 'limit must be an integer'})
                return

            try:
                result = self._get_generator().get_branch_versions(repo, branch, limit=limit_value)
                commits = [
                    {
                        'hash': version['hash'],
                        'message': version['message'],
                        'short_hash': version['short_hash'],
                        'date': version['date'],
                    }
                    for version in result['versions']
                ]
                self._send_json_response(200, {
                    'success': True,
                    'repository': result['repository'],
                    'branch': result['branch'],
                    'limit': result['limit'],
                    'count': result['count'],
                    'commits': commits,
                    'versions': result['versions'],
                })
            except Exception as e:
                self._send_json_response(500, {'success': False, 'error': str(e)})

        else:
            self.send_error(404, f"Not found: {self.path}")

    def do_POST(self):
        """Handle POST requests - execute generator commands"""
        parsed_path = urlparse(self.path)

        if parsed_path.path == '/api/generate':
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length)
                request_data = json.loads(body.decode('utf-8'))

                repo = request_data.get('repo', '')
                if not repo:
                    self._send_json_response(400, {
                        'success': False,
                        'error': 'Repository URL is required',
                    })
                    return

                command = request_data.get('command', 'sync')
                if command not in ('sync', 'info', 'full'):
                    self._send_json_response(400, {
                        'success': False,
                        'error': f'Unknown command: {command}',
                    })
                    return

                try:
                    result = self._run_generate(request_data)
                    self._send_json_response(200, result)
                except Exception as e:
                    self._send_json_response(200, {
                        'success': False,
                        'error': str(e),
                        'data': None,
                        'meta': {
                            'command': request_data.get('command', 'sync'),
                            'repo': request_data.get('repo', ''),
                            'branch': request_data.get('branch', 'main'),
                        },
                    })

            except json.JSONDecodeError:
                self._send_json_response(400, {
                    'success': False,
                    'error': 'Invalid JSON in request body',
                })
            except Exception as e:
                self._send_json_response(500, {
                    'success': False,
                    'error': str(e),
                })
        else:
            self.send_error(404, f"Not found: {self.path}")

    def _run_generate(self, params: dict) -> dict:
        """Run generate command via RepoJSONGenerator and return structured JSON."""
        start_time = time.time()
        command = params.get('command', 'sync')
        repo = params['repo']
        branch = params.get('branch', 'main')
        commit = (params.get('commit') or '').strip()
        file_filter = (params.get('filter') or '').strip() or None
        exclude_filter = (params.get('exclude') or '').strip() or None
        max_files = int(params.get('maxFiles', 50))

        generator = self._get_generator()

        if not commit:
            commit = generator.resolve_latest_commit(repo, branch)

        if command == 'sync':
            data = generator.get_commit_full_changes(
                repo_url=repo,
                commit=commit,
                branch=branch,
                file_filter=file_filter,
                exclude_filter=exclude_filter,
                command_type='sync',
            )
        elif command == 'info':
            data = generator.get_commit_diff_info(
                repo_url=repo,
                commit=commit,
                branch=branch,
                file_filter=file_filter,
                exclude_filter=exclude_filter,
            )
        elif command == 'full':
            data = generator.get_full_repo_content(
                repo_url=repo,
                commit=commit,
                branch=branch,
                file_filter=file_filter,
                exclude_filter=exclude_filter,
                max_files=max_files,
                command_type='full',
            )
        else:
            raise ValueError(f'Unknown command: {command}')

        duration = round(time.time() - start_time, 1)
        return {
            'success': True,
            'data': data,
            'meta': {
                'command': command,
                'duration': duration,
                'repo': repo,
                'branch': branch,
                'commit': commit,
            },
        }

    def _send_json_response(self, status_code, data):
        """Send JSON response"""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def _serve_static_file(self, rel_path: str, content_type: str = None):
        """Serve a file from the web-ui directory (no path traversal)."""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.normpath(os.path.join(base_dir, rel_path))
        if not file_path.startswith(base_dir) or not os.path.isfile(file_path):
            self.send_error(404, f'Not found: /{rel_path}')
            return

        if content_type is None:
            guessed, _ = mimetypes.guess_type(file_path)
            content_type = guessed or 'application/octet-stream'
            if content_type == 'text/javascript':
                content_type = 'application/javascript; charset=utf-8'
            elif content_type == 'image/png':
                content_type = 'image/png'

        with open(file_path, 'rb') as f:
            data = f.read()

        self.send_response(200)
        self.send_header('Content-type', content_type)
        self.send_header('Content-Length', str(len(data)))
        if rel_path in ('favicon.png',) or rel_path.endswith('.png'):
            self.send_header('Cache-Control', 'public, max-age=86400')
        self.end_headers()
        self.wfile.write(data)

    def _client_tokens_from_headers(self) -> dict:
        """Report whether the client sent platform tokens (values are never echoed)."""
        return {
            'github': bool(self.headers.get('X-GitHub-Token')),
            'gitlab': bool(self.headers.get('X-GitLab-Token')),
            'bitbucket': bool(self.headers.get('X-Bitbucket-Token')),
        }

    def _get_generator(self):
        """Create a generator using per-request client tokens, with server env fallback."""
        return RepoJSONGenerator(
            token=self.headers.get('X-GitHub-Token') or None,
            gitlab_token=self.headers.get('X-GitLab-Token') or None,
            bitbucket_token=self.headers.get('X-Bitbucket-Token') or None,
            verbose=False,
        )

    def log_message(self, format, *args):
        """Custom log format"""
        print(f"[{self.log_date_time_string()}] {format % args}")


def run_server(port=8080):
    """Start the HTTP server"""
    server = HTTPServer(('0.0.0.0', port), GeneratorHandler)
    print("=" * 60)
    print("  Repo JSON Generator - Web UI")
    print("=" * 60)
    print()
    print(f"  Server running at:")
    print(f"    → Local: http://localhost:{port}")
    print(f"    → Network: http://0.0.0.0:{port}")
    print()
    print(f"  Public mode: no server-side tokens required")
    print(f"  Users provide their own tokens via X-GitHub-Token headers")
    print()
    print(f"  Press Ctrl+C to stop")
    print("=" * 60)
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\nShutting down server...")
        server.shutdown()


if __name__ == '__main__':
    port = 8080
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Invalid port number: {sys.argv[1]}, using default 8080")

    run_server(port)
